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
#include <cmath>
namespace {
using Coordinate = std::int64_t;
using SizeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr bool kUseExposureEdge = true;
constexpr bool kUseInventoryDual = true;
constexpr int kDistinctCandidateSizes = 8;
constexpr int kMaximumCandidates = 12;
constexpr int kPackingLimit = 40 * 40;
constexpr int kPriceIterations = 6;
constexpr Coordinate kPriceScale = 65536;
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    bool active = false;
    std::size_t leftPid = 0;
    std::size_t rightPid = 0;
};
struct Gap {
    Coordinate end = 0;
    std::uint64_t freeSince = 0;
    std::size_t leftPid = 0;
    std::size_t rightPid = 0;
};
struct Candidate {
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    bool tail = false;
};
struct ReleaseExposure {
    double exposure = 0.0;
    double releases = 0.0;
    std::uint64_t liveCount = 0;
    std::uint64_t lastTick = 0;
};
class Allocator {
public:
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    std::uint64_t sectionTieChecks = 0;
    std::uint64_t sectionTieChanges = 0;
    double sectionTiePredictedSavings = 0.0;
    void place(int length) {
        ++tick_;
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        const bool firstObservation =
            !everObserved_[static_cast<std::size_t>(length)];
        everObserved_[static_cast<std::size_t>(length)] = true;
        observeLength(length);
        refreshModel(newlyObservedLength);
        Coordinate digs = 0;
        Coordinate chosenStart = 0;
        // Growth is permitted only after the complete fitting-gap query.
        const auto firstFit = bySize_.lower_bound({length, {0, 0}});
        if (firstFit == bySize_.end()) {
            ++expansionGateOpportunities;
            Coordinate start = trenchLength_;
            std::uint64_t freeSince = tick_;
            std::size_t leftPid = pipes_[0].leftPid;
            const auto tail = tailGap();
            if (tail != gaps_.end()) {
                start = tail->first;
                freeSince = tail->second.freeSince;
                leftPid = tail->second.leftPid;
                eraseGap(tail);
            }
            const Coordinate available = trenchLength_ - start;
            const Coordinate deficit =
                std::max<Coordinate>(0, length - available);
            digs =
                (deficit + kSectionLength - 1) / kSectionLength;
            trenchLength_ += digs * kSectionLength;
            insertGap(
                start, trenchLength_, freeSince, leftPid, 0);
            chosenStart = start;
        } else {
            chosenStart = chooseGap(length, firstObservation);
        }
        const auto selected = gaps_.find(chosenStart);
        const Gap gap = selected->second;
        const bool highEnd =
            chooseHighEnd(chosenStart, gap, length);
        const Coordinate allocationStart =
            highEnd ? gap.end - length : chosenStart;
        eraseGap(selected);
        const std::size_t pid = pipes_.size();
        pipes_.push_back(Pipe{
            allocationStart, length, true,
            gap.leftPid, gap.rightPid});
        pipes_[gap.leftPid].rightPid = pid;
        pipes_[gap.rightPid].leftPid = pid;
        observeBirth(length);
        if (highEnd) {
            insertGap(
                chosenStart, allocationStart, gap.freeSince,
                gap.leftPid, pid);
        } else {
            insertGap(
                allocationStart + length, gap.end, gap.freeSince,
                pid, gap.rightPid);
        }
        std::cout << digs << ' ' << allocationStart
                  << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const std::size_t pid = static_cast<std::size_t>(pidValue);
        if (!pipes_[pid].active) {
            printInvalidPid();
            return;
        }
        ++tick_;
        const Pipe pipe = pipes_[pid];
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
        pipes_[pipe.leftPid].rightPid = pipe.rightPid;
        pipes_[pipe.rightPid].leftPid = pipe.leftPid;
        pipes_[pid].active = false;
        observeRelease(pipe.length);
        insertGap(
            start, end, tick_, pipe.leftPid, pipe.rightPid);
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    using Prices = std::array<Coordinate, 41>;
    GapMap gaps_;
    std::set<SizeKey> bySize_;
    std::vector<Pipe> pipes_{Pipe{}};
    Coordinate trenchLength_ = 0;
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<bool, 41> everObserved_{};
    std::array<double, 41> requestPrefix_{};
    std::array<ReleaseExposure, 41> releaseExposure_{};
    // Exact inventory for capacities up to the periodicity threshold.
    std::array<Coordinate, kPackingLimit + 1> capacityCount_{};
    // Larger capacities are summarized by every possible optimal period.
    std::array<std::array<Coordinate, 40>, 41>
        largeRemainderCount_{};
    Coordinate largeVolume_ = 0;
    Coordinate freeVolume_ = 0;
    Prices prices_{};
    std::array<Coordinate, kPackingLimit + 1> packingValue_{};
    std::array<std::uint8_t, kPackingLimit + 1> packingChoice_{};
    int packingBuilt_ = 0;
    int bestPeriod_ = 1;
    bool havePrices_ = false;
    std::uint64_t priceTick_ = 0;
    std::uint64_t priceInterval_ = 32;
    static bool candidateLess(
        const Candidate& a, const Candidate& b) {
        if (a.span != b.span) return a.span < b.span;
        if (a.tail != b.tail) return !a.tail;
        if (a.freeSince != b.freeSince) {
            return a.freeSince < b.freeSince;
        }
        return a.start < b.start;
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_
            ? last : gaps_.end();
    }
    void changeInventory(Coordinate capacity, int delta) {
        freeVolume_ += capacity * delta;
        if (capacity <= kPackingLimit) {
            capacityCount_[static_cast<std::size_t>(capacity)] +=
                delta;
            return;
        }
        largeVolume_ += capacity * delta;
        for (int period = 1; period <= 40; ++period) {
            const std::size_t remainder =
                static_cast<std::size_t>(capacity % period);
            largeRemainderCount_[
                static_cast<std::size_t>(period)][remainder] +=
                delta;
        }
    }
    void insertGap(
        Coordinate start, Coordinate end,
        std::uint64_t freeSince,
        std::size_t leftPid, std::size_t rightPid) {
        if (start >= end) return;
        gaps_.emplace(
            start, Gap{end, freeSince, leftPid, rightPid});
        bySize_.insert({end - start, {freeSince, start}});
        changeInventory(end - start, 1);
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const Coordinate span = gap.end - start;
        changeInventory(span, -1);
        bySize_.erase({span, {gap.freeSince, start}});
        gaps_.erase(position);
    }
    void synchronizeExposure(std::size_t index) {
        ReleaseExposure& state = releaseExposure_[index];
        const std::uint64_t elapsed = tick_ - state.lastTick;
        if (elapsed == 0) return;
        constexpr double memory =
            static_cast<double>(kSlowWindow);
        const double exponent =
            -static_cast<double>(elapsed) / memory;
        const double retained = std::exp(exponent);
        const double integratedTime =
            -memory * std::expm1(exponent);
        state.exposure =
            retained * state.exposure +
            static_cast<double>(state.liveCount) * integratedTime;
        state.releases *= retained;
        state.lastTick = tick_;
    }
    void observeBirth(int length) {
        const std::size_t index =
            static_cast<std::size_t>(length);
        synchronizeExposure(0);
        synchronizeExposure(index);
        ++releaseExposure_[0].liveCount;
        ++releaseExposure_[index].liveCount;
    }
    void observeRelease(int length) {
        const std::size_t index =
            static_cast<std::size_t>(length);
        synchronizeExposure(0);
        synchronizeExposure(index);
        --releaseExposure_[0].liveCount;
        --releaseExposure_[index].liveCount;
        releaseExposure_[0].releases += 1.0;
        releaseExposure_[index].releases += 1.0;
    }
    bool chooseHighEnd(
        Coordinate start, const Gap& gap, int length) {
        if (!kUseExposureEdge ||
            gap.end - start == length ||
            gap.leftPid == 0 || gap.rightPid == 0) {
            return false;
        }
        const int leftLength = pipes_[gap.leftPid].length;
        const int rightLength = pipes_[gap.rightPid].length;
        if (leftLength == rightLength) return false;
        synchronizeExposure(0);
        const ReleaseExposure& total = releaseExposure_[0];
        if (total.releases < 8.0 || total.exposure <= 0.0) {
            return false;
        }
        const std::size_t leftIndex =
            static_cast<std::size_t>(leftLength);
        const std::size_t rightIndex =
            static_cast<std::size_t>(rightLength);
        synchronizeExposure(leftIndex);
        synchronizeExposure(rightIndex);
        constexpr double priorReleases = 2.0;
        constexpr double separation = 2.0;
        const double globalRate =
            total.releases / total.exposure;
        const double priorExposure =
            priorReleases / globalRate;
        const ReleaseExposure& left =
            releaseExposure_[leftIndex];
        const ReleaseExposure& right =
            releaseExposure_[rightIndex];
        const double leftShape =
            left.releases + priorReleases;
        const double rightShape =
            right.releases + priorReleases;
        const double leftLower =
            std::max(
                0.0,
                leftShape - separation * std::sqrt(leftShape)) /
            (left.exposure + priorExposure);
        const double rightUpper =
            (rightShape + separation * std::sqrt(rightShape)) /
            (right.exposure + priorExposure);
        return leftLower > rightUpper;
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
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) {
            return;
        }
        haveModel_ = true;
        modelTick_ = tick_;
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        requestPrefix_[0] = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index =
                static_cast<std::size_t>(length);
            const double probability =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            requestPrefix_[index] =
                requestPrefix_[index - 1] + probability;
        }
        requestPrefix_[40] = 1.0;
    }
    void ensurePacking(int limit) {
        for (int capacity = packingBuilt_ + 1;
             capacity <= limit; ++capacity) {
            Coordinate best =
                packingValue_[static_cast<std::size_t>(
                    capacity - 1)];
            int choice = 0;
            const int largestLength = std::min(40, capacity);
            for (int length = 1;
                 length <= largestLength; ++length) {
                const Coordinate value =
                    packingValue_[static_cast<std::size_t>(
                        capacity - length)] +
                    prices_[static_cast<std::size_t>(length)];
                if (value > best) {
                    best = value;
                    choice = length;
                }
            }
            packingValue_[static_cast<std::size_t>(capacity)] =
                best;
            packingChoice_[static_cast<std::size_t>(capacity)] =
                static_cast<std::uint8_t>(choice);
        }
        packingBuilt_ = std::max(packingBuilt_, limit);
    }
    void setPrices(const Prices& prices, int limit) {
        prices_ = prices;
        bestPeriod_ = 1;
        for (int length = 2; length <= 40; ++length) {
            if (prices_[static_cast<std::size_t>(length)] *
                    bestPeriod_ >
                prices_[static_cast<std::size_t>(bestPeriod_)] *
                    length) {
                bestPeriod_ = length;
            }
        }
        packingBuilt_ = 0;
        packingValue_[0] = 0;
        packingChoice_[0] = 0;
        ensurePacking(limit);
    }
    // If b has maximum price per unit length, an optimal packing
    // can contain fewer than b non-b items. Any b such items have
    // a nonempty subset whose total length is divisible by b;
    // replacing that subset with b-items cannot reduce value.
    // Consequently V(c) = V(c-b) + price[b] for c > 1600.
    int reduceCapacity(
        Coordinate capacity, Coordinate& periods) const {
        periods = 0;
        if (capacity <= kPackingLimit) {
            return static_cast<int>(capacity);
        }
        periods =
            (capacity - kPackingLimit - 1) / bestPeriod_ + 1;
        return static_cast<int>(
            capacity - periods * bestPeriod_);
    }
    Coordinate marginalLoss(
        Coordinate capacity, int length) const {
        Coordinate beforePeriods = 0;
        Coordinate afterPeriods = 0;
        const int before =
            reduceCapacity(capacity, beforePeriods);
        const int after =
            reduceCapacity(capacity - length, afterPeriods);
        return
            packingValue_[static_cast<std::size_t>(before)] -
            packingValue_[static_cast<std::size_t>(after)] +
            (beforePeriods - afterPeriods) *
                prices_[static_cast<std::size_t>(bestPeriod_)];
    }
    Coordinate chooseSectionTie(
        int length,
        const std::array<Candidate, kMaximumCandidates>& candidates,
        int candidateCount,
        const std::array<Coordinate, kMaximumCandidates>& losses,
        int originalIndex) {
        const std::size_t originalSlot =
            static_cast<std::size_t>(originalIndex);
        const Coordinate originalStart =
            candidates[originalSlot].start;
        const auto largest = bySize_.rbegin();
        const auto runnerUp = std::next(largest);
        const Coordinate secondLargestSpan =
            runnerUp == bySize_.rend() ? 0 : runnerUp->first;
        const auto tail = tailGap();
        const Coordinate tailCapacity =
            tail == gaps_.end()
                ? 0 : tail->second.end - tail->first;
        const auto profile = [&](const Candidate& candidate) {
            const Coordinate largestOther =
                candidate.start == largest->second.second
                    ? secondLargestSpan : largest->first;
            const Coordinate maximumAfter =
                std::max(largestOther, candidate.span - length);
            const Coordinate tailAfter =
                candidate.tail
                    ? candidate.span - length : tailCapacity;
            // For the next insertion without an intervening deletion,
            // these are the largest lengths needing zero or one section.
            // Every remaining request length needs exactly two sections.
            return std::array<Coordinate, 2>{
                std::min<Coordinate>(40, maximumAfter),
                std::min<Coordinate>(
                    40, std::max(
                        maximumAfter, tailAfter + kSectionLength))};
        };
        const auto originalProfile =
            profile(candidates[originalSlot]);
        if (originalProfile[0] == 40) return originalStart;
        ++sectionTieChecks;

        // Integer weights reproduce the observed fast/slow mixture 3:1.
        // Excluding smoothing requires actual evidence of a strict benefit.
        const std::uint64_t fastCount =
            static_cast<std::uint64_t>(
                std::min(kFastWindow, recentLengths_.size()));
        const std::uint64_t slowCount =
            static_cast<std::uint64_t>(recentLengths_.size());
        std::array<std::uint64_t, 41> observedPrefix{};
        for (int request = 1; request <= 40; ++request) {
            const std::size_t index =
                static_cast<std::size_t>(request);
            const std::uint64_t mass =
                3 * slowCount * static_cast<std::uint64_t>(
                    fastFrequency_[index]) +
                fastCount * static_cast<std::uint64_t>(
                    slowFrequency_[index]);
            observedPrefix[index] =
                observedPrefix[index - 1] + mass;
        }
        const auto coverage =
            [&](const std::array<Coordinate, 2>& limits) {
                return observedPrefix[static_cast<std::size_t>(
                           limits[0])] +
                    observedPrefix[static_cast<std::size_t>(
                        limits[1])];
            };
        const std::uint64_t originalCoverage =
            coverage(originalProfile);
        std::uint64_t bestCoverage = originalCoverage;
        int chosenIndex = originalIndex;
        for (int index = 0; index < candidateCount; ++index) {
            const std::size_t slot =
                static_cast<std::size_t>(index);
            if (losses[slot] != losses[originalSlot]) continue;
            const auto limits = profile(candidates[slot]);
            // Require no additional sections for any possible length,
            // including lengths absent from the observed histogram.
            if (limits[0] < originalProfile[0] ||
                limits[1] < originalProfile[1]) {
                continue;
            }
            const std::uint64_t candidateCoverage = coverage(limits);
            if (candidateCoverage > bestCoverage) {
                bestCoverage = candidateCoverage;
                chosenIndex = index;
            }
        }
        if (chosenIndex != originalIndex) {
            ++sectionTieChanges;
            sectionTiePredictedSavings +=
                static_cast<double>(bestCoverage - originalCoverage) /
                (4.0 * static_cast<double>(fastCount) *
                 static_cast<double>(slowCount));
        }
        return candidates[static_cast<std::size_t>(chosenIndex)].start;
    }
    double inventoryPatternSupply(
        int limit, std::array<double, 41>& supply) const {
        std::array<double, kPackingLimit + 1> mass{};
        supply.fill(0.0);
        for (int capacity = 1; capacity <= limit; ++capacity) {
            mass[static_cast<std::size_t>(capacity)] =
                static_cast<double>(
                    capacityCount_[
                        static_cast<std::size_t>(capacity)]);
        }
        double value = 0.0;
        if (largeVolume_ != 0) {
            double baseVolume = 0.0;
            for (int remainder = 0;
                 remainder < bestPeriod_; ++remainder) {
                const Coordinate count =
                    largeRemainderCount_[
                        static_cast<std::size_t>(bestPeriod_)]
                        [static_cast<std::size_t>(remainder)];
                if (count == 0) continue;
                const int base =
                    kPackingLimit -
                    (kPackingLimit - remainder) % bestPeriod_;
                const double countAsDouble =
                    static_cast<double>(count);
                mass[static_cast<std::size_t>(base)] +=
                    countAsDouble;
                baseVolume += countAsDouble * base;
            }
            const double periods =
                (static_cast<double>(largeVolume_) -
                 baseVolume) / bestPeriod_;
            supply[static_cast<std::size_t>(bestPeriod_)] +=
                periods;
            value += periods *
                static_cast<double>(
                    prices_[
                        static_cast<std::size_t>(bestPeriod_)]);
        }
        for (int capacity = 1; capacity <= limit; ++capacity) {
            value +=
                mass[static_cast<std::size_t>(capacity)] *
                static_cast<double>(
                    packingValue_[
                        static_cast<std::size_t>(capacity)]);
        }
        // Backward propagation recovers the aggregate pattern counts
        // without storing one 40-element pattern for every capacity.
        for (int capacity = limit; capacity > 0; --capacity) {
            const double count =
                mass[static_cast<std::size_t>(capacity)];
            if (count == 0.0) continue;
            const int length =
                packingChoice_[
                    static_cast<std::size_t>(capacity)];
            if (length == 0) {
                mass[static_cast<std::size_t>(capacity - 1)] +=
                    count;
            } else {
                supply[static_cast<std::size_t>(length)] +=
                    count;
                mass[static_cast<std::size_t>(
                    capacity - length)] += count;
            }
        }
        return value;
    }
    void refreshPackingPrices(bool firstObservation) {
        if (havePrices_ && !firstObservation &&
            tick_ - priceTick_ < priceInterval_) {
            return;
        }
        const int limit = static_cast<int>(
            std::min<Coordinate>(
                kPackingLimit, bySize_.rbegin()->first));
        std::array<double, 41> probability{};
        std::array<double, 41> quota{};
        std::array<double, 41> normalized{};
        double meanLength = 0.0;
        double largestProbability = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index =
                static_cast<std::size_t>(length);
            probability[index] =
                requestPrefix_[index] -
                requestPrefix_[index - 1];
            meanLength += probability[index] * length;
            largestProbability =
                std::max(
                    largestProbability, probability[index]);
        }
        // Expected request mix whose total volume equals existing
        // free volume. These are model quotas, never reservations.
        const double requestMass =
            static_cast<double>(freeVolume_) / meanLength;
        Prices initialPrices{};
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index =
                static_cast<std::size_t>(length);
            quota[index] = requestMass * probability[index];
            normalized[index] =
                probability[index] / largestProbability;
            initialPrices[index] =
                static_cast<Coordinate>(std::llround(
                    normalized[index] * length *
                    static_cast<double>(kPriceScale)));
        }
        if constexpr (!kUseInventoryDual) {
            setPrices(initialPrices, limit);
        } else {
            // Packing LP dual:
            // min sum_g V_gap(price)
            //     + sum_k quota[k] * (k - price[k]),
            // with 0 <= price[k] <= k.
            // Zero prices provide a valid initial upper bound.
            Prices bestPrices{};
            double bestObjective =
                static_cast<double>(freeVolume_) *
                static_cast<double>(kPriceScale);
            for (int iteration = 0;
                 iteration < kPriceIterations; ++iteration) {
                Prices trialPrices{};
                for (int length = 1; length <= 40; ++length) {
                    const std::size_t index =
                        static_cast<std::size_t>(length);
                    trialPrices[index] =
                        static_cast<Coordinate>(std::llround(
                            normalized[index] * length *
                            static_cast<double>(kPriceScale)));
                }
                setPrices(trialPrices, limit);
                std::array<double, 41> supply{};
                double objective =
                    inventoryPatternSupply(limit, supply);
                for (int length = 1; length <= 40; ++length) {
                    const std::size_t index =
                        static_cast<std::size_t>(length);
                    objective += quota[index] *
                        static_cast<double>(
                            length * kPriceScale -
                            trialPrices[index]);
                }
                if (objective < bestObjective) {
                    bestObjective = objective;
                    bestPrices = trialPrices;
                }
                const double step =
                    0.5 / std::sqrt(
                        static_cast<double>(iteration + 1));
                for (int length = 1; length <= 40; ++length) {
                    const std::size_t index =
                        static_cast<std::size_t>(length);
                    const double direction =
                        (quota[index] - supply[index]) /
                        (quota[index] + 1.0);
                    normalized[index] =
                        std::clamp(
                            normalized[index] + step * direction,
                            0.0, 1.0);
                }
            }
            setPrices(bestPrices, limit);
        }
        havePrices_ = true;
        priceTick_ = tick_;
        // Keep amortized model work bounded as the DP grows.
        priceInterval_ = std::max<std::uint64_t>(
            32,
            (static_cast<std::uint64_t>(
                (kPriceIterations + 1) * limit) + 7) / 8);
    }
    Coordinate chooseGap(int length, bool firstObservation) {
        std::array<Candidate, kMaximumCandidates> candidates{};
        int candidateCount = 0;
        const auto addCandidate = [&](Coordinate start) {
            for (int i = 0; i < candidateCount; ++i) {
                if (candidates[static_cast<std::size_t>(i)].start ==
                    start) {
                    return;
                }
            }
            if (candidateCount == kMaximumCandidates) return;
            const auto found = gaps_.find(start);
            if (found == gaps_.end()) return;
            const Coordinate span = found->second.end - start;
            if (span < length) return;
            candidates[static_cast<std::size_t>(candidateCount++)] =
                Candidate{
                    start, span, found->second.freeSince,
                    found->second.end == trenchLength_};
        };
        const auto addSizeRepresentatives =
            [&](std::set<SizeKey>::const_iterator position) {
                if (position == bySize_.end()) return;
                addCandidate(position->second.second);
                const auto gap =
                    gaps_.find(position->second.second);
                if (gap->second.end == trenchLength_) {
                    const auto next = std::next(position);
                    if (next != bySize_.end() &&
                        next->first == position->first) {
                        addCandidate(next->second.second);
                    }
                }
            };
        auto current = bySize_.lower_bound({length, {0, 0}});
        const Coordinate fallback = current->second.second;
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const Coordinate span = current->first;
            addSizeRepresentatives(current);
            current = bySize_.upper_bound({
                span,
                {std::numeric_limits<std::uint64_t>::max(),
                 std::numeric_limits<Coordinate>::max()}});
        }
        const Coordinate largestSpan = bySize_.rbegin()->first;
        addSizeRepresentatives(
            bySize_.lower_bound({largestSpan, {0, 0}}));
        const auto tail = tailGap();
        if (tail != gaps_.end() &&
            tail->second.end - tail->first >= length) {
            addCandidate(tail->first);
        }
        if (candidateCount == 0) return fallback;
        std::sort(
            candidates.begin(),
            candidates.begin() + candidateCount,
            candidateLess);
        if (candidateCount == 1) return candidates[0].start;
        refreshPackingPrices(firstObservation);
        // New gaps may have appeared since the last price update.
        // Extend the exact table while retaining the cached prices.
        ensurePacking(static_cast<int>(
            std::min<Coordinate>(
                kPackingLimit, bySize_.rbegin()->first)));
        std::array<Coordinate, kMaximumCandidates> losses{};
        int bestIndex = 0;
        for (int index = 0; index < candidateCount; ++index) {
            const std::size_t slot =
                static_cast<std::size_t>(index);
            losses[slot] =
                marginalLoss(candidates[slot].span, length);
            if (losses[slot] <
                losses[static_cast<std::size_t>(bestIndex)]) {
                bestIndex = index;
            }
        }
        return chooseSectionTie(
            length, candidates, candidateCount, losses, bestIndex);
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
                      << allocator.unitProfileSuppressedExpansions
                      << " section_tie_checks=" << allocator.sectionTieChecks
                      << " section_tie_changes=" << allocator.sectionTieChanges
                      << " section_tie_predicted_sections_saved="
                      << allocator.sectionTiePredictedSavings << '\n';
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