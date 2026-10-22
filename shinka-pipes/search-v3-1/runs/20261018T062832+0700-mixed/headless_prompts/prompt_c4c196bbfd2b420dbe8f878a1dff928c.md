# System Instructions

You are an expert programming assistant analyzing specific program evaluation results to extract actionable optimization insights. Focus on concrete performance data and implementation details from the actual programs that were evaluated.

# Previous Messages

[]

# User Request

# Individual Program Summaries
**Program Name: Conditional Tail-Priced Best Fit**
- **Implementation**: Свободные интервалы индексируются через `map` по координате и `set` по размеру, объединяются при удалении; хвост хранится отдельно, расширение выполняется минимально секциями по 20. Выбор между best fit и хвостом уточняется прогнозом расширения на следующей вставке: условные переходы длин сглаживаются общим распределением с экспоненциальным забыванием, а близкие оценки сохраняют best fit.
- **Performance**: Программа прошла все 152 проверки в 38 семействах, получив средний F/T=0,857536 (score 0,86), при максимальных CPU 0,94 с и RSS 2,61 MiB.
- **Feedback**: Парное сравнение с parent gen0 показывает небольшой прирост среднего F/T на 0,002555: 50 улучшений против 38 регрессий, с наибольшим выигрышем среди семейств у `fifo` и ухудшением у `distribution_switch`. Прогноз игнорирует будущие удаления и дальнейшую фрагментацию; при этом низкие F/T в случаях с B/T=1 уже достигают входного потолка F/B и не свидетельствуют о потерях аллокатора.
**Program Identifier:** Generation 5 - Patch Name Independent 2 - Correct Program: True

**Program Name: Best-fit с прогнозом роста хвоста**
- **Implementation**: Интервалы хранятся в двусвязном списке на индексах, свободные блоки — в `std::set`; применяются best-fit, объединение соседей и расширение секциями по 20 м. Затухающая история длин корректирует выбор между хвостом и внутренним интервалом, а сглаженная частота удалений определяет сторону размещения; сложность команды — O(40 + log(H+1)).
- **Performance**: Пройдены все 152 теста из 38 семейств; среднее F/T — 0,857525, максимальные CPU и RSS — 0,89 с и 3,81 MiB.
- **Feedback**: Прирост относительно gen4 небольшой: +0,000736 среднего F/T при 29 улучшениях, 29 ухудшениях и 94 совпадениях; выигрывает geometric_cohorts, проигрывает uniform_churn. Низкие результаты micro_partial_drain соответствуют входному потолку при B/T=1, тогда как на drifting_sizes наблюдается реальный перерасход длины до 26,8%.
**Program Identifier:** Generation 12 - Patch Name tail_growth_regret - Correct Program: True

**Program Name: Best-fit с прогнозом расширения и выбором края**
- **Implementation**: Выбор между best-fit дырой и суффиксом использует прогноз следующего insert по окну 512 вставок с единичным prior для длин 1–40; край размещения выбирается по ожидаемой выгоде слияния при удалении соседей. Интервалы индексируются по адресу и размеру, объединяются при удалении; расширение блоками по 20 выполняется только при отсутствии места, сложность вставки — O(log Q + 40).
- **Performance**: Средний F/T — 0.858287 на 152 тестах из 38 семейств, худшее семейство — 0.533333; максимальные CPU и RSS — 0.97 с и 6.98 MiB.
- **Feedback**: Относительно gen7 средний F/T вырос на 0.001732: 45 улучшений, 35 регрессий и 72 равенства; наибольший выигрыш среди приведённых семейств получил size_biased_deletion, заметное ухудшение — section_boundaries. Низкие результаты micro_partial_drain уже достигают входного потолка F/B, тогда как drifting_sizes показывает реальные потери: перерасход длины траншеи достигает 28%.
**Program Identifier:** Generation 15 - Patch Name adjacent_release_edge - Correct Program: True

**Program Name: Аллокатор с приоритетом точного размера и внутренних промежутков**
- **Implementation**: Свободные интервалы индексируются по координате, длине и корзинам размеров с объединением длин ≥40; размещение предпочитает точное совпадение, затем самый левый подходящий внутренний промежуток, затем хвост. Траншея расширяется блоками по 20 с использованием свободного хвоста, а удаление по ID объединяет соседние свободные интервалы.
- **Performance**: Средний F/T — 0,855647, итоговая оценка — 0,86; пройдены все 152 теста из 38 семейств, максимальные CPU и RSS составили 0,97 с и 5,58 MiB.
- **Feedback**: Прирост относительно gen10 небольшой: +0,001483 среднего F/T, 35 улучшений против 24 ухудшений; наиболее заметно выиграли drifting_sizes и short_phase_churn. Худшее семейство micro_partial_drain получило 0,533, однако в приведённых случаях B/T=1: низкий результат обусловлен входным потолком F/B, а не избыточным расширением траншеи.
**Program Identifier:** Generation 19 - Patch Name wilderness_last_fit - Correct Program: True

