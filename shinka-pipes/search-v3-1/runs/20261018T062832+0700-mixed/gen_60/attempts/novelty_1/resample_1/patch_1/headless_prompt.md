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

**Добавьте сглаженную поправку на частоту освобождения объектов конкретной длины.** Лениво накапливайте для каждой длины число удалений `D[k]` и exposure `E[k]` — суммарное число команд, проведённых объектами этой длины в живом состоянии; оценку задайте как `h[k] = (D[k] + 8) / (E[k] + 8 / hGlobal)`, где `hGlobal` — общая частота освобождения на единицу exposure. Умножайте текущий вес соседа на `clamp(h[k] / hGlobal, 0.5, 2.0)`, сохраняя PID-gate и порог переключения; до появления положительной общей оценки используйте множитель 1. Это объединяет успешный паттерн `releases/exposure` из gen24 с выигрышем gen52 на `size_lifetimes`, не вводя совместную модель освобождения соседей.

RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Same complete saved trench vector: generations [9, 38, 55]. Advisory only, not equivalence.
Same complete saved trench vector: generations [31, 54]. Advisory only, not equivalence.
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
bellman_ties_release_edge: attempts=1; score_range=0.856981663..0.856981663
gen49 mixed_sequence_gap_dp; correct=True; parent=37; delta_F/T=-0.006936727; claim=Новый механизм — Bellman DP для смешанных последовательностей запросов. Для каждого небольшого gap вычисляется ожидаемая длина, которую он обслужит за четыре гипотетические вставки. Размеры берутся из наблюдавшегося расп
  improved/regressed/tied=37/48/67
  regression s31_006_short_heavy: delta_F/T=-0.245270270
  regression s31_008_short_heavy: delta_F/T=-0.173508772
gen52 conditional_merge_utility_edge; correct=True; parent=13; delta_F/T=+0.001435106; claim=Предлагаю оценивать край размещения по полезности будущего слияния. Родитель учитывает порядок PID соседей, но игнорирует их длины: освобождение короткого соседа может оставить остаток практически бесполезным.
Для остатк
  improved/regressed/tied=17/16/119
  regression s31_022_fifo: delta_F/T=-0.057960564
  regression s31_086_tiny_churn: delta_F/T=-0.024788324
gen59 conditional_two_size_capacity; correct=True; parent=39; delta_F/T=-0.000762877; claim=Родитель — текущий `validated_transition_profile` (gen39). Сохраняются условный прогноз, сравнение с суффиксом и `adjacent_release_edge`. Из Bellman переносится гистограмма размеров дыр.
Единственный механизм: при отсутс
  improved/regressed/tied=42/34/76
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_033_burst_drain: delta_F/T=-0.064468864
gen57 shift_triggered_demand_blend; correct=True; parent=51; delta_F/T=-0.000257633; claim=Предлагаю один механизм: переключение профиля спроса при обнаруженной смене распределения. Хранятся последние 64 длины вставок; каждые 16 вставок их распределение сравнивается с родительским накопленным профилем через to
  improved/regressed/tied=26/29/97
  regression s31_009_long_heavy: delta_F/T=-0.038793103
  regression s31_049_geometric_cohorts: delta_F/T=-0.020295983
gen56 shadow_trench_duel; correct=True; parent=20; delta_F/T=-0.000439769; claim=Новый механизм — причинный выбор политики по двум теневым раскладкам. Каждая полученная команда обрабатывается родительским allocator и обычным Best-Fit без вывода. Политика с меньшим накопленным trench задаёт правило ра
  improved/regressed/tied=23/35/94
  regression s31_041_drifting_sizes: delta_F/T=-0.046432063
  regression s31_008_short_heavy: delta_F/T=-0.028666667
gen55 demand_funded_lifetime_arena; correct=True; parent=0; delta_F/T=+0.000183147; claim=Предлагаю создавать lifetime arena только из уже оплаченного пространства. Сейчас growFor может дополнительно раскопать до трёх длин текущей трубы ради будущего разделения по времени жизни. Патч оставляет только минималь
  improved/regressed/tied=9/9/134
  regression s31_062_size_biased_deletion: delta_F/T=-0.006869067
  regression s31_064_size_biased_deletion: delta_F/T=-0.003859311
