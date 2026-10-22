# System Instructions

You are an expert programming assistant analyzing an individual program. Create a standalone summary focusing on implementation details and evaluation feedback. Consider how this specific program performs and what implementation choices were made.

# Previous Messages

[]

# User Request

# Program to Analyze
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
// NAME: shift_triggered_demand_blend
// DESCRIPTION: Demand-Weighted Residual Fit с детектором смены спроса.
//
// Каждые 16 вставок сравниваются распределения последних 64 вставок
// и накопленных наблюдений. При TV > 1/4 используется их равная смесь
// с прежней эффективной массой наблюдений и равномерным prior +1.
// Дробные веса представлены целыми числителями с общим знаменателем.
//
// Для интервала s и запроса L оценивается дополнительная потеря вместимости:
// R(s,L) = sum_k w[k]*k*(floor(s/k)-floor((s-L)/k)-floor(L/k)).
// Минимизируется 8*R(s,L) + sum(w)*min(s-L,40);
// при равенстве выбирается меньший интервал, затем меньшая координата.
// Для размеров <80 рассматриваются все непустые bins. Для больших дыр
// оценивается левейшая дыра каждого из первых восьми различных размеров.
// Свободный хвост используется после внутренних дыр.
//
// Вставка: амортизированно O(80 + 8*40 + 9*log H + 40*80/16).
// Удаление: O(log H). Память: O(P + H + 64 + 40).
// Возможный недостаток: ложный сигнал смены спроса и задержка окна
// на коротких фазах; корреляция удалений по-прежнему не моделируется.
// Ablation: kEnableShiftBlend = false восстанавливает решения родителя.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    std::array<std::set<int>, kSmallLimit> bins_;
    std::set<std::pair<int, int>> large_;
    std::uint64_t lowMask_ = 0;
    std::uint64_t highMask_ = 0;
    int trench_ = 0;
    int frontier_ = 0;
    std::size_t insertions_ = 0;
    static constexpr bool kEnableShiftBlend = true;
    std::array<std::uint8_t, 64> recentLengths_{};
    std::array<std::uint32_t, kMaxLength + 1> recentObservations_{};
    bool shiftedProfile_ = false;
    std::array<std::uint32_t, kMaxLength + 1> observations_{};
    std::array<std::uint32_t, kMaxLength + 1> weights_{};
    std::array<std::int64_t, kSmallLimit> waste_{};
    std::int64_t totalWeight_ = 0;
    void rebuildProfile() {
        const std::uint32_t recentCount = static_cast<std::uint32_t>(
            std::min(insertions_, recentLengths_.size()));
        std::uint32_t observationCount = 0;
        if (shiftedProfile_) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observationCount += observations_[k];
            }
        }
        waste_.fill(0);
        totalWeight_ = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            if (shiftedProfile_) {
                // 2*recentCount times the effective weight:
                // 1 + (observations[k] + N*recent[k]/recentCount)/2.
                weights_[k] =
                    recentCount * (observations_[k] + 2u)
                    + observationCount * recentObservations_[k];
            } else {
                weights_[k] = observations_[k] + 1;
            }
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
        const std::size_t slot = insertions_ & 63u;
        if (insertions_ >= recentLengths_.size()) {
            --recentObservations_[recentLengths_[slot]];
        }
        recentLengths_[slot] = static_cast<std::uint8_t>(length);
        ++recentObservations_[length];
        ++insertions_;
        ++observations_[length];
        if ((insertions_ & 511u) == 0) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observations_[k] >>= 1;
            }
        }
        bool refreshProfile =
            insertions_ <= 32 || (insertions_ & 63u) == 0;
        if (kEnableShiftBlend && (insertions_ & 15u) == 0) {
            const std::uint64_t recentCount =
                std::min(insertions_, recentLengths_.size());
            std::uint64_t observationCount = 0;
            for (int k = 1; k <= kMaxLength; ++k) {
                observationCount += observations_[k];
            }
            std::uint64_t difference = 0;
            for (int k = 1; k <= kMaxLength; ++k) {
                const std::uint64_t recent =
                    recentObservations_[k] * observationCount;
                const std::uint64_t accumulated =
                    observations_[k] * recentCount;
                difference += recent >= accumulated
                    ? recent - accumulated : accumulated - recent;
            }
            // TV = difference / (2*recentCount*observationCount).
            const bool shifted =
                2 * difference > recentCount * observationCount;
            refreshProfile = refreshProfile || shifted
                || shifted != shiftedProfile_;
            shiftedProfile_ = shifted;
        }
        if (refreshProfile) {
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
            constexpr int kLargeProbes = 8;
            // Здесь residual >= 40, а regret неотрицателен.
            const std::int64_t baseScore = totalWeight_ * kMaxLength;
            auto candidate = large_.begin();
            for (int probe = 0;
                 probe < kLargeProbes && candidate != large_.end()
                     && baseScore < bestScore;
                 ++probe) {
                const int size = candidate->first;
                const int start = candidate->second;
                std::int64_t score = baseScore;
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
                    bestScore = score;
                }
                if (bestScore == baseScore) {
                    break;
                }
                candidate = large_.upper_bound(
                    std::make_pair(size, std::numeric_limits<int>::max()));
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
        observe(length);
        const auto chosen = chooseHole(length);
        int start;
        int sections = 0;
        if (chosen.first >= 0) {
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
        pipes_.push_back({start, length});
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.92; max_solver_rss_mib: 2.53

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.857357742692; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737418457
family=short_phase_churn mean_F/T=0.776072772
family=drifting_sizes mean_F/T=0.800164784
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.804462285
family=short_rounding mean_F/T=0.819122721
family=additive_cohorts mean_F/T=0.822981305
family=distribution_switch mean_F/T=0.825664545
family=size_biased_deletion mean_F/T=0.828646549
family=short_heavy mean_F/T=0.829052920
family=uniform_churn mean_F/T=0.830591357
family=tiny_churn mean_F/T=0.836653564
family=long_heavy mean_F/T=0.839747497
family=size_lifetimes mean_F/T=0.843568674
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846354236
family=serial_churn mean_F/T=0.858671026
family=fifo mean_F/T=0.878225417
family=large_live_set mean_F/T=0.880080271
family=bimodal mean_F/T=0.880282420
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882136426
family=hotset_switching mean_F/T=0.887885994
family=section_boundaries mean_F/T=0.889334007
family=soft_recency_growth mean_F/T=0.897016423
family=burst_drain mean_F/T=0.910962343
family=serial_growth mean_F/T=0.915525816
family=long_prefill_recent mean_F/T=0.917792765
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920602359
family=drain_recovery mean_F/T=0.924264318
family=hotset_growth mean_F/T=0.950305574
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955428778
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001581 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001552 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001505 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001519 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001500 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001471 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611462777 F/B=0.646045362 B/T=0.946470345 overrun=0.056557 cpu_s=0.082416 rss_mib=1.562
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617143304 F/B=0.675406191 B/T=0.913736521 overrun=0.094407 cpu_s=0.296292 rss_mib=1.719
case=s31_060_large_live_set family=large_live_set F/T=0.632236996 F/B=0.641932619 B/T=0.984896198 overrun=0.015335 cpu_s=0.391065 rss_mib=2.062
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001476 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.319114 rss_mib=1.609
case=s31_040_distribution_switch family=distribution_switch F/T=0.645964126 F/B=0.692548077 B/T=0.932735426 overrun=0.072115 cpu_s=0.016704 rss_mib=1.375
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001365 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002886 rss_mib=1.359
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012080 rss_mib=1.359
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002633 rss_mib=1.359
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.331036 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.354552 rss_mib=1.688
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.752840495 F/B=0.950045956 B/T=0.792425346 overrun=0.261949 cpu_s=0.123138 rss_mib=1.547
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002633 rss_mib=1.359
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.062506 rss_mib=1.438
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.073435 rss_mib=1.406
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.637440758 F/B=0.781976744 B/T=0.815165877 overrun=0.226744 cpu_s=0.319114 rss_mib=1.609
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.113745 rss_mib=1.484
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001716 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002417 rss_mib=1.359
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.030652 rss_mib=1.391
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.821801347 F/B=0.950170316 B/T=0.864898990 overrun=0.156204 cpu_s=0.126297 rss_mib=1.531
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.118300 rss_mib=1.469
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.850179289 F/B=0.982097589 B/T=0.865676994 overrun=0.155165 cpu_s=0.150819 rss_mib=1.844
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.112118 rss_mib=1.469
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.035734 rss_mib=1.391

PAIRED SEARCH EVIDENCE
Against parent gen51: delta mean F/T=-0.000257633; improved/regressed/tied=26/29/97.
family=burst_drain delta_F/T=+0.011162997
family=long_heavy delta_F/T=-0.009927111
family=geometric_cohorts delta_F/T=-0.007492311
family=size_lifetimes delta_F/T=-0.006487992
family=additive_cohorts delta_F/T=+0.005077519
family=fifo delta_F/T=-0.004448342
Regressions:
s31_009_long_heavy: delta_F/T=-0.038793103, delta_T=+60
s31_049_geometric_cohorts: delta_F/T=-0.020295983, delta_T=+20
s31_001_uniform_churn: delta_F/T=-0.019390244, delta_T=+20
s31_030_size_lifetimes: delta_F/T=-0.019130435, delta_T=+20
Gains:
s31_033_burst_drain: delta_F/T=+0.044027517, delta_T=-40
s31_055_additive_cohorts: delta_F/T=+0.016264850, delta_T=-20
s31_044_drifting_sizes: delta_F/T=+0.013336415, delta_T=-120
s31_086_tiny_churn: delta_F/T=+0.012209175, delta_T=-40

Against leader gen52: delta mean F/T=-0.001503711; improved/regressed/tied=29/51/72.
family=size_lifetimes delta_F/T=-0.048371896
family=size_biased_deletion delta_F/T=-0.019234802
family=short_heavy delta_F/T=+0.013123942
family=short_rounding delta_F/T=+0.010901031
family=serial_churn delta_F/T=-0.010142162
family=short_phase_churn delta_F/T=-0.009843177
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.165833333, delta_T=+40
s31_063_size_biased_deletion: delta_F/T=-0.082059621, delta_T=+80
s31_103_serial_churn: delta_F/T=-0.043999453, delta_T=+60
s31_127_short_phase_churn: delta_F/T=-0.036640827, delta_T=+40
Gains:
s31_022_fifo: delta_F/T=+0.051499317, delta_T=-340
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_007_short_heavy: delta_F/T=+0.041309524, delta_T=-20
s31_033_burst_drain: delta_F/T=+0.022564103, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857357743; mean positive loss on worst 16 cases=0.029539748; max case loss=0.075378788; regressed cases=40; worst family delta F/T=-0.019738824. These are selection diagnostics; primary fitness remains mean F/T.



# Instructions

Create a standalone summary for this program using the following exact format:

**Program Name: [Short summary name of the algorithm (up to 10 words)]**
- **Implementation**: [Key implementation details (1-2 sentences)]
- **Performance**: [Score/metrics summary (1 sentence)]
- **Feedback**: [Key insights from evaluation (1-2 sentences)]

Focus on:
1. What specific implementation details were done
2. How these details affected performance
3. Implementation details that are relevant to the approach
4. Any evaluation feedback that provides insights

Keep the program summary concise but informative. Follow the format exactly.
