# System Instructions

You are an expert programming assistant generating actionable recommendations for future program mutations based on successful patterns and insights.

# Previous Messages

[]

# User Request

# Global Insights
## Успешные алгоритмические приёмы
- **Gen52 `conditional_merge_utility_edge` стал новым лидером: F/T = 0,858861454**, на +0,001435106 выше parent gen13 и на +0,000135572 выше прежнего лидера gen24. Успешное изменение сосредоточено в выборе края: полезность будущего слияния учитывает размеры спроса, которые остаток сможет вместить после удаления соседа, и относительный вес его освобождения. Край меняется при преимуществе более 25%.
- **Основной выигрыш gen52 связан с зависимостью lifetime от размера.** Относительно gen13 семейства `size_lifetimes` и `size_biased_deletion` прибавили соответственно +0,047953431 и +0,017705988; относительно gen24 — +0,013943237 и +0,015091249. Это продолжает прежний успешный паттерн: gen24 улучшал размещение через `releases/exposure`, а gen41 получил 0,858028, оценивая спрос, доступный после освобождения соседей.
- **Оценка потери вместимости остаётся полезной частью конкурентных решений.** Прежние gen24 и gen20 достигли 0,858725882 и 0,858350. Gen51 с взвешенной потерей вместимости и штрафом за остаток получил 0,857615 — второй результат среди gen48–55, хотя расширение поиска крупных интервалов добавило лишь около +0,000051 относительно gen6.
## Неэффективные подходы
- **Более глубокий прогноз вставок не обеспечил улучшения.** Gen49 с DP на четыре IID-запроса получил 0,850876912: −0,00694 относительно gen37 и примерно −0,007985 относительно gen52, особенно проигрывая в `short_heavy`, `fifo` и `tiny_churn`. Gen54 с двухшаговым прогнозом при равенстве оценок достиг 0,856982, потеряв 0,001306 относительно родителя. Вместе с прежними gen40/gen45 это показывает отсутствие устойчивого выигрыша от исследованных вариантов такого прогноза.
- **Усложнение моделей спроса и освобождений давало небольшие локальные прибавки.** Gen50 с марковским горизонтом 12 получил 0,855795; gen53 с совместной оценкой освобождения соседей — 0,855684; gen48 с veto риска расширения — около 0,8550; gen55 — 0,855164. Все уступили gen52. Особенно заметны потери в `tiny_churn`: перерасход достигал 47,4% у gen50, 35,3% у gen48 и 33,6% у gen55. Эти результаты продолжают тенденцию gen42–43, но не позволяют изолировать причину неудачи каждого компонента.
- **Новый механизм gen52 также имеет выраженные регрессии.** Относительно gen13 средний результат `fifo` снизился на 0,012716877. В `s31_022_fifo` потребовалось дополнительных 380 единиц траншеи относительно родителя и 340 относительно gen24. Выигрыш модели освобождений в сценариях с зависимостью lifetime от размера не переносится равномерно на FIFO.
## Особенности реализации
- **Gen52 сохраняет простой best-fit для выбора внутреннего интервала.** Прогноз сравнивает только найденную дыру и свободный хвост, когда оба вмещают текущий запрос. Ожидаемое число новых секций при следующей вставке вычисляется как `P(S > max(M, W)) + P(S > max(M, W + 20))`. Формула точна при `S ≤ 40` и отсутствии промежуточных удалений; последние прогноз не моделирует.
- **Прогноз спроса ограниченно влияет на решения.** Условные переходы сглаживаются общим распределением с весом prior `8`; коэффициенты затухания составляют `127/128` для общего профиля и `31/32` для обновляемой строки переходов. При разнице стоимости не более `1/64` сохраняется обычный best-fit. В отличие от gen49/gen50, здесь нет развёртывания последовательности будущих размещений.
- **Полезность слияния применяется только после подтверждения PID-сигнала:** `releaseBias² > 2 × releaseWeight`, при двух живых соседях и остатке меньше 40. Оценка использует `P(r < S ≤ min(40, r + neighborLength))`, умноженную на относительный вес освобождения соседа. Эти веса служат эвристикой, а не калиброванными вероятностями. Флаг `kMergeUtilityEdge = false` восстанавливает родительский механизм, связывая парное улучшение с этим изменением.
- **Разделение `frontier_` и `trenchLength_` сохраняет последствия раннего расширения.** Удаления объединяют интервалы и могут отодвинуть `frontier_` назад, однако длина траншеи не уменьшается. Поэтому локальное решение способно оставить постоянную прибавку к итоговому T; парные изменения на 20, 40, 60 и 340 согласуются с расширением секциями по 20.
## Анализ производительности
- **Преимущество gen52 над gen24 невелико и неоднородно:** 47 улучшений, 38 регрессий и 67 совпадений. Один случай `s31_031_size_lifetimes` даёт +0,090454545, то есть около +0,0005951 к среднему по 152 случаям — больше итогового преимущества +0,000135572. Значительная часть выигрыша погашается потерями на других входах; округлённый score `0,86` скрывает эти различия.
- **Лидерство достигнуто почти при прежней стоимости вычислений.** Gen52 использует максимум 0,97 с CPU и 7,03 MiB RSS против 0,96 с / 6,97 MiB у gen24. Gen50 требует 1,97 с / 15,08 MiB при более низком F/T. Gen51 экономнее — 0,90 с / 2,56 MiB, — но уступает gen52 примерно на 0,001246. Все варианты прошли проверки корректности.
- **Низкий F/T необходимо отделять от потерь размещения:** `F/T = (F/B) × (B/T)`. У перечисленных `micro_partial_drain` и `s31_121_short_rounding` значение `B/T = 1`, поэтому достигнут входной потолок. Реальный перерасход gen52 достигает 29,17% в `long_heavy`, 26,16% в `geometric_cohorts`, 26% в `drifting_sizes` и 25% в `tiny_churn`. Средний выигрыш не устранил эти потери.
- **Превосходство над fixed gen0 текущим отчётом не установлено.** Его средний F/T также указан как 0,858861454, при этом у gen52 зафиксированы 35 регрессий и максимальная потеря 0,049653143 на случае. Подтверждён новый максимум среди рассматриваемых эволюционных вариантов, но не доминирование над фиксированным baseline.

