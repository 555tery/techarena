#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <stdexcept>
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

#if defined(EOF_SURVIVOR_DIAG)
struct DiagTarget {
    int op = 0;
    int gapId = 0;
    std::int64_t start = 0;
    std::int64_t end = 0;
    int length = 0;
    int birthOp = 0;
    int request = 0;
    int firstExpansionOp = 0;
};
#endif

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

class Allocator {
public:
#if defined(EOF_SURVIVOR_DIAG)
    std::size_t operationIndex = 0;
    std::map<int, std::vector<DiagTarget>> diagTargets;
    std::ofstream expansionLog;
    std::ofstream candidateLog;
    std::ofstream candidateSummaryLog;
    std::ofstream candidateTargetLog;
    std::ofstream candidateScoresLog;

    Allocator() {
        const char* path = std::getenv("PIPE_SURVIVOR_TARGETS");
        if (path == nullptr) throw std::runtime_error("PIPE_SURVIVOR_TARGETS is unset");
        std::ifstream input(path);
        if (!input) throw std::runtime_error("cannot open target pair list");
        DiagTarget target;
        while (input >> target.op >> target.gapId >> target.start >> target.end
                     >> target.length >> target.birthOp >> target.request
                     >> target.firstExpansionOp) {
            diagTargets[target.op].push_back(target);
        }
        if (!input.eof()) throw std::runtime_error("malformed target pair list");
        std::cerr << "SVDIAG_HEADER op gap_id request start end gap_len birth_op current_gap "
                     "cohort cohort_eligible mode request_cohort high_side pool eligibility representative_start target_score target_rank "
                     "pool_size baseline_start baseline_score selected_start selected_score selected_rank "
                     "rollout_count mc_decisions free_gaps active_pipes history_size\n";
        const char* expansionPath = std::getenv("PIPE_EXPANSION_LOG");
        const char* candidatePath = std::getenv("PIPE_EXPANSION_CANDIDATES");
        const char* candidateSummaryPath = std::getenv("PIPE_CANDIDATE_SUMMARY");
        const char* candidateTargetPath = std::getenv("PIPE_CANDIDATE_TARGETS");
        const char* candidateScoresPath = std::getenv("PIPE_CANDIDATE_SCORES");
        if (expansionPath == nullptr || candidatePath == nullptr ||
            candidateSummaryPath == nullptr || candidateTargetPath == nullptr ||
            candidateScoresPath == nullptr)
            throw std::runtime_error("extension telemetry paths are unset");
        expansionLog.open(expansionPath);
        candidateLog.open(candidatePath);
        candidateSummaryLog.open(candidateSummaryPath);
        candidateTargetLog.open(candidateTargetPath);
        candidateScoresLog.open(candidateScoresPath);
        if (!expansionLog || !candidateLog || !candidateSummaryLog ||
            !candidateTargetLog || !candidateScoresLog)
            throw std::runtime_error("cannot open extension telemetry outputs");
        expansionLog << "op,request,digs,old_trench,new_trench,active_pipes,free_gaps,"
                        "free_volume_before_m,largest_gap_before_m,free_volume_sufficed,history_size,"
                        "parity_mode,size_cohort,high_side,alternating_delete_mode,predicted_deleted_parity,"
                        "tail_gap_start,tail_gap_end,tail_gap_length,tail_start,tail_length,"
                        "preserve_foreign_tail,tail_reused,selected_start,"
                        "physical_fit_count,preferred_fit_count,shared_fit_count,foreign_fit_count,"
                        "selected_pool,eligible_pool_physical_count,representative_count,scored_count,"
                        "after_cap_count,decision\n";
        candidateLog << "op,request,gap_start,gap_end,gap_length,gap_cohort,physical_rank,"
                        "hypothetical_score,slack,history_size,misses,pool,cohort_eligible,"
                        "pool_representative_start,is_pool_representative,score_status,score_rank,"
                        "excluded_reason\n";
        candidateSummaryLog
            << "op,request,target_count,target_first_expansion_ops,parity_mode,request_cohort,high_side,"
               "pool,physical_fit_count,preferred_fit_count,shared_fit_count,foreign_fit_count,"
               "selected_pool_physical_count,representative_count,representative_suppressed_count,"
               "scored_count,after_cap_count,empty_history_skipped_count,"
               "baseline_start,baseline_score,baseline_rank,selected_start,selected_score,selected_rank,"
               "winner_reason,rollouts_this_op,mc_decisions_total,free_gaps,active_pipes,history_size\n";
        candidateTargetLog
            << "op,first_expansion_op,request,gap_id,birth_op,gap_start,gap_end,gap_length,"
               "current_gap,target_cohort,parity_mode,request_cohort,high_side,pool,physical_rank,"
               "cohort_eligible,representative_start,is_representative,score,scored_rank,score_status,"
               "excluded_reason,scored_candidate_count,baseline_start,baseline_score,baseline_rank,"
               "selected_start,selected_score,selected_rank,rollouts_this_op,mc_pool_rank,"
               "mc_decisions_total,free_gaps,active_pipes,history_size\n";
        candidateScoresLog
            << "op,request,pool,high_side,start,gap_length,slack,score,scorer_rank,mc_pool_rank,"
               "scan_status,is_baseline,is_selected,mc_winner\n";
    }
#endif
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
        auto selectedGap = gap;
        const std::size_t rolloutsBefore = mcRolloutsRun;
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) selectedGap = freeByStart.find(selectedStart);
        }
