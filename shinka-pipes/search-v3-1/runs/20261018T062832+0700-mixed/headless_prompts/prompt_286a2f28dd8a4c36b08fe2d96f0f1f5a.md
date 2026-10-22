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
gen0 initial_program; correct=True; parent=None; delta_F/T=n/a; claim=Initial program setup
gen24 exposure_guided_split; correct=True; parent=6; delta_F/T=+0.001161829; claim=Родитель gen6 сохраняется: размеры bins меньше 80, коэффициент regret 8, prior 1 на размер, обновление профиля каждые 64 вставки после первых 32, уменьшение наблюдений вдвое каждые 512 вставок.
Новый механизм выбирает ст
  improved/regressed/tied=39/37/76
  regression s31_007_short_heavy: delta_F/T=-0.041309524
  regression s31_009_long_heavy: delta_F/T=-0.038793103
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
  improved/regressed/tied=28/34/90
  regression s31_049_geometric_cohorts: delta_F/T=-0.058240647
  regression s31_017_section_boundaries: delta_F/T=-0.052240461
gen28 release_order_split; correct=True; parent=3; delta_F/T=-0.000432007; claim=Родитель — текущий gen3 Best-Fit. Предлагаю обучаемый выбор стороны разрезания gap: сохранять остаток рядом с соседом, который, согласно наблюдаемому порядку освобождений, вероятнее освободится раньше. Это может ускорить
  improved/regressed/tied=43/25/84
  regression s31_085_tiny_churn: delta_F/T=-0.041403162
  regression s31_062_size_biased_deletion: delta_F/T=-0.031742630
