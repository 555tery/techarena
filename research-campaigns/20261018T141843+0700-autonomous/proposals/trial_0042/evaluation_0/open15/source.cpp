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
#include <vector>

namespace {
using I = std::int64_t;
using U = std::uint64_t;
constexpr I kDig = 20;
constexpr std::size_t kHistory = 2048;
constexpr int kCap = 512;
constexpr std::size_t kRun = 46;
constexpr std::size_t kMcHistory = 256;
constexpr std::size_t kMcDepth = 4;
constexpr std::size_t kMcTrials = 12;
constexpr std::size_t kMcBudget = 32;
constexpr std::size_t kMcMaxGaps = 64;
constexpr std::size_t kMcMaxActive = 4096;

struct Observation { int kind = 0; int value = 0; };
struct Pipe { I start = 0; int length = 0; bool active = false; int cohort = 0; };
struct SimPipe { int pid = 0; I start = 0; int length = 0; int cohort = 0; };
struct SimGap { I end = 0; int cohort = -1; };
struct GapCandidate { I start = 0; I score = 0; };

bool sameRun(const std::deque<int>& history, int length) {
    if (history.size() < kRun) return false;
    auto it = history.rbegin();
    for (std::size_t n = 0; n < kRun; ++n, ++it) if (*it != length) return false;
    return true;
}

bool steadyTrend(const std::deque<int>& history) {
    if (history.size() < 128) return false;
    std::array<int, 3> sizes{};
    std::size_t n = 0;
    int previous = -1;
    for (auto it = history.rbegin(); it != history.rend(); ++it) {
        if (*it == previous) continue;
        sizes[n++] = *it;
        previous = *it;
        if (n == sizes.size()) break;
    }
    return n == 3 && sizes[0] - sizes[1] == sizes[1] - sizes[2];
}

bool smoothTrend(const std::deque<int>& history, int length) {
    if (history.empty()) return false;
    auto it = history.rbegin();
    if (*it == length) while (it != history.rend() && *it == length) ++it;
    std::array<int, 2> prior{};
    for (std::size_t n = 0; n < prior.size(); ++n) {
        if (it == history.rend()) return false;
        prior[n] = *it;
        while (it != history.rend() && *it == prior[n]) ++it;
    }
    return length - prior[0] == prior[0] - prior[1];
}

int predictGeometric(const std::deque<int>& history, int length) {
    if (history.empty() || history.back() != length) return 0;
    std::array<int, 3> sizes{};
    std::array<std::size_t, 3> counts{};
    auto it = history.rbegin();
    for (std::size_t n = 0; n < sizes.size(); ++n) {
        if (it == history.rend()) return 0;
        sizes[n] = *it;
        while (it != history.rend() && *it == sizes[n]) { ++counts[n]; ++it; }
        if (counts[n] < kRun) return 0;
    }
    if (!(sizes[2] < sizes[1] && sizes[1] < sizes[0])) return 0;
    if (2 * std::abs(sizes[0] * sizes[2] - sizes[1] * sizes[1]) > sizes[2]) return 0;
    const int predicted = (sizes[0] * sizes[1] + sizes[2] / 2) / sizes[2];
    return predicted > length && predicted <= 40 ? predicted : 0;
}

bool geometricSide(const std::deque<int>& history, int length,
                   I start, I end, bool fallback) {
    const int predicted = predictGeometric(history, length);
    if (predicted <= length || end - start <= length) return fallback;
    const auto distance = [predicted](I coordinate) {
        const I residue = coordinate % predicted;
        return std::min(residue, static_cast<I>(predicted) - residue);
    };
    const I low = distance(start + length), high = distance(start);
    return low == high ? fallback : high < low;
}

struct RolloutState {
    bool confidentRecentAddress = false;
    std::map<I, SimGap> gaps;
    std::vector<SimPipe> active;
    I trench = 0;
    int nextPid = 1;
    std::deque<int> history;
    std::array<int, 41> frequency{};
    std::array<I, 41> occurrences{};
    std::array<std::array<I, 2>, 41> removed{};
    bool parityMode = false, smoothSeen = false, alternating = false;
    int deletedParity = 1, lastDeletedPid = -1, lastDeletedLength = -1;
    std::size_t strideTwo = 0;

    void add(I start, I end, int cohort) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto prev = std::prev(it);
            if (prev->second.end >= start) {
                if (prev->second.cohort != cohort) cohort = -1;
                start = prev->first;
                end = std::max(end, prev->second.end);
                gaps.erase(prev);
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

    void split(I gapStart, int length, bool high) {
        const auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        const SimGap gap = it->second;
        const I start = high ? gap.end - length : gapStart;
        gaps.erase(it);
        add(gapStart, start, gap.cohort);
        add(start + length, gap.end, gap.cohort);
    }

    void record(int length) {
        history.push_back(length);
        ++frequency[static_cast<std::size_t>(length)];
        if (history.size() > kHistory) {
            --frequency[static_cast<std::size_t>(history.front())];
            history.pop_front();
        }
    }

    I score(I gapLength, int length) const {
        const I slack = gapLength - length;
        I result = slack * static_cast<I>(history.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int r = static_cast<int>(slack) + 1; r <= 40; ++r) misses += frequency[static_cast<std::size_t>(r)];
            result += 60 * static_cast<I>(misses);
        }
        return result;
    }

    std::optional<I> best(int length, bool high, int cohort) const {
        bool preferred = false;
        if (parityMode) {
            for (const auto& [start, gap] : gaps) {
                if (gap.end - start >= length && gap.cohort == cohort) { preferred = true; break; }
            }
        }
        std::set<I> considered;
        bool found = false;
        I bestStart = 0, bestScore = std::numeric_limits<I>::max();
        for (const auto& [start, gap] : gaps) {
            const I size = gap.end - start;
            if (size < length) continue;
            if (parityMode && (preferred ? gap.cohort != cohort : gap.cohort >= 0)) continue;
            if (!considered.insert(size).second && !(confidentRecentAddress && high)) continue;
            const I value = score(size, length);
            if (!found || value < bestScore || (value == bestScore &&
                (high ? start > bestStart : start < bestStart))) {
                found = true; bestScore = value; bestStart = start;
            }
        }
        return found ? std::optional<I>(bestStart) : std::nullopt;
    }

    void append(int length, I start, int cohort) {
        active.push_back(SimPipe{nextPid++, start, length, cohort});
        ++occurrences[static_cast<std::size_t>(length)];
        record(length);
    }

    void placeCandidate(I gapStart, int length, bool high) {
        const auto it = gaps.find(gapStart);
        if (it == gaps.end()) return;
        const int cohort = static_cast<int>(occurrences[static_cast<std::size_t>(length)] % 2);
        const I start = high ? it->second.end - length : gapStart;
        split(gapStart, length, high);
        append(length, start, cohort);
    }

