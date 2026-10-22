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

**Ускоряйте обновление профиля спроса при обнаруженной смене распределения.** Ведите histogram последних 64 вставок и каждые 16 вставок сравнивайте его нормированное распределение с накопленным через `0.5 × Σ|pRecent[k] − pLong[k]|`. При значении выше 0,25 пересчитывайте `weights_` из равной смеси этих распределений, сохраняя суммарный вес наблюдений и prior `+1`; иначе используйте исходный профиль. Это направлено на `drifting_sizes` и `distribution_switch` и сохраняет успешную формулу штрафа разбиения.

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
gen51 large_gap_residue_frontier; correct=True; parent=6; delta_F/T=+0.000051322; claim=Механизм расширяет поиск среди больших дыр, сохраняя родительскую формулу score. Сейчас для размеров ≥80 проверяется только наименьшая дыра, хотя штраф за потерю вместимости немонотонен по размеру. Предлагается проверять
  improved/regressed/tied=28/25/99
  regression s31_043_drifting_sizes: delta_F/T=-0.022196443
  regression s31_017_section_boundaries: delta_F/T=-0.017398050
gen52 conditional_merge_utility_edge; correct=True; parent=13; delta_F/T=+0.001435106; claim=Предлагаю оценивать край размещения по полезности будущего слияния. Родитель учитывает порядок PID соседей, но игнорирует их длины: освобождение короткого соседа может оставить остаток практически бесполезным.
Для остатк
  improved/regressed/tied=17/16/119
  regression s31_022_fifo: delta_F/T=-0.057960564
  regression s31_086_tiny_churn: delta_F/T=-0.024788324
gen55 demand_funded_lifetime_arena; correct=True; parent=0; delta_F/T=+0.000183147; claim=Предлагаю создавать lifetime arena только из уже оплаченного пространства. Сейчас growFor может дополнительно раскопать до трёх длин текущей трубы ради будущего разделения по времени жизни. Патч оставляет только минималь
  improved/regressed/tied=9/9/134
  regression s31_062_size_biased_deletion: delta_F/T=-0.006869067
  regression s31_064_size_biased_deletion: delta_F/T=-0.003859311
gen54 bellman_ties_release_edge; correct=True; parent=15; delta_F/T=-0.001305584; claim=Crossover сохраняет выбор края из `adjacent_release_edge` и добавляет двухшаговый Bellman-прогноз только для разрешения равенства одношаговых оценок между best-fit дырой и суффиксом.
Это повтор Bellman с изменённым взаим
  improved/regressed/tied=29/27/96
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_007_short_heavy: delta_F/T=-0.041309524
gen53 survivor_censored_release_clock; correct=True; parent=0; delta_F/T=+0.000703061; claim=Новый механизм заменяет независимые Bernoulli-события освобождения соседей совместной моделью времени. Родительские оценки deletion rate преобразуются обратно в относительные интенсивности `r = p / (1-p)`. Предполагается
  improved/regressed/tied=45/30/77
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_126_short_phase_churn: delta_F/T=-0.040992647
gen50 persistent_markov_slot_demand; correct=True; parent=34; delta_F/T=+0.000191120; claim=Механизм: прогнозировать повторения размеров через причинную Markov-модель, сохраняя родительский finite-horizon slot inventory.
Сейчас число будущих запросов каждого размера моделируется Binomial-распределением: порядок
  improved/regressed/tied=24/14/114
  regression s31_087_tiny_churn: delta_F/T=-0.044444444
  regression s31_017_section_boundaries: delta_F/T=-0.035552536
gen49 mixed_sequence_gap_dp; correct=True; parent=37; delta_F/T=-0.006936727; claim=Новый механизм — Bellman DP для смешанных последовательностей запросов. Для каждого небольшого gap вычисляется ожидаемая длина, которую он обслужит за четыре гипотетические вставки. Размеры берутся из наблюдавшегося расп
  improved/regressed/tied=37/48/6
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.026642086; maximum case loss=0.075378788. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
// NAME: Demand-Weighted Residual Fit
// DESCRIPTION: Слияние свободных интервалов, выбор по полезности остатка
// и сохранение свободного хвоста для последующего расширения.
//
// Для интервала s и запроса L оценивается дополнительная потеря вместимости:
// R(s,L) = sum_k w[k]*k*(floor(s/k)-floor((s-L)/k)-floor(L/k)).
// Веса отражают недавние вставки с равномерным prior. Минимизируется
// 8*R(s,L) + sum(w)*min(s-L,40); при равенстве выбирается меньший интервал,
// затем меньшая координата. Exact fit всегда оптимален по этой оценке.
// Для размеров <80 рассматриваются все непустые bins. Для больших дыр
// оценивается левейшая дыра каждого из первых восьми различных размеров.
// Формула score прежняя; при равенстве сохраняется меньший размер.
// Свободный хвост используется после внутренних дыр.
//
// Вставка: амортизированно O(80 + 8*40 + 9*log H), удаление: O(log H).
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
            constexpr int kLargeProbes = 8;
            // Здесь residual >= 40, а regret неотрицателен.
            const std::int64_t baseScore = totalWeight_ * kMaxLength;
            auto candidate = large_.begin();
            for (int probe = 0;
                 probe < kLargeProbes && candidate != large_.end()
                     && baseScore < bestScore;
                 ++probe) {
                const int size = candidate->first;
                const int start = candidate->second;
                std::int64_t score = baseScore;
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
                    bestScore = score;
                }
                if (bestScore == baseScore) {
                    break;
                }
                candidate = large_.upper_bound(
                    std::make_pair(size, std::numeric_limits<int>::max()));
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

