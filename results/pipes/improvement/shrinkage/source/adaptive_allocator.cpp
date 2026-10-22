#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <set>
#include <utility>
#include <vector>

// STRATEGY 0 is a control build of policy 4 (best-fit across all gaps, left edge).
// STRATEGY 1 uses the right edge of the chosen best-fit gap.
// STRATEGY 2 scores the leftover using recent-arrival feasibility:
//   score = slack * history_size + scale * count(previous lengths > slack).
// STRATEGY 3 prefers leftovers whose exact size has appeared recently:
//   score = slack * history_size - scale * count(previous lengths == slack).
// All adaptive statistics are based only on previous insertion commands.
// STRATEGY 4 shrinks the S50 miss penalty for short histories; STRATEGY 5
// gates S50 behind a P4 warm-up; STRATEGY 6 uses exponentially discounted history.
#ifndef PIPES_STRATEGY
#define PIPES_STRATEGY 0
#endif
#ifndef PIPES_HISTORY_WINDOW
#define PIPES_HISTORY_WINDOW 128
#endif
#ifndef PIPES_PENALTY_SCALE
#define PIPES_PENALTY_SCALE 20
#endif
#ifndef PIPES_SHRINK_TAU
#define PIPES_SHRINK_TAU 32
#endif
#ifndef PIPES_WARMUP_THRESHOLD
#define PIPES_WARMUP_THRESHOLD 32
#endif
#ifndef PIPES_DECAY_LAMBDA
#define PIPES_DECAY_LAMBDA 0.9785720620877001
#endif

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
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};
    std::array<double, 41> decayFrequency{};
    double decayTotal = 0.0;

    void place(int length) {
        std::int64_t start = -1;
        const auto gap = bestFittingGap(length);
        if (gap != freeByStart.end()) {
            start = consumeAtStart(gap, length);
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
        recordLength(length);
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
#if PIPES_STRATEGY == 5
        if (recentLengths.size() < PIPES_WARMUP_THRESHOLD) {
            auto it = freeBySize.lower_bound({length, 0});
            return it == freeBySize.end() ? freeByStart.end() : freeByStart.find(it->second);
        }
#endif
#if PIPES_STRATEGY == 2 || PIPES_STRATEGY == 3 || PIPES_STRATEGY == 4 || PIPES_STRATEGY == 5
        if (recentLengths.empty()) {
            auto it = freeBySize.lower_bound({length, 0});
            return it == freeBySize.end() ? freeByStart.end() : freeByStart.find(it->second);
        }
        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
#if PIPES_STRATEGY == 4
        const std::int64_t effectiveSize = historySize + PIPES_SHRINK_TAU;
#endif
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        auto it = freeBySize.lower_bound({length, 0});
        while (it != freeBySize.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
#if PIPES_STRATEGY == 4
            std::int64_t score = slack * effectiveSize;
#else
            std::int64_t score = slack * historySize;
#endif
            if (slack > 0 && slack <= 40) {
#if PIPES_STRATEGY == 3
                score -= PIPES_PENALTY_SCALE * recentFrequency[static_cast<int>(slack)];
#else
                std::int64_t misses = 0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                    misses += recentFrequency[request];
#if PIPES_STRATEGY == 4
                score += PIPES_PENALTY_SCALE * misses;
#else
                score += PIPES_PENALTY_SCALE * misses;
#endif
#endif
            }
            if (score < bestScore) {
                bestScore = score;
                best = freeByStart.find(it->second); // first address in this size class
            }
            if (slack > 40) break; // later gaps have the same zero penalty and larger slack
            const std::int64_t currentSize = it->first;
            it = freeBySize.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
        }
        return best;
#elif PIPES_STRATEGY == 6
        if (decayTotal <= 0.0) {
            auto it = freeBySize.lower_bound({length, 0});
            return it == freeBySize.end() ? freeByStart.end() : freeByStart.find(it->second);
        }
        double bestScore = std::numeric_limits<double>::infinity();
        StartIter best = freeByStart.end();
        auto it = freeBySize.lower_bound({length, 0});
        while (it != freeBySize.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            double score = static_cast<double>(slack) * decayTotal;
            if (slack > 0 && slack <= 40) {
                double misses = 0.0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                    misses += decayFrequency[request];
                score += static_cast<double>(PIPES_PENALTY_SCALE) * misses;
            }
            if (score < bestScore) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = freeBySize.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
        }
        return best;
#else
        auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        return freeByStart.find(it->second);
#endif
    }

    std::int64_t consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        eraseGap(it);
#if PIPES_STRATEGY == 1
        const std::int64_t placed = end - length;
        if (start < placed) addFreeGap(start, placed);
#else
        const std::int64_t placed = start;
        if (start + length < end) addFreeGap(start + length, end);
#endif
        return placed;
    }

    void recordLength(int length) {
#if PIPES_STRATEGY == 6
        for (double& frequency : decayFrequency) frequency *= PIPES_DECAY_LAMBDA;
        decayTotal *= PIPES_DECAY_LAMBDA;
        decayFrequency[length] += 1.0;
        decayTotal += 1.0;
#else
        recentLengths.push_back(length);
        ++recentFrequency[length];
        if (recentLengths.size() > PIPES_HISTORY_WINDOW) {
            --recentFrequency[recentLengths.front()];
            recentLengths.pop_front();
        }
#endif
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
