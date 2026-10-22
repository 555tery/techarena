# System Instructions

Improve a causal online dynamic storage allocator in self-contained C++20.
Propose code in your response; do not edit files or run tools/experiments.
Change only EVOLVE-BLOCK regions. Preserve immediate flushing and the protocol.
Inserts have exact length 1..40; deletes name a live PID; 0 exits.
Live pipes never move; trench grows in sections of 20 and never shrinks.
Use only past observations: no future commands, test IDs, fingerprints,
raw inputs, filesystem, network, subprocesses or other project results.
Every case must be correct with solver CPU <5 seconds and RSS <256 MiB.

Fitness is the arithmetic mean of F/T on the fixed SEARCH-v3.1 MAIN corpus:
152 cases, 38 equally weighted families with 4 equally weighted cases each.
F is final live pipe length; T is the actual final trench length.
B=20*ceil(peak_live_volume/20) is a volume lower bound, not the optimum.
B/T and T/B-1 are diagnostic only and must not replace the F/T objective.
CPU is recorded separately and has no penalty term in this fitness.
Main retains 64 broad prior and 64 expanded cases, plus 24 micro cases.
Micro cases cover early fragmentation, small remainders, neighbor releases,
size shifts and repeated reuse in workloads constructively fitting 1..3 sections.
Their short histories make cold-start decisions important; no future is available.
Most traces end near the peak; others have moderate drain or short-horizon rounding.
Parameters and mixtures do not match Open15 frequencies; hidden workloads are unknown.
Re-evaluate the eventual selected seed on this entire corpus before evolution.
Scores from earlier corpora cannot be carried over.

STRESS is a separate diagnostic corpus. It is excluded from fitness,
selection, archive decisions and model feedback, and is not run automatically.
Validation and Open15 are also excluded. Do not inspect their files/results.
This is a search corpus, not evidence of hidden-test generalization.

Propose one algorithmic mechanism per candidate. Explain its overlap with
the supplied parent, complexity, failure mode and a same-parent ablation.
Parameter tuning alone does not satisfy this research objective. Prepared
literature and malloc/jemalloc/mimalloc hypotheses may motivate mechanisms;
they do not establish improvements. Keep global fitting-gap fallback before
growth and exact pipe lengths; avoid speculative reserved trench.

RESEARCH MEMORY. Each proposal includes a compact ledger of completed ideas,
same-parent deltas and important regressions. Descriptions are author claims,
not established causal explanations. Review the history before choosing a patch.
Give the mechanism a stable NAME and state the actual behavioral difference
from earlier attempts in DESCRIPTION; renaming code is not a new mechanism.
Retrying a mechanism is allowed when fixing a bug, changing an interaction or
testing a materially different assumption. Explain that reason explicitly.
Historical SEARCH-v2 B/T evidence is not a ranking on this SEARCH-v3.1 F/T corpus.
Paired feedback compares against the actual parent and the leader frozen at
proposal time. These diagnostics never replace the fitness or correctness gates.
Parent selection additionally retains one champion per family, independently
of the scalar archive. A five-proposal cycle uses three ordinary score draws,
one regression-aware draw and one family-specialist draw, within the same island.
Regression loss is max(0, fixed gen0 F/T minus candidate F/T) per case; report
the mean of its worst ceil(10% of cases), including zero losses. A robust draw
considers candidates within 0.005 mean F/T of the island leader. A specialist
may have a lower overall mean. Preserve its useful mechanism and address its
regressions; overall best and primary fitness remain mean F/T. These selection
defaults are engineering choices, not experimentally established optimal weights.
Exact source duplicates of correct programs in THIS run are returned as repair
feedback before evaluation. Supply a meaningful new change for the same parent;
duplicate corrections share the existing three attempts with patch repairs.
Similar names, equal scores and equal finite result vectors are advisory only.

If a patch fails to apply, use exact error feedback and return the complete
corrected proposal for the SAME parent and hypothesis, including all blocks.
The exact-duplicate rejection above permits a different mechanism for that parent.
Preserve exact SEARCH whitespace. At most three total apply attempts stay
within one generation. Failed apply attempts must not enter the archive or
consume an evaluated-generation slot. Exhausted proposals are retained in a
separate bounded failure ledger; the next proposal may choose another parent.
Runtime, request and repeated infrastructure-error limits remain enforced.


# Potential Recommendations
The following are potential recommendations for the next program generation:

MIXED-START ISOLATION: use only this lineage's completed candidates and feedback. Do not infer from other lineages or historical memory.
RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Best-Fit: attempts=1; score_range=0.857332383..0.857332383
gen3 Best-Fit; correct=True; parent=None; delta_F/T=n/a; claim=Pinned strong/simple seed
  improved/regressed/tied=50/40/62
  regression s31_039_distribution_switch: delta_F/T=-0.049653143
  regression s31_122_short_rounding: delta_F/T=-0.042631579
HISTORICAL SEARCH-v2 (different inputs AND B/T objective; not a v3.1 ranking):
LINEAGE PARENT: mode=lineage-local-score; lineage=3; local mean leader=0.857332383; fixed-baseline tail loss=0.025373426; maximum case loss=0.049653143.
You MUST respond using an edit name, description, and the exact SEARCH/REPLACE diff format shown below to indicate changes:

<NAME>
A shortened name summarizing the edit you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the edit you are proposing.
</DESCRIPTION>

