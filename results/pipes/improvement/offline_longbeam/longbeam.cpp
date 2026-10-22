#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_set>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kHistoryWindow = 2048;
constexpr std::int64_t kUnfitPenaltyScale = 60;
constexpr int kRightEdgeMaxPipeLength = 4;
constexpr std::size_t kSameLengthRightRun = 46;
constexpr std::size_t kMcHistory = 256;
constexpr std::size_t kMcDepth = 4;
[[maybe_unused]] constexpr std::size_t kMcTrials = 12;
[[maybe_unused]] constexpr std::size_t kMcDecisionBudget = 32;
[[maybe_unused]] constexpr std::size_t kMcMaxGaps = 64;
[[maybe_unused]] constexpr std::size_t kMcMaxActivePipes = 4096;
[[maybe_unused]] constexpr std::int64_t kMcMinimumMeanSavingM = 1;

struct Observation {
    // kind=1 is a placement and value is its length; kind=-1 is a removal and
    // value is the removed pipe's rank from newest, scaled to [0, 1000].
    int kind = 0;
    int value = 0;
};

struct SimPipe {
    int pid = 0;
    std::int64_t start = 0;
    int length = 0;
    int sizeCohort = 0;
};

struct SimGap {
    std::int64_t end = 0;
    int cohort = -1;
};

struct GapCandidate {
    std::int64_t start = 0;
    std::int64_t score = 0;
};