    void place(int length) {
        const int cohort = static_cast<int>(occurrences[static_cast<std::size_t>(length)] % 2);
        if (smoothTrend(history, length)) smoothSeen = true;
        const bool run = sameRun(history, length);
        const bool geometric = !smoothSeen && run;
        const bool reverse = smoothSeen && run && alternating;
        const bool high = geometric || reverse
            ? (reverse ? cohort == 0 : (nextPid & 1) == 0)
            : (alternating ? (nextPid & 1) != deletedParity
                : (parityMode ? cohort == 0 : length <= 4 || run));
        I start = -1;
        const auto chosen = best(length, high, cohort);
        if (chosen) {
            const auto it = gaps.find(*chosen);
            const bool side = geometric ? geometricSide(history, length, it->first, it->second.end, high) : high;
            start = side ? it->second.end - length : it->first;
            split(*chosen, length, side);
        }
        if (start < 0) {
            auto tail = gaps.end();
            if (!gaps.empty() && std::prev(gaps.end())->second.end == trench) tail = std::prev(gaps.end());
            int tailCohort = parityMode ? cohort : -1;
            bool preserve = false;
            if (parityMode && tail != gaps.end()) {
                tailCohort = tail->second.cohort;
                preserve = tailCohort >= 0 && tailCohort != cohort;
                if (preserve) tailCohort = cohort;
            }
            const I tailStart = tail == gaps.end() || preserve ? trench : tail->first;
            const I deficit = std::max<I>(0, length - (trench - tailStart));
            trench += (deficit + kDig - 1) / kDig * kDig;
            if (tail != gaps.end() && !preserve) gaps.erase(tail);
            if (parityMode && high && !preserve) {
                start = trench - length;
                add(tailStart, start, tailCohort);
            } else {
                start = tailStart;
                add(start + length, trench, tailCohort);
            }
        }
        append(length, start, cohort);
    }

    void removeRank(int permille) {
        if (active.empty()) return;
        const std::size_t n = active.size();
        const std::size_t rank = n <= 1 ? 0 : static_cast<std::size_t>(permille) * (n - 1) / 1000;
        const std::size_t index = n - 1 - std::min(rank, n - 1);
        const SimPipe pipe = active[index];
        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
        add(pipe.start, pipe.start + pipe.length, pipe.cohort);
        if (lastDeletedPid >= 0 && lastDeletedLength == pipe.length && pipe.pid == lastDeletedPid + 2) ++strideTwo;
        else { strideTwo = 0; alternating = false; }
        if (strideTwo >= 7) { alternating = true; deletedParity = pipe.pid & 1; }
        lastDeletedPid = pipe.pid; lastDeletedLength = pipe.length;
        auto& counts = removed[static_cast<std::size_t>(pipe.length)];
        ++counts[static_cast<std::size_t>(pipe.cohort)];
        const I total = counts[0] + counts[1];
        if (total >= 8 && std::max(counts[0], counts[1]) * 100 >= total * 85 && steadyTrend(history)) parityMode = true;
    }

    void apply(const Observation& event) {
        if (event.kind > 0) place(event.value);
        else if (event.kind < 0) removeRank(event.value);
    }
};

class CensoredLifetimeModel {
    static constexpr std::array<U, 8> kLower{0, 16, 64, 256, 1024, 4096, 16384, 65536};
    static constexpr std::size_t kBins = kLower.size();
    struct Record { U born = 0; int length = 0; int context = 0; bool active = false; };
    struct Cell { U completedExposure = 0, birthSum = 0, active = 0, deaths = 0; };
    struct Estimate { double mean = 0.0, error = 0.0; };
    using CellGrid = std::array<std::array<Cell, kBins>, 41>;
    using RateGrid = std::array<std::array<Estimate, kBins>, 41>;
    std::vector<Record> records_{Record{}};
    CellGrid cells_{};
    std::array<CellGrid, 2> contextCells_{};
    RateGrid rates_{};
    std::array<RateGrid, 2> contextRates_{};
    std::array<std::size_t, kBins> nextCrossing_{};
    U clock_ = 0;
    int birthContext_ = 0;
    double referenceRate_ = 0.0, referenceError_ = 0.0;
    bool fitted_ = false;
    mutable U supportedQueries_ = 0;

