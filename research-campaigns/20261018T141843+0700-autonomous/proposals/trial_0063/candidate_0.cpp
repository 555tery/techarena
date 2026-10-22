#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <tuple>
#include <utility>
#include <vector>

namespace {
using I = std::int64_t;
using U = std::uint64_t;
constexpr I kDigLength = 20;
constexpr std::size_t kHistoryWindow = 2048;
constexpr I kUnfitPenaltyScale = 60;
constexpr int kPrimalGapValueCap = 512;
constexpr int kRightEdgeMaxPipeLength = 4;
constexpr std::size_t kSameLengthRightRun = 46;
constexpr std::size_t kMcHistory = 256;
constexpr std::size_t kMcDepth = 4;
constexpr std::size_t kMcTrials = 12;
constexpr std::size_t kMcDecisionBudget = 32;
constexpr std::size_t kMcMaxGaps = 64;
constexpr std::size_t kMcMaxActivePipes = 4096;
constexpr I kMcMinimumMeanSavingM = 1;

struct Observation { int kind = 0, value = 0; };
struct SimPipe { int pid = 0; I start = 0; int length = 0, sizeCohort = 0; };
struct SimGap { I end = 0; int cohort = -1; };
struct GapCandidate { I start = 0, score = 0; };

int predictNextGeometricSize(const std::deque<int>& history, int current) {
    if (history.empty() || history.back() != current) return 0;
    auto it = history.rbegin();
    std::array<int, 3> sizes{};
    std::array<std::size_t, 3> counts{};
    std::size_t n = 0;
    while (it != history.rend() && n < sizes.size()) {
        int size = *it;
        while (it != history.rend() && *it == size) { ++counts[n]; ++it; }
        sizes[n++] = size;
    }
    if (n < 3 || sizes[0] != current || counts[0] < kSameLengthRightRun ||
        counts[1] < kSameLengthRightRun || counts[2] < kSameLengthRightRun) return 0;
    int previous = sizes[1], before = sizes[2];
    if (!(before < previous && previous < current)) return 0;
    if (2 * std::abs(current * before - previous * previous) > before) return 0;
    int predicted = (current * previous + before / 2) / before;
    return predicted > current && predicted <= 40 ? predicted : 0;
}

bool trendAlignedHighSide(const std::deque<int>& history, int length,
                          I start, I end, bool fallback) {
    int predicted = predictNextGeometricSize(history, length);
    if (predicted <= length || end - start <= length) return fallback;
    auto distance = [predicted](I x) {
        I residue = x % predicted;
        return std::min(residue, static_cast<I>(predicted) - residue);
    };
    I low = distance(start + length), high = distance(start);
    return high != low ? high < low : fallback;
}

struct RolloutState {
    bool confidentRecentAddress = false;
    std::map<I, SimGap> gaps;
    std::vector<SimPipe> active;
    I trenchLength = 0;
    int nextPid = 1;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};
    std::array<I, 41> lengthOccurrenceCount{};
    std::array<std::array<I, 2>, 41> removedLengthCohort{};
    bool parityCohortMode = false, runLeftDisabledBySmoothTrend = false;
    bool alternatingDeleteMode = false;
    int predictedDeletedParity = 1, lastDeletedPid = -1, lastDeletedLength = -1;
    std::size_t strideTwoDeleteTransitions = 0;

    bool hasSteadySizeTrend() const {
        if (recentLengths.size() < 128) return false;
        std::array<int, 3> sizes{};
        std::size_t n = 0;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (*it == previous) continue;
            sizes[n++] = *it;
            previous = *it;
            if (n == 3) break;
        }
        return n == 3 && sizes[0] - sizes[1] == sizes[1] - sizes[2];
    }
    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t n = 0; n < kSameLengthRightRun; ++n, ++it)
            if (*it != length) return false;
        return true;
    }
    bool hasSmoothSizeTrendWith(int length) const {
        if (recentLengths.empty()) return false;
        bool currentInHistory = recentLengths.back() == length;
        std::array<int, 2> prior{};
        std::size_t n = 0;
        bool first = true;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (first) {
                first = false; previous = *it;
                if (!currentInHistory) prior[n++] = *it;
                continue;
            }
            if (*it == previous) continue;
            previous = *it; prior[n++] = *it;
            if (n == 2) break;
        }
        return n == 2 && length - prior[0] == prior[0] - prior[1];
    }
    I placementStart(const SimGap& gap, I start, int length, bool high) const {
        return high ? gap.end - length : start;
    }
    void addFreeGap(I start, I end, int cohort) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto previous = std::prev(it);
            if (previous->second.end >= start) {
                if (previous->second.cohort != cohort) cohort = -1;
                start = previous->first;
                end = std::max(end, previous->second.end);
                gaps.erase(previous); it = gaps.lower_bound(start);
            }
        }
        while (it != gaps.end() && it->first <= end) {
            if (it->second.cohort != cohort) cohort = -1;
            end = std::max(end, it->second.end); it = gaps.erase(it);
        }
        gaps.emplace(start, SimGap{end, cohort});
    }
    void splitGap(I gapStart, int length, bool high) {
        auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        I start = it->first;
        SimGap gap = it->second;
        I placed = placementStart(gap, start, length, high);
        gaps.erase(it);
        if (start < placed) addFreeGap(start, placed, gap.cohort);
        if (placed + length < gap.end) addFreeGap(placed + length, gap.end, gap.cohort);
    }
    void recordLength(int length) {
        recentLengths.push_back(length); ++recentFrequency[length];
        if (recentLengths.size() > kHistoryWindow) {
            --recentFrequency[recentLengths.front()]; recentLengths.pop_front();
        }
    }
    I fitScore(I width, int length) const {
        I slack = width - length;
        I score = slack * static_cast<I>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                misses += recentFrequency[request];
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }
    std::optional<I> bestGap(int length, bool high, int cohort) const {
        bool preferred = false;
        if (parityCohortMode)
            for (const auto& [start, gap] : gaps)
                if (gap.end - start >= length && gap.cohort == cohort) {
                    preferred = true; break;
                }
        bool found = false;
        I bestStart = 0, bestScore = std::numeric_limits<I>::max();
        std::set<I> considered;
        for (const auto& [start, gap] : gaps) {
            I width = gap.end - start;
            if (width < length) continue;
            if (parityCohortMode &&
                (preferred ? gap.cohort != cohort : gap.cohort >= 0)) continue;
            if (!considered.insert(width).second && !(confidentRecentAddress && high)) continue;
            I score = fitScore(width, length);
            if (!found || score < bestScore || (score == bestScore &&
                ((high && start > bestStart) || (!high && start < bestStart)))) {
                found = true; bestStart = start; bestScore = score;
            }
        }
        return found ? std::optional<I>(bestStart) : std::nullopt;
    }
    void appendPipe(int length, I start, int cohort) {
        active.push_back(SimPipe{nextPid++, start, length, cohort});
        ++lengthOccurrenceCount[length]; recordLength(length);
    }
    void placeAtCandidate(I gapStart, int length, bool high) {
        auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        int cohort = static_cast<int>(lengthOccurrenceCount[length] % 2);
        I start = placementStart(it->second, gapStart, length, high);
        splitGap(gapStart, length, high); appendPipe(length, start, cohort);
    }
    void place(int length) {
        int cohort = static_cast<int>(lengthOccurrenceCount[length] % 2);
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        bool same = hasSameLengthRecentRun(length);
        bool geometric = !runLeftDisabledBySmoothTrend && same;
        bool reverse = runLeftDisabledBySmoothTrend && same && alternatingDeleteMode;
        bool high = geometric || reverse
            ? (reverse ? cohort == 0 : (nextPid & 1) == 0)
            : (alternatingDeleteMode ? ((nextPid & 1) != predictedDeletedParity)
               : (parityCohortMode ? cohort == 0
                  : (length <= kRightEdgeMaxPipeLength || same)));
        I start = -1;
        auto selected = bestGap(length, high, cohort);
        if (selected) {
            auto it = gaps.find(*selected);
            bool side = geometric ? trendAlignedHighSide(recentLengths, length,
                it->first, it->second.end, high) : high;
            start = placementStart(it->second, *selected, length, side);
            splitGap(*selected, length, side);
        }
        if (start < 0) {
            auto tail = gaps.end();
            if (!gaps.empty() && std::prev(gaps.end())->second.end == trenchLength)
                tail = std::prev(gaps.end());
            int owner = parityCohortMode ? cohort : -1;
            bool preserve = false;
            if (parityCohortMode && tail != gaps.end()) {
                owner = tail->second.cohort;
                preserve = owner >= 0 && owner != cohort;
                if (preserve) owner = cohort;
            }
            I tailStart = tail == gaps.end() || preserve ? trenchLength : tail->first;
            I deficit = std::max<I>(0, length - (trenchLength - tailStart));
            trenchLength += ((deficit + kDigLength - 1) / kDigLength) * kDigLength;
            if (tail != gaps.end() && !preserve) gaps.erase(tail);
            if (parityCohortMode && high && !preserve) {
                start = trenchLength - length;
                if (tailStart < start) addFreeGap(tailStart, start, owner);
            } else {
                start = tailStart;
                if (start + length < trenchLength)
                    addFreeGap(start + length, trenchLength, owner);
            }
        }
        appendPipe(length, start, cohort);
    }
    void recordDeletionPattern(int pid, int length) {
        if (lastDeletedPid >= 0 && lastDeletedLength == length && pid == lastDeletedPid + 2)
            ++strideTwoDeleteTransitions;
        else { strideTwoDeleteTransitions = 0; alternatingDeleteMode = false; }
        if (strideTwoDeleteTransitions >= 7) {
            alternatingDeleteMode = true; predictedDeletedParity = pid & 1;
        }
        lastDeletedPid = pid; lastDeletedLength = length;
    }
    void removeByRank(int permille) {
        if (active.empty()) return;
        std::size_t n = active.size();
        std::size_t rank = n <= 1 ? 0 : static_cast<std::size_t>(permille) * (n - 1) / 1000;
        std::size_t index = n - 1 - std::min(rank, n - 1);
        SimPipe pipe = active[index];
        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
        recordDeletionPattern(pipe.pid, pipe.length);
        ++removedLengthCohort[pipe.length][pipe.sizeCohort];
        I total = removedLengthCohort[pipe.length][0] + removedLengthCohort[pipe.length][1];
        I dominant = std::max(removedLengthCohort[pipe.length][0], removedLengthCohort[pipe.length][1]);
        if (total >= 8 && dominant * 100 >= total * 85 && hasSteadySizeTrend())
            parityCohortMode = true;
    }
    void apply(const Observation& event) {
        if (event.kind > 0) place(event.value);
        else if (event.kind < 0) removeByRank(event.value);
    }
};

