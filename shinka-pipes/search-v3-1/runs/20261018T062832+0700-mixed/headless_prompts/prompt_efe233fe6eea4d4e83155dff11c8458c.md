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
namespace {
using Coordinate = std::int64_t;
class Allocator {
    struct Pipe { Coordinate start; int length; };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
    std::map<Coordinate, std::size_t> live_;
    std::array<std::size_t, 41> population_{};
    std::array<double, 41> deaths_{}, exposure_{};
    std::array<std::uint64_t, 41> exposureAt_{};
    std::uint64_t commandTick_ = 0;
    double totalExposure_ = 0, totalDeaths_ = 0;
    void settleExposure(int length) {
        exposure_[length] +=
            static_cast<double>(commandTick_ - exposureAt_[length]) *
            static_cast<double>(population_[length]);
        exposureAt_[length] = commandTick_;
    }
    void advanceReleaseClock() {
        if (commandTick_ != 0 && commandTick_ % 128 == 0) {
            for (int k = 1; k <= 40; ++k) {
                settleExposure(k);
                exposure_[k] *= 0.5;
                deaths_[k] *= 0.5;
            }
            totalExposure_ *= 0.5;
            totalDeaths_ *= 0.5;
        }
        ++commandTick_;
        totalExposure_ += static_cast<double>(live_.size());
    }
    double releaseRate(int length) const {
        const double exposure = exposure_[length] +
            static_cast<double>(commandTick_ - exposureAt_[length]) *
            static_cast<double>(population_[length]);
        const double pooledRate = totalDeaths_ / (totalExposure_ + 1.0);
        return (deaths_[length] + 8.0 * pooledRate) / (exposure + 8.0);
    }
    void observeLength(int length) {
        if (demandMass_ >= 128) {
            demandMass_ = 0;
            for (int k = 1; k <= 40; ++k) {
                demand_[k] /= 2;
                demandMass_ += demand_[k];
            }
        }
        ++demand_[length];
        ++demandMass_;
    }
    std::uint64_t splitPenalty(Coordinate space, int length) const {
        std::uint64_t result = 0;
        for (int k = 1; k <= 40; ++k) {
            if (demand_[k] != 0 && space % k < length % k)
                result += static_cast<std::uint64_t>(demand_[k]) * k;
        }
        return result;
    }
    bool scarcityAllowsExchange(Coordinate smaller, Coordinate larger, int length) const {
        std::size_t fittingGaps = 0;
        long double extraLoss = 0;
        for (int k = 40; k >= 1; --k) {
            fittingGaps += starts_[k].size();
            if (demand_[k] == 0 || fittingGaps == 0) continue;
            const int smallerLoses = smaller >= k && smaller - length < k;
            const int largerLoses = larger >= k && larger - length < k;
            if (smallerLoses != largerLoses) {
                extraLoss += static_cast<long double>(demand_[k]) /
                             static_cast<long double>(fittingGaps) *
                             (largerLoses - smallerLoses);
            }
        }
        return extraLoss <= 0;
    }
    double releaseGain(Coordinate a, Coordinate remainder, bool rightAligned,
                       const std::array<std::uint32_t, 41>& prefix) const {
        auto neighbor = live_.lower_bound(a);
        if (rightAligned) {
            if (neighbor == live_.begin()) return 0;
            --neighbor;
        } else if (neighbor == live_.end()) {
            return 0;
        }
        const Pipe& p = pipes_[neighbor->second];
        Coordinate releasedSpace = p.length;
        if (releasedSpace >= 40) return 0;
        if (rightAligned) {
            auto outside = gaps_.lower_bound(p.start);
            if (outside != gaps_.begin()) {
                --outside;
                if (outside->second == p.start)
                    releasedSpace += outside->second - outside->first;
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end())
                releasedSpace += outside->second - outside->first;
        }
        const int before = static_cast<int>(std::min<Coordinate>(
            40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(std::min<Coordinate>(
            40, remainder + releasedSpace));
        if (before == after) return 0;
        return releaseRate(p.length) *
               static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k)
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        const auto end = sizes_.upper_bound(
            {space, std::numeric_limits<Coordinate>::max()});
        const std::array<Coordinate, 2> candidates{
            at, std::prev(end)->second};
        double best = 0;
        for (std::size_t i = 0; i < candidates.size(); ++i) {
            if (i != 0 && candidates[i] == candidates[0]) continue;
            const Coordinate a = candidates[i];
            for (int side = 0; side < 2; ++side) {
                if (side != 0 && a + space == trench_) continue;
                const double score = releaseGain(a, remainder, side != 0, prefix);
                if (score > best) {
                    best = score;
                    at = a;
                    rightAligned = side != 0;
                }
            }
        }
    }
    static int bucket(Coordinate n) { return static_cast<int>(std::min<Coordinate>(40, n)); }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b-a, a});
        starts_[bucket(b-a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b-a, a});
        starts_[bucket(b-a)].erase(a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        advanceReleaseClock();
        observeLength(length);
        Coordinate at = -1, digs = 0;
        if constexpr (false) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) {
                if (candidate->first > length) {
                    const auto penalty = splitPenalty(candidate->first, length);
                    if (penalty != 0) {
                        auto larger = sizes_.upper_bound(
                            {candidate->first, std::numeric_limits<Coordinate>::max()});
                        if (larger != sizes_.end() &&
                            splitPenalty(larger->first, length) < penalty &&
                            scarcityAllowsExchange(candidate->first, larger->first, length)) {
                            candidate = larger;
                        }
                    }
                }
                at = candidate->second;
            }
        }
        bool rightAligned = false;
        selectReleasePlacement(length, at, rightAligned);
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
                at = gaps_.rbegin()->first;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_);
        }
        const Coordinate finish = gaps_.at(at);
        const Coordinate begin = at;
        erase(begin);
        if (rightAligned) at = finish - length;
        add(begin, at);
        add(at + length, finish);
        settleExposure(length);
        ++population_[length];
        live_.emplace(at, pipes_.size());
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
        advanceReleaseClock();
        settleExposure(p.length);
        --population_[p.length];
        deaths_[p.length] += 1.0;
        totalDeaths_ += 1.0;
        live_.erase(p.start);
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) { a = left->first; erase(a); }
        }
        add(a, b);
        std::cout << p.start << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.03; max_solver_rss_mib: 10.05

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.857813638749; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737397522
family=short_phase_churn mean_F/T=0.786603427
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.808221691
family=drifting_sizes mean_F/T=0.812150913
family=geometric_cohorts mean_F/T=0.815687648
family=additive_cohorts mean_F/T=0.819645721
family=short_heavy mean_F/T=0.822795898
family=tiny_churn mean_F/T=0.830637449
family=size_biased_deletion mean_F/T=0.831240501
family=distribution_switch mean_F/T=0.833561349
family=uniform_churn mean_F/T=0.841568315
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846800647
family=long_heavy mean_F/T=0.847835634
family=size_lifetimes mean_F/T=0.848077735
family=serial_churn mean_F/T=0.862217430
family=fifo mean_F/T=0.865384124
family=large_live_set mean_F/T=0.879856649
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881715390
family=hotset_switching mean_F/T=0.882357642
family=burst_drain mean_F/T=0.886335980
family=section_boundaries mean_F/T=0.889923288
family=bimodal mean_F/T=0.893499968
family=soft_recency_growth mean_F/T=0.896708649
family=serial_growth mean_F/T=0.916435871
family=long_prefill_recent mean_F/T=0.917831360
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921045109
family=drain_recovery mean_F/T=0.925492542
family=hotset_growth mean_F/T=0.949950758
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955360444
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001506 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001299 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001561 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001469 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001481 rss_mib=1.312
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001490 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.612136658 F/B=0.646045362 B/T=0.947513432 overrun=0.055394 cpu_s=0.088466 rss_mib=2.203
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.616757770 F/B=0.675406191 B/T=0.913165704 overrun=0.095091 cpu_s=0.330473 rss_mib=3.344
case=s31_060_large_live_set family=large_live_set F/T=0.632642820 F/B=0.641932619 B/T=0.985528389 overrun=0.014684 cpu_s=0.432633 rss_mib=4.578
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.312
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.338901 rss_mib=2.922
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001395 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002948 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.654772727 F/B=0.692548077 B/T=0.945454545 overrun=0.057692 cpu_s=0.017733 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012929 rss_mib=1.484
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002923 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002923 rss_mib=1.391
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.760316293 F/B=0.950045956 B/T=0.800294226 overrun=0.249540 cpu_s=0.138895 rss_mib=2.172
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.338901 rss_mib=2.922
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.704723127 F/B=0.865400000 B/T=0.814332248 overrun=0.228000 cpu_s=0.077765 rss_mib=1.641
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.778688525 F/B=0.950000000 B/T=0.819672131 overrun=0.220000 cpu_s=0.353149 rss_mib=2.953
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.378123 rss_mib=3.000
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.117747 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001794 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002471 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.116363 rss_mib=1.875
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.050625 rss_mib=1.516
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.036157 rss_mib=1.500
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.031618 rss_mib=1.500
case=s31_033_burst_drain family=burst_drain F/T=0.818604651 F/B=0.951351351 B/T=0.860465116 overrun=0.162162 cpu_s=0.040026 rss_mib=1.500
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.818014244 F/B=0.950170316 B/T=0.860913280 overrun=0.161557 cpu_s=0.135693 rss_mib=2.047
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.364595 rss_mib=2.969

