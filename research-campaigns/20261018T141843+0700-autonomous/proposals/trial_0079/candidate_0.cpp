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
#include <utility>
#include <tuple>
#include <vector>

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kHistoryWindow = 2048;
constexpr std::int64_t kUnfitPenaltyScale = 60;
constexpr int kPrimalGapValueCap = 512;
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
    bool confidentRecentAddress = false;
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
            if (!consideredLengths.insert(gapLength).second && !(confidentRecentAddress && highSide)) continue;
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

class CensoredLifetimeModel {
    static constexpr std::array<std::uint64_t, 8> kLower{
        0, 16, 64, 256, 1024, 4096, 16384, 65536};
    static constexpr std::size_t kBins = kLower.size();

    struct Record {
        std::uint64_t born = 0;
        int length = 0;
        bool active = false;
    };
    struct Cell {
        std::uint64_t completedExposure = 0;
        std::uint64_t birthSum = 0;
        std::uint64_t active = 0;
        std::uint64_t deaths = 0;
    };
    struct Estimate {
        double mean = 0.0;
        double error = 0.0;
    };

    std::vector<Record> records_{Record{}};
    std::array<std::array<Cell, kBins>, 41> cells_{};
    std::array<std::array<Estimate, kBins>, 41> rates_{};
    std::array<std::size_t, kBins> nextCrossing_{};
    std::uint64_t clock_ = 0;
    double referenceRate_ = 0.0;
    double referenceError_ = 0.0;
    bool fitted_ = false;

    static std::size_t ageBin(std::uint64_t age) {
        std::size_t bin = 0;
        while (bin + 1 < kBins && age >= kLower[bin + 1]) ++bin;
        return bin;
    }

    void enter(const Record& record, std::size_t bin) {
        auto& cell = cells_[static_cast<std::size_t>(record.length)][bin];
        ++cell.active;
        cell.birthSum += record.born;
    }

    void leave(const Record& record, std::size_t bin, std::uint64_t age) {
        auto& cell = cells_[static_cast<std::size_t>(record.length)][bin];
        cell.completedExposure += age - kLower[bin];
        --cell.active;
        cell.birthSum -= record.born;
    }

    std::uint64_t exposure(const Cell& cell, std::size_t bin) const {
        const std::uint64_t outstanding = cell.active == 0 ? 0 :
            cell.active * (clock_ - kLower[bin]) - cell.birthSum;
        return cell.completedExposure + outstanding;
    }

    Estimate predict(int length, std::uint64_t age) const {
        Estimate result;
        const std::uint64_t end = age +
            static_cast<std::uint64_t>(kHistoryWindow);
        std::size_t bin = ageBin(age);
        while (age < end) {
            const std::uint64_t next = bin + 1 < kBins
                ? std::min(end, kLower[bin + 1]) : end;
            const double weight = static_cast<double>(next - age) /
                static_cast<double>(kHistoryWindow);
            const auto& rate = rates_[static_cast<std::size_t>(length)][bin];
            result.mean += weight * rate.mean;
            // Sum errors conservatively: the pooled priors are shared.
            result.error += weight * rate.error;
            age = next;
            if (age < end) ++bin;
        }
        return result;
    }

    double adjustedRatio(int length, std::uint64_t age) const {
        if (!fitted_) return 1.0;
        const Estimate prediction = predict(length, age);
        const double margin = 2.0 * (prediction.error + referenceError_);
        double supported = referenceRate_;
        if (prediction.mean - margin > referenceRate_) {
            supported = prediction.mean - margin;
        } else if (prediction.mean + margin < referenceRate_) {
            supported = prediction.mean + margin;
        }
        return std::clamp(supported / referenceRate_, 0.5, 2.0);
    }

public:
    CensoredLifetimeModel() {
        nextCrossing_.fill(1);
    }

    void advance() {
        ++clock_;
        // Birth order is chronological, so each landmark needs one cursor.
        for (std::size_t bin = 1; bin < kBins; ++bin) {
            auto& cursor = nextCrossing_[bin];
            while (cursor < records_.size() &&
                   clock_ - records_[cursor].born >= kLower[bin]) {
                const Record& record = records_[cursor++];
                if (!record.active) continue;
                leave(record, bin - 1, kLower[bin]);
                enter(record, bin);
            }
        }
    }