    static std::size_t ageBin(U age) {
        std::size_t bin = 0;
        while (bin + 1 < kBins && age >= kLower[bin + 1]) ++bin;
        return bin;
    }
    static void enterCell(Cell& cell, const Record& record) {
        ++cell.active; cell.birthSum += record.born;
    }
    static void leaveCell(Cell& cell, const Record& record, std::size_t bin, U age) {
        cell.completedExposure += age - kLower[bin];
        --cell.active; cell.birthSum -= record.born;
    }
    void enter(const Record& record, std::size_t bin) {
        const auto length = static_cast<std::size_t>(record.length);
        enterCell(cells_[length][bin], record);
        enterCell(contextCells_[static_cast<std::size_t>(record.context)][length][bin], record);
    }
    void leave(const Record& record, std::size_t bin, U age) {
        const auto length = static_cast<std::size_t>(record.length);
        leaveCell(cells_[length][bin], record, bin, age);
        leaveCell(contextCells_[static_cast<std::size_t>(record.context)][length][bin], record, bin, age);
    }
    U exposure(const Cell& cell, std::size_t bin) const {
        const U outstanding = cell.active == 0 ? 0 : cell.active * (clock_ - kLower[bin]) - cell.birthSum;
        return cell.completedExposure + outstanding;
    }
    Estimate predict(int length, U age, int context = -1) const {
        Estimate result;
        const U end = age + static_cast<U>(kHistory);
        std::size_t bin = ageBin(age);
        while (age < end) {
            const U next = bin + 1 < kBins ? std::min(end, kLower[bin + 1]) : end;
            const double weight = static_cast<double>(next - age) / static_cast<double>(kHistory);
            const auto index = static_cast<std::size_t>(length);
            const Estimate& rate = context < 0 ? rates_[index][bin]
                : contextRates_[static_cast<std::size_t>(context)][index][bin];
            result.mean += weight * rate.mean;
            result.error += weight * rate.error;
            age = next;
            if (age < end) ++bin;
        }
        return result;
    }
    double risk(int length, U age, int context, bool useContext) const {
        if (!fitted_) return 1.0;
        const Estimate pooled = predict(length, age);
        const double margin = 2.0 * (pooled.error + referenceError_);
        double supported = referenceRate_;
        if (pooled.mean - margin > referenceRate_) supported = pooled.mean - margin;
        else if (pooled.mean + margin < referenceRate_) supported = pooled.mean + margin;
        if (useContext) {
            const Estimate conditional = predict(length, age, context);
            const double difference = conditional.mean - pooled.mean;
            const double uncertainty = 2.0 * (conditional.error + pooled.error);
            double correction = 0.0;
            if (difference > uncertainty) correction = difference - uncertainty;
            else if (difference < -uncertainty) correction = difference + uncertainty;
            if (correction != 0.0) { supported += correction; ++supportedQueries_; }
        }
        return std::clamp(supported / referenceRate_, 0.5, 2.0);
    }
public:
    CensoredLifetimeModel() { nextCrossing_.fill(1); }
    void setBirthContext(bool followsDeletion) { birthContext_ = followsDeletion ? 1 : 0; }
    U supportedQueries() const { return supportedQueries_; }
    void advance() {
        ++clock_;
        for (std::size_t bin = 1; bin < kBins; ++bin) {
            auto& cursor = nextCrossing_[bin];
            while (cursor < records_.size() && clock_ - records_[cursor].born >= kLower[bin]) {
                const Record& record = records_[cursor++];
                if (!record.active) continue;
                leave(record, bin - 1, kLower[bin]);
                enter(record, bin);
            }
        }
    }
    void observeBirth(int length) {
        records_.push_back(Record{clock_, length, birthContext_, true});
        enter(records_.back(), 0);
    }
    void observeDeletion(std::size_t pid) {
        Record& record = records_[pid];
        const U age = clock_ - record.born;
        leave(record, ageBin(age), age);
        const std::size_t eventBin = ageBin(age == 0 ? 0 : age - 1);
        const auto length = static_cast<std::size_t>(record.length);
        ++cells_[length][eventBin].deaths;
        ++contextCells_[static_cast<std::size_t>(record.context)][length][eventBin].deaths;
        record.active = false;
    }
    bool fit(double priorHazard) {
        fitted_ = false;
        if (!(priorHazard > 0.0)) return false;
        constexpr double priorEvents = 8.0;
        for (std::size_t bin = 0; bin < kBins; ++bin) {
            double pooledExposure = 0.0, pooledDeaths = 0.0;
            for (std::size_t length = 1; length <= 40; ++length) {
                pooledExposure += static_cast<double>(exposure(cells_[length][bin], bin));
                pooledDeaths += static_cast<double>(cells_[length][bin].deaths);
            }
            const double pooledDenominator = pooledExposure + priorEvents / priorHazard;
            const double pooledRate = (pooledDeaths + priorEvents) / pooledDenominator;
            const double pooledError = std::sqrt(pooledDeaths + priorEvents) / pooledDenominator;
            for (std::size_t length = 1; length <= 40; ++length) {
                const auto& cell = cells_[length][bin];
                const double borrowed = priorEvents / pooledRate;
                const double denominator = static_cast<double>(exposure(cell, bin)) + borrowed;
                const double shape = static_cast<double>(cell.deaths) + priorEvents;
                const Estimate pooled{shape / denominator,
                    std::sqrt(shape) / denominator + borrowed / denominator * pooledError};
                rates_[length][bin] = pooled;
                for (std::size_t context = 0; context < 2; ++context) {
                    const auto& conditional = contextCells_[context][length][bin];
                    const double contextBorrowed = priorEvents / pooled.mean;
                    const double contextDenominator = static_cast<double>(exposure(conditional, bin)) + contextBorrowed;
                    const double contextShape = static_cast<double>(conditional.deaths) + priorEvents;
                    contextRates_[context][length][bin] = Estimate{
                        contextShape / contextDenominator,
                        std::sqrt(contextShape) / contextDenominator +
                            contextBorrowed / contextDenominator * pooled.error};
                }
            }
        }
        double sumRate = 0.0, sumError = 0.0;
        U population = 0;
        for (std::size_t length = 1; length <= 40; ++length) {
            for (std::size_t bin = 0; bin < kBins; ++bin) {
                const auto& cell = cells_[length][bin];
                if (cell.active == 0) continue;
                const U meanAge = clock_ - cell.birthSum / cell.active;
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
    double existingRisk(int pid, bool useContext = true) const {
        const Record& record = records_[static_cast<std::size_t>(pid)];
        return risk(record.length, clock_ - record.born, record.context, useContext);
    }
    double newRisk(int length, bool useContext = true) const {
        return risk(length, 0, birthContext_, useContext);
    }
};

class Allocator {
    using StartIter = std::map<I, I>::iterator;
    std::map<I, I> gaps;
    std::set<std::pair<I, I>> sizes;
    std::map<I, int> owners;
    std::array<std::set<std::pair<I, I>>, 2> cohortSizes;
    std::set<std::pair<I, I>> sharedSizes;
    std::map<I, int> activeByEnd;
    std::vector<Pipe> pipes{Pipe{}};
    I trench = 0;
    std::deque<int> history;
    std::array<int, 41> frequency{};
    std::array<I, 41> occurrences{};
    std::array<std::array<I, 2>, 41> removed{};
    bool parityMode = false, smoothSeen = false, alternating = false;
    int deletedParity = 1, lastDeletedPid = -1, lastDeletedLength = -1;
    std::size_t strideTwo = 0;
    std::vector<int> fenwick = std::vector<int>(200001, 0);
    std::size_t activeCount = 0;
    std::deque<Observation> observations;
    std::deque<int> deleteRanks;
    bool lifoDisabled = false;
    std::size_t mcDecisions = 0, mcRollouts = 0;
    std::deque<std::pair<int, int>> completedRuns;
    int runLength = -1, runCount = 0, runFirstPid = 1;
    std::array<std::size_t, 2> runDeleted{};
    int lastRelativeParity = -1, previousRelativeParity = -1;
    bool slabActive = false, slabExpanded = false;
    int slabExpected = 0, slabDeleteParity = 0, slabDeleteCount = 0;
    int slabDeletedUsed = 0, slabSurvivorUsed = 0, slabGapRemaining = 0;
    int slabTailCount = 0, slabUsed = 0;
    I slabBase = 0, slabEnd = 0;
    std::array<I, kCap + 2> gapCounts{};
    std::array<int, kHistory> eventHistory{};
    std::array<int, 41> requests{};
    std::array<double, kCap + 1> gapValue{};
    std::size_t eventPosition = 0;
    int recentDeletes = 0, computedLimit = 0;
    U step = 0, modelStep = 0;
    bool modelDirty = true;
    CensoredLifetimeModel lifetime;
    bool previousWasDeletion = false;
    std::array<double, 41> causalRate{};
    std::array<std::array<double, kCap + 1>, 2> causalValue{};
    double baseExpiry = 0.0;
    int causalLimit = 0;
    bool riskReady = false;
    U contextCompared = 0, contextChanged = 0, modelRebuilds = 0;

    void fenwickAdd(int index, int delta) {
        const int limit = static_cast<int>(fenwick.size());
        for (int p = index; p < limit; p += p & -p) fenwick[static_cast<std::size_t>(p)] += delta;
    }
    int prefix(int index) const {
        int result = 0;
        for (int p = index; p > 0; p -= p & -p) result += fenwick[static_cast<std::size_t>(p)];
        return result;
    }
    int rankNewest(int pid) const {
        if (activeCount <= 1) return 0;
        const std::size_t newer = activeCount - static_cast<std::size_t>(prefix(pid));
        return static_cast<int>(newer * 1000U / (activeCount - 1));
    }
    void eraseGap(StartIter it) {
        const I start = it->first, size = it->second - start;
        --gapCounts[static_cast<std::size_t>(std::min<I>(kCap + 1, size))];
        sizes.erase({size, start});
        const int owner = owners.at(start);
        if (owner >= 0 && owner <= 1) cohortSizes[static_cast<std::size_t>(owner)].erase({size, start});
        else sharedSizes.erase({size, start});
        owners.erase(start);
        gaps.erase(it);
    }
    void addGap(I start, I end, int owner) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto prev = std::prev(it);
            if (prev->second >= start) {
                if (owners.at(prev->first) != owner) owner = -1;
                start = prev->first;
                end = std::max(end, prev->second);
                eraseGap(prev);
                it = gaps.lower_bound(start);
            }
        }
        while (it != gaps.end() && it->first <= end) {
            if (owners.at(it->first) != owner) owner = -1;
            end = std::max(end, it->second);
            auto old = it++;
            eraseGap(old);
        }
        gaps.emplace(start, end);
        const I size = end - start;
        ++gapCounts[static_cast<std::size_t>(std::min<I>(kCap + 1, size))];
        sizes.emplace(size, start);
        owners.emplace(start, owner);
        if (owner >= 0 && owner <= 1) cohortSizes[static_cast<std::size_t>(owner)].emplace(size, start);
        else sharedSizes.emplace(size, start);
    }
    I consume(StartIter it, int length, bool high) {
        const I begin = it->first, end = it->second;
        const int owner = owners.at(begin);
        const I start = high ? end - length : begin;
        eraseGap(it);
        addGap(begin, start, owner);
        addGap(start + length, end, owner);
        return start;
    }
    StartIter tailGap() {
        if (gaps.empty()) return gaps.end();
        auto it = std::prev(gaps.end());
        return it->second == trench ? it : gaps.end();
    }
    I fitScore(I size, int length) const {
        const I slack = size - length;
        I score = slack * static_cast<I>(history.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int r = static_cast<int>(slack) + 1; r <= 40; ++r) misses += frequency[static_cast<std::size_t>(r)];
            score += 60 * static_cast<I>(misses);
        }
        return score;
    }
    void recordLength(int length) {
        history.push_back(length);
        ++frequency[static_cast<std::size_t>(length)];
        if (history.size() > kHistory) {
            --frequency[static_cast<std::size_t>(history.front())];
            history.pop_front();
        }
    }
    void recordObservation(Observation event) {
        observations.push_back(event);
        if (observations.size() > kMcHistory) observations.pop_front();
        if (event.kind < 0) {
            deleteRanks.push_back(event.value);
            if (deleteRanks.size() > 64) deleteRanks.pop_front();
        }
    }
    void recordEvent(int event) {
        if (event > 0) lifetime.observeBirth(event);
        const int old = eventHistory[eventPosition];
        if (old > 0) {
            if (--requests[static_cast<std::size_t>(old)] == 0) modelDirty = true;
        } else if (old < 0) {
            if (--recentDeletes == 0) modelDirty = true;
        }
        eventHistory[eventPosition] = event;
        eventPosition = (eventPosition + 1) % eventHistory.size();
        if (event > 0) {
            if (requests[static_cast<std::size_t>(event)]++ == 0) modelDirty = true;
        } else if (event < 0) {
            if (recentDeletes++ == 0) modelDirty = true;
        }
        ++step;
    }
    void deletionPattern(int pid, int length) {
        if (lastDeletedPid >= 0 && lastDeletedLength == length && pid == lastDeletedPid + 2) ++strideTwo;
        else { strideTwo = 0; alternating = false; }
        if (strideTwo >= 7) { alternating = true; deletedParity = pid & 1; }
        lastDeletedPid = pid; lastDeletedLength = length;
    }
    bool lifoConfidence() const {
        if (activeCount < 128 || deleteRanks.size() < 48) return false;
        std::size_t top = 0;
        for (int rank : deleteRanks) if (rank <= 50) ++top;
        if (top * 100 < deleteRanks.size() * 80) return false;
        std::size_t shortCount = 0;
        for (int length : history) if (length <= 8) ++shortCount;
        return history.size() >= 64 && shortCount * 100 >= history.size() * 90;
    }
    bool lifoLane(int length) const {
        return !lifoDisabled && length <= 8 && lifoConfidence();
    }
    bool unitDominant() const {
        if (history.size() < 128) return false;
        const std::size_t window = std::min<std::size_t>(history.size(), 2048);
        auto it = history.rbegin();
        std::size_t units = 0;
        for (std::size_t n = 0; n < window; ++n, ++it) if (*it == 1) ++units;
        return units * 100 >= window * 85;
    }
    bool youngTailNeighbor(I start) const {
        const auto it = activeByEnd.find(start);
        return it != activeByEnd.end() && rankNewest(it->second) <= 50;
    }
    bool additiveTrend(int length) const {
        if (length < 3 || length >= 40 || runCount < 46) return false;
        std::array<int, 3> values{length, 0, 0};
        auto it = history.rbegin();
        while (it != history.rend() && *it == length) ++it;
        for (std::size_t n = 1; n < values.size(); ++n) {
            if (it == history.rend()) return false;
            values[n] = *it;
            int count = 0;
            while (it != history.rend() && *it == values[n]) { ++count; ++it; }
            if (count < 46) return false;
        }
        return values[0] == values[1] + 1 && values[1] == values[2] + 1;
    }
    bool additiveSide(int length, I start, bool fallback) const {
        const I modulus = length + 1;
        const auto distance = [modulus](I coordinate) {
            const I residue = coordinate % modulus;
            return std::min(residue, modulus - residue);
        };
        const I low = distance(start + length), high = distance(start);
        return low == high ? fallback : high < low;
    }
    int earlyGeometric(int length) const {
        if (completedRuns.size() != 1 || runCount < 46 || runCount > 1024 ||
            !alternating || strideTwo < 7 || activeCount > 4096 || gaps.size() > 4096) return 0;
        const auto previous = completedRuns.back();
        if (previous.second < 46 || previous.first <= 0 || lastDeletedLength != previous.first ||
            length != previous.first * 2 || length > 20) return 0;
        return length * 2;
    }
    StartIter bestBefore(int length, bool high, int cohort, I limit) {
        auto best = gaps.end();
        I bestScore = std::numeric_limits<I>::max();
        for (auto it = gaps.begin(); it != gaps.end(); ++it) {
            if (it->second > limit || it->second - it->first < length) continue;
            if (parityMode) {
                const int owner = owners.at(it->first);
                if (owner >= 0 && owner != cohort) continue;
            }
            const I score = fitScore(it->second - it->first, length);
            if (score < bestScore || (score == bestScore && best != gaps.end() &&
                (high ? it->first > best->first : it->first < best->first))) {
                bestScore = score; best = it;
            }
        }
        return best;
    }
    void beginSlab(int length) {
        if (completedRuns.size() < 2 || !alternating) return;
        const auto previous = completedRuns[completedRuns.size() - 2];
        const auto last = completedRuns.back();
        if (!(previous.first < last.first && last.first < length) || lastDeletedLength != last.first) return;
        const int nextStep = length - last.first;
        const int nextSize = length + nextStep;
        if (nextSize > 40) return;
        const bool unitStaircase = last.first - previous.first == nextStep && nextStep == 1;
        const int tolerance = std::max(10, std::max(previous.second, last.second) / 10);
        if (std::abs(previous.second - last.second) > tolerance) return;
        const int expected = (previous.second + last.second) / 2;
        if (expected < 64) return;
        int predictedParity = deletedParity;
        if (lastRelativeParity >= 0 && previousRelativeParity == lastRelativeParity)
            predictedParity = (runFirstPid & 1) ^ lastRelativeParity;
        const int firstPid = static_cast<int>(pipes.size());
        const int deleteCount = expected / 2 + ((expected & 1) && (firstPid & 1) == predictedParity ? 1 : 0);
        const int survivorCount = expected - deleteCount;
        const int firstOccurrenceParity = static_cast<int>(occurrences[static_cast<std::size_t>(length)] & 1);
        const int survivorCohort = firstOccurrenceParity ^ ((firstPid & 1) == predictedParity ? 1 : 0);
        I reusable = 0;
        for (const auto& [start, end] : gaps) {
            if (parityMode) {
                const int owner = owners.at(start);
                if (owner >= 0 && owner != survivorCohort) continue;
            }
            reusable = std::min<I>(survivorCount, reusable + (end - start) / length);
            if (reusable >= survivorCount) break;
        }
        const int gapCount = static_cast<int>(reusable);
        const int tailCount = expected - gapCount;
        const I predictedCapacity = static_cast<I>(deleteCount) * length / nextSize;
        if (predictedCapacity < 64) {
            if (!unitStaircase) return;
            I existing = 0;
            for (const auto& [start, end] : gaps) {
                if (parityMode) {
                    const int owner = owners.at(start);
                    if (owner >= 0 && owner != 0) continue;
                }
                existing += (end - start) / nextSize;
            }
            if (predictedCapacity <= existing) return;
        }
        const I raw = static_cast<I>(tailCount) * length;
        slabActive = true; slabExpanded = false;
        slabExpected = expected; slabDeleteParity = predictedParity;
        slabDeleteCount = deleteCount; slabDeletedUsed = 0; slabSurvivorUsed = 0;
        slabGapRemaining = gapCount; slabTailCount = tailCount; slabUsed = 0;
        slabBase = trench; slabEnd = trench + (raw + kDig - 1) / kDig * kDig;
    }
    using Obstacle = std::pair<I, I>;
    I projectedCapacity(const std::vector<Obstacle>& obstacles, I start, int length, int nextLength) const {
        if (start < 0 || nextLength <= 0) return -1;
        const auto right = std::lower_bound(obstacles.begin(), obstacles.end(), start,
            [](const Obstacle& obstacle, I coordinate) { return obstacle.first < coordinate; });
        const I leftEnd = right == obstacles.begin() ? 0 : std::prev(right)->second;
        const I rightStart = right == obstacles.end() ? trench : right->first;
        if (leftEnd > start || rightStart < start + length) return -1;
        return (start - leftEnd) / nextLength + (rightStart - start - length) / nextLength;
    }
    std::pair<StartIter, bool> counterfactualGap(int length, int nextLength, bool fallback,
                                               int cohort, StartIter baseline) {
        if (activeCount > 4096 || gaps.size() > 4096) return {gaps.end(), fallback};
        std::vector<Obstacle> obstacles;
        obstacles.reserve(activeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            const Pipe& pipe = pipes[pid];
            if (!pipe.active || (pipe.length == length && (static_cast<int>(pid) & 1) == deletedParity)) continue;
            obstacles.emplace_back(pipe.start, pipe.start + pipe.length);
        }
        std::sort(obstacles.begin(), obstacles.end());
        const I baselineStart = baseline == gaps.end() ? -1 : (fallback ? baseline->second - length : baseline->first);
        const I baselineCapacity = projectedCapacity(obstacles, baselineStart, length, nextLength);
        auto best = gaps.end();
        bool bestHigh = fallback;
        I bestStart = -1, bestCapacity = -1, bestScore = std::numeric_limits<I>::max();
        const auto tail = tailGap();
        const auto search = [&](int ownerMode) {
            for (auto it = gaps.begin(); it != gaps.end(); ++it) {
                const I size = it->second - it->first;
                const int owner = owners.at(it->first);
                if (size < length || (tail != gaps.end() && it == tail) ||
                    (ownerMode == 1 && owner != cohort) || (ownerMode == 2 && owner >= 0)) continue;
                const I score = fitScore(size, length);
                for (int side = 0; side < 2; ++side) {
                    const bool high = side != 0;
                    const I start = high ? it->second - length : it->first;
                    const I capacity = projectedCapacity(obstacles, start, length, nextLength);
                    if (capacity < 0) continue;
                    const bool preferredSide = high == fallback, bestPreferredSide = bestHigh == fallback;
                    const bool preferredAddress = best != gaps.end() && (high ? start > bestStart : start < bestStart);
                    if (capacity > bestCapacity || (capacity == bestCapacity && score < bestScore) ||
                        (capacity == bestCapacity && score == bestScore && preferredSide && !bestPreferredSide) ||
                        (capacity == bestCapacity && score == bestScore && preferredSide == bestPreferredSide && preferredAddress)) {
                        best = it; bestHigh = high; bestStart = start; bestCapacity = capacity; bestScore = score;
                    }
                }
            }
        };
        if (parityMode) { search(1); if (best == gaps.end()) search(2); }
        else search(0);
        if (best == gaps.end() || bestCapacity <= baselineCapacity) return {gaps.end(), fallback};
        return {best, bestHigh};
    }

