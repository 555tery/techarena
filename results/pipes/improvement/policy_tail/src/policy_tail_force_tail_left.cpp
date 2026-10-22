#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <set>
#include <utility>
#include <vector>

namespace {

// Compile-time policy controls used only by this experiment copy.
#ifndef PIPE_SELECT_MODE
#define PIPE_SELECT_MODE 0  // 0=canonical adaptive, 1=plain best-fit, 2=address first-fit, 3=FF/BF hybrid
#endif
#ifndef PIPE_PRESERVE_TAIL
#define PIPE_PRESERVE_TAIL 0
#endif
#ifndef PIPE_HIGH_ADDRESS_TIE
#define PIPE_HIGH_ADDRESS_TIE 0
#endif
#ifndef PIPE_HYBRID_THRESHOLD
#define PIPE_HYBRID_THRESHOLD 5000
#endif
#ifndef PIPE_SIDE_MODE
#define PIPE_SIDE_MODE 0  // 0=T46, 1=left, 2=right, 3=right for lengths <= threshold, 4=near-size, 5=near-age, 6=address low-right, 7=address high-right, 8=T46 except selected tail stays left
#endif
#ifndef PIPE_SIDE_THRESHOLD
#define PIPE_SIDE_THRESHOLD 4
#endif

constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kHistoryWindow = 2048;
constexpr std::int64_t kUnfitPenaltyScale = 60;
constexpr int kRightEdgeMaxPipeLength = 4;
constexpr std::size_t kSameLengthRightRun = 46;

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
    std::map<std::int64_t, int> liveByStart;
    std::uint64_t addressTieOpportunityGroups = 0;
    std::uint64_t addressTieOpportunityExtras = 0;
    std::uint64_t selectedSameLengthTieGroups = 0;
    std::uint64_t tailOrdinarySelections = 0;
    std::uint64_t tailFallbackSelections = 0;
    std::uint64_t rightEdgePlacements = 0;

