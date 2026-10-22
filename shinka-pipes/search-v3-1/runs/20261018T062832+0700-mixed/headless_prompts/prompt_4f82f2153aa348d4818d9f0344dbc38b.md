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

You are given multiple code scripts implementing the same algorithm.
You are tasked with generating a new code snippet that combines these code scripts in a way that is more efficient. 
I.e. perform crossover between the code scripts.
Provide the complete new program code.
You MUST respond using a short summary name, description, and the full code:

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

# Research evidence and potential recommendations
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
gen20 scarcity_fit_guard; correct=True; parent=11; delta_F/T=+0.001594366; claim=Предлагаю учитывать дефицит подходящих gaps при разрешении обмена. Родитель по-прежнему сравнивает Best-Fit со следующим строго большим gap через splitPenalty. Новый guard разрешает предложенный обмен, только если он не 
  improved/regressed/tied=22/16/114
  regression s31_015_bimodal: delta_F/T=-0.038297872
  regression s31_102_serial_churn: delta_F/T=-0.013606474
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen85 dual_pattern_fit; correct=True; parent=62; delta_F/T=-0.000333892; claim=Механизм — deterministic packing dual prices. Вместо rollout с искусственным порядком вставок алгоритм оценивает смешанные упаковки в существующих gap через unbounded knapsack. Цены длин корректируются projected subgradi
  improved/regressed/tied=43/41/68
  regression s31_015_bimodal: delta_F/T=-0.036750000
  regression s31_102_serial_churn: delta_F/T=-0.031412656
gen84 horizon_confirmed_scarcity; correct=True; parent=69; delta_F/T=+0.000952391; claim=Добавляю один механизм: подтверждение scarcity exchange через совместную упаковку трёх синтетических запросов. Исходный residual-fit сравнивается с предложенным exchange; exchange принимается только при строго меньшей су
  improved/regressed/tied=30/19/103
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_055_additive_cohorts: delta_F/T=-0.015673401
gen83 oriented_tail_release_guard; correct=True; parent=0; delta_F/T=+0.000558640; claim=Один механизм crossover: использование свободного хвоста с проверкой последствий удаления соседей. Сохраняются модель времени жизни, выбор кандидатов, ориентация размещения и возрастные tie-break родителя.
Хвост заменяет
  improved/regressed/tied=27/27/98
  regression s31_017_section_boundaries: delta_F/T=-0.035552536
  regression s31_001_uniform_churn: delta_F/T=-0.019390244
gen82 repeat_coupled_horizon; correct=True; parent=37; delta_F/T=+0.000059972; claim=Механизм — точный короткий прогноз совместной упаковки. Для каждого рассматриваемого gap оценивается минимальное расширение при трёх синтетических вставках. Восемь сценариев строятся исключительно по наблюдённым длинам: 
  improved/regressed/tied=31/28/93
  regression s31_041_drifting_sizes: delta_F/T=-0.047919294
  regression s31_126_short_phase_churn: delta_F/T=-0.043597263