    void observeBirth(int length) {
        records_.push_back(Record{clock_, length, true});
        enter(records_.back(), 0);
    }

    void observeDeletion(std::size_t pid) {
        Record& record = records_[pid];
        const std::uint64_t age = clock_ - record.born;
        leave(record, ageBin(age), age);
        // A deletion at an integer landmark ends the preceding risk interval.
        const std::size_t eventBin = ageBin(age == 0 ? 0 : age - 1);
        ++cells_[static_cast<std::size_t>(record.length)][eventBin].deaths;
        record.active = false;
    }

    bool fit(double priorHazard) {
        fitted_ = false;
        if (!(priorHazard > 0.0)) return false;
        constexpr double priorEvents = 8.0;
        for (std::size_t bin = 0; bin < kBins; ++bin) {
            double pooledExposure = 0.0;
            double pooledDeaths = 0.0;
            for (std::size_t length = 1; length <= 40; ++length) {
                pooledExposure += static_cast<double>(exposure(cells_[length][bin], bin));
                pooledDeaths += static_cast<double>(cells_[length][bin].deaths);
            }
            const double pooledDenominator = pooledExposure + priorEvents / priorHazard;
            const double pooledRate = (pooledDeaths + priorEvents) / pooledDenominator;
            const double pooledError = std::sqrt(pooledDeaths + priorEvents) /
                pooledDenominator;
            for (std::size_t length = 1; length <= 40; ++length) {
                const auto& cell = cells_[length][bin];
                const double borrowedExposure = priorEvents / pooledRate;
                const double denominator = static_cast<double>(exposure(cell, bin)) +
                    borrowedExposure;
                const double shape = static_cast<double>(cell.deaths) + priorEvents;
                rates_[length][bin] = Estimate{
                    shape / denominator,
                    std::sqrt(shape) / denominator +
                        borrowedExposure / denominator * pooledError};
            }
        }

        double sumRate = 0.0;
        double sumError = 0.0;
        std::uint64_t population = 0;
        for (std::size_t length = 1; length <= 40; ++length) {
            for (std::size_t bin = 0; bin < kBins; ++bin) {
                const auto& cell = cells_[length][bin];
                if (cell.active == 0) continue;
                const std::uint64_t meanAge = clock_ - cell.birthSum / cell.active;
                const Estimate prediction = predict(static_cast<int>(length), meanAge);
                sumRate += static_cast<double>(cell.active) * prediction.mean;
                sumError += static_cast<double>(cell.active) * prediction.error;
                population += cell.active;
            }
        }
        if (population == 0) return false;
        referenceRate_ = sumRate / static_cast<double>(population);
        referenceError_ = sumError / static_cast<double>(population);
        fitted_ = referenceRate_ > 0.0;
        return fitted_;
    }

    double existingRisk(int pid) const {
        const Record& record = records_[static_cast<std::size_t>(pid)];
        return adjustedRatio(record.length, clock_ - record.born);
    }

    double newRisk(int length) const {
        return adjustedRatio(length, 0);
    }
};