gen54 bellman_ties_release_edge; correct=True; parent=15; delta_F/T=-0.001305584; claim=Crossover сохраняет выбор края из `adjacent_release_edge` и добавляет двухшаговый Bellman-прогноз только для разрешения равенства одношаговых оценок между best-fit дырой и суффиксом.
Это повтор Bellman с изменённым взаим
  improved/regressed/tied=29/27/96
  regression s31_031_s
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=specialist; specialist families=['bimodal', 'burst_drain', 'hotset_switching', 'isolated_recent_churn', 'recent_window_growth', 'section_boundaries', 'soft_recency_growth']; fixed-baseline tail loss=0.056575690; maximum case loss=0.159925443. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
Analyze the current program to identify its key parameters and algorithmic components, then design a new algorithm with different parameter settings and configurations.
You MUST respond using a short summary name, description and the full code:

<NAME>
A shortened name summarizing the code you are proposing. Lowercase, no 
spaces, underscores allowed.
</NAME>

<DESCRIPTION>
Identify the key parameters in the current approach and explain how your new parameter choices or algorithmic configuration will lead to better performance.
</DESCRIPTION>

<CODE>
```{language}
# The new parametric algorithm implementation here.
```
</CODE>

* Keep the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the code.
* Identify parameters like: learning rates, iteration counts, thresholds, weights, selection criteria, etc.
* Design a new algorithm with different parameter values or configurations.
* Consider adaptive parameters, different optimization strategies, or alternative heuristics.
* Maintain the same inputs and outputs as the original program.
* Use the <NAME>, <DESCRIPTION>, and <CODE> delimiters to structure your response. It will be parsed afterwards.

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
using Coordinate = std::int64_t;
class Allocator {
    static constexpr int kMaxRequest = 40;
    static constexpr int kMaxScoredGap = 2 * kMaxRequest - 1;
    static constexpr int kLargeBucket = kMaxScoredGap + 1;
    static constexpr int kHorizon = 4;
    // Same-parent ablation: disable only the new placement mechanism.
    static constexpr bool kUseMixedSequenceDP = true;
    struct Pipe {
        Coordinate start;
        int length;
    };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, kLargeBucket + 1> starts_;
    Coordinate trench_ = 0;
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
    std::uint64_t insertions_ = 0;
    std::array<double, kMaxScoredGap + 1> serviceValue_{};
    std::map<Coordinate, std::size_t> live_;
    std::array<std::size_t, 41> population_{};
    std::array<double, 41> deaths_{}, exposure_{};
    std::array<std::uint64_t, 41> exposureAt_{};
    std::uint64_t commandTick_ = 0;
    double totalExposure_ = 0.0;
    double totalDeaths_ = 0.0;
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
    void rebuildServiceValue() {
        if (demandMass_ == 0) {
            serviceValue_.fill(0.0);
            return;
        }
        std::array<double, 41> probability{};
        std::array<std::uint32_t, 41> cumulative{};
        const double inverseMass =
            1.0 / static_cast<double>(demandMass_);
        for (int k = 1; k <= 40; ++k) {
            probability[k] =
                static_cast<double>(demand_[k]) * inverseMass;
            cumulative[k] = cumulative[k - 1] + demand_[k];
        }
        std::array<double, kMaxScoredGap + 1> previous{};
        std::array<double, kMaxScoredGap + 1> next{};
        // V[h][s]: expected volume served by one gap of capacity s
        // during h IID requests drawn from the observed size profile.
        // Requests that do not fit leave this gap unchanged.
        for (int horizon = 1; horizon <= kHorizon; ++horizon) {
            for (int space = 0; space <= kMaxScoredGap; ++space) {
                const int limit = std::min(kMaxRequest, space);
                const double rejectedProbability =
                    static_cast<double>(
                        demandMass_ - cumulative[limit]) * inverseMass;
                double value = rejectedProbability * previous[space];
                for (int k = 1; k <= limit; ++k) {
                    if (demand_[k] != 0) {
                        value += probability[k] *
                            (static_cast<double>(k) +
                             previous[space - k]);
                    }
                }
                next[space] = value;
            }
            previous.swap(next);
        }
        serviceValue_ = previous;
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
        ++insertions_;
        if constexpr (kUseMixedSequenceDP) {
            if (insertions_ <= 32 || insertions_ % 16 == 0) {
                rebuildServiceValue();
            }
        }
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
        for (int b = 40; b <= kLargeBucket; ++b) {
            fittingGaps += starts_[b].size();
        }
        long double extraLoss = 0.0L;
        for (int k = 40; k >= 1; --k) {
            if (k < 40) fittingGaps += starts_[k].size();
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
        return extraLoss <= 0.0L;
    }
    Coordinate chooseParentFit(int length) const {
        auto candidate = sizes_.lower_bound({length, 0});
        if (candidate == sizes_.end()) return -1;
        if (candidate->first > length) {
            const auto penalty =
                splitPenalty(candidate->first, length);
            if (penalty != 0) {
                const auto larger = sizes_.upper_bound({
                    candidate->first,
                    std::numeric_limits<Coordinate>::max()
                });
                if (larger != sizes_.end() &&
                    splitPenalty(larger->first, length) < penalty &&
                    scarcityAllowsExchange(
                        candidate->first, larger->first, length)) {
                    candidate = larger;
                }
            }
        }
        return candidate->second;
    }
    Coordinate chooseFit(int length) const {
        const Coordinate parentAt = chooseParentFit(length);
        if constexpr (!kUseMixedSequenceDP) {
            return parentAt;
        }
        if (parentAt < 0) return parentAt;
        const Coordinate parentSpace = gaps_.at(parentAt) - parentAt;
        if (parentSpace == length || parentSpace > kMaxScoredGap) {
            return parentAt;
        }
        const auto smallest = sizes_.lower_bound({length, 0});
        const int smallestSpace = static_cast<int>(smallest->first);
        // Threshold-loss weights reproduce the parent's scarcity
        // criterion, while prefix sums make each candidate check O(1).
        std::array<long double, 41> weight{};
        std::array<long double, 41> prefix{};
        std::size_t fittingGaps = 0;
        for (int b = 40; b <= kLargeBucket; ++b) {
            fittingGaps += starts_[b].size();
        }
        for (int k = 40; k >= 1; --k) {
            if (k < 40) fittingGaps += starts_[k].size();
            if (fittingGaps != 0 && demand_[k] != 0) {
                weight[k] =
                    static_cast<long double>(demand_[k]) /
                    static_cast<long double>(fittingGaps);
            }
        }
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + weight[k];
        }
        const auto scarcityLoss = [&](int space) {
            const int upper = std::min(40, space);
            const int lower = std::min(40, space - length);
            return prefix[upper] - prefix[lower];
        };
        const long double allowedLoss = scarcityLoss(smallestSpace);
        const int initialSpace = static_cast<int>(parentSpace);
        Coordinate bestAt = parentAt;
        double bestLoss =
            serviceValue_[initialSpace] -
            serviceValue_[initialSpace - length];
        for (int space = smallestSpace;
             space <= kMaxScoredGap; ++space) {
            if (starts_[space].empty()) continue;
            const double loss =
                serviceValue_[space] -
                serviceValue_[space - length];
            // Preserve the parent's choice on numerical ties.
            if (loss >= bestLoss - 1e-10) continue;
            if (scarcityLoss(space) > allowedLoss) continue;
            bestLoss = loss;
            bestAt = *starts_[space].begin();
        }
        return bestAt;
    }
    double releaseGain(
        Coordinate a, Coordinate remainder, bool rightAligned,
        const std::array<std::uint32_t, 41>& prefix) const {
        auto neighbor = live_.lower_bound(a);
        if (rightAligned) {
            if (neighbor == live_.begin()) return 0.0;
            --neighbor;
        } else if (neighbor == live_.end()) {
            return 0.0;
        }
        const Pipe& p = pipes_[neighbor->second];
        Coordinate releasedSpace = p.length;
        if (releasedSpace >= 40) return 0.0;
        if (rightAligned) {
            auto outside = gaps_.lower_bound(p.start);
            if (outside != gaps_.begin()) {
                --outside;
                if (outside->second == p.start) {
                    releasedSpace += outside->second - outside->first;
                }
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end()) {
                releasedSpace += outside->second - outside->first;
            }
        }
        const int before = static_cast<int>(std::min<Coordinate>(
            40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(std::min<Coordinate>(
            40, remainder + releasedSpace));
        if (before == after) return 0.0;
        return releaseRate(p.length) *
            static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(
        int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0.0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        }
        const auto end = sizes_.upper_bound({
            space, std::numeric_limits<Coordinate>::max()
        });
        const std::array<Coordinate, 2> candidates{
            at, std::prev(end)->second
        };
        double best = 0.0;
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
    static int bucket(Coordinate length) {
        return static_cast<int>(
            std::min<Coordinate>(kLargeBucket, length));
    }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b - a, a});
        starts_[bucket(b - a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b - a, a});
        starts_[bucket(b - a)].erase(a);
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
        Coordinate at = chooseFit(length);
        Coordinate digs = 0;
        bool rightAligned = false;
        selectReleasePlacement(length, at, rightAligned);
        // chooseFit searches the global size index before growth.
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

Here are the performance metrics of the program:

Combined score to maximize: 0.85
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.85; worst_family_score: 0.53; mean_overrun: 0.06; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.08; max_solver_rss_mib: 10.05

Here is additional text feedback about the current program:

Fitness F/T=0.850876911733; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=short_heavy mean_F/T=0.699396391
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737010474
family=short_phase_churn mean_F/T=0.753547398
family=geometric_cohorts mean_F/T=0.789045954
family=tiny_churn mean_F/T=0.789305476
family=short_rounding mean_F/T=0.798821969
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.807045616
family=additive_cohorts mean_F/T=0.820079011
family=size_biased_deletion mean_F/T=0.823133470
family=fifo mean_F/T=0.823595711
family=uniform_churn mean_F/T=0.831202858
family=distribution_switch mean_F/T=0.831763653
family=long_prefill_random mean_F/T=0.843676223
family=micro_tail_reuse mean_F/T=0.845833333
family=size_lifetimes mean_F/T=0.845847038
family=long_heavy mean_F/T=0.847000420
family=serial_churn mean_F/T=0.862217430
family=large_live_set mean_F/T=0.880080825
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.883075243
family=hotset_switching mean_F/T=0.892456021
family=soft_recency_growth mean_F/T=0.897602912
family=bimodal mean_F/T=0.899478972
family=section_boundaries mean_F/T=0.905761839
family=serial_growth mean_F/T=0.910519729
family=burst_drain mean_F/T=0.910879376
family=drain_recovery mean_F/T=0.916142981
family=long_prefill_recent mean_F/T=0.917865226
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921144722
family=hotset_growth mean_F/T=0.951904636
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.953271046
family=striped_recycling mean_F/T=0.960358355
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001571 rss_mib=1.312
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001515 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001489 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001707 rss_mib=1.328
case=s31_008_short_heavy family=short_heavy F/T=0.543157895 F/B=0.758823529 B/T=0.715789474 overrun=0.397059 cpu_s=0.017781 rss_mib=1.422
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001629 rss_mib=1.312
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.562761506 F/B=0.781976744 B/T=0.719665272 overrun=0.389535 cpu_s=0.355056 rss_mib=2.938
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001546 rss_mib=1.312
case=s31_006_short_heavy family=short_heavy F/T=0.579729730 F/B=0.953333333 B/T=0.608108108 overrun=0.644444 cpu_s=0.368100 rss_mib=2.969
case=s31_024_fifo family=fifo F/T=0.588172043 F/B=0.770422535 B/T=0.763440860 overrun=0.309859 cpu_s=0.022228 rss_mib=1.500
case=s31_118_partial_drain family=partial_drain F/T=0.611042354 F/B=0.646045362 B/T=0.945819582 overrun=0.057284 cpu_s=0.091552 rss_mib=2.203
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.620537398 F/B=0.675406191 B/T=0.918761785 overrun=0.088421 cpu_s=0.344769 rss_mib=3.312
case=s31_060_large_live_set family=large_live_set F/T=0.632532089 F/B=0.641932619 B/T=0.985355893 overrun=0.014862 cpu_s=0.445066 rss_mib=4.531
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001780 rss_mib=1.328
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001484 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003211 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_006_short_heavy family=short_heavy F/T=0.579729730 F/B=0.953333333 B/T=0.608108108 overrun=0.644444 cpu_s=0.368100 rss_mib=2.969
case=s31_008_short_heavy family=short_heavy F/T=0.543157895 F/B=0.758823529 B/T=0.715789474 overrun=0.397059 cpu_s=0.017781 rss_mib=1.422
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.562761506 F/B=0.781976744 B/T=0.719665272 overrun=0.389535 cpu_s=0.355056 rss_mib=2.938
case=s31_086_tiny_churn family=tiny_churn F/T=0.731907895 F/B=0.959051724 B/T=0.763157895 overrun=0.310345 cpu_s=0.126899 rss_mib=1.875
case=s31_024_fifo family=fifo F/T=0.588172043 F/B=0.770422535 B/T=0.763440860 overrun=0.309859 cpu_s=0.022228 rss_mib=1.500
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.747396963 F/B=0.950045956 B/T=0.786695589 overrun=0.271140 cpu_s=0.146307 rss_mib=2.172
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.675757576 F/B=0.857692308 B/T=0.787878788 overrun=0.269231 cpu_s=0.002683 rss_mib=1.359
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.363735 rss_mib=2.969
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003035 rss_mib=1.391
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.063850 rss_mib=1.547
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.081108 rss_mib=1.656
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.122994 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001843 rss_mib=1.359
case=s31_009_long_heavy family=long_heavy F/T=0.802631579 F/B=0.953125000 B/T=0.842105263 overrun=0.187500 cpu_s=0.395300 rss_mib=3.016
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.037184 rss_mib=1.516
case=s31_127_short_phase_churn family=short_phase_churn F/T=0.738541667 F/B=0.864634146 B/T=0.854166667 overrun=0.170732 cpu_s=0.006441 rss_mib=1.391

PAIRED SEARCH EVIDENCE
Against parent gen37: delta mean F/T=-0.006936727; improved/regressed/tied=37/48/67.
family=short_heavy delta_F/T=-0.123399507
family=fifo delta_F/T=-0.041788413
family=tiny_churn delta_F/T=-0.041331973
family=short_phase_churn delta_F/T=-0.033056029
family=geometric_cohorts delta_F/T=-0.026641694
family=burst_drain delta_F/T=+0.024543397
Regressions:
s31_006_short_heavy: delta_F/T=-0.245270270, delta_T=+440
s31_008_short_heavy: delta_F/T=-0.173508772, delta_T=+460
s31_024_fifo: delta_F/T=-0.161143025, delta_T=+400
s31_127_short_phase_churn: delta_F/T=-0.085876938, delta_T=+100
Gains:
s31_033_burst_drain: delta_F/T=+0.083959451, delta_T=-80
s31_017_section_boundaries: delta_F/T=+0.054513889, delta_T=-60
s31_094_hotset_switching: delta_F/T=+0.030254898, delta_T=-80
s31_015_bimodal: delta_F/T=+0.020397780, delta_T=-20

Against leader gen24: delta mean F/T=-0.007848970; improved/regressed/tied=39/53/60.
family=short_heavy delta_F/T=-0.115912994
family=fifo delta_F/T=-0.047671633
family=tiny_churn delta_F/T=-0.047348088
family=short_phase_churn delta_F/T=-0.034444689
family=size_lifetimes delta_F/T=-0.032150294
family=short_rounding delta_F/T=-0.020057616
Regressions:
s31_006_short_heavy: delta_F/T=-0.261446741, delta_T=+460
s31_008_short_heavy: delta_F/T=-0.163691420, delta_T=+440
s31_024_fifo: delta_F/T=-0.141161290, delta_T=+360
s31_086_tiny_churn: delta_F/T=-0.098315986, delta_T=+360
Gains:
s31_009_long_heavy: delta_F/T=+0.052631579, delta_T=-80
s31_049_geometric_cohorts: delta_F/T=+0.041558442, delta_T=-40
s31_015_bimodal: delta_F/T=+0.039945652, delta_T=-40
s31_055_additive_cohorts: delta_F/T=+0.031938250, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.850876912; mean positive loss on worst 16 cases=0.056575690; max case loss=0.159925443; regressed cases=50; worst family delta F/T=-0.084310951. These are selection diagnostics; primary fitness remains mean F/T.


# Task

Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
