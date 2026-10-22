# System Instructions

You are an expert programming assistant analyzing specific program evaluation results to extract actionable optimization insights. Focus on concrete performance data and implementation details from the actual programs that were evaluated.

# Previous Messages

[]

# User Request

# Individual Program Summaries
**Program Name: Best-fit с адаптивным выбором по теневым раскладкам**
- **Implementation**: Свободные интервалы индексируются по координате и размеру, сливаются при освобождении; траншея растёт блоками по 20 только при отсутствии подходящего интервала. Две теневые раскладки сравнивают обычный best-fit с вариантом, учитывающим штраф за дробление, затухающую статистику запросов и дефицит интервалов; применяется политика с меньшей теневой траншеей, при равенстве сохраняется предыдущая.
- **Performance**: Пройдены все 152 теста из 38 семейств: средний F/T — 0,857908, средний перерасход — около 5%, максимальные CPU-время и память — 1,16 с и 10,89 MiB.
- **Feedback**: Средний F/T ниже parent gen20 на 0,000440 и leader gen52 на 0,000954, поэтому преимущество теневого переключения не подтверждено. Часть низких оценок микротестов достигает входного потолка при B/T=1, однако в drifting_sizes перерасход достигает 32%, указывая на сохраняющиеся потери размещения.
**Program Identifier:** Generation 56 - Patch Name shadow_trench_duel - Correct Program: True

**Program Name: Размещение по остаточной вместимости с адаптацией спроса**
- **Implementation**: Аллокатор объединяет соседние свободные интервалы и минимизирует взвешенную потерю вместимости, проверяя все доступные размеры <80 и до восьми различных больших размеров; затем использует хвост, расширяя пространство блоками по 20. Каждые 16 вставок детектор проверяет TV>¼ между историей и последними 64 запросами и при срабатывании использует их равную смесь со сглаживанием +1.
- **Performance**: Средний F/T — 0,857358 на 152 тестах из 38 семейств; средний overrun — 5%, максимальные CPU и RSS — 0,92 с и 2,53 MiB; все проверки корректности пройдены.
- **Feedback**: Адаптация улучшила отдельные сценарии, особенно `burst_drain`, но средний F/T оказался ниже родителя на 0,000258 и лидера на 0,001504, поэтому общего преимущества не показала. Низкие абсолютные результаты не всегда означают потери аллокатора: несколько худших тестов имеют B/T=1 и уже достигают входного потолка F/B.
**Program Identifier:** Generation 57 - Patch Name shift_triggered_demand_blend - Correct Program: True

**Program Name: Адаптивный аллокатор с прогнозом освобождения интервалов**
- **Implementation**: Свободные интервалы объединяются при удалении и индексируются по размеру, возрасту и группам соседей; при равных оценках предпочтение отдаётся меньшему, затем старейшему интервалу. Эвристический прогноз удалений по длине и циклическим фазам вместе с DP-оценкой остаточной вместимости определяет интервал и край размещения; расширение секциями по 20 выполняется только при отсутствии подходящего места.
- **Performance**: Средний F/T — 0,855002 (score 0,86), пройдены все 152 теста из 38 семейств; средний перерасход — около 5%, максимальные CPU и RSS — 1,65 с и 7,97 MiB.
- **Feedback**: Результат практически совпадает с родителем (+0,000021 F/T), но уступает gen52 на 0,003859, особенно в tiny_churn и fifo. Низкий результат micro_partial_drain объясняется входным потолком при B/T=1, тогда как перерасход до 33,6% в tiny_churn показывает сохраняющиеся потери от фрагментации.
**Program Identifier:** Generation 58 - Patch Name paid_gap_local_fronts - Correct Program: True

**Program Name: Best-fit с условным прогнозом и сохранением ёмкости**
- **Implementation**: Свободные интервалы индексируются по адресу и размеру, объединяются при удалении; траншея расширяется блоками по 20. Валидируемый условный прогноз по истории 512 вставок сравнивает best-fit со следующим большим доступным размером: при остатках <40 замена требует снижения нормированной потери ёмкости более чем на 1/64 без увеличения ожидаемого расширения; дополнительно учитываются свободный хвост и выбор края размещения.
- **Performance**: Средний F/T — 0,857001 на 152 успешно проверенных тестах из 38 семейств без stress; максимальные CPU и RSS — 0,97 с и 6,98 МиБ.
- **Feedback**: Средний F/T ниже gen39 на 0,000763 и gen52 на 0,001861: выигрыш на fifo сопровождается заметными регрессиями на size_lifetimes, поэтому общее улучшение не подтверждено. На части худших микротестов B/T=1, и низкий F/T объясняется входным потолком F/B, а не потерями аллокатора.
**Program Identifier:** Generation 59 - Patch Name conditional_two_size_capacity - Correct Program: True

