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
// NAME: mixed_pair_tail_guard
// DESCRIPTION: Preserve capacity_guarded_tail and additionally reject tail
// placement when it reduces weighted packability of two mixed requests.
// The exact pair test uses the two largest remaining free intervals.
// Same-parent ablation: replace the final pairMass comparison with true.
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
    bool preferFreeTail(int length, int holeSize) const {
        const int tail = trench_ - frontier_;
        if (tail < length || tail >= kMaxLength ||
            !large_.empty() || holeSize - length >= kMaxLength) {
            return false;
        }
        // Capacity guard: суммарная свободная длина одинакова,
        // поэтому меньшая сумма остатков означает большую взвешенную
        // вместимость для однородных продолжений каждого размера.
        // Здесь tail < 40 и holeSize < 80: все индексы допустимы.
        const std::int64_t wasteAfterHole =
            waste_[holeSize - length] + waste_[tail];
        const std::int64_t wasteAfterTail =
            waste_[holeSize] + waste_[tail - length];
        if (wasteAfterTail > wasteAfterHole) {
            return false;
        }
        // После исключения выбранной дыры находим крупнейшую оставшуюся.
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
        if (tailCost >= holeCost) {
            return false;
        }
        // low already excludes the selected hole, including multiplicity.
        int secondOther = 0;
        if (largestOther != 0) {
            const std::size_t copies =
                bins_[largestOther].size()
                - static_cast<std::size_t>(largestOther == holeSize);
            if (copies >= 2) {
                secondOther = largestOther;
            } else {
                const std::uint64_t remaining =
                    low & ~(std::uint64_t{1} << largestOther);
                secondOther = remaining == 0
                    ? 0 : 63 - std::countl_zero(remaining);
            }
        }
        std::array<std::int64_t, kMaxLength + 1> prefix{};
        for (int k = 1; k <= kMaxLength; ++k) {
            prefix[k] = prefix[k - 1] + weights_[k];
        }
        const auto pairMass = [&](int first, int second) -> std::int64_t {
            int largest = std::max(largestOther, first);
            int runnerUp =
                std::max(secondOther, std::min(largestOther, first));
            if (second >= largest) {
                runnerUp = largest;
                largest = second;
            } else {
                runnerUp = std::max(runnerUp, second);
            }
            std::int64_t mass = 0;
            for (int a = 1; a <= kMaxLength && a <= largest; ++a) {
                // For a >= b, either use separate intervals or share
                // the largest interval. Both cases give a prefix in b.
                const int limit =
                    std::min(a, std::max(runnerUp, largest - a));
                const std::int64_t diagonal =
                    limit == a ? weights_[a] : 0;
                mass += static_cast<std::int64_t>(weights_[a])
                      * (2 * prefix[limit] - diagonal);
            }
            return mass;
        };
        return pairMass(holeSize, tail - length) >=
               pairMass(holeSize - length, tail);
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
            !preferFreeTail(length, chosen.second)) {
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.96; max_solver_cpu_seconds: 0.92; max_solver_rss_mib: 2.55

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.857484073311; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737629257
family=short_phase_churn mean_F/T=0.782545303
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.802607687
family=drifting_sizes mean_F/T=0.805009888
family=short_rounding mean_F/T=0.818879585
family=additive_cohorts mean_F/T=0.819174828
family=short_heavy mean_F/T=0.823775225
family=distribution_switch mean_F/T=0.824018292
family=uniform_churn mean_F/T=0.833157585
family=size_biased_deletion mean_F/T=0.833560375
family=tiny_churn mean_F/T=0.835116112
family=long_heavy mean_F/T=0.839345751
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.847436039
family=size_lifetimes mean_F/T=0.852986650
family=serial_churn mean_F/T=0.863333638
family=large_live_set mean_F/T=0.879207521
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882402103
family=fifo mean_F/T=0.882521668
family=hotset_switching mean_F/T=0.882588793
family=bimodal mean_F/T=0.882709140
family=section_boundaries mean_F/T=0.884857643
family=soft_recency_growth mean_F/T=0.896735286
family=burst_drain mean_F/T=0.900233006
family=serial_growth mean_F/T=0.914924680
family=long_prefill_recent mean_F/T=0.917760678
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920733211
family=drain_recovery mean_F/T=0.924876633
family=hotset_growth mean_F/T=0.950605918
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955083670
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001581 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001514 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001705 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001778 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001510 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001463 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.611546931 F/B=0.646045362 B/T=0.946600606 overrun=0.056412 cpu_s=0.083032 rss_mib=1.562
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618206011 F/B=0.675406191 B/T=0.915309956 overrun=0.092526 cpu_s=0.296954 rss_mib=1.766
case=s31_060_large_live_set family=large_live_set F/T=0.632384508 F/B=0.641932619 B/T=0.985125992 overrun=0.015099 cpu_s=0.389790 rss_mib=2.094
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001675 rss_mib=1.344
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.315194 rss_mib=1.625
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001402 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002947 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012370 rss_mib=1.359
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.016782 rss_mib=1.391
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002929 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.335117 rss_mib=1.656
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.347521 rss_mib=1.688
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.755868373 F/B=0.950045956 B/T=0.795612431 overrun=0.256893 cpu_s=0.121759 rss_mib=1.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002929 rss_mib=1.375
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.697903226 F/B=0.865400000 B/T=0.806451613 overrun=0.240000 cpu_s=0.072811 rss_mib=1.438
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.055028 rss_mib=1.422
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.315194 rss_mib=1.625
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.113201 rss_mib=1.484
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001727 rss_mib=1.344
case=s31_017_section_boundaries family=section_boundaries F/T=0.801020408 F/B=0.957317073 B/T=0.836734694 overrun=0.195122 cpu_s=0.030319 rss_mib=1.406
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002309 rss_mib=1.375
case=s31_086_tiny_churn family=tiny_churn F/T=0.824074074 F/B=0.959051724 B/T=0.859259259 overrun=0.163793 cpu_s=0.123352 rss_mib=1.469
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.633609 rss_mib=1.906
case=s31_006_short_heavy family=short_heavy F/T=0.825000000 F/B=0.953333333 B/T=0.865384615 overrun=0.155556 cpu_s=0.325937 rss_mib=1.656
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.822840287 F/B=0.950170316 B/T=0.865992415 overrun=0.154745 cpu_s=0.116695 rss_mib=1.516
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854099424 F/B=0.982097589 B/T=0.869668588 overrun=0.149863 cpu_s=0.154381 rss_mib=1.859

PAIRED SEARCH EVIDENCE
Against parent gen23: delta mean F/T=-0.000124226; improved/regressed/tied=5/9/138.
family=additive_cohorts delta_F/T=-0.002349065
family=hotset_switching delta_F/T=-0.001850548
family=soft_recency_growth delta_F/T=-0.000448157
family=partial_drain delta_F/T=-0.000304361
family=hotset_growth delta_F/T=+0.000284191
family=drain_recovery delta_F/T=+0.000281669
Regressions:
s31_054_additive_cohorts: delta_F/T=-0.009396259, delta_T=+80
s31_096_hotset_switching: delta_F/T=-0.006917094, delta_T=+80
s31_071_soft_recency_growth: delta_F/T=-0.001983674, delta_T=+440
s31_119_partial_drain: delta_F/T=-0.001217446, delta_T=+160
Gains:
s31_116_drain_recovery: delta_F/T=+0.002051886, delta_T=-260
s31_090_hotset_growth: delta_F/T=+0.001278045, delta_T=-180
s31_070_soft_recency_growth: delta_F/T=+0.000191046, delta_T=-40
s31_099_serial_growth: delta_F/T=+0.000093884, delta_T=-20

Against leader gen61: delta mean F/T=-0.002077393; improved/regressed/tied=30/51/71.
family=size_lifetimes delta_F/T=-0.023774882
family=fifo delta_F/T=+0.018009001
family=section_boundaries delta_F/T=-0.016603840
family=bimodal delta_F/T=-0.013925807
family=short_rounding delta_F/T=+0.010657895
family=distribution_switch delta_F/T=-0.010465781
Regressions:
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.052240461, delta_T=+60
s31_033_burst_drain: delta_F/T=-0.044027517, delta_T=+40
s31_049_geometric_cohorts: delta_F/T=-0.039689922, delta_T=+40
Gains:
s31_122_short_rounding: delta_F/T=+0.042631579, delta_T=-20
s31_024_fifo: delta_F/T=+0.019981735, delta_T=-40
s31_008_short_heavy: delta_F/T=+0.019911248, delta_T=-40
s31_127_short_phase_churn: delta_F/T=+0.018736786, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.857484073; mean positive loss on worst 16 cases=0.027202981; max case loss=0.075378788; regressed cases=36; worst family delta F/T=-0.021385077. These are selection diagnostics; primary fitness remains mean F/T.



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
