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
Внутри выбранной дыры остаток оставляется у соседа с большей полезностью
будущего слияния. Учитываются новые обслуживаемые размеры, их прогнозный
спрос и число альтернативных подходящих интервалов. Освобождаемый компонент
включает соседа и внешний свободный интервал, включая хвост.
При равной полезности труба занимает левый край.
Вставка амортизированно: O(40 + log(H + 1)); удаление: O(log(H + 1)).
Память: O(I + H + T + 40^2), где T — фактическая длина траншеи.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения длин нарушает прогноз, а неодинаковые
вероятности удаления соседей могут сделать выбранную ориентацию неудачной.
Ablation: kScarceMergeOrientation = false восстанавливает родителя.
Дополнительное отключение kTailLookahead даёт обычный best fit.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    struct Boundary {
        std::uint8_t starting = 0;
        std::uint8_t ending = 0;
    };
    static constexpr bool kTailLookahead = true;
    static constexpr bool kScarceMergeOrientation = true;
    static constexpr double kGlobalDecay = 127.0 / 128.0;
    static constexpr double kTransitionDecay = 31.0 / 32.0;
    static constexpr double kPriorWeight = 8.0;
    static constexpr double kDecisionMargin = 1.0 / 64.0;
    FreeMap holes_;
    std::set<std::pair<int, int>> bySize_;
    std::vector<Pipe> pipes_;
    std::vector<Boundary> boundaries_;
    std::array<int, 41> holeCounts_{};
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
    bool preferRightEdge(
        FreeMap::const_iterator hole, int length
    ) const {
        const int remainder = hole->second - length;
        if (remainder <= 0 || remainder >= 40) {
            return false;
        }
        const int holeStart = hole->first;
        const int holeEnd = holeStart + hole->second;
        const int tailLength = trenchLength_ - frontier_;
        const int leftLength = boundaries_[holeStart].ending;
        const int rightLength = boundaries_[holeEnd].starting;
        int leftReach = leftLength;
        if (leftLength > 0 && hole != holes_.begin()) {
            auto outside = std::prev(hole);
            if (outside->first + outside->second ==
                holeStart - leftLength) {
                leftReach += outside->second;
            }
        }
        int rightReach = rightLength;
        if (rightLength > 0) {
            const int neighborEnd = holeEnd + rightLength;
            auto outside = std::next(hole);
            if (outside != holes_.end() &&
                outside->first == neighborEnd) {
                rightReach += outside->second;
            } else if (neighborEnd == frontier_) {
                rightReach += tailLength;
            }
        }
        std::array<int, 41> postFits{};
        int fitting = 0;
        for (int k = 40; k >= 1; --k) {
            fitting += holeCounts_[k];
            postFits[k] =
                fitting - (hole->second >= k ? 1 : 0) +
                (remainder >= k ? 1 : 0) +
                (tailLength >= k ? 1 : 0);
        }
        std::array<double, 41> prefix{};
        double previousAbove = forecastAbove(0, length);
        for (int k = 1; k <= 40; ++k) {
            const double above = forecastAbove(k, length);
            const double demand = std::max(0.0, previousAbove - above);
            prefix[k] = prefix[k - 1] +
                demand * static_cast<double>(k) /
                (1.0 + static_cast<double>(postFits[k]));
            previousAbove = above;
        }
        const auto gain = [&](int reach) {
            const int before =
                std::min(40, std::max(remainder, reach));
            const int after = std::min(40, remainder + reach);
            return prefix[after] - prefix[before];
        };
        return gain(leftReach) > gain(rightReach) + 1e-12;
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        bySize_.emplace(length, start);
        ++holeCounts_[std::min(40, length)];
    }
    void eraseHole(FreeMap::iterator it) {
        --holeCounts_[std::min(40, it->second)];
        bySize_.erase(std::make_pair(it->second, it->first));
        holes_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        boundaries_.resize(1);
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
            auto hole = holes_.find(holeStart);
            const int remainder = holeLength - length;
            const bool atRight =
                kScarceMergeOrientation && preferRightEdge(hole, length);
            eraseHole(hole);
            if (atRight) {
                coordinate = holeStart + remainder;
                addHole(holeStart, remainder);
            } else {
                coordinate = holeStart;
                addHole(holeStart + length, remainder);
            }
        } else {
            coordinate = frontier_;
            const int shortage = length - tailLength;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
                boundaries_.resize(
                    static_cast<std::size_t>(trenchLength_) + 1
                );
            }
            frontier_ += length;
        }
        boundaries_[coordinate].starting =
            static_cast<std::uint8_t>(length);
        boundaries_[coordinate + length].ending =
            static_cast<std::uint8_t>(length);
        pipes_.push_back(Pipe{coordinate, length});
        std::cout << sections << ' ' << coordinate << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const std::size_t index = static_cast<std::size_t>(pid);
        const Pipe old = pipes_[index];
        boundaries_[old.start].starting = 0;
        boundaries_[old.start + old.length].ending = 0;
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