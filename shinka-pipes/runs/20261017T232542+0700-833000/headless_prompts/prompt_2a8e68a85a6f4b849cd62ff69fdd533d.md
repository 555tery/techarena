# System Instructions

Improve a causal online dynamic storage allocator in self-contained C++20.
Propose a patch in your response; do not edit files or launch experiments yourself.
Change only EVOLVE-BLOCK regions. Preserve stdin/stdout protocol and immediate flush.
Positive commands insert length 1..40; negative commands delete a PID; 0 exits.
Existing pipes cannot move. Trench grows in sections of 20 and never shrinks.
Use only past observations; no future input, raw test inspection, test fingerprints,
filesystem access, network, subprocesses, or external data in the candidate.
Do not inspect other project results or holdout data. Use supplied code and feedback.
Every case must satisfy 5 seconds solver CPU and 256 MiB RSS.
Fitness uses the frozen SYNTHETIC SEARCH split only. For each trace calculate
B/T, where B=20*ceil(peak_live_volume/20) and T is actual trench length.
Average over cases within each family, then give every family equal weight.
Fitness lies in [0,1]; B is a lower bound, not necessarily an achievable optimum.
Re-evaluate baseline fitness on this same corpus at the start of each run.
Validation and Open15 are excluded from fitness, selection and your feedback.
Do not inspect their files or results. Generalization is not established by search gains.
State the allocator hypothesis behind the change; avoid case-specific hardcoding.

You MUST respond using an edit name, description, and the exact SEARCH/REPLACE diff format shown below to indicate changes:

<NAME>
A shortened name summarizing the edit you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the edit you are proposing.
</DESCRIPTION>

<DIFF>
<<<<<<< SEARCH
# Original code to find and replace (must match exactly including indentation)
=======
# New replacement code
>>>>>>> REPLACE

</DIFF>


Example of a valid diff format:
<DIFF>
<<<<<<< SEARCH
for i in range(m):
    for j in range(p):
        for k in range(n):
            C[i, j] += A[i, k] * B[k, j]
=======
# Reorder loops for better memory access pattern
for i in range(m):
    for k in range(n):
        for j in range(p):
            C[i, j] += A[i, k] * B[k, j]
>>>>>>> REPLACE

</DIFF>

* You may only modify text that lies below a line containing "EVOLVE-BLOCK-START" and above the next "EVOLVE-BLOCK-END". Everything outside those markers is read-only.
* Do not repeat the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the SEARCH/REPLACE blocks.  
* Every block’s SEARCH section must be copied **verbatim** from the current file, including indentation.
* You can propose multiple independent edits. SEARCH/REPLACE blocks follow one after another. DO NOT ADD ANY OTHER TEXT BETWEEN THESE BLOCKS.
* Make sure the file still runs after your changes.

# Previous Messages

[]

# User Request

Here are the performance metrics of a set of previously implemented programs:

# Prior programs