class Allocator {
public:
    std::uint64_t releaseEpoch = 0;
    std::uint64_t recencyDifferentSelections = 0;
    std::map<std::int64_t, std::uint64_t> gapFreedAt;
    std::set<std::tuple<std::int64_t, std::uint64_t, std::int64_t>> freeBySizeAge;
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
    std::size_t tailSideOpportunities = 0;
    std::size_t tailSideComparisons = 0;
    std::size_t tailSideChanges = 0;
    std::size_t tailSideRolloutsRun = 0;
    std::size_t tailSideJointChallengerComparisons = 0;
    std::size_t tailSideJointGapChanges = 0;
    std::uint64_t tailSideForecastSavingSections = 0;
    std::deque<int> recentDeleteRanksPermille;
    bool lifoLaneDisabledForScale = false;
    std::array<std::int64_t, kPrimalGapValueCap + 2> primalGapCounts{};
    std::array<int, kHistoryWindow> primalEventHistory{};
    std::array<int, 41> primalRecentRequests{};
    std::array<double, kPrimalGapValueCap + 1> primalGapValue{};
    std::size_t primalEventPosition = 0;
    int primalRecentDeletes = 0;
    std::uint64_t primalStep = 0;
    std::uint64_t primalModelStep = 0;
    int primalComputedLimit = 0;
    bool primalModelDirty = true;
    std::size_t primalScoredDecisions = 0;
    std::size_t primalChangedSelections = 0;
    std::size_t primalCapFallbacks = 0;
    std::size_t primalModelRebuilds = 0;
    std::uint64_t primalFirstActivationEvent = 0;
    int activeRunFirstPid = 1;
    std::array<std::size_t, 2> activeRunDeleteParityCount{};
    int lastCompletedDeleteRelativeParity = -1;
    int previousCompletedDeleteRelativeParity = -1;
    CensoredLifetimeModel lifetimeModel;
    std::array<double, 41> causalRequestRate{};
    std::array<std::array<double, kPrimalGapValueCap + 1>, 2> causalGapValue{};
    double causalBaseExpiry = 0.0;
    int causalComputedLimit = 0;
    bool causalRiskReady = false;

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
        lifetimeModel.advance();
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
            recordPrimalEvent(length);
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
            const bool allowTailSideRollout = !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice &&
                !lifoStackLane;
            const std::int64_t selectedStart = (additiveNextAlignment ||
                counterfactualCapacityChoice)
                ? gap->first
                : chooseGapWithRollout(length, highSide, sizeCohort, gap,
                                       allowTailSideRollout);
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
        recordPrimalEvent(length);
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