    static void fillValues(std::array<double, kCap + 1>& value,
                           const std::array<double, 41>& rate, double expiry, int limit) {
        value.fill(0.0);
        for (int gap = 1; gap <= limit; ++gap) {
            const int top = std::min(gap, 40);
            if (expiry == 0.0) {
                for (int request = 1; request <= top; ++request) {
                    if (rate[static_cast<std::size_t>(request)] > 0.0)
                        value[static_cast<std::size_t>(gap)] = std::max(value[static_cast<std::size_t>(gap)],
                            request + value[static_cast<std::size_t>(gap - request)]);
                }
                continue;
            }
            std::array<double, 41> reward{};
            U active = 0;
            double numerator = 0.0, denominator = expiry;
            for (int request = 1; request <= top; ++request) {
                const double r = rate[static_cast<std::size_t>(request)];
                if (r == 0.0) continue;
                reward[static_cast<std::size_t>(request)] = request + value[static_cast<std::size_t>(gap - request)];
                numerator += r * reward[static_cast<std::size_t>(request)];
                denominator += r;
                active |= U{1} << static_cast<unsigned>(request);
            }
            double estimate = numerator / denominator;
            for (;;) {
                bool removedAny = false;
                for (int request = 1; request <= top; ++request) {
                    const U bit = U{1} << static_cast<unsigned>(request);
                    if ((active & bit) && reward[static_cast<std::size_t>(request)] < estimate) {
                        numerator -= rate[static_cast<std::size_t>(request)] * reward[static_cast<std::size_t>(request)];
                        denominator -= rate[static_cast<std::size_t>(request)];
                        active &= ~bit; removedAny = true;
                    }
                }
                if (!removedAny) break;
                estimate = numerator / denominator;
            }
            value[static_cast<std::size_t>(gap)] = std::clamp(estimate, 0.0, static_cast<double>(gap));
        }
    }
    void rebuildValues(int limit) {
        std::array<double, 41> rate{};
        I fitting = gapCounts[kCap + 1];
        for (int gap = kCap; gap >= 1; --gap) {
            fitting += gapCounts[static_cast<std::size_t>(gap)];
            if (gap <= 40) rate[static_cast<std::size_t>(gap)] =
                static_cast<double>(requests[static_cast<std::size_t>(gap)]) / static_cast<double>(std::max<I>(1, fitting));
        }
        const double expiry = 2.0 * static_cast<double>(recentDeletes) /
            static_cast<double>(std::max<std::size_t>(1, activeCount));
        fillValues(gapValue, rate, expiry, limit);
        causalRate = rate; baseExpiry = expiry; causalLimit = 0;
        riskReady = !parityMode && activeCount > kMcMaxActive && expiry > 0.0 &&
            lifetime.fit(expiry / (2.0 * static_cast<double>(kHistory)));
        modelStep = step; computedLimit = limit; modelDirty = false; ++modelRebuilds;
    }
    bool ensureValues(int limit) {
        if (limit <= 0 || limit > kCap) return false;
        if (modelDirty || step - modelStep >= 64 || limit > computedLimit) rebuildValues(limit);
        for (std::size_t length = 1; length < requests.size(); ++length) if (requests[length] > 0) return true;
        return false;
    }
    double primalLoss(I size, int length) const {
        return gapValue[static_cast<std::size_t>(size)] - gapValue[static_cast<std::size_t>(size - length)];
    }
    void rebuildCausal(int limit) {
        fillValues(causalValue[0], causalRate, baseExpiry * 0.5, limit);
        fillValues(causalValue[1], causalRate, baseExpiry * 2.0, limit);
        causalLimit = limit;
    }
    double adjustedValue(int gap, double factor) const {
        const auto index = static_cast<std::size_t>(gap);
        const double base = gapValue[index];
        if (factor <= 1.0) return base + 2.0 * (1.0 - factor) * (causalValue[0][index] - base);
        return base + (factor - 1.0) * (causalValue[1][index] - base);
    }
    double lifetimeLoss(StartIter gap, int length, bool high, int limit,
                        double freshRisk, bool useContext) {
        const I size = gap->second - gap->first;
        double leftRisk = 1.0, rightRisk = 1.0;
        const auto left = activeByEnd.find(gap->first);
        if (left != activeByEnd.end()) leftRisk = lifetime.existingRisk(left->second, useContext);
        const auto right = activeByEnd.upper_bound(gap->second);
        if (right != activeByEnd.end() && pipes[static_cast<std::size_t>(right->second)].start == gap->second)
            rightRisk = lifetime.existingRisk(right->second, useContext);
        const double originalFactor = 0.5 * (leftRisk + rightRisk);
        const double remainingFactor = 0.5 * (freshRisk + (high ? leftRisk : rightRisk));
        if (originalFactor == 1.0 && remainingFactor == 1.0) return primalLoss(size, length);
        if (causalLimit < limit) rebuildCausal(limit);
        return adjustedValue(static_cast<int>(size), originalFactor) -
            adjustedValue(static_cast<int>(size) - length, remainingFactor);
    }
    StartIter lifetimeChoice(const std::vector<std::pair<I, I>>& candidates,
                             int length, bool high, StartIter baseline) {
        if (!riskReady || alternating || runCount >= static_cast<int>(kRun) || candidates.size() < 2) return baseline;
        auto challenger = gaps.end();
        double bestScore = std::numeric_limits<double>::infinity();
        for (const auto& [size, start] : candidates) {
            if (start == baseline->first) continue;
            const double score = primalLoss(size, length);
            const bool better = score + 1e-9 < bestScore;
            const bool tied = !(bestScore + 1e-9 < score) && !(score + 1e-9 < bestScore);
            const bool address = challenger != gaps.end() && (high ? start > challenger->first : start < challenger->first);
            if (challenger == gaps.end() || better || (tied && address)) {
                bestScore = score; challenger = gaps.find(start);
            }
        }
        if (challenger == gaps.end()) return baseline;
        const int limit = static_cast<int>(std::max(baseline->second - baseline->first, challenger->second - challenger->first));
        const double pooledFresh = lifetime.newRisk(length, false);
        const double contextualFresh = lifetime.newRisk(length, true);
        const double pooledBase = lifetimeLoss(baseline, length, high, limit, pooledFresh, false);
        const double pooledOther = lifetimeLoss(challenger, length, high, limit, pooledFresh, false);
        const double contextualBase = lifetimeLoss(baseline, length, high, limit, contextualFresh, true);
        const double contextualOther = lifetimeLoss(challenger, length, high, limit, contextualFresh, true);
        const bool oldSwitch = pooledOther + 1e-9 < pooledBase;
        const bool newSwitch = contextualOther + 1e-9 < contextualBase;
        ++contextCompared;
        if (oldSwitch != newSwitch) ++contextChanged;
        return newSwitch ? challenger : baseline;
    }
    StartIter bestFromSet(const std::set<std::pair<I, I>>& index, int length, bool high) {
        auto first = index.lower_bound({length, 0});
        if (first == index.end()) return gaps.end();
        if (history.empty()) return gaps.find(first->second);
        const bool highAddress = high && !lifoDisabled && lifoConfidence();
        std::vector<std::pair<I, I>> candidates;
        auto it = first;
        while (it != index.end()) {
            if (highAddress) it = std::prev(index.upper_bound({it->first, std::numeric_limits<I>::max()}));
            const I size = it->first;
            candidates.emplace_back(size, it->second);
            if (size - length > 40) break;
            it = index.upper_bound({size, std::numeric_limits<I>::max()});
        }
        auto best = gaps.end();
        I bestScore = std::numeric_limits<I>::max();
        for (const auto& [size, start] : candidates) {
            const I score = fitScore(size, length);
            if (score < bestScore || (score == bestScore && best != gaps.end() &&
                (high ? start > best->first : start < best->first))) {
                bestScore = score; best = gaps.find(start);
            }
        }
        if (!parityMode && activeCount > kMcMaxActive && candidates.front().first > length) {
            const I limit = candidates.back().first;
            if (limit <= kCap && ensureValues(static_cast<int>(limit))) {
                auto primalBest = gaps.end();
                double scoreBest = std::numeric_limits<double>::infinity();
                for (const auto& [size, start] : candidates) {
                    const double score = primalLoss(size, length);
                    const bool better = score + 1e-9 < scoreBest;
                    const bool tied = !(scoreBest + 1e-9 < score) && !(score + 1e-9 < scoreBest);
                    const bool address = primalBest != gaps.end() && (high ? start > primalBest->first : start < primalBest->first);
                    if (primalBest == gaps.end() || better || (tied && address)) {
                        scoreBest = score; primalBest = gaps.find(start);
                    }
                }
                if (primalBest != gaps.end()) best = lifetimeChoice(candidates, length, high, primalBest);
            }
        }
        return best;
    }
    StartIter bestGap(int length, bool high, int cohort) {
        if (!parityMode) return bestFromSet(sizes, length, high);
        auto preferred = bestFromSet(cohortSizes[static_cast<std::size_t>(cohort)], length, high);
        return preferred != gaps.end() ? preferred : bestFromSet(sharedSizes, length, high);
    }

