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
**Подтверждайте небольшие преимущества rollout обратным порядком запросов.** Если итоговый победитель превосходит fallback ровно на одну суммарную секцию по восьми сценариям, повторно оцените оба размещения с перевёрнутыми тройками запросов и разрешайте замену только при строгом выигрыше также во второй оценке. Такой узкий фильтр развивает консервативное правило gen61 и проверяет, возникают ли отдельные регрессии из-за чувствительности к искусственно выбранному порядку вставок.

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
gen0 initial_program; correct=True; parent=None; delta_F/T=n/a; claim=Initial program setup
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
gen77 scarcity_capacity_tail; correct=True; parent=20; delta_F/T=-0.002129679; claim=Crossover сохраняет сравнение двух ближайших размеров и scarcity guard родителя. Переносится один механизм: отдельное правило выбора свободного хвоста. Точное попадание сохраняет приоритет; при остальных запросах родител
  improved/regressed/tied=28/53/71
  regression s31_031_size_lifetimes: delta_F/T=-0.075378788
  regression s31_087_tiny_churn: delta_F/T=-0.049673203
gen76 oldest_release_run_veto; correct=True; parent=52; delta_F/T=-0.000093882; claim=Предлагаю условно запрещать merge utility пер
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=robust; specialist families=[]; fixed-baseline tail loss=0.000000000; maximum case loss=0.000000000. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.

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
// NAME: tail_coalescence_guard
// DESCRIPTION: Родительский marginal_tail_growth с ограничением,
// сохраняющим полезность слияния остатка с правым соседом.
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
// Хвост выбирается только при строгом уменьшении этой стоимости
// и не меньшей полезности слияния при удалении правого соседа.
// Полезность — снижение прогнозируемого роста от объединения интервалов.
// Перед любым расширением сохраняется глобальный поиск подходящей дыры.
//
// Вставка: амортизированно O(log(H+V) + 80 + 40),
// удаление: O(log(H+V)); V — число живых труб.
// Память: O(P + H + V).
// Недостаток: время удаления соседа неизвестно; ограничение может
// отклонять полезное использование хвоста ради далёкого слияния.
// Ablation: kTailMergeGuard = false восстанавливает решения родителя.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kTailMergeGuard = true;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    HoleMap liveByAddress_;
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
    std::int64_t projectedGrowth(int largestHole, int tail) const {
        const int threshold = std::max(largestHole, tail);
        std::int64_t cost = 0;
        for (int k = threshold + 1; k <= kMaxLength; ++k) {
            cost += static_cast<std::int64_t>(weights_[k])
                  * ((k - tail + 19) / 20);
        }
        return cost;
    }
    bool tailPreservesMerge(int length, int holeStart, int holeSize,
                            int largestOther) const {
        if constexpr (!kTailMergeGuard) {
            return true;
        }
        const int remainder = holeSize - length;
        if (remainder == 0) {
            return true;
        }
        const auto neighbor = liveByAddress_.find(holeStart + holeSize);
        if (neighbor == liveByAddress_.end()) {
            return true;
        }
        const int tail = trench_ - frontier_;
        const int neighborEnd = neighbor->first + neighbor->second;
        int releasedLength = neighbor->second;
        if (neighborEnd != frontier_) {
            const auto outer = holes_.find(neighborEnd);
            if (outer != holes_.end()) {
                releasedLength += outer->second;
            }
        }
        // largestOther may include the outer hole: releasedLength
        // already dominates its length in both comparisons.
        const auto internalMergeGain = [&](int residual, int suffix) {
            const int separateLargest =
                std::max({largestOther, residual, releasedLength});
            const int joinedLargest =
                std::max(largestOther, residual + releasedLength);
            return projectedGrowth(separateLargest, suffix)
                 - projectedGrowth(joinedLargest, suffix);
        };
        std::int64_t holeGain;
        if (neighborEnd == frontier_) {
            // With the hole placement, deletion returns this neighbor
            // and the adjacent remainder to the free suffix.
            const int releasedTail = tail + neighbor->second;
            holeGain = projectedGrowth(
                           std::max(largestOther, remainder),
                           releasedTail)
                     - projectedGrowth(
                           largestOther, releasedTail + remainder);
        } else {
            holeGain = internalMergeGain(remainder, tail);
        }
        // A tail placement leaves the whole hole available.
        // It also makes the old final neighbor internal.
        const std::int64_t tailGain =
            internalMergeGain(holeSize, tail - length);
        return tailGain >= holeGain;
    }
    bool preferFreeTail(int length, int holeStart, int holeSize) const {
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
        return tailCost < holeCost &&
               tailPreservesMerge(length, holeStart, holeSize,
                                  largestOther);
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
            !preferFreeTail(length, chosen.first, chosen.second)) {
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
        liveByAddress_.emplace(start, length);
        pipes_.push_back({start, length});
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        liveByAddress_.erase(originalStart);
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 6.98

Text feedback:
Fitness F/T=0.857876995742; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737684223
family=short_phase_churn mean_F/T=0.782545303
family=geometric_cohorts mean_F/T=0.800687855
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.807955077
family=additive_cohorts mean_F/T=0.815459768
family=short_heavy mean_F/T=0.815866044
family=short_rounding mean_F/T=0.819122721
family=distribution_switch mean_F/T=0.823387780
family=uniform_churn mean_F/T=0.833157585
family=tiny_churn mean_F/T=0.838214135
family=size_biased_deletion mean_F/T=0.841058387
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847436039
family=long_heavy mean_F/T=0.849044027
family=size_lifetimes mean_F/T=0.852916835
family=serial_churn mean_F/T=0.863333638
family=hotset_switching mean_F/T=0.878669189
family=large_live_set mean_F/T=0.879520330
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881496075
family=fifo mean_F/T=0.882369765
family=bimodal mean_F/T=0.882532473
family=section_boundaries mean_F/T=0.893988670
family=soft_recency_growth mean_F/T=0.896777538
family=burst_drain mean_F/T=0.900233006
family=serial_growth mean_F/T=0.915761319
family=long_prefill_recent mean_F/T=0.917728817
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920742241
family=drain_recovery mean_F/T=0.925397933
family=hotset_growth mean_F/T=0.950014152
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955646292
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001699 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001412 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001370 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001465 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001821 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001620 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611462777 F/B=0.646045362 B/T=0.946470345 overrun=0.056557 cpu_s=0.090503 rss_mib=1.781
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615700031 F/B=0.675406191 B/T=0.911599626 overrun=0.096973 cpu_s=0.300375 rss_mib=1.984
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.309798 rss_mib=1.625
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.397741 rss_mib=2.875
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001381 rss_mib=1.344
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.016937 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001354 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003379 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012316 rss_mib=1.453
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.334164 rss_mib=1.656
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.131112 rss_mib=1.734
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.309798 rss_mib=1.625
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002901 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.072530 rss_mib=1.422
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.058275 rss_mib=1.406
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.353071 rss_mib=1.688
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.115891 rss_mib=1.469
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001788 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002384 rss_mib=1.391
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.626020 rss_mib=1.922
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.827225131 F/B=0.954682779 B/T=0.866492147 overrun=0.154079 cpu_s=0.035098 rss_mib=1.406
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.825972927 F/B=0.950170316 B/T=0.869289340 overrun=0.150365 cpu_s=0.118871 rss_mib=1.625
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854099424 F/B=0.982097589 B/T=0.869668588 overrun=0.149863 cpu_s=0.154159 rss_mib=2.391
case=s31_086_tiny_churn family=tiny_churn F/T=0.836466165 F/B=0.959051724 B/T=0.872180451 overrun=0.146552 cpu_s=0.113236 rss_mib=1.500
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030665 rss_mib=1.406

PAIRED SEARCH EVIDENCE
Against parent gen14: delta mean F/T=+0.000631444; improved/regressed/tied=23/16/113.
family=long_heavy delta_F/T=+0.009698276
family=section_boundaries delta_F/T=+0.009131027
family=tiny_churn delta_F/T=+0.007576686
family=size_biased_deletion delta_F/T=+0.007498012
family=additive_cohorts delta_F/T=-0.006064124
family=hotset_switching delta_F/T=-0.005630237
Regressions:
s31_052_geometric_cohorts: delta_F/T=-0.027073269, delta_T=+180
s31_096_hotset_switching: delta_F/T=-0.024214955, delta_T=+280
s31_055_additive_cohorts: delta_F/T=-0.015673401, delta_T=+20
s31_040_distribution_switch: delta_F/T=-0.011905943, delta_T=+80
Gains:
s31_063_size_biased_deletion: delta_F/T=+0.040963203, delta_T=-40
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_017_section_boundaries: delta_F/T=+0.034085975, delta_T=-40
s31_086_tiny_churn: delta_F/T=+0.030306745, delta_T=-100

Against leader gen61: delta mean F/T=-0.001684471; improved/regressed/tied=32/52/68.
family=size_lifetimes delta_F/T=-0.023844697
family=fifo delta_F/T=+0.017857098
family=bimodal delta_F/T=-0.014102474
family=hotset_switching delta_F/T=-0.013378124
family=additive_cohorts delta_F/T=-0.011431441
family=distribution_switch delta_F/T=-0.011096293
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_033_burst_drain: delta_F/T=-0.044027517, delta_T=+40
s31_055_additive_cohorts: delta_F/T=-0.031938250, delta_T=+40
s31_014_bimodal: delta_F/T=-0.029065630, delta_T=+160
Gains:
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.040963203, delta_T=-40
s31_024_fifo: delta_F/T=+0.019981735, delta_T=-40
s31_127_short_phase_churn: delta_F/T=+0.018736786, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857876996; mean positive loss on worst 16 cases=0.023067076; max case loss=0.075378788; regressed cases=39; worst family delta F/T=-0.022015589. These are selection diagnostics; primary fitness remains mean F/T.


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
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes still-live pipes, so long-lived survivors contribute
// evidence without requiring their eventual deletion.
struct Rate {
    int live = 0;
    double exposure = 0.0;
    double deaths = 0.0;
    std::uint64_t stamp = 0;
    double exposureAt(std::uint64_t now) const {
        return exposure +
            static_cast<double>(now - stamp) * static_cast<double>(live);
    }
    void touch(std::uint64_t now) {
        exposure = exposureAt(now);
        stamp = now;
    }
    void change(std::uint64_t now, int delta, bool removed) {
        touch(now);
        live += delta;
        if (removed) deaths += 1.0;
    }
    void forget(std::uint64_t now) {
        touch(now);
        exposure *= 0.5;
        deaths *= 0.5;
    }
};
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
    std::uint64_t freeSince = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    double score = std::numeric_limits<double>::infinity();
};
class Allocator {
public:
    // Preserve the optional diagnostics interface used outside the block.
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        beginCommand();
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        if (lastPlacementLength_ != length) {
            lastPlacementLength_ = length;
            runOrdinal_ = 0;
        }
        const int runPhase = static_cast<int>(runOrdinal_ & 7U);
        ++runOrdinal_;
        observeLength(length);
        refreshModel(newlyObservedLength);
        const int pid = static_cast<int>(pipes_.size());
        const int globalPhase = pid & 7;
        const double deletionProbability =
            predictDeletion(length, globalPhase, runPhase);
        const int group = classify(deletionProbability);
        peakLiveVolume_ = std::max(
            peakLiveVolume_, liveVolume_ + static_cast<Coordinate>(length));
        // An already available tail can become a two-front arena without
        // requesting any additional excavation.
        if (!arenaActive_ && canSeparate(deletionProbability)) {
            const auto tail = tailGap();
            if (tail != gaps_.end() &&
                tail->second.end - tail->first >= 2LL * length) {
                arenaActive_ = true;
                arenaStart_ = tail->first;
                arenaEnd_ = trenchLength_;
            }
        }
        Choice choice;
        Coordinate digs = 0;
        const auto firstFit = bySize_.lower_bound({length, 0});
        if (firstFit != bySize_.end()) {
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            digs = growFor(length, deletionProbability, choice);
        }
        const auto selected = gaps_.find(choice.gapStart);
        const Coordinate gapStart = selected->first;
        const Gap gap = selected->second;
        eraseGap(selected);
        Pipe pipe;
        pipe.start = choice.start;
        pipe.length = length;
        pipe.previous = gap.left;
        pipe.next = gap.right;
        pipe.runPhase = static_cast<unsigned char>(runPhase);
        pipe.group = static_cast<unsigned char>(group);
        pipe.active = true;
        pipes_.push_back(pipe);
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(
            gapStart, pipe.start, gap.left, pid, gap.freeSince);
        insertGap(
            pipe.start + length, gap.end, pid, gap.right, gap.freeSince);
        changePopulation(length, globalPhase, runPhase, 1, false);
        ++liveGroups_[static_cast<std::size_t>(group)];
        liveVolume_ += length;
        std::cout << digs << ' ' << pipe.start << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const int pid = static_cast<int>(pidValue);
        if (!pipes_[static_cast<std::size_t>(pid)].active) {
            printInvalidPid();
            return;
        }
        beginCommand();
        const Pipe pipe = pipes_[static_cast<std::size_t>(pid)];
        if (pipe.previous != 0) {
            pipes_[pipe.previous].next = pipe.next;
        }
        if (pipe.next != 0) {
            pipes_[pipe.next].previous = pipe.previous;
        } else {
            tailPid_ = pipe.previous;
        }
        Coordinate start = pipe.start;
        Coordinate end = pipe.start + pipe.length;
        auto right = gaps_.lower_bound(start);
        if (right != gaps_.begin()) {
            const auto left = std::prev(right);
            if (left->second.end == start) {
                start = left->first;
                eraseGap(left);
            }
        }
        right = gaps_.lower_bound(end);
        if (right != gaps_.end() && right->first == end) {
            end = right->second.end;
            eraseGap(right);
        }
        pipes_[static_cast<std::size_t>(pid)].active = false;
        insertGap(start, end, pipe.previous, pipe.next, tick_);
        changePopulation(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase), -1, true);
        --liveGroups_[static_cast<std::size_t>(pipe.group)];
        liveVolume_ -= pipe.length;
        if (totalRate_.live == 0) arenaActive_ = false;
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    GapMap gaps_;
    std::set<GapKey> bySize_;
    std::set<GapAgeKey> byAge_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    int tailPid_ = 0;
    Coordinate trenchLength_ = 0;
    Coordinate liveVolume_ = 0;
    Coordinate peakLiveVolume_ = 0;
    std::array<int, 3> liveGroups_{};
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    int lastPlacementLength_ = -1;
    std::uint64_t runOrdinal_ = 0;
    Rate totalRate_;
    std::array<Rate, 41> lengthRates_{};
    std::array<Rate, kPhaseCount> globalPhaseRates_{};
    std::array<Rate, kPhaseCount> runPhaseRates_{};
    std::array<double, 41> lengthRisk_{};
    std::array<double, kPhaseCount> globalPhaseRisk_{};
    std::array<double, kPhaseCount> runPhaseRisk_{};
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, kPotentialLimit + 1> potential_{};
    bool arenaActive_ = false;
    Coordinate arenaStart_ = 0;
    Coordinate arenaEnd_ = 0;
    static double difference(double a, double b) {
        return a >= b ? a - b : b - a;
    }
    static int classify(double probability) {
        if (probability < 1.0 / 3.0) return 0;
        if (probability > 2.0 / 3.0) return 2;
        return 1;
    }
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
        }
    }
    void changePopulation(
        int length, int globalPhase, int runPhase,
        int delta, bool removed) {
        totalRate_.change(tick_, delta, removed);
        lengthRates_[static_cast<std::size_t>(length)].change(
            tick_, delta, removed);
        globalPhaseRates_[static_cast<std::size_t>(globalPhase)].change(
            tick_, delta, removed);
        runPhaseRates_[static_cast<std::size_t>(runPhase)].change(
            tick_, delta, removed);
    }
    void observeLength(int length) {
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        // Hierarchical smoothing shares evidence between cyclic positions.
        // No deletion pattern is enabled by a fixed sequence of commands.
        for (int residue = 0; residue < kPhaseCount; ++residue) {
            double rate = globalRate;
            for (int period = 2; period <= kPhaseCount; period *= 2) {
                double exposure = 0.0;
                double deaths = 0.0;
                for (int position = residue % period;
                     position < kPhaseCount; position += period) {
                    const Rate& observation =
                        observations[static_cast<std::size_t>(position)];
                    exposure += observation.exposureAt(tick_);
                    deaths += observation.deaths;
                }
                constexpr double priorDeaths = 8.0;
                rate = (deaths + priorDeaths) /
                    (exposure + priorDeaths / rate);
            }
            result[static_cast<std::size_t>(residue)] =
                std::clamp(rate / globalRate, 0.125, 8.0);
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
        for (int length = 1; length <= 40; ++length) {
            const Rate& observation =
                lengthRates_[static_cast<std::size_t>(length)];
            constexpr double priorDeaths = 4.0;
            const double rate =
                (observation.deaths + priorDeaths) /
                (observation.exposureAt(tick_) +
                 priorDeaths / globalRate);
            lengthRisk_[static_cast<std::size_t>(length)] =
                std::clamp(rate / globalRate, 0.0625, 16.0);
        }
        rebuildPhaseRisk(
            globalPhaseRates_, globalRate, globalPhaseRisk_);
        rebuildPhaseRisk(
            runPhaseRates_, globalRate, runPhaseRisk_);
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            probability[index] =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            prefix[index] = prefix[index - 1] + probability[index];
        }
        prefix[40] = 1.0;
        // Renewal reward: at each step, allow up to four observed-distribution
        // requests to find a fitting one, then continue with the remainder.
        potential_[0] = 0.0;
        for (int capacity = 1;
             capacity <= kPotentialLimit; ++capacity) {
            const int maximum = std::min(capacity, 40);
            const double fit = prefix[static_cast<std::size_t>(maximum)];
            const double miss = std::max(0.0, 1.0 - fit);
            const double retryFactor =
                1.0 + miss + miss * miss + miss * miss * miss;
            double reward = 0.0;
            for (int length = 1; length <= maximum; ++length) {
                reward += probability[static_cast<std::size_t>(length)] *
                    (static_cast<double>(length) +
                     potential_[static_cast<std::size_t>(capacity - length)]);
            }
            potential_[static_cast<std::size_t>(capacity)] =
                std::clamp(
                    retryFactor * reward,
                    0.0, static_cast<double>(capacity));
        }
    }
    double predictDeletion(
        int length, int globalPhase, int runPhase) const {
        const double phaseMultiplier = 0.5 * (
            globalPhaseRisk_[static_cast<std::size_t>(globalPhase)] +
            runPhaseRisk_[static_cast<std::size_t>(runPhase)]);
        const double relativeRate = std::clamp(
            lengthRisk_[static_cast<std::size_t>(length)] *
                phaseMultiplier,
            1.0 / 32.0, 32.0);
        // A bounded survival approximation over a typical lifetime horizon.
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
    }
    double utility(Coordinate length) const {
        if (length <= 0) return 0.0;
        if (length <= kPotentialLimit) {
            return potential_[static_cast<std::size_t>(length)];
        }
        return potential_[kPotentialLimit] +
            static_cast<double>(length - kPotentialLimit);
    }
    bool canSeparate(double probability) const {
        return totalRate_.deaths >= 16.0 &&
            liveGroups_[0] >= 2 && liveGroups_[2] >= 2 &&
            (probability < 0.25 || probability > 0.75);
    }
    void considerGap(
        Coordinate gapStart, int length,
        double newDeletion, Choice& best) const {
        const auto found = gaps_.find(gapStart);
        if (found == gaps_.end()) return;
        const Gap& gap = found->second;
        const Coordinate span = gap.end - gapStart;
        if (span < length) return;
        if (gap.end == trenchLength_) {
            // Use the expandable tail only when no interior gap fits.
            // The unique tail can occupy at most one size-index entry.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        // On a neighbor's release, its far-side free gap also coalesces.
        // The release loops below include this span only in that event.
        Coordinate leftLength = 0;
        if (gap.left != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.left)];
            leftLength = neighbor.length;
            const auto next = gaps_.lower_bound(neighbor.start);
            if (next != gaps_.begin()) {
                const auto outside = std::prev(next);
                if (kCoalescingReleaseGeometry &&
                    outside->second.end == neighbor.start) {
                    leftLength += outside->second.end - outside->first;
                }
            }
        }
        Coordinate rightLength = 0;
        if (gap.right != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.right)];
            rightLength = neighbor.length;
            const auto outside =
                gaps_.find(neighbor.start + neighbor.length);
            if (kCoalescingReleaseGeometry && outside != gaps_.end()) {
                rightLength += outside->second.end - outside->first;
            }
        }
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
        // Expected opportunity cost conditional on the new pipe surviving.
        // Each neighboring pipe can independently release its occupied span.
        for (int releaseLeft = 0; releaseLeft < 2; ++releaseLeft) {
            const double leftWeight = releaseLeft
                ? leftDeletion : 1.0 - leftDeletion;
            const Coordinate leftFree =
                releaseLeft ? leftLength : 0;
            for (int releaseRight = 0; releaseRight < 2; ++releaseRight) {
                const double rightWeight = releaseRight
                    ? rightDeletion : 1.0 - rightDeletion;
                const double weight = leftWeight * rightWeight;
                if (weight == 0.0) continue;
                const Coordinate rightFree =
                    releaseRight ? rightLength : 0;
                const double whole =
                    utility(span + leftFree + rightFree);
                futureLow += weight * (
                    whole - utility(leftFree) -
                    utility(remainder + rightFree));
                futureHigh += weight * (
                    whole - utility(remainder + leftFree) -
                    utility(rightFree));
            }
        }
        const bool insideArena =
            arenaActive_ && gapStart >= arenaStart_ &&
            gap.end <= arenaEnd_;
        const double futureWeight = 0.5 * (1.0 - newDeletion);
        for (int side = 0; side < 2; ++side) {
            const bool high = side != 0;
            if (high && remainder == 0) continue;
            if (high && gap.end == trenchLength_ && !insideArena) {
                continue;
            }
            const double futureCost = high ? futureHigh : futureLow;
            double score =
                (1.0 - futureWeight) * immediateCost +
                futureWeight * futureCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    // Fast-deleting pipes approach from the low side;
                    // slow-deleting pipes approach from the high side.
                    score += 0.125 * length *
                        (high ? newDeletion : 1.0 - newDeletion);
                }
            } else {
                if (gap.left != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, leftDeletion);
                }
                if (gap.right != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, rightDeletion);
                }
            }
            const Coordinate position =
                high ? gap.end - length : gapStart;
            const bool sameSpanTieBetter =
                (kOldestGapTieBreak && gap.freeSince != best.freeSince)
                    ? gap.freeSince < best.freeSince
                    : position < best.start;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && sameSpanTieBetter)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.freeSince = gap.freeSince;
                best.score = score;
            }
        }
    }
    void considerOldest(
        Coordinate span, int length,
        double deletionProbability, Choice& choice) const {
        if (span < length) return;
        auto oldest = byAge_.lower_bound({span, {0, 0}});
        if (oldest == byAge_.end() || oldest->first != span) return;
        const auto found = gaps_.find(oldest->second.second);
        if (found->second.end == trenchLength_) {
            // If the oldest is the tail, the next entry of this span
            // is the oldest interior gap. There is only one tail.
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        // Candidate coverage is identical in both tie-break ablations.
        // considerGap retains the exact interior-before-tail check.
        considerGap(
            oldest->second.second, length, deletionProbability, choice);
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
        considerOldest(
            first->first, length, deletionProbability, choice);
    }
    void selectCandidates(
        int length, int group,
        double deletionProbability, Choice& choice) const {
        auto current = bySize_.lower_bound({length, 0});
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const auto after = bySize_.upper_bound({
                current->first,
                std::numeric_limits<Coordinate>::max()});
            considerGap(
                current->second, length, deletionProbability, choice);
            const auto last = std::prev(after);
            if (last->second != current->second) {
                considerGap(
                    last->second, length, deletionProbability, choice);
            }
            considerOldest(
                current->first, length, deletionProbability, choice);
            current = after;
        }
        // Include wider residual-capacity bands even when many small
        // distinct spans precede them.
        for (int offset : {40, 80, 160}) {
            considerNear(
                bySize_, static_cast<Coordinate>(length) + offset,
                length, deletionProbability, choice);
        }
        considerNear(
            byBoundaryGroup_[static_cast<std::size_t>(group)],
            length, length, deletionProbability, choice);
        if (!gaps_.empty()) {
            const auto last = std::prev(gaps_.end());
            if (last->second.end == trenchLength_) {
                considerGap(
                    last->first, length, deletionProbability, choice);
                considerOldest(
                    last->second.end - last->first,
                    length, deletionProbability, choice);
            }
        }
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_ ? last : gaps_.end();
    }
    Coordinate growFor(
        int length, double deletionProbability, Choice& choice) {
        Coordinate start = trenchLength_;
        int left = tailPid_;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            start = tail->first;
            left = tail->second.left;
            eraseGap(tail);
        }
        const Coordinate available = trenchLength_ - start;
        const Coordinate deficit =
            std::max<Coordinate>(0, length - available);
        Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        const bool separate = canSeparate(deletionProbability);
        Coordinate extraDigs = 0;
        if (separate) {
            const Coordinate minimumCapacity =
                available + digs * kSectionLength;
            const Coordinate wantedExtra = std::max<Coordinate>(
                0, 3LL * length - minimumCapacity);
            const Coordinate budgetSections =
                (peakLiveVolume_ / 64) / kSectionLength;
            const Coordinate wantedSections =
                (wantedExtra + kSectionLength - 1) / kSectionLength;
            extraDigs = std::min(budgetSections, wantedSections);
            digs += extraDigs;
        }
        if (extraDigs > 0) ++expansionGatePasses;
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0, tick_);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right, freeSince});
        const GapKey key{end - start, start};
        bySize_.insert(key);
        byAge_.insert({key.first, {freeSince, start}});
        const int leftGroup = left == 0
            ? -1 : static_cast<int>(pipes_[left].group);
        const int rightGroup = right == 0
            ? -1 : static_cast<int>(pipes_[right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].insert(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].insert(key);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const GapKey key{gap.end - start, start};
        bySize_.erase(key);
        byAge_.erase({key.first, {gap.freeSince, start}});
        const int leftGroup = gap.left == 0
            ? -1 : static_cast<int>(pipes_[gap.left].group);
        const int rightGroup = gap.right == 0
            ? -1 : static_cast<int>(pipes_[gap.right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].erase(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].erase(key);
        }
        gaps_.erase(position);
    }
    static void printInvalidPid() {
        std::cout << 0 << '\n' << std::flush;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.85; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.76; max_solver_rss_mib: 7.91

Here is additional text feedback about the current program:

Fitness F/T=0.854981207953; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.736993688
family=short_phase_churn mean_F/T=0.771580065
family=short_heavy mean_F/T=0.783707342
family=tiny_churn mean_F/T=0.785003666
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.802981167
family=additive_cohorts mean_F/T=0.807363433
family=geometric_cohorts mean_F/T=0.811928732
family=short_rounding mean_F/T=0.818636924
family=fifo mean_F/T=0.831009381
family=uniform_churn mean_F/T=0.836774842
family=size_biased_deletion mean_F/T=0.845159605
family=distribution_switch mean_F/T=0.845403369
family=long_heavy mean_F/T=0.845457065
family=long_prefill_random mean_F/T=0.845592675
family=micro_tail_reuse mean_F/T=0.845833333
family=size_lifetimes mean_F/T=0.861711288
family=serial_churn mean_F/T=0.871743241
family=large_live_set mean_F/T=0.878994949
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881988264
family=hotset_switching mean_F/T=0.882767279
family=bimodal mean_F/T=0.884310625
family=section_boundaries mean_F/T=0.894107206
family=soft_recency_growth mean_F/T=0.895600096
family=burst_drain mean_F/T=0.901909891
family=serial_growth mean_F/T=0.912305509
family=long_prefill_recent mean_F/T=0.917856960
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920150122
family=drain_recovery mean_F/T=0.923650325
family=background_ephemeral mean_F/T=0.951952070
family=hotset_growth mean_F/T=0.952067505
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001579 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001745 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001523 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001516 rss_mib=1.359
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001493 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001494 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611126393 F/B=0.646045362 B/T=0.945949663 overrun=0.057139 cpu_s=0.104801 rss_mib=2.375
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617722509 F/B=0.675406191 B/T=0.914594087 overrun=0.093381 cpu_s=0.483166 rss_mib=4.016
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.530638 rss_mib=3.125
case=s31_024_fifo family=fifo F/T=0.628735632 F/B=0.770422535 B/T=0.816091954 overrun=0.225352 cpu_s=0.027779 rss_mib=1.578
case=s31_060_large_live_set family=large_live_set F/T=0.632901343 F/B=0.641932619 B/T=0.985931115 overrun=0.014270 cpu_s=0.683288 rss_mib=4.812
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001549 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001796 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003434 rss_mib=1.406
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.014741 rss_mib=1.531
case=s31_008_short_heavy family=short_heavy F/T=0.661538462 F/B=0.758823529 B/T=0.871794872 overrun=0.147059 cpu_s=0.022560 rss_mib=1.500
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_086_tiny_churn family=tiny_churn F/T=0.717741935 F/B=0.959051724 B/T=0.748387097 overrun=0.336207 cpu_s=0.183903 rss_mib=2.156
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.443112 rss_mib=3.766
case=s31_006_short_heavy family=short_heavy F/T=0.739655172 F/B=0.953333333 B/T=0.775862069 overrun=0.288889 cpu_s=0.502206 rss_mib=3.797
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.625581395 F/B=0.781976744 B/T=0.800000000 overrun=0.250000 cpu_s=0.530638 rss_mib=3.125
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003168 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.702435065 F/B=0.865400000 B/T=0.811688312 overrun=0.232000 cpu_s=0.112284 rss_mib=1.812
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.696875000 F/B=0.857692308 B/T=0.812500000 overrun=0.230769 cpu_s=0.002871 rss_mib=1.375
case=s31_009_long_heavy family=long_heavy F/T=0.775423729 F/B=0.953125000 B/T=0.813559322 overrun=0.229167 cpu_s=0.479215 rss_mib=3.844
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.774269663 F/B=0.950045956 B/T=0.814981273 overrun=0.227022 cpu_s=0.205414 rss_mib=2.406
case=s31_024_fifo family=fifo F/T=0.628735632 F/B=0.770422535 B/T=0.816091954 overrun=0.225352 cpu_s=0.027779 rss_mib=1.578
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.071868 rss_mib=1.656
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001849 rss_mib=1.359
case=s31_087_tiny_churn family=tiny_churn F/T=0.800000000 F/B=0.950000000 B/T=0.842105263 overrun=0.187500 cpu_s=0.691647 rss_mib=3.328
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.842553191 F/B=0.990000000 B/T=0.851063830 overrun=0.175000 cpu_s=0.050968 rss_mib=1.625
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821110177 F/B=0.950170316 B/T=0.864171573 overrun=0.157178 cpu_s=0.212051 rss_mib=2.297
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852809150 F/B=0.982097589 B/T=0.868354795 overrun=0.151603 cpu_s=0.234414 rss_mib=3.625

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.854981208; mean positive loss on worst 16 cases=0.000000000; max case loss=0.000000000; regressed cases=0; worst family delta F/T=+0.000000000. These are selection diagnostics; primary fitness remains mean F/T.


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
#include <bit>
// NAME: tail_coalescence_guard
// DESCRIPTION: Родительский marginal_tail_growth с ограничением,
// сохраняющим полезность слияния остатка с правым соседом.
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
// Хвост выбирается только при строгом уменьшении этой стоимости
// и не меньшей полезности слияния при удалении правого соседа.
// Полезность — снижение прогнозируемого роста от объединения интервалов.
// Перед любым расширением сохраняется глобальный поиск подходящей дыры.
//
// Вставка: амортизированно O(log(H+V) + 80 + 40),
// удаление: O(log(H+V)); V — число живых труб.
// Память: O(P + H + V).
// Недостаток: время удаления соседа неизвестно; ограничение может
// отклонять полезное использование хвоста ради далёкого слияния.
// Ablation: kTailMergeGuard = false восстанавливает решения родителя.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kTailMergeGuard = true;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    HoleMap liveByAddress_;
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
    std::int64_t projectedGrowth(int largestHole, int tail) const {
        const int threshold = std::max(largestHole, tail);
        std::int64_t cost = 0;
        for (int k = threshold + 1; k <= kMaxLength; ++k) {
            cost += static_cast<std::int64_t>(weights_[k])
                  * ((k - tail + 19) / 20);
        }
        return cost;
    }
    bool tailPreservesMerge(int length, int holeStart, int holeSize,
                            int largestOther) const {
        if constexpr (!kTailMergeGuard) {
            return true;
        }
        const int remainder = holeSize - length;
        if (remainder == 0) {
            return true;
        }
        const auto neighbor = liveByAddress_.find(holeStart + holeSize);
        if (neighbor == liveByAddress_.end()) {
            return true;
        }
        const int tail = trench_ - frontier_;
        const int neighborEnd = neighbor->first + neighbor->second;
        int releasedLength = neighbor->second;
        if (neighborEnd != frontier_) {
            const auto outer = holes_.find(neighborEnd);
            if (outer != holes_.end()) {
                releasedLength += outer->second;
            }
        }
        // largestOther may include the outer hole: releasedLength
        // already dominates its length in both comparisons.
        const auto internalMergeGain = [&](int residual, int suffix) {
            const int separateLargest =
                std::max({largestOther, residual, releasedLength});
            const int joinedLargest =
                std::max(largestOther, residual + releasedLength);
            return projectedGrowth(separateLargest, suffix)
                 - projectedGrowth(joinedLargest, suffix);
        };
        std::int64_t holeGain;
        if (neighborEnd == frontier_) {
            // With the hole placement, deletion returns this neighbor
            // and the adjacent remainder to the free suffix.
            const int releasedTail = tail + neighbor->second;
            holeGain = projectedGrowth(
                           std::max(largestOther, remainder),
                           releasedTail)
                     - projectedGrowth(
                           largestOther, releasedTail + remainder);
        } else {
            holeGain = internalMergeGain(remainder, tail);
        }
        // A tail placement leaves the whole hole available.
        // It also makes the old final neighbor internal.
        const std::int64_t tailGain =
            internalMergeGain(holeSize, tail - length);
        return tailGain >= holeGain;
    }
    bool preferFreeTail(int length, int holeStart, int holeSize) const {
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
        return tailCost < holeCost &&
               tailPreservesMerge(length, holeStart, holeSize,
                                  largestOther);
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
            !preferFreeTail(length, chosen.first, chosen.second)) {
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
        liveByAddress_.emplace(start, length);
        pipes_.push_back({start, length});
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        liveByAddress_.erase(originalStart);
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

Performance metrics: Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 6.98