Here are the performance metrics of the program:

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.90; max_solver_rss_mib: 2.56

Here is additional text feedback about the current program:

Fitness F/T=0.857615375348; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737300593
family=short_phase_churn mean_F/T=0.776755742
family=drifting_sizes mean_F/T=0.796643258
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.811954596
family=additive_cohorts mean_F/T=0.817903786
family=short_rounding mean_F/T=0.819122721
family=distribution_switch mean_F/T=0.825823614
family=size_biased_deletion mean_F/T=0.828983484
family=short_heavy mean_F/T=0.829674936
family=uniform_churn mean_F/T=0.833405058
family=tiny_churn mean_F/T=0.833601270
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847544635
family=long_heavy mean_F/T=0.849674608
family=size_lifetimes mean_F/T=0.850056666
family=serial_churn mean_F/T=0.859817359
family=large_live_set mean_F/T=0.880181686
family=bimodal mean_F/T=0.880480218
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881631753
family=fifo mean_F/T=0.882673759
family=hotset_switching mean_F/T=0.884882245
family=section_boundaries mean_F/T=0.889334007
family=soft_recency_growth mean_F/T=0.896995100
family=burst_drain mean_F/T=0.899799347
family=serial_growth mean_F/T=0.915756746
family=long_prefill_recent mean_F/T=0.917728817
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920742241
family=drain_recovery mean_F/T=0.924777256
family=hotset_growth mean_F/T=0.950305574
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955254571
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001549 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001374 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001344 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001448 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001384 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001473 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611294538 F/B=0.646045362 B/T=0.946209933 overrun=0.056848 cpu_s=0.081074 rss_mib=1.547
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615124611 F/B=0.675406191 B/T=0.910747664 overrun=0.097999 cpu_s=0.292825 rss_mib=1.734
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.390184 rss_mib=2.078
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001433 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.312140 rss_mib=1.625
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001342 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002884 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.654772727 F/B=0.692548077 B/T=0.945454545 overrun=0.057692 cpu_s=0.016801 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012314 rss_mib=1.375
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002885 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.330836 rss_mib=1.656
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.686825397 F/B=0.865400000 B/T=0.793650794 overrun=0.260000 cpu_s=0.073244 rss_mib=1.422
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.759478325 F/B=0.950045956 B/T=0.799412197 overrun=0.250919 cpu_s=0.126445 rss_mib=1.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002885 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.312140 rss_mib=1.625
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.060319 rss_mib=1.438
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.349528 rss_mib=1.656
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.120034 rss_mib=1.469
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001723 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002438 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.119083 rss_mib=1.484
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.030253 rss_mib=1.391
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.820075598 F/B=0.950170316 B/T=0.863082738 overrun=0.158637 cpu_s=0.127184 rss_mib=1.547
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.112418 rss_mib=1.484
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854591984 F/B=0.982097589 B/T=0.870170127 overrun=0.149201 cpu_s=0.153539 rss_mib=1.844
case=s31_039_distribution_switch family=distribution_switch F/T=0.831690141 F/B=0.952419355 B/T=0.873239437 overrun=0.145161 cpu_s=0.616655 rss_mib=1.922

PAIRED SEARCH EVIDENCE
Against parent gen6: delta mean F/T=+0.000051322; improved/regressed/tied=28/25/99.
family=drifting_sizes delta_F/T=-0.011311819
family=uniform_churn delta_F/T=+0.005413501
family=hotset_switching delta_F/T=-0.005409502
family=geometric_cohorts delta_F/T=+0.005350239
family=distribution_switch delta_F/T=+0.005013530
family=size_lifetimes delta_F/T=+0.004873810
Regressions:
s31_043_drifting_sizes: delta_F/T=-0.022196443, delta_T=+500
s31_017_section_boundaries: delta_F/T=-0.017398050, delta_T=+20
s31_096_hotset_switching: delta_F/T=-0.014140054, delta_T=+160
s31_102_serial_churn: delta_F/T=-0.014065119, delta_T=+60
Gains:
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20
s31_023_fifo: delta_F/T=+0.017793367, delta_T=-20
s31_052_geometric_cohorts: delta_F/T=+0.017791005, delta_T=-120

Against leader gen24: delta mean F/T=-0.001110506; improved/regressed/tied=37/40/75.
family=size_lifetimes delta_F/T=-0.027940666
family=short_heavy delta_F/T=+0.014365552
family=long_heavy delta_F/T=+0.013175690
family=burst_drain delta_F/T=-0.011534834
family=fifo delta_F/T=+0.011406414
family=short_phase_churn delta_F/T=-0.011236345
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.060079365, delta_T=+60
s31_033_burst_drain: delta_F/T=-0.044027517, delta_T=+40
s31_127_short_phase_churn: delta_F/T=-0.036640827, delta_T=+40
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_062_size_biased_deletion: delta_F/T=+0.025722426, delta_T=-240
s31_064_size_biased_deletion: delta_F/T=+0.022629212, delta_T=-2760

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857615375; mean positive loss on worst 16 cases=0.026642086; max case loss=0.075378788; regressed cases=35; worst family delta F/T=-0.019579756. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