```cpp
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

// EVOLVE-BLOCK-START
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

int predictNextGeometricSize(const std::deque<int>& history, int currentLength) {
    if (history.empty() || history.back() != currentLength) return 0;
    auto it = history.rbegin();
    std::array<int, 3> runSizes{};
    std::array<std::size_t, 3> runCounts{};
    std::size_t runIndex = 0;
    while (it != history.rend() && runIndex < runSizes.size()) {
        const int size = *it;
        std::size_t count = 0;
        while (it != history.rend() && *it == size) {
            ++count;
            ++it;
        }
        runSizes[runIndex] = size;
        runCounts[runIndex] = count;
        ++runIndex;
    }
    if (runIndex < runSizes.size() || runSizes[0] != currentLength ||
        runCounts[0] < kSameLengthRightRun ||
        runCounts[1] < kSameLengthRightRun ||
        runCounts[2] < kSameLengthRightRun) {
        return 0;
    }
    const int previous = runSizes[1];
    const int beforePrevious = runSizes[2];
    if (!(beforePrevious < previous && previous < currentLength)) return 0;
    const int observed = currentLength * beforePrevious;
    const int expected = previous * previous;
    const int error = observed > expected ? observed - expected : expected - observed;
    if (2 * error > beforePrevious) return 0;
    const int predicted = (currentLength * previous + beforePrevious / 2) /
        beforePrevious;
    if (predicted <= currentLength || predicted > 40) return 0;
    return predicted;
}

bool trendAlignedHighSide(const std::deque<int>& history, int currentLength,
                          std::int64_t gapStart, std::int64_t gapEnd,
                          bool fallbackHighSide) {
    const int predictedLength = predictNextGeometricSize(history, currentLength);
    if (predictedLength <= currentLength || gapEnd - gapStart <= currentLength) {
        return fallbackHighSide;
    }
    const std::int64_t modulus = predictedLength;
    const auto alignmentDistance = [modulus](std::int64_t coordinate) {
        const std::int64_t residue = coordinate % modulus;
        return std::min(residue, modulus - residue);
    };
    const std::int64_t lowRemainderStart = gapStart + currentLength;
    const std::int64_t highRemainderStart = gapStart;
    const std::int64_t lowScore = alignmentDistance(lowRemainderStart);
    const std::int64_t highScore = alignmentDistance(highRemainderStart);
    if (highScore != lowScore) return highScore < lowScore;
    return fallbackHighSide;
}

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
        const bool sameSizeRun = hasSameLengthRecentRun(length);
        const bool geometricLaneActive = !runLeftDisabledBySmoothTrend && sameSizeRun;
        const bool rearmReverse = runLeftDisabledBySmoothTrend && sameSizeRun &&
            alternatingDeleteMode;
        const bool runLeftActive = geometricLaneActive || rearmReverse;
        // Once a long same-size placement run is observable, proactively split
        // new IDs into two edge lanes. This is deletion-oblivious: it does not
        // infer a future deletion PID parity. If either lane is later removed,
        // its pipes are spatially clustered rather than interleaved with the other.
        const bool highSide = runLeftActive
            ? (rearmReverse ? sizeCohort == 0 : (nextPid & 1) == 0)
            : (alternatingDeleteMode
                ? ((nextPid & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        std::int64_t start = -1;
        const auto gapStart = bestGap(length, highSide, sizeCohort);
        if (gapStart.has_value()) {
            const auto it = gaps.find(*gapStart);
            const bool selectedHighSide = geometricLaneActive
                ? trendAlignedHighSide(recentLengths, length, it->first,
                                       it->second.end, highSide)
                : highSide;
            const int cohort = it->second.cohort;
            start = placementStart(it->second, *gapStart, length, selectedHighSide);
            splitGap(*gapStart, length, selectedHighSide);
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

class Allocator {
public:
    // Free spans are half-open [start, end). The map supports merging after a
    // removal; the set chooses the shortest fitting span, then the lowest start.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::map<std::int64_t, int> activeByEnd;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::map<std::int64_t, int> gapCohort;
    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySizeShared;
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;
    std::deque<std::pair<int, int>> completedPlacementRuns;
    int observedRunLength = -1;
    int observedRunCount = 0;
    bool cohortSlabActive = false;
    bool cohortSlabExpanded = false;
    int cohortSlabExpectedCount = 0;
    int cohortSlabDeleteParity = 0;
    int cohortSlabDeleteCount = 0;
    int cohortSlabDeletedUsed = 0;
    int cohortSlabSurvivorUsed = 0;
    int cohortSlabGapSinkRemaining = 0;
    int cohortSlabTailPipeCount = 0;
    int cohortSlabUsed = 0;
    std::int64_t cohortSlabBase = 0;
    std::int64_t cohortSlabEnd = 0;
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
    std::deque<int> recentDeleteRanksPermille;
    bool lifoLaneDisabledForScale = false;
    int activeRunFirstPid = 1;
    std::array<std::size_t, 2> activeRunDeleteParityCount{};
    int lastCompletedDeleteRelativeParity = -1;
    int previousCompletedDeleteRelativeParity = -1;

    bool hasLongAdditiveSizeTrend(int currentLength) const {
        constexpr int kMinimumRun = 46;
        if (currentLength < 3 || currentLength >= 40 ||
            observedRunCount < kMinimumRun) return false;

        std::array<int, 3> sizes{currentLength, 0, 0};
        std::array<int, 3> counts{observedRunCount, 0, 0};
        auto it = recentLengths.rbegin();
        const auto end = recentLengths.rend();

        // recentLengths is updated after each placement, so its suffix may
        // contain earlier members of the current run. observedRunCount already
        // counts those placements; skip them to avoid double counting.
        while (it != end && *it == currentLength) ++it;

        for (std::size_t run = 1; run < sizes.size(); ++run) {
            if (it == end) return false;
            const int size = *it;
            sizes[run] = size;
            while (it != end && *it == size) {
                ++counts[run];
                ++it;
            }
            if (counts[run] < kMinimumRun) return false;
        }

        return sizes[0] == sizes[1] + 1 && sizes[1] == sizes[2] + 1;
    }

    bool alignForNextAdditiveSize(int length, std::int64_t gapStart,
                                  bool fallbackHighSide) const {
        const std::int64_t modulus = static_cast<std::int64_t>(length + 1);
        const auto distance = [modulus](std::int64_t coordinate) {
            const std::int64_t residue = coordinate % modulus;
            return std::min(residue, modulus - residue);
        };
        // Low-side placement leaves the remainder starting after this pipe;
        // high-side placement leaves it at the original gap start.
        const std::int64_t lowScore = distance(gapStart + length);
        const std::int64_t highScore = distance(gapStart);
        if (highScore != lowScore) return highScore < lowScore;
        return fallbackHighSide;
    }

    int predictEarlyNextGeometricSize(int currentLength) const {
        if (completedPlacementRuns.size() != 1 || observedRunCount < 46 ||
            observedRunCount > 1024 || !alternatingDeleteMode ||
            strideTwoDeleteTransitions < 7 || activePipeCount > 4096 ||
            freeByStart.size() > 4096) {
            return 0;
        }
        const auto previous = completedPlacementRuns.back();
        if (previous.second < 46 || previous.first <= 0 ||
            lastDeletedLength != previous.first ||
            currentLength != previous.first * 2 || currentLength > 20) {
            return 0;
        }
        const int predicted = currentLength * 2;
        return predicted <= 40 ? predicted : 0;
    }

    bool hasLifoDeletionConfidence() const {
        if (activePipeCount < 128 || recentDeleteRanksPermille.size() < 48) return false;
        std::size_t topFivePercent = 0;
        for (int rank : recentDeleteRanksPermille) {
            if (rank <= 50) ++topFivePercent;
        }
        if (topFivePercent * 100 < recentDeleteRanksPermille.size() * 80) return false;
        std::size_t shortPlacements = 0;
        for (int length : recentLengths) {
            if (length <= 8) ++shortPlacements;
        }
        return recentLengths.size() >= 64 &&
            shortPlacements * 100 >= recentLengths.size() * 90;
    }

    bool hasYoungTailNeighbor(std::int64_t tailStart) const {
        const auto it = activeByEnd.find(tailStart);
        return it != activeByEnd.end() && rankFromNewestPermille(it->second) <= 50;
    }

    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;

    bool unitDominantRecentProfile() const {
        if (recentLengths.size() < 128) return false;
        const std::size_t window = std::min<std::size_t>(recentLengths.size(), 2048);
        std::size_t units = 0;
        auto it = recentLengths.rbegin();
        for (std::size_t seen = 0; seen < window; ++seen, ++it) {
            if (*it == 1) ++units;
        }
        return units * 100 >= window * 85;
    }

    bool useLifoStackLane(int currentLength) const {
        if (lifoLaneDisabledForScale || activePipeCount < 128 ||
            currentLength > 8 || recentDeleteRanksPermille.size() < 48) return false;
        std::size_t topFivePercent = 0;
        for (int rank : recentDeleteRanksPermille) {
            if (rank <= 50) ++topFivePercent;
        }
        if (topFivePercent * 100 < recentDeleteRanksPermille.size() * 80) return false;
        std::size_t shortPlacements = 0;
        for (int length : recentLengths) {
            if (length <= 8) ++shortPlacements;
        }
        return recentLengths.size() >= 64 &&
            shortPlacements * 100 >= recentLengths.size() * 90;
    }

    void place(int length) {
        if (observedRunLength != length) {
            if (observedRunCount > 0) {
                completedPlacementRuns.emplace_back(observedRunLength, observedRunCount);
                if (completedPlacementRuns.size() > 8) completedPlacementRuns.pop_front();
                const std::size_t totalRemoved = activeRunDeleteParityCount[0] +
                    activeRunDeleteParityCount[1];
                const std::size_t dominant = std::max(activeRunDeleteParityCount[0],
                                                       activeRunDeleteParityCount[1]);
                if (totalRemoved >= 8 && dominant * 100 >= totalRemoved * 85) {
                    const int absoluteParity = activeRunDeleteParityCount[0] >
                        activeRunDeleteParityCount[1] ? 0 : 1;
                    previousCompletedDeleteRelativeParity =
                        lastCompletedDeleteRelativeParity;
                    lastCompletedDeleteRelativeParity = absoluteParity ^
                        (activeRunFirstPid & 1);
                } else {
                    previousCompletedDeleteRelativeParity = -1;
                    lastCompletedDeleteRelativeParity = -1;
                }
            }
            observedRunLength = length;
            observedRunCount = 0;
            activeRunFirstPid = static_cast<int>(pipes.size());
            activeRunDeleteParityCount = {};
            cohortSlabActive = false;
            beginCohortSlab(length);
        }
        ++observedRunCount;
        const int sizeCohort = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
        if (activePipeCount > kMcMaxActivePipes) lifoLaneDisabledForScale = true;
        const bool lifoStackLane = length > kRightEdgeMaxPipeLength &&
            useLifoStackLane(length);

        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {
            const int pid = static_cast<int>(pipes.size());
            const bool predictedDeleted = (pid & 1) == cohortSlabDeleteParity;
            std::int64_t start = -1;
            bool tailPlacement = true;
            if (!predictedDeleted && cohortSlabGapSinkRemaining > 0) {
                StartIter reusableGap = bestFittingGapBefore(
                    length, false, sizeCohort, cohortSlabBase);
                if (reusableGap != freeByStart.end()) {
                    start = consumeAtSide(reusableGap, length, false);
                    --cohortSlabGapSinkRemaining;
                    tailPlacement = false;
                }
            }
            if (tailPlacement) {
                if (predictedDeleted) {
                    start = cohortSlabBase +
                        static_cast<std::int64_t>(cohortSlabDeletedUsed) * length;
                    ++cohortSlabDeletedUsed;
                } else {
                    start = cohortSlabBase +
                        static_cast<std::int64_t>(cohortSlabDeleteCount +
                                                  cohortSlabSurvivorUsed) * length;
                    ++cohortSlabSurvivorUsed;
                }
            }

            std::int64_t digs = 0;
            if (tailPlacement && !cohortSlabExpanded) {
                const std::int64_t missing = cohortSlabEnd - trenchLength;
                digs = missing > 0
                    ? (missing + kDigLength - 1) / kDigLength : 0;
                trenchLength += digs * kDigLength;
                cohortSlabExpanded = true;
                const std::int64_t occupiedEnd = cohortSlabBase +
                    static_cast<std::int64_t>(cohortSlabTailPipeCount) * length;
                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);
            }
            printPlacement(digs, start);
            pipes.push_back(Pipe{start, length, true, sizeCohort});
            activeByEnd.emplace(start + length, pid);
            fenwickAdd(pid, 1);
            ++activePipeCount;
            ++lengthOccurrenceCount[static_cast<std::size_t>(length)];
            recordLength(length);
            recordObservation(Observation{1, length});
            ++cohortSlabUsed;
            if (cohortSlabUsed >= cohortSlabExpectedCount) cohortSlabActive = false;
            return;
        }

        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool sameSizeRun = hasSameLengthRecentRun(length);
        const bool geometricLaneActive = !runLeftDisabledBySmoothTrend && sameSizeRun;
        const bool rearmReverse = runLeftDisabledBySmoothTrend && sameSizeRun &&
            alternatingDeleteMode;
        const bool runLeftActive = geometricLaneActive || rearmReverse;
        // Add a narrowly gated endpoint choice on top of the staircase
        // candidate: after three long exact +1 runs, align the remaining gap
        // with the predicted next size L+1. This does not alter cohort routing.
        const bool additiveNextAlignment = hasLongAdditiveSizeTrend(length);
        // Split an observed long same-size run into two edge lanes without
        // relying on a learned deletion pattern or any future command.
        bool highSide = lifoStackLane || (runLeftActive
            ? (rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)))));
        std::int64_t start = -1;
        const int predictedNextClass = predictEarlyNextGeometricSize(length);
        auto gap = bestFittingGap(length, highSide, sizeCohort);
        bool counterfactualCapacityChoice = false;
        if (predictedNextClass > length &&
            ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)) {
            const auto projectedChoice = chooseCounterfactualCapacityGap(
                length, predictedNextClass, highSide, sizeCohort, gap);
            if (projectedChoice.first != freeByStart.end()) {
                gap = projectedChoice.first;
                highSide = projectedChoice.second;
                counterfactualCapacityChoice = true;
            }
        }
        if (gap != freeByStart.end()) {
            if (additiveNextAlignment) {
                highSide = alignForNextAdditiveSize(length, gap->first, highSide);
            } else if (geometricLaneActive) {
                highSide = trendAlignedHighSide(recentLengths, length,
                                                gap->first, gap->second, highSide);
            }
            if (lifoStackLane) highSide = true;
            // The rollout does not model the L+1 endpoint objective, so do not
            // let it override this causally triggered action.
            const std::int64_t selectedStart = (additiveNextAlignment ||
                counterfactualCapacityChoice)
                ? gap->first
                : chooseGapWithRollout(length, highSide, sizeCohort, gap);
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
            const bool baseOffsetGate = digs > 0 && activePipeCount > 4096 &&
                !preserveForeignTail && newLength - (tailStart + length) > 0 &&
                hasLifoDeletionConfidence() && hasYoungTailNeighbor(tailStart);
            const bool suppressForUnitProfile =
                baseOffsetGate && unitDominantRecentProfile();
            const bool offsetGate = baseOffsetGate && !suppressForUnitProfile;
            if (suppressForUnitProfile) ++unitProfileSuppressedExpansions;
            if (digs > 0) ++expansionGateOpportunities;
            if (offsetGate) ++expansionGatePasses;
            if (tail != freeByStart.end() && !preserveForeignTail) eraseGap(tail);
            trenchLength = newLength;
            if ((parityCohortMode && highSide && !preserveForeignTail) || offsetGate) {
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
        activeByEnd.emplace(start + length, pid);
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
        activeByEnd.erase(pipe.start + pipe.length);
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        fenwickAdd(static_cast<int>(index), -1);
        --activePipeCount;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
        recordDeletionPattern(static_cast<int>(index), pipe.length);
        if (static_cast<int>(index) >= activeRunFirstPid) {
            ++activeRunDeleteParityCount[static_cast<std::size_t>(
                static_cast<int>(index) & 1)];
        }
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

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    void fenwickAdd(int index, int delta) {
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

    void beginCohortSlab(int length) {
#ifdef TRACE_COHORT_SLAB
        std::cerr << "COHORT_CHECK len=" << length
                  << " prior_runs=" << completedPlacementRuns.size()
                  << " alternating=" << alternatingDeleteMode
                  << " last_delete_length=" << lastDeletedLength << '\n';
#endif
        if (completedPlacementRuns.size() < 2 || !alternatingDeleteMode) return;
        const auto previous = completedPlacementRuns[completedPlacementRuns.size() - 2];
        const auto last = completedPlacementRuns.back();
        if (!(previous.first < last.first && last.first < length) ||
            lastDeletedLength != last.first) return;

        // An observed increasing size regime may have a larger class ahead.
        // Keep the predicted deletion cohort together so its released span
        // remains useful to later, larger requests. The next-size estimate
        // only guards against partitioning the terminal legal size band.
        const int nextStep = length - last.first;
        const int predictedNextSize = length + nextStep;
        if (predictedNextSize > 40) return;
        const bool unitStaircase =
            last.first - previous.first == nextStep && nextStep == 1;

        const int countDifference = std::abs(previous.second - last.second);
        const int stableTolerance =
            std::max(10, std::max(previous.second, last.second) / 10);
        if (countDifference > stableTolerance) return;
        const int expectedCount = (previous.second + last.second) / 2;
        if (expectedCount < 64) return;

        int slabDeleteParity = predictedDeletedParity;
        if (lastCompletedDeleteRelativeParity >= 0 &&
            previousCompletedDeleteRelativeParity ==
                lastCompletedDeleteRelativeParity) {
            slabDeleteParity = (activeRunFirstPid & 1) ^
                lastCompletedDeleteRelativeParity;
        }

        const int firstPid = static_cast<int>(pipes.size());
        const int firstParity = firstPid & 1;
        const int deleteCount = expectedCount / 2 +
            ((expectedCount & 1) != 0 && firstParity == slabDeleteParity ? 1 : 0);
        const int survivorCount = expectedCount - deleteCount;
        const int firstOccurrenceParity = static_cast<int>(
            lengthOccurrenceCount[static_cast<std::size_t>(length)] & 1);
        const int firstPidParity = firstPid & 1;
        const int survivorSizeCohort = firstOccurrenceParity ^
            (firstPidParity == slabDeleteParity ? 1 : 0);
        std::int64_t reusableCapacity = 0;
        for (const auto& [gapStart, gapEnd] : freeByStart) {
            if (parityCohortMode) {
                const int owner = gapCohort.at(gapStart);
                if (owner >= 0 && owner != survivorSizeCohort) continue;
            }
            const std::int64_t gapCapacity = (gapEnd - gapStart) / length;
            reusableCapacity = std::min<std::int64_t>(
                survivorCount, reusableCapacity + gapCapacity);
            if (reusableCapacity >= survivorCount) break;
        }
        const int survivorGapCount = static_cast<int>(reusableCapacity);
        const int tailPipeCount = expectedCount - survivorGapCount;
        const std::int64_t predictedFutureCapacity =
            static_cast<std::int64_t>(deleteCount) * length / predictedNextSize;
        if (predictedFutureCapacity < 64) {
            // A unit staircase can still make a useful cohort slab when its
            // deleted half would recover more next-class capacity than the
            // compatible gaps already present. This avoids the broad
            // per-transition reservation that regressed earlier screens.
            if (!unitStaircase) return;
            std::int64_t existingFutureCapacity = 0;
            for (const auto& [gapStart, gapEnd] : freeByStart) {
                if (parityCohortMode) {
                    const int owner = gapCohort.at(gapStart);
                    if (owner >= 0 && owner != 0) continue;
                }
                existingFutureCapacity += (gapEnd - gapStart) / predictedNextSize;
            }
            if (predictedFutureCapacity <= existingFutureCapacity) return;
        }
        const std::int64_t rawLength = static_cast<std::int64_t>(tailPipeCount) * length;
        const std::int64_t allocatedLength =
            ((rawLength + kDigLength - 1) / kDigLength) * kDigLength;

        cohortSlabActive = true;
        cohortSlabExpanded = false;
        cohortSlabExpectedCount = expectedCount;
        cohortSlabDeleteParity = slabDeleteParity;
        cohortSlabDeleteCount = deleteCount;
        cohortSlabDeletedUsed = 0;
        cohortSlabSurvivorUsed = 0;
        cohortSlabGapSinkRemaining = survivorGapCount;
        cohortSlabTailPipeCount = tailPipeCount;
        cohortSlabUsed = 0;
        cohortSlabBase = trenchLength;
        cohortSlabEnd = cohortSlabBase + allocatedLength;
#ifdef TRACE_COHORT_SLAB
        std::cerr << "COHORT_START len=" << length
                  << " expected=" << expectedCount
                  << " delete_parity=" << cohortSlabDeleteParity
                  << " slots_deleted=" << deleteCount
                  << " base=" << cohortSlabBase
                  << " end=" << cohortSlabEnd << '\n';
#endif
    }

    void recordObservation(const Observation& event) {
        observedHistory.push_back(event);
        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();
        if (event.kind < 0) {
            recentDeleteRanksPermille.push_back(event.value);
            if (recentDeleteRanksPermille.size() > 64) recentDeleteRanksPermille.pop_front();
        }
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

    StartIter bestFittingGapBefore(
        int length, bool highSide, int sizeCohort, std::int64_t endLimit) {
        StartIter best = freeByStart.end();
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {
            if (it->second > endLimit || it->second - it->first < length) continue;
            if (parityCohortMode) {
                const int owner = gapCohort.at(it->first);
                if (owner >= 0 && owner != sizeCohort) continue;
            }
            const std::int64_t score = scoreGap(it->second - it->first, length);
            if (score < bestScore ||
                (score == bestScore && best != freeByStart.end() &&
                 ((highSide && it->first > best->first) ||
                  (!highSide && it->first < best->first)))) {
                bestScore = score;
                best = it;
            }
        }
        return best;
    }

    using ProjectedObstacle = std::pair<std::int64_t, std::int64_t>;

    std::int64_t projectedNextClassCapacity(
        const std::vector<ProjectedObstacle>& obstacles,
        std::int64_t candidateStart, int length, int nextLength) const {
        if (candidateStart < 0 || nextLength <= 0) return -1;
        const auto right = std::lower_bound(
            obstacles.begin(), obstacles.end(), candidateStart,
            [](const ProjectedObstacle& obstacle, std::int64_t coordinate) {
                return obstacle.first < coordinate;
            });
        const std::int64_t leftEnd = right == obstacles.begin()
            ? 0 : std::prev(right)->second;
        const std::int64_t rightStart = right == obstacles.end()
            ? trenchLength : right->first;
        if (leftEnd > candidateStart || rightStart < candidateStart + length) return -1;
        return (candidateStart - leftEnd) / nextLength +
            (rightStart - candidateStart - length) / nextLength;
    }

    std::pair<StartIter, bool> chooseCounterfactualCapacityGap(
        int length, int nextLength, bool fallbackHighSide, int sizeCohort,
        StartIter baselineGap) {
        if (activePipeCount > 4096 || freeByStart.size() > 4096) {
            return {freeByStart.end(), fallbackHighSide};
        }
        std::vector<ProjectedObstacle> obstacles;
        obstacles.reserve(activePipeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            const Pipe& pipe = pipes[pid];
            if (!pipe.active ||
                (pipe.length == length &&
                 (static_cast<int>(pid) & 1) == predictedDeletedParity)) {
                continue;
            }
            obstacles.emplace_back(pipe.start, pipe.start + pipe.length);
        }
        std::sort(obstacles.begin(), obstacles.end());
        const std::int64_t baselineStart = baselineGap == freeByStart.end()
            ? -1 : (fallbackHighSide ? baselineGap->second - length : baselineGap->first);
        const std::int64_t baselineCapacity = projectedNextClassCapacity(
            obstacles, baselineStart, length, nextLength);

        StartIter best = freeByStart.end();
        bool bestHighSide = fallbackHighSide;
        std::int64_t bestStart = -1;
        std::int64_t bestCapacity = -1;
        std::int64_t bestBaseScore = std::numeric_limits<std::int64_t>::max();
        const StartIter tail = tailGap();
        auto search = [&](int ownerMode) {
            for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {
                const std::int64_t gapLength = it->second - it->first;
                const int owner = gapCohort.at(it->first);
                if (gapLength < length || (tail != freeByStart.end() && it == tail) ||
                    (ownerMode == 1 && owner != sizeCohort) ||
                    (ownerMode == 2 && owner >= 0)) {
                    continue;
                }
                const std::int64_t baseScore = scoreGap(gapLength, length);
                for (int side = 0; side < 2; ++side) {
                    const bool high = side != 0;
                    const std::int64_t candidateStart = high
                        ? it->second - length : it->first;
                    const std::int64_t capacity = projectedNextClassCapacity(
                        obstacles, candidateStart, length, nextLength);
                    if (capacity < 0) continue;
                    const bool tieSidePreferred = high == fallbackHighSide;
                    const bool bestTieSidePreferred = bestHighSide == fallbackHighSide;
                    const bool addressPreferred = best != freeByStart.end() &&
                        ((high && candidateStart > bestStart) ||
                         (!high && candidateStart < bestStart));
                    if (capacity > bestCapacity ||
                        (capacity == bestCapacity && baseScore < bestBaseScore) ||
                        (capacity == bestCapacity && baseScore == bestBaseScore &&
                         tieSidePreferred && !bestTieSidePreferred) ||
                        (capacity == bestCapacity && baseScore == bestBaseScore &&
                         tieSidePreferred == bestTieSidePreferred && addressPreferred)) {
                        best = it;
                        bestHighSide = high;
                        bestStart = candidateStart;
                        bestCapacity = capacity;
                        bestBaseScore = baseScore;
                    }
                }
            }
        };
        if (parityCohortMode) {
            search(1);
            if (best == freeByStart.end()) search(2);
        } else {
            search(0);
        }
        if (best == freeByStart.end() || bestCapacity <= baselineCapacity) {
            return {freeByStart.end(), fallbackHighSide};
        }
        return {best, bestHighSide};
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

// EVOLVE-BLOCK-END

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun
                      << " expansion_gate_opportunities=" << allocator.expansionGateOpportunities
                      << " expansion_gate_passes=" << allocator.expansionGatePasses
                      << " unit_profile_suppressed_expansions="
                      << allocator.unitProfileSuppressedExpansions << '\n';
#endif
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

```

