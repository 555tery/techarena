# System Instructions

You are an expert programming assistant analyzing an individual program. Create a standalone summary focusing on implementation details and evaluation feedback. Consider how this specific program performs and what implementation choices were made.

# Previous Messages

[]

# User Request

# Program to Analyze
# Program to Analyze

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
#include <cmath>
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
constexpr bool kAgeConditionalReleaseRisk = true;
constexpr bool kHarmonicFitInventory = true;
constexpr bool kReusableSlotInventory = true;
constexpr bool kFiniteHorizonSlotShortfall = true;
constexpr bool kPersistentMarkovSlotDemand = true;
constexpr int kSlotDemandHorizon = 12;
constexpr double kFitInventoryWeight = 0.35;
constexpr int kAgeBandCount = 4;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes live survivors as well as completed lifetimes.
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
    std::uint64_t bornTick = 0;
    std::uint64_t ageUnit = 1;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    unsigned char ageBand = 0;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
    std::uint64_t freeSince = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
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
        // An existing tail may support two fronts without extra excavation.
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
            rebuildFitInventory(length);
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            // Growth is possible only after the global fitting-gap check.
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
        pipe.bornTick = tick_;
        pipe.ageUnit = std::max<std::uint64_t>(
            1, static_cast<std::uint64_t>(
                std::min(lifetimeHorizon_, static_cast<double>(tick_))));
        pipe.active = true;
        pipes_.push_back(pipe);
        ageRates_[static_cast<std::size_t>(group)][0].change(
            tick_, 1, false);
        ageEvents_.insert({nextAgeCheckpoint(pipe), pid});
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(
            gapStart, pipe.start, gap.left, pid, gap.freeSince);
        insertGap(
            pipe.start + length, gap.end, pid, gap.right, gap.freeSince);
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
        ageRates_[static_cast<std::size_t>(pipe.group)]
                 [static_cast<std::size_t>(pipe.ageBand)].change(
            tick_, -1, true);
        if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
            ageEvents_.erase({nextAgeCheckpoint(pipe), pid});
        }
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
        insertGap(start, end, pipe.previous, pipe.next, tick_);
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
    std::set<GapAgeKey> byAge_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    // Bucket 40 includes every gap whose length is at least 40.
    std::array<std::uint64_t, 41> gapSpanHistogram_{};
    std::array<double, 41> requestProbability_{};
    std::array<double, 41> fitInventoryPrefix_{};
    // Exact repeated-request capacity, including gaps longer than 40.
    std::array<std::uint64_t, 41> reusableSlotInventory_{};
    std::array<std::array<double, kSlotDemandHorizon + 1>, 41>
        slotDemandTail_{};
    std::array<
        std::array<std::array<double, kSlotDemandHorizon + 1>, 2>, 41>
        markovSlotDemandTail_{};
    std::uint64_t fastRepeatTransitions_ = 0;
    std::uint64_t slowRepeatTransitions_ = 0;
    std::array<int, 41> slotRequestRemainder_{};
    std::array<double, 41> slotResiduePenalty_{};
    mutable Coordinate cachedSlotSpan_ = -1;
    mutable double cachedSlotCost_ = 0.0;
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
    std::array<std::array<Rate, kAgeBandCount>, 3> ageRates_{};
    std::array<std::array<double, kAgeBandCount>, 3> ageMultiplier_{};
    std::set<std::pair<std::uint64_t, int>> ageEvents_;
    double lifetimeHorizon_ = 1.0;
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
    static std::size_t fitBucket(Coordinate length) {
        return static_cast<std::size_t>(
            std::clamp<Coordinate>(length, 0, 40));
    }
    static std::uint64_t nextAgeCheckpoint(const Pipe& pipe) {
        return pipe.bornTick +
            pipe.ageUnit * (std::uint64_t{1} << pipe.ageBand);
    }
    void rebuildFitInventory(int requestLength) {
        // Retain the original score for the same-parent ablation.
        std::array<double, 41> marginal{};
        std::uint64_t fitting = 0;
        for (int length = 40; length >= 1; --length) {
            const std::size_t index = static_cast<std::size_t>(length);
            fitting += gapSpanHistogram_[index];
            if (fitting != 0) {
                marginal[index] =
                    static_cast<double>(length) *
                    requestProbability_[index] /
                    static_cast<double>(fitting);
            }
        }
        fitInventoryPrefix_[0] = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            fitInventoryPrefix_[index] =
                fitInventoryPrefix_[index - 1] + marginal[index];
        }
        // Let q = requestLength / s, r = requestLength % s.
        // Every fitting candidate consumes q slots, and consumes one more
        // exactly when span % s < r. The q-slot loss is common under
        // either pricing model; only the optional extra slot is scored.
        for (int size = 1; size <= 40; ++size) {
            const std::size_t index = static_cast<std::size_t>(size);
            const std::uint64_t quotient =
                static_cast<std::uint64_t>(requestLength / size);
            slotRequestRemainder_[index] = requestLength % size;
            const std::uint64_t supply =
                reusableSlotInventory_[index];
            if (slotRequestRemainder_[index] == 0 || supply <= quotient) {
                slotResiduePenalty_[index] = 0.0;
            } else if (kFiniteHorizonSlotShortfall) {
                const std::uint64_t remaining = supply - quotient;
                const auto& demandTail = kPersistentMarkovSlotDemand
                    ? markovSlotDemandTail_[index][
                        requestLength == size ? 1U : 0U]
                    : slotDemandTail_[index];
                slotResiduePenalty_[index] =
                    remaining <=
                        static_cast<std::uint64_t>(kSlotDemandHorizon)
                        ? static_cast<double>(size) *
                            demandTail[
                                static_cast<std::size_t>(remaining)]
                        : 0.0;
            } else {
                slotResiduePenalty_[index] =
                    static_cast<double>(size) *
                    requestProbability_[index] /
                    static_cast<double>(supply - quotient);
            }
        }
        cachedSlotSpan_ = -1;
    }
    double inventoryOpportunityCost(
        Coordinate span, Coordinate remainder) const {
        if (!kReusableSlotInventory) {
            return fitInventoryPrefix_[fitBucket(span)] -
                fitInventoryPrefix_[fitBucket(remainder)];
        }
        if (cachedSlotSpan_ == span) return cachedSlotCost_;
        double cost = 0.0;
        // Size 1 has no residue-dependent term.
        for (int size = 2; size <= 40; ++size) {
            const std::size_t index = static_cast<std::size_t>(size);
            const double penalty = slotResiduePenalty_[index];
            if (penalty != 0.0 &&
                span % size < slotRequestRemainder_[index]) {
                cost += penalty;
            }
        }
        cachedSlotSpan_ = span;
        cachedSlotCost_ = cost;
        return cost;
    }
    void beginCommand() {
        ++tick_;
        // One event per live pipe and at most three age transitions per pipe.
        while (!ageEvents_.empty() &&
               ageEvents_.begin()->first <= tick_) {
            const auto event = *ageEvents_.begin();
            ageEvents_.erase(ageEvents_.begin());
            Pipe& pipe = pipes_[static_cast<std::size_t>(event.second)];
            auto& rates = ageRates_[static_cast<std::size_t>(pipe.group)];
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, -1, false);
            ++pipe.ageBand;
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, 1, false);
            if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
                ageEvents_.insert({
                    nextAgeCheckpoint(pipe), event.second});
            }
        }
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
            for (auto& bands : ageRates_) {
                for (Rate& rate : bands) rate.forget(tick_);
            }
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
        if (kPersistentMarkovSlotDemand &&
            !recentLengths_.empty() &&
            recentLengths_.back() == length) {
            ++fastRepeatTransitions_;
            ++slowRepeatTransitions_;
        }
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            if (kPersistentMarkovSlotDemand &&
                recentLengths_[expired] ==
                    recentLengths_[expired + 1]) {
                --fastRepeatTransitions_;
            }
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            if (kPersistentMarkovSlotDemand &&
                recentLengths_[0] == recentLengths_[1]) {
                --slowRepeatTransitions_;
            }
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
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
    void rebuildAgeRisk(double globalRate) {
        for (std::size_t group = 0; group < ageRates_.size(); ++group) {
            double exposure = 0.0;
            double deaths = 0.0;
            for (const Rate& observation : ageRates_[group]) {
                exposure += observation.exposureAt(tick_);
                deaths += observation.deaths;
            }
            const double pooledRate =
                (deaths + 4.0) / (exposure + 4.0 / globalRate);
            for (int band = 0; band < kAgeBandCount; ++band) {
                const std::size_t index = static_cast<std::size_t>(band);
                const Rate& observation = ageRates_[group][index];
                const double expectedDeaths =
                    observation.exposureAt(tick_) * pooledRate;
                constexpr double priorDeaths = 8.0;
                double multiplier = 1.0;
                if (observation.deaths >= priorDeaths ||
                    expectedDeaths >= priorDeaths) {
                    multiplier =
                        (observation.deaths + priorDeaths) /
                        (expectedDeaths + priorDeaths);
                }
                ageMultiplier_[group][index] = multiplier;
            }
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
        lifetimeHorizon_ = 1.0 / globalRate;
        rebuildAgeRisk(globalRate);
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
        requestProbability_ = probability;
        if (kFiniteHorizonSlotShortfall) {
            double persistence = 0.0;
            if (kPersistentMarkovSlotDemand) {
                const auto estimatePersistence = [](
                    double count, std::uint64_t repeats,
                    const std::array<int, 41>& frequency) {
                    if (count < 2.0) return 0.0;
                    double equalOrderedPairs = 0.0;
                    for (int size = 1; size <= 40; ++size) {
                        const double occurrences =
                            static_cast<double>(
                                frequency[static_cast<std::size_t>(size)]);
                        equalOrderedPairs +=
                            occurrences * (occurrences - 1.0);
                    }
                    const double edges = count - 1.0;
                    // Expected adjacent-repeat probability under a
                    // random permutation of the observed multiset.
                    const double baseline =
                        equalOrderedPairs / (count * edges);
                    if (baseline >= 1.0 - 1e-12) return 0.0;
                    constexpr double independentPriorEdges = 16.0;
                    return std::clamp(
                        (static_cast<double>(repeats) -
                         edges * baseline) /
                            ((edges + independentPriorEdges) *
                             (1.0 - baseline)),
                        0.0, 1.0);
                };
                persistence =
                    0.75 * estimatePersistence(
                        fastCount, fastRepeatTransitions_,
                        fastFrequency_) +
                    0.25 * estimatePersistence(
                        slowCount, slowRepeatTransitions_,
                        slowFrequency_);
            }
            for (int size = 1; size <= 40; ++size) {
                const std::size_t index = static_cast<std::size_t>(size);
                auto& tail = slotDemandTail_[index];
                const double p = requestProbability_[index];
                // The existing uniform prior guarantees 0 < p < 1.
                // Build P(K >= n) downward from P(K = horizon),
                // avoiding subtraction of nearly equal probabilities.
                double mass = std::pow(p, kSlotDemandHorizon);
                double upper = mass;
                tail[kSlotDemandHorizon] = upper;
                for (int count = kSlotDemandHorizon - 1;
                     count >= 1; --count) {
                    mass *=
                        static_cast<double>(count + 1) * (1.0 - p) /
                        (static_cast<double>(kSlotDemandHorizon - count) *
                         p);
                    upper += mass;
                    tail[static_cast<std::size_t>(count)] =
                        std::clamp(upper, 0.0, 1.0);
                }
                tail[0] = 1.0;
                if (!kPersistentMarkovSlotDemand) continue;
                auto& markovTail = markovSlotDemandTail_[index];
                // Preserve the original numbers when dependence is absent.
                markovTail[0] = tail;
                markovTail[1] = tail;
                if (persistence <= 0.0) continue;
                const std::array<double, 2> nextPresentProbability{
                    (1.0 - persistence) * p,
                    persistence + (1.0 - persistence) * p};
                markovTail = {};
                markovTail[0][0] = 1.0;
                markovTail[1][0] = 1.0;
                // State records whether the preceding request had this size.
                // Recurrence counts occurrences in the next 'step' requests.
                for (int step = 1;
                     step <= kSlotDemandHorizon; ++step) {
                    const auto previous = markovTail;
                    for (int count = 1; count <= step; ++count) {
                        const std::size_t n =
                            static_cast<std::size_t>(count);
                        for (std::size_t state = 0; state < 2; ++state) {
                            const double present =
                                nextPresentProbability[state];
                            markovTail[state][n] = std::clamp(
                                (1.0 - present) * previous[0][n] +
                                    present * previous[1][n - 1],
                                0.0, 1.0);
                        }
                    }
                }
            }
        }
        // Parent renewal potential, with up to four attempts per step.
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
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const double fallback = predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
        if (!kAgeConditionalReleaseRisk) return fallback;
        const auto& multipliers =
            ageMultiplier_[static_cast<std::size_t>(pipe.group)];
        double age = static_cast<double>(tick_ - pipe.bornTick);
        double remaining = lifetimeHorizon_;
        double weightedDuration = 0.0;
        bool adjusted = false;
        for (int band = static_cast<int>(pipe.ageBand);
             band < kAgeBandCount && remaining > 0.0; ++band) {
            double duration = remaining;
            if (band + 1 < kAgeBandCount) {
                const double boundary =
                    static_cast<double>(pipe.ageUnit) *
                    static_cast<double>(std::uint64_t{1} << band);
                duration = std::min(
                    remaining, std::max(0.0, boundary - age));
            }
            const double multiplier =
                multipliers[static_cast<std::size_t>(band)];
            weightedDuration += duration * multiplier;
            if (duration > 0.0 && multiplier != 1.0) adjusted = true;
            age += duration;
            remaining -= duration;
        }
        if (!adjusted) return fallback;
        const double logSurvival =
            std::log1p(-fallback) *
            (weightedDuration / lifetimeHorizon_);
        return std::clamp(-std::expm1(logSurvival), 0.0, 1.0);
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
        if (gap.end == trenchLength_) {
            // Preserve the expandable tail whenever an interior gap fits.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        Coordinate leftLength = 0;
        if (gap.left != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.left)];
            leftLength = neighbor.length;
            const auto next = gaps_.lower_bound(neighbor.start);
            if (next != gaps_.begin()) {
                const auto outside = std::prev(next);
                if (kCoalescingReleaseGeometry &&
                    outside->second.end == neighbor.start) {
                    leftLength += outside->second.end - outside->first;
                }
            }
        }
        Coordinate rightLength = 0;
        if (gap.right != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.right)];
            rightLength = neighbor.length;
            const auto outside =
                gaps_.find(neighbor.start + neighbor.length);
            if (kCoalescingReleaseGeometry && outside != gaps_.end()) {
                rightLength += outside->second.end - outside->first;
            }
        }
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
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
        // Loss of repeated-request capacity, with its
        // candidate-independent component omitted under either model.
        const double inventoryCost = kHarmonicFitInventory
            ? kFitInventoryWeight * (1.0 - newDeletion) *
                inventoryOpportunityCost(span, remainder)
            : 0.0;
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
                futureWeight * futureCost +
                inventoryCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
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
            const bool sameSpanTieBetter =
                (kOldestGapTieBreak && gap.freeSince != best.freeSince)
                    ? gap.freeSince < best.freeSince
                    : position < best.start;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && sameSpanTieBetter)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.freeSince = gap.freeSince;
                best.score = score;
            }
        }
    }
    void considerOldest(
        Coordinate span, int length,
        double deletionProbability, Choice& choice) const {
        if (span < length) return;
        auto oldest = byAge_.lower_bound({span, {0, 0}});
        if (oldest == byAge_.end() || oldest->first != span) return;
        const auto found = gaps_.find(oldest->second.second);
        if (found->second.end == trenchLength_) {
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        considerGap(
            oldest->second.second, length, deletionProbability, choice);
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
        considerOldest(
            first->first, length, deletionProbability, choice);
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
            considerOldest(
                current->first, length, deletionProbability, choice);
            current = after;
        }
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
                considerOldest(
                    last->second.end - last->first,
                    length, deletionProbability, choice);
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
        const Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        // Excavate only the sections needed by the current insertion.
        const bool separate = canSeparate(deletionProbability);
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0, tick_);
        rebuildFitInventory(length);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right, freeSince});
        const GapKey key{end - start, start};
        ++gapSpanHistogram_[fitBucket(key.first)];
        const int maximum = static_cast<int>(
            std::min<Coordinate>(40, key.first));
        for (int size = 1; size <= maximum; ++size) {
            reusableSlotInventory_[static_cast<std::size_t>(size)] +=
                static_cast<std::uint64_t>(key.first / size);
        }
        bySize_.insert(key);
        byAge_.insert({key.first, {freeSince, start}});
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
        --gapSpanHistogram_[fitBucket(key.first)];
        const int maximum = static_cast<int>(
            std::min<Coordinate>(40, key.first));
        for (int size = 1; size <= maximum; ++size) {
            reusableSlotInventory_[static_cast<std::size_t>(size)] -=
                static_cast<std::uint64_t>(key.first / size);
        }
        bySize_.erase(key);
        byAge_.erase({key.first, {gap.freeSince, start}});
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
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.97; max_solver_rss_mib: 15.08

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.855794711043; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.738144322
family=tiny_churn mean_F/T=0.768214381
family=short_phase_churn mean_F/T=0.775016633
family=short_heavy mean_F/T=0.789874099
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.805141396
family=drifting_sizes mean_F/T=0.806320311
family=additive_cohorts mean_F/T=0.810685857
family=short_rounding mean_F/T=0.818879585
family=distribution_switch mean_F/T=0.830070276
family=size_biased_deletion mean_F/T=0.835194724
family=uniform_churn mean_F/T=0.838664986
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847248845
family=long_heavy mean_F/T=0.848173228
family=size_lifetimes mean_F/T=0.870578636
family=serial_churn mean_F/T=0.871743241
family=fifo mean_F/T=0.879104773
family=large_live_set mean_F/T=0.879584087
family=bimodal mean_F/T=0.879936997
family=micro_gap_refill mean_F/T=0.881250000
family=section_boundaries mean_F/T=0.882635178
family=recent_window_growth mean_F/T=0.883105085
family=hotset_switching mean_F/T=0.892653077
family=soft_recency_growth mean_F/T=0.895443326
family=burst_drain mean_F/T=0.902344536
family=serial_growth mean_F/T=0.913394554
family=long_prefill_recent mean_F/T=0.917886447
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920428635
family=drain_recovery mean_F/T=0.924979633
family=hotset_growth mean_F/T=0.951972595
family=background_ephemeral mean_F/T=0.952200955
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001579 rss_mib=1.359
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001562 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001618 rss_mib=1.359
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001582 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001601 rss_mib=1.359
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001582 rss_mib=1.359
case=s31_118_partial_drain family=partial_drain F/T=0.612389746 F/B=0.646045362 B/T=0.947905182 overrun=0.054958 cpu_s=0.122890 rss_mib=2.953
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.594811 rss_mib=5.297
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.620927673 F/B=0.675406191 B/T=0.919339623 overrun=0.087737 cpu_s=0.590284 rss_mib=5.703
case=s31_060_large_live_set family=large_live_set F/T=0.632938292 F/B=0.641932619 B/T=0.985988674 overrun=0.014210 cpu_s=0.759413 rss_mib=7.438
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001652 rss_mib=1.359
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001466 rss_mib=1.328
case=s31_086_tiny_churn family=tiny_churn F/T=0.650584795 F/B=0.959051724 B/T=0.678362573 overrun=0.474138 cpu_s=0.226846 rss_mib=2.625
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.004271 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.018334 rss_mib=1.703
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.029060 rss_mib=1.641
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_086_tiny_churn family=tiny_churn F/T=0.650584795 F/B=0.959051724 B/T=0.678362573 overrun=0.474138 cpu_s=0.226846 rss_mib=2.625
case=s31_006_short_heavy family=short_heavy F/T=0.739655172 F/B=0.953333333 B/T=0.775862069 overrun=0.288889 cpu_s=0.610819 rss_mib=5.422
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.542713 rss_mib=5.375
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.675757576 F/B=0.857692308 B/T=0.787878788 overrun=0.269231 cpu_s=0.003202 rss_mib=1.391
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.594811 rss_mib=5.297
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003654 rss_mib=1.406
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.135621 rss_mib=2.078
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.775431358 F/B=0.950045956 B/T=0.816204051 overrun=0.225184 cpu_s=0.240634 rss_mib=2.984
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.541404 rss_mib=5.500
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001791 rss_mib=1.375
case=s31_087_tiny_churn family=tiny_churn F/T=0.800000000 F/B=0.950000000 B/T=0.842105263 overrun=0.187500 cpu_s=0.768393 rss_mib=6.125
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.082187 rss_mib=1.797
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.044149 rss_mib=1.734
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.819387327 F/B=0.950170316 B/T=0.862358372 overrun=0.159611 cpu_s=0.237981 rss_mib=2.844
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854222510 F/B=0.982097589 B/T=0.869793918 overrun=0.149698 cpu_s=0.279382 rss_mib=4.906
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.029060 rss_mib=1.641

