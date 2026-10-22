#include <algorithm>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kDigLength = 20;

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
        const auto gap = bestFittingGap(length);
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

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length) {
        // Coordinates are nonnegative, so zero selects the lowest-address tie.
        auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        return freeByStart.find(it->second);
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