    static std::uint32_t randomNext(std::uint32_t& state) {
        state ^= state << 13U; state ^= state >> 17U; state ^= state << 5U; return state;
    }
    static bool sameKey(const Observation& a, const Observation& b) {
        return a.kind == b.kind && (a.kind <= 0 || a.value == b.value);
    }
    std::array<Observation, kMcDepth> sample(std::uint32_t& randomState) const {
        std::array<Observation, kMcDepth> result{};
        const std::size_t n = observations.size();
        if (n < kMcDepth + 2) return result;
        const std::size_t minStart = n > 128 ? n - 128 : 0;
        const std::size_t maxStart = n - kMcDepth;
        std::vector<std::size_t> starts;
        for (std::size_t context = std::min<std::size_t>(3, n - 1); context > 0 && starts.empty(); --context) {
            for (std::size_t start = minStart + context; start <= maxStart; ++start) {
                bool matches = true;
                for (std::size_t offset = 0; offset < context; ++offset) {
                    if (!sameKey(observations[n - context + offset], observations[start - context + offset])) {
                        matches = false; break;
                    }
                }
                if (matches) starts.push_back(start);
            }
        }
        if (starts.empty()) for (std::size_t start = minStart; start <= maxStart; ++start) starts.push_back(start);
        if (starts.empty()) return result;
        const std::size_t start = starts[static_cast<std::size_t>(randomNext(randomState) % static_cast<std::uint32_t>(starts.size()))];
        for (std::size_t offset = 0; offset < kMcDepth; ++offset) result[offset] = observations[start + offset];
        return result;
    }
    RolloutState rolloutState() const {
        RolloutState state;
        state.confidentRecentAddress = !lifoDisabled && lifoConfidence();
        for (const auto& [start, end] : gaps) state.gaps.emplace(start, SimGap{end, owners.at(start)});
        state.trench = trench; state.nextPid = static_cast<int>(pipes.size());
        state.history = history; state.frequency = frequency; state.occurrences = occurrences; state.removed = removed;
        state.parityMode = parityMode; state.smoothSeen = smoothSeen; state.alternating = alternating;
        state.deletedParity = deletedParity; state.lastDeletedPid = lastDeletedPid;
        state.lastDeletedLength = lastDeletedLength; state.strideTwo = strideTwo;
        state.active.reserve(activeCount + 1);
        for (std::size_t pid = 1; pid < pipes.size(); ++pid) {
            const Pipe& pipe = pipes[pid];
            if (pipe.active) state.active.push_back(SimPipe{static_cast<int>(pid), pipe.start, pipe.length, pipe.cohort});
        }
        return state;
    }
    std::vector<GapCandidate> topCandidates(int length, bool high, int cohort) const {
        const auto* index = &sizes;
        if (parityMode) {
            const auto& preferred = cohortSizes[static_cast<std::size_t>(cohort)];
            index = preferred.lower_bound({length, 0}) != preferred.end() ? &preferred : &sharedSizes;
        }
        std::vector<GapCandidate> result;
        for (auto it = index->lower_bound({length, 0}); it != index->end(); ++it) {
            if (it->first - length > 40) break;
            result.push_back(GapCandidate{it->second, fitScore(it->first, length)});
        }
        std::sort(result.begin(), result.end(), [high](const GapCandidate& a, const GapCandidate& b) {
            if (a.score != b.score) return a.score < b.score;
            return high ? a.start > b.start : a.start < b.start;
        });
        if (result.size() > 3) result.resize(3);
        return result;
    }
    I chooseRollout(int length, bool high, int cohort, StartIter baseline) {
#if defined(MC_ROLLOUT_DISABLED)
        (void)length; (void)high; (void)cohort;
        return baseline->first;
#else
        if (mcDecisions >= kMcBudget || observations.size() < 32 || gaps.size() > kMcMaxGaps || activeCount > kMcMaxActive)
            return baseline->first;
        const auto candidates = topCandidates(length, high, cohort);
        if (candidates.size() < 2 || candidates.front().start != baseline->first) return baseline->first;
        ++mcDecisions;
        const RolloutState base = rolloutState();
        std::uint32_t randomState = 0x9e3779b9U ^ static_cast<std::uint32_t>(pipes.size() * 0x85ebca6bU) ^
            (static_cast<std::uint32_t>(length) * 0xc2b2ae35U) ^ static_cast<std::uint32_t>(trench);
        if (!randomState) randomState = 1;
        std::array<std::array<Observation, kMcDepth>, kMcTrials> scenarios{};
        for (auto& scenario : scenarios) scenario = sample(randomState);
        std::array<I, 3> total{};
        for (std::size_t candidate = 0; candidate < candidates.size(); ++candidate) {
            for (const auto& scenario : scenarios) {
                RolloutState simulation = base;
                simulation.placeCandidate(candidates[candidate].start, length, high);
                for (const auto& event : scenario) simulation.apply(event);
                total[candidate] += simulation.trench; ++mcRollouts;
            }
        }
        std::size_t best = 0;
        for (std::size_t candidate = 1; candidate < candidates.size(); ++candidate) if (total[candidate] < total[best]) best = candidate;
        return best != 0 && total[best] + static_cast<I>(kMcTrials) <= total[0] ? candidates[best].start : baseline->first;
#endif
    }
    static void printPlacement(I digs, I start) { std::cout << digs << ' ' << start << '\n' << std::flush; }
    void appendPipe(int length, I start, int cohort) {
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, cohort});
        activeByEnd.emplace(start + length, pid);
        fenwickAdd(pid, 1); ++activeCount; ++occurrences[static_cast<std::size_t>(length)];
        recordLength(length); recordObservation(Observation{1, length}); recordEvent(length);
    }