gen81 exposure_normalized_release_veto; correct=True; parent=13; delta_F/T=+0.000017098; claim=Предлагаю один механизм: veto выбора правого края, если накопленные удаления показывают, что размер правого соседа освобождается заметно чаще размера левого. Родительский выбор отверст
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.025654128; maximum case loss=0.061204395. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.

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
    // false: same-parent ablation, reproducing the supplied policy.
    static constexpr bool kShadowDuel = true;
    struct DemandProfile {
        std::array<std::uint32_t, 41> demand{};
        std::uint32_t mass = 0;
        void observeLength(int length) {
            if (mass >= 128) {
                mass = 0;
                for (int k = 1; k <= 40; ++k) {
                    demand[k] /= 2;
                    mass += demand[k];
                }
            }
            ++demand[length];
            ++mass;
        }
        std::uint64_t splitPenalty(
            Coordinate space, int length
        ) const {
            std::uint64_t result = 0;
            for (int k = 1; k <= 40; ++k) {
                if (demand[k] != 0 &&
                    space % k < length % k) {
                    result +=
                        static_cast<std::uint64_t>(demand[k]) * k;
                }
            }
            return result;
        }
    };
    struct Placement {
        Coordinate sections;
        Coordinate start;
    };
    class Layout {
        struct Pipe {
            Coordinate start;
            int length;
        };
        std::vector<Pipe> pipes_{{0, 0}};
        std::map<Coordinate, Coordinate> gaps_;
        std::set<std::pair<Coordinate, Coordinate>> sizes_;
        std::array<std::set<Coordinate>, 41> starts_;
        Coordinate trench_ = 0;
        static int bucket(Coordinate length) {
            return static_cast<int>(
                std::min<Coordinate>(40, length)
            );
        }
        void add(Coordinate a, Coordinate b) {
            if (a >= b) {
                return;
            }
            gaps_[a] = b;
            sizes_.insert({b - a, a});
            starts_[bucket(b - a)].insert(a);
        }
        void erase(Coordinate a) {
            const auto it = gaps_.find(a);
            const Coordinate b = it->second;
            sizes_.erase({b - a, a});
            starts_[bucket(b - a)].erase(a);
            gaps_.erase(it);
        }
        bool scarcityAllowsExchange(
            Coordinate smaller,
            Coordinate larger,
            int length,
            const DemandProfile& profile
        ) const {
            std::size_t fittingGaps = 0;
            long double extraLoss = 0;
            for (int k = 40; k >= 1; --k) {
                fittingGaps += starts_[k].size();
                if (profile.demand[k] == 0 ||
                    fittingGaps == 0) {
                    continue;
                }
                const int smallerLoses =
                    smaller >= k && smaller - length < k;
                const int largerLoses =
                    larger >= k && larger - length < k;
                if (smallerLoses != largerLoses) {
                    extraLoss +=
                        static_cast<long double>(
                            profile.demand[k]
                        ) /
                        static_cast<long double>(fittingGaps) *
                        (largerLoses - smallerLoses);
                }
            }
            return extraLoss <= 0;
        }
    public:
        Coordinate trenchLength() const {
            return trench_;
        }
        Placement place(
            int length,
            bool useParentPolicy,
            const DemandProfile& profile
        ) {
            Coordinate at = -1;
            Coordinate digs = 0;
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) {
                if (useParentPolicy &&
                    candidate->first > length) {
                    const auto penalty =
                        profile.splitPenalty(
                            candidate->first, length
                        );
                    if (penalty != 0) {
                        const auto larger = sizes_.upper_bound({
                            candidate->first,
                            std::numeric_limits<Coordinate>::max()
                        });
                        if (larger != sizes_.end() &&
                            profile.splitPenalty(
                                larger->first, length
                            ) < penalty &&
                            scarcityAllowsExchange(
                                candidate->first,
                                larger->first,
                                length,
                                profile
                            )) {
                            candidate = larger;
                        }
                    }
                }
                at = candidate->second;
            }
            // Growth is possible only after the global fitting-gap
            // search has failed.
            if (at < 0) {
                at = trench_;
                if (!gaps_.empty() &&
                    gaps_.rbegin()->second == trench_) {
                    at = gaps_.rbegin()->first;
                    erase(at);
                }
                digs =
                    (length - (trench_ - at) + 19) / 20;
                trench_ += digs * 20;
                add(at, trench_);
            }
            const Coordinate finish = gaps_.at(at);
            erase(at);
            add(at + length, finish);
            pipes_.push_back({at, length});
            return {digs, at};
        }
        Coordinate remove(Coordinate pid) {
            const Pipe p = pipes_.at(
                static_cast<std::size_t>(pid)
            );
            Coordinate a = p.start;
            Coordinate b = a + p.length;
            auto right = gaps_.lower_bound(a);
            if (right != gaps_.end() &&
                right->first == b) {
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
            return p.start;
        }
    };
    DemandProfile profile_;
    Layout actual_;
    Layout parentShadow_;
    Layout bestFitShadow_;
    bool parentSelected_ = true;
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        profile_.observeLength(length);
        bool useParentPolicy = true;
        if constexpr (kShadowDuel) {
            // Both shadows process only the command already received.
            // They never emit coordinates or reserve actual trench.
            parentShadow_.place(length, true, profile_);
            bestFitShadow_.place(length, false, profile_);
            const Coordinate parentTrench =
                parentShadow_.trenchLength();
            const Coordinate bestFitTrench =
                bestFitShadow_.trenchLength();
            if (parentTrench < bestFitTrench) {
                parentSelected_ = true;
            } else if (bestFitTrench < parentTrench) {
                parentSelected_ = false;
            }
            // A tie retains the previously selected policy.
            useParentPolicy = parentSelected_;
        }
        const Placement result = actual_.place(
            length, useParentPolicy, profile_
        );
        std::cout << result.sections << ' '
                  << result.start << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Coordinate start = actual_.remove(pid);
        if constexpr (kShadowDuel) {
            parentShadow_.remove(pid);
            bestFitShadow_.remove(pid);
        }
        std::cout << start << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.16; max_solver_rss_mib: 10.89