struct Pipe { I start = 0; int length = 0; bool active = false; int sizeCohort = 0; };

// Exact geometric metadata, independent of any predicted deletion labels.
// Every live pipe belongs to one maximal touching increasing run and one
// maximal touching decreasing run. New PID is always the largest PID.
class MonotoneSpans {
    struct Span { I end = 0; int firstPid = 0, lastPid = 0; };
    using Index = std::map<I, Span>;
    Index increasing_, decreasing_;
    static void split(Index& index, const Pipe& pipe, const std::map<I, int>& live) {
        auto it = std::prev(index.upper_bound(pipe.start));
        I begin = it->first, end = pipe.start + pipe.length;
        Span original = it->second;
        index.erase(it);
        if (begin < pipe.start) {
            int last = live.find(pipe.start)->second;
            index.emplace(begin, Span{pipe.start, original.firstPid, last});
        }
        if (end < original.end) {
            int first = live.upper_bound(end)->second;
            index.emplace(end, Span{original.end, first, original.lastPid});
        }
    }
public:
    void birth(I start, int length, int pid) {
        I end = start + length, begin = start;
        int first = pid;
        auto left = increasing_.lower_bound(start);
        if (left != increasing_.begin()) {
            --left;
            if (left->second.end == start && left->second.lastPid < pid) {
                begin = left->first; first = left->second.firstPid;
                increasing_.erase(left);
            }
        }
        increasing_.emplace(begin, Span{end, first, pid});
        I finish = end;
        int last = pid;
        auto right = decreasing_.find(end);
        if (right != decreasing_.end() && pid > right->second.firstPid) {
            finish = right->second.end; last = right->second.lastPid;
            decreasing_.erase(right);
        }
        decreasing_.emplace(start, Span{finish, pid, last});
    }
    void death(const Pipe& pipe, const std::map<I, int>& live) {
        split(increasing_, pipe, live); split(decreasing_, pipe, live);
    }
    std::pair<int, I> extension(I start, I end, bool high) const {
        if (high) {
            auto it = decreasing_.find(end);
            if (it == decreasing_.end() || it->second.firstPid == it->second.lastPid)
                return {0, 0};
            return {it->second.firstPid, it->second.end - it->first};
        }
        auto it = increasing_.upper_bound(start);
        if (it == increasing_.begin()) return {0, 0};
        --it;
        if (it->second.end != start || it->second.firstPid == it->second.lastPid)
            return {0, 0};
        return {it->second.lastPid, it->second.end - it->first};
    }
};

class CensoredLifetimeModel {
    static constexpr std::array<U, 8> kLower{0, 16, 64, 256, 1024, 4096, 16384, 65536};
    static constexpr std::size_t kBins = kLower.size();
    struct Record { U born = 0; int length = 0; bool active = false; };
    struct Cell { U completedExposure = 0, birthSum = 0, active = 0, deaths = 0; };
    struct Estimate { double mean = 0, error = 0; };
    std::vector<Record> records_{Record{}};
    std::array<std::array<Cell, kBins>, 41> cells_{};
    std::array<std::array<Estimate, kBins>, 41> rates_{};
    std::array<std::size_t, kBins> nextCrossing_{};
    U clock_ = 0;
    double referenceRate_ = 0, referenceError_ = 0;
    bool fitted_ = false;
    static std::size_t ageBin(U age) {
        std::size_t bin = 0;
        while (bin + 1 < kBins && age >= kLower[bin + 1]) ++bin;
        return bin;
    }
    void enter(const Record& record, std::size_t bin) {
        auto& cell = cells_[record.length][bin];
        ++cell.active; cell.birthSum += record.born;
    }
    void leave(const Record& record, std::size_t bin, U age) {
        auto& cell = cells_[record.length][bin];
        cell.completedExposure += age - kLower[bin];
        --cell.active; cell.birthSum -= record.born;
    }
    U exposure(const Cell& cell, std::size_t bin) const {
        U outstanding = cell.active == 0 ? 0 :
            cell.active * (clock_ - kLower[bin]) - cell.birthSum;
        return cell.completedExposure + outstanding;
    }
    Estimate predict(int length, U age) const {
        Estimate result;
        U end = age + kHistoryWindow;
        std::size_t bin = ageBin(age);
        while (age < end) {
            U next = bin + 1 < kBins ? std::min(end, kLower[bin + 1]) : end;
            double weight = static_cast<double>(next - age) / kHistoryWindow;
            result.mean += weight * rates_[length][bin].mean;
            result.error += weight * rates_[length][bin].error;
            age = next;
            if (age < end) ++bin;
        }
        return result;
    }
    double adjustedRatio(int length, U age) const {
        if (!fitted_) return 1;
        Estimate prediction = predict(length, age);
        double margin = 2 * (prediction.error + referenceError_);
        double supported = referenceRate_;
        if (prediction.mean - margin > referenceRate_) supported = prediction.mean - margin;
        else if (prediction.mean + margin < referenceRate_) supported = prediction.mean + margin;
        return std::clamp(supported / referenceRate_, 0.5, 2.0);
    }
public:
    CensoredLifetimeModel() { nextCrossing_.fill(1); }
    void advance() {
        ++clock_;
        for (std::size_t bin = 1; bin < kBins; ++bin) {
            auto& cursor = nextCrossing_[bin];
            while (cursor < records_.size() && clock_ - records_[cursor].born >= kLower[bin]) {
                const Record& record = records_[cursor++];
                if (!record.active) continue;
                leave(record, bin - 1, kLower[bin]); enter(record, bin);
            }
        }
    }
    void observeBirth(int length) {
        records_.push_back(Record{clock_, length, true}); enter(records_.back(), 0);
    }
    void observeDeletion(std::size_t pid) {
        Record& record = records_[pid];
        U age = clock_ - record.born;
        leave(record, ageBin(age), age);
        ++cells_[record.length][ageBin(age == 0 ? 0 : age - 1)].deaths;
        record.active = false;
    }
    bool fit(double priorHazard) {
        fitted_ = false;
        if (!(priorHazard > 0)) return false;
        constexpr double priorEvents = 8;
        for (std::size_t bin = 0; bin < kBins; ++bin) {
            double pooledExposure = 0, pooledDeaths = 0;
            for (int length = 1; length <= 40; ++length) {
                pooledExposure += static_cast<double>(exposure(cells_[length][bin], bin));
                pooledDeaths += static_cast<double>(cells_[length][bin].deaths);
            }
            double pooledDenominator = pooledExposure + priorEvents / priorHazard;
            double pooledRate = (pooledDeaths + priorEvents) / pooledDenominator;
            double pooledError = std::sqrt(pooledDeaths + priorEvents) / pooledDenominator;
            for (int length = 1; length <= 40; ++length) {
                const auto& cell = cells_[length][bin];
                double borrowed = priorEvents / pooledRate;
                double denominator = static_cast<double>(exposure(cell, bin)) + borrowed;
                double shape = static_cast<double>(cell.deaths) + priorEvents;
                rates_[length][bin] = Estimate{shape / denominator,
                    std::sqrt(shape) / denominator + borrowed / denominator * pooledError};
            }
        }
        double sumRate = 0, sumError = 0;
        U population = 0;
        for (int length = 1; length <= 40; ++length)
            for (std::size_t bin = 0; bin < kBins; ++bin) {
                const auto& cell = cells_[length][bin];
                if (cell.active == 0) continue;
                U age = clock_ - cell.birthSum / cell.active;
                Estimate prediction = predict(length, age);
                sumRate += static_cast<double>(cell.active) * prediction.mean;
                sumError += static_cast<double>(cell.active) * prediction.error;
                population += cell.active;
            }
        if (population == 0) return false;
        referenceRate_ = sumRate / static_cast<double>(population);
        referenceError_ = sumError / static_cast<double>(population);
        fitted_ = referenceRate_ > 0;
        return fitted_;
    }
    double existingRisk(int pid) const {
        const Record& record = records_[static_cast<std::size_t>(pid)];
        return adjustedRatio(record.length, clock_ - record.born);
    }
    double newRisk(int length) const { return adjustedRatio(length, 0); }
};

