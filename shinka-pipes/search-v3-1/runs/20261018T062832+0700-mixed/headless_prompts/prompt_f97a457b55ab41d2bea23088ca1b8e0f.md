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

**Расширьте выбор адреса внутри выбранного размерного класса.** При ненулевом остатке рассматривайте минимальный и максимальный адреса из `bins_[size]`, оценивая оба края размещения для каждого кандидата. Выбирайте по ожидаемой полезности слияния: интенсивность освобождения соседа умножайте на взвешенный спрос на размеры, которые сможет обслужить объединённый интервал. Такая мутация сохраняет быстрый поиск по bins и текущий выбор размера, одновременно проверяя два ограничения лидера: единственный адрес-кандидат и выбор края преимущественно по интенсивности освобождения.

RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Best-Fit: attempts=1; score_range=0.857332383..0.857332383
First-Fit: attempts=1; score_range=0.847432251..0.847432251
Independent 1: attempts=1; score_range=0.856788966..0.856788966
Independent 2: attempts=1; score_range=0.857536047..0.857536047
Independent 3: attempts=1; score_range=0.857564053..0.857564053
Independent 4: attempts=1; score_range=0.856555151..0.856555151
SEARCH-v2 generation 27: attempts=1; score_range=0.855381088..0.855381088
adjacent_release_edge: attempts=1; score_range=0.858287247..0.858287247
age_conditioned_neighbor_release: attempts=1; score_range=0.854363465..0.854363465
appendable_wilderness: attempts=1; score_range=0.854861671..0.854861671
capacity_guarded_tail: attempts=1; score_range=0.857608299..0.857608299
causal_bellman_pair_pricing: attempts=1; score_range=0.857074884..0.857074884
gen20 scarcity_fit_guard; correct=True; parent=11; delta_F/T=+0.001594366; claim=Предлагаю учитывать дефицит подходящих gaps при разрешении обмена. Родитель по-прежнему сравнивает Best-Fit со следующим строго большим gap через splitPenalty. Новый guard разрешает предложенный обмен, только если он не 
  improved/regressed/tied=22/16/114
  regression s31_015_bimodal: delta_F/T=-0.038297872
  regression s31_102_serial_churn: delta_F/T=-0.013606474
gen24 exposure_guided_split; correct=True; parent=6; delta_F/T=+0.001161829; claim=Родитель gen6 сохраняется: размеры bins меньше 80, коэффициент regret 8, prior 1 на размер, обновление профиля каждые 64 вставки после первых 32, уменьшение наблюдений вдвое каждые 512 вставок.
Новый механизм выбирает ст
  improved/regressed/tied=39/37/76
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_009_long_heavy: delta_F/T=-0.038793103
gen35 age_conditioned_neighbor_release; correct=True; parent=0; delta_F/T=-0.000617743; claim=Механизм: возрастная поправка к прогнозу освобождения живых соседей. Для каждой длины отдельно учитываются deaths и exposure в возрастах 0–63, 64–511 и ≥512 команд. Две очереди переводят выжившие трубы между категориями,
  improved/regressed/tied=45/31/76
  regression s31_086_tiny_churn: delta_F/T=-0.109818438
  regression s31_063_size_biased_deletion: delta_F/T=-0.057406471
gen34 finite_horizon_slot_shortfall; correct=True; parent=26; delta_F/T=-0.000751229; claim=Предлагаю оценивать потерю повторно используемого слота через ожидаемый дефицит на следующих 12 вставках. Родитель `reusable_slot_inventory` сохраняется: тот же запас N_s = Σ floor(gap_length/s), кандидаты, прогноз удале
  improved/regressed/tied=25/48/79
  regression s31_006_short_heavy: delta_F/T=-0.051071429
  regression s31_063_size_biased_deletion: delta_F/T=-0.040963203
gen33 appendable_wilderness; correct=True; parent=0; delta_F/T=-0.000119537; claim=Механизм: сохранять свободный суффикс присоединяемым к следующему обязательному расширению. Труба всегда занимает левый край tail gap; growFor добавляет только секции, необходимые текущей вставке. Разделение по прогнозир
  improved/regressed/tied=10/12/130
  regression s31_063_size_biased_deletion: delta_F/T=-0.039121447
  regression s31_102_serial_churn: delta_F/T=-0.009535082
