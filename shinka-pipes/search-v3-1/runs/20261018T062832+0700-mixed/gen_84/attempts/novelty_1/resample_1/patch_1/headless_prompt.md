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

**Добавьте повторяющиеся длины, сохранив стратификацию восьми сценариев.** Для `i = 0..3` постройте четыре сценария `(q[2*i+1], q[2*i+1], q[2*i+1])` и четыре сценария `(q[2*i], q[2*((i+1)%4)], q[2*((i+3)%4)])`, используя существующие восемь квантилей. Каждая позиция по-прежнему использует все квантили ровно один раз; мутация проверяет устойчивость размещений к сериям сходных запросов без усложнения статистики спроса, которое ранее не давало устойчивого выигрыша.

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
gen69 scarce_capacity_exchange; correct=True; parent=24; delta_F/T=-0.000957521; claim=Предлагаю учитывать дефицит свободной вместимости при сравнении родительской дыры с Best-Fit. Для каждого размера k поддерживается C[k] — количество труб размера k, помещающихся в текущие свободные интервалы, включая уже
  improved/regressed/tied=20/29/103
  regression s31_039_distribution_switch: delta_F/T=-0.046892992
  regression s31_063_size_biased_deletion: delta_F/T=-0.040963203
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen82 repeat_coupled_horizon; correct=True; parent=37; delta_F/T=+0.000059972; claim=Механизм — точный короткий прогноз совместной упаковки. Для каждого рассматриваемого gap оценивается минимальное расширение при трёх синтетических вставках. Восемь сценариев строятся исключительно по наблюдённым длинам: 
  improved/regressed/tied=31/28/93
  regression s31_041_drifting_sizes: delta_F/T=-0.047919294
  regression s31_126_short_phase_churn: delta_F/T=-0.043597263
gen81 exposure_normalized_release_veto; correct=True; parent=13; delta_F/T=+0.000017098; claim=Предлагаю один механизм: veto выбора правого края, если накопленные удаления показывают, что размер правого соседа освобождается заметно чаще размера левого. Родительский выбор отверстия, прогноз расширения и глобальный 
  improved/regressed/tied=8/10/134
  regression s31_096_hotset_switching: delta_F/T=-0.012454129
  regression s31_128_short_phase_churn: delta_F/T=-0.008471761
gen80 mixed_pair_tail_guard; correct=True; parent=23; delta_F/T=-0.000124226; claim=Добавляю один механизм: проверку совместной вместимости двух запросов разных размеров перед использованием свободного хвоста. Сохраняются Demand-Weighted Residual Fit и обе проверки capacity_guarded_tail. Новая проверка 
  improved/regressed/tied=5/9/138
  regression s31_054_additive_cohorts: delta_F/T=-0.009396259
  regression s31_096_hotset_switching: delta_F/T=-0.006917094
gen79 tail_pair_capacity_veto; correct=True; parent=23; delta_F/T=+0.000171423; claim=Добавляю один механизм: veto использования свободного хвоста по ожидаемой совместной вместимости для двух синтетических вставок. Родительские capacity guard, профиль длин и строгое сравнение стоимости одной вставки сохра
  improved/regressed/tied=8/17/127
  regression s31_062_size_biased_deletion: delta_F/T=-0.010971156
  regression s31_054_additive_cohorts: delta_F/T=-0.009396259
gen78 boundary_aligned_reclaimed_arena; correct=True; parent=0; delta_F/T=-0.000020470; claim=Предлагаю формировать двухстороннюю arena внутри уже существующей свободной дыры. При подтверждённом различии сроков жизни выбира
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.025056869; maximum case loss=0.072439174. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.90; max_solver_rss_mib: 2.56

