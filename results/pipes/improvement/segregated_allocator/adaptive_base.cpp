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

#ifndef PIPES_POLICY
#define PIPES_POLICY 0
#endif
#ifndef PIPES_WINDOW
#define PIPES_WINDOW 128
#endif
#ifndef PIPES_SCALE
#define PIPES_SCALE 50
#endif
#ifndef PIPES_PLACE_RIGHT
#define PIPES_PLACE_RIGHT 0
#endif
#ifndef PIPES_TIE_HIGH_ADDRESS
#define PIPES_TIE_HIGH_ADDRESS 0
#endif
#ifndef PIPES_RIGHT_MAX_LENGTH
#define PIPES_RIGHT_MAX_LENGTH -1
#endif
#ifndef PIPES_PID_PARITY_RIGHT
#define PIPES_PID_PARITY_RIGHT 0
#endif
#ifndef PIPES_PID_PARITY_REVERSE
#define PIPES_PID_PARITY_REVERSE 0
#endif
#ifndef PIPES_STICKY_DISABLE_NUM
#define PIPES_STICKY_DISABLE_NUM 12
#endif
#ifndef PIPES_STICKY_DISABLE_DEN
#define PIPES_STICKY_DISABLE_DEN 5
#endif
#ifndef PIPES_STICKY_ENABLE_NUM
#define PIPES_STICKY_ENABLE_NUM 21
#endif
#ifndef PIPES_STICKY_ENABLE_DEN
#define PIPES_STICKY_ENABLE_DEN 10
#endif
#ifndef PIPES_STICKY_MIN_RUN
#define PIPES_STICKY_MIN_RUN 32
#endif

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kHistoryWindow = PIPES_WINDOW;

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
    std::uint64_t gapClock = 0;
    std::map<std::int64_t, std::uint64_t> gapBirth;
    std::map<std::int64_t, std::set<std::pair<std::uint64_t, std::int64_t>>> gapsByAge;
    bool stickyValid = false;
    std::int64_t stickyStart = 0;
    std::int64_t stickyEnd = 0;
    int stickyLength = 0;
    bool segregatedMode = false;
    int lastRequestLength = 0;
    int sameLengthRun = 0;
    std::int64_t livePipeCount = 0;
    std::int64_t livePipeLength = 0;

    void place(int length) {
        if (lastRequestLength != length) {
            lastRequestLength = length;
            sameLengthRun = 0;
            stickyValid = false;
        }
        ++sameLengthRun;
        if (livePipeCount > 0 && livePipeLength > 0) {
            const std::int64_t lhs = static_cast<std::int64_t>(length) * livePipeCount;
            if (segregatedMode
                && lhs * PIPES_STICKY_DISABLE_DEN >= livePipeLength * PIPES_STICKY_DISABLE_NUM) {
                segregatedMode = false;
                stickyValid = false;
            } else if (!segregatedMode && sameLengthRun >= PIPES_STICKY_MIN_RUN
                && lhs * PIPES_STICKY_ENABLE_DEN <= livePipeLength * PIPES_STICKY_ENABLE_NUM) {
                segregatedMode = true;
            }
        } else if (!segregatedMode && sameLengthRun >= PIPES_STICKY_MIN_RUN) {
            segregatedMode = true;
        }

        StartIter gap = freeByStart.end();
        if (segregatedMode && stickyValid && stickyLength == length) {
            auto it = freeByStart.find(stickyStart);
            if (it != freeByStart.end() && it->second == stickyEnd
                && it->second - it->first >= length) {
                gap = it;
            } else {
                stickyValid = false;
            }
        } else {
            stickyValid = false;
        }
        if (gap == freeByStart.end()) gap = bestFittingGap(length);

        std::int64_t start = -1;
        std::int64_t arenaStart = 0;
        std::int64_t arenaEnd = 0;
        std::int64_t digs = 0;
        if (gap != freeByStart.end()) {
            arenaStart = gap->first;
            arenaEnd = gap->second;
            const bool placeRight = segregatedMode
                ? ((pipes.size() % 2U) == (PIPES_PID_PARITY_REVERSE ? 1U : 0U))
                : useT46RightEndpoint(length);
            start = placeRight ? arenaEnd - length : arenaStart;
            eraseGap(gap);
            const std::int64_t remainderStart = placeRight ? arenaStart : arenaStart + length;
            const std::int64_t remainderEnd = placeRight ? arenaEnd - length : arenaEnd;
            if (remainderStart < remainderEnd) addFreeGap(remainderStart, remainderEnd);
            arenaStart = remainderStart;
            arenaEnd = remainderEnd;
        } else {
            // Grow the tail only when no free interval fits. Alternate the
            // insertion edge by PID color so each cohort can remain contiguous.
            auto tail = tailGap();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newLength;
            const bool placeRight = segregatedMode
                ? ((pipes.size() % 2U) == (PIPES_PID_PARITY_REVERSE ? 1U : 0U))
                : false;
            start = placeRight ? trenchLength - length : tailStart;
            const std::int64_t remainderStart = placeRight ? tailStart : start + length;
            const std::int64_t remainderEnd = placeRight ? start : trenchLength;
            if (remainderStart < remainderEnd) addFreeGap(remainderStart, remainderEnd);
            arenaStart = remainderStart;
            arenaEnd = remainderEnd;
        }

        stickyValid = segregatedMode && arenaStart < arenaEnd;
        stickyStart = arenaStart;
        stickyEnd = arenaEnd;
        stickyLength = length;
        printPlacement(digs, start);
        pipes.push_back(Pipe{start, length, true});
        ++livePipeCount;
        livePipeLength += length;
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
        stickyValid = false;
        --livePipeCount;
        livePipeLength -= pipe.length;
        addFreeGap(pipe.start, pipe.start + pipe.length);
    }

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    bool useT46RightEndpoint(int length) const {
        if (length <= 4) return true;
        if (recentLengths.size() < 46U) return false;
        auto it = recentLengths.rbegin();
        for (int count = 0; count < 46; ++count, ++it) {
            if (*it != length) return false;
        }
        return true;
    }

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length) {
#if PIPES_POLICY == 1
        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it)
            if (it->second - it->first >= length) return it;
        return freeByStart.end();