**Program Name: Адаптивный best-fit с DP и контролем фрагментации**
- **Implementation**: Свободные интервалы индексируются по адресу и размеру, соседние объединяются, траншея расширяется блоками по 20. Выбор best-fit уточняется DP с горизонтом четыре запроса и адаптивной статистикой размеров, ограничениями дефицита интервалов и capacity dominance; сторона размещения учитывает ожидаемое освобождение соседей.
- **Performance**: Средний F/T составил 0,854188 на 152 тестах из 38 семейств, все проверки пройдены; максимальные CPU/RSS — 1,08 с / 9,98 MiB.
- **Feedback**: Средний F/T выше gen49 на 0,003311, но ниже gen52 на 0,004673, с наиболее заметным отставанием в short_heavy и tiny_churn. Низкие оценки при B/T=1 уже достигают входного потолка F/B, тогда как отдельный short_heavy показывает существенный перерасход траншеи относительно B — 53,3%.
**Program Identifier:** Generation 60 - Patch Name repeated_capacity_dominance - Correct Program: True

**Program Name: Best-Fit с адаптивным прогнозом упаковки**
- **Implementation**: Аллокатор хранит свободные интервалы в упорядоченных индексах, объединяет соседние промежутки и расширяет траншею блоками по 20 только при отсутствии подходящего места. Best-Fit корректируется затухающей статистикой запросов и освобождений, а также восемью детерминированными сценариями по три будущие вставки, моделируемыми через битовый профиль ёмкости до 120.
- **Performance**: Средний F/T — 0,859561; пройдены все 152 проверки из 38 семейств, максимальные CPU time и RSS составили 1,06 с и 9,98 МиБ.
- **Feedback**: Парные сравнения показывают небольшой средний выигрыш относительно gen37 (+0,001748) и gen52 (+0,000700), однако сохраняются регрессии, включая drifting_sizes относительно gen37 и size_biased_deletion относительно gen52. Часть низких F/T объясняется входным потолком F/B: в нескольких худших случаях B/T=1, поэтому дополнительного перерасхода траншеи нет.
**Program Identifier:** Generation 61 - Patch Name stratified_growth_horizon - Correct Program: True

**Program Name: Best-fit с Monte Carlo и прогнозом освобождений**
- **Implementation**: Свободные интервалы индексируются по координате и размеру, объединяются при удалении; расширение секциями по 20 разрешено только при отсутствии подходящего интервала. До 12 кандидатов оцениваются по четырём сценариям из восьми будущих запросов с распределением длин из окон 128/2048; край размещения выбирается по оценкам интенсивности освобождения соседей.
- **Performance**: Пройдены все 152 теста в 38 семействах, средний F/T — 0,85735, средний overrun — 0,05, максимальные CPU и RSS — 1,14 с и 9,41 MiB.
- **Feedback**: Средний F/T выше gen45 на 0,001415, но ниже gen52 на 0,001511; улучшения сопровождаются регрессиями, особенно в size_biased_deletion. Часть низких F/T достигает входного потолка F/B при B/T=1, тогда как отдельные случаи long_heavy и drifting_sizes показывают избыточную длину траншеи примерно на 26–27%.
**Program Identifier:** Generation 62 - Patch Name exposure_normalized_edge - Correct Program: True

**Program Name: Адаптивный аллокатор с прогнозом удаления и слиянием дыр**
- **Implementation**: Свободные интервалы индексируются по размеру, возрасту и классу соседей, объединяются при освобождении; отдельный хвост расширяется секциями по 20 единиц. Ограниченный поиск сравнивает размещение у обоих краёв дыры по DP-потенциалу остатка и эвристическому прогнозу удаления, учитывающему длины, фазы и окна наблюдений 128/2048; при равных оценках предпочтение отдаётся меньшим, затем более старым дырам.
- **Performance**: Все 152 проверки в 38 семействах пройдены; средний F/T — 0,854469, худшее семейство — 0,533333, максимальные CPU time и RSS — 1,56 с и 8,03 MiB.
- **Feedback**: Средний F/T ниже gen0 на 0,000512 и gen61 на 0,005092: отдельные улучшения сопровождаются регрессиями, особенно при смене распределения и дрейфе размеров относительно gen0. Низкие результаты некоторых микросценариев уже достигают входного потолка при B/T=1, тогда как превышение T над B до 40% в drifting_sizes указывает на существенный резерв улучшения размещения.
**Program Identifier:** Generation 63 - Patch Name appendable_wilderness_single_front - Correct Program: True