gen32 release_bridge_excavation; correct=True; parent=17; delta_F/T=+0.000098868; claim=Единственный новый механизм — скидка к excavation pricing за возможность восстановить подходящий gap одним удалением до следующей вставки. Родитель сохраняется: candidate selection, renewal utility, геометрия слияния, вы
  improved/regressed/tied=11/13/128
  regression s31_041_drifting_sizes: delta_F/T=-0.053781703
  regression s31_049_geometric_cohorts: delta_F/T=-0.039689922
gen31 tied_bellman_release; correct=True; parent=15; delta_F/T=-0.001305584; claim=Родитель — gen15 `adjacent_release_edge`. Единственный добавленный механизм: двухшаговый Bellman-прогноз разрешает равенства одношаговой оценки при выборе между внутренней дырой и суффиксом. Выбор края, распределение дли
  improved/regressed/tied=29/27/96
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_007_short_heavy: delta_F/T=-0.041309524
gen30 causal_bellman_pair_pricing; correct=True; parent=22; delta_F/T=-0.000220957; claim=Пр
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.025654128; maximum case loss=0.061204395. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
using Coordinate = std::int64_t;
class Allocator {
    struct Pipe { Coordinate start; int length; };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    std::map<Coordinate, std::size_t> live_;
    std::uint32_t olderFirst_ = 0, youngerFirst_ = 0;
    void observeRelease(std::size_t released, std::size_t survivor) {
        if (olderFirst_ + youngerFirst_ >= 128) {
            olderFirst_ /= 2;
            youngerFirst_ /= 2;
        }
        if (released < survivor)
            ++olderFirst_;
        else
            ++youngerFirst_;
    }
    bool leaveRemainderOnLeft(Coordinate a, Coordinate b, int length) const {
        if (b - a <= length || b == trench_) return false;
        const std::int64_t balance =
            static_cast<std::int64_t>(olderFirst_) - youngerFirst_;
        const std::int64_t observations = olderFirst_ + youngerFirst_;
        if (balance * balance <= 4 * observations) return false;
        const auto right = live_.lower_bound(a);
        if (right == live_.begin() || right == live_.end()) return false;
        const auto left = std::prev(right);
        return (left->second < right->second) == (balance > 0);
    }
    static int bucket(Coordinate n) { return static_cast<int>(std::min<Coordinate>(40, n)); }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b-a, a});
        starts_[bucket(b-a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b-a, a});
        starts_[bucket(b-a)].erase(a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        Coordinate at = -1, digs = 0;
        if constexpr (false) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) at = candidate->second;
        }
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
                at = gaps_.rbegin()->first;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_);
        }
        const Coordinate finish = gaps_.at(at);
        const Coordinate begin = at;
        erase(at);
        if (leaveRemainderOnLeft(begin, finish, length))
            at = finish - length;
        add(begin, at);
        add(at + length, finish);
        live_.emplace(at, pipes_.size());
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
        const auto current = live_.find(p.start);
        if (current != live_.begin())
            observeRelease(current->second, std::prev(current)->second);
        const auto next = std::next(current);
        if (next != live_.end())
            observeRelease(current->second, next->second);
        live_.erase(current);
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) { a = left->first; erase(a); }
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.03; max_solver_rss_mib: 9.98

