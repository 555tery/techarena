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
    static constexpr int kMaxRequest = 40;
    static constexpr int kMaxScoredGap = 2 * kMaxRequest - 1;
    static constexpr int kLargeBucket = kMaxScoredGap + 1;
    static constexpr int kHorizon = 4;
    // Same-parent ablation: disable only the new placement mechanism.
    static constexpr bool kUseMixedSequenceDP = true;
    struct Pipe {
        Coordinate start;
        int length;
    };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, kLargeBucket + 1> starts_;
    Coordinate trench_ = 0;
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
    std::uint64_t insertions_ = 0;
    std::array<double, kMaxScoredGap + 1> serviceValue_{};
    std::map<Coordinate, std::size_t> live_;
    std::array<std::size_t, 41> population_{};
    std::array<double, 41> deaths_{}, exposure_{};
    std::array<std::uint64_t, 41> exposureAt_{};
    std::uint64_t commandTick_ = 0;
    double totalExposure_ = 0.0;
    double totalDeaths_ = 0.0;
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
    void rebuildServiceValue() {
        if (demandMass_ == 0) {
            serviceValue_.fill(0.0);
            return;
        }
        std::array<double, 41> probability{};
        std::array<std::uint32_t, 41> cumulative{};
        const double inverseMass =
            1.0 / static_cast<double>(demandMass_);
        for (int k = 1; k <= 40; ++k) {
            probability[k] =
                static_cast<double>(demand_[k]) * inverseMass;
            cumulative[k] = cumulative[k - 1] + demand_[k];
        }
        std::array<double, kMaxScoredGap + 1> previous{};
        std::array<double, kMaxScoredGap + 1> next{};
        // V[h][s]: expected volume served by one gap of capacity s
        // during h IID requests drawn from the observed size profile.
        // Requests that do not fit leave this gap unchanged.
        for (int horizon = 1; horizon <= kHorizon; ++horizon) {
            for (int space = 0; space <= kMaxScoredGap; ++space) {
                const int limit = std::min(kMaxRequest, space);
                const double rejectedProbability =
                    static_cast<double>(
                        demandMass_ - cumulative[limit]) * inverseMass;
                double value = rejectedProbability * previous[space];
                for (int k = 1; k <= limit; ++k) {
                    if (demand_[k] != 0) {
                        value += probability[k] *
                            (static_cast<double>(k) +
                             previous[space - k]);
                    }
                }
                next[space] = value;
            }
            previous.swap(next);
        }
        serviceValue_ = previous;
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
        ++insertions_;
        if constexpr (kUseMixedSequenceDP) {
            if (insertions_ <= 32 || insertions_ % 16 == 0) {
                rebuildServiceValue();
            }
        }
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
        for (int b = 40; b <= kLargeBucket; ++b) {
            fittingGaps += starts_[b].size();
        }
        long double extraLoss = 0.0L;
        for (int k = 40; k >= 1; --k) {
            if (k < 40) fittingGaps += starts_[k].size();
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
        return extraLoss <= 0.0L;
    }
    Coordinate chooseParentFit(int length) const {
        auto candidate = sizes_.lower_bound({length, 0});
        if (candidate == sizes_.end()) return -1;
        if (candidate->first > length) {
            const auto penalty =
                splitPenalty(candidate->first, length);
            if (penalty != 0) {
                const auto larger = sizes_.upper_bound({
                    candidate->first,
                    std::numeric_limits<Coordinate>::max()
                });
                if (larger != sizes_.end() &&
                    splitPenalty(larger->first, length) < penalty &&
                    scarcityAllowsExchange(
                        candidate->first, larger->first, length)) {
                    candidate = larger;
                }
            }
        }
        return candidate->second;
    }
    Coordinate chooseFit(int length) const {
        const Coordinate parentAt = chooseParentFit(length);
        if constexpr (!kUseMixedSequenceDP) {
            return parentAt;
        }
        if (parentAt < 0) return parentAt;
        const Coordinate parentSpace = gaps_.at(parentAt) - parentAt;
        if (parentSpace == length || parentSpace > kMaxScoredGap) {
            return parentAt;
        }
        const auto smallest = sizes_.lower_bound({length, 0});
        const int smallestSpace = static_cast<int>(smallest->first);
        // Threshold-loss weights reproduce the parent's scarcity
        // criterion, while prefix sums make each candidate check O(1).
        std::array<long double, 41> weight{};
        std::array<long double, 41> prefix{};
        std::size_t fittingGaps = 0;
        for (int b = 40; b <= kLargeBucket; ++b) {
            fittingGaps += starts_[b].size();
        }
        for (int k = 40; k >= 1; --k) {
            if (k < 40) fittingGaps += starts_[k].size();
            if (fittingGaps != 0 && demand_[k] != 0) {
                weight[k] =
                    static_cast<long double>(demand_[k]) /
                    static_cast<long double>(fittingGaps);
            }
        }
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + weight[k];
        }
        const auto scarcityLoss = [&](int space) {
            const int upper = std::min(40, space);
            const int lower = std::min(40, space - length);
            return prefix[upper] - prefix[lower];
        };
        const long double allowedLoss = scarcityLoss(smallestSpace);
        const int initialSpace = static_cast<int>(parentSpace);
        Coordinate bestAt = parentAt;
        double bestLoss =
            serviceValue_[initialSpace] -
            serviceValue_[initialSpace - length];
        for (int space = smallestSpace;
             space <= kMaxScoredGap; ++space) {
            if (starts_[space].empty()) continue;
            const double loss =
                serviceValue_[space] -
                serviceValue_[space - length];
            // Preserve the parent's choice on numerical ties.
            if (loss >= bestLoss - 1e-10) continue;
            if (scarcityLoss(space) > allowedLoss) continue;
            bestLoss = loss;
            bestAt = *starts_[space].begin();
        }
        return bestAt;
    }
    double releaseGain(
        Coordinate a, Coordinate remainder, bool rightAligned,
        const std::array<std::uint32_t, 41>& prefix) const {
        auto neighbor = live_.lower_bound(a);
        if (rightAligned) {
            if (neighbor == live_.begin()) return 0.0;
            --neighbor;
        } else if (neighbor == live_.end()) {
            return 0.0;
        }
        const Pipe& p = pipes_[neighbor->second];
        Coordinate releasedSpace = p.length;
        if (releasedSpace >= 40) return 0.0;
        if (rightAligned) {
            auto outside = gaps_.lower_bound(p.start);
            if (outside != gaps_.begin()) {
                --outside;
                if (outside->second == p.start) {
                    releasedSpace += outside->second - outside->first;
                }
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end()) {
                releasedSpace += outside->second - outside->first;
            }
        }
        const int before = static_cast<int>(std::min<Coordinate>(
            40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(std::min<Coordinate>(
            40, remainder + releasedSpace));
        if (before == after) return 0.0;
        return releaseRate(p.length) *
            static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(
        int length, Coordinate& at, bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0.0) return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40) return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k) {
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        }
        const auto end = sizes_.upper_bound({
            space, std::numeric_limits<Coordinate>::max()
        });
        const std::array<Coordinate, 2> candidates{
            at, std::prev(end)->second
        };
        double best = 0.0;
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
    static int bucket(Coordinate length) {
        return static_cast<int>(
            std::min<Coordinate>(kLargeBucket, length));
    }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b - a, a});
        starts_[bucket(b - a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b - a, a});
        starts_[bucket(b - a)].erase(a);
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
        Coordinate at = chooseFit(length);
        Coordinate digs = 0;
        bool rightAligned = false;
        selectReleasePlacement(length, at, rightAligned);
        // chooseFit searches the global size index before growth.
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
        if (rightAligned) at = finish - length;
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