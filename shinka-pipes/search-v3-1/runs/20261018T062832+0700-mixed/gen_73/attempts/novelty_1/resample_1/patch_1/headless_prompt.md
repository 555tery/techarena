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

**Согласуйте политику внутри rollout с успешной оценкой вместимости.** В `projectedGrowth()` сравнивайте Best-Fit со следующим большим подходящим размером по текущим `splitPenalty()` и `scarcityAllowsExchange()`, вычисляя scarcity из симулируемых корзин с учётом хвоста. Сохраните горизонт, сценарии и правило строгого выигрыша относительно fallback: эта отдельная мутация проверит пользу более точной модели последующих размещений без увеличения глубины прогноза.

RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Same complete saved trench vector: generations [9, 38, 55]. Advisory only, not equivalence.
Same complete saved trench vector: generations [14, 67]. Advisory only, not equivalence.
Same complete saved trench vector: generations [30, 70]. Advisory only, not equivalence.
appendable_wilderness: attempts=2; score_range=0.854861671..0.855164355
Best-Fit: attempts=1; score_range=0.857332383..0.857332383
First-Fit: attempts=1; score_range=0.847432251..0.847432251
Independent 1: attempts=1; score_range=0.856788966..0.856788966
Independent 2: attempts=1; score_range=0.857536047..0.857536047
Independent 3: attempts=1; score_range=0.857564053..0.857564053
Independent 4: attempts=1; score_range=0.856555151..0.856555151
SEARCH-v2 generation 27: attempts=1; score_range=0.855381088..0.855381088
adjacent_release_edge: attempts=1; score_range=0.858287247..0.858287247
age_conditioned_neighbor_release: attempts=1; score_range=0.854363465..0.854363465
age_conditioned_release_edge: attempts=1; score_range=0.848500142..0.848500142
appendable_wilderness_single_front: attempts=1; score_range=0.854469278..0.854469278
gen0 initial_program; correct=True; parent=None; delta_F/T=n/a; claim=Initial program setup
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen71 guarded_quantile_bridge; correct=True; parent=45; delta_F/T=+0.000000000; claim=Добавляется один механизм: поиск промежуточной дыры, способной после текущего размещения вместить крупный прогнозируемый запрос.
Пусть q — квантиль 13/16 существующей модели длин. Если остатки двух минимальных подходящих
  improved/regressed/tied=0/0/152
gen70 causal_pair_commitment; correct=True; parent=22; delta_F/T=-0.000220957; claim=Один механизм: causal Bellman pricing для пары будущих вставок. Сохраняется основа родителя gen22: best fit, Markov-профиль длин и сравнение внутреннего интервала со свободным хвостом.
Родитель оценивает совместную вмест
  improved/regressed/tied=10/13/129
  regression s31_122_short_rounding: delta_F/T=-0.042631579
  regression s31_033_burst_drain: delta_F/T=-0.022564103
gen69 scarce_capacity_exchange; correct=True; parent=24; delta_F/T=-0.000957521; claim=Предлагаю учитывать дефицит свободной вместимости при сравнении родительской дыры с Best-Fit. Для каждого размера k поддерживается C[k] — количество труб размера k, помещающихся в текущие свободные интервалы, включая уже
  improved/regressed/tied=20/29/103
  regression s31_039_distribution_switch: delta_F/T=-0.046892992
  regression s31_063_size_biased_deletion: delta_F/T=-0.040963203
gen68 scarcity_weighted_coalescence; correct=True; parent=0; delta_F/T=-0.000801127; claim=Предлагаю один исследуемый механизм: дополнительную премию за слияние остатка с освобождаемым соседом, нормированную на число альтернативных подходящих дыр.
Для остатка r и освобождаемого участка a учитываются только раз
  improved/regressed/tied=37/47/68
  regression s31_086_tiny_churn: delta_F/T=-0.085639663
  regression s31_085_tiny_churn: delta_F/T=-0.041403162
gen67 zero_growth_tail_exchange; correct=True; parent=6; delta_F/T=-0.000318501; claim=Один механизм: выбор между внутренней дырой, найденной родителем, и уже выделенным хвостом по ожидаемой стоимости одной следующей вставки.
Если текущая труба помещается в хвост без расширения, сравниваются два состояния:
  improved/regressed/tied=23/28/101
  regression s31_008_short_heavy: delta_F/T=-0.047813195
  regression s31_049_geometric_cohorts: delta_F/T=-0.039689922