Text feedback:
Fitness F/T=0.856900376516; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.738063804
family=short_phase_churn mean_F/T=0.782611261
family=drifting_sizes mean_F/T=0.793016864
family=geometric_cohorts mean_F/T=0.798442696
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.808708439
family=short_heavy mean_F/T=0.817190751
family=additive_cohorts mean_F/T=0.819301629
family=distribution_switch mean_F/T=0.822438880
family=tiny_churn mean_F/T=0.826302773
family=size_biased_deletion mean_F/T=0.827336904
family=uniform_churn mean_F/T=0.833614896
family=long_heavy mean_F/T=0.844089261
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847803715
family=size_lifetimes mean_F/T=0.863311107
family=serial_churn mean_F/T=0.871118591
family=fifo mean_F/T=0.879256489
family=large_live_set mean_F/T=0.879681053
family=hotset_switching mean_F/T=0.879831968
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881349466
family=bimodal mean_F/T=0.885319408
family=section_boundaries mean_F/T=0.890545121
family=burst_drain mean_F/T=0.894810870
family=soft_recency_growth mean_F/T=0.896712793
family=serial_growth mean_F/T=0.917775702
family=long_prefill_recent mean_F/T=0.918002355
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920981197
family=drain_recovery mean_F/T=0.927463972
family=hotset_growth mean_F/T=0.950522243
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.956031478
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001528 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001391 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001370 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001412 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001516 rss_mib=1.312
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001470 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.612981101 F/B=0.646045362 B/T=0.948820527 overrun=0.053940 cpu_s=0.087918 rss_mib=2.188
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.614933043 F/B=0.675406191 B/T=0.910464030 overrun=0.098341 cpu_s=0.316711 rss_mib=3.391
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.325503 rss_mib=2.922
case=s31_060_large_live_set family=large_live_set F/T=0.632126407 F/B=0.641932619 B/T=0.984723923 overrun=0.015513 cpu_s=0.418086 rss_mib=4.531
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001388 rss_mib=1.328
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.017473 rss_mib=1.422
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001436 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002999 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012637 rss_mib=1.484
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.669814241 F/B=0.865400000 B/T=0.773993808 overrun=0.292000 cpu_s=0.075633 rss_mib=1.656
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.669814241 F/B=0.865400000 B/T=0.773993808 overrun=0.292000 cpu_s=0.075633 rss_mib=1.656
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.336700 rss_mib=2.953
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.325503 rss_mib=2.922
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.754213791 F/B=0.950045956 B/T=0.793870850 overrun=0.259651 cpu_s=0.134698 rss_mib=2.172
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002804 rss_mib=1.375
case=s31_009_long_heavy family=long_heavy F/T=0.775423729 F/B=0.953125000 B/T=0.813559322 overrun=0.229167 cpu_s=0.446014 rss_mib=3.016
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.041671 rss_mib=1.500
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001704 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002326 rss_mib=1.359
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.802030457 F/B=0.954682779 B/T=0.840101523 overrun=0.190332 cpu_s=0.035739 rss_mib=1.516
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.034418 rss_mib=1.500
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.516660 rss_mib=3.312
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.335867 rss_mib=2.969
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.115329 rss_mib=1.875
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.824577703 F/B=0.950170316 B/T=0.867820946 overrun=0.152311 cpu_s=0.127696 rss_mib=2.016
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854407207 F/B=0.982097589 B/T=0.869981982 overrun=0.149449 cpu_s=0.163600 rss_mib=3.344

PAIRED SEARCH EVIDENCE
Against parent gen3: delta mean F/T=-0.000432007; improved/regressed/tied=43/25/84.
family=serial_churn delta_F/T=+0.013010508
family=long_heavy delta_F/T=+0.011949124
family=tiny_churn delta_F/T=-0.011911362
family=drifting_sizes delta_F/T=-0.010290753
family=size_biased_deletion delta_F/T=-0.009792643
family=bimodal delta_F/T=+0.008150294
Regressions:
s31_085_tiny_churn: delta_F/T=-0.041403162, delta_T=+20
s31_062_size_biased_deletion: delta_F/T=-0.031742630, delta_T=+300
s31_044_drifting_sizes: delta_F/T=-0.030347571, delta_T=+280
s31_049_geometric_cohorts: delta_F/T=-0.020295983, delta_T=+20
Gains:
s31_103_serial_churn: delta_F/T=+0.043999453, delta_T=-60
s31_009_long_heavy: delta_F/T=+0.037520503, delta_T=-60
s31_014_bimodal: delta_F/T=+0.031793400, delta_T=-180
s31_012_long_heavy: delta_F/T=+0.009526436, delta_T=-80