PAIRED SEARCH EVIDENCE
Against parent gen34: delta mean F/T=+0.000191120; improved/regressed/tied=24/14/114.
family=tiny_churn delta_F/T=-0.012067853
family=short_heavy delta_F/T=+0.011078700
family=section_boundaries delta_F/T=-0.007295438
family=long_heavy delta_F/T=+0.006573276
family=uniform_churn delta_F/T=-0.005364372
family=drifting_sizes delta_F/T=+0.003598380
Regressions:
s31_087_tiny_churn: delta_F/T=-0.044444444, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.035552536, delta_T=+40
s31_001_uniform_churn: delta_F/T=-0.021457490, delta_T=+20
s31_041_drifting_sizes: delta_F/T=-0.011780754, delta_T=+20
Gains:
s31_009_long_heavy: delta_F/T=+0.026293103, delta_T=-40
s31_044_drifting_sizes: delta_F/T=+0.026174273, delta_T=-240
s31_006_short_heavy: delta_F/T=+0.024655172, delta_T=-40
s31_102_serial_churn: delta_F/T=+0.014223164, delta_T=-60

Against leader gen24: delta mean F/T=-0.002931171; improved/regressed/tied=40/43/69.
family=tiny_churn delta_F/T=-0.068439183
family=short_heavy delta_F/T=-0.025435286
family=short_phase_churn delta_F/T=-0.012975454
family=long_heavy delta_F/T=+0.011674310
family=serial_churn delta_F/T=+0.011061989
family=section_boundaries delta_F/T=-0.009957250
Regressions:
s31_086_tiny_churn: delta_F/T=-0.179639085, delta_T=+740
s31_006_short_heavy: delta_F/T=-0.101521298, delta_T=+140
s31_087_tiny_churn: delta_F/T=-0.094117647, delta_T=+40
s31_033_burst_drain: delta_F/T=-0.044027517, delta_T=+40
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_024_fifo: delta_F/T=+0.041089202, delta_T=-80
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_062_size_biased_deletion: delta_F/T=+0.034663376, delta_T=-320

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855794711; mean positive loss on worst 16 cases=0.018188060; max case loss=0.067157140; regressed cases=33; worst family delta F/T=-0.016789285. These are selection diagnostics; primary fitness remains mean F/T.



# Instructions

Create a standalone summary for this program using the following exact format:

**Program Name: [Short summary name of the algorithm (up to 10 words)]**
- **Implementation**: [Key implementation details (1-2 sentences)]
- **Performance**: [Score/metrics summary (1 sentence)]
- **Feedback**: [Key insights from evaluation (1-2 sentences)]

Focus on:
1. What specific implementation details were done
2. How these details affected performance
3. Implementation details that are relevant to the approach
4. Any evaluation feedback that provides insights

Keep the program summary concise but informative. Follow the format exactly.