// A bounded clone of the current allocator state. It intentionally forecasts
// only four actions and uses the existing cohort-owner policy for all simulated
// placements; it is not a second planner searching arbitrary command futures.
struct RolloutState {
    std::map<std::int64_t, SimGap> gaps;
    std::vector<SimPipe> active;
    std::int64_t trenchLength = 0;
    int nextPid = 1;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};
    std::array<std::int64_t, 41> lengthOccurrenceCount{};
    std::array<std::array<std::int64_t, 2>, 41> removedLengthCohort{};
    bool parityCohortMode = false;
    bool runLeftDisabledBySmoothTrend = false;
    bool alternatingDeleteMode = false;
    int predictedDeletedParity = 1;
    int lastDeletedPid = -1;
    int lastDeletedLength = -1;
    std::size_t strideTwoDeleteTransitions = 0;

    bool hasSteadySizeTrend() const {
        if (recentLengths.size() < 128) return false;
        std::array<int, 3> distinctLengths{};
        std::size_t distinctCount = 0;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (*it == previous) continue;
            distinctLengths[distinctCount] = *it;
            ++distinctCount;
            previous = *it;
            if (distinctCount == distinctLengths.size()) break;
        }
        if (distinctCount < distinctLengths.size()) return false;
        const int recentStep = distinctLengths[0] - distinctLengths[1];
        const int previousStep = distinctLengths[1] - distinctLengths[2];
        return recentStep == previousStep;
    }

    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t seen = 0; seen < kSameLengthRightRun; ++seen, ++it) {
            if (*it != length) return false;
        }
        return true;
    }

    bool hasSmoothSizeTrendWith(int currentLength) const {
        if (recentLengths.empty()) return false;
        const bool currentRunAlreadyInHistory = recentLengths.back() == currentLength;
        std::array<int, 2> priorRunLengths{};
        std::size_t distinctCount = 0;
        bool firstRun = true;
        int lastRunLength = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (firstRun) {
                firstRun = false;
                lastRunLength = *it;
                if (!currentRunAlreadyInHistory) {
                    priorRunLengths[distinctCount++] = *it;
                }
                continue;
            }
            if (*it == lastRunLength) continue;
            lastRunLength = *it;
            priorRunLengths[distinctCount++] = *it;
            if (distinctCount == priorRunLengths.size()) break;
        }
        if (distinctCount < priorRunLengths.size()) return false;
        return currentLength - priorRunLengths[0] ==
            priorRunLengths[0] - priorRunLengths[1];
    }

    std::int64_t placementStart(const SimGap& gap, std::int64_t start,
                                int length, bool highSide) const {
        return highSide ? gap.end - static_cast<std::int64_t>(length) : start;
    }

    void addFreeGap(std::int64_t start, std::int64_t end, int cohort) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto previous = std::prev(it);
            if (previous->second.end >= start) {
                if (previous->second.cohort != cohort) cohort = -1;
                start = previous->first;
                end = std::max(end, previous->second.end);
                gaps.erase(previous);
                it = gaps.lower_bound(start);
            }
        }
        while (it != gaps.end() && it->first <= end) {
            if (it->second.cohort != cohort) cohort = -1;
            end = std::max(end, it->second.end);
            it = gaps.erase(it);
        }
        gaps.emplace(start, SimGap{end, cohort});
    }

    void splitGap(std::int64_t gapStart, int length, bool highSide) {
        const auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        const std::int64_t start = it->first;
        const SimGap gap = it->second;
        const std::int64_t pipeStart = placementStart(gap, start, length, highSide);
        gaps.erase(it);
        if (start < pipeStart) addFreeGap(start, pipeStart, gap.cohort);
        const std::int64_t pipeEnd = pipeStart + static_cast<std::int64_t>(length);
        if (pipeEnd < gap.end) addFreeGap(pipeEnd, gap.end, gap.cohort);
    }

    void recordLength(int length) {
        recentLengths.push_back(length);
        ++recentFrequency[static_cast<std::size_t>(length)];
        if (recentLengths.size() > kHistoryWindow) {
            --recentFrequency[static_cast<std::size_t>(recentLengths.front())];
            recentLengths.pop_front();
        }
    }

    std::int64_t fitScore(std::int64_t gapLength, int length) const {
        const std::int64_t slack = gapLength - static_cast<std::int64_t>(length);
        std::int64_t score = slack * static_cast<std::int64_t>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                misses += recentFrequency[static_cast<std::size_t>(request)];
            }
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }

    std::optional<std::int64_t> bestGap(int length, bool highSide, int sizeCohort) const {
        bool hasPreferred = false;
        if (parityCohortMode) {
            for (const auto& [start, gap] : gaps) {
                (void)start;
                if (gap.end - start >= length && gap.cohort == sizeCohort) {
                    hasPreferred = true;
                    break;
                }
            }
        }
        bool found = false;
        std::int64_t bestStart = 0;
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        // The real allocator indexes free spans by (length, start) and
        // evaluates only the lowest-address span for each distinct length.
        // This simulator is keyed by start, so suppress later equal-length
        // spans after seeing their first eligible (lowest-address) member.
        std::set<std::int64_t> consideredLengths;
        for (const auto& [start, gap] : gaps) {
            const std::int64_t gapLength = gap.end - start;
            if (gapLength < length) continue;
            if (parityCohortMode &&
                (hasPreferred ? gap.cohort != sizeCohort : gap.cohort >= 0)) continue;
            if (!consideredLengths.insert(gapLength).second) continue;
            const std::int64_t score = fitScore(gapLength, length);
            if (!found || score < bestScore ||
                (score == bestScore &&
                 ((highSide && start > bestStart) || (!highSide && start < bestStart)))) {
                found = true;
                bestStart = start;
                bestScore = score;
            }
        }
        if (!found) return std::nullopt;
        return bestStart;
    }

    void appendPipe(int length, std::int64_t start, int sizeCohort) {
        active.push_back(SimPipe{nextPid++, start, length, sizeCohort});
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];
        recordLength(length);
    }

    void placeAtCandidate(std::int64_t gapStart, int length, bool highSide) {
        const auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        const std::int64_t start = placementStart(it->second, gapStart, length, highSide);
        const int cohort = it->second.cohort;
        splitGap(gapStart, length, highSide);
        appendPipe(length, start, sizeCohort);
        (void)cohort;
    }

    void place(int length) {
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
        // A long observed run of one size is split into two spatial lanes by
        // that size's placement-occurrence cohort, without using PID parity or
        // a predicted deletion pattern.
        const bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((nextPid & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        std::int64_t start = -1;
        const auto gapStart = bestGap(length, highSide, sizeCohort);
        if (gapStart.has_value()) {
            const auto it = gaps.find(*gapStart);
            const int cohort = it->second.cohort;
            start = placementStart(it->second, *gapStart, length, highSide);
            splitGap(*gapStart, length, highSide);
            (void)cohort;
        }

        if (start < 0) {
            auto tail = gaps.end();
            if (!gaps.empty()) {
                auto last = std::prev(gaps.end());
                if (last->second.end == trenchLength) tail = last;
            }
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != gaps.end()) {
                tailCohort = tail->second.cohort;
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == gaps.end() || preserveForeignTail ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            const std::int64_t digs = (deficit + kDigLength - 1) / kDigLength;
            trenchLength += digs * kDigLength;
            if (tail != gaps.end() && !preserveForeignTail) gaps.erase(tail);
            if (parityCohortMode && highSide && !preserveForeignTail) {
                start = trenchLength - length;
                if (tailStart < start) addFreeGap(tailStart, start, tailCohort);
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    addFreeGap(remainderStart, trenchLength, tailCohort);
                }
            }
        }
        appendPipe(length, start, sizeCohort);
    }

    void recordDeletionPattern(int pid, int length) {
        if (lastDeletedPid >= 0 && lastDeletedLength == length &&
            pid == lastDeletedPid + 2) {
            ++strideTwoDeleteTransitions;
        } else {
            strideTwoDeleteTransitions = 0;
            alternatingDeleteMode = false;
        }
        if (strideTwoDeleteTransitions >= 7) {
            alternatingDeleteMode = true;
            predictedDeletedParity = pid & 1;
        }
        lastDeletedPid = pid;
        lastDeletedLength = length;
    }

    void removeByRank(int rankFromNewestPermille) {
        if (active.empty()) return;
        const std::size_t n = active.size();
        const std::size_t rankFromNewest = n <= 1 ? 0 :
            static_cast<std::size_t>(rankFromNewestPermille) * (n - 1) / 1000;
        const std::size_t index = n - 1 - std::min(rankFromNewest, n - 1);
        const SimPipe pipe = active[index];
        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
        recordDeletionPattern(pipe.pid, pipe.length);
        const std::size_t lengthIndex = static_cast<std::size_t>(pipe.length);
        ++removedLengthCohort[lengthIndex][static_cast<std::size_t>(pipe.sizeCohort)];
        const std::int64_t totalForLength =
            removedLengthCohort[lengthIndex][0] + removedLengthCohort[lengthIndex][1];
        const std::int64_t dominantForLength = std::max(
            removedLengthCohort[lengthIndex][0], removedLengthCohort[lengthIndex][1]);
        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 &&
            hasSteadySizeTrend()) {
            parityCohortMode = true;
        }
    }

    void apply(const Observation& event) {
        if (event.kind > 0) place(event.value);
        else if (event.kind < 0) removeByRank(event.value);
    }
};

struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    int sizeCohort = 0;
};

struct DiagnosticAction {
    std::int64_t digs = 0;
    std::int64_t start = 0;
};