    void place(int length) {
        std::int64_t start = -1;
        const auto gap = bestFittingGap(length);
        if (gap != freeByStart.end()) {
            if (gap->second == trenchLength) ++tailOrdinarySelections;
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
            ++tailFallbackSelections;
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
        liveByStart[start] = static_cast<int>(pipes.size());
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
        liveByStart.erase(pipe.start);
        addFreeGap(pipe.start, pipe.start + pipe.length);
    }

    void printDiagnostics() const {
        std::cerr << "policy_trace placements=" << (pipes.size() - 1)
                  << " same_length_tie_groups=" << addressTieOpportunityGroups
                  << " same_length_tie_extra_choices=" << addressTieOpportunityExtras
                  << " selected_from_duplicate_size_group=" << selectedSameLengthTieGroups
                  << " tail_ordinary=" << tailOrdinarySelections
                  << " tail_fallback=" << tailFallbackSelections
                  << " right_edge=" << rightEdgePlacements << '\n';
    }

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length) {
        constexpr int kMode = PIPE_SELECT_MODE;
        const bool useFirstFit = kMode == 2 || (kMode == 3 && trenchLength < PIPE_HYBRID_THRESHOLD);
        const bool useAdaptive = kMode == 0 || (kMode == 3 && !useFirstFit);
        if (useFirstFit) {
            for (auto gap = freeByStart.begin(); gap != freeByStart.end(); ++gap) {
                if (gap->second - gap->first < length) continue;
                if (PIPE_PRESERVE_TAIL && gap->second == trenchLength) continue;
                return gap;
            }
            return freeByStart.end();
        }

        auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        std::int64_t bestGapLength = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        while (it != freeBySize.end()) {
            const std::int64_t gapLength = it->first;
            std::uint64_t eligibleInGroup = 0;
            auto groupEnd = freeBySize.upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
            for (auto candidate = it; candidate != groupEnd; ++candidate) {
                const std::int64_t slack = gapLength - length;
                const std::int64_t candidateStart = candidate->second;
                const auto mapGap = freeByStart.find(candidateStart);
                if (mapGap == freeByStart.end()) continue;
                if (PIPE_PRESERVE_TAIL && mapGap->second == trenchLength) continue;
                ++eligibleInGroup;

                std::int64_t score = slack;
                if (useAdaptive) {
                    score *= historySize;
                    if (slack > 0 && slack <= 40) {
                        int misses = 0;
                        for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                            misses += recentFrequency[static_cast<std::size_t>(request)];
                        }
                        score += kUnfitPenaltyScale * misses;
                    }
                }

                const bool scoreBetter = score < bestScore;
                const bool scoreTieBetterSize = score == bestScore && gapLength < bestGapLength;
                const bool sameSizeTie = score == bestScore && gapLength == bestGapLength && best != freeByStart.end();
                const bool addressTieBetter = sameSizeTie && (PIPE_HIGH_ADDRESS_TIE
                    ? candidateStart > best->first : candidateStart < best->first);
                if (scoreBetter || scoreTieBetterSize || addressTieBetter) {
                    bestScore = score;
                    bestGapLength = gapLength;
                    best = mapGap;
                }
            }
            if (eligibleInGroup > 1) {
                ++addressTieOpportunityGroups;
                addressTieOpportunityExtras += eligibleInGroup - 1;
                if (bestGapLength == gapLength && best != freeByStart.end()) {
                    ++selectedSameLengthTieGroups;
                }
            }
            if (gapLength - length > 40) break;
            it = groupEnd;
        }
        return best;
    }

    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t seen = 0; seen < kSameLengthRightRun; ++seen, ++it) {
            if (*it != length) return false;
        }
        return true;
    }

    std::int64_t consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        bool placeRight = false;
        if (PIPE_SIDE_MODE == 0) {
            placeRight = length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length);
        } else if (PIPE_SIDE_MODE == 2) {
            placeRight = true;
        } else if (PIPE_SIDE_MODE == 3) {
            placeRight = length <= PIPE_SIDE_THRESHOLD;
        } else if (PIPE_SIDE_MODE == 4 || PIPE_SIDE_MODE == 5) {
            placeRight = chooseNeighborEdge(start, end, length, PIPE_SIDE_MODE == 4);
        } else if (PIPE_SIDE_MODE == 6) {
            placeRight = start < trenchLength / 2;
        } else if (PIPE_SIDE_MODE == 7) {
            placeRight = start >= trenchLength / 2;
        } else if (PIPE_SIDE_MODE == 8) {
            placeRight = end != trenchLength
                && (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length));
        }
        if (placeRight) ++rightEdgePlacements;
        const std::int64_t placementStart = placeRight ? end - static_cast<std::int64_t>(length) : start;
        eraseGap(it);
        if (start < placementStart) addFreeGap(start, placementStart);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end);
        return placementStart;
    }

    bool chooseNeighborEdge(std::int64_t gapStart, std::int64_t gapEnd, int length,
                            bool compareLength) const {
        bool hasLeft = false, hasRight = false;
        int leftPid = 0, rightPid = 0;
        int leftLength = 0, rightLength = 0;
        auto rightIt = liveByStart.lower_bound(gapStart);
        if (rightIt != liveByStart.begin()) {
            auto leftIt = std::prev(rightIt);
            const Pipe& pipe = pipes[static_cast<std::size_t>(leftIt->second)];
            if (pipe.start + pipe.length == gapStart) {
                hasLeft = true;
                leftPid = leftIt->second;
                leftLength = pipe.length;
            }
        }
        rightIt = liveByStart.lower_bound(gapEnd);
        if (rightIt != liveByStart.end() && rightIt->first == gapEnd) {
            hasRight = true;
            rightPid = rightIt->second;
            rightLength = pipes[static_cast<std::size_t>(rightPid)].length;
        }
        if (!hasLeft && hasRight) return true;
        if (hasLeft && !hasRight) return false;
        if (!hasLeft && !hasRight) return false;
        const int leftScore = compareLength ? std::abs(length - leftLength)
                                            : static_cast<int>(pipes.size()) - leftPid;
        const int rightScore = compareLength ? std::abs(length - rightLength)
                                             : static_cast<int>(pipes.size()) - rightPid;
        return rightScore < leftScore;
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
        if (command == 0) {
            allocator.printDiagnostics();
            return 0;
        }
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
    }
    return 0;
}