Against leader gen20: delta mean F/T=-0.001447191; improved/regressed/tied=45/42/65.
family=drifting_sizes delta_F/T=-0.019730694
family=fifo delta_F/T=-0.015763239
family=size_biased_deletion delta_F/T=-0.015526091
family=geometric_cohorts delta_F/T=-0.013233295
family=serial_churn delta_F/T=+0.011156447
family=size_lifetimes delta_F/T=-0.010319602
Regressions:
s31_085_tiny_churn: delta_F/T=-0.041403162, delta_T=+20
s31_044_drifting_sizes: delta_F/T=-0.039530021, delta_T=+360
s31_030_size_lifetimes: delta_F/T=-0.037446809, delta_T=+40
s31_023_fifo: delta_F/T=-0.036343899, delta_T=+40
Gains:
s31_103_serial_churn: delta_F/T=+0.029813837, delta_T=-40
s31_086_tiny_churn: delta_F/T=+0.024064460, delta_T=-80
s31_001_uniform_churn: delta_F/T=+0.019390244, delta_T=-20
s31_015_bimodal: delta_F/T=+0.018750000, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.856900377; mean positive loss on worst 16 cases=0.027965173; max case loss=0.052023597; regressed cases=41; worst family delta F/T=-0.022964489. These are selection diagnostics; primary fitness remains mean F/T.

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
    struct Pipe { Coordinate start; int length; };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    static int bucket(Coordinate n) { return static_cast<int>(std::min<Coordinate>(40, n)); }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b-a, a});
        starts_[bucket(b-a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b-a, a});
        starts_[bucket(b-a)].erase(a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        Coordinate at = -1, digs = 0;
        if constexpr (false) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) at = candidate->second;
        }
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
                at = gaps_.rbegin()->first;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_);
        }
        const Coordinate finish = gaps_.at(at);
        erase(at);
        add(at + length, finish);
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) { a = left->first; erase(a); }
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.36; max_solver_rss_mib: 5.64

Text feedback:
Fitness F/T=0.857332383246; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737768271
family=short_phase_churn mean_F/T=0.785915949
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803307617
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808464826
family=short_heavy mean_F/T=0.815928978
family=additive_cohorts mean_F/T=0.822933487
family=distribution_switch mean_F/T=0.828134940
family=long_heavy mean_F/T=0.832140136
family=uniform_churn mean_F/T=0.835086173
family=size_biased_deletion mean_F/T=0.837129548
family=tiny_churn mean_F/T=0.838214135
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.858108083
family=size_lifetimes mean_F/T=0.866732131
family=hotset_switching mean_F/T=0.876089163
family=bimodal mean_F/T=0.877169114
family=large_live_set mean_F/T=0.881134705
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882029077
family=fifo mean_F/T=0.886847360
family=section_boundaries mean_F/T=0.887708414
family=burst_drain mean_F/T=0.894747543
family=soft_recency_growth mean_F/T=0.895967786
family=serial_growth mean_F/T=0.915700639
family=long_prefill_recent mean_F/T=0.917738148
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920891892
family=drain_recovery mean_F/T=0.924242183
family=hotset_growth mean_F/T=0.949413287
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955399574
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001501 rss_mib=1.297
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001355 rss_mib=1.297
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001386 rss_mib=1.297
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001427 rss_mib=1.297
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001503 rss_mib=1.297
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001468 rss_mib=1.297
case=s31_118_partial_drain family=partial_drain F/T=0.612558588 F/B=0.646045362 B/T=0.948166529 overrun=0.054667 cpu_s=0.085796 rss_mib=1.984
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618012520 F/B=0.675406191 B/T=0.915023474 overrun=0.092868 cpu_s=0.316263 rss_mib=3.109
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.329717 rss_mib=2.922
case=s31_060_large_live_set family=large_live_set F/T=0.632126407 F/B=0.641932619 B/T=0.984723923 overrun=0.015513 cpu_s=0.424694 rss_mib=3.797
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001410 rss_mib=1.297
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001416 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003724 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012797 rss_mib=1.422
case=s31_040_distribution_switch family=distribution_switch F/T=0.666898148 F/B=0.692548077 B/T=0.962962963 overrun=0.038462 cpu_s=0.017932 rss_mib=1.422
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002781 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.750182 rss_mib=2.531
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.329717 rss_mib=2.922
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.149187 rss_mib=2.062
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.354893 rss_mib=2.953
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002781 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.079996 rss_mib=1.641
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.079425 rss_mib=1.500
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001833 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002373 rss_mib=1.359
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=1.104163 rss_mib=2.203
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.713259 rss_mib=2.172
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.148238 rss_mib=2.000
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.039194 rss_mib=1.500
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.161876 rss_mib=2.781
case=s31_086_tiny_churn family=tiny_churn F/T=0.836466165 F/B=0.959051724 B/T=0.872180451 overrun=0.146552 cpu_s=0.117083 rss_mib=1.828
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.044475 rss_mib=1.500

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.002351175; improved/regressed/tied=50/40/62.
family=fifo delta_F/T=+0.055837979
family=tiny_churn delta_F/T=+0.053210469
family=short_heavy delta_F/T=+0.032221636
family=distribution_switch delta_F/T=-0.017268430
family=additive_cohorts delta_F/T=+0.015570054
family=short_phase_churn delta_F/T=+0.014335884
Regressions:
s31_039_distribution_switch: delta_F/T=-0.049653143, delta_T=+80
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_009_long_heavy: delta_F/T=-0.037520503, delta_T=+60
Gains:
s31_024_fifo: delta_F/T=+0.141686903, delta_T=-320
s31_086_tiny_churn: delta_F/T=+0.118724230, delta_T=-440
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40
s31_006_short_heavy: delta_F/T=+0.085344828, delta_T=-120

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857332383; mean positive loss on worst 16 cases=0.025373426; max case loss=0.049653143; regressed cases=40; worst family delta F/T=-0.017268430. These are selection diagnostics; primary fitness remains mean F/T.


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
class Allocator {
    struct Pipe { Coordinate start; int length; };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
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
            if (demand_[k] != 0 && space % k < length % k)
                result += static_cast<std::uint64_t>(demand_[k]) * k;
        }
        return result;
    }
    bool scarcityAllowsExchange(Coordinate smaller, Coordinate larger, int length) const {
        std::size_t fittingGaps = 0;
        long double extraLoss = 0;
        for (int k = 40; k >= 1; --k) {
            fittingGaps += starts_[k].size();
            if (demand_[k] == 0 || fittingGaps == 0) continue;
            const int smallerLoses = smaller >= k && smaller - length < k;
            const int largerLoses = larger >= k && larger - length < k;
            if (smallerLoses != largerLoses) {
                extraLoss += static_cast<long double>(demand_[k]) /
                             static_cast<long double>(fittingGaps) *
                             (largerLoses - smallerLoses);
            }
        }
        return extraLoss <= 0;
    }
    static int bucket(Coordinate n) { return static_cast<int>(std::min<Coordinate>(40, n)); }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b-a, a});
        starts_[bucket(b-a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b-a, a});
        starts_[bucket(b-a)].erase(a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        observeLength(length);
        Coordinate at = -1, digs = 0;
        if constexpr (false) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) {
                if (candidate->first > length) {
                    const auto penalty = splitPenalty(candidate->first, length);
                    if (penalty != 0) {
                        auto larger = sizes_.upper_bound(
                            {candidate->first, std::numeric_limits<Coordinate>::max()});
                        if (larger != sizes_.end() &&
                            splitPenalty(larger->first, length) < penalty &&
                            scarcityAllowsExchange(candidate->first, larger->first, length)) {
                            candidate = larger;
                        }
                    }
                }
                at = candidate->second;
            }
        }
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
                at = gaps_.rbegin()->first;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_);
        }
        const Coordinate finish = gaps_.at(at);
        erase(at);
        add(at + length, finish);
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) { a = left->first; erase(a); }
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

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.97; max_solver_rss_mib: 5.62