Text feedback:
Fitness F/T=0.857907798624; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737595404
family=short_phase_churn mean_F/T=0.785232978
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.802746215
family=geometric_cohorts mean_F/T=0.806413892
family=short_rounding mean_F/T=0.807979030
family=short_heavy mean_F/T=0.820610336
family=distribution_switch mean_F/T=0.823101883
family=additive_cohorts mean_F/T=0.823705648
family=uniform_churn mean_F/T=0.828803194
family=tiny_churn mean_F/T=0.835116112
family=size_biased_deletion mean_F/T=0.838729315
family=long_heavy mean_F/T=0.845571709
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846914274
family=serial_churn mean_F/T=0.855306383
family=size_lifetimes mean_F/T=0.871796558
family=hotset_switching mean_F/T=0.879919011
family=large_live_set mean_F/T=0.880097769
family=bimodal mean_F/T=0.880899975
family=micro_gap_refill mean_F/T=0.881250000
family=section_boundaries mean_F/T=0.882218059
family=recent_window_growth mean_F/T=0.882374693
family=fifo mean_F/T=0.893393100
family=soft_recency_growth mean_F/T=0.896478256
family=burst_drain mean_F/T=0.903369982
family=serial_growth mean_F/T=0.915418454
family=long_prefill_recent mean_F/T=0.917722342
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921431107
family=drain_recovery mean_F/T=0.921892265
family=hotset_growth mean_F/T=0.949765360
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955314425
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001495 rss_mib=1.359
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001402 rss_mib=1.359
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001456 rss_mib=1.359
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001394 rss_mib=1.359
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001474 rss_mib=1.359
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001425 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611715308 F/B=0.646045362 B/T=0.946861233 overrun=0.056121 cpu_s=0.097157 rss_mib=2.906
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617915819 F/B=0.675406191 B/T=0.914880300 overrun=0.093039 cpu_s=0.382245 rss_mib=5.141
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.382643 rss_mib=4.578
case=s31_060_large_live_set family=large_live_set F/T=0.632495187 F/B=0.641932619 B/T=0.985298407 overrun=0.014921 cpu_s=0.481334 rss_mib=6.844
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001465 rss_mib=1.359
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001418 rss_mib=1.297
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003244 rss_mib=1.406
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.020277 rss_mib=1.547
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013633 rss_mib=1.641
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.022353 rss_mib=1.641
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.719696970 F/B=0.950000000 B/T=0.757575758 overrun=0.320000 cpu_s=0.390091 rss_mib=4.641
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.756698389 F/B=0.950045956 B/T=0.796486091 overrun=0.255515 cpu_s=0.159935 rss_mib=2.906
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.382643 rss_mib=4.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002826 rss_mib=1.391
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.059117 rss_mib=1.797
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.714026403 F/B=0.865400000 B/T=0.825082508 overrun=0.212000 cpu_s=0.086205 rss_mib=2.016
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.430590 rss_mib=4.734
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001720 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002502 rss_mib=1.375
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.037490 rss_mib=1.766
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.125860 rss_mib=2.422
case=s31_102_serial_churn family=serial_churn F/T=0.816486486 F/B=0.950000000 B/T=0.859459459 overrun=0.163522 cpu_s=0.183877 rss_mib=2.516
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.718996 rss_mib=7.688
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821110177 F/B=0.950170316 B/T=0.864171573 overrun=0.157178 cpu_s=0.154072 rss_mib=2.781
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852012362 F/B=0.982097589 B/T=0.867543481 overrun=0.152680 cpu_s=0.190900 rss_mib=4.938
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.669902913 F/B=0.768089054 B/T=0.872168285 overrun=0.146568 cpu_s=0.022353 rss_mib=1.641

