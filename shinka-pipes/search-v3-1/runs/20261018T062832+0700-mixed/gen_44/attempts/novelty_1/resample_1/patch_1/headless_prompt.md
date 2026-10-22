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

**Сделайте переключение края осторожнее при неопределённой интенсивности освобождений.** Для существующей оценки `λ` вычисляйте эвристическую неопределённость `σ = λ / sqrt(releases + 2)` и выбирайте правый край только при `λL − 1.25λR > z × sqrt(σL² + 1.25²σR²)`, начиная с `z=0.5`. Такая мутация сохраняет механизм gen24 и проверяет, можно ли сократить его регрессии за счёт подавления слабо обоснованных переключений; статистической гарантией этот порог считать нельзя.

RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Same complete saved trench vector: generations [9, 38]. Advisory only, not equivalence.
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
capacity_guarded_tail: attempts=1; score_range=0.857608299..0.857608299
gen12 tail_growth_regret; correct=True; parent=4; delta_F/T=+0.000736378; claim=Механизм — выбор интервала по ожидаемой цене расходования свободного хвоста. Когда исходный best fit выбирает хвост, дополнительно рассматривается минимальный подходящий внутренний интервал. Для обоих вариантов вычисляет
  improved/regressed/tied=29/29/94
  regression s31_001_uniform_churn: delta_F/T=-0.039774859
  regression s31_086_tiny_churn: delta_F/T=-0.018451460
gen24 exposure_guided_split; correct=True; parent=6; delta_F/T=+0.001161829; claim=Родитель gen6 сохраняется: размеры bins меньше 80, коэффициент regret 8, prior 1 на размер, обновление профиля каждые 64 вставки после первых 32, уменьшение наблюдений вдвое каждые 512 вставок.
Новый механизм выбирает ст
  improved/regressed/tied=39/37/76
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_009_long_heavy: delta_F/T=-0.038793103
gen42 cohort_slot_regret; correct=True; parent=32; delta_F/T=+0.000398057; claim=Механизм добавляет штраф за потерю целых мест под повторяющиеся размеры. Из родительского профиля выбираются четыре наиболее вероятные уже наблюдавшиеся длины. Для каждой длины k оценивается потеря вместимости floor(span
  improved/regressed/tied=40/38/74
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_039_distribution_switch: delta_F/T=-0.037771855
gen41 endpoint_demand_unlock; correct=True; parent=23; delta_F/T=+0.000419554; claim=Родитель — `capacity_guarded_tail` (gen23). Сохраняются выбор размера дыры, профиль спроса и проверка хвоста. Из `exposure_guided_split` перенесена оценка частоты освобождения по длине и времени присутствия живых труб.
Е
  improved/regressed/tied=36/37/79
  regression s31_062_size_biased_deletion: delta_F/T=-0.021658819
  regression s31_043_drifting_sizes: delta_F/T=-0.020462616
gen40 geometry_bellman_tail_exchange; correct=True; parent=0; delta_F/T=-0.000629747; claim=Повторная проверка Two-Future-Insert Bellman с изменённым взаимодействием с родителем. Сохраняются его exposure-модель освобождений, геометрия слияния, выбор внутренних gaps и разрешение равенств по возрасту gap. Bellman
  improved/regressed/tied=45/31/76
  regression s31_126_short_phase_churn: delta_F/T=-0.059732143
  regression s31_122_short_rounding: delta_F/T=-0.042631579
gen39 validated_transition_profile; correct=True; parent=15; delta_F/T=-0.000523529; claim=Механизм: условный профиль спроса с проверкой на последующих наблюдениях. Сохраняются best-fit, сравнение внутренней дыры с суффиксом и `adjacent_release_edge`. Меняется распределение длин, используемое прогнозом расшире
  improved/regressed/tied=14/15/123
  regression s31_063_size_biased_deletion: delta_F/T=-0.040963203
  regression s31_102_serial_churn: delta_F/T=-0.023444776
gen38 appendable_wilderness; correct=True; parent=0; delta_F/T=+0.000183147; claim=Повторная проверка `appendable_wilderness` с изменённым взаимодействием: откладывать расширение арены до фактической необходимости, сохраняя родительский выбор обоих краёв размещения. В прежнем gen33 минимальное расширен
  improved/regressed/tied=9/9/134
  regression s31_062_size_biased_deletion: delta_F/T=-0.006869067
  regression s31_064_size_biased_deletion: delta_F/T=-0.003
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.026866513; maximum case loss=0.052023597. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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

Here are the performance metrics of the program:

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.89; max_solver_rss_mib: 3.81

Here is additional text feedback about the current program:

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


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
