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

**Ускорьте адаптацию распределения только для `buildScenarios()`.** Заведите отдельные `forecastDemand_` и `forecastMass_`, уменьшайте счётчики вдвое при массе 64 и стройте квантили по весам `2*forecastDemand_[k]+1` с общей массой `2*forecastMass_+40`; существующий `demand_` продолжайте использовать в остальных эвристиках. Такая мутация примерно сохраняет относительную силу prior при более короткой памяти и проверяет гипотезу, что запаздывание распределения способствует потерям в `drifting_sizes` и `distribution_switch`.

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
gen23 capacity_guarded_tail; correct=True; parent=None; delta_F/T=n/a; claim=Crossover сохраняет выбор внутренних дыр из gen6 и дополняет хвостовую политику gen14 одним механизмом: проверкой совместной потери вместимости двух затронутых интервалов.
При длине дыры h, хвоста t и вставки L использов
  improved/regressed/tied=24/25/103
  regression s31_049_geometric_cohorts: delta_F/T=-0.039689922
  regression s31_009_long_heavy: delta_F/T=-0.038793103
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen77 scarcity_capacity_tail; correct=True; parent=20; delta_F/T=-0.002129679; claim=Crossover сохраняет сравнение двух ближайших размеров и scarcity guard родителя. Переносится один механизм: отдельное правило выбора свободного хвоста. Точное попадание сохраняет приоритет; при остальных запросах родител
  improved/regressed/tied=28/53/71
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_087_tiny_churn: delta_F/T=-0.049673203
gen76 oldest_release_run_veto; correct=True; parent=52; delta_F/T=-0.000093882; claim=Предлагаю условно запрещать merge utility переопределять порядок соседей, когда последние удаления подтверждают FIFO. Родитель оценивает общий уклон к старым PID; новый механизм дополнительно наблюдает, удалялась ли имен
  improved/regressed/tied=2/3/147
  regression s31_063_size_biased_deletion: delta_F/T=-0.062943459
  regression s31_023_fifo: delta_F/T=-0.017793367
gen75 tail_coalescence_guard; correct=True; parent=14; delta_F/T=+0.000631444; claim=Добавляю один механизм: запрет замены выбранной дыры свободным хвостом, если такая замена уменьшает полезность последующего слияния с правым соседом. Сохраняются Demand-Weighted Residual Fit, текущий профиль длин и строг
  improved/regressed/tied=23/16/113
  regression s31_052_geometric_cohorts: delta_F/T=-0.027073269
  regression s31_096_hotset_switching: delta_F/T=-0.024214955
gen74 prequential_forecast_mixture; correct=True; parent=61; delta_F/T=-0.000347969; claim=Механизм — prequential fixed-share смесь двух прогнозов длин исключительно для buildScenarios(). Сохраняется родительская demand_; добавляется отдельная короткая история forecastDemand_ с уменьшением счётчиков вдвое при 
  improved/regressed/tied=26/28/98
  regression s31_033_burst_drain: delta_F/T=-0.022564103
  regression s31_094_hotset_switching: delta_F/T=-0.022492128