gen66 dual_strata_growth_gate; correct=True; parent=52; delta_F/T=-0.000752429; claim=Предлагаю проверять устойчивость короткого прогноза перед изменением родительского выбора между внутренним отверстием и хвостом. Оба размещения уже должны вмещать текущую трубу.
Механизм развивае
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=robust; specialist families=[]; fixed-baseline tail loss=0.000000000; maximum case loss=0.000000000. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
NAME: tail_growth_regret
DESCRIPTION:
Исходный выбор — минимальный подходящий свободный интервал; при равенстве —
интервал с меньшей координатой. Если выбран хвост, рассматривается также
минимальный подходящий внутренний интервал. Он используется только при
строго меньшем ожидаемом росте для следующей вставки. Прогноз учитывает
все свободные интервалы и затухающую историю наблюдавшихся длин вставок
с одним равномерным псевдонаблюдением на каждую длину.
Соседние свободные интервалы объединяются.
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
Возможный недостаток: прогноз следующей вставки не учитывает промежуточные
удаления и может запаздывать при смене распределения длин.
Ablation: chooseFit() возвращает только исходный lower_bound, сохраняя
сбор истории, preferRight() и остальной алгоритм.
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
    std::array<double, 41> requestMass_{};
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
            requestMass_[length] *= decay;
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
    auto chooseFit(int length) const {
        const auto fit =
            freeBySize_.lower_bound(FreeKey{length, -1, -1});
        if (fit == freeBySize_.end() ||
            fit->node != nodes_[0].previous) {
            return fit;
        }
        // There is only one physical tail, so the next fit is internal.
        const auto interior = std::next(fit);
        if (interior == freeBySize_.end()) return fit;
        int otherMaximum = 0;
        for (auto it = freeBySize_.rbegin();
             it != freeBySize_.rend(); ++it) {
            if (it->node != fit->node && it->node != interior->node) {
                otherMaximum = it->length;
                break;
            }
        }
        const int tailLength = fit->length;
        const int tailAfter = tailLength - length;
        const int bestMaximum =
            std::max(otherMaximum, interior->length);
        // Best fit already accommodates every possible next length.
        if (bestMaximum >= 40) return fit;
        const int interiorMaximum = std::max(
            std::max(otherMaximum, tailLength),
            interior->length - length);
        double advantage = 0.0;
        for (int request = 1; request <= 40; ++request) {
            const int bestGrowth = request <= bestMaximum
                ? 0 : (request - tailAfter + 19) / 20;
            const int interiorGrowth = request <= interiorMaximum
                ? 0 : (request - tailLength + 19) / 20;
            advantage += (1.0 + requestMass_[request]) *
                         (bestGrowth - interiorGrowth);
        }
        return advantage > 0.0 ? interior : fit;
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
        requestMass_[length] += 1.0;
        int sections = 0;
        int hole = 0;
        const auto fit = chooseFit(length);
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.89; max_solver_rss_mib: 3.81

Text feedback:
Fitness F/T=0.857525343555; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737339195
family=short_phase_churn mean_F/T=0.785232978
family=drifting_sizes mean_F/T=0.800024211
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.807517634
family=short_rounding mean_F/T=0.808221691
family=short_heavy mean_F/T=0.814350488
family=additive_cohorts mean_F/T=0.820416195
family=distribution_switch mean_F/T=0.823890553
family=size_biased_deletion mean_F/T=0.826037208
family=uniform_churn mean_F/T=0.829072532
family=tiny_churn mean_F/T=0.833601270
family=long_heavy mean_F/T=0.844208389
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.848217942
family=serial_churn mean_F/T=0.856415740
family=size_lifetimes mean_F/T=0.865589657
family=large_live_set mean_F/T=0.879694760
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882497286
family=bimodal mean_F/T=0.884331046
family=fifo mean_F/T=0.886553656
family=hotset_switching mean_F/T=0.889051197
family=section_boundaries mean_F/T=0.890568126
family=soft_recency_growth mean_F/T=0.896503496
family=burst_drain mean_F/T=0.902328478
family=serial_growth mean_F/T=0.916001614
family=long_prefill_recent mean_F/T=0.917865626
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921027007
family=drain_recovery mean_F/T=0.923883192
family=hotset_growth mean_F/T=0.949599715
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955343554
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001624 rss_mib=1.391
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001462 rss_mib=1.391
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001429 rss_mib=1.391
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001563 rss_mib=1.391
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001379 rss_mib=1.391
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001438 rss_mib=1.391
case=s31_118_partial_drain family=partial_drain F/T=0.610538610 F/B=0.646045362 B/T=0.945039846 overrun=0.058156 cpu_s=0.082049 rss_mib=1.625
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618496476 F/B=0.675406191 B/T=0.915740016 overrun=0.092013 cpu_s=0.289912 rss_mib=2.000
case=s31_060_large_live_set family=large_live_set F/T=0.632310743 F/B=0.641932619 B/T=0.985011081 overrun=0.015217 cpu_s=0.383974 rss_mib=2.219
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001402 rss_mib=1.391
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.311055 rss_mib=2.047
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001335 rss_mib=1.391
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003587 rss_mib=1.406
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.016607 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012470 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002961 rss_mib=1.406
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.682492114 F/B=0.865400000 B/T=0.788643533 overrun=0.268000 cpu_s=0.073330 rss_mib=1.516
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.331048 rss_mib=2.094
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.754489051 F/B=0.950045956 B/T=0.794160584 overrun=0.259191 cpu_s=0.123171 rss_mib=1.750
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002961 rss_mib=1.406
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.044336 rss_mib=1.453
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.311055 rss_mib=2.047
case=s31_009_long_heavy family=long_heavy F/T=0.775423729 F/B=0.953125000 B/T=0.813559322 overrun=0.229167 cpu_s=0.353662 rss_mib=2.188
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001693 rss_mib=1.406
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002241 rss_mib=1.406
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.802030457 F/B=0.954682779 B/T=0.840101523 overrun=0.190332 cpu_s=0.035192 rss_mib=1.438
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.034735 rss_mib=1.453
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.116542 rss_mib=1.484
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.516860 rss_mib=2.172
case=s31_102_serial_churn family=serial_churn F/T=0.820923913 F/B=0.950000000 B/T=0.864130435 overrun=0.157233 cpu_s=0.146850 rss_mib=1.688
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.330320 rss_mib=1.703
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.825623679 F/B=0.950170316 B/T=0.868921776 overrun=0.150852 cpu_s=0.117866 rss_mib=1.719

PAIRED SEARCH EVIDENCE
Against parent gen4: delta mean F/T=+0.000736378; improved/regressed/tied=29/29/94.
family=uniform_churn delta_F/T=-0.011215840
family=geometric_cohorts delta_F/T=+0.009194330
family=size_biased_deletion delta_F/T=+0.008837725
family=size_lifetimes delta_F/T=+0.007018286
family=drifting_sizes delta_F/T=+0.006523213
family=tiny_churn delta_F/T=-0.004612865
Regressions:
s31_001_uniform_churn: delta_F/T=-0.039774859, delta_T=+40
s31_086_tiny_churn: delta_F/T=-0.018451460, delta_T=+60
s31_006_short_heavy: delta_F/T=-0.016176471, delta_T=+20
s31_102_serial_churn: delta_F/T=-0.013606474, delta_T=+60
Gains:
s31_049_geometric_cohorts: delta_F/T=+0.039689922, delta_T=-40
s31_063_size_biased_deletion: delta_F/T=+0.039121447, delta_T=-40
s31_008_short_heavy: delta_F/T=+0.028666667, delta_T=-60
s31_041_drifting_sizes: delta_F/T=+0.023199023, delta_T=-40

Against leader gen4: delta mean F/T=+0.000736378; improved/regressed/tied=29/29/94.
family=uniform_churn delta_F/T=-0.011215840
family=geometric_cohorts delta_F/T=+0.009194330
family=size_biased_deletion delta_F/T=+0.008837725
family=size_lifetimes delta_F/T=+0.007018286
family=drifting_sizes delta_F/T=+0.006523213
family=tiny_churn delta_F/T=-0.004612865
Regressions:
s31_001_uniform_churn: delta_F/T=-0.039774859, delta_T=+40
s31_086_tiny_churn: delta_F/T=-0.018451460, delta_T=+60
s31_006_short_heavy: delta_F/T=-0.016176471, delta_T=+20
s31_102_serial_churn: delta_F/T=-0.013606474, delta_T=+60
Gains:
s31_049_geometric_cohorts: delta_F/T=+0.039689922, delta_T=-40
s31_063_size_biased_deletion: delta_F/T=+0.039121447, delta_T=-40
s31_008_short_heavy: delta_F/T=+0.028666667, delta_T=-60
s31_041_drifting_sizes: delta_F/T=+0.023199023, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857525344; mean positive loss on worst 16 cases=0.026866513; max case loss=0.052023597; regressed cases=36; worst family delta F/T=-0.021512816. These are selection diagnostics; primary fitness remains mean F/T.

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
namespace {
using Coordinate = std::int64_t;
class Allocator {
    static constexpr bool packingEnabled_ = true;
    static constexpr int packingCap_ = 120;
    static constexpr int scenarioCount_ = 8;
    struct Pipe {
        Coordinate start;
        int length;
    };
    struct Placement {
        Coordinate at = -1;
        bool rightAligned = false;
    };
    // A simulated horizon consumes at most 120 units. Larger gaps can
    // therefore share one bucket after the current placement is applied.
    struct PackingProfile {
        std::array<std::uint32_t, packingCap_ + 1> count{};
        std::array<std::uint64_t, 2> nonempty{};
        static int bucket(Coordinate length) {
            return static_cast<int>(
                std::min<Coordinate>(packingCap_, length));
        }
        void add(Coordinate length) {
            if (length <= 0) return;
            const int k = bucket(length);
            ++count[k];
            nonempty[(k - 1) / 64] |=
                std::uint64_t{1} << ((k - 1) % 64);
        }
        void take(Coordinate length) {
            if (length <= 0) return;
            const int k = bucket(length);
            if (--count[k] == 0) {
                nonempty[(k - 1) / 64] &=
                    ~(std::uint64_t{1} << ((k - 1) % 64));
            }
        }
        int firstFit(int length) const {
            if (length <= 0 || length > packingCap_) return 0;
            int word = (length - 1) / 64;
            std::uint64_t bits = nonempty[word] &
                (~std::uint64_t{0} << ((length - 1) % 64));
            if (bits == 0 && word == 0) {
                word = 1;
                bits = nonempty[1];
            }
            if (bits == 0) return 0;
            return word * 64 +
                static_cast<int>(std::countr_zero(bits)) + 1;
        }
    };
    struct Scenario {
        std::array<int, 3> lengths{};
        int volume = 0;
    };
    using Scenarios = std::array<Scenario, scenarioCount_>;
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    PackingProfile packingProfile_;
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
        const double pooledRate =
            totalDeaths_ / (totalExposure_ + 1.0);
        return (deaths_[length] + 8.0 * pooledRate) /
               (exposure + 8.0);
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
            if (demand_[k] != 0 && space % k < length % k) {
                result +=
                    static_cast<std::uint64_t>(demand_[k]) * k;
            }
        }
        return result;
    }
    bool scarcityAllowsExchange(
        Coordinate smaller, Coordinate larger, int length) const {
        std::size_t fittingGaps = 0;
        long double extraLoss = 0;
        for (int k = 40; k >= 1; --k) {
            fittingGaps += starts_[k].size();
            if (demand_[k] == 0 || fittingGaps == 0) continue;
            const int smallerLoses =
                smaller >= k && smaller - length < k;
            const int largerLoses =
                larger >= k && larger - length < k;
            if (smallerLoses != largerLoses) {
                extraLoss +=
                    static_cast<long double>(demand_[k]) /
                    static_cast<long double>(fittingGaps) *
                    (largerLoses - smallerLoses);
            }
        }
        return extraLoss <= 0;
    }
    double releaseGain(
        Coordinate a, Coordinate remainder, bool rightAligned,
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
                if (outside->second == p.start) {
                    releasedSpace +=
                        outside->second - outside->first;
                }
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end()) {
                releasedSpace += outside->second - outside->first;
            }
        }
        const int before = static_cast<int>(
            std::min<Coordinate>(
                40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(
            std::min<Coordinate>(40, remainder + releasedSpace));
        if (before == after) return 0;
        return releaseRate(p.length) *
            static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(
        int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        }
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
                const double score =
                    releaseGain(a, remainder, side != 0, prefix);
                if (score > best) {
                    best = score;
                    at = a;
                    rightAligned = side != 0;
                }
            }
        }
    }
    Scenarios buildScenarios() const {
        // One uniform pseudo-observation per possible request length.
        const std::uint32_t mass = demandMass_ + 40;
        std::array<int, scenarioCount_> quantiles{};
        int length = 1;
        std::uint32_t cumulative = demand_[1] + 1;
        for (int i = 0; i < scenarioCount_; ++i) {
            const std::uint32_t target =
                static_cast<std::uint32_t>(
                    (static_cast<std::uint64_t>(2 * i + 1) * mass) /
                    (2 * scenarioCount_));
            while (length < 40 && cumulative <= target) {
                ++length;
                cumulative += demand_[length] + 1;
            }
            quantiles[i] = length;
        }
        // Each horizon position uses every marginal stratum once.
        Scenarios scenarios{};
        for (int i = 0; i < scenarioCount_; ++i) {
            scenarios[i].lengths = {
                quantiles[i],
                quantiles[(3 * i + 1) % scenarioCount_],
                quantiles[(5 * i + 2) % scenarioCount_]
            };
            for (int request : scenarios[i].lengths) {
                scenarios[i].volume += request;
            }
        }
        return scenarios;
    }
    int projectedGrowth(
        const Placement& placement, int length,
        const PackingProfile& interior,
        Coordinate tailStart, Coordinate tailSpace,
        const Scenarios& scenarios, int cutoff) const {
        PackingProfile after = interior;
        Coordinate remainingTail = tailSpace;
        if (placement.at == tailStart) {
            remainingTail -= length;
        } else {
            const Coordinate space =
                gaps_.at(placement.at) - placement.at;
            after.take(space);
            after.add(space - length);
        }
        const int initialTail = static_cast<int>(
            std::min<Coordinate>(packingCap_, remainingTail));
        int totalGrowth = 0;
        for (const Scenario& scenario : scenarios) {
            // One gap holding the entire remaining volume guarantees
            // zero growth under insertion-only Best-Fit.
            if (initialTail >= scenario.volume ||
                after.firstFit(scenario.volume) != 0) {
                continue;
            }
            PackingProfile simulated = after;
            int tail = initialTail;
            for (int request : scenario.lengths) {
                const int fit = simulated.firstFit(request);
                // The physical tail has the largest address, so an
                // equal-sized interior fit wins the Best-Fit tie.
                if (fit != 0 &&
                    (tail < request || fit <= tail)) {
                    simulated.take(fit);
                    simulated.add(fit - request);
                } else if (tail >= request) {
                    tail -= request;
                } else {
                    const int sections =
                        (request - tail + 19) / 20;
                    totalGrowth += sections;
                    tail += sections * 20 - request;
                }
            }
            // All remaining contributions are nonnegative.
            if (totalGrowth >= cutoff) return totalGrowth;
        }
        return totalGrowth;
    }
    Placement choosePlacement(int length) const {
        const auto first = sizes_.lower_bound({length, 0});
        if (first == sizes_.end()) return {};
        const auto nextSize = sizes_.upper_bound(
            {first->first, std::numeric_limits<Coordinate>::max()});
        auto candidate = first;
        // Preserve the parent's complete decision as the fallback.
        if (candidate->first > length) {
            const auto penalty =
                splitPenalty(candidate->first, length);
            if (penalty != 0 && nextSize != sizes_.end() &&
                splitPenalty(nextSize->first, length) < penalty &&
                scarcityAllowsExchange(
                    candidate->first, nextSize->first, length)) {
                candidate = nextSize;
            }
        }
        Placement fallback{candidate->second, false};
        selectReleasePlacement(
            length, fallback.at, fallback.rightAligned);
        if constexpr (!packingEnabled_) {
            return fallback;
        }
        if (first->first == length) return fallback;
        // In either condition every candidate leaves enough guaranteed
        // capacity for three requests of maximum length.
        if (starts_[40].size() >= 4 ||
            sizes_.rbegin()->first >= length + packingCap_) {
            return fallback;
        }
        Coordinate tailStart = -1;
        Coordinate tailSpace = 0;
        if (!gaps_.empty() &&
            gaps_.rbegin()->second == trench_) {
            tailStart = gaps_.rbegin()->first;
            tailSpace = trench_ - tailStart;
        }
        // The fallback belongs to one of the first two size classes.
        // Four slots simplify collection; at most three are distinct.
        std::array<Placement, 4> choices{};
        int choiceCount = 1;
        choices[0] = fallback;
        auto append = [&](Coordinate start) {
            Placement proposed{start, false};
            selectReleasePlacement(
                length, proposed.at, proposed.rightAligned);
            for (int i = 0; i < choiceCount; ++i) {
                if (choices[i].at == proposed.at) return;
            }
            choices[choiceCount++] = proposed;
        };
        append(first->second);
        if (nextSize != sizes_.end()) append(nextSize->second);
        if (tailSpace >= length) append(tailStart);
        if (choiceCount == 1) return fallback;
        PackingProfile interior = packingProfile_;
        interior.take(tailSpace);
        const Scenarios scenarios = buildScenarios();
        int bestIndex = 0;
        int bestScore = projectedGrowth(
            choices[0], length, interior, tailStart, tailSpace,
            scenarios, std::numeric_limits<int>::max());
        for (int i = 1; i < choiceCount && bestScore != 0; ++i) {
            const int score = projectedGrowth(
                choices[i], length, interior, tailStart, tailSpace,
                scenarios, bestScore);
            if (score < bestScore) {
                bestScore = score;
                bestIndex = i;
            }
        }
        return choices[bestIndex];
    }
    static int bucket(Coordinate n) {
        return static_cast<int>(std::min<Coordinate>(40, n));
    }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b - a, a});
        starts_[bucket(b - a)].insert(a);
        packingProfile_.add(b - a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b - a, a});
        starts_[bucket(b - a)].erase(a);
        packingProfile_.take(b - a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        advanceReleaseClock();
        observeLength(length);
        const Placement placement = choosePlacement(length);
        Coordinate at = placement.at;
        Coordinate digs = 0;
        // Growth is allowed only after the global fitting-gap search
        // has established that no existing interval can hold the pipe.
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() &&
                gaps_.rbegin()->second == trench_) {
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
        if (placement.rightAligned) at = finish - length;
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
        Coordinate a = p.start;
        Coordinate b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) {
                a = left->first;
                erase(a);
            }
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.06; max_solver_rss_mib: 9.98

