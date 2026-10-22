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
gen37 marginal_release_coalescence; correct=True; parent=20; delta_F/T=-0.000533929; claim=Предлагаю выбирать адрес и край размещения по ожидаемой полезности одного соседнего освобождения. Родительский выбор размера gap через splitPenalty и scarcityAllowsExchange сохраняется. Внутри выбранного точного размера 
  improved/regressed/tied=49/34/69
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_023_fifo: delta_F/T=-0.053425532
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
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
gen78 boundary_aligned_reclaimed_arena; correct=True; parent=0; delta_F/T=-0.000020470; claim=Предлагаю формировать двухстороннюю arena внутри уже существующей свободной дыры. При подтверждённом различии сроков жизни выбирается минимальная дыра размером хотя бы 2*length; предпочтение получает внутренняя дыра, хво
  improved/regressed/tied=9/13/130
  regression s31_063_size_biased_deletion: delta_F/T=-0.039121447
  regression s31_064_size_biased_deletion: delta_F/T=-0.005192965
gen77 scarcity_capacity_tail; correct=True; parent=20; delta_F/T=-0.002129679; claim=Crossover сохраняет сравнение двух ближайших размеров и scarcity guard родителя. Переносится один механизм: отдельное правило выбора свобо
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.024748306; maximum case loss=0.075378788. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
Design a completely different algorithm approach to solve the same problem.
Ignore the current implementation and think of alternative algorithmic strategies that could achieve better performance.
You MUST respond using a short summary name, description and the full code:

<NAME>
A shortened name summarizing the code you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
Explain the completely different algorithmic approach you are taking and why it should perform better than the current implementation.
</DESCRIPTION>

<CODE>
```{language}
# The completely new algorithm implementation here.
```
</CODE>