class Allocator {
public:
    // Free spans are half-open [start, end). The map supports merging after a
    // removal; the set chooses the shortest fitting span, then the lowest start.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::map<std::int64_t, int> gapCohort;
    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySizeShared;
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};
    std::array<std::int64_t, 41> lengthOccurrenceCount{};
    std::array<std::array<std::int64_t, 2>, 41> removedLengthCohort{};
    bool parityCohortMode = false;
    bool runLeftDisabledBySmoothTrend = false;
    bool alternatingDeleteMode = false;
    int predictedDeletedParity = 1;
    int lastDeletedPid = -1;
    int lastDeletedLength = -1;
    std::size_t strideTwoDeleteTransitions = 0;
    std::vector<int> activeFenwick = std::vector<int>(200001, 0);
    std::size_t activePipeCount = 0;
    std::deque<Observation> observedHistory;
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;

    void place(int length) {
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
        // Split a long observed same-size run by size-local occurrence cohort.
        // The policy is causal and does not inspect deletions or future input.
        const bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            // No existing span fits. Continue from the left edge of the free
            // tail, retaining its unused part as the new expandable tail.
            auto tail = tailGap();
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                tailCohort = gapCohort.at(tail->first);
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == freeByStart.end() || preserveForeignTail
                    ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands can arrive. Each pipe has length at most
            // 40 m, so it can require at most two 20 m sections: total digging
            // is at most 8,000,000 m, below the 100,000,000 m contest cap.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end() && !preserveForeignTail) eraseGap(tail);
            trenchLength = newLength;
            if (parityCohortMode && highSide && !preserveForeignTail) {
                start = trenchLength - length;
                if (tailStart < start) addFreeGap(tailStart, start, tailCohort);
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    addFreeGap(remainderStart, trenchLength, tailCohort);
                }
            }
        }

        printPlacement(digs, start);
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];
        recordLength(length);
        recordObservation(Observation{1, length});
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

        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));

        const Pipe pipe = pipes[index];
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        fenwickAdd(static_cast<int>(index), -1);
        --activePipeCount;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
        recordDeletionPattern(static_cast<int>(index), pipe.length);
        const std::size_t lengthIndex = static_cast<std::size_t>(pipe.length);
        ++removedLengthCohort[lengthIndex][static_cast<std::size_t>(pipe.sizeCohort)];
        const std::int64_t totalForLength =
            removedLengthCohort[lengthIndex][0] + removedLengthCohort[lengthIndex][1];
        const std::int64_t dominantForLength = std::max(
            removedLengthCohort[lengthIndex][0], removedLengthCohort[lengthIndex][1]);
        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 &&
            hasSteadySizeTrend()) {
            parityCohortMode = true;
        }
        recordObservation(Observation{-1, rankPermille});
    }

    void compactFenwickForDiagnostic() {
        activeFenwick.assign(pipes.size(), 0);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            if (pipes[pid].active) fenwickAdd(static_cast<int>(pid), 1);
        }
    }

    std::vector<DiagnosticAction> diagnosticActions(int length, int cap) const {
        std::vector<DiagnosticAction> result;
        std::set<std::pair<std::int64_t, std::int64_t>> unique;
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        const bool smoothDisabled = runLeftDisabledBySmoothTrend ||
            hasSmoothSizeTrendWith(length);
        const bool runLeft = !smoothDisabled && hasSameLengthRecentRun(length);
        const bool highSide = runLeft
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));

        auto add = [&](std::int64_t digs, std::int64_t start) {
            if (start < 0 || start + length > trenchLength + digs * kDigLength) return;
            if (unique.emplace(digs, start).second) result.push_back({digs, start});
        };

        auto baseline = const_cast<Allocator*>(this)->bestFittingGap(length, highSide, sizeCohort);
        std::vector<std::tuple<std::int64_t, std::int64_t, std::int64_t>> fitting;
        for (const auto& [start, end] : freeByStart) {
            const std::int64_t gapLength = end - start;
            if (gapLength < length) continue;
            fitting.emplace_back(scoreGap(gapLength, length), start, end);
        }
        std::sort(fitting.begin(), fitting.end(), [highSide](const auto& lhs, const auto& rhs) {
            if (std::get<0>(lhs) != std::get<0>(rhs)) return std::get<0>(lhs) < std::get<0>(rhs);
            return highSide ? std::get<1>(lhs) > std::get<1>(rhs)
                            : std::get<1>(lhs) < std::get<1>(rhs);
        });

        if (!fitting.empty()) {
            std::vector<std::pair<std::int64_t, std::int64_t>> selected;
            const std::size_t per_rank = static_cast<std::size_t>(std::max(1, cap / 4));
            for (std::size_t i = 0; i < fitting.size() && i < per_rank; ++i)
                selected.emplace_back(std::get<1>(fitting[i]), std::get<2>(fitting[i]));
            auto by_size = fitting;
            std::sort(by_size.begin(), by_size.end(), [](const auto& lhs, const auto& rhs) {
                const auto lsize = std::get<2>(lhs) - std::get<1>(lhs);
                const auto rsize = std::get<2>(rhs) - std::get<1>(rhs);
                if (lsize != rsize) return lsize > rsize;
                return std::get<1>(lhs) < std::get<1>(rhs);
            });
            for (std::size_t i = 0; i < by_size.size() && i < per_rank; ++i)
                selected.emplace_back(std::get<1>(by_size[i]), std::get<2>(by_size[i]));
            if (baseline != freeByStart.end()) selected.emplace_back(baseline->first, baseline->second);
            auto tail = const_cast<Allocator*>(this)->tailGap();
            if (tail != freeByStart.end() && tail->second - tail->first >= length)
                selected.emplace_back(tail->first, tail->second);
            if (!fitting.empty()) {
                auto address = fitting;
                std::sort(address.begin(), address.end(), [](const auto& lhs, const auto& rhs) {
                    return std::get<1>(lhs) < std::get<1>(rhs);
                });
                selected.emplace_back(std::get<1>(address.front()), std::get<2>(address.front()));
                selected.emplace_back(std::get<1>(address.back()), std::get<2>(address.back()));
            }
            std::sort(selected.begin(), selected.end());
            selected.erase(std::unique(selected.begin(), selected.end()), selected.end());
            for (const auto& [left, right] : selected) {
                add(0, left);
                add(0, right - length);
            }
            if (baseline != freeByStart.end()) {
                const std::int64_t start = highSide
                    ? baseline->second - length : baseline->first;
                add(0, start);
            }
            if (result.size() > static_cast<std::size_t>(cap)) {
                std::vector<DiagnosticAction> clipped;
                const std::int64_t base_start = baseline != freeByStart.end()
                    ? (highSide ? baseline->second - length : baseline->first)
                    : result.front().start;
                for (const auto& action : result) {
                    if (action.digs == 0 && action.start == base_start) {
                        clipped.push_back(action);
                        break;
                    }
                }
                for (const auto& action : result) {
                    if (clipped.size() >= static_cast<std::size_t>(cap)) break;
                    if (action.digs == 0 && action.start == base_start) continue;
                    clipped.push_back(action);
                }
                result = std::move(clipped);
            }
            return result;
        }

        auto tail = const_cast<Allocator*>(this)->tailGap();
        int tailCohort = parityCohortMode ? sizeCohort : -1;
        bool preserveForeignTail = false;
        if (parityCohortMode && tail != freeByStart.end()) {
            tailCohort = gapCohort.at(tail->first);
            preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
            if (preserveForeignTail) tailCohort = sizeCohort;
        }
        const std::int64_t tailStart =
            tail == freeByStart.end() || preserveForeignTail ? trenchLength : tail->first;
        const std::int64_t tailLength = trenchLength - tailStart;
        const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
        const std::int64_t digs = (deficit + kDigLength - 1) / kDigLength;
        const std::int64_t newLength = trenchLength + digs * kDigLength;
        for (std::int64_t start = tailStart; start + length <= newLength; ++start)
            add(digs, start);
        if (result.size() > static_cast<std::size_t>(cap)) {
            std::vector<DiagnosticAction> clipped;
            if (!result.empty()) clipped.push_back(result.front());
            if (result.size() > 1 && clipped.size() < static_cast<std::size_t>(cap))
                clipped.push_back(result.back());
            for (std::size_t i = 1; i + 1 < result.size() &&
                 clipped.size() < static_cast<std::size_t>(cap); ++i) {
                if (i % std::max<std::size_t>(1, result.size() /
                        std::max(1, cap - static_cast<int>(clipped.size()))) == 0)
                    clipped.push_back(result[i]);
            }
            result = std::move(clipped);
        }
        return result;
    }

    void placeDiagnostic(int length, const DiagnosticAction& action) {
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
        const bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        auto baselineGap = bestFittingGap(length, highSide, sizeCohort);
        if (baselineGap != freeByStart.end())
            (void)chooseGapWithRollout(length, highSide, sizeCohort, baselineGap);

        const std::int64_t start = action.start;
        const std::int64_t end = start + length;
        if (action.digs == 0) {
            auto it = freeByStart.upper_bound(start);
            if (it == freeByStart.begin()) throw std::runtime_error("forced placement has no containing gap");
            --it;
            if (it->first > start || it->second < end)
                throw std::runtime_error("forced placement is outside a free gap");
            const std::int64_t gapStart = it->first;
            const std::int64_t gapEnd = it->second;
            const int cohort = gapCohort.at(gapStart);
            eraseGap(it);
            if (gapStart < start) addFreeGap(gapStart, start, cohort);
            if (end < gapEnd) addFreeGap(end, gapEnd, cohort);
        } else {
            const std::int64_t oldTrench = trenchLength;
            const std::int64_t newTrench = oldTrench + action.digs * kDigLength;
            auto tail = tailGap();
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                tailCohort = gapCohort.at(tail->first);
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == freeByStart.end() || preserveForeignTail ? oldTrench : tail->first;
            if (start < tailStart || end > newTrench)
                throw std::runtime_error("forced trench placement is outside expandable tail");
            if (!preserveForeignTail && tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newTrench;
            if (!preserveForeignTail && tailStart < start)
                addFreeGap(tailStart, start, tailCohort);
            if (end < newTrench) addFreeGap(end, newTrench, tailCohort);
        }
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];
        recordLength(length);
        recordObservation(Observation{1, length});
    }