Here is additional text feedback about the current program:

Fitness F/T=0.858347567674; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737103135
family=short_phase_churn mean_F/T=0.785915949
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.807979030
family=geometric_cohorts mean_F/T=0.811675991
family=drifting_sizes mean_F/T=0.812747558
family=short_heavy mean_F/T=0.813719605
family=additive_cohorts mean_F/T=0.823705648
family=distribution_switch mean_F/T=0.825147983
family=uniform_churn mean_F/T=0.830529159
family=tiny_churn mean_F/T=0.830637449
family=long_heavy mean_F/T=0.839706411
family=size_biased_deletion mean_F/T=0.842862995
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846914274
family=serial_churn mean_F/T=0.859962144
family=size_lifetimes mean_F/T=0.873630709
family=large_live_set mean_F/T=0.878783594
family=recent_window_growth mean_F/T=0.881199310
family=micro_gap_refill mean_F/T=0.881250000
family=bimodal mean_F/T=0.882743831
family=hotset_switching mean_F/T=0.883051847
family=section_boundaries mean_F/T=0.884754102
family=fifo mean_F/T=0.895019728
family=soft_recency_growth mean_F/T=0.896312745
family=burst_drain mean_F/T=0.899719553
family=serial_growth mean_F/T=0.915587982
family=long_prefill_recent mean_F/T=0.917704145
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920954915
family=drain_recovery mean_F/T=0.923335943
family=hotset_growth mean_F/T=0.950208451
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955014768
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001498 rss_mib=1.297
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001325 rss_mib=1.297
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001351 rss_mib=1.297
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001405 rss_mib=1.297
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001442 rss_mib=1.297
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001497 rss_mib=1.297
case=s31_118_partial_drain family=partial_drain F/T=0.611715308 F/B=0.646045362 B/T=0.946861233 overrun=0.056121 cpu_s=0.085211 rss_mib=2.000
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.613214286 F/B=0.675406191 B/T=0.907919255 overrun=0.101420 cpu_s=0.317991 rss_mib=3.109
case=s31_060_large_live_set family=large_live_set F/T=0.632532089 F/B=0.641932619 B/T=0.985355893 overrun=0.014862 cpu_s=0.414800 rss_mib=3.750
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001445 rss_mib=1.297
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.332530 rss_mib=2.922
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001363 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002948 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.017039 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012656 rss_mib=1.422
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.019611 rss_mib=1.422
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.758363903 F/B=0.950045956 B/T=0.798239178 overrun=0.252757 cpu_s=0.133648 rss_mib=2.062
case=s31_009_long_heavy family=long_heavy F/T=0.762500000 F/B=0.953125000 B/T=0.800000000 overrun=0.250000 cpu_s=0.374042 rss_mib=3.000
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002858 rss_mib=1.375
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.062912 rss_mib=1.516
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.766129032 F/B=0.950000000 B/T=0.806451613 overrun=0.240000 cpu_s=0.347167 rss_mib=2.953
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.332530 rss_mib=2.922
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.709344262 F/B=0.865400000 B/T=0.819672131 overrun=0.220000 cpu_s=0.077088 rss_mib=1.641
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001727 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002361 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.115798 rss_mib=1.844
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.031148 rss_mib=1.500
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.528910 rss_mib=3.297
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.645237 rss_mib=4.469
case=s31_102_serial_churn family=serial_churn F/T=0.820923913 F/B=0.950000000 B/T=0.864130435 overrun=0.157233 cpu_s=0.158330 rss_mib=1.891
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821110177 F/B=0.950170316 B/T=0.864171573 overrun=0.157178 cpu_s=0.125965 rss_mib=1.953
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.337235 rss_mib=2.969