public:
    void place(int length) {
        lifetime.advance();
        lifetime.setBirthContext(previousWasDeletion);
        previousWasDeletion = false;
        if (runLength != length) {
            if (runCount > 0) {
                completedRuns.emplace_back(runLength, runCount);
                if (completedRuns.size() > 8) completedRuns.pop_front();
                const std::size_t total = runDeleted[0] + runDeleted[1];
                const std::size_t dominant = std::max(runDeleted[0], runDeleted[1]);
                if (total >= 8 && dominant * 100 >= total * 85) {
                    const int absoluteParity = runDeleted[0] > runDeleted[1] ? 0 : 1;
                    previousRelativeParity = lastRelativeParity;
                    lastRelativeParity = absoluteParity ^ (runFirstPid & 1);
                } else { previousRelativeParity = -1; lastRelativeParity = -1; }
            }
            runLength = length; runCount = 0;
            runFirstPid = static_cast<int>(pipes.size()); runDeleted = {};
            slabActive = false; beginSlab(length);
        }
        ++runCount;
        const int cohort = static_cast<int>(occurrences[static_cast<std::size_t>(length)] % 2);
        if (activeCount > kMcMaxActive) lifoDisabled = true;
        const bool stackLane = length > 4 && lifoLane(length);
        if (slabActive && slabUsed < slabExpected) {
            const int pid = static_cast<int>(pipes.size());
            const bool predictedDeleted = (pid & 1) == slabDeleteParity;
            I start = -1;
            bool tailPlacement = true;
            if (!predictedDeleted && slabGapRemaining > 0) {
                auto reusable = bestBefore(length, false, cohort, slabBase);
                if (reusable != gaps.end()) {
                    start = consume(reusable, length, false); --slabGapRemaining; tailPlacement = false;
                }
            }
            if (tailPlacement) {
                if (predictedDeleted) start = slabBase + static_cast<I>(slabDeletedUsed++) * length;
                else start = slabBase + static_cast<I>(slabDeleteCount + slabSurvivorUsed++) * length;
            }
            I digs = 0;
            if (tailPlacement && !slabExpanded) {
                const I missing = slabEnd - trench;
                digs = missing > 0 ? (missing + kDig - 1) / kDig : 0;
                trench += digs * kDig; slabExpanded = true;
                const I occupiedEnd = slabBase + static_cast<I>(slabTailCount) * length;
                addGap(occupiedEnd, trench, -1);
            }
            printPlacement(digs, start); appendPipe(length, start, cohort);
            if (++slabUsed >= slabExpected) slabActive = false;
            return;
        }
        if (smoothTrend(history, length)) smoothSeen = true;
        const bool same = sameRun(history, length);
        const bool geometric = !smoothSeen && same;
        const bool reverse = smoothSeen && same && alternating;
        const bool additive = additiveTrend(length);
        bool high = stackLane || ((geometric || reverse)
            ? (reverse ? cohort == 0 : (pipes.size() & 1U) == 0U)
            : (alternating ? (static_cast<int>(pipes.size()) & 1) != deletedParity
                : (parityMode ? cohort == 0 : length <= 4 || same)));
        I start = -1;
        const int nextClass = earlyGeometric(length);
        auto gap = bestGap(length, high, cohort);
        bool capacityChoice = false;
        if (nextClass > length && (static_cast<int>(pipes.size()) & 1) != deletedParity) {
            const auto projected = counterfactualGap(length, nextClass, high, cohort, gap);
            if (projected.first != gaps.end()) { gap = projected.first; high = projected.second; capacityChoice = true; }
        }
        if (gap != gaps.end()) {
            if (additive) high = additiveSide(length, gap->first, high);
            else if (geometric) high = geometricSide(history, length, gap->first, gap->second, high);
            if (stackLane) high = true;
            const I selected = additive || capacityChoice ? gap->first : chooseRollout(length, high, cohort, gap);
            if (selected >= 0) gap = gaps.find(selected);
            start = consume(gap, length, high);
        }
        I digs = 0;
        if (start < 0) {
            auto tail = tailGap();
            int tailCohort = parityMode ? cohort : -1;
            bool preserve = false;
            if (parityMode && tail != gaps.end()) {
                tailCohort = owners.at(tail->first);
                preserve = tailCohort >= 0 && tailCohort != cohort;
                if (preserve) tailCohort = cohort;
            }
            const I tailStart = tail == gaps.end() || preserve ? trench : tail->first;
            const I deficit = std::max<I>(0, length - (trench - tailStart));
            digs = (deficit + kDig - 1) / kDig;
            const I newLength = trench + digs * kDig;
            const bool offset = digs > 0 && activeCount > 4096 && !preserve &&
                newLength - (tailStart + length) > 0 && lifoConfidence() && youngTailNeighbor(tailStart) && !unitDominant();
            if (tail != gaps.end() && !preserve) eraseGap(tail);
            trench = newLength;
            if ((parityMode && high && !preserve) || offset) {
                start = trench - length; addGap(tailStart, start, tailCohort);
            } else {
                start = tailStart; addGap(start + length, trench, tailCohort);
            }
        }
        printPlacement(digs, start); appendPipe(length, start, cohort);
    }
    void remove(I pid) {
        if (pid <= 0 || static_cast<U>(pid) >= static_cast<U>(pipes.size()) || !pipes[static_cast<std::size_t>(pid)].active) {
            std::cout << 0 << '\n' << std::flush; return;
        }
        const auto index = static_cast<std::size_t>(pid);
        lifetime.advance();
        const int rank = rankNewest(static_cast<int>(pid));
        const Pipe pipe = pipes[index];
        lifetime.observeDeletion(index); previousWasDeletion = true;
        activeByEnd.erase(pipe.start + pipe.length);
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false; fenwickAdd(static_cast<int>(pid), -1); --activeCount;
        addGap(pipe.start, pipe.start + pipe.length, pipe.cohort);
        deletionPattern(static_cast<int>(pid), pipe.length); recordEvent(-1);
        if (static_cast<int>(pid) >= runFirstPid) ++runDeleted[static_cast<std::size_t>(pid & 1)];
        auto& counts = removed[static_cast<std::size_t>(pipe.length)];
        ++counts[static_cast<std::size_t>(pipe.cohort)];
        const I total = counts[0] + counts[1];
        if (total >= 8 && std::max(counts[0], counts[1]) * 100 >= total * 85 && steadyTrend(history)) parityMode = true;
        recordObservation(Observation{-1, rank});
    }
    void diagnostics() const {
        std::cerr << "lifetime_context_supported_queries=" << lifetime.supportedQueries()
                  << " context_compared_decisions=" << contextCompared
                  << " context_changed_selections=" << contextChanged
                  << " model_rebuilds=" << modelRebuilds
                  << " mc_decisions=" << mcDecisions
                  << " mc_rollouts=" << mcRollouts << '\n';
    }
};
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    Allocator allocator;
    I command;
    while (std::cin >> command) {
        if (command == 0) { allocator.diagnostics(); return 0; }
        if (command > 0) allocator.place(static_cast<int>(command));
        else allocator.remove(-command);
    }
    return 0;
}