Text feedback:
Fitness F/T=0.859561466483; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737963871
family=short_phase_churn mean_F/T=0.781231752
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.802662964
family=short_rounding mean_F/T=0.808221691
family=geometric_cohorts mean_F/T=0.808527948
family=short_heavy mean_F/T=0.821278547
family=additive_cohorts mean_F/T=0.826891209
family=size_biased_deletion mean_F/T=0.831375197
family=distribution_switch mean_F/T=0.834484073
family=tiny_churn mean_F/T=0.835116112
family=uniform_churn mean_F/T=0.836919475
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847093254
family=long_heavy mean_F/T=0.849756128
family=fifo mean_F/T=0.864512668
family=serial_churn mean_F/T=0.867743936
family=size_lifetimes mean_F/T=0.876761532
family=large_live_set mean_F/T=0.878380217
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882848124
family=hotset_switching mean_F/T=0.892047313
family=soft_recency_growth mean_F/T=0.896392595
family=bimodal mean_F/T=0.896634947
family=section_boundaries mean_F/T=0.901461482
family=burst_drain mean_F/T=0.907481748
family=serial_growth mean_F/T=0.917407304
family=long_prefill_recent mean_F/T=0.917872355
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920999287
family=drain_recovery mean_F/T=0.924758483
family=hotset_growth mean_F/T=0.950641471
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955291422
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001512 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001432 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001426 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001446 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001456 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001398 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.611210454 F/B=0.646045362 B/T=0.946079780 overrun=0.056993 cpu_s=0.090102 rss_mib=2.156
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.620927673 F/B=0.675406191 B/T=0.919339623 overrun=0.087737 cpu_s=0.343123 rss_mib=3.312
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.344370 rss_mib=2.938
case=s31_060_large_live_set family=large_live_set F/T=0.632458290 F/B=0.641932619 B/T=0.985240929 overrun=0.014980 cpu_s=0.447067 rss_mib=4.359
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001460 rss_mib=1.328
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001405 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003143 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013349 rss_mib=1.484
case=s31_040_distribution_switch family=distribution_switch F/T=0.666898148 F/B=0.692548077 B/T=0.962962963 overrun=0.038462 cpu_s=0.018197 rss_mib=1.406
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003007 rss_mib=1.359
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.353512 rss_mib=2.938
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.138815 rss_mib=2.172
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003007 rss_mib=1.359
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.078591 rss_mib=1.641
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.344370 rss_mib=2.938
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.379089 rss_mib=2.984
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001699 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002357 rss_mib=1.359
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.060392 rss_mib=1.484
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.117015 rss_mib=1.859
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821455616 F/B=0.950170316 B/T=0.864535128 overrun=0.156691 cpu_s=0.135745 rss_mib=2.000
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.348536 rss_mib=2.969
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852931866 F/B=0.982097589 B/T=0.868479747 overrun=0.151437 cpu_s=0.171293 rss_mib=3.344
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.835978836 F/B=0.954682779 B/T=0.875661376 overrun=0.141994 cpu_s=0.037223 rss_mib=1.500
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.677577741 F/B=0.768089054 B/T=0.882160393 overrun=0.133581 cpu_s=0.021092 rss_mib=1.438
case=s31_061_size_biased_deletion family=size_biased_deletion F/T=0.841041667 F/B=0.950054308 B/T=0.885256410 overrun=0.129616 cpu_s=0.766433 rss_mib=4.672