PAIRED SEARCH EVIDENCE
Against parent gen20: delta mean F/T=-0.000533929; improved/regressed/tied=49/34/69.
family=fifo delta_F/T=-0.029635603
family=size_lifetimes delta_F/T=-0.025552975
family=burst_drain delta_F/T=-0.013383574
family=size_biased_deletion delta_F/T=-0.011622494
family=uniform_churn delta_F/T=+0.011039156
family=bimodal delta_F/T=+0.010756137
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_023_fifo: delta_F/T=-0.053425532, delta_T=+60
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_033_burst_drain: delta_F/T=-0.039931934, delta_T=+40
Gains:
s31_039_distribution_switch: delta_F/T=+0.048243464, delta_T=-80
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_001_uniform_churn: delta_F/T=+0.039774859, delta_T=-40
s31_015_bimodal: delta_F/T=+0.038297872, delta_T=-40

Against leader gen24: delta mean F/T=-0.000912243; improved/regressed/tied=44/42/66.
family=size_lifetimes delta_F/T=-0.029919598
family=burst_drain delta_F/T=-0.024998201
family=long_heavy delta_F/T=+0.011336716
family=geometric_cohorts delta_F/T=+0.011028837
family=short_rounding delta_F/T=-0.010657895
family=bimodal delta_F/T=+0.007850151
Regressions:
s31_033_burst_drain: delta_F/T=-0.083959451, delta_T=+80
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
Gains:
s31_049_geometric_cohorts: delta_F/T=+0.041558442, delta_T=-40
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_062_size_biased_deletion: delta_F/T=+0.025722426, delta_T=-240

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857813639; mean positive loss on worst 16 cases=0.024748306; max case loss=0.075378788; regressed cases=37; worst family delta F/T=-0.015573911. These are selection diagnostics; primary fitness remains mean F/T.



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
