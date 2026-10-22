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
        Coordinate at = -1, digs = 0;
        Coordinate tail = -1;
        if (!gaps_.empty() && gaps_.rbegin()->second == trench_)
            tail = gaps_.rbegin()->first;
        if (length < 40 && !starts_[length].empty()) {
            at = *starts_[length].begin();
        } else if (length == 40) {
            auto exact = sizes_.lower_bound({40, 0});
            if (exact != sizes_.end() && exact->first == 40)
                at = exact->second;
        }
        if (at >= 0 && at == tail) at = -1;
        if (at < 0) {
            for (int k = length; k <= 40; ++k) {
                if (starts_[k].empty()) continue;
                const Coordinate candidate = *starts_[k].begin();
                if (candidate != tail && (at < 0 || candidate < at))
                    at = candidate;
            }
        }
        if (at < 0 && tail >= 0 && trench_ - tail >= length)
            at = tail;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.97; max_solver_rss_mib: 5.58

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.855647273918; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.738008982
family=short_phase_churn mean_F/T=0.769027006
family=drifting_sizes mean_F/T=0.794273673
family=micro_size_shift mean_F/T=0.802083333
family=distribution_switch mean_F/T=0.816720456
family=geometric_cohorts mean_F/T=0.817305377
family=short_rounding mean_F/T=0.819122721
family=uniform_churn mean_F/T=0.820191128
family=short_heavy mean_F/T=0.825295868
family=additive_cohorts mean_F/T=0.827016922
family=size_biased_deletion mean_F/T=0.831831993
family=long_heavy mean_F/T=0.834759157
family=tiny_churn mean_F/T=0.836653564
family=long_prefill_random mean_F/T=0.837980697
family=micro_tail_reuse mean_F/T=0.845833333
family=size_lifetimes mean_F/T=0.849337556
family=serial_churn mean_F/T=0.859817359
family=bimodal mean_F/T=0.865128226
family=large_live_set mean_F/T=0.874854453
family=section_boundaries mean_F/T=0.879591613
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881780077
family=fifo mean_F/T=0.884953138
family=hotset_switching mean_F/T=0.885312853
family=soft_recency_growth mean_F/T=0.897642195
family=burst_drain mean_F/T=0.898058136
family=serial_growth mean_F/T=0.911769346
family=long_prefill_recent mean_F/T=0.917760464
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920891321
family=drain_recovery mean_F/T=0.923938362
family=hotset_growth mean_F/T=0.949971348
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955023797
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001512 rss_mib=1.312
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001332 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001509 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001420 rss_mib=1.312
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001400 rss_mib=1.312
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001617 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.612305360 F/B=0.646045362 B/T=0.947774562 overrun=0.055103 cpu_s=0.086585 rss_mib=2.000
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.616565183 F/B=0.675406191 B/T=0.912880562 overrun=0.095434 cpu_s=0.371972 rss_mib=3.109
case=s31_060_large_live_set family=large_live_set F/T=0.628498551 F/B=0.641932619 B/T=0.979072464 overrun=0.021375 cpu_s=0.407071 rss_mib=3.703
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001438 rss_mib=1.312
case=s31_040_distribution_switch family=distribution_switch F/T=0.643080357 F/B=0.692548077 B/T=0.928571429 overrun=0.076923 cpu_s=0.017819 rss_mib=1.422
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001311 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003773 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.656097561 F/B=0.781976744 B/T=0.839024390 overrun=0.191860 cpu_s=0.330134 rss_mib=2.922
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012862 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003187 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.342988 rss_mib=2.953
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.368393 rss_mib=3.000
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.675757576 F/B=0.857692308 B/T=0.787878788 overrun=0.269231 cpu_s=0.002315 rss_mib=1.359
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.682492114 F/B=0.865400000 B/T=0.788643533 overrun=0.268000 cpu_s=0.077239 rss_mib=1.641
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003187 rss_mib=1.375
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.062382 rss_mib=1.531
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.791159587 F/B=0.950045956 B/T=0.832759281 overrun=0.200827 cpu_s=0.133246 rss_mib=2.062
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.120917 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001765 rss_mib=1.359
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.656097561 F/B=0.781976744 B/T=0.839024390 overrun=0.191860 cpu_s=0.330134 rss_mib=2.922
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.833795189 F/B=0.982097589 B/T=0.848994233 overrun=0.177864 cpu_s=0.163283 rss_mib=2.797
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.032273 rss_mib=1.500
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.653538 rss_mib=4.469
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.132565 rss_mib=1.844
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.827225131 F/B=0.954682779 B/T=0.866492147 overrun=0.154079 cpu_s=0.043356 rss_mib=1.500
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.829129512 F/B=0.950170316 B/T=0.872611465 overrun=0.145985 cpu_s=0.132398 rss_mib=2.000

PAIRED SEARCH EVIDENCE
Against parent gen10: delta mean F/T=+0.001483311; improved/regressed/tied=35/24/93.
family=drifting_sizes delta_F/T=+0.014517202
family=short_phase_churn delta_F/T=+0.012341281
family=tiny_churn delta_F/T=+0.007466042
family=size_lifetimes delta_F/T=+0.005629582
family=long_heavy delta_F/T=+0.005455717
family=burst_drain delta_F/T=+0.005219307
Regressions:
s31_020_section_boundaries: delta_F/T=-0.019430894, delta_T=+120
s31_004_uniform_churn: delta_F/T=-0.010889774, delta_T=+80
s31_096_hotset_switching: delta_F/T=-0.008703004, delta_T=+100
s31_054_additive_cohorts: delta_F/T=-0.004674281, delta_T=+40
Gains:
s31_041_drifting_sizes: delta_F/T=+0.061755146, delta_T=-120
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_086_tiny_churn: delta_F/T=+0.029864168, delta_T=-100
s31_033_burst_drain: delta_F/T=+0.020441347, delta_T=-20

Against leader gen10: delta mean F/T=+0.001483311; improved/regressed/tied=35/24/93.
family=drifting_sizes delta_F/T=+0.014517202
family=short_phase_churn delta_F/T=+0.012341281
family=tiny_churn delta_F/T=+0.007466042
family=size_lifetimes delta_F/T=+0.005629582
family=long_heavy delta_F/T=+0.005455717
family=burst_drain delta_F/T=+0.005219307
Regressions:
s31_020_section_boundaries: delta_F/T=-0.019430894, delta_T=+120
s31_004_uniform_churn: delta_F/T=-0.010889774, delta_T=+80
s31_096_hotset_switching: delta_F/T=-0.008703004, delta_T=+100
s31_054_additive_cohorts: delta_F/T=-0.004674281, delta_T=+40
Gains:
s31_041_drifting_sizes: delta_F/T=+0.061755146, delta_T=-120
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_086_tiny_churn: delta_F/T=+0.029864168, delta_T=-100
s31_033_burst_drain: delta_F/T=+0.020441347, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855647274; mean positive loss on worst 16 cases=0.032748923; max case loss=0.075378788; regressed cases=52; worst family delta F/T=-0.028682913. These are selection diagnostics; primary fitness remains mean F/T.



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
