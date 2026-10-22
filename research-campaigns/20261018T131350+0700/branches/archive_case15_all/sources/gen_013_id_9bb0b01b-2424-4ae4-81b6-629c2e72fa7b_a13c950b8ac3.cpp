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
NAME: Conditional Tail-Priced Best Fit + Causal Release Edge
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
Для выбранного внутреннего отверстия дополнительно выбирается край
размещения. Затухающий сигнал сравнивает PID удаляемых труб со средним
PID живых труб. Положительный сигнал соответствует удалению старых,
отрицательный — новых. При выраженном сигнале остаток оставляется
рядом с соседом, ожидаемым к удалению раньше; иначе труба ставится слева.
Вставка: O(40 + log(H + 1) + log(L + 1)).
Удаление: амортизированно O(log(H + 1) + log(L + 1)).
Память: O(I + H + L + 40^2), где I — число вставок,
H — число отверстий, L — число живых труб.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения длин или порядка удалений,
а также зависимость lifetime от размера могут сделать прогноз неверным.
Ablation нового механизма: kReleaseEdge = false восстанавливает
родительский Conditional Tail-Priced Best Fit.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    static constexpr bool kTailLookahead = true;
    static constexpr bool kReleaseEdge = true;
    static constexpr double kGlobalDecay = 127.0 / 128.0;
    static constexpr double kTransitionDecay = 31.0 / 32.0;
    static constexpr double kPriorWeight = 8.0;
    static constexpr double kDecisionMargin = 1.0 / 64.0;
    FreeMap holes_;
    std::set<std::pair<int, int>> bySize_;
    std::vector<Pipe> pipes_;
    std::map<int, int> liveByStart_;
    std::int64_t livePidSum_ = 0;
    std::size_t oldestLivePid_ = 1;
    double releaseBias_ = 0.0;
    double releaseWeight_ = 0.0;
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
    void observeRelease(std::size_t pid) {
        constexpr double decay = 15.0 / 16.0;
        releaseBias_ *= decay;
        releaseWeight_ *= decay;
        if (liveByStart_.size() < 2) {
            return;
        }
        const double mean =
            static_cast<double>(livePidSum_) /
            static_cast<double>(liveByStart_.size());
        // При двух и более живых PID масштаб не меньше 0.5.
        const double scale = std::max(
            mean - static_cast<double>(oldestLivePid_),
            static_cast<double>(pipes_.size() - 1) - mean
        );
        releaseBias_ += (mean - static_cast<double>(pid)) / scale;
        releaseWeight_ += 1.0;
    }
    bool preferRightEdge(int holeStart) const {
        // Порог накопленного сигнала, без предположения независимости.
        if (releaseBias_ * releaseBias_ <= 2.0 * releaseWeight_) {
            return false;
        }
        const auto right = liveByStart_.lower_bound(holeStart);
        if (right == liveByStart_.end() ||
            right == liveByStart_.begin()) {
            return false;
        }
        const auto left = std::prev(right);
        // Размещение справа оставляет остаток рядом с левым соседом.
        return (left->second < right->second) == (releaseBias_ > 0.0);
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
            const int remainder = holeLength - length;
            const bool fromRight =
                kReleaseEdge && remainder > 0 && preferRightEdge(holeStart);
            coordinate = fromRight ? holeStart + remainder : holeStart;
            eraseHole(holes_.find(holeStart));
            addHole(fromRight ? holeStart : holeStart + length, remainder);
        } else {
            coordinate = frontier_;
            const int shortage = length - tailLength;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ += length;
        }
        const int pid = static_cast<int>(pipes_.size());
        pipes_.push_back(Pipe{coordinate, length});
        liveByStart_.emplace(coordinate, pid);
        livePidSum_ += pid;
        std::cout << sections << ' ' << coordinate << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const std::size_t index = static_cast<std::size_t>(pid);
        const Pipe old = pipes_[index];
        observeRelease(index);
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
        liveByStart_.erase(old.start);
        livePidSum_ -= static_cast<std::int64_t>(index);
        pipes_[index].length = 0;
        while (oldestLivePid_ < pipes_.size() &&
               pipes_[oldestLivePid_].length == 0) {
            ++oldestLivePid_;
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