<DIFF>
<<<<<<< SEARCH
# Original code to find and replace (must match exactly including indentation)
=======
# New replacement code
>>>>>>> REPLACE

</DIFF>


Example of a valid diff format:
<DIFF>
<<<<<<< SEARCH
for i in range(m):
    for j in range(p):
        for k in range(n):
            C[i, j] += A[i, k] * B[k, j]
=======
# Reorder loops for better memory access pattern
for i in range(m):
    for k in range(n):
        for j in range(p):
            C[i, j] += A[i, k] * B[k, j]
>>>>>>> REPLACE

</DIFF>

* You may only modify text that lies below a line containing "EVOLVE-BLOCK-START" and above the next "EVOLVE-BLOCK-END". Everything outside those markers is read-only.
* Do not repeat the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the SEARCH/REPLACE blocks.  
* Every block’s SEARCH section must be copied **verbatim** from the current file, including indentation.
* You can propose multiple independent edits. SEARCH/REPLACE blocks follow one after another. DO NOT ADD ANY OTHER TEXT BETWEEN THESE BLOCKS.
* Make sure the file still runs after your changes.

# Previous Messages

[]

# User Request


# Current program

Here is the current program we are trying to improve (you will need to propose a modification to it below):

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
        if constexpr (false) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) at = candidate->second;
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

Here are the performance metrics of the program:

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.36; max_solver_rss_mib: 5.64

Here is additional text feedback about the current program:

Fitness F/T=0.857332383246; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737768271
family=short_phase_churn mean_F/T=0.785915949
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803307617
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808464826
family=short_heavy mean_F/T=0.815928978
family=additive_cohorts mean_F/T=0.822933487
family=distribution_switch mean_F/T=0.828134940
family=long_heavy mean_F/T=0.832140136
family=uniform_churn mean_F/T=0.835086173
family=size_biased_deletion mean_F/T=0.837129548
family=tiny_churn mean_F/T=0.838214135
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.858108083
family=size_lifetimes mean_F/T=0.866732131
family=hotset_switching mean_F/T=0.876089163
family=bimodal mean_F/T=0.877169114
family=large_live_set mean_F/T=0.881134705
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882029077
family=fifo mean_F/T=0.886847360
family=section_boundaries mean_F/T=0.887708414
family=burst_drain mean_F/T=0.894747543
family=soft_recency_growth mean_F/T=0.895967786
family=serial_growth mean_F/T=0.915700639
family=long_prefill_recent mean_F/T=0.917738148
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920891892
family=drain_recovery mean_F/T=0.924242183
family=hotset_growth mean_F/T=0.949413287
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955399574
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001501 rss_mib=1.297
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001355 rss_mib=1.297
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001386 rss_mib=1.297
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001427 rss_mib=1.297
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001503 rss_mib=1.297
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001468 rss_mib=1.297
case=s31_118_partial_drain family=partial_drain F/T=0.612558588 F/B=0.646045362 B/T=0.948166529 overrun=0.054667 cpu_s=0.085796 rss_mib=1.984
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618012520 F/B=0.675406191 B/T=0.915023474 overrun=0.092868 cpu_s=0.316263 rss_mib=3.109
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.329717 rss_mib=2.922
case=s31_060_large_live_set family=large_live_set F/T=0.632126407 F/B=0.641932619 B/T=0.984723923 overrun=0.015513 cpu_s=0.424694 rss_mib=3.797
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001410 rss_mib=1.297
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001416 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003724 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012797 rss_mib=1.422
case=s31_040_distribution_switch family=distribution_switch F/T=0.666898148 F/B=0.692548077 B/T=0.962962963 overrun=0.038462 cpu_s=0.017932 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002781 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.750182 rss_mib=2.531
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.329717 rss_mib=2.922
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.149187 rss_mib=2.062
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.354893 rss_mib=2.953
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002781 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.079996 rss_mib=1.641
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.079425 rss_mib=1.500
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001833 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002373 rss_mib=1.359
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=1.104163 rss_mib=2.203
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.713259 rss_mib=2.172
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.148238 rss_mib=2.000
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.039194 rss_mib=1.500
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.161876 rss_mib=2.781
case=s31_086_tiny_churn family=tiny_churn F/T=0.836466165 F/B=0.959051724 B/T=0.872180451 overrun=0.146552 cpu_s=0.117083 rss_mib=1.828
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.044475 rss_mib=1.500

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.002351175; improved/regressed/tied=50/40/62.
family=fifo delta_F/T=+0.055837979
family=tiny_churn delta_F/T=+0.053210469
family=short_heavy delta_F/T=+0.032221636
family=distribution_switch delta_F/T=-0.017268430
family=additive_cohorts delta_F/T=+0.015570054
family=short_phase_churn delta_F/T=+0.014335884
Regressions:
s31_039_distribution_switch: delta_F/T=-0.049653143, delta_T=+80
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_009_long_heavy: delta_F/T=-0.037520503, delta_T=+60
Gains:
s31_024_fifo: delta_F/T=+0.141686903, delta_T=-320
s31_086_tiny_churn: delta_F/T=+0.118724230, delta_T=-440
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40
s31_006_short_heavy: delta_F/T=+0.085344828, delta_T=-120

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857332383; mean positive loss on worst 16 cases=0.025373426; max case loss=0.049653143; regressed cases=40; worst family delta F/T=-0.017268430. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