PAIRED SEARCH EVIDENCE
Against parent gen37: delta mean F/T=+0.001747828; improved/regressed/tied=42/27/83.
family=size_lifetimes delta_F/T=+0.028683798
family=burst_drain delta_F/T=+0.021145768
family=section_boundaries delta_F/T=+0.011538194
family=hotset_switching delta_F/T=+0.009689671
family=drifting_sizes delta_F/T=-0.009487948
family=additive_cohorts delta_F/T=+0.007245488
Regressions:
s31_041_drifting_sizes: delta_F/T=-0.036501025, delta_T=+60
s31_039_distribution_switch: delta_F/T=-0.024810924, delta_T=+40
s31_049_geometric_cohorts: delta_F/T=-0.021262458, delta_T=+20
s31_024_fifo: delta_F/T=-0.019981735, delta_T=+40
Gains:
s31_033_burst_drain: delta_F/T=+0.083959451, delta_T=-80
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.057446809, delta_T=-60
s31_017_section_boundaries: delta_F/T=+0.035552536, delta_T=-40

Against leader gen52: delta mean F/T=+0.000700012; improved/regressed/tied=44/39/69.
family=long_heavy delta_F/T=+0.016797553
family=size_biased_deletion delta_F/T=-0.016506154
family=size_lifetimes delta_F/T=-0.015179037
family=bimodal delta_F/T=+0.014230775
family=section_boundaries delta_F/T=+0.012813208
family=distribution_switch delta_F/T=+0.009592012
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.090454545, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.062943459, delta_T=+60
s31_024_fifo: delta_F/T=-0.030388889, delta_T=+60
s31_103_serial_churn: delta_F/T=-0.029813837, delta_T=+40
Gains:
s31_009_long_heavy: delta_F/T=+0.050889878, delta_T=-80
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.039130435, delta_T=-40
s31_022_fifo: delta_F/T=+0.035732110, delta_T=-240

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.859561466; mean positive loss on worst 16 cases=0.016110133; max case loss=0.042631579; regressed cases=31; worst family delta F/T=-0.013784408. These are selection diagnostics; primary fitness remains mean F/T.


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
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes still-live pipes, so long-lived survivors contribute
// evidence without requiring their eventual deletion.
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
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
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
        // An already available tail can become a two-front arena without
        // requesting any additional excavation.
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
            selectCandidates(length, group, deletionProbability, choice);
        } else {
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
        pipe.active = true;
        pipes_.push_back(pipe);
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
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
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
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        // Hierarchical smoothing shares evidence between cyclic positions.
        // No deletion pattern is enabled by a fixed sequence of commands.
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
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
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
        // Renewal reward: at each step, allow up to four observed-distribution
        // requests to find a fitting one, then continue with the remainder.
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
        // A bounded survival approximation over a typical lifetime horizon.
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
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
            // Use the expandable tail only when no interior gap fits.
            // The unique tail can occupy at most one size-index entry.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        // On a neighbor's release, its far-side free gap also coalesces.
        // The release loops below include this span only in that event.
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
        // Expected opportunity cost conditional on the new pipe surviving.
        // Each neighboring pipe can independently release its occupied span.
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
                futureWeight * futureCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    // Fast-deleting pipes approach from the low side;
                    // slow-deleting pipes approach from the high side.
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
            // If the oldest is the tail, the next entry of this span
            // is the oldest interior gap. There is only one tail.
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        // Candidate coverage is identical in both tie-break ablations.
        // considerGap retains the exact interior-before-tail check.
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
        // Include wider residual-capacity bands even when many small
        // distinct spans precede them.
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
        Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        const bool separate = canSeparate(deletionProbability);
        Coordinate extraDigs = 0;
        if (separate) {
            const Coordinate minimumCapacity =
                available + digs * kSectionLength;
            const Coordinate wantedExtra = std::max<Coordinate>(
                0, 3LL * length - minimumCapacity);
            const Coordinate budgetSections =
                (peakLiveVolume_ / 64) / kSectionLength;
            const Coordinate wantedSections =
                (wantedExtra + kSectionLength - 1) / kSectionLength;
            extraDigs = std::min(budgetSections, wantedSections);
            digs += extraDigs;
        }
        if (extraDigs > 0) ++expansionGatePasses;
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0, tick_);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right, freeSince});
        const GapKey key{end - start, start};
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

