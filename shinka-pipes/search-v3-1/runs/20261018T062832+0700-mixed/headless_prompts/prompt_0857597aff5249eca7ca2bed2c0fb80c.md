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
// NAME: scarce_capacity_exchange
// DESCRIPTION: Parent residual-fit and exposure-guided splitting,
// with a capacity-scarcity exchange against Best-Fit.
// Ablation: kEnableScarceCapacityExchange=false restores gen24.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kEnableExposureSplit = true;
    static constexpr bool kEnableScarceCapacityExchange = true;
    static constexpr long double kHazardPriorReleases = 2.0L;
    static constexpr long double kSplitRateRatio = 1.25L;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    using LiveMap = std::map<int, std::size_t>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    LiveMap live_;
    std::array<std::set<int>, kSmallLimit> bins_;
    std::set<std::pair<int, int>> large_;
    // Homogeneous capacity of internal holes; the tail is added on demand.
    std::array<std::int64_t, kMaxLength + 1> holeCapacity_{};
    std::uint64_t lowMask_ = 0;
    std::uint64_t highMask_ = 0;
    int trench_ = 0;
    int frontier_ = 0;
    std::size_t insertions_ = 0;
    std::array<std::uint32_t, kMaxLength + 1> observations_{};
    std::array<std::uint32_t, kMaxLength + 1> weights_{};
    std::array<std::int64_t, kSmallLimit> waste_{};
    std::int64_t totalWeight_ = 0;
    // Exposure is measured in live-pipe command steps.
    // Per-size exposure is settled lazily when its population changes.
    std::uint64_t commandClock_ = 0;
    std::size_t liveCount_ = 0;
    std::uint64_t totalReleases_ = 0;
    long double totalExposure_ = 0.0L;
    std::array<std::size_t, kMaxLength + 1> liveByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> releasesByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> exposureClock_{};
    std::array<long double, kMaxLength + 1> exposure_{};
    void rebuildProfile() {
        waste_.fill(0);
        totalWeight_ = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            weights_[k] = observations_[k] + 1;
            const std::int64_t weight = weights_[k];
            totalWeight_ += weight;
            int remainder = 0;
            for (int s = 0; s < kSmallLimit; ++s) {
                waste_[s] += weight * remainder;
                if (++remainder == k) {
                    remainder = 0;
                }
            }
        }
    }
    void observe(int length) {
        ++insertions_;
        ++observations_[length];
        if ((insertions_ & 511u) == 0) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observations_[k] >>= 1;
            }
        }
        if (insertions_ <= 32 || (insertions_ & 63u) == 0) {
            rebuildProfile();
        }
    }
    void beginCommand() {
        ++commandClock_;
        totalExposure_ += static_cast<long double>(liveCount_);
    }
    long double exposureAt(int length) const {
        return exposure_[length]
             + static_cast<long double>(liveByLength_[length])
             * static_cast<long double>(
                   commandClock_ - exposureClock_[length]);
    }
    void settleExposure(int length) {
        exposure_[length] = exposureAt(length);
        exposureClock_[length] = commandClock_;
    }
    void recordBirth(int length) {
        settleExposure(length);
        ++liveByLength_[length];
        ++liveCount_;
    }
    void recordRelease(int length) {
        settleExposure(length);
        --liveByLength_[length];
        --liveCount_;
        ++releasesByLength_[length];
        ++totalReleases_;
    }
    bool preferRightSplit(int start, int size, int length) const {
        if (!kEnableExposureSplit ||
            size == length ||
            totalReleases_ == 0) {
            return false;
        }
        const auto right = live_.lower_bound(start);
        if (right == live_.begin() || right == live_.end()) {
            return false;
        }
        const auto left = std::prev(right);
        const Pipe& leftPipe = pipes_[left->second];
        const Pipe& rightPipe = pipes_[right->second];
        if (leftPipe.start + leftPipe.length != start ||
            rightPipe.start != start + size ||
            leftPipe.length == rightPipe.length) {
            return false;
        }
        const long double priorExposure =
            kHazardPriorReleases * totalExposure_
            / static_cast<long double>(totalReleases_);
        const auto releaseRate = [&](int neighborLength) {
            const long double releases =
                static_cast<long double>(
                    releasesByLength_[neighborLength])
                + kHazardPriorReleases;
            return releases
                 / (exposureAt(neighborLength) + priorExposure);
        };
        // Leave the residual beside the neighbor with a sufficiently
        // higher estimated release rate.
        return releaseRate(leftPipe.length)
             > kSplitRateRatio * releaseRate(rightPipe.length);
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] += length / k;
            }
        }
        if (length < kSmallLimit) {
            bins_[length].insert(start);
            if (length < 64) {
                lowMask_ |= std::uint64_t{1} << length;
            } else {
                highMask_ |= std::uint64_t{1} << (length - 64);
            }
        } else {
            large_.emplace(length, start);
        }
    }
    void eraseHole(HoleMap::iterator it) {
        const int start = it->first;
        const int length = it->second;
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] -= length / k;
            }
        }
        if (length < kSmallLimit) {
            auto& bin = bins_[length];
            bin.erase(start);
            if (bin.empty()) {
                if (length < 64) {
                    lowMask_ &= ~(std::uint64_t{1} << length);
                } else {
                    highMask_ &= ~(std::uint64_t{1} << (length - 64));
                }
            }
        } else {
            large_.erase(std::make_pair(length, start));
        }
        holes_.erase(it);
    }
    std::pair<int, int> chooseHole(int length) const {
        if (!bins_[length].empty()) {
            return {*bins_[length].begin(), length};
        }
        int bestStart = -1;
        int bestSize = 0;
        std::int64_t bestScore =
            std::numeric_limits<std::int64_t>::max();
        const auto consider = [&](int size) {
            const int residual = size - length;
            const std::int64_t regret =
                waste_[residual] + waste_[length] - waste_[size];
            const std::int64_t score =
                kRegretScale * regret
                + totalWeight_ * std::min(residual, kMaxLength);
            if (score < bestScore ||
                (score == bestScore && size < bestSize)) {
                bestScore = score;
                bestSize = size;
                bestStart = *bins_[size].begin();
            }
        };
        std::uint64_t mask =
            lowMask_ & (~std::uint64_t{0} << length);
        while (mask != 0) {
            const int size = std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        mask = highMask_;
        while (mask != 0) {
            const int size = 64 + std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        if (!large_.empty()) {
            const auto candidate = *large_.begin();
            const int size = candidate.first;
            const int start = candidate.second;
            if (bestStart < 0) {
                return {start, size};
            }
            // Here residual >= 40, and regret is nonnegative.
            std::int64_t score = totalWeight_ * kMaxLength;
            if (score < bestScore) {
                for (int k = 2; k <= kMaxLength; ++k) {
                    const int remainder = length % k;
                    if (remainder != 0 && size % k < remainder) {
                        score += kRegretScale
                               * static_cast<std::int64_t>(weights_[k]) * k;
                        if (score >= bestScore) {
                            break;
                        }
                    }
                }
                if (score < bestScore) {
                    bestStart = start;
                    bestSize = size;
                }
            }
        }
        return {bestStart, bestSize};
    }
    std::pair<int, int> chooseScarcityExchange(
        int length, std::pair<int, int> parent) const {
        if (!kEnableScarceCapacityExchange ||
            parent.first < 0 || parent.second == length) {
            return parent;
        }
        std::pair<int, int> bestFit = parent;
        const std::uint64_t fittingLow =
            lowMask_ & (~std::uint64_t{0} << length);
        if (fittingLow != 0) {
            const int size = std::countr_zero(fittingLow);
            bestFit = {*bins_[size].begin(), size};
        } else if (highMask_ != 0) {
            const int size = 64 + std::countr_zero(highMask_);
            bestFit = {*bins_[size].begin(), size};
        } else if (!large_.empty()) {
            const auto candidate = *large_.begin();
            bestFit = {candidate.second, candidate.first};
        }
        if (bestFit.second >= parent.second) {
            return parent;
        }
        const int tail = trench_ - frontier_;
        const std::int64_t freeVolume = holeCapacity_[1] + tail;
        long double difference =
            static_cast<long double>(totalWeight_)
            * (std::min(bestFit.second - length, kMaxLength)
               - std::min(parent.second - length, kMaxLength));
        for (int k = 2; k <= kMaxLength; ++k) {
            const int remainder = length % k;
            if (remainder == 0) {
                continue;
            }
            // For s >= length, splitting loses an extra homogeneous
            // slot precisely when s % k < length % k.
            const int carryDifference =
                static_cast<int>(bestFit.second % k < remainder)
                - static_cast<int>(parent.second % k < remainder);
            if (carryDifference == 0) {
                continue;
            }
            const std::int64_t capacity =
                holeCapacity_[k] + tail / k;
            const std::int64_t pooledCapacity = freeVolume / k;
            // Different carry indicators imply a hole of size >= k,
            // hence capacity is positive. Pooled capacity is >= capacity.
            const long double penalty =
                static_cast<long double>(kRegretScale)
                * static_cast<long double>(weights_[k]) * k
                * static_cast<long double>(pooledCapacity)
                / static_cast<long double>(capacity);
            difference += carryDifference * penalty;
        }
        return difference < 0.0L ? bestFit : parent;
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        pipes_.reserve(200001);
        pipes_.push_back({0, 0});
        rebuildProfile();
    }
    void place(int length) {
        beginCommand();
        observe(length);
        const auto chosen =
            chooseScarcityExchange(length, chooseHole(length));
        int start;
        int sections = 0;
        if (chosen.first >= 0) {
            const int holeStart = chosen.first;
            const int size = chosen.second;
            const bool splitRight =
                preferRightSplit(holeStart, size, length);
            eraseHole(holes_.find(holeStart));
            if (splitRight) {
                start = holeStart + size - length;
                addHole(holeStart, size - length);
            } else {
                start = holeStart;
                addHole(start + length, size - length);
            }
        } else {
            start = frontier_;
            const int missing = length - (trench_ - frontier_);
            if (missing > 0) {
                sections = (missing + 19) / 20;
                trench_ += sections * 20;
            }
            frontier_ += length;
        }
        const std::size_t pid = pipes_.size();
        pipes_.push_back({start, length});
        live_.emplace(start, pid);
        recordBirth(length);
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        beginCommand();
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        const int length = pipe.length;
        int start = pipe.start;
        int end = start + length;
        recordRelease(length);
        live_.erase(originalStart);
        pipe.length = 0;
        auto next = holes_.lower_bound(start);
        if (next != holes_.begin()) {
            auto previous = std::prev(next);
            if (previous->first + previous->second == start) {
                start = previous->first;
                eraseHole(previous);
            }
        }
        if (next != holes_.end() && next->first == end) {
            end += next->second;
            eraseHole(next);
        }
        if (end == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, end - start);
        }
        std::cout << originalStart << '\n';
        std::cout.flush();
    }
};
}
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.96; max_solver_rss_mib: 7.00

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.857768360995; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737790388
family=short_phase_churn mean_F/T=0.787992087
family=drifting_sizes mean_F/T=0.800592585
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.804518839
family=short_rounding mean_F/T=0.818879585
family=distribution_switch mean_F/T=0.819379426
family=additive_cohorts mean_F/T=0.819584404
family=size_biased_deletion mean_F/T=0.821977053
family=short_heavy mean_F/T=0.826267648
family=tiny_churn mean_F/T=0.833601270
family=uniform_churn mean_F/T=0.839144287
family=long_heavy mean_F/T=0.839623918
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847075529
family=serial_churn mean_F/T=0.859534919
family=size_lifetimes mean_F/T=0.869160652
family=fifo mean_F/T=0.871117667
family=bimodal mean_F/T=0.878717767
family=large_live_set mean_F/T=0.880270940
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881844748
family=hotset_switching mean_F/T=0.886025038
family=section_boundaries mean_F/T=0.888814287
family=soft_recency_growth mean_F/T=0.897012698
family=burst_drain mean_F/T=0.910457307
family=serial_growth mean_F/T=0.916371801
family=long_prefill_recent mean_F/T=0.917772168
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920728456
family=drain_recovery mean_F/T=0.924504785
family=hotset_growth mean_F/T=0.950146436
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955712409
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001519 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001512 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001424 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001509 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001452 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001471 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611126393 F/B=0.646045362 B/T=0.945949663 overrun=0.057139 cpu_s=0.084135 rss_mib=1.812
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615796039 F/B=0.675406191 B/T=0.911741775 overrun=0.096802 cpu_s=0.300155 rss_mib=1.938
case=s31_060_large_live_set family=large_live_set F/T=0.632236996 F/B=0.641932619 B/T=0.984896198 overrun=0.015335 cpu_s=0.391472 rss_mib=2.859
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001409 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.313051 rss_mib=1.641
case=s31_040_distribution_switch family=distribution_switch F/T=0.645964126 F/B=0.692548077 B/T=0.932735426 overrun=0.072115 cpu_s=0.016793 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001469 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003411 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012406 rss_mib=1.438
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.332088 rss_mib=1.672
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755316039 F/B=0.950045956 B/T=0.795031056 overrun=0.257812 cpu_s=0.133614 rss_mib=1.734
case=s31_009_long_heavy family=long_heavy F/T=0.762500000 F/B=0.953125000 B/T=0.800000000 overrun=0.250000 cpu_s=0.350334 rss_mib=1.703
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.704723127 F/B=0.865400000 B/T=0.814332248 overrun=0.228000 cpu_s=0.074380 rss_mib=1.453
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.313051 rss_mib=1.641
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001719 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002367 rss_mib=1.391
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.059226 rss_mib=1.422
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.810256410 F/B=0.954682779 B/T=0.848717949 overrun=0.178248 cpu_s=0.040135 rss_mib=1.422
case=s31_039_distribution_switch family=distribution_switch F/T=0.808904110 F/B=0.952419355 B/T=0.849315068 overrun=0.177419 cpu_s=0.617064 rss_mib=1.938
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.113863 rss_mib=1.531
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822147368 F/B=0.950170316 B/T=0.865263158 overrun=0.155718 cpu_s=0.122662 rss_mib=1.656
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852686471 F/B=0.982097589 B/T=0.868229878 overrun=0.151769 cpu_s=0.154893 rss_mib=2.391
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030207 rss_mib=1.422
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.670988655 F/B=0.768089054 B/T=0.873581848 overrun=0.144712 cpu_s=0.019598 rss_mib=1.391

