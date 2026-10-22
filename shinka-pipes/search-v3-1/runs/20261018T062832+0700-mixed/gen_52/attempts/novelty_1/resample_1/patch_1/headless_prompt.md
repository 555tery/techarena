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

**Учитывайте полезность слияния при выборе края.** Сохраните `chooseHole()` из gen24, а для остатка `r < 40` вычисляйте `U(r,n) = Σ weights_[k]` по размерам `r < k ≤ min(40,r+n)`, где `n` — длина соседнего объекта. Сравнивайте `λL·U(r,nL)` и `λR·U(r,nR)` с прежним порогом 1,25, сохраняя исходное правило, когда обе полезности равны нулю: это переносит перспективную идею gen41 непосредственно в успешный механизм gen24.

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
bounded_section_risk_veto: attempts=1; score_range=0.855006605..0.855006605
gen13 causal_release_edge; correct=True; parent=5; delta_F/T=-0.000109698; claim=Предлагаю выбирать край размещения внутри уже выбранного отверстия так, чтобы свободный остаток примыкал к соседу, который предположительно освободится раньше. Родитель всегда размещает трубу слева; выбор отверстия, прог
  improved/regressed/tied=26/11/115
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_085_tiny_churn: delta_F/T=-0.041403162
gen24 exposure_guided_split; correct=True; parent=6; delta_F/T=+0.001161829; claim=Родитель gen6 сохраняется: размеры bins меньше 80, коэффициент regret 8, prior 1 на размер, обновление профиля каждые 64 вставки после первых 32, уменьшение наблюдений вдвое каждые 512 вставок.
Новый механизм выбирает ст
  improved/regressed/tied=39/37/76
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_009_long_heavy: delta_F/T=-0.038793103
gen50 persistent_markov_slot_demand; correct=True; parent=34; delta_F/T=+0.000191120; claim=Механизм: прогнозировать повторения размеров через причинную Markov-модель, сохраняя родительский finite-horizon slot inventory.
Сейчас число будущих запросов каждого размера моделируется Binomial-распределением: порядок
  improved/regressed/tied=24/14/114
  regression s31_087_tiny_churn: delta_F/T=-0.044444444
  regression s31_017_section_boundaries: delta_F/T=-0.035552536
gen49 mixed_sequence_gap_dp; correct=True; parent=37; delta_F/T=-0.006936727; claim=Новый механизм — Bellman DP для смешанных последовательностей запросов. Для каждого небольшого gap вычисляется ожидаемая длина, которую он обслужит за четыре гипотетические вставки. Размеры берутся из наблюдавшегося расп
  improved/regressed/tied=37/48/67
  regression s31_006_short_heavy: delta_F/T=-0.245270270
  regression s31_008_short_heavy: delta_F/T=-0.173508772
gen48 bounded_section_risk_veto; correct=True; parent=0; delta_F/T=+0.000025397; claim=Новый механизм ограниченно переключает родительский выбор на best-fit, когда это уменьшает ожидаемое расширение при следующей вставке. Родитель сохраняет renewal potential, модель освобождений соседей, выбор края и oldes
  improved/regressed/tied=31/29/92
  regression s31_006_short_heavy: delta_F/T=-0.024655172
  regression s31_126_short_phase_churn: delta_F/T=-0.021117424
gen47 scarcity_weighted_residual_fit; correct=True; parent=6; delta_F/T=-0.000756554; claim=Архитектура разделена на индекс свободных интервалов `FreeIntervals`, модель спроса `DemandProfile` и координатор протокола `Allocator`. Индекс поддерживает вместимость внутренних дыр `C[k] = Σ floor(size/k)` при каждом 
  improved/regressed/tied=25/28/99
  regression s31_017_section_boundaries: delta_F/T=-0.065498540
  regression s31_007_short_heavy: delta_F/T=-0.041309524
gen46 hall_transport_inventory; correct=True; parent=42; delta_F/T=+0.000334636; claim=Новый механизм ранжирует gaps через глобальную транспортную модель свободной памяти. Сохраняется родительский профиль размеров. После предполагаемой вставки оставшийся свободный объём W распределяется между размерами сог
  improved/regressed/tied=46/37/69
  regression s31_009_long_heavy: delta_F/T=-0.076441103
  regression s31_023_fifo: delta_F/T=-0.053425532
