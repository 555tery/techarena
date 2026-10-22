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
namespace {
using Coordinate = std::int64_t;
class Allocator {
    struct Pipe {
        Coordinate start = 0;
        int length = 0;
        std::uint64_t birthClock = 0;
        std::size_t left = 0;
        std::size_t right = 0;
    };
    struct Gap {
        Coordinate finish;
        std::size_t left;
        std::size_t right;
    };
    struct ReleaseCell {
        std::uint64_t live = 0;
        std::uint64_t deaths = 0;
        std::uint64_t lastClock = 0;
        double exposure = 0.0;
    };
    static constexpr bool useAgeConditioning_ = true;
    static constexpr std::array<std::uint64_t, 2> ageLimits_{{64, 512}};
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Gap> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    std::array<std::array<ReleaseCell, 3>, 41> release_{};
    std::array<std::size_t, 2> ageCursor_{{1, 1}};
    std::uint64_t clock_ = 0;
    std::uint64_t liveCount_ = 0;
    std::uint64_t deaths_ = 0;
    double totalExposure_ = 0.0;
    Coordinate trench_ = 0;
    std::size_t rightmostPipe_ = 0;
    static int bucket(Coordinate n) {
        return static_cast<int>(std::min<Coordinate>(40, n));
    }
    static int ageBucket(std::uint64_t age) {
        if (age < ageLimits_[0]) return 0;
        if (age < ageLimits_[1]) return 1;
        return 2;
    }
    void add(Coordinate a, Coordinate b,
             std::size_t left, std::size_t right) {
        if (a >= b) return;
        gaps_.emplace(a, Gap{b, left, right});
        sizes_.insert({b - a, a});
        starts_[bucket(b - a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a).finish;
        sizes_.erase({b - a, a});
        starts_[bucket(b - a)].erase(a);
        gaps_.erase(a);
    }
    static void settle(ReleaseCell& cell, std::uint64_t time) {
        cell.exposure += static_cast<double>(time - cell.lastClock)
                       * static_cast<double>(cell.live);
        cell.lastClock = time;
    }
    void changeCount(int length, int age, bool increase,
                     std::uint64_t time) {
        ReleaseCell& cell = release_[length][age];
        settle(cell, time);
        if (increase) {
            ++cell.live;
        } else {
            --cell.live;
        }
    }
    double exposureNow(const ReleaseCell& cell) const {
        return cell.exposure
             + static_cast<double>(clock_ - cell.lastClock)
             * static_cast<double>(cell.live);
    }
    void advanceClock() {
        const std::uint64_t previousClock = clock_;
        ++clock_;
        totalExposure_ += static_cast<double>(liveCount_);
        for (int stage = 0; stage < 2; ++stage) {
            std::size_t& cursor = ageCursor_[stage];
            while (cursor < pipes_.size()) {
                const Pipe& pipe = pipes_[cursor];
                if (clock_ - pipe.birthClock < ageLimits_[stage]) break;
                ++cursor;
                if (pipe.length == 0) continue;
                // Move at the previous timestamp so the current command's
                // exposure belongs to the new age bucket.
                changeCount(pipe.length, stage, false, previousClock);
                changeCount(pipe.length, stage + 1, true, previousClock);
            }
        }
    }
    double releaseRate(std::size_t pid) const {
        const Pipe& pipe = pipes_[pid];
        const auto& cells = release_[pipe.length];
        double sizeExposure = 0.0;
        std::uint64_t sizeDeaths = 0;
        for (const ReleaseCell& cell : cells) {
            sizeExposure += exposureNow(cell);
            sizeDeaths += cell.deaths;
        }
        const double pooledRate =
            static_cast<double>(deaths_) / totalExposure_;
        // Two virtual deaths shrink sparse size estimates to the pooled rate.
        const double sizeRate =
            (static_cast<double>(sizeDeaths) + 2.0)
            / (sizeExposure + 2.0 / pooledRate);
        if constexpr (!useAgeConditioning_) {
            return sizeRate;
        }
        const int age = ageBucket(clock_ - pipe.birthClock);
        const ReleaseCell& cell = cells[age];
        const double ageExposure = exposureNow(cell);
        // Survival without deaths also supplies evidence of a lower rate.
        if (cell.deaths < 4 && ageExposure * sizeRate < 8.0) {
            return sizeRate;
        }
        // Four virtual deaths shrink the age estimate to its size estimate.
        return (static_cast<double>(cell.deaths) + 4.0)
             / (ageExposure + 4.0 / sizeRate);
    }
    bool preferRight(const Gap& gap) const {
        // Preserve the parent's behavior at both trench boundaries.
        if (gap.left == 0 || gap.right == 0 ||
            deaths_ == 0 || totalExposure_ <= 0.0) {
            return false;
        }
        const double leftRate = releaseRate(gap.left);
        const double rightRate = releaseRate(gap.right);
        // Placing on the right leaves the remainder beside the left neighbor.
        return leftRate > 1.25 * rightRate;
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        advanceClock();
        Coordinate at = -1, digs = 0;
        for (int k = length; k <= 40; ++k) {
            if (!starts_[k].empty() &&
                (at < 0 || *starts_[k].begin() < at)) {
                at = *starts_[k].begin();
            }
        }
        // Growth is permitted only after the global fitting-gap search fails.
        if (at < 0) {
            at = trench_;
            std::size_t left = rightmostPipe_;
            if (!gaps_.empty() &&
                gaps_.rbegin()->second.finish == trench_) {
                at = gaps_.rbegin()->first;
                left = gaps_.rbegin()->second.left;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_, left, 0);
        }
        const Gap chosen = gaps_.at(at);
        const Coordinate finish = chosen.finish;
        Coordinate start = at;
        if (finish - at > length && preferRight(chosen)) {
            start = finish - length;
        }
        erase(at);
        const std::size_t pid = pipes_.size();
        pipes_.push_back(
            Pipe{start, length, clock_, chosen.left, chosen.right});
        if (chosen.left != 0) {
            pipes_[chosen.left].right = pid;
        }
        if (chosen.right != 0) {
            pipes_[chosen.right].left = pid;
        } else {
            rightmostPipe_ = pid;
        }
        add(at, start, chosen.left, pid);
        add(start + length, finish, pid, chosen.right);
        changeCount(length, 0, true, clock_);
        ++liveCount_;
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        advanceClock();
        const std::size_t id = static_cast<std::size_t>(pid);
        const Pipe p = pipes_.at(id);
        const int age = ageBucket(clock_ - p.birthClock);
        ReleaseCell& cell = release_[p.length][age];
        settle(cell, clock_);
        --cell.live;
        ++cell.deaths;
        ++deaths_;
        --liveCount_;
        // A zero length marks a dead pipe for the two transition cursors.
        pipes_[id].length = 0;
        if (p.left != 0) {
            pipes_[p.left].right = p.right;
        }
        if (p.right != 0) {
            pipes_[p.right].left = p.left;
        } else {
            rightmostPipe_ = p.left;
        }
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second.finish;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second.finish == a) {
                a = left->first;
                erase(a);
            }
        }
        add(a, b, p.left, p.right);
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
Combined score to maximize: 0.85
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.85; worst_family_score: 0.53; mean_overrun: 0.06; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.03; max_solver_rss_mib: 12.58

The program is correct and passes all validation tests.

Text feedback:
Fitness F/T=0.848500141568; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.736914168
family=short_phase_churn mean_F/T=0.766340446
family=drifting_sizes mean_F/T=0.782245745
family=uniform_churn mean_F/T=0.789673106
family=short_heavy mean_F/T=0.794548974
family=micro_size_shift mean_F/T=0.802083333
family=distribution_switch mean_F/T=0.807161395
family=long_heavy mean_F/T=0.810158819
family=geometric_cohorts mean_F/T=0.814406445
family=short_rounding mean_F/T=0.818636924
family=large_live_set mean_F/T=0.819270823
family=additive_cohorts mean_F/T=0.823194963
family=size_biased_deletion mean_F/T=0.824178002
family=long_prefill_random mean_F/T=0.827567764
family=tiny_churn mean_F/T=0.838214135
family=micro_tail_reuse mean_F/T=0.845833333
family=section_boundaries mean_F/T=0.847729199
family=size_lifetimes mean_F/T=0.850893940
family=serial_churn mean_F/T=0.860757943
family=bimodal mean_F/T=0.866848933
family=hotset_switching mean_F/T=0.873825880
family=fifo mean_F/T=0.879233491
family=recent_window_growth mean_F/T=0.881136620
family=micro_gap_refill mean_F/T=0.881250000
family=soft_recency_growth mean_F/T=0.886597916
family=burst_drain mean_F/T=0.893394419
family=serial_growth mean_F/T=0.909570124
family=long_prefill_recent mean_F/T=0.916731939
family=isolated_recent_churn mean_F/T=0.917621871
family=drain_recovery mean_F/T=0.917725562
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=hotset_growth mean_F/T=0.946211564
family=background_ephemeral mean_F/T=0.951658406
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960464194
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001622 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001442 rss_mib=1.312
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001446 rss_mib=1.312
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001579 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001451 rss_mib=1.312
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001478 rss_mib=1.312
case=s31_060_large_live_set family=large_live_set F/T=0.583352166 F/B=0.641932619 B/T=0.908743610 overrun=0.100420 cpu_s=0.427895 rss_mib=6.734
case=s31_118_partial_drain family=partial_drain F/T=0.610203241 F/B=0.646045362 B/T=0.944520736 overrun=0.058738 cpu_s=0.085519 rss_mib=2.656
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.612453474 F/B=0.675406191 B/T=0.906792804 overrun=0.102788 cpu_s=0.310358 rss_mib=5.453
case=s31_040_distribution_switch family=distribution_switch F/T=0.631798246 F/B=0.692548077 B/T=0.912280702 overrun=0.096154 cpu_s=0.016932 rss_mib=1.578
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001407 rss_mib=1.328
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.322422 rss_mib=5.250
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001491 rss_mib=1.312
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.002925 rss_mib=1.391
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.012493 rss_mib=1.578
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002768 rss_mib=1.391
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.673987539 F/B=0.865400000 B/T=0.778816199 overrun=0.284000 cpu_s=0.074421 rss_mib=2.047
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.742187500 F/B=0.950000000 B/T=0.781250000 overrun=0.280000 cpu_s=0.336620 rss_mib=5.344
case=s31_001_uniform_churn family=uniform_churn F/T=0.757142857 F/B=0.963636364 B/T=0.785714286 overrun=0.272727 cpu_s=0.063782 rss_mib=1.750
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.355719 rss_mib=5.469
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002768 rss_mib=1.391
case=s31_017_section_boundaries family=section_boundaries F/T=0.769607843 F/B=0.957317073 B/T=0.803921569 overrun=0.243902 cpu_s=0.030425 rss_mib=1.688
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.649758454 F/B=0.781976744 B/T=0.830917874 overrun=0.203488 cpu_s=0.322422 rss_mib=5.250
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.789950325 F/B=0.950045956 B/T=0.831486435 overrun=0.202665 cpu_s=0.130874 rss_mib=2.766
case=s31_102_serial_churn family=serial_churn F/T=0.790837696 F/B=0.950000000 B/T=0.832460733 overrun=0.201258 cpu_s=0.157694 rss_mib=2.672
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001697 rss_mib=1.344
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002343 rss_mib=1.375
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.831689350 F/B=0.982097589 B/T=0.846850007 overrun=0.180847 cpu_s=0.157705 rss_mib=4.156
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.812339332 F/B=0.954682779 B/T=0.850899743 overrun=0.175227 cpu_s=0.036379 rss_mib=1.734
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.522224 rss_mib=6.188
case=s31_039_distribution_switch family=distribution_switch F/T=0.820138889 F/B=0.952419355 B/T=0.861111111 overrun=0.161290 cpu_s=0.626634 rss_mib=9.156
case=s31_128_short_phase_churn family=short_phase_churn F/T=0.791562500 F/B=0.917753623 B/T=0.862500000 overrun=0.159420 cpu_s=0.029643 rss_mib=1.703

PAIRED SEARCH EVIDENCE
Against parent gen2: delta mean F/T=+0.001067891; improved/regressed/tied=47/29/76.
family=size_lifetimes delta_F/T=+0.021170646
family=short_phase_churn delta_F/T=+0.015135506
family=geometric_cohorts delta_F/T=+0.013140849
family=serial_churn delta_F/T=-0.008643035
family=uniform_churn delta_F/T=-0.007073230
family=bimodal delta_F/T=+0.006816360
Regressions:
s31_001_uniform_churn: delta_F/T=-0.037857143, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.034572140, delta_T=+160
s31_044_drifting_sizes: delta_F/T=-0.026174273, delta_T=+240
s31_008_short_heavy: delta_F/T=-0.018849315, delta_T=+40
Gains:
s31_031_size_lifetimes: delta_F/T=+0.075378788, delta_T=-20
s31_126_short_phase_churn: delta_F/T=+0.043597263, delta_T=-40
s31_049_geometric_cohorts: delta_F/T=+0.041558442, delta_T=-40
s31_041_drifting_sizes: delta_F/T=+0.033232276, delta_T=-60

Against leader gen24: delta mean F/T=-0.010225740; improved/regressed/tied=13/78/61.
family=large_live_set delta_F/T=-0.061553750
family=uniform_churn delta_F/T=-0.050510345
family=section_boundaries delta_F/T=-0.044863229
family=size_lifetimes delta_F/T=-0.027103392
family=long_heavy delta_F/T=-0.026340099
family=distribution_switch delta_F/T=-0.026019137
Regressions:
s31_017_section_boundaries: delta_F/T=-0.083653026, delta_T=+100
s31_057_large_live_set: delta_F/T=-0.076849251, delta_T=+57780
s31_059_large_live_set: delta_F/T=-0.068892090, delta_T=+13400
s31_005_short_heavy: delta_F/T=-0.064192329, delta_T=+1100
Gains:
s31_103_serial_churn: delta_F/T=+0.043999453, delta_T=-60
s31_049_geometric_cohorts: delta_F/T=+0.041558442, delta_T=-40
s31_050_geometric_cohorts: delta_F/T=+0.037109830, delta_T=-2580
s31_055_additive_cohorts: delta_F/T=+0.031938250, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.848500142; mean positive loss on worst 16 cases=0.056190478; max case loss=0.083653026; regressed cases=71; worst family delta F/T=-0.059724125. These are selection diagnostics; primary fitness remains mean F/T.



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