PAIRED SEARCH EVIDENCE
Against parent gen24: delta mean F/T=-0.000957521; improved/regressed/tied=20/29/103.
family=distribution_switch delta_F/T=-0.013801107
family=short_heavy delta_F/T=+0.010958264
family=size_biased_deletion delta_F/T=-0.010813050
family=size_lifetimes delta_F/T=-0.008836681
family=bimodal delta_F/T=-0.006932050
family=drifting_sizes delta_F/T=-0.003950533
Regressions:
s31_039_distribution_switch: delta_F/T=-0.046892992, delta_T=+80
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_029_size_lifetimes: delta_F/T=-0.035346722, delta_T=+160
s31_014_bimodal: delta_F/T=-0.024725047, delta_T=+140
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_055_additive_cohorts: delta_F/T=+0.015673401, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.012500000, delta_T=-20
s31_094_hotset_switching: delta_F/T=+0.007496252, delta_T=-20

Against leader gen61: delta mean F/T=-0.001793105; improved/regressed/tied=28/52/72.
family=bimodal delta_F/T=-0.017917181
family=distribution_switch delta_F/T=-0.015104647
family=section_boundaries delta_F/T=-0.012647196
family=short_rounding delta_F/T=+0.010657895
family=long_heavy delta_F/T=-0.010132211
family=size_biased_deletion delta_F/T=-0.009398144
Regressions:
s31_014_bimodal: delta_F/T=-0.039493211, delta_T=+220
s31_039_distribution_switch: delta_F/T=-0.034667319, delta_T=+60
s31_020_section_boundaries: delta_F/T=-0.027011372, delta_T=+160
s31_009_long_heavy: delta_F/T=-0.026293103, delta_T=+40
Gains:
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_127_short_phase_churn: delta_F/T=+0.018736786, delta_T=-20
s31_006_short_heavy: delta_F/T=+0.016176471, delta_T=-20
s31_022_fifo: delta_F/T=+0.015767207, delta_T=-100

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857768361; mean positive loss on worst 16 cases=0.025056869; max case loss=0.072439174; regressed cases=40; worst family delta F/T=-0.026023943. These are selection diagnostics; primary fitness remains mean F/T.



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