class Allocator {
public:
    U releaseEpoch = 0, recencyDifferentSelections = 0;
    std::map<I, U> gapFreedAt;
    std::set<std::tuple<I, U, I>> freeBySizeAge;
    std::map<I, I> freeByStart;
    std::map<I, int> activeByEnd;
    std::set<std::pair<I, I>> freeBySize;
    std::map<I, int> gapCohort;
    std::array<std::set<std::pair<I, I>>, 2> freeBySizeCohort;
    std::set<std::pair<I, I>> freeBySizeShared;
    std::vector<Pipe> pipes{Pipe{}};
    MonotoneSpans monotoneSpans;
    U spanTieQueries = 0, spanTieAlternatives = 0, spanTieChanges = 0;
    U spanTieExtendedVolume = 0;
    bool spanTieProfile = false;
    I trenchLength = 0;
    std::deque<std::pair<int, int>> completedPlacementRuns;
    int observedRunLength = -1, observedRunCount = 0;
    bool cohortSlabActive = false, cohortSlabExpanded = false;
    int cohortSlabExpectedCount = 0, cohortSlabDeleteParity = 0;
    int cohortSlabDeleteCount = 0, cohortSlabDeletedUsed = 0, cohortSlabSurvivorUsed = 0;
    int cohortSlabGapSinkRemaining = 0, cohortSlabTailPipeCount = 0, cohortSlabUsed = 0;
    I cohortSlabBase = 0, cohortSlabEnd = 0;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};
    std::array<I, 41> lengthOccurrenceCount{};
    std::array<std::array<I, 2>, 41> removedLengthCohort{};
    bool parityCohortMode = false, runLeftDisabledBySmoothTrend = false;
    bool alternatingDeleteMode = false;
    int predictedDeletedParity = 1, lastDeletedPid = -1, lastDeletedLength = -1;
    std::size_t strideTwoDeleteTransitions = 0;
    std::vector<int> activeFenwick = std::vector<int>(200001, 0);
    std::size_t activePipeCount = 0;
    std::deque<Observation> observedHistory;
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::deque<int> recentDeleteRanksPermille;
    bool lifoLaneDisabledForScale = false;
    std::array<I, kPrimalGapValueCap + 2> primalGapCounts{};
    std::array<int, kHistoryWindow> primalEventHistory{};
    std::array<int, 41> primalRecentRequests{};
    std::array<double, kPrimalGapValueCap + 1> primalGapValue{};
    std::size_t primalEventPosition = 0;
    int primalRecentDeletes = 0;
    U primalStep = 0, primalModelStep = 0;
    int primalComputedLimit = 0;
    bool primalModelDirty = true;
    std::size_t primalScoredDecisions = 0, primalChangedSelections = 0;
    std::size_t primalCapFallbacks = 0, primalModelRebuilds = 0;
    U primalFirstActivationEvent = 0;
    int activeRunFirstPid = 1;
    std::array<std::size_t, 2> activeRunDeleteParityCount{};
    int lastCompletedDeleteRelativeParity = -1, previousCompletedDeleteRelativeParity = -1;
    CensoredLifetimeModel lifetimeModel;
    std::array<double, 41> causalRequestRate{};
    std::array<std::array<double, kPrimalGapValueCap + 1>, 2> causalGapValue{};
    double causalBaseExpiry = 0;
    int causalComputedLimit = 0;
    bool causalRiskReady = false;
    U expansionGateOpportunities = 0, expansionGatePasses = 0;
    U unitProfileSuppressedExpansions = 0;

    bool hasLongAdditiveSizeTrend(int current) const {
        if (current < 3 || current >= 40 || observedRunCount < 46) return false;
        std::array<int, 3> sizes{current, 0, 0}, counts{observedRunCount, 0, 0};
        auto it = recentLengths.rbegin();
        while (it != recentLengths.rend() && *it == current) ++it;
        for (std::size_t run = 1; run < 3; ++run) {
            if (it == recentLengths.rend()) return false;
            sizes[run] = *it;
            while (it != recentLengths.rend() && *it == sizes[run]) { ++counts[run]; ++it; }
            if (counts[run] < 46) return false;
        }
        return sizes[0] == sizes[1] + 1 && sizes[1] == sizes[2] + 1;
    }
    bool alignForNextAdditiveSize(int length, I start, bool fallback) const {
        I modulus = length + 1;
        auto distance = [modulus](I x) {
            I residue = x % modulus; return std::min(residue, modulus - residue);
        };
        I low = distance(start + length), high = distance(start);
        return high != low ? high < low : fallback;
    }
    int predictEarlyNextGeometricSize(int current) const {
        if (completedPlacementRuns.size() != 1 || observedRunCount < 46 ||
            observedRunCount > 1024 || !alternatingDeleteMode ||
            strideTwoDeleteTransitions < 7 || activePipeCount > 4096 ||
            freeByStart.size() > 4096) return 0;
        auto previous = completedPlacementRuns.back();
        if (previous.second < 46 || previous.first <= 0 || lastDeletedLength != previous.first ||
            current != previous.first * 2 || current > 20) return 0;
        int predicted = current * 2;
        return predicted <= 40 ? predicted : 0;
    }
    bool hasLifoDeletionConfidence() const {
        if (activePipeCount < 128 || recentDeleteRanksPermille.size() < 48) return false;
        std::size_t top = 0, shortCount = 0;
        for (int rank : recentDeleteRanksPermille) if (rank <= 50) ++top;
        if (top * 100 < recentDeleteRanksPermille.size() * 80) return false;
        for (int length : recentLengths) if (length <= 8) ++shortCount;
        return recentLengths.size() >= 64 && shortCount * 100 >= recentLengths.size() * 90;
    }
    bool hasYoungTailNeighbor(I start) const {
        auto it = activeByEnd.find(start);
        return it != activeByEnd.end() && rankFromNewestPermille(it->second) <= 50;
    }
    bool unitDominantRecentProfile() const {
        if (recentLengths.size() < 128) return false;
        std::size_t window = std::min<std::size_t>(recentLengths.size(), 2048), units = 0;
        auto it = recentLengths.rbegin();
        for (std::size_t n = 0; n < window; ++n, ++it) if (*it == 1) ++units;
        return units * 100 >= window * 85;
    }
    bool useLifoStackLane(int length) const {
        if (lifoLaneDisabledForScale || activePipeCount < 128 || length > 8 ||
            recentDeleteRanksPermille.size() < 48) return false;
        return hasLifoDeletionConfidence();
    }

    void place(int length) {
        lifetimeModel.advance();
        spanTieProfile = false;
        if (observedRunLength != length) {
            if (observedRunCount > 0) {
                completedPlacementRuns.emplace_back(observedRunLength, observedRunCount);
                if (completedPlacementRuns.size() > 8) completedPlacementRuns.pop_front();
                std::size_t total = activeRunDeleteParityCount[0] + activeRunDeleteParityCount[1];
                std::size_t dominant = std::max(activeRunDeleteParityCount[0], activeRunDeleteParityCount[1]);
                if (total >= 8 && dominant * 100 >= total * 85) {
                    int parity = activeRunDeleteParityCount[0] > activeRunDeleteParityCount[1] ? 0 : 1;
                    previousCompletedDeleteRelativeParity = lastCompletedDeleteRelativeParity;
                    lastCompletedDeleteRelativeParity = parity ^ (activeRunFirstPid & 1);
                } else {
                    previousCompletedDeleteRelativeParity = lastCompletedDeleteRelativeParity = -1;
                }
            }
            observedRunLength = length; observedRunCount = 0;
            activeRunFirstPid = static_cast<int>(pipes.size());
            activeRunDeleteParityCount = {};
            cohortSlabActive = false; beginCohortSlab(length);
        }
        ++observedRunCount;
        int sizeCohort = static_cast<int>(lengthOccurrenceCount[length] % 2);
        if (activePipeCount > kMcMaxActivePipes) lifoLaneDisabledForScale = true;
        bool lifoStackLane = length > kRightEdgeMaxPipeLength && useLifoStackLane(length);
        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {
            int pid = static_cast<int>(pipes.size());
            bool predictedDeleted = (pid & 1) == cohortSlabDeleteParity;
            I start = -1;
            bool tailPlacement = true;
            if (!predictedDeleted && cohortSlabGapSinkRemaining > 0) {
                auto reusable = bestFittingGapBefore(length, false, sizeCohort, cohortSlabBase);
                if (reusable != freeByStart.end()) {
                    start = consumeAtSide(reusable, length, false);
                    --cohortSlabGapSinkRemaining; tailPlacement = false;
                }
            }
            if (tailPlacement) {
                if (predictedDeleted) {
                    start = cohortSlabBase + static_cast<I>(cohortSlabDeletedUsed++) * length;
                } else {
                    start = cohortSlabBase + static_cast<I>(cohortSlabDeleteCount + cohortSlabSurvivorUsed++) * length;
                }
            }
            I digs = 0;
            if (tailPlacement && !cohortSlabExpanded) {
                I missing = cohortSlabEnd - trenchLength;
                digs = missing > 0 ? (missing + kDigLength - 1) / kDigLength : 0;
                trenchLength += digs * kDigLength; cohortSlabExpanded = true;
                I occupiedEnd = cohortSlabBase + static_cast<I>(cohortSlabTailPipeCount) * length;
                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);
            }
            printPlacement(digs, start);
            pipes.push_back(Pipe{start, length, true, sizeCohort});
            activeByEnd.emplace(start + length, pid);
            monotoneSpans.birth(start, length, pid);
            fenwickAdd(pid, 1); ++activePipeCount; ++lengthOccurrenceCount[length];
            recordLength(length); recordObservation(Observation{1, length}); recordPrimalEvent(length);
            if (++cohortSlabUsed >= cohortSlabExpectedCount) cohortSlabActive = false;
            return;
        }
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        bool same = hasSameLengthRecentRun(length);
        bool geometric = !runLeftDisabledBySmoothTrend && same;
        bool reverse = runLeftDisabledBySmoothTrend && same && alternatingDeleteMode;
        bool runLeftActive = geometric || reverse;
        bool additive = hasLongAdditiveSizeTrend(length);
        bool high = lifoStackLane || (runLeftActive
            ? (reverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || same))));
        I start = -1;
        int predicted = predictEarlyNextGeometricSize(length);
        auto gap = bestFittingGap(length, high, sizeCohort);
        bool capacityChoice = false;
        if (predicted > length && ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)) {
            auto projected = chooseCounterfactualCapacityGap(length, predicted, high, sizeCohort, gap);
            if (projected.first != freeByStart.end()) {
                gap = projected.first; high = projected.second; capacityChoice = true;
            }
        }
        if (gap != freeByStart.end()) {
            if (additive) high = alignForNextAdditiveSize(length, gap->first, high);
            else if (geometric)
                high = trendAlignedHighSide(recentLengths, length, gap->first, gap->second, high);
            if (lifoStackLane) high = true;
            I selected = additive || capacityChoice ? gap->first
                : chooseGapWithRollout(length, high, sizeCohort, gap);
            if (selected >= 0) gap = freeByStart.find(selected);
            if (!additive && !capacityChoice && !runLeftActive && !alternatingDeleteMode &&
                observedRunCount < static_cast<int>(kSameLengthRightRun))
                gap = chooseMonotoneSpanTie(gap, high);
            start = consumeAtSide(gap, length, high);
        }
        I digs = 0;
        if (start < 0) {
            auto tail = tailGap();
            int owner = parityCohortMode ? sizeCohort : -1;
            bool preserve = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                owner = gapCohort.at(tail->first);
                preserve = owner >= 0 && owner != sizeCohort;
                if (preserve) owner = sizeCohort;
            }
            I tailStart = tail == freeByStart.end() || preserve ? trenchLength : tail->first;
            I deficit = std::max<I>(0, length - (trenchLength - tailStart));
            digs = (deficit + kDigLength - 1) / kDigLength;
            I newLength = trenchLength + digs * kDigLength;
            bool baseOffset = digs > 0 && activePipeCount > 4096 && !preserve &&
                newLength - (tailStart + length) > 0 && hasLifoDeletionConfidence() &&
                hasYoungTailNeighbor(tailStart);
            bool suppress = baseOffset && unitDominantRecentProfile();
            bool offset = baseOffset && !suppress;
            if (suppress) ++unitProfileSuppressedExpansions;
            if (digs > 0) ++expansionGateOpportunities;
            if (offset) ++expansionGatePasses;
            if (tail != freeByStart.end() && !preserve) eraseGap(tail);
            trenchLength = newLength;
            if ((parityCohortMode && high && !preserve) || offset) {
                start = trenchLength - length;
                if (tailStart < start) addFreeGap(tailStart, start, owner);
            } else {
                start = tailStart;
                if (start + length < trenchLength) addFreeGap(start + length, trenchLength, owner);
            }
        }
        printPlacement(digs, start);
        int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        activeByEnd.emplace(start + length, pid);
        monotoneSpans.birth(start, length, pid);
        fenwickAdd(pid, 1); ++activePipeCount; ++lengthOccurrenceCount[length];
        recordLength(length); recordObservation(Observation{1, length}); recordPrimalEvent(length);
    }

    void remove(I pid) {
        if (pid <= 0 || static_cast<U>(pid) >= static_cast<U>(pipes.size()) ||
            !pipes[static_cast<std::size_t>(pid)].active) {
            printInvalidPidFallback(); return;
        }
        std::size_t index = static_cast<std::size_t>(pid);
        lifetimeModel.advance();
        int rank = rankFromNewestPermille(static_cast<int>(index));
        Pipe pipe = pipes[index];
        lifetimeModel.observeDeletion(index);
        activeByEnd.erase(pipe.start + pipe.length);
        monotoneSpans.death(pipe, activeByEnd);
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        fenwickAdd(static_cast<int>(index), -1); --activePipeCount;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, ++releaseEpoch);
        recordDeletionPattern(static_cast<int>(index), pipe.length); recordPrimalEvent(-1);
        if (static_cast<int>(index) >= activeRunFirstPid)
            ++activeRunDeleteParityCount[index & 1U];
        ++removedLengthCohort[pipe.length][pipe.sizeCohort];
        I total = removedLengthCohort[pipe.length][0] + removedLengthCohort[pipe.length][1];
        I dominant = std::max(removedLengthCohort[pipe.length][0], removedLengthCohort[pipe.length][1]);
        if (total >= 8 && dominant * 100 >= total * 85 && hasSteadySizeTrend()) parityCohortMode = true;
        recordObservation(Observation{-1, rank});
    }