HISTORICA
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=specialist; specialist families=['bimodal', 'distribution_switch', 'geometric_cohorts', 'hotset_growth', 'long_heavy', 'section_boundaries', 'serial_churn', 'size_biased_deletion', 'uniform_churn']; fixed-baseline tail loss=0.000000000; maximum case loss=0.000000000. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
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
NAME: Causal Bellman Pair Pricing
DESCRIPTION:
Свободные внутренние интервалы объединяются при удалениях и индексируются
по координате и длине. Основной выбор — best fit с предпочтением меньшей
координаты. Свободный хвост хранится отдельно и расширяется минимально.
Когда текущая труба помещается и во внутренний интервал, и в хвост,
сравнивается прогноз расширения для двух следующих вставок.
Профили P(a | current) и P(b | a) используют только прошлые наблюдения.
После раскрытия прогнозируемой длины a выбирается размещение,
минимизирующее расширение для a плюс ожидаемое расширение для b.
Выбор размещения a не получает доступа к ещё неизвестной длине b.
Внутренний вариант сохраняет крупнейшее отверстие, если a помещается
во второе; иначе крупнейшим становится максимум остатка и второго.
Хвост рассматривается без роста, когда он уже вмещает a.
Рост для a разрешён только при отсутствии подходящего свободного места.
Для последней прогнозируемой вставки используется expectedNextGrowth.
При близких оценках сохраняется обычный best fit.
Реальное расширение также выполняется только при отсутствии места.
Вставка: O(40 + log(H + 1)); удаление: O(log(H + 1)).
Память: O(I + H + 40^2), дополнительная память механизма постоянная.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения, удаления между вставками
и отличие реального пересчитываемого горизонта от модели продолжения.
Same-parent ablation: kCausalPairPricing = false при
kPairTailPricing = true восстанавливает Markov Pair Tail Pricing.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    static constexpr bool kTailLookahead = true;
    static constexpr bool kPairTailPricing = true;
    static constexpr bool kCausalPairPricing = true;
    static constexpr double kGlobalDecay = 127.0 / 128.0;
    static constexpr double kTransitionDecay = 31.0 / 32.0;
    static constexpr double kPriorWeight = 8.0;
    static constexpr double kDecisionMargin = 1.0 / 64.0;
    FreeMap holes_;
    std::set<std::pair<int, int>> bySize_;
    std::vector<Pipe> pipes_;
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
    double expectedPairGrowth(
        int largestHole, int secondLargestHole,
        int tailLength, int currentLength
    ) const {
        if (kCausalPairPricing) {
            double expected = 0.0;
            double previousAbove = forecastAbove(0, currentLength);
            for (int firstLength = 1; firstLength <= 40; ++firstLength) {
                const double above =
                    forecastAbove(firstLength, currentLength);
                const double probability = previousAbove - above;
                previousAbove = above;
                if (probability <= 0.0) {
                    continue;
                }
                double cost = 0.0;
                if (largestHole >= firstLength) {
                    // Best fit сохраняет крупнейшее отверстие,
                    // если существует другое подходящее.
                    const int largestAfter =
                        secondLargestHole >= firstLength
                        ? largestHole
                        : std::max(
                            secondLargestHole, largestHole - firstLength
                        );
                    cost = expectedNextGrowth(
                        largestAfter, tailLength, firstLength
                    );
                    if (tailLength >= firstLength) {
                        // Минимум берётся до раскрытия второй длины.
                        cost = std::min(
                            cost,
                            expectedNextGrowth(
                                largestHole,
                                tailLength - firstLength,
                                firstLength
                            )
                        );
                    }
                } else {
                    // Внутреннего места нет: используем хвост
                    // и добавляем только необходимые секции.
                    const int shortage =
                        std::max(0, firstLength - tailLength);
                    const int sections = (shortage + 19) / 20;
                    const int remainingTail =
                        tailLength + 20 * sections - firstLength;
                    cost = static_cast<double>(sections) +
                        expectedNextGrowth(
                            largestHole, remainingTail, firstLength
                        );
                }
                expected += probability * cost;
            }
            return expected;
        }
        std::array<int, 4> largest{};
        std::array<int, 4> second{};
        int stages = 0;
        for (int sections = 0; sections < 4; ++sections) {
            const int extendedTail = tailLength + 20 * sections;
            const int first = std::max(largestHole, extendedTail);
            const int next = std::max(
                secondLargestHole, std::min(largestHole, extendedTail)
            );
            // Любая пара длин 1..40 уже помещается.
            if (first >= 80 || next >= 40) {
                break;
            }
            largest[stages] = first;
            second[stages] = next;
            ++stages;
        }
        if (stages == 0) {
            return 0.0;
        }
        double expected = 0.0;
        double previousAbove = forecastAbove(0, currentLength);
        for (int firstLength = 1; firstLength <= 40; ++firstLength) {
            const double above = forecastAbove(firstLength, currentLength);
            const double probability = previousAbove - above;
            previousAbove = above;
            if (probability <= 0.0) {
                continue;
            }
            for (int stage = 0; stage < stages; ++stage) {
                if (firstLength > largest[stage]) {
                    expected += probability;
                    continue;
                }
                // Если первая труба помещается во второй интервал,
                // крупнейший целиком доступен второй трубе.
                // Иначе трубы используют крупнейший совместно
                // либо вторая труба занимает второй интервал.
                const int secondLimit =
                    firstLength <= second[stage]
                    ? largest[stage]
                    : std::max(
                        second[stage], largest[stage] - firstLength
                    );
                expected += probability *
                    forecastAbove(secondLimit, firstLength);
            }
        }
        return expected;
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
                const auto largestIt = bySize_.rbegin();
                const int largestBefore = largestIt->first;
                const auto secondIt = std::next(largestIt);
                const int secondBefore =
                    secondIt == bySize_.rend() ? 0 : secondIt->first;
                int largestOther = 0;
                int secondOther = 0;
                // Достаточно просмотреть максимум три элемента.
                for (auto it = bySize_.rbegin(); it != bySize_.rend(); ++it) {
                    if (it->second == holeStart) {
                        continue;
                    }
                    if (largestOther == 0) {
                        largestOther = it->first;
                    } else {
                        secondOther = it->first;
                        break;
                    }
                }
                const int remainder = holeLength - length;
                const int largestAfterHole =
                    std::max(largestOther, remainder);
                const int secondAfterHole = std::max(
                    secondOther, std::min(largestOther, remainder)
                );
                const double holeCost = kPairTailPricing
                    ? expectedPairGrowth(
                        largestAfterHole, secondAfterHole, tailLength, length
                    )
                    : expectedNextGrowth(
                        largestAfterHole, tailLength, length
                    );
                const double tailCost = kPairTailPricing
                    ? expectedPairGrowth(
                        largestBefore, secondBefore, tailLength - length, length
                    )
                    : expectedNextGrowth(
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
            coordinate = holeStart;
            eraseHole(holes_.find(holeStart));
            addHole(holeStart + length, holeLength - length);
        } else {
            coordinate = frontier_;
            const int shortage = length - tailLength;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ += length;
        }
        pipes_.push_back(Pipe{coordinate, length});
        std::cout << sections << ' ' << coordinate << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const std::size_t index = static_cast<std::size_t>(pid);
        const Pipe old = pipes_[index];
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
        pipes_[index].length = 0;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 0.89; max_solver_rss_mib: 2.61

Text feedback:
Fitness F/T=0.857074883957; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737654500
family=short_phase_churn mean_F/T=0.785232978
family=drifting_sizes mean_F/T=0.797299008
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808464826
family=short_heavy mean_F/T=0.812037469
family=additive_cohorts mean_F/T=0.822933487
family=size_biased_deletion mean_F/T=0.824921648
family=distribution_switch mean_F/T=0.827333363
family=tiny_churn mean_F/T=0.830637449
family=uniform_churn mean_F/T=0.831586840
family=long_heavy mean_F/T=0.839416878
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.853987158
family=size_lifetimes mean_F/T=0.868427086
family=large_live_set mean_F/T=0.880364533
family=bimodal mean_F/T=0.880879623
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881619127
family=fifo mean_F/T=0.882703012
family=section_boundaries mean_F/T=0.887002269
family=hotset_switching mean_F/T=0.887174306
family=soft_recency_growth mean_F/T=0.896268309
family=burst_drain mean_F/T=0.904727655
family=serial_growth mean_F/T=0.915404237
family=long_prefill_recent mean_F/T=0.917726656
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920923550
family=drain_recovery mean_F/T=0.925242605
family=hotset_growth mean_F/T=0.949589609
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955600008
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001514 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001318 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001382 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001385 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001394 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001414 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.612558588 F/B=0.646045362 B/T=0.948166529 overrun=0.054667 cpu_s=0.090064 rss_mib=1.578
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.616372717 F/B=0.675406191 B/T=0.912595599 overrun=0.095776 cpu_s=0.290892 rss_mib=1.750
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.315122 rss_mib=1.625
case=s31_060_large_live_set family=large_live_set F/T=0.631905345 F/B=0.641932619 B/T=0.984379554 overrun=0.015868 cpu_s=0.395381 rss_mib=2.141
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001433 rss_mib=1.344
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001397 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002871 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012667 rss_mib=1.375
case=s31_040_distribution_switch family=distribution_switch F/T=0.670000000 F/B=0.692548077 B/T=0.967441860 overrun=0.033654 cpu_s=0.018389 rss_mib=1.375
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002827 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.376357 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.353609 rss_mib=1.672
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.315122 rss_mib=1.625
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.122355 rss_mib=1.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002827 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.072676 rss_mib=1.422
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.060374 rss_mib=1.391
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001679 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002286 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.118036 rss_mib=1.469
case=s31_006_short_heavy family=short_heavy F/T=0.809433962 F/B=0.953333333 B/T=0.849056604 overrun=0.177778 cpu_s=0.324916 rss_mib=1.656
case=s31_102_serial_churn family=serial_churn F/T=0.807754011 F/B=0.950000000 B/T=0.850267380 overrun=0.176101 cpu_s=0.145721 rss_mib=1.484
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.518712 rss_mib=1.812
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.825065274 F/B=0.954682779 B/T=0.864229765 overrun=0.157100 cpu_s=0.035077 rss_mib=1.391
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.116394 rss_mib=1.562
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.117156 rss_mib=1.469

PAIRED SEARCH EVIDENCE
Against parent gen22: delta mean F/T=-0.000220957; improved/regressed/tied=10/13/129.
family=short_rounding delta_F/T=-0.010414759
family=hotset_switching delta_F/T=+0.005813614
family=burst_drain delta_F/T=-0.005641026
family=fifo delta_F/T=-0.004448342
family=additive_cohorts delta_F/T=+0.004066212
family=long_heavy delta_F/T=+0.003621563
Regressions:
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_033_burst_drain: delta_F/T=-0.022564103, delta_T=+20
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
s31_038_distribution_switch: delta_F/T=-0.006584261, delta_T=+40
Gains:
s31_094_hotset_switching: delta_F/T=+0.021732831, delta_T=-60
s31_055_additive_cohorts: delta_F/T=+0.016264850, delta_T=-20
s31_012_long_heavy: delta_F/T=+0.014486253, delta_T=-120
s31_037_distribution_switch: delta_F/T=+0.002165455, delta_T=-60

Against leader gen5: delta mean F/T=-0.000461163; improved/regressed/tied=24/25/103.
family=size_biased_deletion delta_F/T=-0.011957315
family=long_heavy delta_F/T=+0.006687374
family=drifting_sizes delta_F/T=-0.006661367
family=serial_churn delta_F/T=-0.006452015
family=hotset_switching delta_F/T=+0.005310053
family=size_lifetimes delta_F/T=+0.004539398
Regressions:
s31_063_size_biased_deletion: delta_F/T=-0.039121447, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.036100738, delta_T=+160
s31_041_drifting_sizes: delta_F/T=-0.023199023, delta_T=+40
s31_023_fifo: delta_F/T=-0.017793367, delta_T=+20
Gains:
s31_040_distribution_switch: delta_F/T=+0.021126126, delta_T=-140
s31_127_short_phase_churn: delta_F/T=+0.018736786, delta_T=-20
s31_095_hotset_switching: delta_F/T=+0.017786561, delta_T=-100
s31_029_size_lifetimes: delta_F/T=+0.017318118, delta_T=-80

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857074884; mean positive loss on worst 16 cases=0.027358963; max case loss=0.049653143; regressed cases=41; worst family delta F/T=-0.020237957. These are selection diagnostics; primary fitness remains mean F/T.

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
NAME: Conditional Tail-Priced Best Fit
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
Вставка: O(40 + log(H + 1)); удаление: O(log(H + 1)).
Память: O(I + H + 40^2), где I — число вставок, H — число отверстий.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения длин или ближайшее удаление могут
сделать прогноз неверным; горизонт в одну вставку не учитывает дальнейшую
фрагментацию. Ablation: установить kTailLookahead = false, получив обычный
best fit с теми же объединениями и минимальным расширением.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    static constexpr bool kTailLookahead = true;
    static constexpr double kGlobalDecay = 127.0 / 128.0;
    static constexpr double kTransitionDecay = 31.0 / 32.0;
    static constexpr double kPriorWeight = 8.0;
    static constexpr double kDecisionMargin = 1.0 / 64.0;
    FreeMap holes_;
    std::set<std::pair<int, int>> bySize_;
    std::vector<Pipe> pipes_;
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
            coordinate = holeStart;
            eraseHole(holes_.find(holeStart));
            addHole(holeStart + length, holeLength - length);
        } else {
            coordinate = frontier_;
            const int shortage = length - tailLength;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ += length;
        }
        pipes_.push_back(Pipe{coordinate, length});
        std::cout << sections << ' ' << coordinate << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const std::size_t index = static_cast<std::size_t>(pid);
        const Pipe old = pipes_[index];
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
        pipes_[index].length = 0;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.94; max_solver_rss_mib: 2.61

