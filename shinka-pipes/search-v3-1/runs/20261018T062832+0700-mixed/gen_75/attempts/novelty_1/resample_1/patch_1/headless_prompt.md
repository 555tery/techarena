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

**Добавьте ограничение, сохраняющее полезность слияния при замене fallback.** Рассчитайте для каждого кандидата `G = releaseGain(...)` с его фактическим остатком и стороной; разрешайте замену только при строго меньшем `projectedGrowth()` и `G_candidate >= G_fallback`. Это проверит, связаны ли потери в `size_lifetimes` и `size_biased_deletion` с тем, что прогноз только вставок отменяет перспективное слияние, выбранное родительской эвристикой.

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
gen14 marginal_tail_growth; correct=True; parent=6; delta_F/T=-0.000318501; claim=Добавляю причинное сравнение свободного хвоста с выбранной родителем дырой. Родитель всегда предпочитает внутреннюю дыру. Новый механизм использует хвост, если текущая вставка помещается туда без расширения и это строго 
  improved/regressed/tied=23/28/101
  regression s31_008_short_heavy: delta_F/T=-0.047813195
  regression s31_049_geometric_cohorts: delta_F/T=-0.039689922
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen73 preexisting_tail_arena; correct=True; parent=0; delta_F/T=+0.000174374; claim=Механизм: вставка, потребовавшая расширения, размещается у левого края минимально необходимого хвоста. Двусторонняя arena допускается только из свободного хвоста, существовавшего перед вставкой; соответствующая логика уж
  improved/regressed/tied=9/9/134
  regression s31_062_size_biased_deletion: delta_F/T=-0.006869067
  regression s31_064_size_biased_deletion: delta_F/T=-0.003859311
