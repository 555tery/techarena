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

The program is correct and passes all validation tests.

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