# Previous Recommendations (if any)
1. **Учитывайте полезность слияния при выборе края.** Сохраните `chooseHole()` из gen24, а для остатка `r < 40` вычисляйте `U(r,n) = Σ weights_[k]` по размерам `r < k ≤ min(40,r+n)`, где `n` — длина соседнего объекта. Сравнивайте `λL·U(r,nL)` и `λR·U(r,nR)` с прежним порогом 1,25, сохраняя исходное правило, когда обе полезности равны нулю: это переносит перспективную идею gen41 непосредственно в успешный механизм gen24.
2. **Добавьте затухание статистики освобождений.** Каждые 2048 команд сначала вызывайте `settleExposure()` для всех длин, затем умножайте накопленные освобождения и exposure, включая глобальные суммы, на 0,5; счётчики освобождений потребуется перевести в floating-point. Оставьте prior и порог переключения прежними: такая изолированная мутация проверит, помогает ли адаптация к смене режима в `distribution_switch` и `drifting_sizes`, сохраняя основу успешной оценки `releases/exposure`.
3. **Проверяйте два адреса для уже выбранного размера дыры.** При `0 < residual < 40` рассмотрите первый и последний адреса в соответствующем `bins_`: их текущий residual-fit score одинаков, но соседи могут иметь разную вероятность полезного освобождения. Используйте оценку слияния из пункта 1 и меняйте исходный адрес только при преимуществе более 25%; это ограниченно расширяет поиск по примеру gen41, сохраняя exact-fit и выбор размера gen24.
4. **Ускоряйте обновление профиля спроса при обнаруженной смене распределения.** Ведите histogram последних 64 вставок и каждые 16 вставок сравнивайте его нормированное распределение с накопленным через `0.5 × Σ|pRecent[k] − pLong[k]|`. При значении выше 0,25 пересчитывайте `weights_` из равной смеси этих распределений, сохраняя суммарный вес наблюдений и prior `+1`; иначе используйте исходный профиль. Это направлено на `drifting_sizes` и `distribution_switch` и сохраняет успешную формулу штрафа разбиения.
5. **Распространите exact-fit на свободный хвост без расширения траншеи.** При отсутствии точного совпадения среди дыр разрешите размещение в хвосте, если `trench_ − frontier_ == length`, даже когда существует подходящая внутренняя дыра. Следующим вариантом сравните любой вмещающий запрос хвост с выбранной дырой по той же формуле modular regret, разрешая хвост только при строго меньшем score: это развивает exact-fit лидера и учитывает уже оплаченную вместимость без многозапросного прогноза.