Text feedback:
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
// NAME: scarce_capacity_exchange
// DESCRIPTION: Parent residual-fit and exposure-guided splitting,
// with a capacity-scarcity exchange against Best-Fit.
// Ablation: kEnableScarceCapacityExchange=false restores gen24.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kEnableExposureSplit = true;
    static constexpr bool kEnableScarceCapacityExchange = true;
    static constexpr long double kHazardPriorReleases = 2.0L;
    static constexpr long double kSplitRateRatio = 1.25L;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    using LiveMap = std::map<int, std::size_t>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    LiveMap live_;
    std::array<std::set<int>, kSmallLimit> bins_;
    std::set<std::pair<int, int>> large_;
    // Homogeneous capacity of internal holes; the tail is added on demand.
    std::array<std::int64_t, kMaxLength + 1> holeCapacity_{};
    std::uint64_t lowMask_ = 0;
    std::uint64_t highMask_ = 0;
    int trench_ = 0;
    int frontier_ = 0;
    std::size_t insertions_ = 0;
    std::array<std::uint32_t, kMaxLength + 1> observations_{};
    std::array<std::uint32_t, kMaxLength + 1> weights_{};
    std::array<std::int64_t, kSmallLimit> waste_{};
    std::int64_t totalWeight_ = 0;
    // Exposure is measured in live-pipe command steps.
    // Per-size exposure is settled lazily when its population changes.
    std::uint64_t commandClock_ = 0;
    std::size_t liveCount_ = 0;
    std::uint64_t totalReleases_ = 0;
    long double totalExposure_ = 0.0L;
    std::array<std::size_t, kMaxLength + 1> liveByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> releasesByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> exposureClock_{};
    std::array<long double, kMaxLength + 1> exposure_{};
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
    void beginCommand() {
        ++commandClock_;
        totalExposure_ += static_cast<long double>(liveCount_);
    }
    long double exposureAt(int length) const {
        return exposure_[length]
             + static_cast<long double>(liveByLength_[length])
             * static_cast<long double>(
                   commandClock_ - exposureClock_[length]);
    }
    void settleExposure(int length) {
        exposure_[length] = exposureAt(length);
        exposureClock_[length] = commandClock_;
    }
    void recordBirth(int length) {
        settleExposure(length);
        ++liveByLength_[length];
        ++liveCount_;
    }
    void recordRelease(int length) {
        settleExposure(length);
        --liveByLength_[length];
        --liveCount_;
        ++releasesByLength_[length];
        ++totalReleases_;
    }
    bool preferRightSplit(int start, int size, int length) const {
        if (!kEnableExposureSplit ||
            size == length ||
            totalReleases_ == 0) {
            return false;
        }
        const auto right = live_.lower_bound(start);
        if (right == live_.begin() || right == live_.end()) {
            return false;
        }
        const auto left = std::prev(right);
        const Pipe& leftPipe = pipes_[left->second];
        const Pipe& rightPipe = pipes_[right->second];
        if (leftPipe.start + leftPipe.length != start ||
            rightPipe.start != start + size ||
            leftPipe.length == rightPipe.length) {
            return false;
        }
        const long double priorExposure =
            kHazardPriorReleases * totalExposure_
            / static_cast<long double>(totalReleases_);
        const auto releaseRate = [&](int neighborLength) {
            const long double releases =
                static_cast<long double>(
                    releasesByLength_[neighborLength])
                + kHazardPriorReleases;
            return releases
                 / (exposureAt(neighborLength) + priorExposure);
        };
        // Leave the residual beside the neighbor with a sufficiently
        // higher estimated release rate.
        return releaseRate(leftPipe.length)
             > kSplitRateRatio * releaseRate(rightPipe.length);
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] += length / k;
            }
        }
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
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] -= length / k;
            }
        }
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
            // Here residual >= 40, and regret is nonnegative.
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
    std::pair<int, int> chooseScarcityExchange(
        int length, std::pair<int, int> parent) const {
        if (!kEnableScarceCapacityExchange ||
            parent.first < 0 || parent.second == length) {
            return parent;
        }
        std::pair<int, int> bestFit = parent;
        const std::uint64_t fittingLow =
            lowMask_ & (~std::uint64_t{0} << length);
        if (fittingLow != 0) {
            const int size = std::countr_zero(fittingLow);
            bestFit = {*bins_[size].begin(), size};
        } else if (highMask_ != 0) {
            const int size = 64 + std::countr_zero(highMask_);
            bestFit = {*bins_[size].begin(), size};
        } else if (!large_.empty()) {
            const auto candidate = *large_.begin();
            bestFit = {candidate.second, candidate.first};
        }
        if (bestFit.second >= parent.second) {
            return parent;
        }
        const int tail = trench_ - frontier_;
        const std::int64_t freeVolume = holeCapacity_[1] + tail;
        long double difference =
            static_cast<long double>(totalWeight_)
            * (std::min(bestFit.second - length, kMaxLength)
               - std::min(parent.second - length, kMaxLength));
        for (int k = 2; k <= kMaxLength; ++k) {
            const int remainder = length % k;
            if (remainder == 0) {
                continue;
            }
            // For s >= length, splitting loses an extra homogeneous
            // slot precisely when s % k < length % k.
            const int carryDifference =
                static_cast<int>(bestFit.second % k < remainder)
                - static_cast<int>(parent.second % k < remainder);
            if (carryDifference == 0) {
                continue;
            }
            const std::int64_t capacity =
                holeCapacity_[k] + tail / k;
            const std::int64_t pooledCapacity = freeVolume / k;
            // Different carry indicators imply a hole of size >= k,
            // hence capacity is positive. Pooled capacity is >= capacity.
            const long double penalty =
                static_cast<long double>(kRegretScale)
                * static_cast<long double>(weights_[k]) * k
                * static_cast<long double>(pooledCapacity)
                / static_cast<long double>(capacity);
            difference += carryDifference * penalty;
        }
        return difference < 0.0L ? bestFit : parent;
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
        beginCommand();
        observe(length);
        const auto chosen =
            chooseScarcityExchange(length, chooseHole(length));
        int start;
        int sections = 0;
        if (chosen.first >= 0) {
            const int holeStart = chosen.first;
            const int size = chosen.second;
            const bool splitRight =
                preferRightSplit(holeStart, size, length);
            eraseHole(holes_.find(holeStart));
            if (splitRight) {
                start = holeStart + size - length;
                addHole(holeStart, size - length);
            } else {
                start = holeStart;
                addHole(start + length, size - length);
            }
        } else {
            start = frontier_;
            const int missing = length - (trench_ - frontier_);
            if (missing > 0) {
                sections = (missing + 19) / 20;
                trench_ += sections * 20;
            }
            frontier_ += length;
        }
        const std::size_t pid = pipes_.size();
        pipes_.push_back({start, length});
        live_.emplace(start, pid);
        recordBirth(length);
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        beginCommand();
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        const int length = pipe.length;
        int start = pipe.start;
        int end = start + length;
        recordRelease(length);
        live_.erase(originalStart);
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.96; max_solver_rss_mib: 7.00

Here is additional text feedback about the current program:

Fitness F/T=0.857768360995; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737790388
family=short_phase_churn mean_F/T=0.787992087
family=drifting_sizes mean_F/T=0.800592585
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.804518839
family=short_rounding mean_F/T=0.818879585
family=distribution_switch mean_F/T=0.819379426
family=additive_cohorts mean_F/T=0.819584404
family=size_biased_deletion mean_F/T=0.821977053
family=short_heavy mean_F/T=0.826267648
family=tiny_churn mean_F/T=0.833601270
family=uniform_churn mean_F/T=0.839144287
family=long_heavy mean_F/T=0.839623918
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847075529
family=serial_churn mean_F/T=0.859534919
family=size_lifetimes mean_F/T=0.869160652
family=fifo mean_F/T=0.871117667
family=bimodal mean_F/T=0.878717767
family=large_live_set mean_F/T=0.880270940
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881844748
family=hotset_switching mean_F/T=0.886025038
family=section_boundaries mean_F/T=0.888814287
family=soft_recency_growth mean_F/T=0.897012698
family=burst_drain mean_F/T=0.910457307
family=serial_growth mean_F/T=0.916371801
family=long_prefill_recent mean_F/T=0.917772168
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920728456
family=drain_recovery mean_F/T=0.924504785
family=hotset_growth mean_F/T=0.950146436
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955712409
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001519 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001512 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001424 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001509 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001452 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001471 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611126393 F/B=0.646045362 B/T=0.945949663 overrun=0.057139 cpu_s=0.084135 rss_mib=1.812
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615796039 F/B=0.675406191 B/T=0.911741775 overrun=0.096802 cpu_s=0.300155 rss_mib=1.938
case=s31_060_large_live_set family=large_live_set F/T=0.632236996 F/B=0.641932619 B/T=0.984896198 overrun=0.015335 cpu_s=0.391472 rss_mib=2.859
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001409 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.313051 rss_mib=1.641
case=s31_040_distribution_switch family=distribution_switch F/T=0.645964126 F/B=0.692548077 B/T=0.932735426 overrun=0.072115 cpu_s=0.016793 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001469 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003411 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012406 rss_mib=1.438
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.332088 rss_mib=1.672
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755316039 F/B=0.950045956 B/T=0.795031056 overrun=0.257812 cpu_s=0.133614 rss_mib=1.734
case=s31_009_long_heavy family=long_heavy F/T=0.762500000 F/B=0.953125000 B/T=0.800000000 overrun=0.250000 cpu_s=0.350334 rss_mib=1.703
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.704723127 F/B=0.865400000 B/T=0.814332248 overrun=0.228000 cpu_s=0.074380 rss_mib=1.453
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.313051 rss_mib=1.641
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001719 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002367 rss_mib=1.391
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.059226 rss_mib=1.422
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.810256410 F/B=0.954682779 B/T=0.848717949 overrun=0.178248 cpu_s=0.040135 rss_mib=1.422
case=s31_039_distribution_switch family=distribution_switch F/T=0.808904110 F/B=0.952419355 B/T=0.849315068 overrun=0.177419 cpu_s=0.617064 rss_mib=1.938
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.113863 rss_mib=1.531
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822147368 F/B=0.950170316 B/T=0.865263158 overrun=0.155718 cpu_s=0.122662 rss_mib=1.656
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852686471 F/B=0.982097589 B/T=0.868229878 overrun=0.151769 cpu_s=0.154893 rss_mib=2.391
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030207 rss_mib=1.422
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.670988655 F/B=0.768089054 B/T=0.873581848 overrun=0.144712 cpu_s=0.019598 rss_mib=1.391

PAIRED SEARCH EVIDENCE
Against parent gen24: delta mean F/T=-0.000957521; improved/regressed/tied=20/29/103.
family=distribution_switch delta_F/T=-0.013801107
family=short_heavy delta_F/T=+0.010958264
family=size_biased_deletion delta_F/T=-0.010813050
family=size_lifetimes delta_F/T=-0.008836681
family=bimodal delta_F/T=-0.006932050
family=drifting_sizes delta_F/T=-0.003950533
Regressions:
s31_039_distribution_switch: delta_F/T=-0.046892992, delta_T=+80
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_029_size_lifetimes: delta_F/T=-0.035346722, delta_T=+160
s31_014_bimodal: delta_F/T=-0.024725047, delta_T=+140
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_055_additive_cohorts: delta_F/T=+0.015673401, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.012500000, delta_T=-20
s31_094_hotset_switching: delta_F/T=+0.007496252, delta_T=-20

Against leader gen61: delta mean F/T=-0.001793105; improved/regressed/tied=28/52/72.
family=bimodal delta_F/T=-0.017917181
family=distribution_switch delta_F/T=-0.015104647
family=section_boundaries delta_F/T=-0.012647196
family=short_rounding delta_F/T=+0.010657895
family=long_heavy delta_F/T=-0.010132211
family=size_biased_deletion delta_F/T=-0.009398144
Regressions:
s31_014_bimodal: delta_F/T=-0.039493211, delta_T=+220
s31_039_distribution_switch: delta_F/T=-0.034667319, delta_T=+60
s31_020_section_boundaries: delta_F/T=-0.027011372, delta_T=+160
s31_009_long_heavy: delta_F/T=-0.026293103, delta_T=+40
Gains:
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_127_short_phase_churn: delta_F/T=+0.018736786, delta_T=-20
s31_006_short_heavy: delta_F/T=+0.016176471, delta_T=-20
s31_022_fifo: delta_F/T=+0.015767207, delta_T=-100

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857768361; mean positive loss on worst 16 cases=0.025056869; max case loss=0.072439174; regressed cases=40; worst family delta F/T=-0.026023943. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