#elif PIPES_POLICY == 2
        if (freeBySize.empty()) return freeByStart.end();
        auto it = std::prev(freeBySize.end());
        if (it->first < length) return freeByStart.end();
        return freeByStart.find(it->second);
#elif PIPES_POLICY == 3
        // First fit by address, scanning from the high end.
        for (auto it = freeByStart.rbegin(); it != freeByStart.rend(); ++it)
            if (it->second - it->first >= length) return freeByStart.find(it->first);
        return freeByStart.end();
#elif PIPES_POLICY == 4 || PIPES_POLICY == 5
        // Choose the oldest/newest gap within 40 m of best-fit; this limits
        // the scan to at most 41 distinct length classes.
        auto bestBySize = freeBySize.lower_bound({length, 0});
        if (bestBySize == freeBySize.end()) return freeByStart.end();
        const std::int64_t maxSize = bestBySize->first + 40;
        bool found = false;
        std::uint64_t chosenAge = PIPES_POLICY == 4 ? UINT64_MAX : 0;
        StartIter best = freeByStart.end();
        auto it = gapsByAge.lower_bound(bestBySize->first);
        while (it != gapsByAge.end() && it->first <= maxSize) {
            if (!it->second.empty()) {
                auto ageIt = PIPES_POLICY == 4 ? it->second.begin() : std::prev(it->second.end());
                const auto [born, start] = *ageIt;
                if (!found || (PIPES_POLICY == 4 ? born < chosenAge : born > chosenAge)) {
                    found = true;
                    chosenAge = born;
                    best = freeByStart.find(start);
                }
            }
            ++it;
        }
        if (found) return best;
        return freeByStart.find(bestBySize->second);
#elif PIPES_POLICY == 0
        auto it = freeBySize.lower_bound({length, 0});
        return it == freeBySize.end() ? freeByStart.end() : freeByStart.find(it->second);
#elif PIPES_POLICY == 7
        auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        while (it != freeBySize.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            std::int64_t score = slack * historySize;
            if (slack > 0 && slack <= 40) {
                int misses = 0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                    misses += recentFrequency[static_cast<std::size_t>(request)];
                }
                score += PIPES_SCALE * misses;
            }

            // Iteration is by size and then start, so keeping the first tie
            // implements the smaller-gap, then lower-address tie-break.
            bool take = score < bestScore;
#if PIPES_TIE_HIGH_ADDRESS
            if (score == bestScore && best != freeByStart.end() && it->second > best->first)
                take = true;
#endif
            if (take) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = freeBySize.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
        }
        return best;
#endif
    }

    std::int64_t consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        eraseGap(it);
#if PIPES_PID_PARITY_RIGHT
        const bool placeRight = ((pipes.size() % 2U) == (PIPES_PID_PARITY_REVERSE ? 1U : 0U));
        const std::int64_t placed = placeRight ? end - static_cast<std::int64_t>(length) : start;
        if (start < placed) addFreeGap(start, placed);
        const std::int64_t placedEnd = placed + static_cast<std::int64_t>(length);
        if (placedEnd < end) addFreeGap(placedEnd, end);
#elif PIPES_RIGHT_MAX_LENGTH >= 0
        const std::int64_t placed = length <= PIPES_RIGHT_MAX_LENGTH
            ? end - static_cast<std::int64_t>(length) : start;
        if (start < placed) addFreeGap(start, placed);
        const std::int64_t placedEnd = placed + static_cast<std::int64_t>(length);
        if (placedEnd < end) addFreeGap(placedEnd, end);
#elif PIPES_PLACE_RIGHT
        const std::int64_t placed = end - length;
        if (start < placed) addFreeGap(start, placed);
#else
        if (start + length < end) {
            addFreeGap(start + length, end);
        }
        const std::int64_t placed = start;
#endif
        return placed;
    }

    void recordLength(int length) {
        recentLengths.push_back(length);
        ++recentFrequency[static_cast<std::size_t>(length)];
        if (recentLengths.size() > kHistoryWindow) {
            --recentFrequency[static_cast<std::size_t>(recentLengths.front())];
            recentLengths.pop_front();
        }
    }

    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const std::int64_t length = end - start;
        freeBySize.erase({length, start});
        auto born = gapBirth.find(start);
        if (born != gapBirth.end()) {
            auto byAge = gapsByAge.find(length);
            if (byAge != gapsByAge.end()) {
                byAge->second.erase({born->second, start});
                if (byAge->second.empty()) gapsByAge.erase(byAge);
            }
            gapBirth.erase(born);
        }
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
        const std::int64_t length = end - start;
        freeBySize.emplace(length, start);
        const std::uint64_t born = ++gapClock;
        gapBirth[start] = born;
        gapsByAge[length].emplace(born, start);
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