private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    void fenwickAdd(int index, int delta) {
        while (index >= static_cast<int>(activeFenwick.size())) {
            const int position = static_cast<int>(activeFenwick.size());
            const int lowbit = position & -position;
            const int prior = fenwickPrefix(position - 1) - fenwickPrefix(position - lowbit);
            activeFenwick.push_back(prior);
        }
        const int limit = static_cast<int>(activeFenwick.size());
        for (int position = index; position < limit; position += position & -position) {
            activeFenwick[static_cast<std::size_t>(position)] += delta;
        }
    }

    int fenwickPrefix(int index) const {
        int sum = 0;
        for (int position = index; position > 0; position -= position & -position) {
            sum += activeFenwick[static_cast<std::size_t>(position)];
        }
        return sum;
    }

    int rankFromNewestPermille(int pid) const {
        if (activePipeCount <= 1) return 0;
        const std::size_t newer = activePipeCount -
            static_cast<std::size_t>(fenwickPrefix(pid));
        const std::size_t denominator = activePipeCount - 1;
        return static_cast<int>(newer * 1000U / denominator);
    }

    void recordDeletionPattern(int pid, int length) {
        if (lastDeletedPid >= 0 && lastDeletedLength == length &&
            pid == lastDeletedPid + 2) {
            ++strideTwoDeleteTransitions;
        } else {
            strideTwoDeleteTransitions = 0;
            alternatingDeleteMode = false;
        }
        if (strideTwoDeleteTransitions >= 7) {
            alternatingDeleteMode = true;
            predictedDeletedParity = pid & 1;
        }
        lastDeletedPid = pid;
        lastDeletedLength = length;
    }

    void recordObservation(const Observation& event) {
        observedHistory.push_back(event);
        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();
    }

    std::int64_t scoreGap(std::int64_t gapLength, int length) const {
        const std::int64_t slack = gapLength - static_cast<std::int64_t>(length);
        std::int64_t score = slack * static_cast<std::int64_t>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                misses += recentFrequency[static_cast<std::size_t>(request)];
            }
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }

    bool observationKeyEqual(const Observation& lhs, const Observation& rhs) const {
        if (lhs.kind != rhs.kind) return false;
        return lhs.kind <= 0 || lhs.value == rhs.value;
    }

    std::uint32_t nextRandom(std::uint32_t& state) const {
        state ^= state << 13U;
        state ^= state >> 17U;
        state ^= state << 5U;
        return state;
    }

    std::array<Observation, kMcDepth> sampleScenario(std::uint32_t& randomState) const {
        std::array<Observation, kMcDepth> result{};
        const std::size_t n = observedHistory.size();
        const std::size_t minStart = n > 128 ? n - 128 : 0;
        std::vector<std::size_t> starts;
        const std::size_t maxStart = n >= kMcDepth ? n - kMcDepth : 0;
        if (n < kMcDepth + 2) return result;

        const std::size_t maxContext = std::min<std::size_t>(3, n - 1);
        for (std::size_t context = maxContext; context > 0 && starts.empty(); --context) {
            const std::size_t contextBegin = n - context;
            for (std::size_t start = minStart + context; start <= maxStart; ++start) {
                bool matches = true;
                for (std::size_t offset = 0; offset < context; ++offset) {
                    if (!observationKeyEqual(observedHistory[contextBegin + offset],
                                             observedHistory[start - context + offset])) {
                        matches = false;
                        break;
                    }
                }
                if (matches) starts.push_back(start);
            }
        }
        if (starts.empty()) {
            for (std::size_t start = minStart; start <= maxStart; ++start) {
                starts.push_back(start);
            }
        }
        if (starts.empty()) return result;

        const std::size_t start = starts[static_cast<std::size_t>(
            nextRandom(randomState) % static_cast<std::uint32_t>(starts.size()))];
        for (std::size_t offset = 0; offset < kMcDepth; ++offset) {
            result[offset] = observedHistory[start + offset];
        }
        return result;
    }

    RolloutState makeRolloutState() const {
        RolloutState state;
        for (const auto& [start, end] : freeByStart) {
            state.gaps.emplace(start, SimGap{end, gapCohort.at(start)});
        }
        state.trenchLength = trenchLength;
        state.nextPid = static_cast<int>(pipes.size());
        state.recentLengths = recentLengths;
        state.recentFrequency = recentFrequency;
        state.lengthOccurrenceCount = lengthOccurrenceCount;
        state.removedLengthCohort = removedLengthCohort;
        state.parityCohortMode = parityCohortMode;
        state.runLeftDisabledBySmoothTrend = runLeftDisabledBySmoothTrend;
        state.alternatingDeleteMode = alternatingDeleteMode;
        state.predictedDeletedParity = predictedDeletedParity;
        state.lastDeletedPid = lastDeletedPid;
        state.lastDeletedLength = lastDeletedLength;
        state.strideTwoDeleteTransitions = strideTwoDeleteTransitions;
        state.active.reserve(activePipeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            if (!pipes[pid].active) continue;
            const Pipe& pipe = pipes[pid];
            state.active.push_back(SimPipe{static_cast<int>(pid), pipe.start,
                                           pipe.length, pipe.sizeCohort});
        }
        return state;
    }

    std::vector<GapCandidate> topGapCandidates(
        int length, bool highSide, int sizeCohort) const {
        const std::set<std::pair<std::int64_t, std::int64_t>>* index = &freeBySize;
        if (parityCohortMode) {
            const auto& preferred = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            auto it = preferred.lower_bound({length, 0});
            if (it != preferred.end()) index = &preferred;
            else index = &freeBySizeShared;
        }

        std::vector<GapCandidate> candidates;
        auto it = index->lower_bound({length, 0});
        while (it != index->end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});
            ++it;
        }
        std::sort(candidates.begin(), candidates.end(), [highSide](
            const GapCandidate& lhs, const GapCandidate& rhs) {
            if (lhs.score != rhs.score) return lhs.score < rhs.score;
            return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
        });
        if (candidates.size() > 3) candidates.resize(3);
        return candidates;
    }

    std::int64_t chooseGapWithRollout(
        int length, bool highSide, int sizeCohort, StartIter baselineGap) {
#if defined(MC_ROLLOUT_DISABLED)
        (void)length;
        (void)highSide;
        (void)sizeCohort;
        return baselineGap->first;
#else
        if (mcDecisionsUsed >= kMcDecisionBudget ||
            observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps ||
            activePipeCount > kMcMaxActivePipes) {
            return baselineGap->first;
        }
        const auto candidates = topGapCandidates(length, highSide, sizeCohort);
        if (candidates.size() < 2 || candidates.front().start != baselineGap->first) {
            return baselineGap->first;
        }

        ++mcDecisionsUsed;
        const RolloutState base = makeRolloutState();
        std::uint32_t randomState = 0x9e3779b9U ^
            static_cast<std::uint32_t>(pipes.size() * 0x85ebca6bU) ^
            (static_cast<std::uint32_t>(length) * 0xc2b2ae35U) ^
            static_cast<std::uint32_t>(trenchLength);
        if (randomState == 0) randomState = 1;

        std::array<std::array<Observation, kMcDepth>, kMcTrials> scenarios{};
        for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
            scenarios[trial] = sampleScenario(randomState);
        }

        std::array<std::int64_t, 3> totalTrench{};
        for (std::size_t candidate = 0; candidate < candidates.size(); ++candidate) {
            for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
                RolloutState simulation = base;
                simulation.placeAtCandidate(candidates[candidate].start, length, highSide);
                for (const auto& event : scenarios[trial]) simulation.apply(event);
                totalTrench[candidate] += simulation.trenchLength;
                ++mcRolloutsRun;
            }
        }
        std::size_t best = 0;
        for (std::size_t candidate = 1; candidate < candidates.size(); ++candidate) {
            if (totalTrench[candidate] < totalTrench[best]) best = candidate;
        }
        if (best != 0 && totalTrench[best] +
            static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[0]) {
            return candidates[best].start;
        }
        return baselineGap->first;
