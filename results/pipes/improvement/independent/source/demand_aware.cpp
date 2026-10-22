#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kDigLength = 20;

#ifndef DEMAND_WINDOW
#define DEMAND_WINDOW 128
#endif

#ifndef DEMAND_BONUS_METERS
#define DEMAND_BONUS_METERS 20
#endif

constexpr std::size_t kDemandWindow = DEMAND_WINDOW;
constexpr std::int64_t kDemandBonusMeters = DEMAND_BONUS_METERS;

struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
};

class Allocator {
public:
    // Free spans are half-open [start, end). The map supports merging after a
    // removal; the set chooses the shortest fitting span, then the lowest start.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;

    void place(int length) {
        std::int64_t start = -1;
        const auto gap = demandAwareFittingGap(length);
        if (gap != freeByStart.end()) {
            start = gap->first;
            consumeAtStart(gap, length);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            // No existing span fits. Continue from the left edge of the free
            // tail, retaining its unused part as the new expandable tail.
            auto tail = tailGap();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands can arrive. Each pipe has length at most
            // 40 m, so it can require at most two 20 m sections: total digging
            // is at most 8,000,000 m, below the 100,000,000 m contest cap.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newLength;
            start = tailStart;
            const std::int64_t remainderStart = start + length;
            if (remainderStart < trenchLength) {
                addFreeGap(remainderStart, trenchLength);
            }
        }

        printPlacement(digs, start);
        pipes.push_back(Pipe{start, length, true});
        rememberDemand(length);
    }

    void remove(std::int64_t pid) {
        if (pid <= 0) {
            printInvalidPidFallback();
            return;
        }
        const std::uint64_t unsignedPid = static_cast<std::uint64_t>(pid);
        if (unsignedPid >= static_cast<std::uint64_t>(pipes.size())) {
            printInvalidPidFallback();
            return;
        }
        // The range check above makes this signed-to-unsigned index conversion safe.
        const std::size_t index = static_cast<std::size_t>(unsignedPid);
        if (!pipes[index].active) {
            printInvalidPidFallback();
            return;
        }

        const Pipe pipe = pipes[index];
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        addFreeGap(pipe.start, pipe.start + pipe.length);
    }

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    std::array<std::size_t, 41> demandCounts{};
    std::deque<int> recentDemands;

    void rememberDemand(int length) {
        if (recentDemands.size() == kDemandWindow) {
            --demandCounts[static_cast<std::size_t>(recentDemands.front())];
            recentDemands.pop_front();
        }
        recentDemands.push_back(length);
        ++demandCounts[static_cast<std::size_t>(length)];
    }

    std::size_t fittingDemandCount(std::int64_t residual) const {
        const std::size_t limit = static_cast<std::size_t>(std::min<std::int64_t>(40, residual));
        std::size_t count = 0;
        for (std::size_t length = 1; length <= limit; ++length) {
            count += demandCounts[length];
        }
        return count;
    }

    std::int64_t intervalCost(std::int64_t gapLength, int length) const {
        const std::int64_t residual = gapLength - length;
        const std::int64_t observations = static_cast<std::int64_t>(recentDemands.size());
        const std::int64_t fits = static_cast<std::int64_t>(fittingDemandCount(residual));
        // Favor a residual span only when recent pipe sizes indicate it is
        // likely to be reusable. The score is scaled by the window size, so
        // division and floating-point ties are unnecessary.
        return residual * observations - kDemandBonusMeters * fits;
    }

    void considerGap(std::pair<std::int64_t, std::int64_t> candidate,
                     int length,
                     std::pair<std::int64_t, std::int64_t>& best,
                     std::int64_t& bestCost) const {
        const std::int64_t cost = intervalCost(candidate.first, length);
        if (cost < bestCost || (cost == bestCost && candidate < best)) {
            best = candidate;
            bestCost = cost;
        }
    }

    StartIter demandAwareFittingGap(int length) {
        auto first = freeBySize.lower_bound({length, 0});
        if (first == freeBySize.end()) return freeByStart.end();

        auto best = *first;
        std::int64_t bestCost = intervalCost(best.first, length);
        if (recentDemands.empty()) return freeByStart.find(best.second);

        // Probe gaps whose residual can fit an empirical mode or quantile of
        // recent requests. The baseline best-fit candidate remains in the set.
        std::array<int, 5> residualTargets{};
        std::size_t targetCount = 0;
        std::size_t modeLength = 1;
        for (std::size_t size = 2; size <= 40; ++size) {
            if (demandCounts[size] > demandCounts[modeLength]) modeLength = size;
        }
        residualTargets[targetCount++] = static_cast<int>(modeLength);
        const std::array<std::size_t, 4> ranks{
            (recentDemands.size() + 3) / 4,
            (recentDemands.size() + 1) / 2,
            (3 * recentDemands.size() + 3) / 4,
            (9 * recentDemands.size() + 9) / 10,
        };
        for (std::size_t rank : ranks) {
            std::size_t cumulative = 0;
            std::size_t quantile = 1;
            for (; quantile <= 40; ++quantile) {
                cumulative += demandCounts[quantile];
                if (cumulative >= rank) break;
            }
            const int target = static_cast<int>(std::min<std::size_t>(40, quantile));
            if (std::find(residualTargets.begin(), residualTargets.begin() + static_cast<std::ptrdiff_t>(targetCount), target)
                == residualTargets.begin() + static_cast<std::ptrdiff_t>(targetCount)) {
                residualTargets[targetCount++] = target;
            }
        }

        for (std::size_t i = 0; i < targetCount; ++i) {
            const std::int64_t targetLength = static_cast<std::int64_t>(length) + residualTargets[i];
            auto candidate = freeBySize.lower_bound({targetLength, 0});
            if (candidate != freeBySize.end()) {
                considerGap(*candidate, length, best, bestCost);
            }
        }
        return freeByStart.find(best.second);
    }

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    void consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        eraseGap(it);
        if (start + length < end) {
            addFreeGap(start + length, end);
        }
    }

    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        freeBySize.erase({end - start, start});
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                start = previous->first;
                end = std::max(end, previous->second);
                eraseGap(previous);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            end = std::max(end, it->second);
            auto next = it++;
            eraseGap(next);
        }
        freeByStart.emplace(start, end);
        freeBySize.emplace(end - start, start);
    }

    static void printPlacement(std::int64_t digs, std::int64_t start) {
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }

    static void printInvalidPidFallback() {
        // Contest inputs guarantee an active PID. This keeps a malformed input
        // from causing an out-of-bounds access while preserving protocol shape.
        std::cout << 0 << '\n' << std::flush;
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) return 0;
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
    }
    return 0;
}
