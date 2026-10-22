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
NAME: bellman_ties_release_edge
DESCRIPTION:
Preserve the parent's one-insert growth comparisons and
adjacent-release edge selection. Use the donor's two-insert
Bellman forecast only when the one-insert costs are equal.
If both forecasts tie, preserve the smaller-region rule.
The forecast uses the last 512 insertion lengths plus a unit
prior for lengths 1..40. Internal gap multiplicities are exact;
sizes >=80 are aggregated only inside the forecast.
No hypothetical deletions or future commands are observed.
Complexity: O(log Q + 40) per insert, O(log Q) per delete,
O(Q) memory. Deletions and correlated requests can invalidate
the forecast's assumptions.
Same-parent ablation: disable enableBellmanTieBreak_.
All other decisions and maintained indexes remain unchanged.
*/
class Allocator {
    static constexpr bool enableBellmanTieBreak_ = true;
    struct Pipe {
        int start;
        int length;
    };
    using AddressIndex = std::map<int, int>;
    using SizeIndex = std::set<std::pair<int, int>>;
    AddressIndex freeByAddress_;
    SizeIndex freeBySize_;
    AddressIndex liveByAddress_;
    std::array<int, 81> holeCount_{};
    std::vector<Pipe> pipes_;
    int trenchLength_ = 0;
    int frontier_ = 0;
    std::array<int, 41> frequency_{};
    std::array<int, 41> massAbove_{};
    std::array<int, 512> recent_{};
    std::size_t recentCount_ = 0;
    std::size_t recentCursor_ = 0;
    void rememberLength(int length) {
        if (recentCount_ == recent_.size()) {
            --frequency_[recent_[recentCursor_]];
        } else {
            ++recentCount_;
        }
        recent_[recentCursor_] = length;
        recentCursor_ = (recentCursor_ + 1) % recent_.size();
        ++frequency_[length];
        massAbove_[40] = 0;
        for (int bound = 39; bound >= 0; --bound) {
            massAbove_[bound] =
                massAbove_[bound + 1] + frequency_[bound + 1];
        }
    }
    int predictedGrowth(int largestHole, int suffixLength) const {
        // Each request needs at most two additional sections.
        const int firstThreshold =
            std::min(40, std::max(largestHole, suffixLength));
        const int secondThreshold =
            std::min(40, std::max(largestHole, suffixLength + 20));
        return massAbove_[firstThreshold] + massAbove_[secondThreshold];
    }
    std::int64_t predictedTwoGrowth(
        const std::array<int, 81>& counts, int suffixLength) const {
        // One region of length >=80 can serve both requests.
        if (counts[80] != 0 || suffixLength >= 80) {
            return 0;
        }
        std::array<int, 41> bestFit{};
        int largest = 0;
        int second = 0;
        int nearest = 0;
        for (int size = 80; size >= 1; --size) {
            if (counts[size] != 0) {
                nearest = size;
                if (largest == 0) {
                    largest = size;
                    if (counts[size] >= 2) {
                        second = size;
                    }
                } else if (second == 0) {
                    second = size;
                }
            }
            if (size <= 40) {
                bestFit[size] = nearest;
            }
        }
        if (second >= 40 ||
            (largest >= 40 && suffixLength >= 40)) {
            return 0;
        }
        const int totalMass = massAbove_[0];
        std::int64_t cost = 0;
        for (int nextLength = 1; nextLength <= 40; ++nextLength) {
            const int fit = bestFit[nextLength];
            int nextCost = 0;
            if (fit != 0) {
                int largestAfter = largest;
                if (fit == largest && counts[fit] == 1) {
                    largestAfter = std::max(
                        second, fit - nextLength);
                }
                nextCost = predictedGrowth(
                    largestAfter, suffixLength);
                if (suffixLength >= nextLength) {
                    nextCost = std::min(
                        nextCost,
                        predictedGrowth(
                            largest, suffixLength - nextLength));
                }
            } else {
                int remaining = suffixLength - nextLength;
                int sections = 0;
                if (remaining < 0) {
                    sections = (-remaining + 19) / 20;
                    remaining += sections * 20;
                }
                nextCost = sections * totalMass +
                    predictedGrowth(largest, remaining);
            }
            cost += static_cast<std::int64_t>(
                frequency_[nextLength]) * nextCost;
        }
        // Common denominator: totalMass squared.
        return cost;
    }
    int largestHoleExcept(int firstStart, int secondStart) const {
        for (auto it = freeBySize_.rbegin(); it != freeBySize_.rend();
             ++it) {
            if (it->second != firstStart && it->second != secondStart) {
                return it->first;
            }
        }
        return 0;
    }
    bool preferRightEdge(int holeStart, int holeLength, int length) const {
        const int remainder = holeLength - length;
        const int suffixLength = trenchLength_ - frontier_;
        if (remainder == 0 || remainder >= 40 || suffixLength >= 40 ||
            largestHoleExcept(holeStart, -1) >= 40) {
            return false;
        }
        const auto right =
            liveByAddress_.lower_bound(holeStart + holeLength);
        const auto benefit = [&](AddressIndex::const_iterator neighbor,
                                 bool leftSide) {
            const int end = neighbor->first + neighbor->second;
            if (!leftSide && end == frontier_) {
                const int largest = largestHoleExcept(holeStart, -1);
                const int newSuffix = suffixLength + neighbor->second;
                return predictedGrowth(std::max(largest, remainder),
                                       newSuffix) -
                       predictedGrowth(largest, newSuffix + remainder);
            }
            int joinedLength = neighbor->second;
            int outerStart = -1;
            if (leftSide) {
                const auto next =
                    freeByAddress_.lower_bound(neighbor->first);
                if (next != freeByAddress_.begin()) {
                    const auto outer = std::prev(next);
                    if (outer->first + outer->second == neighbor->first) {
                        outerStart = outer->first;
                        joinedLength += outer->second;
                    }
                }
            } else {
                const auto outer = freeByAddress_.find(end);
                if (outer != freeByAddress_.end()) {
                    outerStart = outer->first;
                    joinedLength += outer->second;
                }
            }
            const int largest = largestHoleExcept(holeStart, outerStart);
            const int separateCost = predictedGrowth(
                std::max({largest, remainder, joinedLength}),
                suffixLength);
            const int joinedCost = predictedGrowth(
                std::max(largest, joinedLength + remainder),
                suffixLength);
            return separateCost - joinedCost;
        };
        int leftBenefit = 0;
        if (right != liveByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == holeStart) {
                leftBenefit = benefit(left, true);
            }
        }
        int rightBenefit = 0;
        if (right != liveByAddress_.end() &&
            right->first == holeStart + holeLength) {
            rightBenefit = benefit(right, false);
        }
        return leftBenefit > rightBenefit;
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        freeByAddress_.emplace(start, length);
        freeBySize_.emplace(length, start);
        ++holeCount_[std::min(80, length)];
    }
    void eraseHole(AddressIndex::iterator it) {
        --holeCount_[std::min(80, it->second)];
        freeBySize_.erase(std::make_pair(it->second, it->first));
        freeByAddress_.erase(it);
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        frequency_.fill(1);
        frequency_[0] = 0;
        pipes_.reserve(200001);
        pipes_.push_back(Pipe{0, 0});
    }
    void place(int length) {
        rememberLength(length);
        const int suffixLength = trenchLength_ - frontier_;
        const auto fit = freeBySize_.lower_bound(
            std::make_pair(length, 0));
        bool useHole = fit != freeBySize_.end();
        if (useHole && suffixLength >= length) {
            const auto largest = std::prev(freeBySize_.end());
            const int largestBefore = largest->first;
            int largestAfter = largestBefore;
            if (fit == largest) {
                largestAfter = 0;
                if (largest != freeBySize_.begin()) {
                    largestAfter = std::prev(largest)->first;
                }
            }
            largestAfter = std::max(
                largestAfter, fit->first - length);
            const int holeCost =
                predictedGrowth(largestAfter, suffixLength);
            const int suffixCost =
                predictedGrowth(largestBefore, suffixLength - length);
            if (holeCost != suffixCost) {
                useHole = holeCost < suffixCost;
            } else {
                useHole = fit->first <= suffixLength;
                if constexpr (enableBellmanTieBreak_) {
                    auto afterHole = holeCount_;
                    --afterHole[std::min(80, fit->first)];
                    const int remainder = fit->first - length;
                    if (remainder > 0) {
                        ++afterHole[std::min(80, remainder)];
                    }
                    const std::int64_t holeTwoCost =
                        predictedTwoGrowth(afterHole, suffixLength);
                    const std::int64_t suffixTwoCost =
                        predictedTwoGrowth(
                            holeCount_, suffixLength - length);
                    if (holeTwoCost != suffixTwoCost) {
                        useHole = holeTwoCost < suffixTwoCost;
                    }
                }
            }
        }
        int start = 0;
        int sections = 0;
        if (useHole) {
            const int holeLength = fit->first;
            const int holeStart = fit->second;
            const bool atRight =
                preferRightEdge(holeStart, holeLength, length);
            start = atRight ? holeStart + holeLength - length : holeStart;
            eraseHole(freeByAddress_.find(holeStart));
            addHole(atRight ? holeStart : holeStart + length,
                    holeLength - length);
        } else {
            start = frontier_;
            const int shortage = start + length - trenchLength_;
            if (shortage > 0) {
                sections = (shortage + 19) / 20;
                trenchLength_ += sections * 20;
            }
            frontier_ = start + length;
        }
        liveByAddress_.emplace(start, length);
        pipes_.push_back(Pipe{start, length});
        std::cout << sections << ' ' << start << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        const Pipe old = pipes_[static_cast<std::size_t>(pid)];
        liveByAddress_.erase(old.start);
        int start = old.start;
        int length = old.length;
        const auto right = freeByAddress_.lower_bound(start);
        if (right != freeByAddress_.begin()) {
            const auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                eraseHole(left);
            }
        }
        if (right != freeByAddress_.end() &&
            start + length == right->first) {
            length += right->second;
            eraseHole(right);
        }
        if (start + length == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, length);
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