# Previous Global Insights (if any)
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
#include <bit>
namespace {
using Coordinate = std::int64_t;
class Allocator {
    static constexpr bool packingEnabled_ = true;
    static constexpr int packingCap_ = 120;
    static constexpr int scenarioCount_ = 8;
    struct Pipe {
        Coordinate start;
        int length;
    };
    struct Placement {
        Coordinate at = -1;
        bool rightAligned = false;
    };
    // A simulated horizon consumes at most 120 units. Larger gaps can
    // therefore share one bucket after the current placement is applied.
    struct PackingProfile {
        std::array<std::uint32_t, packingCap_ + 1> count{};
        std::array<std::uint64_t, 2> nonempty{};
        static int bucket(Coordinate length) {
            return static_cast<int>(
                std::min<Coordinate>(packingCap_, length));
        }
        void add(Coordinate length) {
            if (length <= 0) return;
            const int k = bucket(length);
            ++count[k];
            nonempty[(k - 1) / 64] |=
                std::uint64_t{1} << ((k - 1) % 64);
        }
        void take(Coordinate length) {
            if (length <= 0) return;
            const int k = bucket(length);
            if (--count[k] == 0) {
                nonempty[(k - 1) / 64] &=
                    ~(std::uint64_t{1} << ((k - 1) % 64));
            }
        }
        int firstFit(int length) const {
            if (length <= 0 || length > packingCap_) return 0;
            int word = (length - 1) / 64;
            std::uint64_t bits = nonempty[word] &
                (~std::uint64_t{0} << ((length - 1) % 64));
            if (bits == 0 && word == 0) {
                word = 1;
                bits = nonempty[1];
            }
            if (bits == 0) return 0;
            return word * 64 +
                static_cast<int>(std::countr_zero(bits)) + 1;
        }
    };
    struct Scenario {
        std::array<int, 3> lengths{};
        int volume = 0;
    };
    using Scenarios = std::array<Scenario, scenarioCount_>;
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    PackingProfile packingProfile_;
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
        const double pooledRate =
            totalDeaths_ / (totalExposure_ + 1.0);
        return (deaths_[length] + 8.0 * pooledRate) /
               (exposure + 8.0);
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
            if (demand_[k] != 0 && space % k < length % k) {
                result +=
                    static_cast<std::uint64_t>(demand_[k]) * k;
            }
        }
        return result;
    }
    bool scarcityAllowsExchange(
        Coordinate smaller, Coordinate larger, int length) const {
        std::size_t fittingGaps = 0;
        long double extraLoss = 0;
        for (int k = 40; k >= 1; --k) {
            fittingGaps += starts_[k].size();
            if (demand_[k] == 0 || fittingGaps == 0) continue;
            const int smallerLoses =
                smaller >= k && smaller - length < k;
            const int largerLoses =
                larger >= k && larger - length < k;
            if (smallerLoses != largerLoses) {
                extraLoss +=
                    static_cast<long double>(demand_[k]) /
                    static_cast<long double>(fittingGaps) *
                    (largerLoses - smallerLoses);
            }
        }
        return extraLoss <= 0;
    }
    double releaseGain(
        Coordinate a, Coordinate remainder, bool rightAligned,
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
                if (outside->second == p.start) {
                    releasedSpace +=
                        outside->second - outside->first;
                }
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end()) {
                releasedSpace += outside->second - outside->first;
            }
        }
        const int before = static_cast<int>(
            std::min<Coordinate>(
                40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(
            std::min<Coordinate>(40, remainder + releasedSpace));
        if (before == after) return 0;
        return releaseRate(p.length) *
            static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(
        int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        }
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
                const double score =
                    releaseGain(a, remainder, side != 0, prefix);
                if (score > best) {
                    best = score;
                    at = a;
                    rightAligned = side != 0;
                }
            }
        }
    }
    Scenarios buildScenarios() const {
        // One uniform pseudo-observation per possible request length.
        const std::uint32_t mass = demandMass_ + 40;
        std::array<int, scenarioCount_> quantiles{};
        int length = 1;
        std::uint32_t cumulative = demand_[1] + 1;
        for (int i = 0; i < scenarioCount_; ++i) {
            const std::uint32_t target =
                static_cast<std::uint32_t>(
                    (static_cast<std::uint64_t>(2 * i + 1) * mass) /
                    (2 * scenarioCount_));
            while (length < 40 && cumulative <= target) {
                ++length;
                cumulative += demand_[length] + 1;
            }
            quantiles[i] = length;
        }
        // Each horizon position uses every marginal stratum once.
        Scenarios scenarios{};
        for (int i = 0; i < scenarioCount_; ++i) {
            scenarios[i].lengths = {
                quantiles[i],
                quantiles[(3 * i + 1) % scenarioCount_],
                quantiles[(5 * i + 2) % scenarioCount_]
            };
            for (int request : scenarios[i].lengths) {
                scenarios[i].volume += request;
            }
        }
        return scenarios;
    }
    int projectedGrowth(
        const Placement& placement, int length,
        const PackingProfile& interior,
        Coordinate tailStart, Coordinate tailSpace,
        const Scenarios& scenarios, int cutoff) const {
        PackingProfile after = interior;
        Coordinate remainingTail = tailSpace;
        if (placement.at == tailStart) {
            remainingTail -= length;
        } else {
            const Coordinate space =
                gaps_.at(placement.at) - placement.at;
            after.take(space);
            after.add(space - length);
        }
        const int initialTail = static_cast<int>(
            std::min<Coordinate>(packingCap_, remainingTail));
        int totalGrowth = 0;
        for (const Scenario& scenario : scenarios) {
            // One gap holding the entire remaining volume guarantees
            // zero growth under insertion-only Best-Fit.
            if (initialTail >= scenario.volume ||
                after.firstFit(scenario.volume) != 0) {
                continue;
            }
            PackingProfile simulated = after;
            int tail = initialTail;
            for (int request : scenario.lengths) {
                const int fit = simulated.firstFit(request);
                // The physical tail has the largest address, so an
                // equal-sized interior fit wins the Best-Fit tie.
                if (fit != 0 &&
                    (tail < request || fit <= tail)) {
                    simulated.take(fit);
                    simulated.add(fit - request);
                } else if (tail >= request) {
                    tail -= request;
                } else {
                    const int sections =
                        (request - tail + 19) / 20;
                    totalGrowth += sections;
                    tail += sections * 20 - request;
                }
            }
            // All remaining contributions are nonnegative.
            if (totalGrowth >= cutoff) return totalGrowth;
        }
        return totalGrowth;
    }
    Placement choosePlacement(int length) const {
        const auto first = sizes_.lower_bound({length, 0});
        if (first == sizes_.end()) return {};
        const auto nextSize = sizes_.upper_bound(
            {first->first, std::numeric_limits<Coordinate>::max()});
        auto candidate = first;
        // Preserve the parent's complete decision as the fallback.
        if (candidate->first > length) {
            const auto penalty =
                splitPenalty(candidate->first, length);
            if (penalty != 0 && nextSize != sizes_.end() &&
                splitPenalty(nextSize->first, length) < penalty &&
                scarcityAllowsExchange(
                    candidate->first, nextSize->first, length)) {
                candidate = nextSize;
            }
        }
        Placement fallback{candidate->second, false};
        selectReleasePlacement(
            length, fallback.at, fallback.rightAligned);
        if constexpr (!packingEnabled_) {
            return fallback;
        }
        if (first->first == length) return fallback;
        // In either condition every candidate leaves enough guaranteed
        // capacity for three requests of maximum length.
        if (starts_[40].size() >= 4 ||
            sizes_.rbegin()->first >= length + packingCap_) {
            return fallback;
        }
        Coordinate tailStart = -1;
        Coordinate tailSpace = 0;
        if (!gaps_.empty() &&
            gaps_.rbegin()->second == trench_) {
            tailStart = gaps_.rbegin()->first;
            tailSpace = trench_ - tailStart;
        }
        // The fallback belongs to one of the first two size classes.
        // Four slots simplify collection; at most three are distinct.
        std::array<Placement, 4> choices{};
        int choiceCount = 1;
        choices[0] = fallback;
        auto append = [&](Coordinate start) {
            Placement proposed{start, false};
            selectReleasePlacement(
                length, proposed.at, proposed.rightAligned);
            for (int i = 0; i < choiceCount; ++i) {
                if (choices[i].at == proposed.at) return;
            }
            choices[choiceCount++] = proposed;
        };
        append(first->second);
        if (nextSize != sizes_.end()) append(nextSize->second);
        if (tailSpace >= length) append(tailStart);
        if (choiceCount == 1) return fallback;
        PackingProfile interior = packingProfile_;
        interior.take(tailSpace);
        const Scenarios scenarios = buildScenarios();
        int bestIndex = 0;
        int bestScore = projectedGrowth(
            choices[0], length, interior, tailStart, tailSpace,
            scenarios, std::numeric_limits<int>::max());
        for (int i = 1; i < choiceCount && bestScore != 0; ++i) {
            const int score = projectedGrowth(
                choices[i], length, interior, tailStart, tailSpace,
                scenarios, bestScore);
            if (score < bestScore) {
                bestScore = score;
                bestIndex = i;
            }
        }
        return choices[bestIndex];
    }
    static int bucket(Coordinate n) {
        return static_cast<int>(std::min<Coordinate>(40, n));
    }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b - a, a});
        starts_[bucket(b - a)].insert(a);
        packingProfile_.add(b - a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b - a, a});
        starts_[bucket(b - a)].erase(a);
        packingProfile_.take(b - a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        advanceReleaseClock();
        observeLength(length);
        const Placement placement = choosePlacement(length);
        Coordinate at = placement.at;
        Coordinate digs = 0;
        // Growth is allowed only after the global fitting-gap search
        // has established that no existing interval can hold the pipe.
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() &&
                gaps_.rbegin()->second == trench_) {
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
        if (placement.rightAligned) at = finish - length;
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
        Coordinate a = p.start;
        Coordinate b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 1.06; max_solver_rss_mib: 9.98

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.859561466483; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737963871
family=short_phase_churn mean_F/T=0.781231752
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.802662964
family=short_rounding mean_F/T=0.808221691
family=geometric_cohorts mean_F/T=0.808527948
family=short_heavy mean_F/T=0.821278547
family=additive_cohorts mean_F/T=0.826891209
family=size_biased_deletion mean_F/T=0.831375197
family=distribution_switch mean_F/T=0.834484073
family=tiny_churn mean_F/T=0.835116112
family=uniform_churn mean_F/T=0.836919475
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847093254
family=long_heavy mean_F/T=0.849756128
family=fifo mean_F/T=0.864512668
family=serial_churn mean_F/T=0.867743936
family=size_lifetimes mean_F/T=0.876761532
family=large_live_set mean_F/T=0.878380217
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882848124
family=hotset_switching mean_F/T=0.892047313
family=soft_recency_growth mean_F/T=0.896392595
family=bimodal mean_F/T=0.896634947
family=section_boundaries mean_F/T=0.901461482
family=burst_drain mean_F/T=0.907481748
family=serial_growth mean_F/T=0.917407304
family=long_prefill_recent mean_F/T=0.917872355
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920999287
family=drain_recovery mean_F/T=0.924758483
family=hotset_growth mean_F/T=0.950641471
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955291422
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001512 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001432 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001426 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001446 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001456 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001398 rss_mib=1.312
case=s31_118_partial_drain family=partial_drain F/T=0.611210454 F/B=0.646045362 B/T=0.946079780 overrun=0.056993 cpu_s=0.090102 rss_mib=2.156
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.620927673 F/B=0.675406191 B/T=0.919339623 overrun=0.087737 cpu_s=0.343123 rss_mib=3.312
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.344370 rss_mib=2.938
case=s31_060_large_live_set family=large_live_set F/T=0.632458290 F/B=0.641932619 B/T=0.985240929 overrun=0.014980 cpu_s=0.447067 rss_mib=4.359
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001460 rss_mib=1.328
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001405 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003143 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013349 rss_mib=1.484
case=s31_040_distribution_switch family=distribution_switch F/T=0.666898148 F/B=0.692548077 B/T=0.962962963 overrun=0.038462 cpu_s=0.018197 rss_mib=1.406
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003007 rss_mib=1.359
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.353512 rss_mib=2.938
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.753663872 F/B=0.950045956 B/T=0.793292016 overrun=0.260570 cpu_s=0.138815 rss_mib=2.172
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003007 rss_mib=1.359
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.078591 rss_mib=1.641
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.344370 rss_mib=2.938
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.379089 rss_mib=2.984
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001699 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002357 rss_mib=1.359
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.060392 rss_mib=1.484
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.117015 rss_mib=1.859
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821455616 F/B=0.950170316 B/T=0.864535128 overrun=0.156691 cpu_s=0.135745 rss_mib=2.000
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.348536 rss_mib=2.969
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.852931866 F/B=0.982097589 B/T=0.868479747 overrun=0.151437 cpu_s=0.171293 rss_mib=3.344
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.835978836 F/B=0.954682779 B/T=0.875661376 overrun=0.141994 cpu_s=0.037223 rss_mib=1.500
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.677577741 F/B=0.768089054 B/T=0.882160393 overrun=0.133581 cpu_s=0.021092 rss_mib=1.438
case=s31_061_size_biased_deletion family=size_biased_deletion F/T=0.841041667 F/B=0.950054308 B/T=0.885256410 overrun=0.129616 cpu_s=0.766433 rss_mib=4.672

PAIRED SEARCH EVIDENCE
Against parent gen37: delta mean F/T=+0.001747828; improved/regressed/tied=42/27/83.
family=size_lifetimes delta_F/T=+0.028683798
family=burst_drain delta_F/T=+0.021145768
family=section_boundaries delta_F/T=+0.011538194
family=hotset_switching delta_F/T=+0.009689671
family=drifting_sizes delta_F/T=-0.009487948
family=additive_cohorts delta_F/T=+0.007245488
Regressions:
s31_041_drifting_sizes: delta_F/T=-0.036501025, delta_T=+60
s31_039_distribution_switch: delta_F/T=-0.024810924, delta_T=+40
s31_049_geometric_cohorts: delta_F/T=-0.021262458, delta_T=+20
s31_024_fifo: delta_F/T=-0.019981735, delta_T=+40
Gains:
s31_033_burst_drain: delta_F/T=+0.083959451, delta_T=-80
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.057446809, delta_T=-60
s31_017_section_boundaries: delta_F/T=+0.035552536, delta_T=-40

Against leader gen52: delta mean F/T=+0.000700012; improved/regressed/tied=44/39/69.
family=long_heavy delta_F/T=+0.016797553
family=size_biased_deletion delta_F/T=-0.016506154
family=size_lifetimes delta_F/T=-0.015179037
family=bimodal delta_F/T=+0.014230775
family=section_boundaries delta_F/T=+0.012813208
family=distribution_switch delta_F/T=+0.009592012
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.090454545, delta_T=+20
s31_063_size_biased_deletion: delta_F/T=-0.062943459, delta_T=+60
s31_024_fifo: delta_F/T=-0.030388889, delta_T=+60
s31_103_serial_churn: delta_F/T=-0.029813837, delta_T=+40
Gains:
s31_009_long_heavy: delta_F/T=+0.050889878, delta_T=-80
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_030_size_lifetimes: delta_F/T=+0.039130435, delta_T=-40
s31_022_fifo: delta_F/T=+0.035732110, delta_T=-240

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.859561466; mean positive loss on worst 16 cases=0.016110133; max case loss=0.042631579; regressed cases=31; worst family delta F/T=-0.013784408. These are selection diagnostics; primary fitness remains mean F/T.



# Instructions

Analyze the SPECIFIC program evaluation results above to extract concrete optimization insights. Look at the actual performance scores, implementation details, and evaluation feedback to identify patterns. Reference specific programs and their results.
Make sure to incorporate the previous insights into the new insights.

**CRITICAL: Pay special attention to the current best program and how it compares to other evaluated programs. Ensure the best program's successful patterns are prominently featured in your analysis.**

Update or create insights in these sections:

## Successful Algorithmic Patterns
- Identify specific implementation changes that led to score improvements
- Reference which programs achieved these improvements and their scores
- **Highlight patterns from the current best program**
- Note the specific techniques or approaches that worked (2-4 bullet points)

## Ineffective Approaches
- Identify specific implementation changes that worsened performance
- Reference which programs had these issues and how scores were affected
- Note why these approaches failed based on evaluation feedback (2-4 bullet points)

## Implementation Insights
- Extract specific coding patterns/techniques from the evaluated programs
- **Analyze what makes the current best program effective**
- Connect implementation details to their performance impact
- Reference concrete examples from the program summaries (2-4 bullet points)

## Performance Analysis
- Analyze actual score changes and trends from the evaluated programs
- **Compare other programs' performance against the current best**
- Compare performance between different implementation approaches
- Identify score patterns and correlations (2-4 bullet points)

CRITICAL: Base insights on the ACTUAL individual program summaries, previous insights, and the current best program information. Reference specific program names, scores, and implementation details. Build upon previous insights with concrete evidence from the new evaluations. IMPORTANT: Make sure that the best results are not ignored and are prominently featured in your analysis. Do not make recommendations for the next steps. ONLY PERFORM THE ANALYSIS.