#endif
    }

    bool hasSteadySizeTrend() const {
        if (recentLengths.size() < 128) return false;
        std::array<int, 3> distinctLengths{};
        std::size_t distinctCount = 0;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (*it == previous) continue;
            distinctLengths[distinctCount] = *it;
            ++distinctCount;
            previous = *it;
            if (distinctCount == distinctLengths.size()) break;
        }
        if (distinctCount < distinctLengths.size()) return false;
        const int recentStep = distinctLengths[0] - distinctLengths[1];
        const int previousStep = distinctLengths[1] - distinctLengths[2];
        return recentStep == previousStep;
    }

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
        if (parityCohortMode) {
            const auto& cohortGaps = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            StartIter preferred = bestFittingGapFromSet(cohortGaps, length, highSide);
            if (preferred != freeByStart.end()) return preferred;
            StartIter shared = bestFittingGapFromSet(freeBySizeShared, length, highSide);
            if (shared != freeByStart.end()) return shared;
            return freeByStart.end();
        }
        return bestFittingGapFromSet(freeBySize, length, highSide);
    }

    StartIter bestFittingGapFromSet(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length,
        bool highSide) {
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            std::int64_t score = slack * historySize;
            if (slack > 0 && slack <= 40) {
                int misses = 0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                    misses += recentFrequency[static_cast<std::size_t>(request)];
                }
                score += kUnfitPenaltyScale * misses;
            }

            // Iteration is by size and then start, so keeping the first tie
            // implements the smaller-gap, then lower-address tie-break.
            if (score < bestScore ||
                (score == bestScore && best != freeByStart.end() &&
                 ((highSide && it->second > best->first) ||
                  (!highSide && it->second < best->first)))) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = gaps.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
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

    bool hasSmoothSizeTrendWith(int currentLength) const {
        if (recentLengths.empty()) return false;
        const bool currentRunAlreadyInHistory = recentLengths.back() == currentLength;
        std::array<int, 2> priorRunLengths{};
        std::size_t distinctCount = 0;
        bool firstRun = true;
        int lastRunLength = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (firstRun) {
                firstRun = false;
                lastRunLength = *it;
                if (!currentRunAlreadyInHistory) {
                    priorRunLengths[distinctCount++] = *it;
                }
                continue;
            }
            if (*it == lastRunLength) continue;
            lastRunLength = *it;
            priorRunLengths[distinctCount++] = *it;
            if (distinctCount == priorRunLengths.size()) break;
        }
        if (distinctCount < priorRunLengths.size()) return false;
        return currentLength - priorRunLengths[0] ==
            priorRunLengths[0] - priorRunLengths[1];
    }

    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const int cohort = gapCohort.at(start);
        const std::int64_t placementStart = highSide
            ? end - static_cast<std::int64_t>(length) : start;
        eraseGap(it);
        if (start < placementStart) addFreeGap(start, placementStart, cohort);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort);
        return placementStart;
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
        const std::int64_t gapLength = end - start;
        const int cohort = gapCohort.at(start);
        freeBySize.erase({gapLength, start});
        if (cohort >= 0 && cohort <= 1) {
            freeBySizeCohort[static_cast<std::size_t>(cohort)].erase({gapLength, start});
        } else {
            freeBySizeShared.erase({gapLength, start});
        }
        gapCohort.erase(start);
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end, int cohort) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                start = previous->first;
                end = std::max(end, previous->second);
                eraseGap(previous);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            if (gapCohort.at(it->first) != cohort) cohort = -1;
            end = std::max(end, it->second);
            auto next = it++;
            eraseGap(next);
        }
        freeByStart.emplace(start, end);
        const std::int64_t gapLength = end - start;
        freeBySize.emplace(gapLength, start);
        gapCohort.emplace(start, cohort);
        if (cohort >= 0 && cohort <= 1) {
            freeBySizeCohort[static_cast<std::size_t>(cohort)].emplace(gapLength, start);
        } else {
            freeBySizeShared.emplace(gapLength, start);
        }
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