**Program Name: Best-fit с адаптацией к спросу**
- **Implementation**: Свободные интервалы индексируются через map/set и объединяются при освобождении; траншея расширяется блоками по 20. Затухающий профиль запросов длиной 1–40 позволяет заменить best-fit следующим большим размером интервала, если снижается штраф дробления и проходит проверка дефицита подходящих промежутков.
- **Performance**: Средний F/T — 0,85835 на 152 корректно пройденных случаях из 38 семейств; максимальные CPU time и RSS — 0,97 с и 5,62 MiB.
- **Feedback**: Прирост среднего F/T небольшой: +0,00159 относительно gen11 и +0,00102 относительно gen3, с отдельными регрессиями, включая bimodal и tiny_churn. В худших случаях micro_partial_drain значение B/T=1 означает отсутствие перерасхода относительно границы B: низкий F/T соответствует входному потолку F/B.
**Program Identifier:** Generation 20 - Patch Name scarcity_fit_guard - Correct Program: True

**Program Name: Аллокатор с подбором остатков и прогнозом освобождения**
- **Implementation**: Свободные участки объединяются при освобождении и выбираются через размерные bins и битовые маски по штрафу фрагментации, учитывающему затухающую статистику размеров запросов. Во внутреннем зазоре размещение переключается на правый край, если сглаженная частота освобождения левого соседа, оценённая через releases/exposure, превышает частоту правого более чем в 1,25 раза.
- **Performance**: Пройдены все 152 теста из 38 семейств; средний F/T — 0,858726, максимальное процессорное время — 0,96 с, максимальный RSS — 6,97 MiB.
- **Feedback**: Прирост относительно gen6 небольшой: +0,001162 среднего F/T, при 39 улучшениях и 37 ухудшениях; size_lifetimes выигрывает +0,0328, тогда как long_heavy и short_heavy теряют около 0,0125 каждый. Низкие результаты случаев с B/T=1 уже соответствуют входному потолку F/B и не свидетельствуют о потерях аллокатора.
**Program Identifier:** Generation 24 - Patch Name exposure_guided_split - Correct Program: True

**Program Name: Адаптивный аллокатор с прогнозированием освобождений и расширения**
- **Implementation**: Свободные интервалы хранятся в индексах `map/set`, объединяются при удалении труб; ограниченный поиск кандидатов учитывает размер, соседей и возраст промежутка. Размещение использует сглаженные оценки удаления по длине и циклической позиции, окна запросов 128/2048, DP-оценку полезности остатка и прогноз следующего расширения по переходам размеров; траншея увеличивается минимально необходимыми секциями по 20.
- **Performance**: Средний F/T — 0.855416; пройдены все 152 теста из 38 семейств, среднее превышение нижней границы — около 5%, максимальные CPU и RSS — 1.63 с и 7.97 MiB.
- **Feedback**: Улучшение относительно gen17 небольшое: +0.000281 среднего F/T при 17 улучшениях и 23 регрессиях; заметные потери сохраняются на `drifting_sizes` и `size_biased_deletion`. Низкие результаты приведённых `micro_partial_drain` совпадают с входным потолком F/B при B/T=1, поэтому сами по себе не свидетельствуют о потерях аллокатора.
**Program Identifier:** Generation 25 - Patch Name transition_conditioned_excavation - Correct Program: True

**Program Name: Адаптивный аллокатор с гармонической оценкой свободных интервалов**
- **Implementation**: Аллокатор поддерживает индексы свободных интервалов, сливает соседние промежутки при удалении и расширяет траншею секциями по 20 только при отсутствии подходящего места. Ограниченный набор кандидатов оценивается по прогнозу освобождения с учётом длины, фазы и возраста объектов, будущему слиянию и гармонической стоимости потери ёмкости для повторных запросов.
- **Performance**: Пройдены все 152 проверки из 38 семейств; средний F/T=0.856354820 без stress, средний перерасход относительно B — 5%, максимальные CPU и RSS — 1.90 с и 15.02 MiB.
- **Feedback**: Выигрыш относительно gen8 небольшой: +0.000627576 среднего F/T при 39 улучшениях, 36 ухудшениях и 77 совпадениях; улучшились tiny_churn и size_biased_deletion, ухудшились short_phase_churn и serial_churn. Низкие результаты micro_partial_drain достигают входного потолка и не свидетельствуют о потерях аллокатора, тогда как отдельный случай tiny_churn показывает перерасход траншеи относительно B на 44.8%.
**Program Identifier:** Generation 26 - Patch Name reusable_slot_inventory - Correct Program: True