Performance metrics:
Combined score to maximize: 0.91
valid_cases: 32; family_count: 16; worst_family_score: 0.77; mean_raw_kpi: 0.53; max_solver_cpu_seconds: 1.30; max_solver_rss_mib: 7.98

Text feedback:
case=s001_uniform_churn family=uniform_churn normalized=0.889182058 trench=7580 bound=6740 cpu_s=0.111619 rss_mib=3.344
case=s002_uniform_churn family=uniform_churn normalized=0.825396825 trench=3780 bound=3120 cpu_s=0.409676 rss_mib=3.766
case=s003_short_heavy family=short_heavy normalized=0.842105263 trench=1520 bound=1280 cpu_s=0.102068 rss_mib=3.344
case=s004_short_heavy family=short_heavy normalized=0.888888889 trench=360 bound=320 cpu_s=0.416143 rss_mib=3.328
case=s005_long_heavy family=long_heavy normalized=0.913043478 trench=4600 bound=4200 cpu_s=0.130809 rss_mib=2.953
case=s006_long_heavy family=long_heavy normalized=0.842857143 trench=1400 bound=1180 cpu_s=0.428543 rss_mib=3.656
case=s007_bimodal family=bimodal normalized=0.943231441 trench=4580 bound=4320 cpu_s=0.096425 rss_mib=3.188
case=s008_bimodal family=bimodal normalized=0.958432871 trench=41860 bound=40120 cpu_s=0.433222 rss_mib=3.859
case=s009_section_boundaries family=section_boundaries normalized=0.966666667 trench=600 bound=580 cpu_s=0.091544 rss_mib=3.234
case=s010_section_boundaries family=section_boundaries normalized=0.953669537 trench=48780 bound=46520 cpu_s=0.437264 rss_mib=5.047
case=s011_fifo family=fifo normalized=0.998623222 trench=43580 bound=43520 cpu_s=0.100922 rss_mib=3.422
case=s012_fifo family=fifo normalized=0.933333333 trench=600 bound=560 cpu_s=0.398978 rss_mib=3.375
case=s013_lifo family=lifo normalized=0.972972973 trench=740 bound=720 cpu_s=0.094434 rss_mib=3.203
case=s014_lifo family=lifo normalized=1.000000000 trench=840 bound=840 cpu_s=0.410362 rss_mib=3.016
case=s015_size_lifetimes family=size_lifetimes normalized=0.958333333 trench=960 bound=920 cpu_s=0.108904 rss_mib=3.234
case=s016_size_lifetimes family=size_lifetimes normalized=0.947750363 trench=27560 bound=26120 cpu_s=0.516238 rss_mib=3.531
case=s017_burst_drain family=burst_drain normalized=0.979166667 trench=3840 bound=3760 cpu_s=0.112517 rss_mib=3.000
case=s018_burst_drain family=burst_drain normalized=1.000000000 trench=55920 bound=55920 cpu_s=0.467757 rss_mib=3.469
case=s019_distribution_switch family=distribution_switch normalized=0.896551724 trench=580 bound=520 cpu_s=0.097864 rss_mib=3.203
case=s020_distribution_switch family=distribution_switch normalized=0.894736842 trench=1140 bound=1020 cpu_s=0.387471 rss_mib=4.094
case=s021_drifting_sizes family=drifting_sizes normalized=0.787234043 trench=940 bound=740 cpu_s=0.115430 rss_mib=2.688
case=s022_drifting_sizes family=drifting_sizes normalized=0.878121878 trench=20020 bound=17580 cpu_s=0.508526 rss_mib=3.094
case=s023_striped_recycling family=striped_recycling normalized=0.999792982 trench=193220 bound=193180 cpu_s=0.106531 rss_mib=3.875
case=s024_striped_recycling family=striped_recycling normalized=0.999948312 trench=773880 bound=773840 cpu_s=0.435467 rss_mib=6.062
case=s025_geometric_cohorts family=geometric_cohorts normalized=0.819095477 trench=3980 bound=3260 cpu_s=0.114159 rss_mib=2.578
case=s026_geometric_cohorts family=geometric_cohorts normalized=0.975609756 trench=820 bound=800 cpu_s=0.375611 rss_mib=4.328
case=s027_additive_cohorts family=additive_cohorts normalized=0.809061489 trench=6180 bound=5000 cpu_s=0.126620 rss_mib=2.844
case=s028_additive_cohorts family=additive_cohorts normalized=0.923076923 trench=780 bound=720 cpu_s=0.393141 rss_mib=3.688
case=s029_large_live_set family=large_live_set normalized=0.967536006 trench=256900 bound=248560 cpu_s=1.301224 rss_mib=6.078
case=s030_large_live_set family=large_live_set normalized=0.967443667 trench=257400 bound=249020 cpu_s=1.236118 rss_mib=7.984
case=s031_size_biased_deletion family=size_biased_deletion normalized=0.773809524 trench=1680 bound=1300 cpu_s=0.109043 rss_mib=2.969
case=s032_size_biased_deletion family=size_biased_deletion normalized=0.773809524 trench=1680 bound=1300 cpu_s=0.430428 rss_mib=3.391