private:
    using StartIter = std::map<I, I>::iterator;
    void fenwickAdd(int index, int delta) {
        int limit = static_cast<int>(activeFenwick.size());
        for (int p = index; p < limit; p += p & -p) activeFenwick[p] += delta;
    }
    int fenwickPrefix(int index) const {
        int sum = 0;
        for (int p = index; p > 0; p -= p & -p) sum += activeFenwick[p];
        return sum;
    }
    int rankFromNewestPermille(int pid) const {
        if (activePipeCount <= 1) return 0;
        std::size_t newer = activePipeCount - static_cast<std::size_t>(fenwickPrefix(pid));
        return static_cast<int>(newer * 1000U / (activePipeCount - 1));
    }
    StartIter chooseMonotoneSpanTie(StartIter parent, bool high) {
        if (!spanTieProfile || parent == freeByStart.end()) return parent;
        ++spanTieQueries;
        I width = parent->second - parent->first;
        auto first = freeBySize.lower_bound({width, 0});
        auto after = freeBySize.upper_bound({width, std::numeric_limits<I>::max()});
        auto ageAfter = freeBySizeAge.upper_bound({width,
            std::numeric_limits<U>::max(), std::numeric_limits<I>::max()});
        std::array<I, 4> starts{parent->first, first->second,
            std::prev(after)->second, std::get<2>(*std::prev(ageAfter))};
        auto value = [&](StartIter gap) {
            auto [tip, volume] = monotoneSpans.extension(gap->first, gap->second, high);
            return tip > 0 && rankFromNewestPermille(tip) <= 50 ? volume : I{0};
        };
        StartIter best = parent;
        I original = value(parent), bestValue = original;
        for (std::size_t i = 1; i < starts.size(); ++i) {
            bool duplicate = false;
            for (std::size_t j = 0; j < i; ++j) if (starts[j] == starts[i]) duplicate = true;
            if (duplicate) continue;
            ++spanTieAlternatives;
            auto gap = freeByStart.find(starts[i]);
            I candidate = value(gap);
            if (candidate > bestValue) { best = gap; bestValue = candidate; }
        }
        if (best != parent) {
            ++spanTieChanges;
            spanTieExtendedVolume += static_cast<U>(bestValue - original);
        }
        return best;
    }
    void recordDeletionPattern(int pid, int length) {
        if (lastDeletedPid >= 0 && lastDeletedLength == length && pid == lastDeletedPid + 2)
            ++strideTwoDeleteTransitions;
        else { strideTwoDeleteTransitions = 0; alternatingDeleteMode = false; }
        if (strideTwoDeleteTransitions >= 7) {
            alternatingDeleteMode = true; predictedDeletedParity = pid & 1;
        }
        lastDeletedPid = pid; lastDeletedLength = length;
    }
    void beginCohortSlab(int length) {
        if (completedPlacementRuns.size() < 2 || !alternatingDeleteMode) return;
        auto previous = completedPlacementRuns[completedPlacementRuns.size() - 2];
        auto last = completedPlacementRuns.back();
        if (!(previous.first < last.first && last.first < length) || lastDeletedLength != last.first) return;
        int step = length - last.first, nextSize = length + step;
        if (nextSize > 40) return;
        bool staircase = last.first - previous.first == step && step == 1;
        int tolerance = std::max(10, std::max(previous.second, last.second) / 10);
        if (std::abs(previous.second - last.second) > tolerance) return;
        int expected = (previous.second + last.second) / 2;
        if (expected < 64) return;
        int deleteParity = predictedDeletedParity;
        if (lastCompletedDeleteRelativeParity >= 0 &&
            previousCompletedDeleteRelativeParity == lastCompletedDeleteRelativeParity)
            deleteParity = (activeRunFirstPid & 1) ^ lastCompletedDeleteRelativeParity;
        int firstPid = static_cast<int>(pipes.size());
        int deleteCount = expected / 2 + ((expected & 1) && (firstPid & 1) == deleteParity ? 1 : 0);
        int survivorCount = expected - deleteCount;
        int firstOccurrenceParity = static_cast<int>(lengthOccurrenceCount[length] & 1);
        int survivorCohort = firstOccurrenceParity ^ ((firstPid & 1) == deleteParity ? 1 : 0);
        I reusable = 0;
        for (const auto& [start, end] : freeByStart) {
            if (parityCohortMode) {
                int owner = gapCohort.at(start);
                if (owner >= 0 && owner != survivorCohort) continue;
            }
            reusable = std::min<I>(survivorCount, reusable + (end - start) / length);
            if (reusable >= survivorCount) break;
        }
        int survivorGaps = static_cast<int>(reusable);
        int tailCount = expected - survivorGaps;
        I futureCapacity = static_cast<I>(deleteCount) * length / nextSize;
        if (futureCapacity < 64) {
            if (!staircase) return;
            I existing = 0;
            for (const auto& [start, end] : freeByStart) {
                if (parityCohortMode) {
                    int owner = gapCohort.at(start);
                    if (owner >= 0 && owner != 0) continue;
                }
                existing += (end - start) / nextSize;
            }
            if (futureCapacity <= existing) return;
        }
        I raw = static_cast<I>(tailCount) * length;
        I allocated = ((raw + kDigLength - 1) / kDigLength) * kDigLength;
        cohortSlabActive = true; cohortSlabExpanded = false;
        cohortSlabExpectedCount = expected; cohortSlabDeleteParity = deleteParity;
        cohortSlabDeleteCount = deleteCount;
        cohortSlabDeletedUsed = cohortSlabSurvivorUsed = 0;
        cohortSlabGapSinkRemaining = survivorGaps; cohortSlabTailPipeCount = tailCount;
        cohortSlabUsed = 0; cohortSlabBase = trenchLength; cohortSlabEnd = trenchLength + allocated;
    }
    void recordObservation(const Observation& event) {
        observedHistory.push_back(event);
        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();
        if (event.kind < 0) {
            recentDeleteRanksPermille.push_back(event.value);
            if (recentDeleteRanksPermille.size() > 64) recentDeleteRanksPermille.pop_front();
        }
    }
    void recordPrimalEvent(int event) {
        if (event > 0) lifetimeModel.observeBirth(event);
        int old = primalEventHistory[primalEventPosition];
        if (old > 0) {
            if (--primalRecentRequests[old] == 0) primalModelDirty = true;
        } else if (old < 0) {
            if (--primalRecentDeletes == 0) primalModelDirty = true;
        }
        primalEventHistory[primalEventPosition] = event;
        primalEventPosition = (primalEventPosition + 1) % primalEventHistory.size();
        if (event > 0) {
            if (primalRecentRequests[event]++ == 0) primalModelDirty = true;
        } else if (event < 0) {
            if (primalRecentDeletes++ == 0) primalModelDirty = true;
        }
        ++primalStep;
    }
    bool hasRecentPrimalDemand() const {
        for (int length = 1; length <= 40; ++length)
            if (primalRecentRequests[length] > 0) return true;
        return false;
    }
    void rebuildPrimalGapValues(int maxGap) {
        std::array<double, 41> rate{};
        I fitting = primalGapCounts[kPrimalGapValueCap + 1];
        for (int gap = kPrimalGapValueCap; gap >= 1; --gap) {
            fitting += primalGapCounts[gap];
            if (gap <= 40) rate[gap] = static_cast<double>(primalRecentRequests[gap]) /
                static_cast<double>(std::max<I>(1, fitting));
        }
        double expiry = 2.0 * primalRecentDeletes /
            static_cast<double>(std::max<std::size_t>(1, activePipeCount));
        primalGapValue.fill(0);
        for (int gap = 1; gap <= maxGap; ++gap) {
            int top = std::min(gap, 40);
            if (expiry == 0) {
                for (int request = 1; request <= top; ++request)
                    if (rate[request] > 0)
                        primalGapValue[gap] = std::max(primalGapValue[gap],
                            request + primalGapValue[gap - request]);
                continue;
            }
            std::array<double, 41> reward{};
            U active = 0;
            double numerator = 0, denominator = expiry;
            for (int request = 1; request <= top; ++request) {
                if (rate[request] == 0) continue;
                reward[request] = request + primalGapValue[gap - request];
                numerator += rate[request] * reward[request]; denominator += rate[request];
                active |= U{1} << static_cast<unsigned>(request);
            }
            double estimate = numerator / denominator;
            for (;;) {
                bool removed = false;
                for (int request = 1; request <= top; ++request) {
                    U bit = U{1} << static_cast<unsigned>(request);
                    if ((active & bit) && reward[request] < estimate) {
                        numerator -= rate[request] * reward[request]; denominator -= rate[request];
                        active &= ~bit; removed = true;
                    }
                }
                if (!removed) break;
                estimate = numerator / denominator;
            }
            primalGapValue[gap] = std::clamp(estimate, 0.0, static_cast<double>(gap));
        }
        causalRequestRate = rate; causalBaseExpiry = expiry; causalComputedLimit = 0;
        causalRiskReady = !parityCohortMode && activePipeCount > kMcMaxActivePipes &&
            expiry > 0 && lifetimeModel.fit(expiry / (2.0 * kHistoryWindow));
        primalModelStep = primalStep; primalComputedLimit = maxGap;
        primalModelDirty = false; ++primalModelRebuilds;
    }
    bool ensurePrimalGapValues(int maxGap) {
        if (maxGap <= 0 || maxGap > kPrimalGapValueCap) return false;
        if (primalModelDirty || primalStep - primalModelStep >= 64 || maxGap > primalComputedLimit)
            rebuildPrimalGapValues(maxGap);
        return hasRecentPrimalDemand();
    }
    void rebuildCausalGapValues(int maxGap) {
        for (std::size_t model = 0; model < 2; ++model) {
            auto& value = causalGapValue[model]; value.fill(0);
            double expiry = causalBaseExpiry * (model == 0 ? 0.5 : 2.0);
            for (int gap = 1; gap <= maxGap; ++gap) {
                int top = std::min(gap, 40);
                std::array<double, 41> reward{};
                U active = 0;
                double numerator = 0, denominator = expiry;
                for (int request = 1; request <= top; ++request) {
                    double rate = causalRequestRate[request];
                    if (rate == 0) continue;
                    reward[request] = request + value[gap - request];
                    numerator += rate * reward[request]; denominator += rate;
                    active |= U{1} << static_cast<unsigned>(request);
                }
                double estimate = numerator / denominator;
                for (;;) {
                    bool removed = false;
                    for (int request = 1; request <= top; ++request) {
                        U bit = U{1} << static_cast<unsigned>(request);
                        if ((active & bit) && reward[request] < estimate) {
                            numerator -= causalRequestRate[request] * reward[request];
                            denominator -= causalRequestRate[request]; active &= ~bit; removed = true;
                        }
                    }
                    if (!removed) break;
                    estimate = numerator / denominator;
                }
                value[gap] = std::clamp(estimate, 0.0, static_cast<double>(gap));
            }
        }
        causalComputedLimit = maxGap;
    }
    double causalValueAt(int gap, double factor) const {
        double base = primalGapValue[gap];
        if (factor <= 1) return base + 2 * (1 - factor) * (causalGapValue[0][gap] - base);
        return base + (factor - 1) * (causalGapValue[1][gap] - base);
    }
    double primalGapLoss(I width, int length) const {
        return primalGapValue[static_cast<std::size_t>(width)] -
            primalGapValue[static_cast<std::size_t>(width - length)];
    }
    double causalPrimalLoss(StartIter gap, int length, bool high, int limit, double fresh) {
        I width = gap->second - gap->first;
        double leftRisk = 1, rightRisk = 1;
        auto left = activeByEnd.find(gap->first);
        if (left != activeByEnd.end()) leftRisk = lifetimeModel.existingRisk(left->second);
        auto right = activeByEnd.upper_bound(gap->second);
        if (right != activeByEnd.end() && pipes[right->second].start == gap->second)
            rightRisk = lifetimeModel.existingRisk(right->second);
        double original = 0.5 * (leftRisk + rightRisk);
        double remaining = 0.5 * (fresh + (high ? leftRisk : rightRisk));
        if (original == 1 && remaining == 1) return primalGapLoss(width, length);
        if (causalComputedLimit < limit) rebuildCausalGapValues(limit);
        return causalValueAt(static_cast<int>(width), original) -
            causalValueAt(static_cast<int>(width) - length, remaining);
    }
    StartIter chooseCausalLifetimeGap(const std::vector<std::pair<I, I>>& candidates,
                                     int length, bool high, StartIter baseline) {
        if (!causalRiskReady || alternatingDeleteMode ||
            observedRunCount >= static_cast<int>(kSameLengthRightRun) || candidates.size() < 2)
            return baseline;
        StartIter challenger = freeByStart.end();
        double bestScore = std::numeric_limits<double>::infinity();
        for (const auto& [width, start] : candidates) {
            if (start == baseline->first) continue;
            double score = primalGapLoss(width, length);
            bool better = score + 1e-9 < bestScore;
            bool tied = !(bestScore + 1e-9 < score) && !(score + 1e-9 < bestScore);
            bool address = challenger != freeByStart.end() &&
                ((high && start > challenger->first) || (!high && start < challenger->first));
            if (challenger == freeByStart.end() || better || (tied && address)) {
                bestScore = score; challenger = freeByStart.find(start);
            }
        }
        if (challenger == freeByStart.end()) return baseline;
        int limit = static_cast<int>(std::max(baseline->second - baseline->first,
                                              challenger->second - challenger->first));
        double fresh = lifetimeModel.newRisk(length);
        double original = causalPrimalLoss(baseline, length, high, limit, fresh);
        double alternative = causalPrimalLoss(challenger, length, high, limit, fresh);
        return alternative + 1e-9 < original ? challenger : baseline;
    }
    I scoreGap(I width, int length) const {
        I slack = width - length, score = slack * static_cast<I>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)
                misses += recentFrequency[request];
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }
    bool observationKeyEqual(const Observation& a, const Observation& b) const {
        return a.kind == b.kind && (a.kind <= 0 || a.value == b.value);
    }
    std::uint32_t nextRandom(std::uint32_t& state) const {
        state ^= state << 13U; state ^= state >> 17U; state ^= state << 5U; return state;
    }
    std::array<Observation, kMcDepth> sampleScenario(std::uint32_t& random) const {
        std::array<Observation, kMcDepth> result{};
        std::size_t n = observedHistory.size();
        if (n < kMcDepth + 2) return result;
        std::size_t minStart = n > 128 ? n - 128 : 0, maxStart = n - kMcDepth;
        std::vector<std::size_t> starts;
        for (std::size_t context = std::min<std::size_t>(3, n - 1);
             context > 0 && starts.empty(); --context) {
            for (std::size_t start = minStart + context; start <= maxStart; ++start) {
                bool matches = true;
                for (std::size_t offset = 0; offset < context; ++offset)
                    if (!observationKeyEqual(observedHistory[n - context + offset],
                                             observedHistory[start - context + offset])) {
                        matches = false; break;
                    }
                if (matches) starts.push_back(start);
            }
        }
        if (starts.empty())
            for (std::size_t start = minStart; start <= maxStart; ++start) starts.push_back(start);
        if (starts.empty()) return result;
        std::size_t start = starts[nextRandom(random) % static_cast<std::uint32_t>(starts.size())];
        for (std::size_t offset = 0; offset < kMcDepth; ++offset) result[offset] = observedHistory[start + offset];
        return result;
    }
    RolloutState makeRolloutState() const {
        RolloutState state;
        state.confidentRecentAddress = !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
        for (const auto& [start, end] : freeByStart)
            state.gaps.emplace(start, SimGap{end, gapCohort.at(start)});
        state.trenchLength = trenchLength; state.nextPid = static_cast<int>(pipes.size());
        state.recentLengths = recentLengths; state.recentFrequency = recentFrequency;
        state.lengthOccurrenceCount = lengthOccurrenceCount; state.removedLengthCohort = removedLengthCohort;
        state.parityCohortMode = parityCohortMode;
        state.runLeftDisabledBySmoothTrend = runLeftDisabledBySmoothTrend;
        state.alternatingDeleteMode = alternatingDeleteMode; state.predictedDeletedParity = predictedDeletedParity;
        state.lastDeletedPid = lastDeletedPid; state.lastDeletedLength = lastDeletedLength;
        state.strideTwoDeleteTransitions = strideTwoDeleteTransitions;
        state.active.reserve(activePipeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            const Pipe& pipe = pipes[pid];
            if (pipe.active) state.active.push_back(SimPipe{static_cast<int>(pid), pipe.start, pipe.length, pipe.sizeCohort});
        }
        return state;
    }
    std::vector<GapCandidate> topGapCandidates(int length, bool high, int cohort) const {
        const std::set<std::pair<I, I>>* index = &freeBySize;
        if (parityCohortMode) {
            const auto& preferred = freeBySizeCohort[cohort];
            index = preferred.lower_bound({length, 0}) != preferred.end() ? &preferred : &freeBySizeShared;
        }
        std::vector<GapCandidate> candidates;
        auto it = index->lower_bound({length, 0});
        while (it != index->end()) {
            if (it->first - length > 40) break;
            candidates.push_back(GapCandidate{it->second, scoreGap(it->first, length)}); ++it;
        }
        std::sort(candidates.begin(), candidates.end(), [high](const auto& a, const auto& b) {
            if (a.score != b.score) return a.score < b.score;
            return high ? a.start > b.start : a.start < b.start;
        });
        if (candidates.size() > 3) candidates.resize(3);
        return candidates;
    }
    I chooseGapWithRollout(int length, bool high, int cohort, StartIter baseline) {
#if defined(MC_ROLLOUT_DISABLED)
        (void)length; (void)high; (void)cohort;
        return baseline->first;
#else
        if (mcDecisionsUsed >= kMcDecisionBudget || observedHistory.size() < 32 ||
            freeByStart.size() > kMcMaxGaps || activePipeCount > kMcMaxActivePipes)
            return baseline->first;
        auto candidates = topGapCandidates(length, high, cohort);
        if (candidates.size() < 2 || candidates.front().start != baseline->first) return baseline->first;
        ++mcDecisionsUsed;
        RolloutState base = makeRolloutState();
        std::uint32_t random = 0x9e3779b9U ^ static_cast<std::uint32_t>(pipes.size() * 0x85ebca6bU) ^
            (static_cast<std::uint32_t>(length) * 0xc2b2ae35U) ^ static_cast<std::uint32_t>(trenchLength);
        if (random == 0) random = 1;
        std::array<std::array<Observation, kMcDepth>, kMcTrials> scenarios{};
        for (std::size_t trial = 0; trial < kMcTrials; ++trial) scenarios[trial] = sampleScenario(random);
        std::array<I, 3> total{};
        for (std::size_t candidate = 0; candidate < candidates.size(); ++candidate)
            for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
                RolloutState simulation = base;
                simulation.placeAtCandidate(candidates[candidate].start, length, high);
                for (const auto& event : scenarios[trial]) simulation.apply(event);
                total[candidate] += simulation.trenchLength; ++mcRolloutsRun;
            }
        std::size_t best = 0;
        for (std::size_t candidate = 1; candidate < candidates.size(); ++candidate)
            if (total[candidate] < total[best]) best = candidate;
        if (best != 0 && total[best] + static_cast<I>(kMcTrials) * kMcMinimumMeanSavingM <= total[0])
            return candidates[best].start;
        return baseline->first;