gen45 prefix_growth_t
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.031251383; maximum case loss=0.075378788. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
NAME: Conditional Tail-Priced Best Fit + Causal Release Edge
DESCRIPTION:
Свободные внутренние интервалы объединяются при удалениях и индексируются
по координате и длине. Основной выбор — best fit с предпочтением меньшей
координаты. Свободный хвост хранится отдельно и расширяется минимально.
Если запрос помещается и во внутренний интервал, и в хвост, сравнивается
ожидаемое расширение при следующей вставке. Прогноз длины использует только
прошлые вставки: условный профиль переходов между длинами сглаживается
общим профилем. Оба профиля экспоненциально забывают старые наблюдения.
При близких оценках сохраняется обычный best fit.
Для максимального внутреннего отверстия M и хвоста длины W следующий
запрос S потребует:
    [S > max(M, W)] + [S > max(M, W + 20)]
новых секций. Формула точна, поскольку S <= 40. Прогноз предполагает,
что перед следующей вставкой удалений не будет. Расширение заранее
никогда не выполняется, если текущий запрос уже куда-либо помещается.
Для выбранного внутреннего отверстия дополнительно выбирается край
размещения. Затухающий сигнал сравнивает PID удаляемых труб со средним
PID живых труб. Положительный сигнал соответствует удалению старых,
отрицательный — новых. При выраженном сигнале остаток оставляется
рядом с соседом, ожидаемым к удалению раньше; иначе труба ставится слева.
Вставка: O(40 + log(H + 1) + log(L + 1)).
Удаление: амортизированно O(log(H + 1) + log(L + 1)).
Память: O(I + H + L + 40^2), где I — число вставок,
H — число отверстий, L — число живых труб.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения длин или порядка удалений,
а также зависимость lifetime от размера могут сделать прогноз неверным.
Ablation нового механизма: kReleaseEdge = false восстанавливает
родительский Conditional Tail-Priced Best Fit.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    static constexpr bool kTailLookahead = true;
    static constexpr bool kReleaseEdge = true;
    static constexpr double kGlobalDecay = 127.0 / 128.0;
    static constexpr double kTransitionDecay = 31.0 / 32.0;
    static constexpr double kPriorWeight = 8.0;
    static constexpr double kDecisionMargin = 1.0 / 64.0;
    FreeMap holes_;
    std::set<std::pair<int, int>> bySize_;
    std::vector<Pipe> pipes_;
    std::map<int, int> liveByStart_;
    std::int64_t livePidSum_ = 0;
    std::size_t oldestLivePid_ = 1;
    double releaseBias_ = 0.0;
    double releaseWeight_ = 0.0;
    // above[k] — вес наблюдений с длиной строго больше k.
    std::array<double, 41> globalAbove_{};
    std::array<std::array<double, 41>, 41> transitionAbove_{};
    int previousLength_ = 0;
    int trenchLength_ = 0;
    // Конец самой правой живой трубы. Хвост [frontier_, trenchLength_)
    // свободен и не входит в holes_.
    int frontier_ = 0;
    void observe(int length) {
        for (int k = 0; k < 40; ++k) {
            const double increment = length > k ? 1.0 : 0.0;
            globalAbove_[k] =
                globalAbove_[k] * kGlobalDecay + increment;
        }
        if (previousLength_ != 0) {
            auto& row = transitionAbove_[previousLength_];
            for (int k = 0; k < 40; ++k) {
                const double increment = length > k ? 1.0 : 0.0;
                row[k] = row[k] * kTransitionDecay + increment;
            }
        }
        previousLength_ = length;
    }
    double forecastAbove(int threshold, int currentLength) const {
        if (threshold >= 40) {
            return 0.0;
        }
        const auto& row = transitionAbove_[currentLength];
        const double marginal =
            globalAbove_[threshold] / globalAbove_[0];
        return (row[threshold] + kPriorWeight * marginal) /
               (row[0] + kPriorWeight);
    }
    double expectedNextGrowth(
        int largestHole, int tailLength, int currentLength
    ) const {
        const int firstThreshold =
            std::min(40, std::max(largestHole, tailLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, tailLength + 20));
        return forecastAbove(firstThreshold, currentLength) +
               forecastAbove(secondThreshold, currentLength);
    }
    void observeRelease(std::size_t pid) {
        constexpr double decay = 15.0 / 16.0;
        releaseBias_ *= decay;
        releaseWeight_ *= decay;
        if (liveByStart_.size() < 2) {
            return;
        }
        const double mean =
            static_cast<double>(livePidSum_) /
            static_cast<double>(liveByStart_.size());
        // При двух и более живых PID масштаб не меньше 0.5.
        const double scale = std::max(
            mean - static_cast<double>(oldestLivePid_),
            static_cast<double>(pipes_.size() - 1) - mean
        );
        releaseBias_ += (mean - static_cast<double>(pid)) / scale;
        releaseWeight_ += 1.0;
    }
    bool preferRightEdge(int holeStart) const {
        // Порог накопленного сигнала, без предположения независимости.
        if (releaseBias_ * releaseBias_ <= 2.0 * releaseWeight_) {
            return false;
        }
        const auto right = liveByStart_.lower_bound(holeStart);
        if (right == liveByStart_.end() ||
            right == liveByStart_.begin()) {
            return false;
        }
        const auto left = std::prev(right);
        // Размещение справа оставляет остаток рядом с левым соседом.
        return (left->second < right->second) == (releaseBias_ > 0.0);
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        bySize_.emplace(length, start);
    }
    void eraseHole(FreeMap::iterator it) {
        bySize_.erase(std::make_pair(it->second, it->first));
        holes_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
        // Начальный общий профиль: одно равномерное псевдонаблюдение.
        for (int k = 0; k <= 40; ++k) {
            globalAbove_[k] = static_cast<double>(40 - k) / 40.0;
        }
    }
    void place(int length) {
        observe(length);
        const int tailLength = trenchLength_ - frontier_;
        auto fit = bySize_.lower_bound(std::make_pair(length, 0));
        bool useHole = fit != bySize_.end();
        const int holeLength = useHole ? fit->first : 0;
        const int holeStart = useHole ? fit->second : 0;
        if (useHole && tailLength >= length) {
            // Обычный best fit служит выбором при равенстве прогнозов.
            useHole = holeLength <= tailLength;
            if (kTailLookahead) {
                auto largestIt = std::prev(bySize_.end());
                const int largestBefore = largestIt->first;
                int largestOther = largestBefore;
                if (largestIt->second == holeStart) {
                    if (largestIt == bySize_.begin()) {
                        largestOther = 0;
                    } else {
                        largestOther = std::prev(largestIt)->first;
                    }
                }
                const int largestAfterHole =
                    std::max(largestOther, holeLength - length);
                const double holeCost = expectedNextGrowth(
                    largestAfterHole, tailLength, length
                );
                const double tailCost = expectedNextGrowth(
                    largestBefore, tailLength - length, length
                );
                if (holeCost + kDecisionMargin < tailCost) {
                    useHole = true;
                } else if (tailCost + kDecisionMargin < holeCost) {
                    useHole = false;
                }
            }
        }
        int sections = 0;
        int coordinate = 0;
        if (useHole) {
            const int remainder = holeLength - length;
            const bool fromRight =
                kReleaseEdge && remainder > 0 && preferRightEdge(holeStart);
            coordinate = fromRight ? holeStart + remainder : holeStart;
            eraseHole(holes_.find(holeStart));
            addHole(fromRight ? holeStart : holeStart + length, remainder);
        } else {
            coordinate = frontier_;
            const int shortage = length - tailLength;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ += length;
        }
        const int pid = static_cast<int>(pipes_.size());
        pipes_.push_back(Pipe{coordinate, length});
        liveByStart_.emplace(coordinate, pid);
        livePidSum_ += pid;
        std::cout << sections << ' ' << coordinate << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const std::size_t index = static_cast<std::size_t>(pid);
        const Pipe old = pipes_[index];
        observeRelease(index);
        int mergedStart = old.start;
        int mergedLength = old.length;
        auto right = holes_.lower_bound(old.start);
        if (right != holes_.begin()) {
            auto left = std::prev(right);
            if (left->first + left->second == mergedStart) {
                mergedStart = left->first;
                mergedLength += left->second;
                eraseHole(left);
            }
        }
        if (right != holes_.end() &&
            mergedStart + mergedLength == right->first) {
            mergedLength += right->second;
            eraseHole(right);
        }
        if (mergedStart + mergedLength == frontier_) {
            // Освободившийся суффикс становится частью свободного хвоста.
            frontier_ = mergedStart;
        } else {
            addHole(mergedStart, mergedLength);
        }
        liveByStart_.erase(old.start);
        livePidSum_ -= static_cast<std::int64_t>(index);
        pipes_[index].length = 0;
        while (oldestLivePid_ < pipes_.size() &&
               pipes_[oldestLivePid_].length == 0) {
            ++oldestLivePid_;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.99; max_solver_rss_mib: 6.98

Here is additional text feedback about the current program:

Fitness F/T=0.857426348237; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737903587
family=short_phase_churn mean_F/T=0.785425831
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803960374
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808464826
family=short_heavy mean_F/T=0.815928978
family=additive_cohorts mean_F/T=0.822933487
family=distribution_switch mean_F/T=0.824892062
family=tiny_churn mean_F/T=0.829447561
family=size_biased_deletion mean_F/T=0.830175363
family=long_heavy mean_F/T=0.832958575
family=uniform_churn mean_F/T=0.835245846
family=size_lifetimes mean_F/T=0.843987138
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.867415603
family=large_live_set mean_F/T=0.880156087
family=micro_gap_refill mean_F/T=0.881250000
family=bimodal mean_F/T=0.882404172
family=recent_window_growth mean_F/T=0.882835317
family=fifo mean_F/T=0.885117596
family=section_boundaries mean_F/T=0.888648274
family=hotset_switching mean_F/T=0.889967103
family=soft_recency_growth mean_F/T=0.896811216
family=burst_drain mean_F/T=0.904727891
family=serial_growth mean_F/T=0.916984290
family=long_prefill_recent mean_F/T=0.917952203
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921026711
family=drain_recovery mean_F/T=0.926642283
family=hotset_growth mean_F/T=0.950357939
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.956143515
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001515 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001363 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001569 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001509 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001549 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001511 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611883779 F/B=0.646045362 B/T=0.947122005 overrun=0.055830 cpu_s=0.085322 rss_mib=1.766
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.619758318 F/B=0.675406191 B/T=0.917608286 overrun=0.089790 cpu_s=0.306749 rss_mib=1.984
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.326391 rss_mib=1.625
case=s31_060_large_live_set family=large_live_set F/T=0.631905345 F/B=0.641932619 B/T=0.984379554 overrun=0.015868 cpu_s=0.411736 rss_mib=2.781
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001474 rss_mib=1.328
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.018140 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001445 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002896 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013047 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002747 rss_mib=1.359
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.364106 rss_mib=1.656
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.326391 rss_mib=1.625
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.130107 rss_mib=1.719
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.337802 rss_mib=1.625
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002747 rss_mib=1.359
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.075150 rss_mib=1.422
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.047030 rss_mib=1.391
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.119598 rss_mib=1.484
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001741 rss_mib=1.328
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002334 rss_mib=1.375
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.527653 rss_mib=1.812
case=s31_102_serial_churn family=serial_churn F/T=0.820923913 F/B=0.950000000 B/T=0.864130435 overrun=0.157233 cpu_s=0.151059 rss_mib=1.484
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.338004 rss_mib=1.672
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.124386 rss_mib=1.594
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.827225131 F/B=0.954682779 B/T=0.866492147 overrun=0.154079 cpu_s=0.037851 rss_mib=1.391
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.034975 rss_mib=1.375

PAIRED SEARCH EVIDENCE
Against parent gen5: delta mean F/T=-0.000109698; improved/regressed/tied=26/11/115.
family=size_lifetimes delta_F/T=-0.019900550
family=hotset_switching delta_F/T=+0.008102850
family=serial_churn delta_F/T=+0.006976430
family=size_biased_deletion delta_F/T=-0.006703600
family=short_phase_churn delta_F/T=+0.003506601
family=fifo delta_F/T=-0.002033758
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_085_tiny_churn: delta_F/T=-0.041403162, delta_T=+20
s31_102_serial_churn: delta_F/T=-0.022930836, delta_T=+100
s31_063_size_biased_deletion: delta_F/T=-0.020005285, delta_T=+20
Gains:
s31_103_serial_churn: delta_F/T=+0.043999453, delta_T=-60
s31_086_tiny_churn: delta_F/T=+0.036643610, delta_T=-120
s31_096_hotset_switching: delta_F/T=+0.019401330, delta_T=-220
s31_128_short_phase_churn: delta_F/T=+0.014026403, delta_T=-100

Against leader gen5: delta mean F/T=-0.000109698; improved/regressed/tied=26/11/115.
family=size_lifetimes delta_F/T=-0.019900550
family=hotset_switching delta_F/T=+0.008102850
family=serial_churn delta_F/T=+0.006976430
family=size_biased_deletion delta_F/T=-0.006703600
family=short_phase_churn delta_F/T=+0.003506601
family=fifo delta_F/T=-0.002033758
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_085_tiny_churn: delta_F/T=-0.041403162, delta_T=+20
s31_102_serial_churn: delta_F/T=-0.022930836, delta_T=+100
s31_063_size_biased_deletion: delta_F/T=-0.020005285, delta_T=+20
Gains:
s31_103_serial_churn: delta_F/T=+0.043999453, delta_T=-60
s31_086_tiny_churn: delta_F/T=+0.036643610, delta_T=-120
s31_096_hotset_switching: delta_F/T=+0.019401330, delta_T=-220
s31_128_short_phase_churn: delta_F/T=+0.014026403, delta_T=-100

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857426348; mean positive loss on worst 16 cases=0.031251383; max case loss=0.075378788; regressed cases=37; worst family delta F/T=-0.020511308. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