gen73 preexisting_tail_arena; correct=True; parent=0; delta_F/T=+0.000174374; claim=Механизм: вставка, потребовавшая расширения, размещается у левого края минимально необходимого хвоста. Двусторонняя arena допускается только из свободного хвоста, существовавшего перед вс
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.027172662; maximum case loss=0.075378788. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
#include <bit>
// NAME: capacity_guarded_tail
// DESCRIPTION: Demand-Weighted Residual Fit с проверкой совместной
// вместимости перед применением marginal_tail_growth.
//
// Хвост используется вместо выбранной дыры только при строгом уменьшении
// ожидаемого роста для следующей вставки и неувеличении взвешенной суммы
// остатков двух затронутых свободных интервалов.
//
// Ablation относительно gen6: preferFreeTail всегда возвращает false.
// Ablation проверки вместимости: удалить отмеченный guard, получив gen14.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    std::array<std::set<int>, kSmallLimit> bins_;
    std::set<std::pair<int, int>> large_;
    std::uint64_t lowMask_ = 0;
    std::uint64_t highMask_ = 0;
    int trench_ = 0;
    int frontier_ = 0;
    std::size_t insertions_ = 0;
    std::array<std::uint32_t, kMaxLength + 1> observations_{};
    std::array<std::uint32_t, kMaxLength + 1> weights_{};
    std::array<std::int64_t, kSmallLimit> waste_{};
    std::int64_t totalWeight_ = 0;
    void rebuildProfile() {
        waste_.fill(0);
        totalWeight_ = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            weights_[k] = observations_[k] + 1;
            const std::int64_t weight = weights_[k];
            totalWeight_ += weight;
            int remainder = 0;
            for (int s = 0; s < kSmallLimit; ++s) {
                waste_[s] += weight * remainder;
                if (++remainder == k) {
                    remainder = 0;
                }
            }
        }
    }
    void observe(int length) {
        ++insertions_;
        ++observations_[length];
        if ((insertions_ & 511u) == 0) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observations_[k] >>= 1;
            }
        }
        if (insertions_ <= 32 || (insertions_ & 63u) == 0) {
            rebuildProfile();
        }
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        if (length < kSmallLimit) {
            bins_[length].insert(start);
            if (length < 64) {
                lowMask_ |= std::uint64_t{1} << length;
            } else {
                highMask_ |= std::uint64_t{1} << (length - 64);
            }
        } else {
            large_.emplace(length, start);
        }
    }
    void eraseHole(HoleMap::iterator it) {
        const int start = it->first;
        const int length = it->second;
        if (length < kSmallLimit) {
            auto& bin = bins_[length];
            bin.erase(start);
            if (bin.empty()) {
                if (length < 64) {
                    lowMask_ &= ~(std::uint64_t{1} << length);
                } else {
                    highMask_ &= ~(std::uint64_t{1} << (length - 64));
                }
            }
        } else {
            large_.erase(std::make_pair(length, start));
        }
        holes_.erase(it);
    }
    std::pair<int, int> chooseHole(int length) const {
        if (!bins_[length].empty()) {
            return {*bins_[length].begin(), length};
        }
        int bestStart = -1;
        int bestSize = 0;
        std::int64_t bestScore =
            std::numeric_limits<std::int64_t>::max();
        const auto consider = [&](int size) {
            const int residual = size - length;
            const std::int64_t regret =
                waste_[residual] + waste_[length] - waste_[size];
            const std::int64_t score =
                kRegretScale * regret
                + totalWeight_ * std::min(residual, kMaxLength);
            if (score < bestScore ||
                (score == bestScore && size < bestSize)) {
                bestScore = score;
                bestSize = size;
                bestStart = *bins_[size].begin();
            }
        };
        std::uint64_t mask =
            lowMask_ & (~std::uint64_t{0} << length);
        while (mask != 0) {
            const int size = std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        mask = highMask_;
        while (mask != 0) {
            const int size = 64 + std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        if (!large_.empty()) {
            const auto candidate = *large_.begin();
            const int size = candidate.first;
            const int start = candidate.second;
            if (bestStart < 0) {
                return {start, size};
            }
            // Здесь residual >= 40, а regret неотрицателен.
            std::int64_t score = totalWeight_ * kMaxLength;
            if (score < bestScore) {
                for (int k = 2; k <= kMaxLength; ++k) {
                    const int remainder = length % k;
                    if (remainder != 0 && size % k < remainder) {
                        score += kRegretScale
                               * static_cast<std::int64_t>(weights_[k]) * k;
                        if (score >= bestScore) {
                            break;
                        }
                    }
                }
                if (score < bestScore) {
                    bestStart = start;
                    bestSize = size;
                }
            }
        }
        return {bestStart, bestSize};
    }
    bool preferFreeTail(int length, int holeSize) const {
        const int tail = trench_ - frontier_;
        if (tail < length || tail >= kMaxLength ||
            !large_.empty() || holeSize - length >= kMaxLength) {
            return false;
        }
        // Capacity guard: суммарная свободная длина одинакова,
        // поэтому меньшая сумма остатков означает большую взвешенную
        // вместимость для однородных продолжений каждого размера.
        // Здесь tail < 40 и holeSize < 80: все индексы допустимы.
        const std::int64_t wasteAfterHole =
            waste_[holeSize - length] + waste_[tail];
        const std::int64_t wasteAfterTail =
            waste_[holeSize] + waste_[tail - length];
        if (wasteAfterTail > wasteAfterHole) {
            return false;
        }
        // После исключения выбранной дыры находим крупнейшую оставшуюся.
        std::uint64_t low = lowMask_;
        std::uint64_t high = highMask_;
        if (bins_[holeSize].size() == 1) {
            if (holeSize < 64) {
                low &= ~(std::uint64_t{1} << holeSize);
            } else {
                high &= ~(std::uint64_t{1} << (holeSize - 64));
            }
        }
        if (high != 0) {
            return false;
        }
        const int largestOther =
            low == 0 ? 0 : 63 - std::countl_zero(low);
        const int largestAfterHole =
            std::max(largestOther, holeSize - length);
        if (largestAfterHole >= kMaxLength) {
            return false;
        }
        const int largestAfterTail = std::max(largestOther, holeSize);
        std::int64_t holeCost = 0;
        std::int64_t tailCost = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            const int missingAfterHole = k > largestAfterHole
                ? std::max(0, k - tail) : 0;
            const int missingAfterTail = k > largestAfterTail
                ? std::max(0, k - (tail - length)) : 0;
            const std::int64_t weight = weights_[k];
            holeCost += weight * ((missingAfterHole + 19) / 20);
            tailCost += weight * ((missingAfterTail + 19) / 20);
        }
        return tailCost < holeCost;
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        pipes_.reserve(200001);
        pipes_.push_back({0, 0});
        rebuildProfile();
    }
    void place(int length) {
        observe(length);
        const auto chosen = chooseHole(length);
        int start;
        int sections = 0;
        if (chosen.first >= 0 &&
            !preferFreeTail(length, chosen.second)) {
            start = chosen.first;
            const int size = chosen.second;
            eraseHole(holes_.find(start));
            addHole(start + length, size - length);
        } else {
            start = frontier_;
            const int missing = length - (trench_ - frontier_);
            if (missing > 0) {
                sections = (missing + 19) / 20;
                trench_ += sections * 20;
            }
            frontier_ += length;
        }
        pipes_.push_back({start, length});
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        int start = pipe.start;
        int end = start + pipe.length;
        pipe.length = 0;
        auto next = holes_.lower_bound(start);
        if (next != holes_.begin()) {
            auto previous = std::prev(next);
            if (previous->first + previous->second == start) {
                start = previous->first;
                eraseHole(previous);
            }
        }
        if (next != holes_.end() && next->first == end) {
            end += next->second;
            eraseHole(next);
        }
        if (end == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, end - start);
        }
        std::cout << originalStart << '\n';
        std::cout.flush();
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.89; max_solver_rss_mib: 2.55

Here is additional text feedback about the current program:

Fitness F/T=0.857608298922; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737933618
family=short_phase_churn mean_F/T=0.782545303
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.802607687
family=drifting_sizes mean_F/T=0.805009888
family=short_rounding mean_F/T=0.818879585
family=additive_cohorts mean_F/T=0.821523893
family=short_heavy mean_F/T=0.823775225
family=distribution_switch mean_F/T=0.824018292
family=uniform_churn mean_F/T=0.833157585
family=size_biased_deletion mean_F/T=0.833560375
family=tiny_churn mean_F/T=0.835116112
family=long_heavy mean_F/T=0.839345751
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847436039
family=size_lifetimes mean_F/T=0.852986650
family=serial_churn mean_F/T=0.863333638
family=large_live_set mean_F/T=0.879207521
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882402103
family=fifo mean_F/T=0.882521668
family=bimodal mean_F/T=0.882709140
family=hotset_switching mean_F/T=0.884439341
family=section_boundaries mean_F/T=0.884857643
family=soft_recency_growth mean_F/T=0.897183443
family=burst_drain mean_F/T=0.900233006
family=serial_growth mean_F/T=0.915131030
family=long_prefill_recent mean_F/T=0.917760678
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920733211
family=drain_recovery mean_F/T=0.924594964
family=hotset_growth mean_F/T=0.950321727
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955211623
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001587 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001378 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001539 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001488 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001419 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611546931 F/B=0.646045362 B/T=0.946600606 overrun=0.056412 cpu_s=0.080543 rss_mib=1.562
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618206011 F/B=0.675406191 B/T=0.915309956 overrun=0.092526 cpu_s=0.288909 rss_mib=1.734
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.380251 rss_mib=2.078
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001481 rss_mib=1.328
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.308019 rss_mib=1.641
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001395 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002832 rss_mib=1.344
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012401 rss_mib=1.344
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.016531 rss_mib=1.391
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002924 rss_mib=1.344
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.321746 rss_mib=1.656
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.354148 rss_mib=1.688
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.121164 rss_mib=1.562
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002924 rss_mib=1.344
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.072333 rss_mib=1.438
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.062892 rss_mib=1.422
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.308019 rss_mib=1.641
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.112850 rss_mib=1.469
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001739 rss_mib=1.328
case=s31_017_section_boundaries family=section_boundaries F/T=0.801020408 F/B=0.957317073 B/T=0.836734694 overrun=0.195122 cpu_s=0.029773 rss_mib=1.406
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002364 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.112628 rss_mib=1.469
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.605690 rss_mib=1.922
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.328973 rss_mib=1.672
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.118221 rss_mib=1.547
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854099424 F/B=0.982097589 B/T=0.869668588 overrun=0.149863 cpu_s=0.149900 rss_mib=1.859

PAIRED SEARCH EVIDENCE
Against parent gen6: delta mean F/T=+0.000044246; improved/regressed/tied=24/25/103.
family=long_heavy delta_F/T=-0.009698276
family=section_boundaries delta_F/T=-0.009131027
family=size_lifetimes delta_F/T=+0.007803794
family=size_biased_deletion delta_F/T=+0.007521829
family=hotset_switching delta_F/T=-0.005852406
family=short_phase_churn delta_F/T=+0.005789561
Regressions:
s31_049_geometric_cohorts: delta_F/T=-0.039689922, delta_T=+40
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
s31_006_short_heavy: delta_F/T=-0.016176471, delta_T=+20
Gains:
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_052_geometric_cohorts: delta_F/T=+0.027073269, delta_T=-180
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20

Against leader gen6: delta mean F/T=+0.000044246; improved/regressed/tied=24/25/103.
family=long_heavy delta_F/T=-0.009698276
family=section_boundaries delta_F/T=-0.009131027
family=size_lifetimes delta_F/T=+0.007803794
family=size_biased_deletion delta_F/T=+0.007521829
family=hotset_switching delta_F/T=-0.005852406
family=short_phase_churn delta_F/T=+0.005789561
Regressions:
s31_049_geometric_cohorts: delta_F/T=-0.039689922, delta_T=+40
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
s31_006_short_heavy: delta_F/T=-0.016176471, delta_T=+20
Gains:
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_052_geometric_cohorts: delta_F/T=+0.027073269, delta_T=-180
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857608299; mean positive loss on worst 16 cases=0.027172662; max case loss=0.075378788; regressed cases=35; worst family delta F/T=-0.021385077. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
