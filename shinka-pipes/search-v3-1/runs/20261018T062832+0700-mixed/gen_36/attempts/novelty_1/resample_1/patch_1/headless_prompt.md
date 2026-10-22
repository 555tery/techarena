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

**Учитывайте возраст соседей при выборе края.** Добавьте `birthClock` в `Pipe` и оценку интенсивности освобождения по размеру и трём возрастным категориям, например 0–63, 64–511 и ≥512 команд, корректно учитывая exposure при переходах между категориями. При недостатке наблюдений используйте исходную оценку по размеру; при достаточной статистике разрешите сравнение даже соседей одинаковой длины. Это проверит ограничение текущей модели, особенно заметное в регрессии `fifo`, сохраняя работающий механизм exposure-guided split.

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
appendable_wilderness: attempts=1; score_range=0.854861671..0.854861671
capacity_guarded_tail: attempts=1; score_range=0.857608299..0.857608299
causal_bellman_pair_pricing: attempts=1; score_range=0.857074884..0.857074884
causal_release_edge: attempts=1; score_range=0.857426348..0.857426348
gen2 First-Fit; correct=True; parent=0; delta_F/T=-0.007548957; claim=Pinned strong/simple seed
  improved/regressed/tied=19/76/57
  regression s31_057_large_live_set: delta_F/T=-0.075770120
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
gen24 exposure_guided_split; correct=True; parent=6; delta_F/T=+0.001161829; claim=Родитель gen6 сохраняется: размеры bins меньше 80, коэффициент regret 8, prior 1 на размер, обновление профиля каждые 64 вставки после первых 32, уменьшение наблюдений вдвое каждые 512 вставок.
Новый механизм выбирает ст
  improved/regressed/tied=39/37/76
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_009_long_heavy: delta_F/T=-0.038793103
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
gen30 causal_bellman_pair_pricing; correct=True; parent=22; delta_F/T=-0.000220957; claim=Предлагаю заменить оптимистичное совместное размещение будущей пары на causal Bellman pricing. Родитель допускает выбор размещения первой прогнозируемой трубы с учётом ещё неизвестной второй длины. Новый механизм выбирае
  improved/regressed/tied=10/13/129
  regression s31_122_short_rounding: delta_F/T=-0.042631579
  regression s31_033_burst_drain: delta_F/T=-0.022564103
gen29 interior_pair_growth_regret; correct=True; parent=12; delta_F/T=-0.000993729; claim=Механизм оценивает совместимость свободных интервалов с парой следующих вставок. Родитель gen12 сравнивает хвост и внутренний интервал по прогнозу одной вставки. Новый механизм сохраняет это решение, затем для неполного 