# Previous Global Insights (if any)
*No previous insights available.*

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
// NAME: exposure_guided_split
// DESCRIPTION: Parent residual-fit selection with exposure-guided
// placement at either edge of the selected hole.
// Ablation: kEnableExposureSplit=false restores parent placements.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kEnableExposureSplit = true;
    static constexpr long double kHazardPriorReleases = 2.0L;
    static constexpr long double kSplitRateRatio = 1.25L;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    using LiveMap = std::map<int, std::size_t>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    LiveMap live_;
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
    // Exposure is measured in live-pipe command steps.
    // Per-size exposure is settled lazily when its population changes.
    std::uint64_t commandClock_ = 0;
    std::size_t liveCount_ = 0;
    std::uint64_t totalReleases_ = 0;
    long double totalExposure_ = 0.0L;
    std::array<std::size_t, kMaxLength + 1> liveByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> releasesByLength_{};
    std::array<std::uint64_t, kMaxLength + 1> exposureClock_{};
    std::array<long double, kMaxLength + 1> exposure_{};
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
    void beginCommand() {
        ++commandClock_;
        totalExposure_ += static_cast<long double>(liveCount_);
    }
    long double exposureAt(int length) const {
        return exposure_[length]
             + static_cast<long double>(liveByLength_[length])
             * static_cast<long double>(
                   commandClock_ - exposureClock_[length]);
    }
    void settleExposure(int length) {
        exposure_[length] = exposureAt(length);
        exposureClock_[length] = commandClock_;
    }
    void recordBirth(int length) {
        settleExposure(length);
        ++liveByLength_[length];
        ++liveCount_;
    }
    void recordRelease(int length) {
        settleExposure(length);
        --liveByLength_[length];
        --liveCount_;
        ++releasesByLength_[length];
        ++totalReleases_;
    }
    bool preferRightSplit(int start, int size, int length) const {
        if (!kEnableExposureSplit ||
            size == length ||
            totalReleases_ == 0) {
            return false;
        }
        const auto right = live_.lower_bound(start);
        if (right == live_.begin() || right == live_.end()) {
            return false;
        }
        const auto left = std::prev(right);
        const Pipe& leftPipe = pipes_[left->second];
        const Pipe& rightPipe = pipes_[right->second];
        if (leftPipe.start + leftPipe.length != start ||
            rightPipe.start != start + size ||
            leftPipe.length == rightPipe.length) {
            return false;
        }
        const long double priorExposure =
            kHazardPriorReleases * totalExposure_
            / static_cast<long double>(totalReleases_);
        const auto releaseRate = [&](int neighborLength) {
            const long double releases =
                static_cast<long double>(
                    releasesByLength_[neighborLength])
                + kHazardPriorReleases;
            return releases
                 / (exposureAt(neighborLength) + priorExposure);
        };
        // Leave the residual beside the neighbor with a sufficiently
        // higher estimated release rate.
        return releaseRate(leftPipe.length)
             > kSplitRateRatio * releaseRate(rightPipe.length);
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
            // Here residual >= 40, and regret is nonnegative.
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
        beginCommand();
        observe(length);
        const auto chosen = chooseHole(length);
        int start;
        int sections = 0;
        if (chosen.first >= 0) {
            const int holeStart = chosen.first;
            const int size = chosen.second;
            const bool splitRight =
                preferRightSplit(holeStart, size, length);
            eraseHole(holes_.find(holeStart));
            if (splitRight) {
                start = holeStart + size - length;
                addHole(holeStart, size - length);
            } else {
                start = holeStart;
                addHole(start + length, size - length);
            }
        } else {
            start = frontier_;
            const int missing = length - (trench_ - frontier_);
            if (missing > 0) {
                sections = (missing + 19) / 20;
                trench_ += sections * 20;
            }
            frontier_ += length;
        }
        const std::size_t pid = pipes_.size();
        pipes_.push_back({start, length});
        live_.emplace(start, pid);
        recordBirth(length);
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        beginCommand();
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        const int length = pipe.length;
        int start = pipe.start;
        int end = start + length;
        recordRelease(length);
        live_.erase(originalStart);
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.96; max_solver_rss_mib: 6.97

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.858725881688; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737372285
family=short_phase_churn mean_F/T=0.787992087
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.804543117
family=geometric_cohorts mean_F/T=0.804658811
family=short_heavy mean_F/T=0.815309385
family=additive_cohorts mean_F/T=0.816622444
family=short_rounding mean_F/T=0.818879585
family=size_biased_deletion mean_F/T=0.832790102
family=distribution_switch mean_F/T=0.833180533
family=long_heavy mean_F/T=0.836498918
family=tiny_churn mean_F/T=0.836653564
family=uniform_churn mean_F/T=0.840183451
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847447788
family=serial_churn mean_F/T=0.860681252
family=fifo mean_F/T=0.871267344
family=size_lifetimes mean_F/T=0.877997332
family=large_live_set mean_F/T=0.880824573
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882253931
family=hotset_switching mean_F/T=0.884150975
family=bimodal mean_F/T=0.885649817
family=section_boundaries mean_F/T=0.892592429
family=soft_recency_growth mean_F/T=0.896819876
family=burst_drain mean_F/T=0.911334181
family=serial_growth mean_F/T=0.915940726
family=long_prefill_recent mean_F/T=0.917708455
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920715402
family=drain_recovery mean_F/T=0.925561568
family=hotset_growth mean_F/T=0.950146436
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955228518
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001551 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001431 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001378 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001541 rss_mib=1.328
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001467 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001546 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611126393 F/B=0.646045362 B/T=0.945949663 overrun=0.057139 cpu_s=0.087911 rss_mib=1.812
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617432770 F/B=0.675406191 B/T=0.914165103 overrun=0.093894 cpu_s=0.310511 rss_mib=1.938
case=s31_060_large_live_set family=large_live_set F/T=0.632236996 F/B=0.641932619 B/T=0.984896198 overrun=0.015335 cpu_s=0.410322 rss_mib=2.828
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001463 rss_mib=1.328
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.321618 rss_mib=1.656
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001430 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002988 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012696 rss_mib=1.438
case=s31_040_distribution_switch family=distribution_switch F/T=0.663824885 F/B=0.692548077 B/T=0.958525346 overrun=0.043269 cpu_s=0.017038 rss_mib=1.406
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003085 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.353591 rss_mib=1.703
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.752840495 F/B=0.950045956 B/T=0.792425346 overrun=0.261949 cpu_s=0.131466 rss_mib=1.734
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.330365 rss_mib=1.672
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003085 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.074027 rss_mib=1.453
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.640476190 F/B=0.781976744 B/T=0.819047619 overrun=0.220930 cpu_s=0.321618 rss_mib=1.656
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001752 rss_mib=1.328
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002440 rss_mib=1.391
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.057560 rss_mib=1.438
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.810256410 F/B=0.954682779 B/T=0.848717949 overrun=0.178248 cpu_s=0.035789 rss_mib=1.422
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.515271 rss_mib=1.812
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.119721 rss_mib=1.516
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.825972927 F/B=0.950170316 B/T=0.869289340 overrun=0.150365 cpu_s=0.122868 rss_mib=1.609
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854160963 F/B=0.982097589 B/T=0.869731249 overrun=0.149780 cpu_s=0.161188 rss_mib=2.391
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.670988655 F/B=0.768089054 B/T=0.873581848 overrun=0.144712 cpu_s=0.019384 rss_mib=1.391
case=s31_102_serial_churn family=serial_churn F/T=0.834530387 F/B=0.950000000 B/T=0.878453039 overrun=0.138365 cpu_s=0.148440 rss_mib=1.500

PAIRED SEARCH EVIDENCE
Against parent gen6: delta mean F/T=+0.001161829; improved/regressed/tied=39/37/76.
family=size_lifetimes delta_F/T=+0.032814476
family=long_heavy delta_F/T=-0.012545109
family=short_heavy delta_F/T=-0.012509958
family=distribution_switch delta_F/T=+0.012370449
family=uniform_churn delta_F/T=+0.012191894
family=short_phase_churn delta_F/T=+0.011236345
Regressions:
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_024_fifo: delta_F/T=-0.030388889, delta_T=+60
s31_049_geometric_cohorts: delta_F/T=-0.020295983, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.060079365, delta_T=-60
s31_033_burst_drain: delta_F/T=+0.044027517, delta_T=-40
s31_001_uniform_churn: delta_F/T=+0.039774859, delta_T=-40

Against leader gen6: delta mean F/T=+0.001161829; improved/regressed/tied=39/37/76.
family=size_lifetimes delta_F/T=+0.032814476
family=long_heavy delta_F/T=-0.012545109
family=short_heavy delta_F/T=-0.012509958
family=distribution_switch delta_F/T=+0.012370449
family=uniform_churn delta_F/T=+0.012191894
family=short_phase_churn delta_F/T=+0.011236345
Regressions:
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_024_fifo: delta_F/T=-0.030388889, delta_T=+60
s31_049_geometric_cohorts: delta_F/T=-0.020295983, delta_T=+20
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_063_size_biased_deletion: delta_F/T=+0.060079365, delta_T=-60
s31_033_burst_drain: delta_F/T=+0.044027517, delta_T=-40
s31_001_uniform_churn: delta_F/T=+0.039774859, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.858725882; mean positive loss on worst 16 cases=0.020671861; max case loss=0.043797644; regressed cases=38; worst family delta F/T=-0.012369502. These are selection diagnostics; primary fitness remains mean F/T.



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