gen72 scarce_merge_orientation; correct=True; parent=5; delta_F/T=+0.000659216; claim=Предлагаю выбирать сторону размещения внутри уже выбранной родителем дыры. Остаток оставляется рядом с тем соседом, освобождение которого создаст более полезный свободный интервал.
Для остатка r и освобождаемого компонен
  improved/regressed/tied=45/34/73
  regression s31_023_fifo: delta_F/T=-0.051286765
  regression s31_085_tiny_churn: delta_F/T=-0.041403162
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
  regression s31_039_distribution_switch: delta_F
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=specialist; specialist families=['soft_recency_growth']; fixed-baseline tail loss=0.027358686; maximum case loss=0.075378788. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
#include <bit>
// NAME: Demand-Weighted Residual Fit
// DESCRIPTION: Слияние свободных интервалов, выбор по полезности остатка
// и сохранение свободного хвоста для последующего расширения.
//
// Для интервала s и запроса L оценивается дополнительная потеря вместимости:
// R(s,L) = sum_k w[k]*k*(floor(s/k)-floor((s-L)/k)-floor(L/k)).
// Веса отражают недавние вставки с равномерным prior. Минимизируется
// 8*R(s,L) + sum(w)*min(s-L,40); при равенстве выбирается меньший интервал,
// затем меньшая координата. Exact fit всегда оптимален по этой оценке.
// Для размеров <80 рассматриваются все непустые bins, для остальных —
// наименьший интервал. Свободный хвост используется после внутренних дыр.
//
// Вставка: амортизированно O(log H + 80), удаление: O(log H).
// Память: O(P + H), где P — число вставок, H — число свободных интервалов.
// Возможный недостаток: смена распределения размеров и корреляция удалений
// могут сделать оценку по отдельным размерам неудачной; резервирование хвоста
// также не гарантирует оптимального результата.
// Ablation: kRegretScale = 0 даёт best fit с тем же резервированием хвоста.
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
        if (chosen.first >= 0) {
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.95; max_solver_rss_mib: 2.53

Text feedback:
Fitness F/T=0.857564053155; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737946754
family=short_phase_churn mean_F/T=0.776755742
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.806604357
family=drifting_sizes mean_F/T=0.807955077
family=short_rounding mean_F/T=0.819122721
family=additive_cohorts mean_F/T=0.819378118
family=distribution_switch mean_F/T=0.820810083
family=size_biased_deletion mean_F/T=0.826038546
family=short_heavy mean_F/T=0.827819343
family=uniform_churn mean_F/T=0.827991557
family=tiny_churn mean_F/T=0.833601270
family=size_lifetimes mean_F/T=0.845182856
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847436039
family=long_heavy mean_F/T=0.849044027
family=serial_churn mean_F/T=0.863333638
family=large_live_set mean_F/T=0.879520330
family=fifo mean_F/T=0.880675115
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881559926
family=bimodal mean_F/T=0.882004094
family=hotset_switching mean_F/T=0.890291747
family=section_boundaries mean_F/T=0.893988670
family=soft_recency_growth mean_F/T=0.896746977
family=burst_drain mean_F/T=0.900233006
family=serial_growth mean_F/T=0.915099989
family=long_prefill_recent mean_F/T=0.917801654
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920787398
family=drain_recovery mean_F/T=0.924449312
family=hotset_growth mean_F/T=0.949668303
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955008751
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001579 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001372 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001411 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001546 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001614 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001517 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611294538 F/B=0.646045362 B/T=0.946209933 overrun=0.056848 cpu_s=0.093510 rss_mib=1.594
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.614837303 F/B=0.675406191 B/T=0.910322279 overrun=0.098512 cpu_s=0.297119 rss_mib=1.734
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.309624 rss_mib=1.609
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.397293 rss_mib=2.062
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001449 rss_mib=1.328
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.017193 rss_mib=1.375
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001391 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002967 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012462 rss_mib=1.375
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002825 rss_mib=1.344
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.330749 rss_mib=1.625
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.128026 rss_mib=1.609
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.309624 rss_mib=1.609
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002825 rss_mib=1.344
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.055803 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.075360 rss_mib=1.406
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.355054 rss_mib=1.672
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.117100 rss_mib=1.438
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001748 rss_mib=1.328
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002415 rss_mib=1.344
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.114424 rss_mib=1.469
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.622728 rss_mib=1.922
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.827225131 F/B=0.954682779 B/T=0.866492147 overrun=0.154079 cpu_s=0.036782 rss_mib=1.359
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.115655 rss_mib=1.469
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.825972927 F/B=0.950170316 B/T=0.869289340 overrun=0.150365 cpu_s=0.121358 rss_mib=1.531
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.034676 rss_mib=1.375

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.002582845; improved/regressed/tied=48/36/68.
family=fifo delta_F/T=+0.049665734
family=tiny_churn delta_F/T=+0.048597604
family=short_heavy delta_F/T=+0.044112001
family=distribution_switch delta_F/T=-0.024593286
family=size_biased_deletion delta_F/T=-0.019121059
family=size_lifetimes delta_F/T=-0.016528432
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_039_distribution_switch: delta_F/T=-0.061204395, delta_T=+100
s31_063_size_biased_deletion: delta_F/T=-0.039121447, delta_T=+40
s31_040_distribution_switch: delta_F/T=-0.030607258, delta_T=+200
Gains:
s31_024_fifo: delta_F/T=+0.130986590, delta_T=-300
s31_006_short_heavy: delta_F/T=+0.101521298, delta_T=-140
s31_086_tiny_churn: delta_F/T=+0.100272770, delta_T=-380
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857564053; mean positive loss on worst 16 cases=0.025648965; max case loss=0.075378788; regressed cases=36; worst family delta F/T=-0.024593286. These are selection diagnostics; primary fitness remains mean F/T.

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
NAME: validated_transition_profile
DESCRIPTION:
Preserve the adjacent_release_edge placement policy.
Use a first-order insertion-length profile only when its
prequential Brier advantage over the parent's marginal profile
is positive within the recent transition window.
Conditional rows have 16 marginal-profile pseudo-observations
and require at least eight observed transitions.
Score each transition before incorporating its outcome.
All physical lengths and placements remain exact.
Ablation: set enableValidatedTransitionProfile_ to false.
*/
class Allocator {
    static constexpr bool enableValidatedTransitionProfile_ = true;
    static constexpr int transitionPrior_ = 16;
    static constexpr int minimumTransitionSupport_ = 8;
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
    std::array<std::array<int, 41>, 41> transitionCount_{};
    std::array<int, 41> transitionMass_{};
    std::array<double, 41> transitionGain_{};
    std::array<int, 512> recentFrom_{};
    std::array<double, 512> recentGain_{};
    int lastLength_ = 0;
    double prequentialGain(int length) const {
        if (lastLength_ == 0 ||
            transitionMass_[lastLength_] == 0) {
            return 0.0;
        }
        const double inverseGlobalMass =
            1.0 / static_cast<double>(recentCount_ + 40);
        const double inverseConditionalMass =
            1.0 / static_cast<double>(
                transitionPrior_ + transitionMass_[lastLength_]);
        double gain = 0.0;
        for (int size = 1; size <= 40; ++size) {
            const double marginal =
                frequency_[size] * inverseGlobalMass;
            const double conditional =
                (transitionCount_[lastLength_][size] +
                 transitionPrior_ * marginal) *
                inverseConditionalMass;
            const double outcome = size == length ? 1.0 : 0.0;
            const double marginalError = marginal - outcome;
            const double conditionalError = conditional - outcome;
            gain += marginalError * marginalError -
                    conditionalError * conditionalError;
        }
        return gain;
    }
    void rememberLength(int length) {
        // Evaluate both forecasts using only the preceding history.
        const double gain = prequentialGain(length);
        if (recentCount_ == recent_.size()) {
            const int oldLength = recent_[recentCursor_];
            const int oldFrom = recentFrom_[recentCursor_];
            --frequency_[oldLength];
            if (oldFrom != 0) {
                --transitionCount_[oldFrom][oldLength];
                --transitionMass_[oldFrom];
                transitionGain_[oldFrom] -=
                    recentGain_[recentCursor_];
                if (transitionMass_[oldFrom] == 0) {
                    transitionGain_[oldFrom] = 0.0;
                }
            }
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentFrom_[recentCursor_] = lastLength_;
        recentGain_[recentCursor_] = gain;
        if (lastLength_ != 0) {
            ++transitionCount_[lastLength_][length];
            ++transitionMass_[lastLength_];
            transitionGain_[lastLength_] += gain;
        }
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        lastLength_ = length;
        bool useTransitions = false;
        if constexpr (enableValidatedTransitionProfile_) {
            useTransitions =
                transitionMass_[length] >= minimumTransitionSupport_ &&
                transitionGain_[length] > 0.0;
        }
        const int globalMass = static_cast<int>(recentCount_) + 40;
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            const int size = bound + 1;
            int mass = frequency_[size];
            if (useTransitions) {
                // A common denominator cancels in all placement
                // comparisons, so integer masses suffice.
                mass = transitionPrior_ * mass +
                       globalMass * transitionCount_[length][size];
            }
            massAbove_[bound] = massAbove_[bound + 1] + mass;
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // ceil((length - suffixLength) / 20) is at most two.
        // Growth is needed only when length > largestHole.
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.98; max_solver_rss_mib: 6.98

Text feedback:
Fitness F/T=0.857763717751; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737848564
family=short_phase_churn mean_F/T=0.786603427
family=geometric_cohorts mean_F/T=0.800531484
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.804914186
family=additive_cohorts mean_F/T=0.818063788
family=short_rounding mean_F/T=0.819122721
family=distribution_switch mean_F/T=0.825807738
family=short_heavy mean_F/T=0.827914946
family=tiny_churn mean_F/T=0.833601270
family=size_biased_deletion mean_F/T=0.834088859
family=long_heavy mean_F/T=0.836628052
family=uniform_churn mean_F/T=0.836830051
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.856961750
family=size_lifetimes mean_F/T=0.867265606
family=fifo mean_F/T=0.874590682
family=section_boundaries mean_F/T=0.877823395
family=large_live_set mean_F/T=0.880160636
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882110786
family=hotset_switching mean_F/T=0.882752514
family=bimodal mean_F/T=0.885391376
family=soft_recency_growth mean_F/T=0.896417892
family=burst_drain mean_F/T=0.907973080
family=serial_growth mean_F/T=0.915347262
family=long_prefill_recent mean_F/T=0.917824636
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920991108
family=drain_recovery mean_F/T=0.923925194
family=hotset_growth mean_F/T=0.949739969
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955438751
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001534 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001300 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001366 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001387 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001406 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001484 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611968048 F/B=0.646045362 B/T=0.947252445 overrun=0.055685 cpu_s=0.084459 rss_mib=1.812
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.616950476 F/B=0.675406191 B/T=0.913451023 overrun=0.094749 cpu_s=0.311988 rss_mib=1.984
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.323650 rss_mib=1.625
case=s31_060_large_live_set family=large_live_set F/T=0.631979015 F/B=0.641932619 B/T=0.984494317 overrun=0.015750 cpu_s=0.416402 rss_mib=2.891
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001384 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001399 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002864 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.017527 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012673 rss_mib=1.453
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.019450 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.337144 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.357307 rss_mib=1.672
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.323650 rss_mib=1.625
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.130225 rss_mib=1.703
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002844 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.714026403 F/B=0.865400000 B/T=0.825082508 overrun=0.212000 cpu_s=0.076670 rss_mib=1.422
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001740 rss_mib=1.344
case=s31_017_section_boundaries family=section_boundaries F/T=0.801020408 F/B=0.957317073 B/T=0.836734694 overrun=0.195122 cpu_s=0.030114 rss_mib=1.391
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002342 rss_mib=1.375
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.039099 rss_mib=1.391
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.115221 rss_mib=1.500
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821801347 F/B=0.950170316 B/T=0.864898990 overrun=0.156204 cpu_s=0.126796 rss_mib=1.609
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.335681 rss_mib=1.656
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.156356 rss_mib=2.438
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.019450 rss_mib=1.391
case=s31_039_distribution_switch family=distribution_switch F/T=0.831690141 F/B=0.952419355 B/T=0.873239437 overrun=0.145161 cpu_s=0.632654 rss_mib=1.906

PAIRED SEARCH EVIDENCE
Against parent gen15: delta mean F/T=-0.000523529; improved/regressed/tied=14/15/123.
family=size_biased_deletion delta_F/T=-0.010240801
family=serial_churn delta_F/T=-0.005861194
family=fifo delta_F/T=-0.005133258
family=drifting_sizes delta_F/T=+0.003162953
family=drain_recovery delta_F/T=-0.002071154
family=short_phase_churn delta_F/T=+0.002048955
Regressions:
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.023444776, delta_T=+100
s31_024_fifo: delta_F/T=-0.020533033, delta_T=+40
s31_040_distribution_switch: delta_F/T=-0.008969862, delta_T=+60
Gains:
s31_044_drifting_sizes: delta_F/T=+0.011591338, delta_T=-100
s31_128_short_phase_churn: delta_F/T=+0.008195820, delta_T=-60
s31_038_distribution_switch: delta_F/T=+0.003327029, delta_T=-20
s31_093_hotset_switching: delta_F/T=+0.002179103, delta_T=-180

Against leader gen24: delta mean F/T=-0.000962164; improved/regressed/tied=32/46/74.
family=section_boundaries delta_F/T=-0.014769034
family=short_heavy delta_F/T=+0.012605561
family=size_lifetimes delta_F/T=-0.010731726
family=distribution_switch delta_F/T=-0.007372795
family=geometric_cohorts delta_F/T=-0.004127326
family=serial_churn delta_F/T=-0.003719502
Regressions:
s31_017_section_boundaries: delta_F/T=-0.052240461, delta_T=+60
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_029_size_lifetimes: delta_F/T=-0.039570136, delta_T=+180
s31_039_distribution_switch: delta_F/T=-0.024106961, delta_T=+40
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_008_short_heavy: delta_F/T=+0.030293542, delta_T=-60
s31_062_size_biased_deletion: delta_F/T=+0.027939876, delta_T=-260
s31_064_size_biased_deletion: delta_F/T=+0.020105916, delta_T=-2460

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857763718; mean positive loss on worst 16 cases=0.023009976; max case loss=0.052240461; regressed cases=40; worst family delta F/T=-0.019595632. These are selection diagnostics; primary fitness remains mean F/T.


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
// NAME: marginal_tail_growth
// DESCRIPTION: Родительский Demand-Weighted Residual Fit с причинным
// сравнением внутренней дыры и уже свободного хвоста.
//
// Для интервала s и запроса L оценивается дополнительная потеря вместимости:
// R(s,L) = sum_k w[k]*k*(floor(s/k)-floor((s-L)/k)-floor(L/k)).
// Веса отражают недавние вставки с равномерным prior. Минимизируется
// 8*R(s,L) + sum(w)*min(s-L,40); при равенстве выбирается меньший интервал,
// затем меньшая координата. Exact fit всегда оптимален по этой оценке.
// Для размеров <80 рассматриваются все непустые bins, для остальных —
// наименьший интервал.
//
// Если текущая вставка помещается в хвост без роста, сравнивается ожидаемое
// число новых секций для одной следующей вставки по существующим weights_.
// Учитываются наибольшая оставшаяся дыра и длина оставшегося хвоста.
// Хвост выбирается только при строгом уменьшении этой стоимости.
// Перед любым расширением сохраняется глобальный поиск подходящей дыры.
//
// Вставка: амортизированно O(log H + 80), удаление: O(log H).
// Сравнение хвоста добавляет не более 40 шагов без новых контейнеров.
// Память: O(P + H), где P — число вставок, H — число свободных интервалов.
// Недостаток: одношаговая оценка не учитывает последующие удаления
// и может недооценить пользу хвоста для более длинного продолжения.
// Ablation: preferFreeTail возвращает false, восстанавливая родителя.
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
        // После исключения выбранной дыры находим крупнейшую оставшуюся.
        // Здесь holeSize < kSmallLimit, поскольку large_ пуста.
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.91; max_solver_rss_mib: 2.53

Here is additional text feedback about the current program:

Fitness F/T=0.857245552211; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737933618
family=short_phase_churn mean_F/T=0.782545303
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.802607687
family=drifting_sizes mean_F/T=0.803891454
family=short_heavy mean_F/T=0.815866044
family=short_rounding mean_F/T=0.818879585
family=additive_cohorts mean_F/T=0.821523893
family=distribution_switch mean_F/T=0.824018292
family=tiny_churn mean_F/T=0.830637449
family=uniform_churn mean_F/T=0.833157585
family=size_biased_deletion mean_F/T=0.833560375
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
family=hotset_switching mean_F/T=0.884299426
family=section_boundaries mean_F/T=0.884857643
family=soft_recency_growth mean_F/T=0.897002870
family=burst_drain mean_F/T=0.900233006
family=serial_growth mean_F/T=0.915248431
family=long_prefill_recent mean_F/T=0.917756126
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920710641
family=drain_recovery mean_F/T=0.924594964
family=hotset_growth mean_F/T=0.950250837
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955234625
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001616 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001379 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001447 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001524 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001488 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001492 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611546931 F/B=0.646045362 B/T=0.946600606 overrun=0.056412 cpu_s=0.083601 rss_mib=1.578
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618206011 F/B=0.675406191 B/T=0.915309956 overrun=0.092526 cpu_s=0.297928 rss_mib=1.750
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.393768 rss_mib=2.062
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001465 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.314121 rss_mib=1.625
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001588 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002945 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012705 rss_mib=1.359
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.019222 rss_mib=1.359
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002959 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.326981 rss_mib=1.625
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.354233 rss_mib=1.672
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.123974 rss_mib=1.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002959 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.693429487 F/B=0.865400000 B/T=0.801282051 overrun=0.248000 cpu_s=0.073698 rss_mib=1.406
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.060846 rss_mib=1.391
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.314121 rss_mib=1.625
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.113254 rss_mib=1.453
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001761 rss_mib=1.344
case=s31_017_section_boundaries family=section_boundaries F/T=0.801020408 F/B=0.957317073 B/T=0.836734694 overrun=0.195122 cpu_s=0.030540 rss_mib=1.391
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002378 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.113828 rss_mib=1.469
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.621768 rss_mib=1.906
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.121194 rss_mib=1.531
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854099424 F/B=0.982097589 B/T=0.869668588 overrun=0.149863 cpu_s=0.152783 rss_mib=1.828
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.670988655 F/B=0.768089054 B/T=0.873581848 overrun=0.144712 cpu_s=0.020073 rss_mib=1.375

PAIRED SEARCH EVIDENCE
Against parent gen6: delta mean F/T=-0.000318501; improved/regressed/tied=23/28/101.
family=short_heavy delta_F/T=-0.011953299
family=long_heavy delta_F/T=-0.009698276
family=section_boundaries delta_F/T=-0.009131027
family=size_lifetimes delta_F/T=+0.007803794
family=size_biased_deletion delta_F/T=+0.007521829
family=hotset_switching delta_F/T=-0.005992320
Regressions:
s31_008_short_heavy: delta_F/T=-0.047813195, delta_T=+100
s31_049_geometric_cohorts: delta_F/T=-0.039689922, delta_T=+40
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
Gains:
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_052_geometric_cohorts: delta_F/T=+0.027073269, delta_T=-180
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20

Against leader gen6: delta mean F/T=-0.000318501; improved/regressed/tied=23/28/101.
family=short_heavy delta_F/T=-0.011953299
family=long_heavy delta_F/T=-0.009698276
family=section_boundaries delta_F/T=-0.009131027
family=size_lifetimes delta_F/T=+0.007803794
family=size_biased_deletion delta_F/T=+0.007521829
family=hotset_switching delta_F/T=-0.005992320
Regressions:
s31_008_short_heavy: delta_F/T=-0.047813195, delta_T=+100
s31_049_geometric_cohorts: delta_F/T=-0.039689922, delta_T=+40
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_017_section_boundaries: delta_F/T=-0.034085975, delta_T=+40
Gains:
s31_127_short_phase_churn: delta_F/T=+0.036640827, delta_T=-40
s31_052_geometric_cohorts: delta_F/T=+0.027073269, delta_T=-180
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857245552; mean positive loss on worst 16 cases=0.027358686; max case loss=0.075378788; regressed cases=37; worst family delta F/T=-0.021385077. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