Here are the performance metrics of the program:

Combined score to maximize: 0.85
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.85; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.76; max_solver_rss_mib: 7.91

Here is additional text feedback about the current program:

Fitness F/T=0.854981207953; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.736993688
family=short_phase_churn mean_F/T=0.771580065
family=short_heavy mean_F/T=0.783707342
family=tiny_churn mean_F/T=0.785003666
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.802981167
family=additive_cohorts mean_F/T=0.807363433
family=geometric_cohorts mean_F/T=0.811928732
family=short_rounding mean_F/T=0.818636924
family=fifo mean_F/T=0.831009381
family=uniform_churn mean_F/T=0.836774842
family=size_biased_deletion mean_F/T=0.845159605
family=distribution_switch mean_F/T=0.845403369
family=long_heavy mean_F/T=0.845457065
family=long_prefill_random mean_F/T=0.845592675
family=micro_tail_reuse mean_F/T=0.845833333
family=size_lifetimes mean_F/T=0.861711288
family=serial_churn mean_F/T=0.871743241
family=large_live_set mean_F/T=0.878994949
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881988264
family=hotset_switching mean_F/T=0.882767279
family=bimodal mean_F/T=0.884310625
family=section_boundaries mean_F/T=0.894107206
family=soft_recency_growth mean_F/T=0.895600096
family=burst_drain mean_F/T=0.901909891
family=serial_growth mean_F/T=0.912305509
family=long_prefill_recent mean_F/T=0.917856960
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920150122
family=drain_recovery mean_F/T=0.923650325
family=background_ephemeral mean_F/T=0.951952070
family=hotset_growth mean_F/T=0.952067505
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001579 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001745 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001523 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001516 rss_mib=1.359
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001493 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001494 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611126393 F/B=0.646045362 B/T=0.945949663 overrun=0.057139 cpu_s=0.104801 rss_mib=2.375
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617722509 F/B=0.675406191 B/T=0.914594087 overrun=0.093381 cpu_s=0.483166 rss_mib=4.016
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.530638 rss_mib=3.125
case=s31_024_fifo family=fifo F/T=0.628735632 F/B=0.770422535 B/T=0.816091954 overrun=0.225352 cpu_s=0.027779 rss_mib=1.578
case=s31_060_large_live_set family=large_live_set F/T=0.632901343 F/B=0.641932619 B/T=0.985931115 overrun=0.014270 cpu_s=0.683288 rss_mib=4.812
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001549 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001796 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003434 rss_mib=1.406
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.014741 rss_mib=1.531
case=s31_008_short_heavy family=short_heavy F/T=0.661538462 F/B=0.758823529 B/T=0.871794872 overrun=0.147059 cpu_s=0.022560 rss_mib=1.500
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_086_tiny_churn family=tiny_churn F/T=0.717741935 F/B=0.959051724 B/T=0.748387097 overrun=0.336207 cpu_s=0.183903 rss_mib=2.156
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.443112 rss_mib=3.766
case=s31_006_short_heavy family=short_heavy F/T=0.739655172 F/B=0.953333333 B/T=0.775862069 overrun=0.288889 cpu_s=0.502206 rss_mib=3.797
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.530638 rss_mib=3.125
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003168 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.702435065 F/B=0.865400000 B/T=0.811688312 overrun=0.232000 cpu_s=0.112284 rss_mib=1.812
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.696875000 F/B=0.857692308 B/T=0.812500000 overrun=0.230769 cpu_s=0.002871 rss_mib=1.375
case=s31_009_long_heavy family=long_heavy F/T=0.775423729 F/B=0.953125000 B/T=0.813559322 overrun=0.229167 cpu_s=0.479215 rss_mib=3.844
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.774269663 F/B=0.950045956 B/T=0.814981273 overrun=0.227022 cpu_s=0.205414 rss_mib=2.406
case=s31_024_fifo family=fifo F/T=0.628735632 F/B=0.770422535 B/T=0.816091954 overrun=0.225352 cpu_s=0.027779 rss_mib=1.578
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.071868 rss_mib=1.656
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001849 rss_mib=1.359
case=s31_087_tiny_churn family=tiny_churn F/T=0.800000000 F/B=0.950000000 B/T=0.842105263 overrun=0.187500 cpu_s=0.691647 rss_mib=3.328
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.050968 rss_mib=1.625
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821110177 F/B=0.950170316 B/T=0.864171573 overrun=0.157178 cpu_s=0.212051 rss_mib=2.297
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852809150 F/B=0.982097589 B/T=0.868354795 overrun=0.151603 cpu_s=0.234414 rss_mib=3.625

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.854981208; mean positive loss on worst 16 cases=0.000000000; max case loss=0.000000000; regressed cases=0; worst family delta F/T=+0.000000000. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