```cpp
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

// EVOLVE-BLOCK-START
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes still-live pipes, so long-lived survivors contribute
// evidence without requiring their eventual deletion.
struct Rate {
    int live = 0;
    double exposure = 0.0;
    double deaths = 0.0;
    std::uint64_t stamp = 0;
    double exposureAt(std::uint64_t now) const {
        return exposure +
            static_cast<double>(now - stamp) * static_cast<double>(live);
    }
    void touch(std::uint64_t now) {
        exposure = exposureAt(now);
        stamp = now;
    }
    void change(std::uint64_t now, int delta, bool removed) {
        touch(now);
        live += delta;
        if (removed) deaths += 1.0;
    }
    void forget(std::uint64_t now) {
        touch(now);
        exposure *= 0.5;
        deaths *= 0.5;
    }
};
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    double score = std::numeric_limits<double>::infinity();
};
class Allocator {
public:
    // Preserve the optional diagnostics interface used outside the block.
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        beginCommand();
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        if (lastPlacementLength_ != length) {
            lastPlacementLength_ = length;
            runOrdinal_ = 0;
        }
        const int runPhase = static_cast<int>(runOrdinal_ & 7U);
        ++runOrdinal_;
        observeLength(length);
        refreshModel(newlyObservedLength);
        const int pid = static_cast<int>(pipes_.size());
        const int globalPhase = pid & 7;
        const double deletionProbability =
            predictDeletion(length, globalPhase, runPhase);
        const int group = classify(deletionProbability);
        peakLiveVolume_ = std::max(
            peakLiveVolume_, liveVolume_ + static_cast<Coordinate>(length));
        // An already available tail can become a two-front arena without
        // requesting any additional excavation.
        if (!arenaActive_ && canSeparate(deletionProbability)) {
            const auto tail = tailGap();
            if (tail != gaps_.end() &&
                tail->second.end - tail->first >= 2LL * length) {
                arenaActive_ = true;
                arenaStart_ = tail->first;
                arenaEnd_ = trenchLength_;
            }
        }
        Choice choice;
        Coordinate digs = 0;
        const auto firstFit = bySize_.lower_bound({length, 0});
        if (firstFit != bySize_.end()) {
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            digs = growFor(length, deletionProbability, choice);
        }
        const auto selected = gaps_.find(choice.gapStart);
        const Coordinate gapStart = selected->first;
        const Gap gap = selected->second;
        eraseGap(selected);
        Pipe pipe;
        pipe.start = choice.start;
        pipe.length = length;
        pipe.previous = gap.left;
        pipe.next = gap.right;
        pipe.runPhase = static_cast<unsigned char>(runPhase);
        pipe.group = static_cast<unsigned char>(group);
        pipe.active = true;
        pipes_.push_back(pipe);
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(gapStart, pipe.start, gap.left, pid);
        insertGap(pipe.start + length, gap.end, pid, gap.right);
        changePopulation(length, globalPhase, runPhase, 1, false);
        ++liveGroups_[static_cast<std::size_t>(group)];
        liveVolume_ += length;
        std::cout << digs << ' ' << pipe.start << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const int pid = static_cast<int>(pidValue);
        if (!pipes_[static_cast<std::size_t>(pid)].active) {
            printInvalidPid();
            return;
        }
        beginCommand();
        const Pipe pipe = pipes_[static_cast<std::size_t>(pid)];
        if (pipe.previous != 0) {
            pipes_[pipe.previous].next = pipe.next;
        }
        if (pipe.next != 0) {
            pipes_[pipe.next].previous = pipe.previous;
        } else {
            tailPid_ = pipe.previous;
        }
        Coordinate start = pipe.start;
        Coordinate end = pipe.start + pipe.length;
        auto right = gaps_.lower_bound(start);
        if (right != gaps_.begin()) {
            const auto left = std::prev(right);
            if (left->second.end == start) {
                start = left->first;
                eraseGap(left);
            }
        }
        right = gaps_.lower_bound(end);
        if (right != gaps_.end() && right->first == end) {
            end = right->second.end;
            eraseGap(right);
        }
        pipes_[static_cast<std::size_t>(pid)].active = false;
        insertGap(start, end, pipe.previous, pipe.next);
        changePopulation(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase), -1, true);
        --liveGroups_[static_cast<std::size_t>(pipe.group)];
        liveVolume_ -= pipe.length;
        if (totalRate_.live == 0) arenaActive_ = false;
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    GapMap gaps_;
    std::set<GapKey> bySize_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    int tailPid_ = 0;
    Coordinate trenchLength_ = 0;
    Coordinate liveVolume_ = 0;
    Coordinate peakLiveVolume_ = 0;
    std::array<int, 3> liveGroups_{};
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    int lastPlacementLength_ = -1;
    std::uint64_t runOrdinal_ = 0;
    Rate totalRate_;
    std::array<Rate, 41> lengthRates_{};
    std::array<Rate, kPhaseCount> globalPhaseRates_{};
    std::array<Rate, kPhaseCount> runPhaseRates_{};
    std::array<double, 41> lengthRisk_{};
    std::array<double, kPhaseCount> globalPhaseRisk_{};
    std::array<double, kPhaseCount> runPhaseRisk_{};
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, kPotentialLimit + 1> potential_{};
    bool arenaActive_ = false;
    Coordinate arenaStart_ = 0;
    Coordinate arenaEnd_ = 0;
    static double difference(double a, double b) {
        return a >= b ? a - b : b - a;
    }
    static int classify(double probability) {
        if (probability < 1.0 / 3.0) return 0;
        if (probability > 2.0 / 3.0) return 2;
        return 1;
    }
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
        }
    }
    void changePopulation(
        int length, int globalPhase, int runPhase,
        int delta, bool removed) {
        totalRate_.change(tick_, delta, removed);
        lengthRates_[static_cast<std::size_t>(length)].change(
            tick_, delta, removed);
        globalPhaseRates_[static_cast<std::size_t>(globalPhase)].change(
            tick_, delta, removed);
        runPhaseRates_[static_cast<std::size_t>(runPhase)].change(
            tick_, delta, removed);
    }
    void observeLength(int length) {
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        // Hierarchical smoothing shares evidence between cyclic positions.
        // No deletion pattern is enabled by a fixed sequence of commands.
        for (int residue = 0; residue < kPhaseCount; ++residue) {
            double rate = globalRate;
            for (int period = 2; period <= kPhaseCount; period *= 2) {
                double exposure = 0.0;
                double deaths = 0.0;
                for (int position = residue % period;
                     position < kPhaseCount; position += period) {
                    const Rate& observation =
                        observations[static_cast<std::size_t>(position)];
                    exposure += observation.exposureAt(tick_);
                    deaths += observation.deaths;
                }
                constexpr double priorDeaths = 8.0;
                rate = (deaths + priorDeaths) /
                    (exposure + priorDeaths / rate);
            }
            result[static_cast<std::size_t>(residue)] =
                std::clamp(rate / globalRate, 0.125, 8.0);
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
        for (int length = 1; length <= 40; ++length) {
            const Rate& observation =
                lengthRates_[static_cast<std::size_t>(length)];
            constexpr double priorDeaths = 4.0;
            const double rate =
                (observation.deaths + priorDeaths) /
                (observation.exposureAt(tick_) +
                 priorDeaths / globalRate);
            lengthRisk_[static_cast<std::size_t>(length)] =
                std::clamp(rate / globalRate, 0.0625, 16.0);
        }
        rebuildPhaseRisk(
            globalPhaseRates_, globalRate, globalPhaseRisk_);
        rebuildPhaseRisk(
            runPhaseRates_, globalRate, runPhaseRisk_);
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            probability[index] =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            prefix[index] = prefix[index - 1] + probability[index];
        }
        prefix[40] = 1.0;
        // Renewal reward: at each step, allow up to four observed-distribution
        // requests to find a fitting one, then continue with the remainder.
        potential_[0] = 0.0;
        for (int capacity = 1;
             capacity <= kPotentialLimit; ++capacity) {
            const int maximum = std::min(capacity, 40);
            const double fit = prefix[static_cast<std::size_t>(maximum)];
            const double miss = std::max(0.0, 1.0 - fit);
            const double retryFactor =
                1.0 + miss + miss * miss + miss * miss * miss;
            double reward = 0.0;
            for (int length = 1; length <= maximum; ++length) {
                reward += probability[static_cast<std::size_t>(length)] *
                    (static_cast<double>(length) +
                     potential_[static_cast<std::size_t>(capacity - length)]);
            }
            potential_[static_cast<std::size_t>(capacity)] =
                std::clamp(
                    retryFactor * reward,
                    0.0, static_cast<double>(capacity));
        }
    }
    double predictDeletion(
        int length, int globalPhase, int runPhase) const {
        const double phaseMultiplier = 0.5 * (
            globalPhaseRisk_[static_cast<std::size_t>(globalPhase)] +
            runPhaseRisk_[static_cast<std::size_t>(runPhase)]);
        const double relativeRate = std::clamp(
            lengthRisk_[static_cast<std::size_t>(length)] *
                phaseMultiplier,
            1.0 / 32.0, 32.0);
        // A bounded survival approximation over a typical lifetime horizon.
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
    }
    double utility(Coordinate length) const {
        if (length <= 0) return 0.0;
        if (length <= kPotentialLimit) {
            return potential_[static_cast<std::size_t>(length)];
        }
        return potential_[kPotentialLimit] +
            static_cast<double>(length - kPotentialLimit);
    }
    bool canSeparate(double probability) const {
        return totalRate_.deaths >= 16.0 &&
            liveGroups_[0] >= 2 && liveGroups_[2] >= 2 &&
            (probability < 0.25 || probability > 0.75);
    }
    void considerGap(
        Coordinate gapStart, int length,
        double newDeletion, Choice& best) const {
        const auto found = gaps_.find(gapStart);
        if (found == gaps_.end()) return;
        const Gap& gap = found->second;
        const Coordinate span = gap.end - gapStart;
        if (span < length) return;
        const Coordinate remainder = span - length;
        // Releasing a neighbor also joins the free span beyond that pipe.
        // Its previous/next link identifies the outer occupied boundary.
        Coordinate leftLength = 0;
        if (gap.left != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.left)];
            const Coordinate outerEnd = neighbor.previous == 0
                ? 0
                : pipes_[static_cast<std::size_t>(neighbor.previous)].start +
                    pipes_[static_cast<std::size_t>(neighbor.previous)].length;
            leftLength = gapStart - outerEnd;
        }
        Coordinate rightLength = 0;
        if (gap.right != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.right)];
            const Coordinate outerStart = neighbor.next == 0
                ? trenchLength_
                : pipes_[static_cast<std::size_t>(neighbor.next)].start;
            rightLength = outerStart - gap.end;
        }
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
        // Expected opportunity cost conditional on the new pipe surviving.
        // Each neighboring pipe can independently release its occupied span.
        for (int releaseLeft = 0; releaseLeft < 2; ++releaseLeft) {
            const double leftWeight = releaseLeft
                ? leftDeletion : 1.0 - leftDeletion;
            const Coordinate leftFree =
                releaseLeft ? leftLength : 0;
            for (int releaseRight = 0; releaseRight < 2; ++releaseRight) {
                const double rightWeight = releaseRight
                    ? rightDeletion : 1.0 - rightDeletion;
                const double weight = leftWeight * rightWeight;
                if (weight == 0.0) continue;
                const Coordinate rightFree =
                    releaseRight ? rightLength : 0;
                const double whole =
                    utility(span + leftFree + rightFree);
                futureLow += weight * (
                    whole - utility(leftFree) -
                    utility(remainder + rightFree));
                futureHigh += weight * (
                    whole - utility(remainder + leftFree) -
                    utility(rightFree));
            }
        }
        const bool insideArena =
            arenaActive_ && gapStart >= arenaStart_ &&
            gap.end <= arenaEnd_;
        const double futureWeight = 0.5 * (1.0 - newDeletion);
        for (int side = 0; side < 2; ++side) {
            const bool high = side != 0;
            if (high && remainder == 0) continue;
            if (high && gap.end == trenchLength_ && !insideArena) {
                continue;
            }
            const double futureCost = high ? futureHigh : futureLow;
            double score =
                (1.0 - futureWeight) * immediateCost +
                futureWeight * futureCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    // Fast-deleting pipes approach from the low side;
                    // slow-deleting pipes approach from the high side.
                    score += 0.125 * length *
                        (high ? newDeletion : 1.0 - newDeletion);
                }
            } else {
                if (gap.left != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, leftDeletion);
                }
                if (gap.right != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, rightDeletion);
                }
            }
            const Coordinate position =
                high ? gap.end - length : gapStart;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && position < best.start)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.score = score;
            }
        }
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
    }
    void selectCandidates(
        int length, int group,
        double deletionProbability, Choice& choice) const {
        auto current = bySize_.lower_bound({length, 0});
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const auto after = bySize_.upper_bound({
                current->first,
                std::numeric_limits<Coordinate>::max()});
            considerGap(
                current->second, length, deletionProbability, choice);
            const auto last = std::prev(after);
            if (last->second != current->second) {
                considerGap(
                    last->second, length, deletionProbability, choice);
            }
            current = after;
        }
        // Include wider residual-capacity bands even when many small
        // distinct spans precede them.
        for (int offset : {40, 80, 160}) {
            considerNear(
                bySize_, static_cast<Coordinate>(length) + offset,
                length, deletionProbability, choice);
        }
        considerNear(
            byBoundaryGroup_[static_cast<std::size_t>(group)],
            length, length, deletionProbability, choice);
        if (!gaps_.empty()) {
            const auto last = std::prev(gaps_.end());
            if (last->second.end == trenchLength_) {
                considerGap(
                    last->first, length, deletionProbability, choice);
            }
        }
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_ ? last : gaps_.end();
    }
    Coordinate growFor(
        int length, double deletionProbability, Choice& choice) {
        Coordinate start = trenchLength_;
        int left = tailPid_;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            start = tail->first;
            left = tail->second.left;
            eraseGap(tail);
        }
        const Coordinate available = trenchLength_ - start;
        const Coordinate deficit =
            std::max<Coordinate>(0, length - available);
        Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        const bool separate = canSeparate(deletionProbability);
        Coordinate extraDigs = 0;
        if (separate) {
            const Coordinate minimumCapacity =
                available + digs * kSectionLength;
            const Coordinate wantedExtra = std::max<Coordinate>(
                0, 3LL * length - minimumCapacity);
            const Coordinate budgetSections =
                (peakLiveVolume_ / 64) / kSectionLength;
            const Coordinate wantedSections =
                (wantedExtra + kSectionLength - 1) / kSectionLength;
            extraDigs = std::min(budgetSections, wantedSections);
            digs += extraDigs;
        }
        if (extraDigs > 0) ++expansionGatePasses;
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right});
        const GapKey key{end - start, start};
        bySize_.insert(key);
        const int leftGroup = left == 0
            ? -1 : static_cast<int>(pipes_[left].group);
        const int rightGroup = right == 0
            ? -1 : static_cast<int>(pipes_[right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].insert(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].insert(key);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const GapKey key{gap.end - start, start};
        bySize_.erase(key);
        const int leftGroup = gap.left == 0
            ? -1 : static_cast<int>(pipes_[gap.left].group);
        const int rightGroup = gap.right == 0
            ? -1 : static_cast<int>(pipes_[gap.right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].erase(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].erase(key);
        }
        gaps_.erase(position);
    }
    static void printInvalidPid() {
        std::cout << 0 << '\n' << std::flush;
    }
};
}  // namespace
// EVOLVE-BLOCK-END

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun
                      << " expansion_gate_opportunities=" << allocator.expansionGateOpportunities
                      << " expansion_gate_passes=" << allocator.expansionGatePasses
                      << " unit_profile_suppressed_expansions="
                      << allocator.unitProfileSuppressedExpansions << '\n';
#endif
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
```