#endif
    }
    bool hasSteadySizeTrend() const {
        if (recentLengths.size() < 128) return false;
        std::array<int, 3> sizes{};
        std::size_t n = 0;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (*it == previous) continue;
            sizes[n++] = *it; previous = *it;
            if (n == 3) break;
        }
        return n == 3 && sizes[0] - sizes[1] == sizes[1] - sizes[2];
    }
    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }
    StartIter bestFittingGapBefore(int length, bool high, int cohort, I limit) {
        StartIter best = freeByStart.end();
        I bestScore = std::numeric_limits<I>::max();
        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {
            if (it->second > limit || it->second - it->first < length) continue;
            if (parityCohortMode) {
                int owner = gapCohort.at(it->first);
                if (owner >= 0 && owner != cohort) continue;
            }
            I score = scoreGap(it->second - it->first, length);
            if (score < bestScore || (score == bestScore && best != freeByStart.end() &&
                ((high && it->first > best->first) || (!high && it->first < best->first)))) {
                bestScore = score; best = it;
            }
        }
        return best;
    }
    using ProjectedObstacle = std::pair<I, I>;
    I projectedNextClassCapacity(const std::vector<ProjectedObstacle>& obstacles,
                                 I start, int length, int nextLength) const {
        if (start < 0 || nextLength <= 0) return -1;
        auto right = std::lower_bound(obstacles.begin(), obstacles.end(), start,
            [](const auto& obstacle, I coordinate) { return obstacle.first < coordinate; });
        I leftEnd = right == obstacles.begin() ? 0 : std::prev(right)->second;
        I rightStart = right == obstacles.end() ? trenchLength : right->first;
        if (leftEnd > start || rightStart < start + length) return -1;
        return (start - leftEnd) / nextLength + (rightStart - start - length) / nextLength;
    }
    std::pair<StartIter, bool> chooseCounterfactualCapacityGap(
        int length, int nextLength, bool fallback, int cohort, StartIter baseline) {
        if (activePipeCount > 4096 || freeByStart.size() > 4096) return {freeByStart.end(), fallback};
        std::vector<ProjectedObstacle> obstacles;
        obstacles.reserve(activePipeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            const Pipe& pipe = pipes[pid];
            if (!pipe.active || (pipe.length == length && (static_cast<int>(pid) & 1) == predictedDeletedParity)) continue;
            obstacles.emplace_back(pipe.start, pipe.start + pipe.length);
        }
        std::sort(obstacles.begin(), obstacles.end());
        I baselineStart = baseline == freeByStart.end() ? -1 :
            (fallback ? baseline->second - length : baseline->first);
        I baselineCapacity = projectedNextClassCapacity(obstacles, baselineStart, length, nextLength);
        StartIter best = freeByStart.end();
        bool bestHigh = fallback;
        I bestStart = -1, bestCapacity = -1, bestBase = std::numeric_limits<I>::max();
        StartIter tail = tailGap();
        auto search = [&](int ownerMode) {
            for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {
                I width = it->second - it->first;
                int owner = gapCohort.at(it->first);
                if (width < length || (tail != freeByStart.end() && it == tail) ||
                    (ownerMode == 1 && owner != cohort) || (ownerMode == 2 && owner >= 0)) continue;
                I baseScore = scoreGap(width, length);
                for (int side = 0; side < 2; ++side) {
                    bool high = side != 0;
                    I start = high ? it->second - length : it->first;
                    I capacity = projectedNextClassCapacity(obstacles, start, length, nextLength);
                    if (capacity < 0) continue;
                    bool preferredSide = high == fallback, bestPreferredSide = bestHigh == fallback;
                    bool address = best != freeByStart.end() &&
                        ((high && start > bestStart) || (!high && start < bestStart));
                    if (capacity > bestCapacity || (capacity == bestCapacity && baseScore < bestBase) ||
                        (capacity == bestCapacity && baseScore == bestBase && preferredSide && !bestPreferredSide) ||
                        (capacity == bestCapacity && baseScore == bestBase && preferredSide == bestPreferredSide && address)) {
                        best = it; bestHigh = high; bestStart = start; bestCapacity = capacity; bestBase = baseScore;
                    }
                }
            }
        };
        if (parityCohortMode) { search(1); if (best == freeByStart.end()) search(2); }
        else search(0);
        if (best == freeByStart.end() || bestCapacity <= baselineCapacity) return {freeByStart.end(), fallback};
        return {best, bestHigh};
    }
    StartIter bestFittingGap(int length, bool high, int cohort) {
        if (parityCohortMode) {
            auto preferred = bestFittingGapFromSet(freeBySizeCohort[cohort], length, high);
            if (preferred != freeByStart.end()) return preferred;
            return bestFittingGapFromSet(freeBySizeShared, length, high);
        }
        return bestFittingGapFromSet(freeBySize, length, high);
    }
    StartIter bestFittingGapFromSet(const std::set<std::pair<I, I>>& gaps, int length, bool high) {
        bool recycle = !parityCohortMode && activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence();
        spanTieProfile = recycle;
        bool confidentAddress = high && !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);
        std::vector<std::pair<I, I>> candidates;
        auto candidate = it;
        while (candidate != gaps.end()) {
            if (confidentAddress) candidate = std::prev(gaps.upper_bound({candidate->first, std::numeric_limits<I>::max()}));
            I width = candidate->first, start = candidate->second;
            if (recycle) {
                auto age = freeBySizeAge.upper_bound({width, std::numeric_limits<U>::max(), std::numeric_limits<I>::max()});
                start = std::get<2>(*std::prev(age));
            }
            candidates.emplace_back(width, start);
            if (width - length > 40) break;
            candidate = gaps.upper_bound({width, std::numeric_limits<I>::max()});
        }
        I bestScore = std::numeric_limits<I>::max();
        StartIter legacy = freeByStart.end();
        for (const auto& [width, start] : candidates) {
            I score = scoreGap(width, length);
            if (score < bestScore || (score == bestScore && legacy != freeByStart.end() &&
                ((high && start > legacy->first) || (!high && start < legacy->first)))) {
                bestScore = score; legacy = freeByStart.find(start);
            }
        }
        StartIter best = legacy;
        bool ordinaryLarge = !parityCohortMode && activePipeCount > kMcMaxActivePipes;
        if (ordinaryLarge && candidates.front().first > length) {
            I maxGap = candidates.back().first;
            if (maxGap > kPrimalGapValueCap) ++primalCapFallbacks;
            else if (ensurePrimalGapValues(static_cast<int>(maxGap))) {
                double primalScore = std::numeric_limits<double>::infinity();
                StartIter primalBest = freeByStart.end();
                for (const auto& [width, start] : candidates) {
                    double score = primalGapLoss(width, length);
                    bool better = score + 1e-9 < primalScore;
                    bool tied = !(primalScore + 1e-9 < score) && !(score + 1e-9 < primalScore);
                    bool address = primalBest != freeByStart.end() &&
                        ((high && start > primalBest->first) || (!high && start < primalBest->first));
                    if (primalBest == freeByStart.end() || better || (tied && address)) {
                        primalScore = score; primalBest = freeByStart.find(start);
                    }
                }
                if (primalBest != freeByStart.end()) {
                    primalBest = chooseCausalLifetimeGap(candidates, length, high, primalBest);
                    ++primalScoredDecisions;
                    if (primalFirstActivationEvent == 0) primalFirstActivationEvent = primalStep + 1;
                    if (primalBest != legacy) ++primalChangedSelections;
                    best = primalBest;
                }
            }
        }
        if (recycle && best != freeByStart.end()) {
            auto first = gaps.lower_bound({best->second - best->first, 0});
            if (first->second != best->first) ++recencyDifferentSelections;
        }
        return best;
    }
    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t n = 0; n < kSameLengthRightRun; ++n, ++it)
            if (*it != length) return false;
        return true;
    }
    bool hasSmoothSizeTrendWith(int length) const {
        if (recentLengths.empty()) return false;
        bool currentInHistory = recentLengths.back() == length;
        std::array<int, 2> prior{};
        std::size_t n = 0;
        bool first = true;
        int previous = -1;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend(); ++it) {
            if (first) {
                first = false; previous = *it;
                if (!currentInHistory) prior[n++] = *it;
                continue;
            }
            if (*it == previous) continue;
            previous = *it; prior[n++] = *it;
            if (n == 2) break;
        }
        return n == 2 && length - prior[0] == prior[0] - prior[1];
    }
    I consumeAtSide(StartIter it, int length, bool high) {
        I start = it->first, end = it->second;
        int cohort = gapCohort.at(start);
        U freedAt = gapFreedAt.at(start);
        I placed = high ? end - length : start;
        eraseGap(it);
        if (start < placed) addFreeGap(start, placed, cohort, freedAt);
        if (placed + length < end) addFreeGap(placed + length, end, cohort, freedAt);
        return placed;
    }
    void recordLength(int length) {
        recentLengths.push_back(length); ++recentFrequency[length];
        if (recentLengths.size() > kHistoryWindow) {
            --recentFrequency[recentLengths.front()]; recentLengths.pop_front();
        }
    }
    void eraseGap(StartIter it) {
        I start = it->first, width = it->second - start;
        int cohort = gapCohort.at(start);
        --primalGapCounts[static_cast<std::size_t>(std::min<I>(kPrimalGapValueCap + 1, width))];
        freeBySizeAge.erase({width, gapFreedAt.at(start), start}); gapFreedAt.erase(start);
        freeBySize.erase({width, start});
        if (cohort >= 0 && cohort <= 1) freeBySizeCohort[cohort].erase({width, start});
        else freeBySizeShared.erase({width, start});
        gapCohort.erase(start); freeByStart.erase(it);
    }
    void addFreeGap(I start, I end, int cohort, U freedAt = 0) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                freedAt = std::max(freedAt, gapFreedAt.at(previous->first));
                start = previous->first; end = std::max(end, previous->second);
                eraseGap(previous); it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            if (gapCohort.at(it->first) != cohort) cohort = -1;
            freedAt = std::max(freedAt, gapFreedAt.at(it->first));
            end = std::max(end, it->second);
            auto next = it++; eraseGap(next);
        }
        freeByStart.emplace(start, end);
        I width = end - start;
        ++primalGapCounts[static_cast<std::size_t>(std::min<I>(kPrimalGapValueCap + 1, width))];
        freeBySize.emplace(width, start); freeBySizeAge.emplace(width, freedAt, start);
        gapFreedAt.emplace(start, freedAt); gapCohort.emplace(start, cohort);
        if (cohort >= 0 && cohort <= 1) freeBySizeCohort[cohort].emplace(width, start);
        else freeBySizeShared.emplace(width, start);
    }
    static void printPlacement(I digs, I start) {
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }
    static void printInvalidPidFallback() { std::cout << 0 << '\n' << std::flush; }
};
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    Allocator allocator;
    I command;
    while (std::cin >> command) {
        if (command == 0) {
            std::cerr << "recency_different_selections=" << allocator.recencyDifferentSelections << '\n';
            std::cerr << "primal_dp_scored_decisions=" << allocator.primalScoredDecisions
                      << " changed_selections=" << allocator.primalChangedSelections
                      << " first_activation_event=" << allocator.primalFirstActivationEvent
                      << " cap_fallbacks=" << allocator.primalCapFallbacks
                      << " model_rebuilds=" << allocator.primalModelRebuilds << '\n';
            std::cerr << "span_tie_queries=" << allocator.spanTieQueries
                      << " alternatives=" << allocator.spanTieAlternatives
                      << " changes=" << allocator.spanTieChanges
                      << " extended_volume=" << allocator.spanTieExtendedVolume << '\n';
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun
                      << " expansion_gate_opportunities=" << allocator.expansionGateOpportunities
                      << " expansion_gate_passes=" << allocator.expansionGatePasses
                      << " unit_profile_suppressed_expansions=" << allocator.unitProfileSuppressedExpansions << '\n';
#endif
            return 0;
        }
        if (command > 0) allocator.place(static_cast<int>(command));
        else allocator.remove(-command);
    }
    return 0;
}
