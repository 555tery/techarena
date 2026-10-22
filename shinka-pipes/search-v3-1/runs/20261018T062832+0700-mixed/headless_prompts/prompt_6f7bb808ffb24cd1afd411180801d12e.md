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

You are given multiple code scripts implementing the same algorithm.
You are tasked with generating a new code snippet that combines these code scripts in a way that is more efficient. 
I.e. perform crossover between the code scripts.
Provide the complete new program code.
You MUST respond using a short summary name, description, and the full code:

<NAME>
A shortened name summarizing the code you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the code you are proposing.
</DESCRIPTION>

<CODE>
```{language}
# The new rewritten program here.
```
</CODE>

* Keep the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the code. Do not change the code outside of these markers.
* Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
* Make sure the file still runs after your changes.
* Use the <NAME>, <DESCRIPTION>, and <CODE> delimiters to structure your response. It will be parsed afterwards.

# Research evidence and potential recommendations
MIXED-START ISOLATION: use only this lineage's completed candidates and feedback. Do not infer from other lineages or historical memory.
RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Independent 4: attempts=1; score_range=0.856555151..0.856555151
adjacent_release_edge: attempts=1; score_range=0.858287247..0.858287247
two_future_bellman: attempts=1; score_range=0.857248996..0.857248996
gen15 adjacent_release_edge; correct=True; parent=7; delta_F/T=+0.001732096; claim=Механизм выбирает край размещения внутри уже выбранной дыры. Для каждого соседнего pipe вычисляется benefit: насколько присоединение остатка к этому соседу после его удаления уменьшит прогноз расширения для следующего in
  improved/regressed/tied=45/35/72
  regression s31_017_section_boundaries: delta_F/T=-0.034085975
  regression s31_006_short_heavy: delta_F/T=-0.033000000
gen16 two_future_bellman; correct=True; parent=7; delta_F/T=+0.000693845; claim=Механизм: двухшаговый Bellman-прогноз вместо оценки только следующей вставки. Сохраняются кандидаты родителя — best fit среди внутренних интервалов и свободный суффикс. Для каждого вычисляется ожидаемое суммарное расшире
  improved/regressed/tied=31/30/91
  regression s31_122_short_rounding: delta_F/T=-0.038571429
  regression s31_008_short_heavy: delta_F/T=-0.019369369
gen7 Independent 4; correct=True; parent=None; delta_F/T=n/a; claim=Independent task-only implementation
  improved/regressed/tied=48/42/62
  regression s31_039_distribution_switch: delta_F/T=-0.049653143
  regression s31_122_short_rounding: delta_F/T=-0.042631579
HISTORICAL SEARCH-v2 (different inputs AND B/T objective; not a v3.1 ranking):
LINEAGE PARENT: mode=lineage-local-score; lineage=7; local mean leader=0.858287247; fixed-baseline tail loss=0.021022083; maximum case loss=0.052240461.

# Previous Messages

[]

# User Request

Here are the performance metrics of a set of previously implemented programs:

# Prior programs

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
/*
NAME: One-Step Frontier Best Fit
DESCRIPTION:
Внутренние свободные интервалы индексируются по адресу и по длине.
Основной кандидат — наименьший подходящий внутренний интервал.
Второй кандидат — свободный суффикс траншеи, если он достаточно велик.
Выбор между ними минимизирует прогноз расширения для одного следующего
insert без промежуточного delete. Распределение длин оценивается по
последним 512 insert с единичным prior для каждой длины 1..40.
При равном прогнозе выбирается меньший свободный интервал.
Для следующего запроса достаточно знать максимальный внутренний
интервал и длину суффикса. Поэтому прогноз вычисляется точно для
каждого кандидата относительно используемого распределения.
Расширение выполняется только тогда, когда запрос нигде не помещается.
Сложность: O(log Q + 40) на insert, O(log Q) на delete, O(Q) памяти.
Возможная неудача: смена распределения или последующие delete делают
прогноз неточным; горизонт в один insert не учитывает накопление
мелких фрагментов.
Ablation: отключить сравнение прогнозов и всегда выбирать меньший
из подходящего внутреннего интервала и суффикса. Получится обычный
best fit с теми же индексами, слиянием и минимальным расширением.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using AddressIndex = std::map<int, int>;
    using SizeIndex = std::set<std::pair<int, int>>;
    AddressIndex freeByAddress_;
    SizeIndex freeBySize_;
    std::vector<Pipe> pipes_;
    int trenchLength_ = 0;
    int frontier_ = 0;
    std::array<int, 41> frequency_{};
    std::array<int, 41> massAbove_{};
    std::array<int, 512> recent_{};
    std::size_t recentCount_ = 0;
    std::size_t recentCursor_ = 0;
    void rememberLength(int length) {
        if (recentCount_ == recent_.size()) {
            --frequency_[recent_[recentCursor_]];
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            massAbove_[bound] =
                massAbove_[bound + 1] + frequency_[bound + 1];
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // ceil((length - suffixLength) / 20) не превосходит двух.
        // Расширение нужно лишь при length > largestHole.
        const int firstThreshold =
            std::min(40, std::max(largestHole, suffixLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, suffixLength + 20));
        return massAbove_[firstThreshold] + massAbove_[secondThreshold];
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        freeByAddress_.emplace(start, length);
        freeBySize_.emplace(length, start);
    }
    void eraseHole(AddressIndex::iterator it) {
        freeBySize_.erase(std::make_pair(it->second, it->first));
        freeByAddress_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        frequency_.fill(1);
        frequency_[0] = 0;
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
    }
    void place(int length) {
        rememberLength(length);
        const int suffixLength = trenchLength_ - frontier_;
        const auto fit = freeBySize_.lower_bound(
            std::make_pair(length, 0));
        bool useHole = fit != freeBySize_.end();
        if (useHole && suffixLength >= length) {
            const auto largest = std::prev(freeBySize_.end());
            const int largestBefore = largest->first;
            int largestAfter = largestBefore;
            if (fit == largest) {
                largestAfter = 0;
                if (largest != freeBySize_.begin()) {
                    largestAfter = std::prev(largest)->first;
                }
            }
            largestAfter = std::max(
                largestAfter, fit->first - length);
            const int holeCost =
                predictedGrowth(largestAfter, suffixLength);
            const int suffixCost =
                predictedGrowth(largestBefore, suffixLength - length);
            if (holeCost != suffixCost) {
                useHole = holeCost < suffixCost;
            } else {
                useHole = fit->first <= suffixLength;
            }
        }
        int start = 0;
        int sections = 0;
        if (useHole) {
            const int holeLength = fit->first;
            start = fit->second;
            eraseHole(freeByAddress_.find(start));
            addHole(start + length, holeLength - length);
        } else {
            start = frontier_;
            const int shortage = start + length - trenchLength_;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ = start + length;
        }
        pipes_.push_back(Pipe{start, length});
        std::cout << sections << ' ' << start << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const Pipe old = pipes_[static_cast<std::size_t>(pid)];
        int start = old.start;
        int length = old.length;
        const auto right = freeByAddress_.lower_bound(start);
        if (right != freeByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                eraseHole(left);
            }
        }
        if (right != freeByAddress_.end() &&
            start + length == right->first) {
            length += right->second;
            eraseHole(right);
        }
        if (start + length == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, length);
        }
        std::cout << old.start << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.95; max_solver_rss_mib: 2.64

Text feedback:
Fitness F/T=0.856555151094; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737844190
family=short_phase_churn mean_F/T=0.781919230
family=drifting_sizes mean_F/T=0.795373350
family=geometric_cohorts mean_F/T=0.801698998
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.808221691
family=short_heavy mean_F/T=0.821655504
family=additive_cohorts mean_F/T=0.821782467
family=distribution_switch mean_F/T=0.824004658
family=size_biased_deletion mean_F/T=0.824384496
family=long_heavy mean_F/T=0.832729504
family=tiny_churn mean_F/T=0.833601270
family=uniform_churn mean_F/T=0.835086173
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.848317518
family=serial_churn mean_F/T=0.856961750
family=size_lifetimes mean_F/T=0.859658612
family=hotset_switching mean_F/T=0.878326870
family=large_live_set mean_F/T=0.880174504
family=micro_gap_refill mean_F/T=0.881250000
family=fifo mean_F/T=0.881874487
family=recent_window_growth mean_F/T=0.882331168
family=bimodal mean_F/T=0.882404172
family=section_boundaries mean_F/T=0.889100566
family=soft_recency_growth mean_F/T=0.895701709
family=burst_drain mean_F/T=0.902423379
family=serial_growth mean_F/T=0.915492559
family=long_prefill_recent mean_F/T=0.917770005
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921040583
family=drain_recovery mean_F/T=0.923693902
family=hotset_growth mean_F/T=0.949484363
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955459443
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001504 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001374 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001321 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001458 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001355 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001496 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.612558588 F/B=0.646045362 B/T=0.948166529 overrun=0.054667 cpu_s=0.085625 rss_mib=1.562
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618012520 F/B=0.675406191 B/T=0.915023474 overrun=0.092868 cpu_s=0.334947 rss_mib=1.750
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.326921 rss_mib=1.609
case=s31_060_large_live_set family=large_live_set F/T=0.631979015 F/B=0.641932619 B/T=0.984494317 overrun=0.015750 cpu_s=0.464034 rss_mib=2.125
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001329 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001378 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003347 rss_mib=1.359
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.019713 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012499 rss_mib=1.391
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003253 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.350820 rss_mib=1.625
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.368596 rss_mib=1.672
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.754489051 F/B=0.950045956 B/T=0.794160584 overrun=0.259191 cpu_s=0.142276 rss_mib=1.578
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.689012739 F/B=0.865400000 B/T=0.796178344 overrun=0.256000 cpu_s=0.075762 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003253 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.326921 rss_mib=1.609
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.049076 rss_mib=1.391
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001741 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002735 rss_mib=1.375
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.040290 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.119061 rss_mib=1.453
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.532687 rss_mib=1.797
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.822916667 F/B=0.954682779 B/T=0.861979167 overrun=0.160121 cpu_s=0.066072 rss_mib=1.406
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.123050 rss_mib=1.531
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.141791 rss_mib=1.469
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.162648 rss_mib=1.906

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.001573943; improved/regressed/tied=48/42/62.
family=fifo delta_F/T=+0.050865106
family=tiny_churn delta_F/T=+0.048597604
family=short_heavy delta_F/T=+0.037948162
family=distribution_switch delta_F/T=-0.021398712
family=size_biased_deletion delta_F/T=-0.020775109
family=serial_churn delta_F/T=-0.014781491
Regressions:
s31_039_distribution_switch: delta_F/T=-0.049653143, delta_T=+80
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.039121447, delta_T=+40
Gains:
s31_024_fifo: delta_F/T=+0.120579436, delta_T=-280
s31_006_short_heavy: delta_F/T=+0.118344828, delta_T=-160
s31_086_tiny_churn: delta_F/T=+0.100272770, delta_T=-380
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.856555151; mean positive loss on worst 16 cases=0.027827561; max case loss=0.049653143; regressed cases=42; worst family delta F/T=-0.021398712. These are selection diagnostics; primary fitness remains mean F/T.

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
/*
NAME: Two-Future-Insert Bellman
DESCRIPTION:
Кандидаты — наименьший подходящий внутренний интервал и суффикс.
Выбор минимизирует ожидаемое суммарное расширение на две следующие
вставки без промежуточных удалений. Распределение фиксируется на время
прогноза: последние 512 insert и единичный prior для длин 1..40.
Для первой моделируемой вставки выбирается размещение с минимальным
ожидаемым расширением на второй; её длина заранее неизвестна.
Гистограмма внутренних интервалов учитывает их размеры и кратность.
Длины от 80 объединяются только в прогнозе: такого интервала достаточно
для любых двух запросов. Физические длины интервалов остаются точными.
При равенстве используются одношаговый прогноз и меньший интервал.
Расширение выполняется только тогда, когда запрос нигде не помещается.
Сложность: O(log Q + 40) на insert, O(log Q) на delete, O(Q) памяти.
Возможная неудача: удаления, корреляция длин и смена распределения
нарушают предположения прогноза.
Ablation: отключить сравнение двухшаговых оценок, сохранив одношаговый
прогноз, разрешение равенств и все вспомогательные индексы.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using AddressIndex = std::map<int, int>;
    using SizeIndex = std::set<std::pair<int, int>>;
    AddressIndex freeByAddress_;
    SizeIndex freeBySize_;
    std::array<int, 81> holeCount_{};
    std::vector<Pipe> pipes_;
    int trenchLength_ = 0;
    int frontier_ = 0;
    std::array<int, 41> frequency_{};
    std::array<int, 41> massAbove_{};
    std::array<int, 512> recent_{};
    std::size_t recentCount_ = 0;
    std::size_t recentCursor_ = 0;
    void rememberLength(int length) {
        if (recentCount_ == recent_.size()) {
            --frequency_[recent_[recentCursor_]];
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            massAbove_[bound] =
                massAbove_[bound + 1] + frequency_[bound + 1];
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // ceil((length - suffixLength) / 20) не превосходит двух.
        // Расширение нужно лишь при length > largestHole.
        const int firstThreshold =
            std::min(40, std::max(largestHole, suffixLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, suffixLength + 20));
        return massAbove_[firstThreshold] + massAbove_[secondThreshold];
    }
    std::int64_t predictedTwoGrowth(
        const std::array<int, 81>& counts, int suffixLength) const {
        // Either region can hold both future requests without growth.
        if (counts[80] != 0 || suffixLength >= 80) {
            return 0;
        }
        std::array<int, 41> bestFit{};
        int largest = 0;
        int second = 0;
        int nearest = 0;
        for (int size = 80; size >= 1; --size) {
            if (counts[size] != 0) {
                nearest = size;
                if (largest == 0) {
                    largest = size;
                    if (counts[size] >= 2) {
                        second = size;
                    }
                } else if (second == 0) {
                    second = size;
                }
            }
            if (size <= 40) {
                bestFit[size] = nearest;
            }
        }
        if (second >= 40 ||
            (largest >= 40 && suffixLength >= 40)) {
            return 0;
        }
        const int totalMass = massAbove_[0];
        std::int64_t cost = 0;
        for (int nextLength = 1; nextLength <= 40; ++nextLength) {
            const int fit = bestFit[nextLength];
            int nextCost = 0;
            if (fit != 0) {
                int largestAfter = largest;
                if (fit == largest && counts[fit] == 1) {
                    largestAfter = std::max(
                        second, fit - nextLength);
                }
                nextCost = predictedGrowth(
                    largestAfter, suffixLength);
                if (suffixLength >= nextLength) {
                    nextCost = std::min(
                        nextCost,
                        predictedGrowth(
                            largest, suffixLength - nextLength));
                }
            } else {
                int remaining = suffixLength - nextLength;
                int sections = 0;
                if (remaining < 0) {
                    sections = (-remaining + 19) / 20;
                    remaining += sections * 20;
                }
                nextCost = sections * totalMass +
                    predictedGrowth(largest, remaining);
            }
            cost += static_cast<std::int64_t>(
                frequency_[nextLength]) * nextCost;
        }
        // Common denominator: totalMass squared.
        return cost;
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        freeByAddress_.emplace(start, length);
        freeBySize_.emplace(length, start);
        ++holeCount_[std::min(80, length)];
    }
    void eraseHole(AddressIndex::iterator it) {
        --holeCount_[std::min(80, it->second)];
        freeBySize_.erase(std::make_pair(it->second, it->first));
        freeByAddress_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        frequency_.fill(1);
        frequency_[0] = 0;
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
    }
    void place(int length) {
        rememberLength(length);
        const int suffixLength = trenchLength_ - frontier_;
        const auto fit = freeBySize_.lower_bound(
            std::make_pair(length, 0));
        bool useHole = fit != freeBySize_.end();
        if (useHole && suffixLength >= length) {
            const auto largest = std::prev(freeBySize_.end());
            const int largestBefore = largest->first;
            int largestAfter = largestBefore;
            if (fit == largest) {
                largestAfter = 0;
                if (largest != freeBySize_.begin()) {
                    largestAfter = std::prev(largest)->first;
                }
            }
            largestAfter = std::max(
                largestAfter, fit->first - length);
            const int holeCost =
                predictedGrowth(largestAfter, suffixLength);
            const int suffixCost =
                predictedGrowth(largestBefore, suffixLength - length);
            auto afterHole = holeCount_;
            --afterHole[std::min(80, fit->first)];
            const int remainder = fit->first - length;
            if (remainder > 0) {
                ++afterHole[std::min(80, remainder)];
            }
            const std::int64_t holeTwoCost =
                predictedTwoGrowth(afterHole, suffixLength);
            const std::int64_t suffixTwoCost =
                predictedTwoGrowth(holeCount_, suffixLength - length);
            if (holeTwoCost != suffixTwoCost) {
                useHole = holeTwoCost < suffixTwoCost;
            } else if (holeCost != suffixCost) {
                useHole = holeCost < suffixCost;
            } else {
                useHole = fit->first <= suffixLength;
            }
        }
        int start = 0;
        int sections = 0;
        if (useHole) {
            const int holeLength = fit->first;
            start = fit->second;
            eraseHole(freeByAddress_.find(start));
            addHole(start + length, holeLength - length);
        } else {
            start = frontier_;
            const int shortage = start + length - trenchLength_;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ = start + length;
        }
        pipes_.push_back(Pipe{start, length});
        std::cout << sections << ' ' << start << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const Pipe old = pipes_[static_cast<std::size_t>(pid)];
        int start = old.start;
        int length = old.length;
        const auto right = freeByAddress_.lower_bound(start);
        if (right != freeByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                eraseHole(left);
            }
        }
        if (right != freeByAddress_.end() &&
            start + length == right->first) {
            length += right->second;
            eraseHole(right);
        }
        if (start + length == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, length);
        }
        std::cout << old.start << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 2.64

Text feedback:
Fitness F/T=0.857248996282; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737519513
family=short_phase_churn mean_F/T=0.783307891
family=drifting_sizes mean_F/T=0.792010683
family=short_rounding mean_F/T=0.798578833
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.802959006
family=short_heavy mean_F/T=0.813869052
family=distribution_switch mean_F/T=0.822144539
family=additive_cohorts mean_F/T=0.824060652
family=tiny_churn mean_F/T=0.830637449
family=uniform_churn mean_F/T=0.832473254
family=size_biased_deletion mean_F/T=0.834743730
family=long_heavy mean_F/T=0.835732894
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847780204
family=serial_churn mean_F/T=0.859534919
family=fifo mean_F/T=0.877426145
family=large_live_set mean_F/T=0.880487314
family=bimodal mean_F/T=0.880680951
family=recent_window_growth mean_F/T=0.880969918
family=micro_gap_refill mean_F/T=0.881250000
family=hotset_switching mean_F/T=0.885374724
family=section_boundaries mean_F/T=0.887071801
family=size_lifetimes mean_F/T=0.890012155
family=soft_recency_growth mean_F/T=0.896187838
family=burst_drain mean_F/T=0.908064404
family=serial_growth mean_F/T=0.915070914
family=long_prefill_recent mean_F/T=0.917804037
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920932597
family=drain_recovery mean_F/T=0.924225105
family=hotset_growth mean_F/T=0.949899110
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955323605
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001477 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001293 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001470 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001395 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001439 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001448 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611715308 F/B=0.646045362 B/T=0.946861233 overrun=0.056121 cpu_s=0.083406 rss_mib=1.578
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.613595401 F/B=0.675406191 B/T=0.908483530 overrun=0.100735 cpu_s=0.304426 rss_mib=1.781
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.324311 rss_mib=1.609
case=s31_060_large_live_set family=large_live_set F/T=0.631979015 F/B=0.641932619 B/T=0.984494317 overrun=0.015750 cpu_s=0.403627 rss_mib=2.141
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001365 rss_mib=1.344
case=s31_040_distribution_switch family=distribution_switch F/T=0.645964126 F/B=0.692548077 B/T=0.932735426 overrun=0.072115 cpu_s=0.016843 rss_mib=1.359
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001458 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002934 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012665 rss_mib=1.375
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002933 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.719696970 F/B=0.950000000 B/T=0.757575758 overrun=0.320000 cpu_s=0.339217 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.364111 rss_mib=1.672
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753938731 F/B=0.950045956 B/T=0.793581327 overrun=0.260110 cpu_s=0.129211 rss_mib=1.578
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.689012739 F/B=0.865400000 B/T=0.796178344 overrun=0.256000 cpu_s=0.074925 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002933 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.324311 rss_mib=1.609
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.056591 rss_mib=1.391
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001662 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002264 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.118339 rss_mib=1.469
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.523404 rss_mib=1.812
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.825065274 F/B=0.954682779 B/T=0.864229765 overrun=0.157100 cpu_s=0.035392 rss_mib=1.391
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.122872 rss_mib=1.531
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.035018 rss_mib=1.391
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.151970 rss_mib=1.891
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030997 rss_mib=1.375

PAIRED SEARCH EVIDENCE
Against parent gen7: delta mean F/T=+0.000693845; improved/regressed/tied=31/30/91.
family=size_lifetimes delta_F/T=+0.030353543
family=size_biased_deletion delta_F/T=+0.010359234
family=short_rounding delta_F/T=-0.009642857
family=short_heavy delta_F/T=-0.007786451
family=hotset_switching delta_F/T=+0.007047854
family=burst_drain delta_F/T=+0.005641026
Regressions:
s31_122_short_rounding: delta_F/T=-0.038571429, delta_T=+20
s31_008_short_heavy: delta_F/T=-0.019369369, delta_T=+40
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
s31_006_short_heavy: delta_F/T=-0.016823529, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.090454545, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.039121447, delta_T=-40
s31_033_burst_drain: delta_F/T=+0.022564103, delta_T=-20
s31_094_hotset_switching: delta_F/T=+0.021732831, delta_T=-60

Against leader gen7: delta mean F/T=+0.000693845; improved/regressed/tied=31/30/91.
family=size_lifetimes delta_F/T=+0.030353543
family=size_biased_deletion delta_F/T=+0.010359234
family=short_rounding delta_F/T=-0.009642857
family=short_heavy delta_F/T=-0.007786451
family=hotset_switching delta_F/T=+0.007047854
family=burst_drain delta_F/T=+0.005641026
Regressions:
s31_122_short_rounding: delta_F/T=-0.038571429, delta_T=+20
s31_008_short_heavy: delta_F/T=-0.019369369, delta_T=+40
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
s31_006_short_heavy: delta_F/T=-0.016823529, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.090454545, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.039121447, delta_T=-40
s31_033_burst_drain: delta_F/T=+0.022564103, delta_T=-20
s31_094_hotset_switching: delta_F/T=+0.021732831, delta_T=-60

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857248996; mean positive loss on worst 16 cases=0.028564068; max case loss=0.081203008; regressed cases=43; worst family delta F/T=-0.023258830. These are selection diagnostics; primary fitness remains mean F/T.


# Current program

Here is the current program we are trying to improve (you will need to propose a new program with the same inputs and outputs as the original program, but with improved internal implementation):

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
/*
NAME: adjacent_release_edge
DESCRIPTION:
Выбор между best-fit внутренней дырой и суффиксом сохраняет
прогноз одного insert, окно 512 insert и единичный prior длин 1..40.
При split дополнительно выбирается край размещения новой трубы.
Остаток оставляется рядом с соседом, удаление которого сильнее
уменьшит прогноз расширения следующего insert благодаря слиянию.
Учитываются внешние дыры и освобождение правого соседа на frontier.
Модель следующего delete равномерна по живым трубам; удаления
несоседних труб дают одинаковую стоимость для обоих краев.
При равной пользе сохраняется размещение слева.
Расширение выполняется только тогда, когда запрос нигде не помещается.
Сложность: O(log Q + 40) на insert, O(log Q) на delete, O(Q) памяти.
Возможная неудача: неравномерные lifetime и длинный горизонт
могут сделать предпочтительным другой край.
Ablation: preferRightEdge всегда возвращает false, остальные
индексы и правила остаются прежними.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using AddressIndex = std::map<int, int>;
    using SizeIndex = std::set<std::pair<int, int>>;
    AddressIndex freeByAddress_;
    SizeIndex freeBySize_;
    AddressIndex liveByAddress_;
    std::vector<Pipe> pipes_;
    int trenchLength_ = 0;
    int frontier_ = 0;
    std::array<int, 41> frequency_{};
    std::array<int, 41> massAbove_{};
    std::array<int, 512> recent_{};
    std::size_t recentCount_ = 0;
    std::size_t recentCursor_ = 0;
    void rememberLength(int length) {
        if (recentCount_ == recent_.size()) {
            --frequency_[recent_[recentCursor_]];
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            massAbove_[bound] =
                massAbove_[bound + 1] + frequency_[bound + 1];
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // ceil((length - suffixLength) / 20) не превосходит двух.
        // Расширение нужно лишь при length > largestHole.
        const int firstThreshold =
            std::min(40, std::max(largestHole, suffixLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, suffixLength + 20));
        return massAbove_[firstThreshold] + massAbove_[secondThreshold];
    }
    int largestHoleExcept(int firstStart, int secondStart) const {
        for (auto it = freeBySize_.rbegin(); it != freeBySize_.rend();
             ++it) {
            if (it->second != firstStart && it->second != secondStart) {
                return it->first;
            }
        }
        return 0;
    }
    bool preferRightEdge(int holeStart, int holeLength, int length) const {
        const int remainder = holeLength - length;
        const int suffixLength = trenchLength_ - frontier_;
        if (remainder == 0 || remainder >= 40 || suffixLength >= 40 ||
            largestHoleExcept(holeStart, -1) >= 40) {
            return false;
        }
        const auto right =
            liveByAddress_.lower_bound(holeStart + holeLength);
        const auto benefit = [&](AddressIndex::const_iterator neighbor,
                                 bool leftSide) {
            const int end = neighbor->first + neighbor->second;
            if (!leftSide && end == frontier_) {
                const int largest = largestHoleExcept(holeStart, -1);
                const int newSuffix = suffixLength + neighbor->second;
                return predictedGrowth(std::max(largest, remainder),
                                       newSuffix) -
                       predictedGrowth(largest, newSuffix + remainder);
            }
            int joinedLength = neighbor->second;
            int outerStart = -1;
            if (leftSide) {
                const auto next =
                    freeByAddress_.lower_bound(neighbor->first);
                if (next != freeByAddress_.begin()) {
                    const auto outer = std::prev(next);
                    if (outer->first + outer->second == neighbor->first) {
                        outerStart = outer->first;
                        joinedLength += outer->second;
                    }
                }
            } else {
                const auto outer = freeByAddress_.find(end);
                if (outer != freeByAddress_.end()) {
                    outerStart = outer->first;
                    joinedLength += outer->second;
                }
            }
            const int largest = largestHoleExcept(holeStart, outerStart);
            const int separateCost = predictedGrowth(
                std::max({largest, remainder, joinedLength}),
                suffixLength);
            const int joinedCost = predictedGrowth(
                std::max(largest, joinedLength + remainder),
                suffixLength);
            return separateCost - joinedCost;
        };
        int leftBenefit = 0;
        if (right != liveByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == holeStart) {
                leftBenefit = benefit(left, true);
            }
        }
        int rightBenefit = 0;
        if (right != liveByAddress_.end() &&
            right->first == holeStart + holeLength) {
            rightBenefit = benefit(right, false);
        }
        return leftBenefit > rightBenefit;
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        freeByAddress_.emplace(start, length);
        freeBySize_.emplace(length, start);
    }
    void eraseHole(AddressIndex::iterator it) {
        freeBySize_.erase(std::make_pair(it->second, it->first));
        freeByAddress_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        frequency_.fill(1);
        frequency_[0] = 0;
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
    }
    void place(int length) {
        rememberLength(length);
        const int suffixLength = trenchLength_ - frontier_;
        const auto fit = freeBySize_.lower_bound(
            std::make_pair(length, 0));
        bool useHole = fit != freeBySize_.end();
        if (useHole && suffixLength >= length) {
            const auto largest = std::prev(freeBySize_.end());
            const int largestBefore = largest->first;
            int largestAfter = largestBefore;
            if (fit == largest) {
                largestAfter = 0;
                if (largest != freeBySize_.begin()) {
                    largestAfter = std::prev(largest)->first;
                }
            }
            largestAfter = std::max(
                largestAfter, fit->first - length);
            const int holeCost =
                predictedGrowth(largestAfter, suffixLength);
            const int suffixCost =
                predictedGrowth(largestBefore, suffixLength - length);
            if (holeCost != suffixCost) {
                useHole = holeCost < suffixCost;
            } else {
                useHole = fit->first <= suffixLength;
            }
        }
        int start = 0;
        int sections = 0;
        if (useHole) {
            const int holeLength = fit->first;
            const int holeStart = fit->second;
            const bool atRight =
                preferRightEdge(holeStart, holeLength, length);
            start = atRight ? holeStart + holeLength - length : holeStart;
            eraseHole(freeByAddress_.find(holeStart));
            addHole(atRight ? holeStart : holeStart + length,
                    holeLength - length);
        } else {
            start = frontier_;
            const int shortage = start + length - trenchLength_;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ = start + length;
        }
        liveByAddress_.emplace(start, length);
        pipes_.push_back(Pipe{start, length});
        std::cout << sections << ' ' << start << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const Pipe old = pipes_[static_cast<std::size_t>(pid)];
        liveByAddress_.erase(old.start);
        int start = old.start;
        int length = old.length;
        const auto right = freeByAddress_.lower_bound(start);
        if (right != freeByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                eraseHole(left);
            }
        }
        if (right != freeByAddress_.end() &&
            start + length == right->first) {
            length += right->second;
            eraseHole(right);
        }
        if (start + length == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, length);
        }
        std::cout << old.start << '\n' << std::flush;
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

Here are the performance metrics of the program:

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.97; max_solver_rss_mib: 6.98

Here is additional text feedback about the current program:

Fitness F/T=0.858287246717; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737810540
family=short_phase_churn mean_F/T=0.784554472
family=geometric_cohorts mean_F/T=0.800531484
family=drifting_sizes mean_F/T=0.801751233
family=micro_size_shift mean_F/T=0.802083333
family=additive_cohorts mean_F/T=0.818063788
family=short_rounding mean_F/T=0.819122721
family=distribution_switch mean_F/T=0.827036790
family=short_heavy mean_F/T=0.827914946
family=tiny_churn mean_F/T=0.835116112
family=long_heavy mean_F/T=0.836628052
family=uniform_churn mean_F/T=0.836830051
family=size_biased_deletion mean_F/T=0.844329660
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.862822944
family=size_lifetimes mean_F/T=0.867824312
family=section_boundaries mean_F/T=0.877523186
family=fifo mean_F/T=0.879723940
family=large_live_set mean_F/T=0.880160636
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881582493
family=hotset_switching mean_F/T=0.882637249
family=bimodal mean_F/T=0.885740150
family=soft_recency_growth mean_F/T=0.896174241
family=burst_drain mean_F/T=0.907973080
family=serial_growth mean_F/T=0.914775317
family=long_prefill_recent mean_F/T=0.917733597
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920967907
family=drain_recovery mean_F/T=0.925996349
family=hotset_growth mean_F/T=0.949739969
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955498606
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001490 rss_mib=1.359
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001336 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001398 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001408 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001437 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001410 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611968048 F/B=0.646045362 B/T=0.947252445 overrun=0.055685 cpu_s=0.083591 rss_mib=1.734
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.614837303 F/B=0.675406191 B/T=0.910322279 overrun=0.098512 cpu_s=0.302444 rss_mib=1.906
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.319365 rss_mib=1.641
case=s31_060_large_live_set family=large_live_set F/T=0.631979015 F/B=0.641932619 B/T=0.984494317 overrun=0.015750 cpu_s=0.400448 rss_mib=2.672
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001511 rss_mib=1.328
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001442 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002793 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012562 rss_mib=1.438
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.016696 rss_mib=1.359
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.018591 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.329214 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.353157 rss_mib=1.672
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.319365 rss_mib=1.641
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.128573 rss_mib=1.719
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002810 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.702435065 F/B=0.865400000 B/T=0.811688312 overrun=0.232000 cpu_s=0.074618 rss_mib=1.438
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001685 rss_mib=1.359
case=s31_017_section_boundaries family=section_boundaries F/T=0.801020408 F/B=0.957317073 B/T=0.836734694 overrun=0.195122 cpu_s=0.030539 rss_mib=1.391
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002280 rss_mib=1.359
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.059331 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.114883 rss_mib=1.500
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821801347 F/B=0.950170316 B/T=0.864898990 overrun=0.156204 cpu_s=0.122127 rss_mib=1.578
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.333364 rss_mib=1.656
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.157216 rss_mib=2.438
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.018591 rss_mib=1.375
case=s31_039_distribution_switch family=distribution_switch F/T=0.831690141 F/B=0.952419355 B/T=0.873239437 overrun=0.145161 cpu_s=0.620492 rss_mib=1.875

PAIRED SEARCH EVIDENCE
Against parent gen7: delta mean F/T=+0.001732096; improved/regressed/tied=45/35/72.
family=size_biased_deletion delta_F/T=+0.019945165
family=section_boundaries delta_F/T=-0.011577380
family=short_rounding delta_F/T=+0.010901031
family=size_lifetimes delta_F/T=+0.008165700
family=drifting_sizes delta_F/T=+0.006377883
family=short_heavy delta_F/T=+0.006259442
Regressions:
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
s31_006_short_heavy: delta_F/T=-0.033000000, delta_T=+40
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
s31_055_additive_cohorts: delta_F/T=-0.016264850, delta_T=+20
Gains:
s31_063_size_biased_deletion: delta_F/T=+0.060079365, delta_T=-60
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.037446809, delta_T=-40

Against leader gen7: delta mean F/T=+0.001732096; improved/regressed/tied=45/35/72.
family=size_biased_deletion delta_F/T=+0.019945165
family=section_boundaries delta_F/T=-0.011577380
family=short_rounding delta_F/T=+0.010901031
family=size_lifetimes delta_F/T=+0.008165700
family=drifting_sizes delta_F/T=+0.006377883
family=short_heavy delta_F/T=+0.006259442
Regressions:
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
s31_006_short_heavy: delta_F/T=-0.033000000, delta_T=+40
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
s31_055_additive_cohorts: delta_F/T=-0.016264850, delta_T=+20
Gains:
s31_063_size_biased_deletion: delta_F/T=+0.060079365, delta_T=-60
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.037446809, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.858287247; mean positive loss on worst 16 cases=0.021022083; max case loss=0.052240461; regressed cases=39; worst family delta F/T=-0.018366579. These are selection diagnostics; primary fitness remains mean F/T.


# Task

Perform a cross-over between the code script above and the one below. Aim to combine the best parts of both code implementations that improves the score.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.

# Crossover Inspiration Programs
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
/*
NAME: Two-Future-Insert Bellman
DESCRIPTION:
Кандидаты — наименьший подходящий внутренний интервал и суффикс.
Выбор минимизирует ожидаемое суммарное расширение на две следующие
вставки без промежуточных удалений. Распределение фиксируется на время
прогноза: последние 512 insert и единичный prior для длин 1..40.
Для первой моделируемой вставки выбирается размещение с минимальным
ожидаемым расширением на второй; её длина заранее неизвестна.
Гистограмма внутренних интервалов учитывает их размеры и кратность.
Длины от 80 объединяются только в прогнозе: такого интервала достаточно
для любых двух запросов. Физические длины интервалов остаются точными.
При равенстве используются одношаговый прогноз и меньший интервал.
Расширение выполняется только тогда, когда запрос нигде не помещается.
Сложность: O(log Q + 40) на insert, O(log Q) на delete, O(Q) памяти.
Возможная неудача: удаления, корреляция длин и смена распределения
нарушают предположения прогноза.
Ablation: отключить сравнение двухшаговых оценок, сохранив одношаговый
прогноз, разрешение равенств и все вспомогательные индексы.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using AddressIndex = std::map<int, int>;
    using SizeIndex = std::set<std::pair<int, int>>;
    AddressIndex freeByAddress_;
    SizeIndex freeBySize_;
    std::array<int, 81> holeCount_{};
    std::vector<Pipe> pipes_;
    int trenchLength_ = 0;
    int frontier_ = 0;
    std::array<int, 41> frequency_{};
    std::array<int, 41> massAbove_{};
    std::array<int, 512> recent_{};
    std::size_t recentCount_ = 0;
    std::size_t recentCursor_ = 0;
    void rememberLength(int length) {
        if (recentCount_ == recent_.size()) {
            --frequency_[recent_[recentCursor_]];
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            massAbove_[bound] =
                massAbove_[bound + 1] + frequency_[bound + 1];
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // ceil((length - suffixLength) / 20) не превосходит двух.
        // Расширение нужно лишь при length > largestHole.
        const int firstThreshold =
            std::min(40, std::max(largestHole, suffixLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, suffixLength + 20));
        return massAbove_[firstThreshold] + massAbove_[secondThreshold];
    }
    std::int64_t predictedTwoGrowth(
        const std::array<int, 81>& counts, int suffixLength) const {
        // Either region can hold both future requests without growth.
        if (counts[80] != 0 || suffixLength >= 80) {
            return 0;
        }
        std::array<int, 41> bestFit{};
        int largest = 0;
        int second = 0;
        int nearest = 0;
        for (int size = 80; size >= 1; --size) {
            if (counts[size] != 0) {
                nearest = size;
                if (largest == 0) {
                    largest = size;
                    if (counts[size] >= 2) {
                        second = size;
                    }
                } else if (second == 0) {
                    second = size;
                }
            }
            if (size <= 40) {
                bestFit[size] = nearest;
            }
        }
        if (second >= 40 ||
            (largest >= 40 && suffixLength >= 40)) {
            return 0;
        }
        const int totalMass = massAbove_[0];
        std::int64_t cost = 0;
        for (int nextLength = 1; nextLength <= 40; ++nextLength) {
            const int fit = bestFit[nextLength];
            int nextCost = 0;
            if (fit != 0) {
                int largestAfter = largest;
                if (fit == largest && counts[fit] == 1) {
                    largestAfter = std::max(
                        second, fit - nextLength);
                }
                nextCost = predictedGrowth(
                    largestAfter, suffixLength);
                if (suffixLength >= nextLength) {
                    nextCost = std::min(
                        nextCost,
                        predictedGrowth(
                            largest, suffixLength - nextLength));
                }
            } else {
                int remaining = suffixLength - nextLength;
                int sections = 0;
                if (remaining < 0) {
                    sections = (-remaining + 19) / 20;
                    remaining += sections * 20;
                }
                nextCost = sections * totalMass +
                    predictedGrowth(largest, remaining);
            }
            cost += static_cast<std::int64_t>(
                frequency_[nextLength]) * nextCost;
        }
        // Common denominator: totalMass squared.
        return cost;
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        freeByAddress_.emplace(start, length);
        freeBySize_.emplace(length, start);
        ++holeCount_[std::min(80, length)];
    }
    void eraseHole(AddressIndex::iterator it) {
        --holeCount_[std::min(80, it->second)];
        freeBySize_.erase(std::make_pair(it->second, it->first));
        freeByAddress_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        frequency_.fill(1);
        frequency_[0] = 0;
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
    }
    void place(int length) {
        rememberLength(length);
        const int suffixLength = trenchLength_ - frontier_;
        const auto fit = freeBySize_.lower_bound(
            std::make_pair(length, 0));
        bool useHole = fit != freeBySize_.end();
        if (useHole && suffixLength >= length) {
            const auto largest = std::prev(freeBySize_.end());
            const int largestBefore = largest->first;
            int largestAfter = largestBefore;
            if (fit == largest) {
                largestAfter = 0;
                if (largest != freeBySize_.begin()) {
                    largestAfter = std::prev(largest)->first;
                }
            }
            largestAfter = std::max(
                largestAfter, fit->first - length);
            const int holeCost =
                predictedGrowth(largestAfter, suffixLength);
            const int suffixCost =
                predictedGrowth(largestBefore, suffixLength - length);
            auto afterHole = holeCount_;
            --afterHole[std::min(80, fit->first)];
            const int remainder = fit->first - length;
            if (remainder > 0) {
                ++afterHole[std::min(80, remainder)];
            }
            const std::int64_t holeTwoCost =
                predictedTwoGrowth(afterHole, suffixLength);
            const std::int64_t suffixTwoCost =
                predictedTwoGrowth(holeCount_, suffixLength - length);
            if (holeTwoCost != suffixTwoCost) {
                useHole = holeTwoCost < suffixTwoCost;
            } else if (holeCost != suffixCost) {
                useHole = holeCost < suffixCost;
            } else {
                useHole = fit->first <= suffixLength;
            }
        }
        int start = 0;
        int sections = 0;
        if (useHole) {
            const int holeLength = fit->first;
            start = fit->second;
            eraseHole(freeByAddress_.find(start));
            addHole(start + length, holeLength - length);
        } else {
            start = frontier_;
            const int shortage = start + length - trenchLength_;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ = start + length;
        }
        pipes_.push_back(Pipe{start, length});
        std::cout << sections << ' ' << start << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const Pipe old = pipes_[static_cast<std::size_t>(pid)];
        int start = old.start;
        int length = old.length;
        const auto right = freeByAddress_.lower_bound(start);
        if (right != freeByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                eraseHole(left);
            }
        }
        if (right != freeByAddress_.end() &&
            start + length == right->first) {
            length += right->second;
            eraseHole(right);
        }
        if (start + length == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, length);
        }
        std::cout << old.start << '\n' << std::flush;
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

Performance metrics: Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 2.64