# Current Best Program
# Program to Analyze

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
NAME: Conditional Tail-Priced Best Fit + Conditional Merge Utility Edge
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
отрицательный — новых. При выраженном сигнале исходный выбор использует
порядок PID соседей. Для остатка r < 40 дополнительно оценивается доля
прогнозируемых размеров r < S <= min(40, r + длина соседа).
Эта полезность умножается на относительный вес освобождения соседа,
вычисленный из того же PID-сигнала. Преимущество более 25% меняет край;
при близких оценках, нулевой полезности или r >= 40 выбор исходный.
При недостаточном сигнале труба по-прежнему ставится слева.
Вставка: O(40 + log(H + 1) + log(L + 1)).
Удаление: амортизированно O(log(H + 1) + log(L + 1)).
Память: O(I + H + L + 40^2), где I — число вставок,
H — число отверстий, L — число живых труб.
Координаты помещаются в int: суммарно вставляется не более 8000000 метров.
Возможная неудача: смена распределения длин или порядка удалений,
а также зависимость lifetime от размера могут сделать прогноз неверным.
Ablation нового механизма: kMergeUtilityEdge = false восстанавливает
родительский Causal Release Edge с прежним выбором отверстия и хвоста.
*/
class Allocator {
    struct Pipe {
        int start;
        int length;
    };
    using FreeMap = std::map<int, int>;
    static constexpr bool kTailLookahead = true;
    static constexpr bool kReleaseEdge = true;
    static constexpr bool kMergeUtilityEdge = true;
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
    bool preferRightEdge(
        int holeStart, int remainder, int currentLength
    ) const {
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
        const bool parentChoice =
            (left->second < right->second) == (releaseBias_ > 0.0);
        if (!kMergeUtilityEdge || remainder >= 40) {
            return parentChoice;
        }
        const double aboveRemainder =
            forecastAbove(remainder, currentLength);
        const int leftLimit = std::min(
            40, remainder + pipes_[left->second].length
        );
        const int rightLimit = std::min(
            40, remainder + pipes_[right->second].length
        );
        const double leftUtility = std::max(
            0.0, aboveRemainder - forecastAbove(leftLimit, currentLength)
        );
        const double rightUtility = std::max(
            0.0, aboveRemainder - forecastAbove(rightLimit, currentLength)
        );
        if (leftUtility == 0.0 && rightUtility == 0.0) {
            return parentChoice;
        }
        const double mean =
            static_cast<double>(livePidSum_) /
            static_cast<double>(liveByStart_.size());
        const double scale = std::max(
            mean - static_cast<double>(oldestLivePid_),
            static_cast<double>(pipes_.size() - 1) - mean
        );
        const double direction = std::clamp(
            releaseBias_ / releaseWeight_, -1.0, 1.0
        );
        // Относительные веса, сохраняющие порядок родительского сигнала.
        const double leftWeight = std::max(
            0.0, 1.0 + direction *
                (mean - static_cast<double>(left->second)) / scale
        );
        const double rightWeight = std::max(
            0.0, 1.0 + direction *
                (mean - static_cast<double>(right->second)) / scale
        );
        const double leftScore = leftWeight * leftUtility;
        const double rightScore = rightWeight * rightUtility;
        if (leftScore > 1.25 * rightScore) {
            return true;
        }
        if (rightScore > 1.25 * leftScore) {
            return false;
        }
        return parentChoice;
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
                kReleaseEdge && remainder > 0 &&
                preferRightEdge(holeStart, remainder, length);
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
```

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.97; max_solver_rss_mib: 7.03

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.858861454049; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737975712
family=short_phase_churn mean_F/T=0.785915949
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803960374
family=geometric_cohorts mean_F/T=0.805335852
family=short_rounding mean_F/T=0.808221691
family=short_heavy mean_F/T=0.815928978
family=additive_cohorts mean_F/T=0.822933487
family=distribution_switch mean_F/T=0.824892062
family=long_heavy mean_F/T=0.832958575
family=tiny_churn mean_F/T=0.833601270
family=uniform_churn mean_F/T=0.835245846
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847772930
family=size_biased_deletion mean_F/T=0.847881351
family=serial_churn mean_F/T=0.868813188
family=fifo mean_F/T=0.872400718
family=large_live_set mean_F/T=0.880156087
family=micro_gap_refill mean_F/T=0.881250000
family=bimodal mean_F/T=0.882404172
family=recent_window_growth mean_F/T=0.882495644
family=hotset_switching mean_F/T=0.887276008
family=section_boundaries mean_F/T=0.888648274
family=size_lifetimes mean_F/T=0.891940569
family=soft_recency_growth mean_F/T=0.896141566
family=burst_drain mean_F/T=0.904727891
family=serial_growth mean_F/T=0.916939114
family=long_prefill_recent mean_F/T=0.917952203
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.921035761
family=drain_recovery mean_F/T=0.925865899
family=hotset_growth mean_F/T=0.950612845
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.956122617
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001474 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001350 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001434 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001410 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611715308 F/B=0.646045362 B/T=0.946861233 overrun=0.056121 cpu_s=0.084665 rss_mib=1.812
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618399624 F/B=0.675406191 B/T=0.915596618 overrun=0.092184 cpu_s=0.311110 rss_mib=1.984
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.320486 rss_mib=1.641
case=s31_060_large_live_set family=large_live_set F/T=0.631905345 F/B=0.641932619 B/T=0.984379554 overrun=0.015868 cpu_s=0.405559 rss_mib=2.922
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001390 rss_mib=1.344
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.016702 rss_mib=1.391
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001433 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002908 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012364 rss_mib=1.438
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002871 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.737903226 F/B=0.953125000 B/T=0.774193548 overrun=0.291667 cpu_s=0.360663 rss_mib=1.688
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.619815668 F/B=0.781976744 B/T=0.792626728 overrun=0.261628 cpu_s=0.320486 rss_mib=1.641
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.127704 rss_mib=1.719
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.329379 rss_mib=1.656
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002871 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.074107 rss_mib=1.438
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.036796 rss_mib=1.406
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001738 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002426 rss_mib=1.391
case=s31_086_tiny_churn family=tiny_churn F/T=0.818014706 F/B=0.959051724 B/T=0.852941176 overrun=0.172414 cpu_s=0.115722 rss_mib=1.516
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.520299 rss_mib=1.828
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.334334 rss_mib=1.672
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.122145 rss_mib=1.656
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.034265 rss_mib=1.406
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854284067 F/B=0.982097589 B/T=0.869856597 overrun=0.149615 cpu_s=0.155612 rss_mib=2.453
case=s31_017_section_boundaries family=section_boundaries F/T=0.835106383 F/B=0.957317073 B/T=0.872340426 overrun=0.146341 cpu_s=0.030239 rss_mib=1.406

PAIRED SEARCH EVIDENCE
Against parent gen13: delta mean F/T=+0.001435106; improved/regressed/tied=17/16/119.
family=size_lifetimes delta_F/T=+0.047953431
family=size_biased_deletion delta_F/T=+0.017705988
family=fifo delta_F/T=-0.012716877
family=tiny_churn delta_F/T=+0.004153709
family=hotset_switching delta_F/T=-0.002691095
family=serial_churn delta_F/T=+0.001397585
Regressions:
s31_022_fifo: delta_F/T=-0.057960564, delta_T=+380
s31_086_tiny_churn: delta_F/T=-0.024788324, delta_T=+80
s31_096_hotset_switching: delta_F/T=-0.021119375, delta_T=+240
s31_128_short_phase_churn: delta_F/T=-0.016776316, delta_T=+120
Gains:
s31_031_size_lifetimes: delta_F/T=+0.165833333, delta_T=-40
s31_063_size_biased_deletion: delta_F/T=+0.062943459, delta_T=-60
s31_085_tiny_churn: delta_F/T=+0.041403162, delta_T=-20
s31_029_size_lifetimes: delta_F/T=+0.025980392, delta_T=-120

Against leader gen24: delta mean F/T=+0.000135572; improved/regressed/tied=47/38/67.
family=size_biased_deletion delta_F/T=+0.015091249
family=size_lifetimes delta_F/T=+0.013943237
family=short_rounding delta_F/T=-0.010657895
family=distribution_switch delta_F/T=-0.008288471
family=serial_churn delta_F/T=+0.008131936
family=burst_drain delta_F/T=-0.006606290
Regressions:
s31_022_fifo: delta_F/T=-0.051499317, delta_T=+340
s31_122_short_rounding: delta_F/T=-0.042631579, delta_T=+20
s31_039_distribution_switch: delta_F/T=-0.024106961, delta_T=+40
s31_033_burst_drain: delta_F/T=-0.022564103, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.090454545, delta_T=-20
s31_103_serial_churn: delta_F/T=+0.043999453, delta_T=-60
s31_055_additive_cohorts: delta_F/T=+0.031938250, delta_T=-40
s31_024_fifo: delta_F/T=+0.030388889, delta_T=-60

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.858861454; mean positive loss on worst 16 cases=0.024506015; max case loss=0.049653143; regressed cases=35; worst family delta F/T=-0.020511308. These are selection diagnostics; primary fitness remains mean F/T.



# Instructions

Based on the global insights above and the current best program, generate 5 actionable recommendations for future program mutations. Each recommendation should be:

1. **Specific**: Clear about what to implement or try
2. **Actionable**: Something that can be directly applied
3. **Evidence-based**: Grounded in the successful patterns identified
4. **Diverse**: Cover different types of optimizations
5. **Best-program informed**: Consider what makes the current best program successful

Format as a numbered list:

1. [Specific recommendation based on successful patterns]
2. [Another recommendation focusing on a different aspect]
...

**CRITICAL: Prioritize recommendations that build upon or extend the successful patterns from the current best program. Consider both incremental improvements to the best program's approach and novel variations that could surpass it.**

Focus on the most promising approaches that have shown success in recent evaluations, especially those demonstrated by the best program. Avoid generic advice - provide 2-3 sentences per recommendation. DO NOT RECOMMEND CHANGING THE EVALUATION CODE. ONLY MAKE ALGORITHMIC RECOMMENDATIONS.