PAIRED SEARCH EVIDENCE
Against parent gen20: delta mean F/T=-0.000439769; improved/regressed/tied=23/35/94.
family=drifting_sizes delta_F/T=-0.010001342
family=short_heavy delta_F/T=+0.006890731
family=long_heavy delta_F/T=+0.005865297
family=geometric_cohorts delta_F/T=-0.005262099
family=serial_churn delta_F/T=-0.004655761
family=tiny_churn delta_F/T=+0.004478663
Regressions:
s31_041_drifting_sizes: delta_F/T=-0.046432063, delta_T=+80
s31_008_short_heavy: delta_F/T=-0.028666667, delta_T=+60
s31_063_size_biased_deletion: delta_F/T=-0.020957918, delta_T=+20
s31_052_geometric_cohorts: delta_F/T=-0.014894795, delta_T=+100
Gains:
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.026293103, delta_T=-40
s31_033_burst_drain: delta_F/T=+0.021463415, delta_T=-20
s31_086_tiny_churn: delta_F/T=+0.017914654, delta_T=-60

Against leader gen52: delta mean F/T=-0.000953655; improved/regressed/tied=33/47/72.
family=fifo delta_F/T=+0.020992382
family=size_lifetimes delta_F/T=-0.020144011
family=serial_churn delta_F/T=-0.013506804
family=long_heavy delta_F/T=+0.012613134
family=size_biased_deletion delta_F/T=-0.009152036
family=hotset_switching delta_F/T=-0.007356997
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.090454545, delta_T=+20
s31_103_serial_churn: delta_F/T=-0.043999453, delta_T=+60
s31_063_size_biased_deletion: delta_F/T=-0.042938174, delta_T=+40
s31_008_short_heavy: delta_F/T=-0.038760563, delta_T=+80
Gains:
s31_022_fifo: delta_F/T=+0.054718684, delta_T=-360
s31_009_long_heavy: delta_F/T=+0.050889878, delta_T=-80
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.019130435, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857907799; mean positive loss on worst 16 cases=0.025103695; max case loss=0.061204395; regressed cases=37; worst family delta F/T=-0.022301487. These are selection diagnostics; primary fitness remains mean F/T.


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


# Task

Perform a cross-over between the code script above and the one below. Aim to combine the best parts of both code implementations that improves the score.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.