        lifetimeModel.advance();
        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));

        const Pipe pipe = pipes[index];
        lifetimeModel.observeDeletion(index);
        activeByEnd.erase(pipe.start + pipe.length);
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        fenwickAdd(static_cast<int>(index), -1);
        --activePipeCount;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, ++releaseEpoch);
        recordDeletionPattern(static_cast<int>(index), pipe.length);
        recordPrimalEvent(-1);
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

    void recordPrimalEvent(int event) {
        if (event > 0) lifetimeModel.observeBirth(event);
        const int old = primalEventHistory[primalEventPosition];
        if (old > 0) {
            if (--primalRecentRequests[static_cast<std::size_t>(old)] == 0) {
                primalModelDirty = true;
            }
        } else if (old < 0) {
            if (--primalRecentDeletes == 0) primalModelDirty = true;
        }

        primalEventHistory[primalEventPosition] = event;
        primalEventPosition = (primalEventPosition + 1) % primalEventHistory.size();
        if (event > 0) {
            if (primalRecentRequests[static_cast<std::size_t>(event)]++ == 0) {
                primalModelDirty = true;
            }
        } else if (event < 0) {
            if (primalRecentDeletes++ == 0) primalModelDirty = true;
        }
        ++primalStep;
    }

    bool hasRecentPrimalDemand() const {
        for (std::size_t length = 1; length < primalRecentRequests.size(); ++length) {
            if (primalRecentRequests[length] > 0) return true;
        }
        return false;
    }

    void rebuildPrimalGapValues(int maxGap) {
        std::array<double, 41> rate{};
        std::int64_t fitting = primalGapCounts[kPrimalGapValueCap + 1];
        for (int gap = kPrimalGapValueCap; gap >= 1; --gap) {
            fitting += primalGapCounts[static_cast<std::size_t>(gap)];
            if (gap <= 40) {
                rate[static_cast<std::size_t>(gap)] =
                    static_cast<double>(primalRecentRequests[static_cast<std::size_t>(gap)]) /
                    static_cast<double>(std::max<std::int64_t>(1, fitting));
            }
        }

        const double expiry = 2.0 * static_cast<double>(primalRecentDeletes) /
            static_cast<double>(std::max<std::size_t>(1, activePipeCount));
        primalGapValue.fill(0.0);
        for (int gap = 1; gap <= maxGap; ++gap) {
            const int top = std::min(gap, 40);
            if (expiry == 0.0) {
                for (int request = 1; request <= top; ++request) {
                    if (rate[static_cast<std::size_t>(request)] > 0.0) {
                        primalGapValue[static_cast<std::size_t>(gap)] = std::max(
                            primalGapValue[static_cast<std::size_t>(gap)],
                            static_cast<double>(request) +
                                primalGapValue[static_cast<std::size_t>(gap - request)]);
                    }
                }
                continue;
            }

            std::array<double, 41> reward{};
            std::uint64_t active = 0;
            double numerator = 0.0;
            double denominator = expiry;
            for (int request = 1; request <= top; ++request) {
                const double requestRate = rate[static_cast<std::size_t>(request)];
                if (requestRate == 0.0) continue;
                reward[static_cast<std::size_t>(request)] =
                    static_cast<double>(request) +
                    primalGapValue[static_cast<std::size_t>(gap - request)];
                numerator += requestRate * reward[static_cast<std::size_t>(request)];
                denominator += requestRate;
                active |= std::uint64_t{1} << static_cast<unsigned>(request);
            }
            double estimate = numerator / denominator;
            for (;;) {
                bool removed = false;
                for (int request = 1; request <= top; ++request) {
                    const std::uint64_t bit = std::uint64_t{1} <<
                        static_cast<unsigned>(request);
                    if ((active & bit) != 0 &&
                        reward[static_cast<std::size_t>(request)] < estimate) {
                        numerator -= rate[static_cast<std::size_t>(request)] *
                            reward[static_cast<std::size_t>(request)];
                        denominator -= rate[static_cast<std::size_t>(request)];
                        active &= ~bit;
                        removed = true;
                    }
                }
                if (!removed) break;
                estimate = numerator / denominator;
            }
            primalGapValue[static_cast<std::size_t>(gap)] = std::clamp(
                estimate, 0.0, static_cast<double>(gap));
        }
        causalRequestRate = rate;
        causalBaseExpiry = expiry;
        causalComputedLimit = 0;
        causalRiskReady = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes && expiry > 0.0 &&
            lifetimeModel.fit(expiry /
                (2.0 * static_cast<double>(kHistoryWindow)));
        primalModelStep = primalStep;
        primalComputedLimit = maxGap;
        primalModelDirty = false;
        ++primalModelRebuilds;
    }

    bool ensurePrimalGapValues(int maxGap) {
        if (maxGap <= 0 || maxGap > kPrimalGapValueCap) return false;
        if (primalModelDirty || primalStep - primalModelStep >= 64 ||
            maxGap > primalComputedLimit) {
            rebuildPrimalGapValues(maxGap);
        }
        return hasRecentPrimalDemand();
    }

    void rebuildCausalGapValues(int maxGap) {
        for (std::size_t model = 0; model < causalGapValue.size(); ++model) {
            auto& value = causalGapValue[model];
            value.fill(0.0);
            const double expiry = causalBaseExpiry * (model == 0 ? 0.5 : 2.0);
            for (int gap = 1; gap <= maxGap; ++gap) {
                const int top = std::min(gap, 40);
                std::array<double, 41> reward{};
                std::uint64_t active = 0;
                double numerator = 0.0;
                double denominator = expiry;
                for (int request = 1; request <= top; ++request) {
                    const double requestRate = causalRequestRate[static_cast<std::size_t>(request)];
                    if (requestRate == 0.0) continue;
                    reward[static_cast<std::size_t>(request)] =
                        static_cast<double>(request) + value[static_cast<std::size_t>(gap - request)];
                    numerator += requestRate * reward[static_cast<std::size_t>(request)];
                    denominator += requestRate;
                    active |= std::uint64_t{1} << static_cast<unsigned>(request);
                }
                double estimate = numerator / denominator;
                for (;;) {
                    bool removed = false;
                    for (int request = 1; request <= top; ++request) {
                        const std::uint64_t bit = std::uint64_t{1} <<
                            static_cast<unsigned>(request);
                        if ((active & bit) != 0 &&
                            reward[static_cast<std::size_t>(request)] < estimate) {
                            numerator -= causalRequestRate[static_cast<std::size_t>(request)] *
                                reward[static_cast<std::size_t>(request)];
                            denominator -= causalRequestRate[static_cast<std::size_t>(request)];
                            active &= ~bit;
                            removed = true;
                        }
                    }
                    if (!removed) break;
                    estimate = numerator / denominator;
                }
                value[static_cast<std::size_t>(gap)] = std::clamp(
                    estimate, 0.0, static_cast<double>(gap));
            }
        }
        causalComputedLimit = maxGap;
    }

    double causalValueAt(int gap, double expiryFactor) const {
        const std::size_t index = static_cast<std::size_t>(gap);
        const double base = primalGapValue[index];
        if (expiryFactor <= 1.0) {
            return base + 2.0 * (1.0 - expiryFactor) *
                (causalGapValue[0][index] - base);
        }
        return base + (expiryFactor - 1.0) *
            (causalGapValue[1][index] - base);
    }

    double causalPrimalLoss(StartIter gap, int length, bool highSide,
                           int modelLimit, double freshRisk) {
        const std::int64_t gapLength = gap->second - gap->first;
        // Missing neighbors retain the parent's prior contribution. Thus
        // topology alone cannot activate this lifetime correction.
        double leftRisk = 1.0;
        double rightRisk = 1.0;
        const auto left = activeByEnd.find(gap->first);
        if (left != activeByEnd.end()) {
            leftRisk = lifetimeModel.existingRisk(left->second);
        }
        const auto right = activeByEnd.upper_bound(gap->second);
        if (right != activeByEnd.end() &&
            pipes[static_cast<std::size_t>(right->second)].start == gap->second) {
            rightRisk = lifetimeModel.existingRisk(right->second);
        }
        const double originalFactor = 0.5 * (leftRisk + rightRisk);
        const double remainingFactor = 0.5 *
            (freshRisk + (highSide ? leftRisk : rightRisk));
        if (originalFactor == 1.0 && remainingFactor == 1.0) {
            return primalGapLoss(gapLength, length);
        }
        if (causalComputedLimit < modelLimit) rebuildCausalGapValues(modelLimit);
        return causalValueAt(static_cast<int>(gapLength), originalFactor) -
            causalValueAt(static_cast<int>(gapLength) - length, remainingFactor);
    }

    StartIter chooseCausalLifetimeGap(
        const std::vector<std::pair<std::int64_t, std::int64_t>>& candidates,
        int length, bool highSide, StartIter baselineGap) {
        if (!causalRiskReady || alternatingDeleteMode ||
            observedRunCount >= static_cast<int>(kSameLengthRightRun) ||
            candidates.size() < 2) {
            return baselineGap;
        }

        // Keep the parent's two finalists, including its address tie-break.
        // Boundary lookup and lifetime forecasts are bounded to two spans.
        StartIter challenger = freeByStart.end();
        double challengerScore = std::numeric_limits<double>::infinity();
        for (const auto& [gapLength, representativeStart] : candidates) {
            if (representativeStart == baselineGap->first) continue;
            const double score = primalGapLoss(gapLength, length);
            const bool strictlyBetter = score + 1e-9 < challengerScore;
            const bool tied = !(challengerScore + 1e-9 < score) &&
                !(score + 1e-9 < challengerScore);
            const bool addressPreferred = challenger != freeByStart.end() &&
                ((highSide && representativeStart > challenger->first) ||
                 (!highSide && representativeStart < challenger->first));
            if (challenger == freeByStart.end() || strictlyBetter ||
                (tied && addressPreferred)) {
                challengerScore = score;
                challenger = freeByStart.find(representativeStart);
            }
        }
        if (challenger == freeByStart.end()) return baselineGap;
        const int modelLimit = static_cast<int>(std::max(
            baselineGap->second - baselineGap->first,
            challenger->second - challenger->first));
        const double freshRisk = lifetimeModel.newRisk(length);
        const double baselineScore = causalPrimalLoss(
            baselineGap, length, highSide, modelLimit, freshRisk);
        const double alternativeScore = causalPrimalLoss(
            challenger, length, highSide, modelLimit, freshRisk);
        return alternativeScore + 1e-9 < baselineScore ? challenger : baselineGap;
    }

    double primalGapLoss(std::int64_t gapLength, int length) const {
        const std::size_t gap = static_cast<std::size_t>(gapLength);
        const std::size_t request = static_cast<std::size_t>(length);
        return primalGapValue[gap] - primalGapValue[gap - request];
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
        state.confidentRecentAddress = !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
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

    bool chooseTailSideWithRollout(
        int length, bool highSide, StartIter selectedGap) {
#if defined(MC_ROLLOUT_DISABLED)
        (void)length;
        (void)selectedGap;
        return highSide;
#else
        if (!highSide || selectedGap == freeByStart.end() ||
            selectedGap->second != trenchLength ||
            selectedGap->second - selectedGap->first <= length ||
            parityCohortMode || alternatingDeleteMode ||
            observedRunCount >= static_cast<int>(kSameLengthRightRun)) {
            return highSide;
        }
        ++tailSideOpportunities;
        if (tailSideComparisons >= kMcDecisionBudget ||
            observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps ||
            activePipeCount > kMcMaxActivePipes) {
            return highSide;
        }

        ++tailSideComparisons;
        const RolloutState base = makeRolloutState();
        // Use the parent's scenario generator and seed. Both endpoints see
        // exactly the same continuations; only the current placement differs.
        std::uint32_t randomState = 0x9e3779b9U ^
            static_cast<std::uint32_t>(pipes.size() * 0x85ebca6bU) ^
            (static_cast<std::uint32_t>(length) * 0xc2b2ae35U) ^
            static_cast<std::uint32_t>(trenchLength);
        if (randomState == 0) randomState = 1;

        // Index zero preserves an expandable tail; index one is the parent.
        std::array<std::int64_t, 2> totalTrench{};
        for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
            const auto scenario = sampleScenario(randomState);
            for (std::size_t side = 0; side < totalTrench.size(); ++side) {
                RolloutState simulation = base;
                simulation.placeAtCandidate(selectedGap->first, length, side != 0);
                for (const auto& event : scenario) simulation.apply(event);
                totalTrench[side] += simulation.trenchLength;
                ++tailSideRolloutsRun;
            }
        }

        const std::int64_t requiredSaving =
            static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM;
        if (totalTrench[0] + requiredSaving <= totalTrench[1]) {
            ++tailSideChanges;
            tailSideForecastSavingSections += static_cast<std::uint64_t>(
                (totalTrench[1] - totalTrench[0]) / kDigLength);
            return false;
        }
        return highSide;
#endif
    }

    std::int64_t chooseGapWithRollout(
        int length, bool& highSide, int sizeCohort, StartIter baselineGap,
        bool allowTailSide) {
#if defined(MC_ROLLOUT_DISABLED)
        (void)length;
        (void)highSide;
        (void)sizeCohort;
        (void)allowTailSide;
        return baselineGap->first;
#else
        // Preserve the standalone endpoint policy whenever the gap rollout
        // cannot supply paired scores for its original candidate set.
        const auto finishSequentially = [&](std::int64_t selectedStart) {
            if (allowTailSide) {
                highSide = chooseTailSideWithRollout(
                    length, highSide, freeByStart.find(selectedStart));
            }
            return selectedStart;
        };
        if (mcDecisionsUsed >= kMcDecisionBudget ||
            observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps ||
            activePipeCount > kMcMaxActivePipes) {
            return finishSequentially(baselineGap->first);
        }
        const auto candidates = topGapCandidates(length, highSide, sizeCohort);
        if (candidates.size() < 2 || candidates.front().start != baselineGap->first) {
            return finishSequentially(baselineGap->first);
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
        const std::int64_t requiredSaving =
            static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM;
        std::size_t selected = 0;
        if (best != 0 && totalTrench[best] + requiredSaving <= totalTrench[0]) {
            selected = best;
        }

        // Keep the exact original top-3 enumeration. Only an existing tail
        // candidate may receive the endpoint alternative from trial_0075.
        // History and state-size gates already passed above; retain the
        // endpoint policy's structural gates and independent decision quota.
        if (allowTailSide && highSide && !parityCohortMode &&
            !alternatingDeleteMode &&
            observedRunCount < static_cast<int>(kSameLengthRightRun) &&
            tailSideComparisons < kMcDecisionBudget) {
            std::size_t tailCandidate = candidates.size();
            for (std::size_t candidate = 0; candidate < candidates.size(); ++candidate) {
                const auto gap = freeByStart.find(candidates[candidate].start);
                if (gap != freeByStart.end() && gap->second == trenchLength &&
                    gap->second - gap->first > length) {
                    tailCandidate = candidate;
                    break;
                }
            }
            if (tailCandidate != candidates.size()) {
                ++tailSideOpportunities;
                ++tailSideComparisons;
                const bool changesGap = tailCandidate != selected;
                if (changesGap) ++tailSideJointChallengerComparisons;

                // The high-side tail score is already available. Reuse the
                // exact same continuations for its low-side alternative.
                std::int64_t lowTailTotal = 0;
                for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
                    RolloutState simulation = base;
                    simulation.placeAtCandidate(
                        candidates[tailCandidate].start, length, false);
                    for (const auto& event : scenarios[trial]) simulation.apply(event);
                    lowTailTotal += simulation.trenchLength;
                    ++tailSideRolloutsRun;
                }

                // Require the endpoint's original saving against its own
                // high side and the same saving against the gap-stage choice.
                if (lowTailTotal + requiredSaving <= totalTrench[tailCandidate] &&
                    lowTailTotal + requiredSaving <= totalTrench[selected]) {
                    ++tailSideChanges;
                    if (changesGap) ++tailSideJointGapChanges;
                    tailSideForecastSavingSections += static_cast<std::uint64_t>(
                        (totalTrench[tailCandidate] - lowTailTotal) / kDigLength);
                    highSide = false;
                    return candidates[tailCandidate].start;
                }
                // A selected tail has now received exactly the standalone
                // endpoint comparison; do not evaluate or charge it twice.
                return candidates[selected].start;
            }
        }
        return finishSequentially(candidates[selected].start);
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
        // LIFO free lists use observed free recency, not predicted lifetime.
        // At this scale the parent MC is already disabled, so no forecast
        // silently uses a different recycler policy.
        const bool recycleRecent = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence();
        const bool confidentRecentAddress = highSide &&
            !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        std::vector<std::pair<std::int64_t, std::int64_t>> candidates;
        auto candidate = it;
        while (candidate != gaps.end()) {
            if (confidentRecentAddress) {
                candidate = std::prev(gaps.upper_bound({candidate->first,
                    std::numeric_limits<std::int64_t>::max()}));
            }
            const std::int64_t gapLength = candidate->first;
            std::int64_t representativeStart = candidate->second;
            if (recycleRecent) {
                auto age = freeBySizeAge.upper_bound({gapLength,
                    std::numeric_limits<std::uint64_t>::max(),
                    std::numeric_limits<std::int64_t>::max()});
                --age;
                representativeStart = std::get<2>(*age);
            }
            candidates.emplace_back(gapLength, representativeStart);

            // Keep the seed's domain exactly: evaluate the first candidate
            // beyond 40 m of slack, then stop scanning.
            if (gapLength - static_cast<std::int64_t>(length) > 40) break;
            candidate = gaps.upper_bound({gapLength,
                std::numeric_limits<std::int64_t>::max()});
        }

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter legacyBest = freeByStart.end();
        for (const auto& [gapLength, representativeStart] : candidates) {
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
                (score == bestScore && legacyBest != freeByStart.end() &&
                 ((highSide && representativeStart > legacyBest->first) ||
                  (!highSide && representativeStart < legacyBest->first)))) {
                bestScore = score;
                legacyBest = freeByStart.find(representativeStart);
            }
        }

        StartIter best = legacyBest;
        const bool ordinaryLargeMode = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes;
        if (ordinaryLargeMode && candidates.front().first > length) {
            const std::int64_t maxCandidateGap = candidates.back().first;
            if (maxCandidateGap > kPrimalGapValueCap) {
                ++primalCapFallbacks;
            } else if (ensurePrimalGapValues(static_cast<int>(maxCandidateGap))) {
                double primalBestScore = std::numeric_limits<double>::infinity();
                StartIter primalBest = freeByStart.end();
                for (const auto& [gapLength, representativeStart] : candidates) {
                    const double score = primalGapLoss(gapLength, length);
                    const bool strictlyBetter = score + 1e-9 < primalBestScore;
                    const bool tied = !(primalBestScore + 1e-9 < score) &&
                        !(score + 1e-9 < primalBestScore);
                    const bool addressPreferred = primalBest != freeByStart.end() &&
                        ((highSide && representativeStart > primalBest->first) ||
                         (!highSide && representativeStart < primalBest->first));
                    if (primalBest == freeByStart.end() || strictlyBetter ||
                        (tied && addressPreferred)) {
                        primalBestScore = score;
                        primalBest = freeByStart.find(representativeStart);
                    }
                }
                if (primalBest != freeByStart.end()) {
                    primalBest = chooseCausalLifetimeGap(
                        candidates, length, highSide, primalBest);
                    ++primalScoredDecisions;
                    if (primalFirstActivationEvent == 0) {
                        primalFirstActivationEvent = primalStep + 1;
                    }
                    if (primalBest != legacyBest) ++primalChangedSelections;
                    best = primalBest;
                }
            }
        }
        if (recycleRecent && best != freeByStart.end()) {
            const auto first = gaps.lower_bound({best->second - best->first, 0});
            if (first->second != best->first) ++recencyDifferentSelections;
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
        const std::uint64_t freedAt = gapFreedAt.at(start);
        const std::int64_t placementStart = highSide
            ? end - static_cast<std::int64_t>(length) : start;
        eraseGap(it);
        if (start < placementStart) addFreeGap(start, placementStart, cohort, freedAt);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort, freedAt);
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
        const std::size_t bucket = static_cast<std::size_t>(
            std::min<std::int64_t>(kPrimalGapValueCap + 1, gapLength));
        --primalGapCounts[bucket];
        freeBySizeAge.erase({gapLength, gapFreedAt.at(start), start});
        gapFreedAt.erase(start);
        freeBySize.erase({gapLength, start});
        if (cohort >= 0 && cohort <= 1) {
            freeBySizeCohort[static_cast<std::size_t>(cohort)].erase({gapLength, start});
        } else {
            freeBySizeShared.erase({gapLength, start});
        }
        gapCohort.erase(start);
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end, int cohort,
                    std::uint64_t freedAt = 0) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                if (gapCohort.at(previous->first) != cohort) cohort = -1;
                freedAt = std::max(freedAt, gapFreedAt.at(previous->first));
                start = previous->first;
                end = std::max(end, previous->second);
                eraseGap(previous);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            if (gapCohort.at(it->first) != cohort) cohort = -1;
            freedAt = std::max(freedAt, gapFreedAt.at(it->first));
            end = std::max(end, it->second);
            auto next = it++;
            eraseGap(next);
        }
        freeByStart.emplace(start, end);
        const std::int64_t gapLength = end - start;
        const std::size_t bucket = static_cast<std::size_t>(
            std::min<std::int64_t>(kPrimalGapValueCap + 1, gapLength));
        ++primalGapCounts[bucket];
        freeBySize.emplace(gapLength, start);
        freeBySizeAge.emplace(gapLength, freedAt, start);
        gapFreedAt.emplace(start, freedAt);
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
            std::cerr << "recency_different_selections="
                      << allocator.recencyDifferentSelections << '\n';
            std::cerr << "tail_side_opportunities="
                      << allocator.tailSideOpportunities
                      << " comparisons=" << allocator.tailSideComparisons
                      << " changes=" << allocator.tailSideChanges
                      << " rollouts=" << allocator.tailSideRolloutsRun
                      << " forecast_section_sum="
                      << allocator.tailSideForecastSavingSections
                      << " joint_challenger_comparisons="
                      << allocator.tailSideJointChallengerComparisons
                      << " joint_gap_changes="
                      << allocator.tailSideJointGapChanges << '\n';
            std::cerr << "primal_dp_scored_decisions="
                      << allocator.primalScoredDecisions
                      << " changed_selections=" << allocator.primalChangedSelections
                      << " first_activation_event=" << allocator.primalFirstActivationEvent
                      << " cap_fallbacks=" << allocator.primalCapFallbacks
                      << " model_rebuilds=" << allocator.primalModelRebuilds << '\n';
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