Text feedback:
Fitness F/T=0.857536046508; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737806224
family=short_phase_churn mean_F/T=0.781919230
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803960374
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808464826
family=short_heavy mean_F/T=0.815928978
family=additive_cohorts mean_F/T=0.822933487
family=distribution_switch mean_F/T=0.824892062
family=tiny_churn mean_F/T=0.830637449
family=long_heavy mean_F/T=0.832729504
family=uniform_churn mean_F/T=0.834687953
family=size_biased_deletion mean_F/T=0.836878963
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=serial_churn mean_F/T=0.860439174
family=size_lifetimes mean_F/T=0.863887688
family=large_live_set mean_F/T=0.880156087
family=micro_gap_refill mean_F/T=0.881250000
family=hotset_switching mean_F/T=0.881864253
family=recent_window_growth mean_F/T=0.882308610
family=bimodal mean_F/T=0.882404172
family=fifo mean_F/T=0.887151354
family=section_boundaries mean_F/T=0.888648274
family=soft_recency_growth mean_F/T=0.895941490
family=burst_drain mean_F/T=0.904727891
family=serial_growth mean_F/T=0.915216684
family=long_prefill_recent mean_F/T=0.917738148
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921058688
family=drain_recovery mean_F/T=0.925497134
family=hotset_growth mean_F/T=0.949413287
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955390382
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001513 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001310 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001316 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001348 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001383 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001526 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.612558588 F/B=0.646045362 B/T=0.948166529 overrun=0.054667 cpu_s=0.083167 rss_mib=1.609
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618012520 F/B=0.675406191 B/T=0.915023474 overrun=0.092868 cpu_s=0.292684 rss_mib=1.750
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.322374 rss_mib=1.625
case=s31_060_large_live_set family=large_live_set F/T=0.631905345 F/B=0.641932619 B/T=0.984379554 overrun=0.015868 cpu_s=0.396608 rss_mib=2.172
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001378 rss_mib=1.344
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.016791 rss_mib=1.375
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001304 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002799 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.011911 rss_mib=1.375
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002757 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.370642 rss_mib=1.672
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.322374 rss_mib=1.625
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.133684 rss_mib=1.609
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.346111 rss_mib=1.641
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002757 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.074404 rss_mib=1.422
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.062092 rss_mib=1.391
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001674 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002265 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.806159420 F/B=0.959051724 B/T=0.840579710 overrun=0.189655 cpu_s=0.114306 rss_mib=1.469
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.537218 rss_mib=1.812
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.351359 rss_mib=1.656
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.119309 rss_mib=1.562
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.033976 rss_mib=1.391
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.152689 rss_mib=1.906
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030590 rss_mib=1.391

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.002554839; improved/regressed/tied=50/38/64.
family=fifo delta_F/T=+0.056141973
family=tiny_churn delta_F/T=+0.045633783
family=short_heavy delta_F/T=+0.032221636
family=distribution_switch delta_F/T=-0.020511308
family=additive_cohorts delta_F/T=+0.015570054
family=long_heavy delta_F/T=-0.012727561
Regressions:
s31_039_distribution_switch: delta_F/T=-0.049653143, delta_T=+80
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_009_long_heavy: delta_F/T=-0.037520503, delta_T=+60
Gains:
s31_024_fifo: delta_F/T=+0.141686903, delta_T=-320
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40
s31_086_tiny_churn: delta_F/T=+0.088417485, delta_T=-340
s31_006_short_heavy: delta_F/T=+0.085344828, delta_T=-120

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857536047; mean positive loss on worst 16 cases=0.024157481; max case loss=0.049653143; regressed cases=38; worst family delta F/T=-0.020511308. These are selection diagnostics; primary fitness remains mean F/T.


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

Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
