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
        erase(at);
        add(at + length, finish);
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.97; max_solver_rss_mib: 5.62

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.858347567674; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737103135
family=short_phase_churn mean_F/T=0.785915949
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.807979030
family=geometric_cohorts mean_F/T=0.811675991
family=drifting_sizes mean_F/T=0.812747558
family=short_heavy mean_F/T=0.813719605
family=additive_cohorts mean_F/T=0.823705648
family=distribution_switch mean_F/T=0.825147983
family=uniform_churn mean_F/T=0.830529159
family=tiny_churn mean_F/T=0.830637449
family=long_heavy mean_F/T=0.839706411
family=size_biased_deletion mean_F/T=0.842862995
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846914274
family=serial_churn mean_F/T=0.859962144
family=size_lifetimes mean_F/T=0.873630709
family=large_live_set mean_F/T=0.878783594
family=recent_window_growth mean_F/T=0.881199310
family=micro_gap_refill mean_F/T=0.881250000
family=bimodal mean_F/T=0.882743831
family=hotset_switching mean_F/T=0.883051847
family=section_boundaries mean_F/T=0.884754102
family=fifo mean_F/T=0.895019728
family=soft_recency_growth mean_F/T=0.896312745
family=burst_drain mean_F/T=0.899719553
family=serial_growth mean_F/T=0.915587982
family=long_prefill_recent mean_F/T=0.917704145
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920954915
family=drain_recovery mean_F/T=0.923335943
family=hotset_growth mean_F/T=0.950208451
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955014768
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001498 rss_mib=1.297
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001325 rss_mib=1.297
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001351 rss_mib=1.297
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001405 rss_mib=1.297
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001442 rss_mib=1.297
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001497 rss_mib=1.297
case=s31_118_partial_drain family=partial_drain F/T=0.611715308 F/B=0.646045362 B/T=0.946861233 overrun=0.056121 cpu_s=0.085211 rss_mib=2.000
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.613214286 F/B=0.675406191 B/T=0.907919255 overrun=0.101420 cpu_s=0.317991 rss_mib=3.109
case=s31_060_large_live_set family=large_live_set F/T=0.632532089 F/B=0.641932619 B/T=0.985355893 overrun=0.014862 cpu_s=0.414800 rss_mib=3.750
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001445 rss_mib=1.297
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.332530 rss_mib=2.922
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001363 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002948 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.017039 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012656 rss_mib=1.422
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.019611 rss_mib=1.422
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.758363903 F/B=0.950045956 B/T=0.798239178 overrun=0.252757 cpu_s=0.133648 rss_mib=2.062
case=s31_009_long_heavy family=long_heavy F/T=0.762500000 F/B=0.953125000 B/T=0.800000000 overrun=0.250000 cpu_s=0.374042 rss_mib=3.000
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002858 rss_mib=1.375
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.062912 rss_mib=1.516
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.766129032 F/B=0.950000000 B/T=0.806451613 overrun=0.240000 cpu_s=0.347167 rss_mib=2.953
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.332530 rss_mib=2.922
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.709344262 F/B=0.865400000 B/T=0.819672131 overrun=0.220000 cpu_s=0.077088 rss_mib=1.641
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001727 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002361 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.115798 rss_mib=1.844
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.031148 rss_mib=1.500
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.528910 rss_mib=3.297
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.645237 rss_mib=4.469
case=s31_102_serial_churn family=serial_churn F/T=0.820923913 F/B=0.950000000 B/T=0.864130435 overrun=0.157233 cpu_s=0.158330 rss_mib=1.891
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821110177 F/B=0.950170316 B/T=0.864171573 overrun=0.157178 cpu_s=0.125965 rss_mib=1.953
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.337235 rss_mib=2.969

PAIRED SEARCH EVIDENCE
Against parent gen11: delta mean F/T=+0.001594366; improved/regressed/tied=22/16/114.
family=size_lifetimes delta_F/T=+0.019195661
family=size_biased_deletion delta_F/T=+0.010998815
family=bimodal delta_F/T=-0.009574468
family=short_heavy delta_F/T=+0.008578530
family=uniform_churn delta_F/T=+0.006516678
family=fifo delta_F/T=+0.006264261
Regressions:
s31_015_bimodal: delta_F/T=-0.038297872, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.013606474, delta_T=+60
s31_040_distribution_switch: delta_F/T=-0.008969862, delta_T=+60
s31_086_tiny_churn: delta_F/T=-0.005884375, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.040963203, delta_T=-40
s31_006_short_heavy: delta_F/T=+0.030555556, delta_T=-40
s31_004_uniform_churn: delta_F/T=+0.027669271, delta_T=-200

Against leader gen3: delta mean F/T=+0.001015184; improved/regressed/tied=49/33/70.
family=drifting_sizes delta_F/T=+0.009439940
family=fifo delta_F/T=+0.008172368
family=tiny_churn delta_F/T=-0.007576686
family=long_heavy delta_F/T=+0.007566275
family=hotset_switching delta_F/T=+0.006962685
family=size_lifetimes delta_F/T=+0.006898578
Regressions:
s31_086_tiny_churn: delta_F/T=-0.030306745, delta_T=+100
s31_001_uniform_churn: delta_F/T=-0.019390244, delta_T=+20
s31_015_bimodal: delta_F/T=-0.018750000, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.017398050, delta_T=+20
Gains:
s31_014_bimodal: delta_F/T=+0.035470188, delta_T=-200
s31_009_long_heavy: delta_F/T=+0.024596774, delta_T=-40
s31_096_hotset_switching: delta_F/T=+0.022930166, delta_T=-260
s31_063_size_biased_deletion: delta_F/T=+0.020957918, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.858347568; mean positive loss on worst 16 cases=0.025654128; max case loss=0.061204395; regressed cases=39; worst family delta F/T=-0.020255386. These are selection diagnostics; primary fitness remains mean F/T.



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