Performance metrics:
Combined score to maximize: 0.93
valid_cases: 32; family_count: 16; worst_family_score: 0.81; mean_raw_kpi: 0.54; max_solver_cpu_seconds: 1.32; max_solver_rss_mib: 7.23

Text feedback:
case=s001_uniform_churn family=uniform_churn normalized=0.968390805 trench=6960 bound=6740 cpu_s=0.144110 rss_mib=1.625
case=s002_uniform_churn family=uniform_churn normalized=0.896551724 trench=3480 bound=3120 cpu_s=0.467549 rss_mib=3.219
case=s003_short_heavy family=short_heavy normalized=0.853333333 trench=1500 bound=1280 cpu_s=0.111868 rss_mib=2.016
case=s004_short_heavy family=short_heavy normalized=0.941176471 trench=340 bound=320 cpu_s=0.401765 rss_mib=3.188
case=s005_long_heavy family=long_heavy normalized=0.929203540 trench=4520 bound=4200 cpu_s=0.119913 rss_mib=2.016
case=s006_long_heavy family=long_heavy normalized=0.867647059 trench=1360 bound=1180 cpu_s=0.428784 rss_mib=3.828
case=s007_bimodal family=bimodal normalized=0.935064935 trench=4620 bound=4320 cpu_s=0.109118 rss_mib=2.016
case=s008_bimodal family=bimodal normalized=0.946226415 trench=42400 bound=40120 cpu_s=0.481039 rss_mib=3.969
case=s009_section_boundaries family=section_boundaries normalized=0.966666667 trench=600 bound=580 cpu_s=0.095420 rss_mib=2.016
case=s010_section_boundaries family=section_boundaries normalized=0.946297803 trench=49160 bound=46520 cpu_s=0.485910 rss_mib=3.969
case=s011_fifo family=fifo normalized=0.983280615 trench=44260 bound=43520 cpu_s=0.122683 rss_mib=2.125
case=s012_fifo family=fifo normalized=0.933333333 trench=600 bound=560 cpu_s=0.389760 rss_mib=3.812
case=s013_lifo family=lifo normalized=1.000000000 trench=720 bound=720 cpu_s=0.095682 rss_mib=2.016
case=s014_lifo family=lifo normalized=0.976744186 trench=860 bound=840 cpu_s=0.380060 rss_mib=3.812
case=s015_size_lifetimes family=size_lifetimes normalized=0.978723404 trench=940 bound=920 cpu_s=0.105729 rss_mib=2.016
case=s016_size_lifetimes family=size_lifetimes normalized=0.970282318 trench=26920 bound=26120 cpu_s=0.489039 rss_mib=3.906
case=s017_burst_drain family=burst_drain normalized=0.984293194 trench=3820 bound=3760 cpu_s=0.106635 rss_mib=2.016
case=s018_burst_drain family=burst_drain normalized=0.998571429 trench=56000 bound=55920 cpu_s=0.467882 rss_mib=3.938
case=s019_distribution_switch family=distribution_switch normalized=0.928571429 trench=560 bound=520 cpu_s=0.097380 rss_mib=2.000
case=s020_distribution_switch family=distribution_switch normalized=0.944444444 trench=1080 bound=1020 cpu_s=0.393007 rss_mib=3.828
case=s021_drifting_sizes family=drifting_sizes normalized=0.840909091 trench=880 bound=740 cpu_s=0.098062 rss_mib=2.016
case=s022_drifting_sizes family=drifting_sizes normalized=0.878121878 trench=20020 bound=17580 cpu_s=0.464507 rss_mib=3.844
case=s023_striped_recycling family=striped_recycling normalized=0.999379203 trench=193300 bound=193180 cpu_s=0.103055 rss_mib=2.109
case=s024_striped_recycling family=striped_recycling normalized=0.999793282 trench=774000 bound=773840 cpu_s=0.417765 rss_mib=4.234
case=s025_geometric_cohorts family=geometric_cohorts normalized=0.806930693 trench=4040 bound=3260 cpu_s=0.113934 rss_mib=2.000
case=s026_geometric_cohorts family=geometric_cohorts normalized=0.952380952 trench=840 bound=800 cpu_s=0.377132 rss_mib=3.828
case=s027_additive_cohorts family=additive_cohorts normalized=0.748502994 trench=6680 bound=5000 cpu_s=0.112298 rss_mib=2.016
case=s028_additive_cohorts family=additive_cohorts normalized=0.947368421 trench=760 bound=720 cpu_s=0.397060 rss_mib=3.812
case=s029_large_live_set family=large_live_set normalized=0.978351570 trench=254060 bound=248560 cpu_s=1.315871 rss_mib=7.047
case=s030_large_live_set family=large_live_set normalized=0.979237122 trench=254300 bound=249020 cpu_s=1.306473 rss_mib=7.234
case=s031_size_biased_deletion family=size_biased_deletion normalized=0.812500000 trench=1600 bound=1300 cpu_s=0.105187 rss_mib=2.016
case=s032_size_biased_deletion family=size_biased_deletion normalized=0.812500000 trench=1600 bound=1300 cpu_s=0.431708 rss_mib=3.641


