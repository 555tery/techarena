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
#include <bit>
#include <cmath>
namespace {
using Coordinate = std::int64_t;
using SizeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr bool kUseGlobalPackingForecast = true;
constexpr bool kUseExposureEdge = true;
constexpr int kForecastHorizon = 8;
constexpr int kForecastScenarios = 4;
constexpr int kForecastCapacity = 40 * kForecastHorizon;
constexpr int kMaskWords = kForecastCapacity / 64 + 1;
constexpr int kDistinctCandidateSizes = 8;
constexpr int kMaximumCandidates = 12;
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
struct Change {
    int capacity = 0;
    int delta = 0;
};
struct ReleaseExposure {
    double exposure = 0.0;
    double releases = 0.0;
    std::uint64_t liveCount = 0;
    std::uint64_t lastTick = 0;
};
// Capacities above the complete forecast volume are interchangeable:
// any one of them can accommodate the entire remaining forecast.
struct Inventory {
    std::array<int, kForecastCapacity + 1> count{};
    std::array<std::uint64_t, kMaskWords> mask{};
    void change(int capacity, int delta) {
        if (capacity <= 0) return;
        int& value = count[static_cast<std::size_t>(capacity)];
        value += delta;
        const std::size_t word =
            static_cast<std::size_t>(capacity >> 6);
        const std::uint64_t bit =
            std::uint64_t{1} << (capacity & 63);
        if (value == 0) {
            mask[word] &= ~bit;
        } else {
            mask[word] |= bit;
        }
    }
    int firstFit(int length) const {
        int word = length >> 6;
        std::uint64_t available =
            mask[static_cast<std::size_t>(word)] &
            (~std::uint64_t{0} << (length & 63));
        while (true) {
            if (available != 0) {
                return word * 64 +
                    static_cast<int>(std::countr_zero(available));
            }
            ++word;
            if (word >= kMaskWords) return 0;
            available = mask[static_cast<std::size_t>(word)];
        }
    }
};
class Allocator {
public:
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        ++tick_;
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        observeLength(length);
        refreshModel(newlyObservedLength);
        Coordinate digs = 0;
        Coordinate chosenStart = 0;
        // Growth is allowed only after checking the complete size index.
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
            chosenStart = chooseGap(length);
        }
        const auto selected = gaps_.find(chosenStart);
        const Gap gap = selected->second;
        const bool highEnd = chooseHighEnd(
            chosenStart, gap, length);
        const Coordinate allocationStart =
            highEnd ? gap.end - length : chosenStart;
        eraseGap(selected);
        // PID zero is the sentinel of the spatial live-pipe list.
        const std::size_t pid = pipes_.size();
        pipes_.push_back(Pipe{
            allocationStart, length, true,
            gap.leftPid, gap.rightPid});
        pipes_[gap.leftPid].rightPid = pid;
        pipes_[gap.rightPid].leftPid = pid;
        observeBirth(length);
        // Allocate the exact length at one endpoint of the selected gap.
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
    using Scenarios = std::array<
        std::array<int, kForecastHorizon>, kForecastScenarios>;
    GapMap gaps_;
    std::set<SizeKey> bySize_;
    std::vector<Pipe> pipes_{Pipe{}};
    // The expandable tail is represented separately during forecasts.
    Inventory interiorInventory_;
    Coordinate trenchLength_ = 0;
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, 41> requestPrefix_{};
    // Index zero aggregates exposure and releases over all lengths.
    std::array<ReleaseExposure, 41> releaseExposure_{};
    // Internal sampling state; independent of case identifiers or raw input.
    std::uint64_t randomState_ = 0x243f6a8885a308d3ULL;
    static int capacityBucket(Coordinate capacity) {
        return static_cast<int>(
            std::min<Coordinate>(capacity, kForecastCapacity));
    }
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
    void insertGap(
        Coordinate start, Coordinate end,
        std::uint64_t freeSince,
        std::size_t leftPid, std::size_t rightPid) {
        if (start >= end) return;
        gaps_.emplace(
            start, Gap{end, freeSince, leftPid, rightPid});
        bySize_.insert({end - start, {freeSince, start}});
        if (end != trenchLength_) {
            interiorInventory_.change(
                capacityBucket(end - start), 1);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const Coordinate span = gap.end - start;
        if (gap.end != trenchLength_) {
            interiorInventory_.change(capacityBucket(span), -1);
        }
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
        // The live count is constant between updates of this class.
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
        // Empirical-Bayes Gamma-Poisson rate estimates. Live exposure
        // includes pipes whose lifetimes have not ended.
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
        // Leave the remainder next to the more strongly releasing
        // boundary only when the heuristic uncertainty bands separate.
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
    std::uint64_t nextRandom() {
        randomState_ += 0x9e3779b97f4a7c15ULL;
        std::uint64_t value = randomState_;
        value = (value ^ (value >> 30)) *
            0xbf58476d1ce4e5b9ULL;
        value = (value ^ (value >> 27)) *
            0x94d049bb133111ebULL;
        return value ^ (value >> 31);
    }
    double unitRandom() {
        return static_cast<double>(nextRandom() >> 11) *
            (1.0 / 9007199254740992.0);
    }
    int sampleLength(double quantile) const {
        const auto found = std::lower_bound(
            requestPrefix_.begin() + 1,
            requestPrefix_.end(), quantile);
        return static_cast<int>(
            found - requestPrefix_.begin());
    }
    Scenarios makeScenarios() {
        Scenarios scenarios{};
        // Stratification reduces sampling noise. Every candidate receives
        // exactly the same scenarios for this real insertion.
        for (int step = 0; step < kForecastHorizon; ++step) {
            std::array<int, kForecastScenarios> order{};
            for (int i = 0; i < kForecastScenarios; ++i) {
                order[static_cast<std::size_t>(i)] = i;
            }
            for (int i = kForecastScenarios - 1; i > 0; --i) {
                const int j = static_cast<int>(
                    nextRandom() %
                    static_cast<std::uint64_t>(i + 1));
                std::swap(
                    order[static_cast<std::size_t>(i)],
                    order[static_cast<std::size_t>(j)]);
            }
            for (int stratum = 0;
                 stratum < kForecastScenarios; ++stratum) {
                const double quantile =
                    (stratum + unitRandom()) /
                    static_cast<double>(kForecastScenarios);
                const int scenario =
                    order[static_cast<std::size_t>(stratum)];
                scenarios[static_cast<std::size_t>(scenario)]
                         [static_cast<std::size_t>(step)] =
                    sampleLength(quantile);
            }
        }
        return scenarios;
    }
    static void recordChange(
        Inventory& inventory, int capacity, int delta,
        Change* undo, int& undoCount) {
        if (capacity <= 0) return;
        inventory.change(capacity, delta);
        undo[undoCount++] = Change{capacity, delta};
    }
    static void restore(
        Inventory& inventory, const Change* undo,
        int undoCount) {
        while (undoCount > 0) {
            const Change change = undo[--undoCount];
            inventory.change(change.capacity, -change.delta);
        }
    }
    static unsigned forecastGrowth(
        Inventory& inventory, int tailCapacity,
        const std::array<int, kForecastHorizon>& requests) {
        std::array<Change, 2 * kForecastHorizon> undo{};
        int undoCount = 0;
        // At most two sections per request. Terminal growth must
        // dominate every possible prefix-area difference summed
        // across all scenarios; timing only breaks terminal ties.
        constexpr unsigned primaryScale =
            1U + static_cast<unsigned>(
                kForecastScenarios * kForecastHorizon *
                (kForecastHorizon + 1));
        unsigned sections = 0;
        unsigned prefixArea = 0;
        for (int length : requests) {
            const int capacity = inventory.firstFit(length);
            // Virtual successor policy: global best-fit, preferring an
            // interior gap when its capacity ties the expandable tail.
            if (capacity != 0 &&
                (tailCapacity < length ||
                 capacity <= tailCapacity)) {
                recordChange(
                    inventory, capacity, -1,
                    undo.data(), undoCount);
                recordChange(
                    inventory, capacity - length, 1,
                    undo.data(), undoCount);
            } else if (tailCapacity >= length) {
                tailCapacity -= length;
            } else {
                const int deficit = length - tailCapacity;
                const int digs =
                    (deficit + static_cast<int>(kSectionLength) - 1) /
                    static_cast<int>(kSectionLength);
                sections += static_cast<unsigned>(digs);
                tailCapacity +=
                    digs * static_cast<int>(kSectionLength) - length;
            }
            prefixArea += sections;
        }
        restore(inventory, undo.data(), undoCount);
        return sections * primaryScale + prefixArea;
    }
    Coordinate chooseGap(int length) {
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
        // Equal-span interior gaps are equivalent to the forecast.
        // Retain the oldest representative, plus the distinct tail case.
        const auto addSizeRepresentatives =
            [&](std::set<SizeKey>::const_iterator position) {
                if (position == bySize_.end()) return;
                addCandidate(position->second.second);
                const auto gap = gaps_.find(position->second.second);
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
        Coordinate tailSpan = 0;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            tailSpan = tail->second.end - tail->first;
            if (tailSpan >= length) addCandidate(tail->first);
        }
        // The complete size index has already established a fitting gap.
        if (candidateCount == 0) return fallback;
        std::sort(
            candidates.begin(),
            candidates.begin() + candidateCount,
            candidateLess);
        if (!kUseGlobalPackingForecast || candidateCount == 1) {
            return candidates[0].start;
        }
        const Scenarios scenarios = makeScenarios();
        Inventory working = interiorInventory_;
        ++mcDecisionsUsed;
        Coordinate chosenStart = candidates[0].start;
        unsigned bestScore =
            std::numeric_limits<unsigned>::max();
        for (int index = 0; index < candidateCount; ++index) {
            const Candidate& candidate =
                candidates[static_cast<std::size_t>(index)];
            std::array<Change, 2> undo{};
            int undoCount = 0;
            int virtualTail = capacityBucket(tailSpan);
            if (candidate.tail) {
                virtualTail =
                    capacityBucket(candidate.span - length);
            } else {
                recordChange(
                    working, capacityBucket(candidate.span), -1,
                    undo.data(), undoCount);
                recordChange(
                    working,
                    capacityBucket(candidate.span - length), 1,
                    undo.data(), undoCount);
            }
            unsigned score = 0;
            // Such a gap alone fits the complete forecast volume.
            const bool forecastFits =
                virtualTail >= kForecastCapacity ||
                working.count[kForecastCapacity] != 0;
            if (!forecastFits) {
                for (const auto& scenario : scenarios) {
                    score += forecastGrowth(
                        working, virtualTail, scenario);
                    ++mcRolloutsRun;
                    // Candidates are already ordered by the tie-break.
                    // Further nonnegative costs cannot rescue this one.
                    if (score >= bestScore) break;
                }
            }
            restore(working, undo.data(), undoCount);
            if (score < bestScore) {
                bestScore = score;
                chosenStart = candidate.start;
            }
            // Zero is the global minimum; later ties are less preferred.
            if (bestScore == 0) break;
        }
        return chosenStart;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.14; max_solver_rss_mib: 9.41

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.857350147178; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.736787991
family=short_phase_churn mean_F/T=0.783307891
family=short_rounding mean_F/T=0.798578833
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.807490331
family=geometric_cohorts mean_F/T=0.808650042
family=short_heavy mean_F/T=0.815520960
family=additive_cohorts mean_F/T=0.816906248
family=size_biased_deletion mean_F/T=0.821883605
family=distribution_switch mean_F/T=0.826662009
family=uniform_churn mean_F/T=0.834715116
family=long_heavy mean_F/T=0.836555587
family=tiny_churn mean_F/T=0.836653564
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.849362079
family=serial_churn mean_F/T=0.859267153
family=size_lifetimes mean_F/T=0.868848101
family=large_live_set mean_F/T=0.879035986
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881607548
family=bimodal mean_F/T=0.882881946
family=hotset_switching mean_F/T=0.884439341
family=section_boundaries mean_F/T=0.885905461
family=fifo mean_F/T=0.888451474
family=soft_recency_growth mean_F/T=0.896003405
family=burst_drain mean_F/T=0.902254811
family=serial_growth mean_F/T=0.915785594
family=long_prefill_recent mean_F/T=0.917753961
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920982059
family=drain_recovery mean_F/T=0.925825910
family=hotset_growth mean_F/T=0.951220369
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955389599
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001514 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001357 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001484 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001449 rss_mib=1.359
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001484 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001466 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.610454733 F/B=0.646045362 B/T=0.944910015 overrun=0.058302 cpu_s=0.089077 rss_mib=2.422
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615604053 F/B=0.675406191 B/T=0.911457521 overrun=0.097144 cpu_s=0.354936 rss_mib=4.656
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.362718 rss_mib=4.453
case=s31_060_large_live_set family=large_live_set F/T=0.632347623 F/B=0.641932619 B/T=0.985068533 overrun=0.015158 cpu_s=0.461561 rss_mib=5.500
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001485 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001405 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003019 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.014668 rss_mib=1.578
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.019373 rss_mib=1.516
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002574 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.422511 rss_mib=4.609
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.370423 rss_mib=4.531
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.757530231 F/B=0.950045956 B/T=0.797361671 overrun=0.254136 cpu_s=0.145295 rss_mib=2.531
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002574 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.362718 rss_mib=4.453
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.709344262 F/B=0.865400000 B/T=0.819672131 overrun=0.220000 cpu_s=0.086621 rss_mib=1.891
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001699 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002544 rss_mib=1.375
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.806122449 F/B=0.954682779 B/T=0.844387755 overrun=0.184290 cpu_s=0.044512 rss_mib=1.656
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.064033 rss_mib=1.672
case=s31_006_short_heavy family=short_heavy F/T=0.809433962 F/B=0.953333333 B/T=0.849056604 overrun=0.177778 cpu_s=0.384923 rss_mib=4.562
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.035298 rss_mib=1.625
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.687091 rss_mib=7.594
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.132147 rss_mib=2.297
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.824926067 F/B=0.950170316 B/T=0.868187579 overrun=0.151825 cpu_s=0.139578 rss_mib=2.406
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.040731 rss_mib=1.641

PAIRED SEARCH EVIDENCE
Against parent gen45: delta mean F/T=+0.001415289; improved/regressed/tied=26/20/106.
family=size_lifetimes delta_F/T=+0.035857452
family=tiny_churn delta_F/T=+0.011693294
family=size_biased_deletion delta_F/T=-0.010831782
family=geometric_cohorts delta_F/T=+0.005073996
family=short_phase_churn delta_F/T=-0.003987567
family=additive_cohorts delta_F/T=+0.003638792
Regressions:
s31_006_short_heavy: delta_F/T=-0.031742508, delta_T=+40
s31_062_size_biased_deletion: delta_F/T=-0.027650638, delta_T=+260
s31_039_distribution_switch: delta_F/T=-0.023432540, delta_T=+40
s31_127_short_phase_churn: delta_F/T=-0.018736786, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.052706300, delta_T=-60
s31_086_tiny_churn: delta_F/T=+0.046773176, delta_T=-160
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20

Against leader gen52: delta mean F/T=-0.001511307; improved/regressed/tied=34/49/69.
family=size_biased_deletion delta_F/T=-0.025997746
family=size_lifetimes delta_F/T=-0.023092469
family=fifo delta_F/T=+0.016050756
family=short_rounding delta_F/T=-0.009642857
family=serial_churn delta_F/T=-0.009546035
family=additive_cohorts delta_F/T=-0.006027239
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.090454545, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.062943459, delta_T=+60
s31_103_serial_churn: delta_F/T=-0.043999453, delta_T=+60
s31_122_short_rounding: delta_F/T=-0.038571429, delta_T=+20
Gains:
s31_022_fifo: delta_F/T=+0.054718684, delta_T=-360
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_001_uniform_churn: delta_F/T=+0.020384615, delta_T=-20
s31_086_tiny_churn: delta_F/T=+0.012209175, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857350147; mean positive loss on worst 16 cases=0.028224431; max case loss=0.081203008; regressed cases=41; worst family delta F/T=-0.023276000. These are selection diagnostics; primary fitness remains mean F/T.



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
