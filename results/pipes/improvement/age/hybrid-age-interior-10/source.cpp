#include <algorithm>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

// Policy 0 is final policy4. Policy 1 applies the newest-age choice to
// interior gaps for short incoming pipes; policy 2 applies newest-age as the
// equal-size tie-break among all gaps, including the tail, for short pipes.
constexpr int kAgeMode = 1;
constexpr int kAgeLengthThreshold = 10;
constexpr std::int64_t kDigLength = 20;

namespace {

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
    using StartMap = std::map<std::int64_t, Gap>;
    using StartIter = StartMap::iterator;
    using AgeSet = std::set<std::pair<std::uint64_t, std::int64_t>>;

    StartMap freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::map<std::int64_t, AgeSet> freeByLengthAge;
    std::vector<Pipe> pipes{Pipe{}};
    std::int64_t trenchLength = 0;
    std::uint64_t nextAge = 1;

    void place(int length) {
        StartIter chosen = freeByStart.end();
        if (length <= kAgeLengthThreshold && kAgeMode == 1) {
            chosen = newestFittingGap(length, false);
        } else if (length <= kAgeLengthThreshold && kAgeMode == 2) {
            chosen = newestFittingGap(length, true);
        } else {
            chosen = bestFittingGap(length);
        }

        std::int64_t start = -1;
        if (chosen != freeByStart.end()) {
            start = chosen->first;
            consumeAtStart(chosen, length);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            auto tail = tailGap();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands and L <= 40 imply no more than
            // 8,000,000 m of added trench, below the 100,000,000 m limit.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newLength;
            start = tailStart;
            const std::int64_t remainderStart = start + length;
            if (remainderStart < trenchLength) {
                addFreeGap(remainderStart, trenchLength);
            }
        }

        std::cout << digs << ' ' << start << '\n' << std::flush;
        pipes.push_back(Pipe{start, length, true});
    }

    void remove(std::int64_t pid) {
        if (pid <= 0 || static_cast<std::uint64_t>(pid) >= pipes.size()) {
            printInvalidPidFallback();
            return;
        }
        const auto index = static_cast<std::size_t>(pid);
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
    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second.end == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length) {
        const auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        return freeByStart.find(it->second);
    }

    StartIter newestFittingGap(int length, bool includeTail) {
        auto tail = tailGap();
        const std::int64_t tailStart = tail == freeByStart.end() ? -1 : tail->first;
        for (auto sizeIt = freeByLengthAge.lower_bound(length);
             sizeIt != freeByLengthAge.end(); ++sizeIt) {
            auto ageIt = sizeIt->second.rbegin();
            if (!includeTail && ageIt != sizeIt->second.rend() &&
                ageIt->second == tailStart) {
                ++ageIt;
            }
            if (ageIt != sizeIt->second.rend()) {
                return freeByStart.find(ageIt->second);
            }
        }
        return freeByStart.end();
    }

    void consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second.end;
        eraseGap(it);
        if (start + length < end) addFreeGap(start + length, end);
    }

    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second.end;
        const std::uint64_t age = it->second.age;
        freeBySize.erase({end - start, start});
        auto ageIt = freeByLengthAge.find(end - start);
        ageIt->second.erase({age, start});
        if (ageIt->second.empty()) freeByLengthAge.erase(ageIt);
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

        const std::uint64_t age = nextAge++;
        const std::int64_t length = end - start;
        freeByStart.emplace(start, Gap{end, age});
        freeBySize.emplace(length, start);
        freeByLengthAge[length].insert({age, start});
    }

    static void printInvalidPidFallback() {
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