# Current program

Here is the current program we are trying to improve (you will need to propose a modification to it below):

```cpp
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

// EVOLVE-BLOCK-START
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes still-live pipes, so long-lived survivors contribute
// evidence without requiring their eventual deletion.
struct Rate {
    int live = 0;
    double exposure = 0.0;
    double deaths = 0.0;
    std::uint64_t stamp = 0;
    double exposureAt(std::uint64_t now) const {
        return exposure +
            static_cast<double>(now - stamp) * static_cast<double>(live);
    }
    void touch(std::uint64_t now) {
        exposure = exposureAt(now);
        stamp = now;
    }
    void change(std::uint64_t now, int delta, bool removed) {
        touch(now);
        live += delta;
        if (removed) deaths += 1.0;
    }
    void forget(std::uint64_t now) {
        touch(now);
        exposure *= 0.5;
        deaths *= 0.5;
    }
};
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    double score = std::numeric_limits<double>::infinity();
};
class Allocator {
public:
    // Preserve the optional diagnostics interface used outside the block.
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        beginCommand();
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        if (lastPlacementLength_ != length) {
            lastPlacementLength_ = length;
            runOrdinal_ = 0;
        }
        const int runPhase = static_cast<int>(runOrdinal_ & 7U);
        ++runOrdinal_;
        observeLength(length);
        refreshModel(newlyObservedLength);
        const int pid = static_cast<int>(pipes_.size());
        const int globalPhase = pid & 7;
        const double deletionProbability =
            predictDeletion(length, globalPhase, runPhase);
        const int group = classify(deletionProbability);
        peakLiveVolume_ = std::max(
            peakLiveVolume_, liveVolume_ + static_cast<Coordinate>(length));
        // An already available tail can become a two-front arena without
        // requesting any additional excavation.
        if (!arenaActive_ && canSeparate(deletionProbability)) {
            const auto tail = tailGap();
            if (tail != gaps_.end() &&
                tail->second.end - tail->first >= 2LL * length) {
                arenaActive_ = true;
                arenaStart_ = tail->first;
                arenaEnd_ = trenchLength_;
            }
        }
        Choice choice;
        Coordinate digs = 0;
        const auto firstFit = bySize_.lower_bound({length, 0});
        if (firstFit != bySize_.end()) {
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            digs = growFor(length, deletionProbability, choice);
        }
        const auto selected = gaps_.find(choice.gapStart);
        const Coordinate gapStart = selected->first;
        const Gap gap = selected->second;
        eraseGap(selected);
        Pipe pipe;
        pipe.start = choice.start;
        pipe.length = length;
        pipe.previous = gap.left;
        pipe.next = gap.right;
        pipe.runPhase = static_cast<unsigned char>(runPhase);
        pipe.group = static_cast<unsigned char>(group);
        pipe.active = true;
        pipes_.push_back(pipe);
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(gapStart, pipe.start, gap.left, pid);
        insertGap(pipe.start + length, gap.end, pid, gap.right);
        changePopulation(length, globalPhase, runPhase, 1, false);
        ++liveGroups_[static_cast<std::size_t>(group)];
        liveVolume_ += length;
        std::cout << digs << ' ' << pipe.start << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const int pid = static_cast<int>(pidValue);
        if (!pipes_[static_cast<std::size_t>(pid)].active) {
            printInvalidPid();
            return;
        }
        beginCommand();
        const Pipe pipe = pipes_[static_cast<std::size_t>(pid)];
        if (pipe.previous != 0) {
            pipes_[pipe.previous].next = pipe.next;
        }
        if (pipe.next != 0) {
            pipes_[pipe.next].previous = pipe.previous;
        } else {
            tailPid_ = pipe.previous;
        }
        Coordinate start = pipe.start;
        Coordinate end = pipe.start + pipe.length;
        auto right = gaps_.lower_bound(start);
        if (right != gaps_.begin()) {
            const auto left = std::prev(right);
            if (left->second.end == start) {
                start = left->first;
                eraseGap(left);
            }
        }
        right = gaps_.lower_bound(end);
        if (right != gaps_.end() && right->first == end) {
            end = right->second.end;
            eraseGap(right);
        }
        pipes_[static_cast<std::size_t>(pid)].active = false;
        insertGap(start, end, pipe.previous, pipe.next);
        changePopulation(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase), -1, true);
        --liveGroups_[static_cast<std::size_t>(pipe.group)];
        liveVolume_ -= pipe.length;
        if (totalRate_.live == 0) arenaActive_ = false;
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    GapMap gaps_;
    std::set<GapKey> bySize_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    int tailPid_ = 0;
    Coordinate trenchLength_ = 0;
    Coordinate liveVolume_ = 0;
    Coordinate peakLiveVolume_ = 0;
    std::array<int, 3> liveGroups_{};
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    int lastPlacementLength_ = -1;
    std::uint64_t runOrdinal_ = 0;
    Rate totalRate_;
    std::array<Rate, 41> lengthRates_{};
    std::array<Rate, kPhaseCount> globalPhaseRates_{};
    std::array<Rate, kPhaseCount> runPhaseRates_{};
    std::array<double, 41> lengthRisk_{};
    std::array<double, kPhaseCount> globalPhaseRisk_{};
    std::array<double, kPhaseCount> runPhaseRisk_{};
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, kPotentialLimit + 1> potential_{};
    bool arenaActive_ = false;
    Coordinate arenaStart_ = 0;
    Coordinate arenaEnd_ = 0;
    static double difference(double a, double b) {
        return a >= b ? a - b : b - a;
    }
    static int classify(double probability) {
        if (probability < 1.0 / 3.0) return 0;
        if (probability > 2.0 / 3.0) return 2;
        return 1;
    }
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
        }
    }
    void changePopulation(
        int length, int globalPhase, int runPhase,
        int delta, bool removed) {
        totalRate_.change(tick_, delta, removed);
        lengthRates_[static_cast<std::size_t>(length)].change(
            tick_, delta, removed);
        globalPhaseRates_[static_cast<std::size_t>(globalPhase)].change(
            tick_, delta, removed);
        runPhaseRates_[static_cast<std::size_t>(runPhase)].change(
            tick_, delta, removed);
    }
    void observeLength(int length) {
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        // Hierarchical smoothing shares evidence between cyclic positions.
        // No deletion pattern is enabled by a fixed sequence of commands.
        for (int residue = 0; residue < kPhaseCount; ++residue) {
            double rate = globalRate;
            for (int period = 2; period <= kPhaseCount; period *= 2) {
                double exposure = 0.0;
                double deaths = 0.0;
                for (int position = residue % period;
                     position < kPhaseCount; position += period) {
                    const Rate& observation =
                        observations[static_cast<std::size_t>(position)];
                    exposure += observation.exposureAt(tick_);
                    deaths += observation.deaths;
                }
                constexpr double priorDeaths = 8.0;
                rate = (deaths + priorDeaths) /
                    (exposure + priorDeaths / rate);
            }
            result[static_cast<std::size_t>(residue)] =
                std::clamp(rate / globalRate, 0.125, 8.0);
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
        for (int length = 1; length <= 40; ++length) {
            const Rate& observation =
                lengthRates_[static_cast<std::size_t>(length)];
            constexpr double priorDeaths = 4.0;
            const double rate =
                (observation.deaths + priorDeaths) /
                (observation.exposureAt(tick_) +
                 priorDeaths / globalRate);
            lengthRisk_[static_cast<std::size_t>(length)] =
                std::clamp(rate / globalRate, 0.0625, 16.0);
        }
        rebuildPhaseRisk(
            globalPhaseRates_, globalRate, globalPhaseRisk_);
        rebuildPhaseRisk(
            runPhaseRates_, globalRate, runPhaseRisk_);
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            probability[index] =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            prefix[index] = prefix[index - 1] + probability[index];
        }
        prefix[40] = 1.0;
        // Renewal reward: at each step, allow up to four observed-distribution
        // requests to find a fitting one, then continue with the remainder.
        potential_[0] = 0.0;
        for (int capacity = 1;
             capacity <= kPotentialLimit; ++capacity) {
            const int maximum = std::min(capacity, 40);
            const double fit = prefix[static_cast<std::size_t>(maximum)];
            const double miss = std::max(0.0, 1.0 - fit);
            const double retryFactor =
                1.0 + miss + miss * miss + miss * miss * miss;
            double reward = 0.0;
            for (int length = 1; length <= maximum; ++length) {
                reward += probability[static_cast<std::size_t>(length)] *
                    (static_cast<double>(length) +
                     potential_[static_cast<std::size_t>(capacity - length)]);
            }
            potential_[static_cast<std::size_t>(capacity)] =
                std::clamp(
                    retryFactor * reward,
                    0.0, static_cast<double>(capacity));
        }
    }
    double predictDeletion(
        int length, int globalPhase, int runPhase) const {
        const double phaseMultiplier = 0.5 * (
            globalPhaseRisk_[static_cast<std::size_t>(globalPhase)] +
            runPhaseRisk_[static_cast<std::size_t>(runPhase)]);
        const double relativeRate = std::clamp(
            lengthRisk_[static_cast<std::size_t>(length)] *
                phaseMultiplier,
            1.0 / 32.0, 32.0);
        // A bounded survival approximation over a typical lifetime horizon.
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
    }
    double utility(Coordinate length) const {
        if (length <= 0) return 0.0;
        if (length <= kPotentialLimit) {
            return potential_[static_cast<std::size_t>(length)];
        }
        return potential_[kPotentialLimit] +
            static_cast<double>(length - kPotentialLimit);
    }
    bool canSeparate(double probability) const {
        return totalRate_.deaths >= 16.0 &&
            liveGroups_[0] >= 2 && liveGroups_[2] >= 2 &&
            (probability < 0.25 || probability > 0.75);
    }
    void considerGap(
        Coordinate gapStart, int length,
        double newDeletion, Choice& best) const {
        const auto found = gaps_.find(gapStart);
        if (found == gaps_.end()) return;
        const Gap& gap = found->second;
        const Coordinate span = gap.end - gapStart;
        if (span < length) return;
        const Coordinate remainder = span - length;
        const Coordinate leftLength = gap.left == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.left)].length;
        const Coordinate rightLength = gap.right == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.right)].length;
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
        // Expected opportunity cost conditional on the new pipe surviving.
        // Each neighboring pipe can independently release its occupied span.
        for (int releaseLeft = 0; releaseLeft < 2; ++releaseLeft) {
            const double leftWeight = releaseLeft
                ? leftDeletion : 1.0 - leftDeletion;
            const Coordinate leftFree =
                releaseLeft ? leftLength : 0;
            for (int releaseRight = 0; releaseRight < 2; ++releaseRight) {
                const double rightWeight = releaseRight
                    ? rightDeletion : 1.0 - rightDeletion;
                const double weight = leftWeight * rightWeight;
                if (weight == 0.0) continue;
                const Coordinate rightFree =
                    releaseRight ? rightLength : 0;
                const double whole =
                    utility(span + leftFree + rightFree);
                futureLow += weight * (
                    whole - utility(leftFree) -
                    utility(remainder + rightFree));
                futureHigh += weight * (
                    whole - utility(remainder + leftFree) -
                    utility(rightFree));
            }
        }
        const bool insideArena =
            arenaActive_ && gapStart >= arenaStart_ &&
            gap.end <= arenaEnd_;
        const double futureWeight = 0.5 * (1.0 - newDeletion);
        for (int side = 0; side < 2; ++side) {
            const bool high = side != 0;
            if (high && remainder == 0) continue;
            if (high && gap.end == trenchLength_ && !insideArena) {
                continue;
            }
            const double futureCost = high ? futureHigh : futureLow;
            double score =
                (1.0 - futureWeight) * immediateCost +
                futureWeight * futureCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    // Fast-deleting pipes approach from the low side;
                    // slow-deleting pipes approach from the high side.
                    score += 0.125 * length *
                        (high ? newDeletion : 1.0 - newDeletion);
                }
            } else {
                if (gap.left != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, leftDeletion);
                }
                if (gap.right != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, rightDeletion);
                }
            }
            const Coordinate position =
                high ? gap.end - length : gapStart;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && position < best.start)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.score = score;
            }
        }
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
    }
    void selectCandidates(
        int length, int group,
        double deletionProbability, Choice& choice) const {
        auto current = bySize_.lower_bound({length, 0});
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const auto after = bySize_.upper_bound({
                current->first,
                std::numeric_limits<Coordinate>::max()});
            considerGap(
                current->second, length, deletionProbability, choice);
            const auto last = std::prev(after);
            if (last->second != current->second) {
                considerGap(
                    last->second, length, deletionProbability, choice);
            }
            current = after;
        }
        // Include wider residual-capacity bands even when many small
        // distinct spans precede them.
        for (int offset : {40, 80, 160}) {
            considerNear(
                bySize_, static_cast<Coordinate>(length) + offset,
                length, deletionProbability, choice);
        }
        considerNear(
            byBoundaryGroup_[static_cast<std::size_t>(group)],
            length, length, deletionProbability, choice);
        if (!gaps_.empty()) {
            const auto last = std::prev(gaps_.end());
            if (last->second.end == trenchLength_) {
                considerGap(
                    last->first, length, deletionProbability, choice);
            }
        }
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_ ? last : gaps_.end();
    }
    Coordinate growFor(
        int length, double deletionProbability, Choice& choice) {
        Coordinate start = trenchLength_;
        int left = tailPid_;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            start = tail->first;
            left = tail->second.left;
            eraseGap(tail);
        }
        const Coordinate available = trenchLength_ - start;
        const Coordinate deficit =
            std::max<Coordinate>(0, length - available);
        Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        const bool separate = canSeparate(deletionProbability);
        Coordinate extraDigs = 0;
        if (separate) {
            const Coordinate minimumCapacity =
                available + digs * kSectionLength;
            const Coordinate wantedExtra = std::max<Coordinate>(
                0, 3LL * length - minimumCapacity);
            const Coordinate budgetSections =
                (peakLiveVolume_ / 64) / kSectionLength;
            const Coordinate wantedSections =
                (wantedExtra + kSectionLength - 1) / kSectionLength;
            extraDigs = std::min(budgetSections, wantedSections);
            digs += extraDigs;
        }
        if (extraDigs > 0) ++expansionGatePasses;
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right});
        const GapKey key{end - start, start};
        bySize_.insert(key);
        const int leftGroup = left == 0
            ? -1 : static_cast<int>(pipes_[left].group);
        const int rightGroup = right == 0
            ? -1 : static_cast<int>(pipes_[right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].insert(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].insert(key);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const GapKey key{gap.end - start, start};
        bySize_.erase(key);
        const int leftGroup = gap.left == 0
            ? -1 : static_cast<int>(pipes_[gap.left].group);
        const int rightGroup = gap.right == 0
            ? -1 : static_cast<int>(pipes_[gap.right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].erase(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].erase(key);
        }
        gaps_.erase(position);
    }
    static void printInvalidPid() {
        std::cout << 0 << '\n' << std::flush;
    }
};
}  // namespace
// EVOLVE-BLOCK-END

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun
                      << " expansion_gate_opportunities=" << allocator.expansionGateOpportunities
                      << " expansion_gate_passes=" << allocator.expansionGatePasses
                      << " unit_profile_suppressed_expansions="
                      << allocator.unitProfileSuppressedExpansions << '\n';
#endif
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

```