#if defined(EOF_SURVIVOR_DIAG)
        diagnosticCapture(length, highSide, sizeCohort, gap, selectedGap,
                          mcRolloutsRun - rolloutsBefore);
#endif
        if (selectedGap != freeByStart.end()) {
            start = consumeAtSide(selectedGap, length, highSide);
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
#if defined(EOF_SURVIVOR_DIAG)
            if (digs > 0) {
                const std::int64_t tailGapStart = tail == freeByStart.end() ? -1 : tail->first;
                const std::int64_t tailGapEnd = tail == freeByStart.end() ? -1 : tail->second;
                diagnosticExpansion(length, highSide, sizeCohort, tailGapStart,
                                    tailGapEnd, tailStart, tailLength, digs,
                                    preserveForeignTail);
            }
#endif

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

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

#if defined(EOF_SURVIVOR_DIAG)
    void diagnosticExpansion(int length, bool highSide, int sizeCohort,
                             std::int64_t tailGapStart, std::int64_t tailGapEnd,
                             std::int64_t tailStart, std::int64_t tailLength,
                             std::int64_t digs, bool preserveForeignTail) {
        struct PhysicalGap {
            std::int64_t start;
            std::int64_t end;
            std::int64_t gapLength;
            int cohort;
            std::int64_t slack;
            std::int64_t misses;
            std::int64_t score;
            int physicalRank = -1;
            std::int64_t representativeStart = -1;
            bool cohortEligible = false;
            bool representative = false;
            std::string pool;
            std::string status;
            std::string excludedReason;
            int scoreRank = -1;
        };

        std::vector<PhysicalGap> physical;
        std::size_t preferredFitCount = 0;
        std::size_t sharedFitCount = 0;
        std::size_t foreignFitCount = 0;
        std::int64_t freeVolumeBefore = 0;
        std::int64_t largestGapBefore = 0;
        for (const auto& [start, end] : freeByStart) {
            const std::int64_t gapLength = end - start;
            freeVolumeBefore += gapLength;
            largestGapBefore = std::max(largestGapBefore, gapLength);
            if (gapLength < length) continue;
            const int cohort = gapCohort.at(start);
            if (cohort == sizeCohort) ++preferredFitCount;
            else if (cohort == -1) ++sharedFitCount;
            else ++foreignFitCount;
            const std::int64_t slack = gapLength - length;
            std::int64_t misses = 0;
            if (slack > 0 && slack <= 40) {
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                    misses += recentFrequency[static_cast<std::size_t>(request)];
            }
            PhysicalGap candidate;
            candidate.start = start;
            candidate.end = end;
            candidate.gapLength = gapLength;
            candidate.cohort = cohort;
            candidate.slack = slack;
            candidate.misses = misses;
            candidate.score = scoreGap(gapLength, length);
            physical.push_back(std::move(candidate));
        }

        std::string selectedPool = "all";
        const std::set<std::pair<std::int64_t, std::int64_t>>* index = &freeBySize;
        if (parityCohortMode) {
            if (preferredFitCount != 0) {
                selectedPool = "preferred";
                index = &freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            } else if (sharedFitCount != 0) {
                selectedPool = "shared";
                index = &freeBySizeShared;
            } else {
                selectedPool = "none";
                index = nullptr;
            }
        }

        std::map<std::int64_t, std::int64_t> representatives;
        std::vector<PhysicalGap*> scored;
        std::size_t eligibleRepresentativeCount = 0;
        std::size_t eligiblePoolPhysicalCount = 0;
        std::size_t afterCapCount = 0;
        if (index != nullptr) {
            auto it = index->lower_bound({length, 0});
            while (it != index->end()) {
                const std::int64_t gapLength = it->first;
                representatives.emplace(gapLength, it->second);
                ++eligibleRepresentativeCount;
                it = index->upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
            }
            for (const PhysicalGap& candidate : physical) {
                if (!parityCohortMode ||
                    (selectedPool == "preferred" && candidate.cohort == sizeCohort) ||
                    (selectedPool == "shared" && candidate.cohort == -1)) {
                    ++eligiblePoolPhysicalCount;
                }
            }

            it = index->lower_bound({length, 0});
            while (it != index->end()) {
                const std::int64_t gapLength = it->first;
                const std::int64_t start = it->second;
                const std::int64_t slack = gapLength - length;
                const auto physicalIt = std::find_if(physical.begin(), physical.end(),
                    [start](const PhysicalGap& candidate) { return candidate.start == start; });
                if (physicalIt == physical.end())
                    throw std::runtime_error("candidate index disagrees with free-gap map");
                physicalIt->cohortEligible = true;
                physicalIt->representative = true;
                physicalIt->representativeStart = start;
                physicalIt->pool = selectedPool;
                physicalIt->status = slack > 40 ? "scored_first_over40" : "scored";
                scored.push_back(&*physicalIt);
                if (slack > 40) {
                    it = index->upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
                    while (it != index->end()) {
                        const std::int64_t laterLength = it->first;
                        const std::int64_t laterStart = it->second;
                        const auto later = std::find_if(physical.begin(), physical.end(),
                            [laterStart](const PhysicalGap& candidate) {
                                return candidate.start == laterStart;
                            });
                        if (later == physical.end())
                            throw std::runtime_error("post-cap index disagrees with free-gap map");
                        later->cohortEligible = true;
                        later->representative = true;
                        later->representativeStart = laterStart;
                        later->pool = selectedPool;
                        later->status = "excluded_after_first_over40";
                        later->excludedReason = "after_first_over40_candidate";
                        ++afterCapCount;
                        it = index->upper_bound({laterLength,
                            std::numeric_limits<std::int64_t>::max()});
                    }
                    break;
                }
                it = index->upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
            }
        }

        auto byScore = [highSide](const PhysicalGap* lhs, const PhysicalGap* rhs) {
            if (lhs->score != rhs->score) return lhs->score < rhs->score;
            return highSide ? lhs->start > rhs->start : lhs->start < rhs->start;
        };
        std::vector<PhysicalGap*> physicalRanked;
        physicalRanked.reserve(physical.size());
        for (auto& candidate : physical) physicalRanked.push_back(&candidate);
        std::sort(physicalRanked.begin(), physicalRanked.end(), byScore);
        for (std::size_t i = 0; i < physicalRanked.size(); ++i)
            physicalRanked[i]->physicalRank = static_cast<int>(i + 1);

        std::sort(scored.begin(), scored.end(), byScore);
        for (std::size_t i = 0; i < scored.size(); ++i)
            scored[i]->scoreRank = static_cast<int>(i + 1);

        for (auto& candidate : physical) {
            if (selectedPool == "none") {
                candidate.pool = "none";
                candidate.status = "excluded_by_cohort";
                candidate.excludedReason = "no_preferred_or_shared_fit";
            } else if (parityCohortMode &&
                       !((selectedPool == "preferred" && candidate.cohort == sizeCohort) ||
                         (selectedPool == "shared" && candidate.cohort == -1))) {
                candidate.pool = selectedPool;
                candidate.status = "excluded_by_cohort";
                candidate.excludedReason = selectedPool == "preferred"
                    ? "foreign_or_shared_while_preferred_fit_exists"
                    : "foreign_cohort_not_shared";
            } else if (!candidate.representative) {
                candidate.cohortEligible = true;
                candidate.pool = selectedPool;
                const auto rep = representatives.find(candidate.gapLength);
                candidate.representativeStart = rep == representatives.end() ? -1 : rep->second;
                candidate.status = "excluded_by_representative";
                candidate.excludedReason = "same_length_lower_address_representative";
            } else if (candidate.status.empty()) {
                candidate.status = "excluded_by_candidate_scan";
                candidate.excludedReason = "not_in_live_score_loop";
            }
        }

        if (eligibleRepresentativeCount != 0 || !scored.empty())
            throw std::runtime_error("expansion has an eligible physical candidate");

        const std::int64_t oldTrench = trenchLength;
        const std::int64_t newTrench = oldTrench + digs * kDigLength;
        const std::int64_t selectedStart = parityCohortMode && highSide &&
            !preserveForeignTail ? newTrench - length : tailStart;
        const bool tailReused = tailGapStart >= 0 && tailStart == tailGapStart;
        std::string decision = physical.empty()
            ? "no_physical_fit_extend_tail"
            : "all_physical_fits_filtered_by_cohort_extend_tail";
        expansionLog << operationIndex << ',' << length << ',' << digs << ','
                     << oldTrench << ',' << newTrench << ',' << activePipeCount << ','
                     << freeByStart.size() << ',' << freeVolumeBefore << ','
                     << largestGapBefore << ',' << (freeVolumeBefore >= length) << ','
                     << recentLengths.size() << ','
                     << parityCohortMode << ',' << sizeCohort << ',' << highSide << ','
                     << alternatingDeleteMode << ',' << predictedDeletedParity << ','
                     << tailGapStart << ',' << tailGapEnd << ','
                     << (tailGapStart < 0 ? 0 : tailGapEnd - tailGapStart) << ','
                     << tailStart << ',' << tailLength << ',' << preserveForeignTail << ','
                     << tailReused << ',' << selectedStart << ',' << physical.size() << ','
                     << preferredFitCount << ',' << sharedFitCount << ',' << foreignFitCount << ','
                     << selectedPool << ',' << eligiblePoolPhysicalCount << ','
                     << eligibleRepresentativeCount << ','
                     << scored.size() << ',' << afterCapCount << ',' << decision << '\n';

        for (const PhysicalGap& candidate : physical) {
            candidateLog << operationIndex << ',' << length << ',' << candidate.start << ','
                         << candidate.end << ',' << candidate.gapLength << ',' << candidate.cohort << ','
                         << candidate.physicalRank << ',' << candidate.score << ',' << candidate.slack << ','
                         << recentLengths.size() << ',' << candidate.misses << ',' << candidate.pool << ','
                         << candidate.cohortEligible << ',' << candidate.representativeStart << ','
                         << candidate.representative << ',' << candidate.status << ','
                         << candidate.scoreRank << ',' << candidate.excludedReason << '\n';
        }
    }

    std::vector<GapCandidate> diagnosticCandidates(
        const std::set<std::pair<std::int64_t, std::int64_t>>& index,
        int length, bool highSide) const {
        std::vector<GapCandidate> candidates;
        auto it = index.lower_bound({length, 0});
        if (it == index.end()) return candidates;
        if (recentLengths.empty()) {
            // bestFittingGapFromSet() returns immediately without history.
            candidates.push_back(GapCandidate{it->second, 0});
            return candidates;
        }
        while (it != index.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            candidates.push_back(GapCandidate{it->second,
                scoreGap(gapLength, length)});
            // The live scorer evaluates one representative for each length,
            // including the first >40 m slack representative, then stops.
            if (slack > 40) break;
            it = index.upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
        }
        std::sort(candidates.begin(), candidates.end(), [highSide](
            const GapCandidate& lhs, const GapCandidate& rhs) {
            if (lhs.score != rhs.score) return lhs.score < rhs.score;
            return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
        });
        return candidates;
    }

    void diagnosticCapture(int length, bool highSide, int sizeCohort,
                           StartIter baseline, StartIter selected,
                           std::size_t rolloutCount) {
        const auto event = diagTargets.find(static_cast<int>(operationIndex));
        if (event == diagTargets.end()) return;

        std::vector<GapCandidate> candidates;
        std::string poolName = "all";
        const std::set<std::pair<std::int64_t, std::int64_t>>* selectedIndex = &freeBySize;
        if (parityCohortMode) {
            selectedIndex = &freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            const auto preferred = diagnosticCandidates(
                *selectedIndex, length, highSide);
            if (!preferred.empty()) {
                candidates = preferred;
                poolName = "preferred";
            } else {
                selectedIndex = &freeBySizeShared;
                candidates = diagnosticCandidates(freeBySizeShared, length, highSide);
                poolName = candidates.empty() ? "none" : "shared";
            }
        } else {
            candidates = diagnosticCandidates(freeBySize, length, highSide);
        }

        std::size_t physicalFitCount = 0;
        std::size_t preferredFitCount = 0;
        std::size_t sharedFitCount = 0;
        std::size_t foreignFitCount = 0;
        std::size_t selectedPoolPhysicalCount = 0;
        std::vector<GapCandidate> physicalCandidates;
        for (const auto& [start, end] : freeByStart) {
            const std::int64_t gapLength = end - start;
            if (gapLength < length) continue;
            ++physicalFitCount;
            const int cohort = gapCohort.at(start);
            if (cohort == sizeCohort) ++preferredFitCount;
            else if (cohort == -1) ++sharedFitCount;
            else ++foreignFitCount;
            if (poolName == "all" ||
                (poolName == "preferred" && cohort == sizeCohort) ||
                (poolName == "shared" && cohort == -1)) {
                ++selectedPoolPhysicalCount;
            }
            physicalCandidates.push_back(GapCandidate{start, scoreGap(gapLength, length)});
        }
        const auto byScore = [highSide](const GapCandidate& lhs, const GapCandidate& rhs) {
            if (lhs.score != rhs.score) return lhs.score < rhs.score;
            return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
        };
        std::sort(physicalCandidates.begin(), physicalCandidates.end(), byScore);
        std::map<std::int64_t, std::size_t> physicalRankByStart;
        for (std::size_t i = 0; i < physicalCandidates.size(); ++i)
            physicalRankByStart.emplace(physicalCandidates[i].start, i + 1);

        std::size_t representativeCount = 0;
        if (poolName != "none") {
            auto it = selectedIndex->lower_bound({length, 0});
            while (it != selectedIndex->end()) {
                const std::int64_t gapLength = it->first;
                ++representativeCount;
                it = selectedIndex->upper_bound(
                    {gapLength, std::numeric_limits<std::int64_t>::max()});
            }
        }
        const std::size_t afterCapCount = recentLengths.empty()
            ? 0 : (representativeCount > candidates.size()
                ? representativeCount - candidates.size() : 0);
        const std::size_t emptyHistorySkippedCount = recentLengths.empty() &&
            representativeCount > candidates.size()
                ? representativeCount - candidates.size() : 0;

        std::vector<GapCandidate> mcCandidates =
            topGapCandidates(length, highSide, sizeCohort);
        std::map<std::int64_t, std::size_t> scorerRankByStart;
        for (std::size_t i = 0; i < candidates.size(); ++i)
            scorerRankByStart.emplace(candidates[i].start, i + 1);
        std::map<std::int64_t, std::size_t> mcRankByStart;
        for (std::size_t i = 0; i < mcCandidates.size(); ++i)
            mcRankByStart.emplace(mcCandidates[i].start, i + 1);

        const std::int64_t baselineStart = baseline == freeByStart.end() ? -1 : baseline->first;
        const std::int64_t baselineScore = baseline == freeByStart.end() ? -1
            : scoreGap(baseline->second - baseline->first, length);
        const std::int64_t selectedStart = selected == freeByStart.end() ? -1 : selected->first;
        const std::int64_t selectedScore = selected == freeByStart.end() ? -1
            : scoreGap(selected->second - selected->first, length);
        int selectedRank = -1;
        for (std::size_t i = 0; i < candidates.size(); ++i)
            if (candidates[i].start == selectedStart) selectedRank = static_cast<int>(i + 1);

        int baselineRank = -1;
        for (std::size_t i = 0; i < candidates.size(); ++i)
            if (candidates[i].start == baselineStart) baselineRank = static_cast<int>(i + 1);

        std::map<int, std::size_t> targetsByExpansion;
        for (const DiagTarget& target : event->second)
            ++targetsByExpansion[target.firstExpansionOp];
        candidateSummaryLog << operationIndex << ',' << length << ',' << event->second.size() << ',';
        bool firstExpansion = true;
        for (const auto& [expansion, count] : targetsByExpansion) {
            if (!firstExpansion) candidateSummaryLog << '|';
            firstExpansion = false;
            candidateSummaryLog << expansion << ':' << count;
        }
        std::string winnerReason;
        if (baseline == freeByStart.end()) winnerReason = "no_eligible_candidate";
        else if (rolloutCount == 0) winnerReason = "baseline_scorer";
        else if (selectedStart == baselineStart) winnerReason = "monte_carlo_kept_baseline";
        else winnerReason = "monte_carlo_override";
        candidateSummaryLog << ',' << parityCohortMode << ',' << sizeCohort << ','
            << highSide << ',' << poolName << ',' << physicalFitCount << ','
            << preferredFitCount << ',' << sharedFitCount << ',' << foreignFitCount << ','
            << selectedPoolPhysicalCount << ',' << representativeCount << ','
            << (selectedPoolPhysicalCount > representativeCount
                ? selectedPoolPhysicalCount - representativeCount : 0) << ','
            << candidates.size() << ',' << afterCapCount << ',' << emptyHistorySkippedCount << ','
            << baselineStart << ',' << baselineScore << ',' << baselineRank << ','
            << selectedStart << ',' << selectedScore << ',' << selectedRank << ','
            << winnerReason << ',' << rolloutCount << ',' << mcDecisionsUsed << ','
            << freeByStart.size() << ',' << activePipeCount << ',' << observedHistory.size() << '\n';

        std::map<std::int64_t, std::size_t> unionStarts = scorerRankByStart;
        for (const auto& [start, rank] : mcRankByStart) {
            (void)rank;
            unionStarts.emplace(start, 0);
        }
        for (const auto& [start, unused] : unionStarts) {
            (void)unused;
            const auto gap = freeByStart.find(start);
            if (gap == freeByStart.end()) throw std::runtime_error("candidate disappeared during capture");
            const std::int64_t gapLength = gap->second - gap->first;
            const std::int64_t slack = gapLength - length;
            const bool scored = scorerRankByStart.find(start) != scorerRankByStart.end();
            const bool mcRanked = mcRankByStart.find(start) != mcRankByStart.end();
            const std::size_t scorerRank = scored ? scorerRankByStart.at(start) : 0;
            const std::size_t mcRank = mcRanked ? mcRankByStart.at(start) : 0;
            const std::string scanStatus = !scored ? "mc_pool_only" :
                (recentLengths.empty() ? "scored_first_fit" :
                    (slack > 40 ? "scored_first_over40" : "scored"));
            candidateScoresLog << operationIndex << ',' << length << ',' << poolName << ','
                << highSide << ',' << start << ',' << gapLength << ',' << slack << ','
                << scoreGap(gapLength, length) << ',' << scorerRank << ',' << mcRank << ','
                << scanStatus << ',' << (start == baselineStart) << ','
                << (start == selectedStart) << ',' << (rolloutCount > 0 && start == selectedStart)
                << '\n';
        }

        for (const DiagTarget& target : event->second) {
            if (target.request != length || target.length < length)
                throw std::runtime_error("target pair/input mismatch");
            const auto actual = freeByStart.find(target.start);
            const bool sameGap = actual != freeByStart.end() && actual->second == target.end;
            const int targetCohort = sameGap ? gapCohort.at(target.start) : -9;
            const bool cohortEligible = sameGap && (!parityCohortMode ||
                targetCohort == sizeCohort || (targetCohort == -1 && poolName == "shared"));
            const std::int64_t targetScore = sameGap
                ? scoreGap(target.end - target.start, length) : -1;
            std::int64_t representativeStart = -1;
            if (sameGap) {
                auto representative = selectedIndex->lower_bound({target.length, 0});
                if (representative != selectedIndex->end() && representative->first == target.length)
                    representativeStart = representative->second;
            }
            int targetRank = -1;
            for (std::size_t i = 0; i < candidates.size(); ++i)
                if (candidates[i].start == target.start) targetRank = static_cast<int>(i + 1);

            const auto physicalRank = physicalRankByStart.find(target.start);
            const auto mcRank = mcRankByStart.find(target.start);
            const bool isRepresentative = representativeStart == target.start;

            std::string eligibility;
            if (!sameGap) {
                eligibility = "not_same_gap";
            } else if (!cohortEligible) {
                eligibility = poolName == "preferred" && targetCohort == -1
                    ? "shared_blocked_by_preferred" : "foreign_cohort";
            } else if (targetRank >= 0) {
                eligibility = "evaluated";
            } else if (representativeStart >= 0 && representativeStart != target.start) {
                eligibility = "same_size_shadowed";
            } else if (recentLengths.empty() && candidates.size() == 1 &&
                       candidates.front().start != target.start) {
                eligibility = "empty_history_first_fit";
            } else if (representativeStart == target.start && afterCapCount != 0) {
                eligibility = "after_first_over40_cap";
            } else {
                eligibility = "not_in_candidate_loop";
            }

            if (!sameGap || physicalRank == physicalRankByStart.end())
                throw std::runtime_error("target gap is absent from physical candidate universe");
            candidateTargetLog << operationIndex << ',' << target.firstExpansionOp << ','
                << length << ',' << target.gapId << ',' << target.birthOp << ','
                << target.start << ',' << target.end << ',' << target.length << ','
                << sameGap << ',' << targetCohort << ',' << parityCohortMode << ','
                << sizeCohort << ',' << highSide << ',' << poolName << ','
                << physicalRank->second << ',' << cohortEligible << ','
                << representativeStart << ',' << isRepresentative << ',' << targetScore << ','
                << targetRank << ',' << eligibility << ','
                << (eligibility == "same_size_shadowed"
                    ? "same_length_lower_address_representative"
                    : (eligibility == "shared_blocked_by_preferred"
                        ? "preferred_cohort_fit_exists"
                        : (eligibility == "foreign_cohort"
                            ? "no_preferred_or_shared_candidate_for_this_cohort"
                            : (eligibility == "after_first_over40_cap"
                                ? "candidate_size_after_first_over40_representative"
                                : (eligibility == "empty_history_first_fit"
                                    ? "no_history_returns_first_fitting_size"
                                    : "none"))))) << ','
                << candidates.size() << ',' << baselineStart << ',' << baselineScore << ','
                << baselineRank << ',' << selectedStart << ',' << selectedScore << ','
                << selectedRank << ',' << rolloutCount << ','
                << (mcRank == mcRankByStart.end() ? 0 : mcRank->second) << ','
                << mcDecisionsUsed << ',' << freeByStart.size() << ','
                << activePipeCount << ',' << observedHistory.size() << '\n';
        }
    }
#endif

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

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun << '\n';
#endif
            return 0;
        }
#if defined(EOF_SURVIVOR_DIAG)
        ++allocator.operationIndex;
#endif
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
    }
    return 0;
}