[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.055947609; maximum case loss=0.075770120. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.
You MUST respond using a short summary name, description and the full code:

<NAME>
A shortened name summarizing the code you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the code you are proposing.
</DESCRIPTION>

<CODE>
```{language}
# The new rewritten program here.
```
</CODE>

* Keep the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the code. Do not change the code outside of these markers.
* Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
* Make sure the file still runs after your changes.
* Use the <NAME>, <DESCRIPTION>, and <CODE> delimiters to structure your response. It will be parsed afterwards.

# Previous Messages

[]

# User Request


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
        if constexpr (true) {
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

Here are the performance metrics of the program:

Combined score to maximize: 0.85
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.85; worst_family_score: 0.53; mean_overrun: 0.06; mean_bound_to_trench: 0.94; max_solver_cpu_seconds: 2.14; max_solver_rss_mib: 5.95

Here is additional text feedback about the current program:

Fitness F/T=0.847432250997; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.736377659
family=short_phase_churn mean_F/T=0.751204939
family=drifting_sizes mean_F/T=0.785248125
family=uniform_churn mean_F/T=0.796746336
family=short_heavy mean_F/T=0.800076523
family=geometric_cohorts mean_F/T=0.801265596
family=micro_size_shift mean_F/T=0.802083333
family=long_heavy mean_F/T=0.803893194
family=distribution_switch mean_F/T=0.806621971
family=short_rounding mean_F/T=0.818394737
family=large_live_set mean_F/T=0.819717525
family=size_biased_deletion mean_F/T=0.822080518
family=additive_cohorts mean_F/T=0.825195096
family=long_prefill_random mean_F/T=0.827749018
family=size_lifetimes mean_F/T=0.829723294
family=tiny_churn mean_F/T=0.833601270
family=micro_tail_reuse mean_F/T=0.845833333
family=section_boundaries mean_F/T=0.851435359
family=bimodal mean_F/T=0.860032574
family=serial_churn mean_F/T=0.869400978
family=hotset_switching mean_F/T=0.878869531
family=fifo mean_F/T=0.878878168
family=recent_window_growth mean_F/T=0.880109897
family=micro_gap_refill mean_F/T=0.881250000
family=soft_recency_growth mean_F/T=0.885700632
family=burst_drain mean_F/T=0.894171240
family=serial_growth mean_F/T=0.909138493
family=drain_recovery mean_F/T=0.915626325
family=long_prefill_recent mean_F/T=0.916445644
family=isolated_recent_churn mean_F/T=0.917413989
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=hotset_growth mean_F/T=0.945617876
family=background_ephemeral mean_F/T=0.951133168
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960464194
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.002568 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001625 rss_mib=1.297
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001599 rss_mib=1.297
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001787 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001762 rss_mib=1.297
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001698 rss_mib=1.297
case=s31_060_large_live_set family=large_live_set F/T=0.583069807 F/B=0.641932619 B/T=0.908303754 overrun=0.100953 cpu_s=0.813443 rss_mib=3.953
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.609523075 F/B=0.675406191 B/T=0.902454082 overrun=0.108090 cpu_s=0.573265 rss_mib=3.172
case=s31_118_partial_drain family=partial_drain F/T=0.610622509 F/B=0.646045362 B/T=0.945169713 overrun=0.058011 cpu_s=0.153914 rss_mib=2.047
case=s31_040_distribution_switch family=distribution_switch F/T=0.631798246 F/B=0.692548077 B/T=0.912280702 overrun=0.096154 cpu_s=0.031076 rss_mib=1.422
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.002028 rss_mib=1.297
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.617833 rss_mib=2.609
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002080 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.005407 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.026565 rss_mib=1.438
case=s31_004_uniform_churn family=uniform_churn F/T=0.667624521 F/B=0.771017699 B/T=0.865900383 overrun=0.154867 cpu_s=0.589371 rss_mib=2.969
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.708955224 F/B=0.950000000 B/T=0.746268657 overrun=0.340000 cpu_s=0.708076 rss_mib=2.141
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.657367 rss_mib=2.984
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.675757576 F/B=0.857692308 B/T=0.787878788 overrun=0.269231 cpu_s=0.003688 rss_mib=1.359
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.004394 rss_mib=1.344
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.177505 rss_mib=1.641
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.617833 rss_mib=2.609
case=s31_017_section_boundaries family=section_boundaries F/T=0.785000000 F/B=0.957317073 B/T=0.820000000 overrun=0.219512 cpu_s=0.057033 rss_mib=1.500
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.061230 rss_mib=1.516
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.790252294 F/B=0.950045956 B/T=0.831804281 overrun=0.202206 cpu_s=0.260807 rss_mib=2.016
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.200308 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.002522 rss_mib=1.359
case=s31_128_short_phase_churn family=short_phase_churn F/T=0.774617737 F/B=0.917753623 B/T=0.844036697 overrun=0.184783 cpu_s=0.062220 rss_mib=1.500
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.832565489 F/B=0.982097589 B/T=0.847742117 overrun=0.179604 cpu_s=0.296043 rss_mib=2.672
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.065307 rss_mib=1.484
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.228217 rss_mib=1.828
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.814432990 F/B=0.954682779 B/T=0.853092784 overrun=0.172205 cpu_s=0.069787 rss_mib=1.484

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=-0.007548957; improved/regressed/tied=19/76/57.
family=large_live_set delta_F/T=-0.059277423
family=tiny_churn delta_F/T=+0.048597604
family=fifo delta_F/T=+0.047868787
family=section_boundaries delta_F/T=-0.042671847
family=long_heavy delta_F/T=-0.041563871
family=uniform_churn delta_F/T=-0.040028505
Regressions:
s31_057_large_live_set: delta_F/T=-0.075770120, delta_T=+57040
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_059_large_live_set: delta_F/T=-0.068622962, delta_T=+13420
s31_017_section_boundaries: delta_F/T=-0.068260870, delta_T=+80
Gains:
s31_024_fifo: delta_F/T=+0.120579436, delta_T=-280
s31_006_short_heavy: delta_F/T=+0.101521298, delta_T=-140
s31_086_tiny_churn: delta_F/T=+0.100272770, delta_T=-380
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.847432251; mean positive loss on worst 16 cases=0.055947609; max case loss=0.075770120; regressed cases=76; worst family delta F/T=-0.059277423. These are selection diagnostics; primary fitness remains mean F/T.


# Task

Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