class NullBuffer final : public std::streambuf {
protected:
    int overflow(int ch) override { return ch; }
};

int main(int argc, char** argv) {
    if (argc != 8) {
        std::cerr << "usage: longbeam INPUT TRACE OUT START COUNT WIDTH ACTION_CAP\n";
        return 2;
    }
    const std::string input_path = argv[1];
    const std::string trace_path = argv[2];
    const std::string output_path = argv[3];
    const int start_op = std::stoi(argv[4]);
    const int window_count = std::stoi(argv[5]);
    const int width = std::stoi(argv[6]);
    const int action_cap = std::stoi(argv[7]);

    std::ifstream in(input_path);
    double weight = 0.0;
    int n = 0;
    in >> weight >> n;
    std::vector<std::int64_t> ops(static_cast<std::size_t>(n));
    for (auto& op : ops) in >> op;
    if (!in || start_op < 1 || window_count < 1 || start_op + window_count - 1 > n)
        throw std::runtime_error("invalid input/window");

    std::ifstream tr(trace_path);
    std::vector<std::int64_t> expected;
    std::int64_t value;
    while (tr >> value) expected.push_back(value);
    if (!tr.eof()) throw std::runtime_error("bad trace");

    Allocator base;
    std::unique_ptr<Allocator> initial;
    std::vector<DiagnosticAction> baseline_actions(static_cast<std::size_t>(n));
    std::size_t answer_cursor = 0;
    for (int i = 0; i < n; ++i) {
        if (i + 1 == start_op) {
            base.compactFenwickForDiagnostic();
            initial.reset(new Allocator(base));
        }
        std::ostringstream capture;
        std::streambuf* old = std::cout.rdbuf(capture.rdbuf());
        if (ops[static_cast<std::size_t>(i)] > 0)
            base.place(static_cast<int>(ops[static_cast<std::size_t>(i)]));
        else
            base.remove(-ops[static_cast<std::size_t>(i)]);
        std::cout.rdbuf(old);
        std::istringstream actual_stream(capture.str());
        std::vector<std::int64_t> actual;
        while (actual_stream >> value) actual.push_back(value);
        const std::size_t need = ops[static_cast<std::size_t>(i)] > 0 ? 2 : 1;
        if (answer_cursor + need > expected.size())
            throw std::runtime_error("baseline answer stream too short");
        if (ops[static_cast<std::size_t>(i)] > 0)
            baseline_actions[static_cast<std::size_t>(i)] =
                {expected[answer_cursor], expected[answer_cursor + 1]};
        if (actual.size() != need)
            throw std::runtime_error("unexpected baseline response shape at op " + std::to_string(i + 1));
        for (std::size_t k = 0; k < need; ++k) {
            if (actual[k] != expected[answer_cursor + k])
                throw std::runtime_error("baseline mismatch at op " + std::to_string(i + 1));
        }
        answer_cursor += need;
    }
    if (answer_cursor != expected.size()) throw std::runtime_error("baseline answer token mismatch");
    if (!initial) throw std::runtime_error("initial window state missing");
    const std::int64_t baseline_final = base.trenchLength;
    const std::int64_t initial_trench = initial->trenchLength;
    const std::size_t begin = static_cast<std::size_t>(start_op - 1);
    const std::size_t stop = begin + static_cast<std::size_t>(window_count);

    std::set<int> future_deleted;
    for (std::size_t i = begin; i < stop; ++i)
        if (ops[i] < 0) future_deleted.insert(static_cast<int>(-ops[i]));
    std::array<int, 41> future_lengths{};
    for (std::size_t i = begin; i < stop; ++i)
        if (ops[i] > 0) ++future_lengths[static_cast<std::size_t>(ops[i])];

    NullBuffer null_buffer;
    std::streambuf* original_stdout = std::cout.rdbuf(&null_buffer);
    Allocator control = *initial;
    struct Choice { int op_index; DiagnosticAction action; };
    struct Node { Allocator state; std::vector<Choice> path; };
    std::vector<Choice> control_path;
    std::vector<Node> beam;
    beam.push_back(Node{*initial, {}});
    std::uint64_t expanded = 0;

    auto signature = [](const Allocator& s) {
        std::string key;
        auto put = [&](auto x) {
            key.append(reinterpret_cast<const char*>(&x), sizeof(x));
        };
        put(s.trenchLength);
        put(s.mcDecisionsUsed);
        for (const auto& [left, right] : s.freeByStart) {
            put(left); put(right); put(s.gapCohort.at(left));
        }
        const std::int64_t sentinel = -1;
        put(sentinel);
        for (std::size_t pid = 1; pid < s.pipes.size(); ++pid) {
            if (!s.pipes[pid].active) continue;
            const std::int64_t p = static_cast<std::int64_t>(pid);
            put(p); put(s.pipes[pid].start); put(s.pipes[pid].sizeCohort);
        }
        return key;
    };

    struct Ranked { std::size_t index; std::int64_t trench; std::int64_t capacity;
                    std::int64_t max_gap; std::int64_t tail; std::size_t gaps; };
    auto rank_node = [&](const Node& node) {
        const Allocator& s = node.state;
        std::vector<std::pair<std::int64_t, std::int64_t>> intervals;
        intervals.reserve(s.freeByStart.size() + future_deleted.size());
        for (const auto& [left, right] : s.freeByStart) intervals.emplace_back(left, right);
        for (int pid : future_deleted) {
            if (pid > 0 && static_cast<std::size_t>(pid) < s.pipes.size() && s.pipes[pid].active)
                intervals.emplace_back(s.pipes[pid].start,
                                       s.pipes[pid].start + s.pipes[pid].length);
        }
        std::sort(intervals.begin(), intervals.end());
        std::vector<std::pair<std::int64_t, std::int64_t>> merged;
        for (const auto& iv : intervals) {
            if (merged.empty() || iv.first > merged.back().second) merged.push_back(iv);
            else merged.back().second = std::max(merged.back().second, iv.second);
        }
        std::int64_t capacity = 0, max_gap = 0, tail = 0;
        for (const auto& [left, right] : merged) {
            const auto len = right - left;
            max_gap = std::max(max_gap, len);
            if (right == s.trenchLength) tail = len;
            for (int l = 1; l <= 40; ++l)
                capacity += static_cast<std::int64_t>(future_lengths[static_cast<std::size_t>(l)]) *
                            (len / l);
        }
        return std::tuple<std::int64_t, std::int64_t, std::int64_t,
                          std::int64_t, std::size_t>(
            s.trenchLength, -capacity, -max_gap, -tail, s.freeByStart.size());
    };

    for (std::size_t i = begin; i < stop; ++i) {
        const std::int64_t op = ops[i];
        std::vector<Node> generated;
        if (op > 0) {
            for (const Node& node : beam) {
                auto actions = node.state.diagnosticActions(static_cast<int>(op), action_cap);
                for (const auto& action : actions) {
                    Node child{node.state, node.path};
                    child.state.placeDiagnostic(static_cast<int>(op), action);
                    child.path.push_back(Choice{static_cast<int>(i + 1), action});
                    generated.push_back(std::move(child));
                }
            }
        } else {
            for (const Node& node : beam) {
                Node child{node.state, node.path};
                child.state.remove(-op);
                generated.push_back(std::move(child));
            }
        }
        if (op < 0) future_deleted.erase(static_cast<int>(-op));
        else --future_lengths[static_cast<std::size_t>(op)];

        if (op > 0) {
            // The baseline control remains available in every beam layer.
            control.place(static_cast<int>(op));
            control_path.push_back(Choice{static_cast<int>(i + 1), baseline_actions[i]});
        } else {
            control.remove(-op);
        }

        std::unordered_set<std::string> seen;
        std::vector<Node> unique;
        unique.reserve(generated.size() + 1);
        for (auto& node : generated) {
            auto key = signature(node.state);
            if (seen.insert(std::move(key)).second) unique.push_back(std::move(node));
        }
        auto control_key = signature(control);
        if (seen.insert(control_key).second) unique.push_back(Node{control, control_path});
        expanded += generated.size();

        std::sort(unique.begin(), unique.end(), [&](const Node& lhs, const Node& rhs) {
            return rank_node(lhs) < rank_node(rhs);
        });
        if (unique.size() > static_cast<std::size_t>(width)) unique.resize(static_cast<std::size_t>(width));
        beam = std::move(unique);
    }

    std::int64_t best_final = std::numeric_limits<std::int64_t>::max();
    std::size_t best_index = 0;
    bool best_is_baseline_control = false;
    std::vector<std::int64_t> finalist_trenches;
    for (std::size_t j = 0; j < beam.size(); ++j) {
        Allocator replay = beam[j].state;
        replay.compactFenwickForDiagnostic();
        for (std::size_t i = stop; i < ops.size(); ++i) {
            if (ops[i] > 0) replay.place(static_cast<int>(ops[i]));
            else replay.remove(-ops[i]);
        }
        finalist_trenches.push_back(replay.trenchLength);
        if (replay.trenchLength < best_final) { best_final = replay.trenchLength; best_index = j; }
    }
    Allocator baseline_replay = control;
    baseline_replay.compactFenwickForDiagnostic();
    for (std::size_t i = stop; i < ops.size(); ++i) {
        if (ops[i] > 0) baseline_replay.place(static_cast<int>(ops[i]));
        else baseline_replay.remove(-ops[i]);
    }
    const std::int64_t baseline_control_replay_trench = baseline_replay.trenchLength;
    if (baseline_control_replay_trench != baseline_final)
        throw std::runtime_error("baseline control suffix replay diverges from the verified trace");
    finalist_trenches.push_back(baseline_control_replay_trench);
    if (baseline_control_replay_trench < best_final) {
        best_final = baseline_control_replay_trench;
        best_is_baseline_control = true;
    }
    std::cout.rdbuf(original_stdout);

    std::ofstream out(output_path);
    out << "{\n  \"scope\": \"offline bounded beam inside one command block; exact frozen allocator policy replays the entire remaining suffix; future data used only for diagnostic beam ranking\",\n";
    out << "  \"input\": \"" << input_path << "\",\n  \"trace\": \"" << trace_path << "\",\n";
    out << "  \"commands\": " << n << ", \"window_start_op_1based\": " << start_op
        << ", \"window_count\": " << window_count << ", \"beam_width\": " << width
        << ", \"action_cap\": " << action_cap << ",\n";
    out << "  \"baseline_final_trench_m\": " << baseline_final << ",\n";
    out << "  \"window_initial_trench_m\": " << initial_trench << ",\n";
    out << "  \"baseline_control_window_final_trench_m\": " << control.trenchLength << ",\n";
    out << "  \"mc_decisions_at_window_start\": " << initial->mcDecisionsUsed << ",\n";
    out << "  \"expanded_states_generated\": " << expanded << ",\n";
    out << "  \"finalist_replay_trench_m\": [";
    for (std::size_t i = 0; i < finalist_trenches.size(); ++i) out << (i ? ", " : "") << finalist_trenches[i];
    out << "],\n  \"best_full_suffix_witness_trench_m\": " << best_final
        << ",\n  \"full_suffix_witness_saving_m\": " << baseline_final - best_final << ",\n";
    out << "  \"best_is_baseline_control\": " << (best_is_baseline_control ? "true" : "false") << ",\n";
    out << "  \"baseline_control_replay_trench_m\": " << baseline_control_replay_trench << ",\n";
    out << "  \"winner_path\": [";
    const auto& path = best_is_baseline_control ? control_path : beam[best_index].path;
    for (std::size_t i = 0; i < path.size(); ++i) {
        out << (i ? ", " : "") << "{\"op\":" << path[i].op_index
            << ",\"digs\":" << path[i].action.digs
            << ",\"start\":" << path[i].action.start << "}";
    }
    out << "]\n}\n";
    std::cerr << "baseline=" << baseline_final << " best=" << best_final
              << " saving=" << baseline_final - best_final << " expanded=" << expanded
              << " finalists=" << beam.size() << " winner=" << best_index << '\n';
    return 0;
}