# Crossover Inspiration Programs
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
    // false: same-parent ablation, reproducing the supplied policy.
    static constexpr bool kShadowDuel = true;
    struct DemandProfile {
        std::array<std::uint32_t, 41> demand{};
        std::uint32_t mass = 0;
        void observeLength(int length) {
            if (mass >= 128) {
                mass = 0;
                for (int k = 1; k <= 40; ++k) {
                    demand[k] /= 2;
                    mass += demand[k];
                }
            }
            ++demand[length];
            ++mass;
        }
        std::uint64_t splitPenalty(
            Coordinate space, int length
        ) const {
            std::uint64_t result = 0;
            for (int k = 1; k <= 40; ++k) {
                if (demand[k] != 0 &&
                    space % k < length % k) {
                    result +=
                        static_cast<std::uint64_t>(demand[k]) * k;
                }
            }
            return result;
        }
    };
    struct Placement {
        Coordinate sections;
        Coordinate start;
    };
    class Layout {
        struct Pipe {
            Coordinate start;
            int length;
        };
        std::vector<Pipe> pipes_{{0, 0}};
        std::map<Coordinate, Coordinate> gaps_;
        std::set<std::pair<Coordinate, Coordinate>> sizes_;
        std::array<std::set<Coordinate>, 41> starts_;
        Coordinate trench_ = 0;
        static int bucket(Coordinate length) {
            return static_cast<int>(
                std::min<Coordinate>(40, length)
            );
        }
        void add(Coordinate a, Coordinate b) {
            if (a >= b) {
                return;
            }
            gaps_[a] = b;
            sizes_.insert({b - a, a});
            starts_[bucket(b - a)].insert(a);
        }
        void erase(Coordinate a) {
            const auto it = gaps_.find(a);
            const Coordinate b = it->second;
            sizes_.erase({b - a, a});
            starts_[bucket(b - a)].erase(a);
            gaps_.erase(it);
        }
        bool scarcityAllowsExchange(
            Coordinate smaller,
            Coordinate larger,
            int length,
            const DemandProfile& profile
        ) const {
            std::size_t fittingGaps = 0;
            long double extraLoss = 0;
            for (int k = 40; k >= 1; --k) {
                fittingGaps += starts_[k].size();
                if (profile.demand[k] == 0 ||
                    fittingGaps == 0) {
                    continue;
                }
                const int smallerLoses =
                    smaller >= k && smaller - length < k;
                const int largerLoses =
                    larger >= k && larger - length < k;
                if (smallerLoses != largerLoses) {
                    extraLoss +=
                        static_cast<long double>(
                            profile.demand[k]
                        ) /
                        static_cast<long double>(fittingGaps) *
                        (largerLoses - smallerLoses);
                }
            }
            return extraLoss <= 0;
        }
    public:
        Coordinate trenchLength() const {
            return trench_;
        }
        Placement place(
            int length,
            bool useParentPolicy,
            const DemandProfile& profile
        ) {
            Coordinate at = -1;
            Coordinate digs = 0;
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) {
                if (useParentPolicy &&
                    candidate->first > length) {
                    const auto penalty =
                        profile.splitPenalty(
                            candidate->first, length
                        );
                    if (penalty != 0) {
                        const auto larger = sizes_.upper_bound({
                            candidate->first,
                            std::numeric_limits<Coordinate>::max()
                        });
                        if (larger != sizes_.end() &&
                            profile.splitPenalty(
                                larger->first, length
                            ) < penalty &&
                            scarcityAllowsExchange(
                                candidate->first,
                                larger->first,
                                length,
                                profile
                            )) {
                            candidate = larger;
                        }
                    }
                }
                at = candidate->second;
            }
            // Growth is possible only after the global fitting-gap
            // search has failed.
            if (at < 0) {
                at = trench_;
                if (!gaps_.empty() &&
                    gaps_.rbegin()->second == trench_) {
                    at = gaps_.rbegin()->first;
                    erase(at);
                }
                digs =
                    (length - (trench_ - at) + 19) / 20;
                trench_ += digs * 20;
                add(at, trench_);
            }
            const Coordinate finish = gaps_.at(at);
            erase(at);
            add(at + length, finish);
            pipes_.push_back({at, length});
            return {digs, at};
        }
        Coordinate remove(Coordinate pid) {
            const Pipe p = pipes_.at(
                static_cast<std::size_t>(pid)
            );
            Coordinate a = p.start;
            Coordinate b = a + p.length;
            auto right = gaps_.lower_bound(a);
            if (right != gaps_.end() &&
                right->first == b) {
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
            return p.start;
        }
    };
    DemandProfile profile_;
    Layout actual_;
    Layout parentShadow_;
    Layout bestFitShadow_;
    bool parentSelected_ = true;
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        profile_.observeLength(length);
        bool useParentPolicy = true;
        if constexpr (kShadowDuel) {
            // Both shadows process only the command already received.
            // They never emit coordinates or reserve actual trench.
            parentShadow_.place(length, true, profile_);
            bestFitShadow_.place(length, false, profile_);
            const Coordinate parentTrench =
                parentShadow_.trenchLength();
            const Coordinate bestFitTrench =
                bestFitShadow_.trenchLength();
            if (parentTrench < bestFitTrench) {
                parentSelected_ = true;
            } else if (bestFitTrench < parentTrench) {
                parentSelected_ = false;
            }
            // A tie retains the previously selected policy.
            useParentPolicy = parentSelected_;
        }
        const Placement result = actual_.place(
            length, useParentPolicy, profile_
        );
        std::cout << result.sections << ' '
                  << result.start << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Coordinate start = actual_.remove(pid);
        if constexpr (kShadowDuel) {
            parentShadow_.remove(pid);
            bestFitShadow_.remove(pid);
        }
        std::cout << start << '\n' << std::flush;
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

Performance metrics: Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.16; max_solver_rss_mib: 10.89


