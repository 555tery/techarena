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