* Keep the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the code.
* Your algorithm should solve the same problem but use a fundamentally different approach.
* Ensure the same inputs and outputs are maintained.
* Think outside the box - consider different data structures, algorithms, or paradigms.
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
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
    std::map<Coordinate, std::size_t> live_;
    std::array<std::size_t, 41> population_{};
    std::array<double, 41> deaths_{}, exposure_{};
    std::array<std::uint64_t, 41> exposureAt_{};
    std::uint64_t commandTick_ = 0;
    double totalExposure_ = 0, totalDeaths_ = 0;
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
        const double pooledRate = totalDeaths_ / (totalExposure_ + 1.0);
        return (deaths_[length] + 8.0 * pooledRate) / (exposure + 8.0);
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
    double releaseGain(Coordinate a, Coordinate remainder, bool rightAligned,
                       const std::array<std::uint32_t, 41>& prefix) const {
        auto neighbor = live_.lower_bound(a);
        if (rightAligned) {
            if (neighbor == live_.begin()) return 0;
            --neighbor;
        } else if (neighbor == live_.end()) {
            return 0;
        }
        const Pipe& p = pipes_[neighbor->second];
        Coordinate releasedSpace = p.length;
        if (releasedSpace >= 40) return 0;
        if (rightAligned) {
            auto outside = gaps_.lower_bound(p.start);
            if (outside != gaps_.begin()) {
                --outside;
                if (outside->second == p.start)
                    releasedSpace += outside->second - outside->first;
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end())
                releasedSpace += outside->second - outside->first;
        }
        const int before = static_cast<int>(std::min<Coordinate>(
            40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(std::min<Coordinate>(
            40, remainder + releasedSpace));
        if (before == after) return 0;
        return releaseRate(p.length) *
               static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k)
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        const auto end = sizes_.upper_bound(
            {space, std::numeric_limits<Coordinate>::max()});
        const std::array<Coordinate, 2> candidates{
            at, std::prev(end)->second};
        double best = 0;
        for (std::size_t i = 0; i < candidates.size(); ++i) {
            if (i != 0 && candidates[i] == candidates[0]) continue;
            const Coordinate a = candidates[i];
            for (int side = 0; side < 2; ++side) {
                if (side != 0 && a + space == trench_) continue;
                const double score = releaseGain(a, remainder, side != 0, prefix);
                if (score > best) {
                    best = score;
                    at = a;
                    rightAligned = side != 0;
                }
            }
        }
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
        advanceReleaseClock();
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
        bool rightAligned = false;
        selectReleasePlacement(length, at, rightAligned);
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.03; max_solver_rss_mib: 10.05

Here is additional text feedback about the current program:

Fitness F/T=0.857813638749; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737397522
family=short_phase_churn mean_F/T=0.786603427
family=micro_size_shift mean_F/T=0.802083333
family=short_rounding mean_F/T=0.808221691
family=drifting_sizes mean_F/T=0.812150913
family=geometric_cohorts mean_F/T=0.815687648
family=additive_cohorts mean_F/T=0.819645721
family=short_heavy mean_F/T=0.822795898
family=tiny_churn mean_F/T=0.830637449
family=size_biased_deletion mean_F/T=0.831240501
family=distribution_switch mean_F/T=0.833561349
family=uniform_churn mean_F/T=0.841568315
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846800647
family=long_heavy mean_F/T=0.847835634
family=size_lifetimes mean_F/T=0.848077735
family=serial_churn mean_F/T=0.862217430
family=fifo mean_F/T=0.865384124
family=large_live_set mean_F/T=0.879856649
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881715390
family=hotset_switching mean_F/T=0.882357642
family=burst_drain mean_F/T=0.886335980
family=section_boundaries mean_F/T=0.889923288
family=bimodal mean_F/T=0.893499968
family=soft_recency_growth mean_F/T=0.896708649
family=serial_growth mean_F/T=0.916435871
family=long_prefill_recent mean_F/T=0.917831360
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921045109
family=drain_recovery mean_F/T=0.925492542
family=hotset_growth mean_F/T=0.949950758
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955360444
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001506 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001299 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001561 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001469 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001481 rss_mib=1.312
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001490 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.612136658 F/B=0.646045362 B/T=0.947513432 overrun=0.055394 cpu_s=0.088466 rss_mib=2.203
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.616757770 F/B=0.675406191 B/T=0.913165704 overrun=0.095091 cpu_s=0.330473 rss_mib=3.344
case=s31_060_large_live_set family=large_live_set F/T=0.632642820 F/B=0.641932619 B/T=0.985528389 overrun=0.014684 cpu_s=0.432633 rss_mib=4.578
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.312
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.338901 rss_mib=2.922
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001395 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002948 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.654772727 F/B=0.692548077 B/T=0.945454545 overrun=0.057692 cpu_s=0.017733 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012929 rss_mib=1.484
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002923 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002923 rss_mib=1.391
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.760316293 F/B=0.950045956 B/T=0.800294226 overrun=0.249540 cpu_s=0.138895 rss_mib=2.172
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.634433962 F/B=0.781976744 B/T=0.811320755 overrun=0.232558 cpu_s=0.338901 rss_mib=2.922
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.704723127 F/B=0.865400000 B/T=0.814332248 overrun=0.228000 cpu_s=0.077765 rss_mib=1.641
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.778688525 F/B=0.950000000 B/T=0.819672131 overrun=0.220000 cpu_s=0.353149 rss_mib=2.953
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.378123 rss_mib=3.000
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.117747 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001794 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002471 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.116363 rss_mib=1.875
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.050625 rss_mib=1.516
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.036157 rss_mib=1.500
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.031618 rss_mib=1.500
case=s31_033_burst_drain family=burst_drain F/T=0.818604651 F/B=0.951351351 B/T=0.860465116 overrun=0.162162 cpu_s=0.040026 rss_mib=1.500
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.818014244 F/B=0.950170316 B/T=0.860913280 overrun=0.161557 cpu_s=0.135693 rss_mib=2.047
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.364595 rss_mib=2.969

PAIRED SEARCH EVIDENCE
Against parent gen20: delta mean F/T=-0.000533929; improved/regressed/tied=49/34/69.
family=fifo delta_F/T=-0.029635603
family=size_lifetimes delta_F/T=-0.025552975
family=burst_drain delta_F/T=-0.013383574
family=size_biased_deletion delta_F/T=-0.011622494
family=uniform_churn delta_F/T=+0.011039156
family=bimodal delta_F/T=+0.010756137
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_023_fifo: delta_F/T=-0.053425532, delta_T=+60
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
s31_033_burst_drain: delta_F/T=-0.039931934, delta_T=+40
Gains:
s31_039_distribution_switch: delta_F/T=+0.048243464, delta_T=-80
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_001_uniform_churn: delta_F/T=+0.039774859, delta_T=-40
s31_015_bimodal: delta_F/T=+0.038297872, delta_T=-40

Against leader gen24: delta mean F/T=-0.000912243; improved/regressed/tied=44/42/66.
family=size_lifetimes delta_F/T=-0.029919598
family=burst_drain delta_F/T=-0.024998201
family=long_heavy delta_F/T=+0.011336716
family=geometric_cohorts delta_F/T=+0.011028837
family=short_rounding delta_F/T=-0.010657895
family=bimodal delta_F/T=+0.007850151
Regressions:
s31_033_burst_drain: delta_F/T=-0.083959451, delta_T=+80
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.040963203, delta_T=+40
Gains:
s31_049_geometric_cohorts: delta_F/T=+0.041558442, delta_T=-40
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_062_size_biased_deletion: delta_F/T=+0.025722426, delta_T=-240

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857813639; mean positive loss on worst 16 cases=0.024748306; max case loss=0.075378788; regressed cases=37; worst family delta F/T=-0.015573911. These are selection diagnostics; primary fitness remains mean F/T.


# Task

Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