PAIRED SEARCH EVIDENCE
Against parent gen11: delta mean F/T=+0.001594366; improved/regressed/tied=22/16/114.
family=size_lifetimes delta_F/T=+0.019195661
family=size_biased_deletion delta_F/T=+0.010998815
family=bimodal delta_F/T=-0.009574468
family=short_heavy delta_F/T=+0.008578530
family=uniform_churn delta_F/T=+0.006516678
family=fifo delta_F/T=+0.006264261
Regressions:
s31_015_bimodal: delta_F/T=-0.038297872, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.013606474, delta_T=+60
s31_040_distribution_switch: delta_F/T=-0.008969862, delta_T=+60
s31_086_tiny_churn: delta_F/T=-0.005884375, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.040963203, delta_T=-40
s31_006_short_heavy: delta_F/T=+0.030555556, delta_T=-40
s31_004_uniform_churn: delta_F/T=+0.027669271, delta_T=-200

Against leader gen3: delta mean F/T=+0.001015184; improved/regressed/tied=49/33/70.
family=drifting_sizes delta_F/T=+0.009439940
family=fifo delta_F/T=+0.008172368
family=tiny_churn delta_F/T=-0.007576686
family=long_heavy delta_F/T=+0.007566275
family=hotset_switching delta_F/T=+0.006962685
family=size_lifetimes delta_F/T=+0.006898578
Regressions:
s31_086_tiny_churn: delta_F/T=-0.030306745, delta_T=+100
s31_001_uniform_churn: delta_F/T=-0.019390244, delta_T=+20
s31_015_bimodal: delta_F/T=-0.018750000, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.017398050, delta_T=+20
Gains:
s31_014_bimodal: delta_F/T=+0.035470188, delta_T=-200
s31_009_long_heavy: delta_F/T=+0.024596774, delta_T=-40
s31_096_hotset_switching: delta_F/T=+0.022930166, delta_T=-260
s31_063_size_biased_deletion: delta_F/T=+0.020957918, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.858347568; mean positive loss on worst 16 cases=0.025654128; max case loss=0.061204395; regressed cases=39; worst family delta F/T=-0.020255386. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
