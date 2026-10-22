#include <algorithm>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <set>
#include <utility>
#include <vector>

// Local strategy selector. The default is the score-conscious best-fit policy:
// consume the smallest interior free interval that fits, and preserve the
// expandable trench tail until no interior interval can hold the new pipe.
//   0: best-fit interior interval (default)
//   1: first-fit interior interval by coordinate
//   2: worst-fit interior interval
//   3: largest-coordinate fitting interior interval
//   4: best-fit among all intervals, including the tail (benchmark only)
#ifndef PIPE_POLICY
#define PIPE_POLICY 0
#endif

#if PIPE_POLICY < 0 || PIPE_POLICY > 4
#error "Unsupported PIPE_POLICY"
#endif

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::int64_t kMaxTrenchLength = 100'000'000;

struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
};

class Allocator {
public:
    // Free intervals are half-open [start, end). Each interval is represented
    // in both indexes: by start for coalescing, and by (length, start) for
    // best/worst-fit selection. Pipe lengths are at most 40, but free spans can
    // be much larger, so the size index is not a fixed-size array.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::set<std::int64_t> freeStartsByClass[41];
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;

    void place(int length) {
        std::int64_t start = -1;
        const auto chosen = chooseInterior(length);
        if (chosen != freeByStart.end()) {
            start = chosen->first;
            consumeAtStart(chosen, length);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            // No interior hole fits. Extend the existing free tail if present,
            // then place at its left edge so the remainder stays expandable.
            auto tail = tailInterval();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t oldTailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - oldTailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;
            const std::int64_t newLength = trenchLength + digs * kDigLength;

            // This is unreachable for the official operation bound, but keeping
            // the cap check prevents accidentally emitting an invalid command.
            if (newLength > kMaxTrenchLength) {
                digs = 0;
                start = 0;
                printPlacement(0, 0);
                pipes.push_back(Pipe{0, length, false});
                return;
            }

            if (tail != freeByStart.end()) {
                eraseInterval(tail);
            }
            trenchLength = newLength;
            start = tailStart;
            const std::int64_t remainderStart = start + length;
            if (remainderStart < trenchLength) {
                addFreeInterval(remainderStart, trenchLength);
            }
        }

        printPlacement(digs, start);
        pipes.push_back(Pipe{start, length, true});
    }

    void remove(std::int64_t pid) {
        if (pid > 0 && pid < static_cast<std::int64_t>(pipes.size()) && pipes[pid].active) {
            const Pipe p = pipes[pid];
            std::cout << p.start << '\n' << std::flush;
            pipes[pid].active = false;
            addFreeInterval(p.start, p.start + p.length);
            return;
        }
        // Inputs are guaranteed valid. Keep the protocol well-formed if that
        // guarantee is violated, while avoiding an out-of-bounds access.
        std::cout << 0 << '\n' << std::flush;
    }

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    StartIter tailInterval() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter chooseInterior(int length) {
#if PIPE_POLICY == 0 || PIPE_POLICY == 4
        auto it = freeBySize.lower_bound({length, std::numeric_limits<std::int64_t>::min()});
        if (it == freeBySize.end()) return freeByStart.end();
        auto candidate = freeByStart.find(it->second);
#if PIPE_POLICY == 0
        if (isTail(candidate)) {
            ++it;  // There can be only one tail interval.
            if (it == freeBySize.end()) return freeByStart.end();
            candidate = freeByStart.find(it->second);
        }
#endif
        return candidate;
#elif PIPE_POLICY == 1
        // Scanning at most 40 size classes is cheap and avoids an O(number of
        // intervals) coordinate scan. Class 40 means any span of >= 40 m.
        std::int64_t bestStart = std::numeric_limits<std::int64_t>::max();
        auto tail = tailInterval();
        const std::int64_t tailStart = tail == freeByStart.end()
            ? -1 : tail->first;
        for (int sizeClass = length; sizeClass <= 40; ++sizeClass) {
            const auto& starts = freeStartsByClass[sizeClass];
            auto it = starts.begin();
            if (it != starts.end() && *it == tailStart) ++it;
            if (it != starts.end()) bestStart = std::min(bestStart, *it);
        }
        return bestStart == std::numeric_limits<std::int64_t>::max()
            ? freeByStart.end() : freeByStart.find(bestStart);
#elif PIPE_POLICY == 2
        if (freeBySize.empty()) return freeByStart.end();
        auto it = freeBySize.rbegin();
        if (it->first < length) return freeByStart.end();
        auto candidate = freeByStart.find(it->second);
        if (isTail(candidate)) {
            ++it;
            if (it == freeBySize.rend() || it->first < length) return freeByStart.end();
            candidate = freeByStart.find(it->second);
        }
        return candidate;
#elif PIPE_POLICY == 3
        std::int64_t bestStart = -1;
        auto tail = tailInterval();
        const std::int64_t tailStart = tail == freeByStart.end()
            ? -1 : tail->first;
        for (int sizeClass = length; sizeClass <= 40; ++sizeClass) {
            const auto& starts = freeStartsByClass[sizeClass];
            auto it = starts.rbegin();
            if (it != starts.rend() && *it == tailStart) ++it;
            if (it != starts.rend()) bestStart = std::max(bestStart, *it);
        }
        return bestStart < 0 ? freeByStart.end() : freeByStart.find(bestStart);
#endif
    }

    bool isTail(StartIter it) const {
        return it != freeByStart.end() && it->second == trenchLength;
    }

    void consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        eraseInterval(it);
        if (start + length < end) {
            addFreeInterval(start + length, end);
        }
    }

    void eraseInterval(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        freeBySize.erase({end - start, start});
        freeStartsByClass[sizeClass(end - start)].erase(start);
        freeByStart.erase(it);
    }

    void addFreeInterval(std::int64_t start, std::int64_t end) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto prev = std::prev(it);
            if (prev->second >= start) {
                start = prev->first;
                end = std::max(end, prev->second);
                eraseInterval(prev);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            end = std::max(end, it->second);
            auto next = it++;
            eraseInterval(next);
        }
        freeByStart.emplace(start, end);
        freeBySize.emplace(end - start, start);
        freeStartsByClass[sizeClass(end - start)].insert(start);
    }

    static int sizeClass(std::int64_t length) {
        return static_cast<int>(std::min<std::int64_t>(length, 40));
    }

    static void printPlacement(std::int64_t digs, std::int64_t start) {
        std::cout << digs << ' ' << start << '\n' << std::flush;
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
