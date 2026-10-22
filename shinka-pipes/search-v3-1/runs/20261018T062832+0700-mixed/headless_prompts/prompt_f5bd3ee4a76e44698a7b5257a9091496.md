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
Independent 1: attempts=1; score_range=0.856788966..0.856788966
gen4 Independent 1; correct=True; parent=None; delta_F/T=n/a; claim=Independent task-only implementation
  improved/regressed/tied=47/38/67
  regression s31_039_distribution_switch: delta_F/T=-0.049653143
  regression s31_062_size_biased_deletion: delta_F/T=-0.047931605
HISTORICAL SEARCH-v2 (different inputs AND B/T objective; not a v3.1 ranking):
LINEAGE PARENT: mode=lineage-local-score; lineage=4; local mean leader=0.856788966; fixed-baseline tail loss=0.028571895; maximum case loss=0.049653143.
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
/*
NAME: Causal Rate-Oriented Best Fit
DESCRIPTION:
Выбирается минимальный подходящий свободный интервал; при равенстве —
интервал с меньшей координатой. Соседние свободные интервалы объединяются.
При отсутствии подходящего интервала расширяется свободный хвост, причем
добавляется только необходимое число секций.
Для каждого length оценивается частота удалений на единицу времени жизни
pipe. История экспоненциально затухает; оценки сглаживаются общей частотой.
При разбиении внутреннего интервала остаток оставляется рядом с соседом,
который, согласно этой оценке, скорее освободится. Это помогает последующему
объединению свободного места. При слабых данных используется левый край.
Сложность команды: O(40 + log(H + 1)), H — число свободных интервалов.
Память: O(Q), Q — число команд. Расширение за вставку не превышает 40 метров,
поэтому при заданном ограничении команд T не превысит 8000000 метров.
Возможный недостаток: best fit может создавать мелкие фрагменты, а связь
между length и временем жизни может отсутствовать или быстро меняться.
Ablation: заставить preferRight() всегда возвращать false, сохранив
остальной алгоритм, и сравнить влияние выбора края.
*/
class Allocator {
    struct Node {
        int start;
        int length;
        int previous;
        int next;
        int pid;
    };
    struct FreeKey {
        int length;
        int start;
        int node;
    };
    struct FreeOrder {
        bool operator()(const FreeKey& a, const FreeKey& b) const {
            if (a.length != b.length) return a.length < b.length;
            if (a.start != b.start) return a.start < b.start;
            return a.node < b.node;
        }
    };
    // Node 0 is the sentinel of the physical interval list.
    std::vector<Node> nodes_;
    std::vector<int> pidNode_;
    std::set<FreeKey, FreeOrder> freeBySize_;
    std::array<int, 41> liveByLength_{};
    std::array<double, 41> exposure_{};
    std::array<double, 41> deaths_{};
    int liveCount_ = 0;
    int trenchLength_ = 0;
    double totalExposure_ = 0.0;
    double totalDeaths_ = 0.0;
    void advanceHistory() {
        // Effective history length is approximately 4000 commands.
        constexpr double decay = 0.99975;
        for (int length = 1; length <= 40; ++length) {
            exposure_[length] =
                decay * exposure_[length] + liveByLength_[length];
            deaths_[length] *= decay;
        }
        totalExposure_ = decay * totalExposure_ + liveCount_;
        totalDeaths_ *= decay;
    }
    int linkBetween(int previous, int next, int start, int length, int pid) {
        const int id = static_cast<int>(nodes_.size());
        nodes_.push_back(Node{start, length, previous, next, pid});
        nodes_[previous].next = id;
        nodes_[next].previous = id;
        return id;
    }
    void indexFree(int id) {
        freeBySize_.insert(
            FreeKey{nodes_[id].length, nodes_[id].start, id});
    }
    void unindexFree(int id) {
        freeBySize_.erase(
            FreeKey{nodes_[id].length, nodes_[id].start, id});
    }
    bool preferRight(int hole) const {
        const int left = nodes_[hole].previous;
        const int right = nodes_[hole].next;
        // Boundary holes are filled from their left edge.
        if (left == 0 || right == 0 || totalDeaths_ < 12.0) {
            return false;
        }
        if (nodes_[left].pid <= 0 || nodes_[right].pid <= 0) {
            return false;
        }
        const int leftLength = nodes_[left].length;
        const int rightLength = nodes_[right].length;
        if (leftLength == rightLength) return false;
        // Three pseudo-events shrink each estimate toward the global rate.
        constexpr double priorEvents = 3.0;
        const double priorExposure =
            priorEvents * (totalExposure_ + 1.0) / (totalDeaths_ + 1.0);
        const double leftNumerator = deaths_[leftLength] + priorEvents;
        const double rightNumerator = deaths_[rightLength] + priorEvents;
        const double leftDenominator = exposure_[leftLength] + priorExposure;
        const double rightDenominator = exposure_[rightLength] + priorExposure;
        // Place against the right neighbor when the left neighbor has a
        // sufficiently higher estimated deletion rate.
        return leftNumerator * rightDenominator >
               1.25 * rightNumerator * leftDenominator;
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        nodes_.reserve(400001);
        pidNode_.reserve(200001);
        nodes_.push_back(Node{0, 0, 0, 0, -1});
        pidNode_.push_back(0);
    }
    void place(int length) {
        advanceHistory();
        int sections = 0;
        int hole = 0;
        const auto fit =
            freeBySize_.lower_bound(FreeKey{length, -1, -1});
        if (fit != freeBySize_.end()) {
            hole = fit->node;
            freeBySize_.erase(fit);
        } else {
            const int tail = nodes_[0].previous;
            const bool freeTail = tail != 0 && nodes_[tail].pid == 0;
            const int available = freeTail ? nodes_[tail].length : 0;
            sections = (length - available + 19) / 20;
            const int added = sections * 20;
            if (freeTail) {
                unindexFree(tail);
                nodes_[tail].length += added;
                hole = tail;
            } else {
                hole = linkBetween(tail, 0, trenchLength_, added, 0);
            }
            trenchLength_ += added;
        }
        const int pid = static_cast<int>(pidNode_.size());
        const int originalStart = nodes_[hole].start;
        const int remainder = nodes_[hole].length - length;
        const int previous = nodes_[hole].previous;
        const int next = nodes_[hole].next;
        const bool fromRight = remainder > 0 && preferRight(hole);
        nodes_[hole].pid = pid;
        nodes_[hole].length = length;
        if (fromRight) {
            nodes_[hole].start = originalStart + remainder;
            const int freeNode =
                linkBetween(previous, hole, originalStart, remainder, 0);
            indexFree(freeNode);
        } else if (remainder > 0) {
            const int freeNode =
                linkBetween(hole, next, originalStart + length, remainder, 0);
            indexFree(freeNode);
        }
        pidNode_.push_back(hole);
        ++liveByLength_[length];
        ++liveCount_;
        std::cout << sections << ' ' << nodes_[hole].start
                  << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        advanceHistory();
        const std::size_t ordinal = static_cast<std::size_t>(pid);
        const int id = pidNode_[ordinal];
        const int originalStart = nodes_[id].start;
        const int length = nodes_[id].length;
        deaths_[length] += 1.0;
        totalDeaths_ += 1.0;
        --liveByLength_[length];
        --liveCount_;
        pidNode_[ordinal] = 0;
        nodes_[id].pid = 0;
        const int left = nodes_[id].previous;
        if (left != 0 && nodes_[left].pid == 0) {
            unindexFree(left);
            const int previous = nodes_[left].previous;
            nodes_[id].start = nodes_[left].start;
            nodes_[id].length += nodes_[left].length;
            nodes_[id].previous = previous;
            nodes_[previous].next = id;
        }
        const int right = nodes_[id].next;
        if (right != 0 && nodes_[right].pid == 0) {
            unindexFree(right);
            const int next = nodes_[right].next;
            nodes_[id].length += nodes_[right].length;
            nodes_[id].next = next;
            nodes_[next].previous = id;
        }
        indexFree(id);
        std::cout << originalStart << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 3.36

Here is additional text feedback about the current program:

Fitness F/T=0.856788965701; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737107573
family=short_phase_churn mean_F/T=0.781231752
family=drifting_sizes mean_F/T=0.793500998
family=geometric_cohorts mean_F/T=0.798323304
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.808221691
family=short_heavy mean_F/T=0.811227939
family=size_biased_deletion mean_F/T=0.817199482
family=additive_cohorts mean_F/T=0.821584765
family=distribution_switch mean_F/T=0.826390617
family=tiny_churn mean_F/T=0.838214135
family=uniform_churn mean_F/T=0.840288372
family=long_heavy mean_F/T=0.843025658
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847680628
family=size_lifetimes mean_F/T=0.858571370
family=serial_churn mean_F/T=0.859817359
family=large_live_set mean_F/T=0.878184081
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882217753
family=bimodal mean_F/T=0.883426645
family=hotset_switching mean_F/T=0.884504821
family=fifo mean_F/T=0.886852097
family=section_boundaries mean_F/T=0.890204893
family=soft_recency_growth mean_F/T=0.895823727
family=burst_drain mean_F/T=0.898159849
family=serial_growth mean_F/T=0.915959275
family=long_prefill_recent mean_F/T=0.917906629
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920954623
family=drain_recovery mean_F/T=0.925315775
family=hotset_growth mean_F/T=0.949616362
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955889903
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001577 rss_mib=1.391
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001477 rss_mib=1.391
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001348 rss_mib=1.391
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001544 rss_mib=1.391
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001460 rss_mib=1.391
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001413 rss_mib=1.391
case=s31_118_partial_drain family=partial_drain F/T=0.610370879 F/B=0.646045362 B/T=0.944780220 overrun=0.058447 cpu_s=0.081288 rss_mib=1.625
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618496476 F/B=0.675406191 B/T=0.915740016 overrun=0.092013 cpu_s=0.409338 rss_mib=1.781
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.339425 rss_mib=2.047
case=s31_060_large_live_set family=large_live_set F/T=0.632015856 F/B=0.641932619 B/T=0.984551708 overrun=0.015691 cpu_s=0.394868 rss_mib=2.250
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001356 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001348 rss_mib=1.391
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.005168 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012219 rss_mib=1.422
case=s31_040_distribution_switch family=distribution_switch F/T=0.657762557 F/B=0.692548077 B/T=0.949771689 overrun=0.052885 cpu_s=0.017051 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.004595 rss_mib=1.406
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.331172 rss_mib=2.094
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.682492114 F/B=0.865400000 B/T=0.788643533 overrun=0.268000 cpu_s=0.076894 rss_mib=1.516
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.122464 rss_mib=1.734
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.004595 rss_mib=1.406
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.339425 rss_mib=2.047
case=s31_009_long_heavy family=long_heavy F/T=0.775423729 F/B=0.953125000 B/T=0.813559322 overrun=0.229167 cpu_s=0.356598 rss_mib=2.188
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.825000000 F/B=0.990000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.047786 rss_mib=1.453
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001684 rss_mib=1.406
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002304 rss_mib=1.406
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.806122449 F/B=0.954682779 B/T=0.844387755 overrun=0.184290 cpu_s=0.037210 rss_mib=1.438
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.059137 rss_mib=1.469
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.525475 rss_mib=2.172
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.119839 rss_mib=1.609
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.825623679 F/B=0.950170316 B/T=0.868921776 overrun=0.150852 cpu_s=0.125743 rss_mib=1.734
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.853914860 F/B=0.982097589 B/T=0.869480660 overrun=0.150112 cpu_s=0.173391 rss_mib=2.062
case=s31_086_tiny_churn family=tiny_churn F/T=0.836466165 F/B=0.959051724 B/T=0.872180451 overrun=0.146552 cpu_s=0.168796 rss_mib=1.484

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.001807758; improved/regressed/tied=47/38/67.
family=fifo delta_F/T=+0.055842716
family=tiny_churn delta_F/T=+0.053210469
family=size_biased_deletion delta_F/T=-0.027960122
family=short_heavy delta_F/T=+0.027520597
family=distribution_switch delta_F/T=-0.019012753
family=additive_cohorts delta_F/T=+0.014221332
Regressions:
s31_039_distribution_switch: delta_F/T=-0.049653143, delta_T=+80
s31_062_size_biased_deletion: delta_F/T=-0.047931605, delta_T=+440
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
Gains:
s31_024_fifo: delta_F/T=+0.130986590, delta_T=-300
s31_086_tiny_churn: delta_F/T=+0.118724230, delta_T=-440
s31_006_short_heavy: delta_F/T=+0.101521298, delta_T=-140
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.856788966; mean positive loss on worst 16 cases=0.028571895; max case loss=0.049653143; regressed cases=38; worst family delta F/T=-0.027960122. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
