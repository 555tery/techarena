#include <algorithm>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <set>
#include <utility>
#include <vector>

// Tie-breaking experiment for best-fit allocation.
//   PIPE_AGE_POLICY=0: choose the oldest fitting minimum-size interior gap.
//   PIPE_AGE_POLICY=1: choose the newest fitting minimum-size interior gap.
#ifndef PIPE_AGE_POLICY
#define PIPE_AGE_POLICY 0
#endif

#if PIPE_AGE_POLICY < 0 || PIPE_AGE_POLICY > 1
#error "Unsupported PIPE_AGE_POLICY"
#endif

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::int64_t kMaxTrenchLength = 100'000'000;

struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
};

struct Gap {
    std::int64_t end = 0;
    std::uint64_t age = 0;
};

class Allocator {
public:
    // Free gaps are indexed by start for coalescing, and by length then age
    // for best-fit selection. Ages are unique monotonically increasing stamps.
    std::map<std::int64_t, Gap> freeByStart;
    std::map<std::int64_t, std::set<std::pair<std::uint64_t, std::int64_t>>>
        freeByLengthAge;
    std::vector<Pipe> pipes{Pipe{}};
    std::int64_t trenchLength = 0;
    std::uint64_t nextAge = 1;

    void place(int length) {
        std::int64_t start = -1;
        auto chosen = chooseInterior(length);
        if (chosen != freeByStart.end()) {
            start = chosen->first;
            consumeAtStart(chosen, length);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            // No fitting interior gap: use the existing tail first and extend
            // it by the minimum number of 20 m sections if necessary.
            auto tail = tailGap();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;
            const std::int64_t newLength = trenchLength + digs * kDigLength;

            // The official operation bound makes this cap unreachable, but
            // retain a guard rather than emitting an out-of-range dig request.
            if (newLength > kMaxTrenchLength) {
                printPlacement(0, 0);
                pipes.push_back(Pipe{0, length, false});
                return;
            }

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
        if (pid > 0 && pid < static_cast<std::int64_t>(pipes.size()) && pipes[pid].active) {
            const Pipe pipe = pipes[pid];
            std::cout << pipe.start << '\n' << std::flush;
            pipes[pid].active = false;
            addFreeGap(pipe.start, pipe.start + pipe.length);
            return;
        }
        // The statement guarantees a valid, active PID.
        std::cout << 0 << '\n' << std::flush;
    }

private:
    using StartIter = std::map<std::int64_t, Gap>::iterator;
    using AgeSet = std::set<std::pair<std::uint64_t, std::int64_t>>;

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second.end == trenchLength ? it : freeByStart.end();
    }

    StartIter chooseInterior(int length) {
        auto tail = tailGap();
        const std::int64_t tailStart = tail == freeByStart.end() ? -1 : tail->first;

        // Iterate by increasing gap length. The tail is the only gap that may
        // need skipping, so at most one size group is empty after that skip.
        for (auto sizeIt = freeByLengthAge.lower_bound(length);
             sizeIt != freeByLengthAge.end(); ++sizeIt) {
            const AgeSet& ties = sizeIt->second;
#if PIPE_AGE_POLICY == 0
            auto ageIt = ties.begin();
            if (ageIt != ties.end() && ageIt->second == tailStart) ++ageIt;
            if (ageIt != ties.end()) return freeByStart.find(ageIt->second);
#else
            auto ageIt = ties.rbegin();
            if (ageIt != ties.rend() && ageIt->second == tailStart) ++ageIt;
            if (ageIt != ties.rend()) return freeByStart.find(ageIt->second);
#endif
        }
        return freeByStart.end();
    }

    void consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second.end;
        eraseGap(it);
        if (start + length < end) {
            // A split creates a new gap with a fresh age stamp.
            addFreeGap(start + length, end);
        }
    }

    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second.end;
        const std::uint64_t age = it->second.age;
        auto sizeIt = freeByLengthAge.find(end - start);
        sizeIt->second.erase({age, start});
        if (sizeIt->second.empty()) freeByLengthAge.erase(sizeIt);
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second.end >= start) {
                start = previous->first;
                end = std::max(end, previous->second.end);
                eraseGap(previous);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            end = std::max(end, it->second.end);
            auto next = it++;
            eraseGap(next);
        }

        // A deletion/merge or a split remainder is one newly formed gap and
        // receives exactly one fresh stamp after coalescing is complete.
        const std::uint64_t age = nextAge++;
        freeByStart.emplace(start, Gap{end, age});
        freeByLengthAge[end - start].insert({age, start});
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