Here are the performance metrics of the program:

Combined score to maximize: 0.93
valid_cases: 32; family_count: 16; worst_family_score: 0.83; mean_raw_kpi: 0.54; max_solver_cpu_seconds: 1.47; max_solver_rss_mib: 5.12

Here is additional text feedback about the current program:

case=s001_uniform_churn family=uniform_churn normalized=0.957386364 trench=7040 bound=6740 cpu_s=0.115498 rss_mib=2.000
case=s002_uniform_churn family=uniform_churn normalized=0.906976744 trench=3440 bound=3120 cpu_s=0.474890 rss_mib=2.938
case=s003_short_heavy family=short_heavy normalized=0.831168831 trench=1540 bound=1280 cpu_s=0.117754 rss_mib=1.766
case=s004_short_heavy family=short_heavy normalized=1.000000000 trench=320 bound=320 cpu_s=0.413006 rss_mib=3.172
case=s005_long_heavy family=long_heavy normalized=0.925110132 trench=4540 bound=4200 cpu_s=0.117890 rss_mib=2.016
case=s006_long_heavy family=long_heavy normalized=0.842857143 trench=1400 bound=1180 cpu_s=0.440762 rss_mib=3.734
case=s007_bimodal family=bimodal normalized=0.943231441 trench=4580 bound=4320 cpu_s=0.119370 rss_mib=1.984
case=s008_bimodal family=bimodal normalized=0.949810606 trench=42240 bound=40120 cpu_s=0.509895 rss_mib=3.531
case=s009_section_boundaries family=section_boundaries normalized=0.966666667 trench=600 bound=580 cpu_s=0.101718 rss_mib=2.000
case=s010_section_boundaries family=section_boundaries normalized=0.945912973 trench=49180 bound=46520 cpu_s=0.493700 rss_mib=3.547
case=s011_fifo family=fifo normalized=0.980621902 trench=44380 bound=43520 cpu_s=0.118287 rss_mib=2.125
case=s012_fifo family=fifo normalized=0.965517241 trench=580 bound=560 cpu_s=0.405463 rss_mib=2.812
case=s013_lifo family=lifo normalized=1.000000000 trench=720 bound=720 cpu_s=0.097989 rss_mib=2.000
case=s014_lifo family=lifo normalized=0.976744186 trench=860 bound=840 cpu_s=0.380832 rss_mib=3.812
case=s015_size_lifetimes family=size_lifetimes normalized=0.978723404 trench=940 bound=920 cpu_s=0.102948 rss_mib=2.016
case=s016_size_lifetimes family=size_lifetimes normalized=0.965976331 trench=27040 bound=26120 cpu_s=0.503115 rss_mib=3.266
case=s017_burst_drain family=burst_drain normalized=0.974093264 trench=3860 bound=3760 cpu_s=0.117829 rss_mib=1.766
case=s018_burst_drain family=burst_drain normalized=0.998928189 trench=55980 bound=55920 cpu_s=0.495376 rss_mib=2.969
case=s019_distribution_switch family=distribution_switch normalized=0.928571429 trench=560 bound=520 cpu_s=0.102451 rss_mib=2.016
case=s020_distribution_switch family=distribution_switch normalized=0.944444444 trench=1080 bound=1020 cpu_s=0.400411 rss_mib=3.531
case=s021_drifting_sizes family=drifting_sizes normalized=0.840909091 trench=880 bound=740 cpu_s=0.097905 rss_mib=2.000
case=s022_drifting_sizes family=drifting_sizes normalized=0.896938776 trench=19600 bound=17580 cpu_s=0.483413 rss_mib=2.891
case=s023_striped_recycling family=striped_recycling normalized=0.998862461 trench=193400 bound=193180 cpu_s=0.114322 rss_mib=2.125
case=s024_striped_recycling family=striped_recycling normalized=0.999767448 trench=774020 bound=773840 cpu_s=0.446338 rss_mib=3.891
case=s025_geometric_cohorts family=geometric_cohorts normalized=0.795121951 trench=4100 bound=3260 cpu_s=0.113605 rss_mib=2.000
case=s026_geometric_cohorts family=geometric_cohorts normalized=0.952380952 trench=840 bound=800 cpu_s=0.407536 rss_mib=2.797
case=s027_additive_cohorts family=additive_cohorts normalized=0.757575758 trench=6600 bound=5000 cpu_s=0.113921 rss_mib=2.016
case=s028_additive_cohorts family=additive_cohorts normalized=0.972972973 trench=740 bound=720 cpu_s=0.392410 rss_mib=3.328
case=s029_large_live_set family=large_live_set normalized=0.978428594 trench=254040 bound=248560 cpu_s=1.467803 rss_mib=4.500
case=s030_large_live_set family=large_live_set normalized=0.980625345 trench=253940 bound=249020 cpu_s=1.394250 rss_mib=5.125
case=s031_size_biased_deletion family=size_biased_deletion normalized=0.855263158 trench=1520 bound=1300 cpu_s=0.104519 rss_mib=2.000
case=s032_size_biased_deletion family=size_biased_deletion normalized=0.812500000 trench=1600 bound=1300 cpu_s=0.423969 rss_mib=3.828


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
