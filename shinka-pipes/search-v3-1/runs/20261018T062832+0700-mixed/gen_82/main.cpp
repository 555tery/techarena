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
        Coordinate start;
        int length;
    };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    std::array<std::uint32_t, 41> demand_{};
    std::uint32_t demandMass_ = 0;
    std::map<Coordinate, std::size_t> live_;
    std::array<std::size_t, 41> population_{};
    std::array<double, 41> deaths_{}, exposure_{};
    std::array<std::uint64_t, 41> exposureAt_{};
    std::uint64_t commandTick_ = 0;
    double totalExposure_ = 0;
    double totalDeaths_ = 0;
    struct GrowthState {
        std::array<int, 3> interior{};
        int tail = 0;
    };
    struct Scenario {
        std::array<int, 3> lengths{};
        int weight = 0;
    };
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
        const double pooledRate = totalDeaths_ / (totalExposure_ + 1.0);
        return (deaths_[length] + 8.0 * pooledRate) / (exposure + 8.0);
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
    static int horizonCapacity(Coordinate capacity) {
        // Three requests have total length at most 120.
        return static_cast<int>(std::min<Coordinate>(120, capacity));
    }
    static void retainLargest(GrowthState& state, int capacity) {
        for (int& existing : state.interior) {
            if (capacity > existing)
                std::swap(capacity, existing);
        }
    }
    static int sectionsFor(int length, int available) {
        return length <= available ? 0 : (length - available + 19) / 20;
    }
    static int pairGrowth(const std::array<int, 3>& interior,
                          int tail, int x, int y) {
        int largest = 0;
        int second = 0;
        for (int capacity : interior) {
            if (capacity >= largest) {
                second = largest;
                largest = capacity;
            } else if (capacity > second) {
                second = capacity;
            }
        }
        const int bigger = std::max(x, y);
        const int smaller = std::min(x, y);
        // Exhaustive zero-growth packings of two requests.
        if (largest >= x + y ||
            tail >= x + y ||
            (largest >= bigger && second >= smaller) ||
            (largest >= x && tail >= y) ||
            (largest >= y && tail >= x)) {
            return 0;
        }
        // A fitting first request forbids growth. Since no zero-growth
        // packing exists, the second request must then extend the tail.
        if (largest >= x)
            return sectionsFor(y, tail);
        if (tail >= x)
            return sectionsFor(y, tail - x);
        // No gap fits x: extending the tail is mandatory.
        const int firstGrowth = sectionsFor(x, tail);
        tail += firstGrowth * 20 - x;
        if (largest >= y || tail >= y)
            return firstGrowth;
        return firstGrowth + sectionsFor(y, tail);
    }
    static int tripleGrowth(GrowthState state,
                            const std::array<int, 3>& lengths) {
        const int x = lengths[0];
        const int y = lengths[1];
        const int z = lengths[2];
        const int total = x + y + z;
        if (state.tail >= total)
            return 0;
        for (int capacity : state.interior) {
            if (capacity >= total)
                return 0;
        }
        int best = 7;
        bool foundFit = false;
        // Enumerate every distinct fitting interior capacity for x.
        for (int i = 0; i < 3; ++i) {
            const int capacity = state.interior[i];
            if (capacity < x)
                continue;
            bool duplicate = false;
            for (int j = 0; j < i; ++j) {
                if (state.interior[j] == capacity) {
                    duplicate = true;
                    break;
                }
            }
            if (duplicate)
                continue;
            foundFit = true;
            state.interior[i] -= x;
            best = std::min(
                best, pairGrowth(state.interior, state.tail, y, z));
            state.interior[i] += x;
            if (best == 0)
                return 0;
        }
        if (state.tail >= x) {
            foundFit = true;
            best = std::min(
                best, pairGrowth(state.interior, state.tail - x, y, z));
        }
        if (foundFit)
            return best;
        const int growth = sectionsFor(x, state.tail);
        state.tail += growth * 20 - x;
        return growth + pairGrowth(state.interior, state.tail, y, z);
    }
    std::array<Scenario, 8> makeScenarios(int& count) const {
        std::array<int, 8> quantiles{};
        int length = 1;
        std::uint32_t cumulative = demand_[length];
        for (int i = 0; i < 8; ++i) {
            const std::uint32_t target =
                ((2 * i + 1) * demandMass_ + 15) / 16;
            while (length < 40 && cumulative < target) {
                ++length;
                cumulative += demand_[length];
            }
            quantiles[i] = length;
        }
        std::array<Scenario, 8> scenarios{};
        count = 0;
        const auto append = [&](std::array<int, 3> lengths) {
            for (int i = 0; i < count; ++i) {
                if (scenarios[i].lengths == lengths) {
                    ++scenarios[i].weight;
                    return;
                }
            }
            scenarios[count].lengths = lengths;
            scenarios[count].weight = 1;
            ++count;
        };
        for (int i = 0; i < 4; ++i) {
            const int q = quantiles[2 * i + 1];
            append({q, q, q});
        }
        for (int i = 0; i < 4; ++i) {
            append({
                quantiles[2 * i],
                quantiles[2 * ((i + 1) % 4)],
                quantiles[2 * ((i + 3) % 4)]
            });
        }
        return scenarios;
    }
    void selectHorizonPlacement(int length, Coordinate& at) {
        if (at < 0 || gaps_.at(at) - at == length)
            return;
        Coordinate tailAt = -1;
        Coordinate tailSpace = 0;
        if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
            tailAt = gaps_.rbegin()->first;
            tailSpace = trench_ - tailAt;
        }
        std::array<Coordinate, 4> candidates{};
        int candidateCount = 0;
        const auto appendCandidate = [&](Coordinate candidate) {
            if (candidate < 0)
                return;
            for (int i = 0; i < candidateCount; ++i) {
                if (candidates[i] == candidate)
                    return;
            }
            if (candidateCount < static_cast<int>(candidates.size()))
                candidates[candidateCount++] = candidate;
        };
        // Keep the parent's decision first, so every tie preserves it.
        appendCandidate(at);
        const auto first = sizes_.lower_bound({length, 0});
        if (first != sizes_.end()) {
            appendCandidate(first->second);
            const auto second = sizes_.upper_bound({
                first->first, std::numeric_limits<Coordinate>::max()
            });
            if (second != sizes_.end())
                appendCandidate(second->second);
        }
        if (tailSpace >= length)
            appendCandidate(tailAt);
        if (candidateCount < 2)
            return;
        // Even consuming 40 units leaves enough tail for all three requests.
        if (tailSpace >= 160)
            return;
        // Four are needed here because the current insertion can remove one.
        std::array<std::pair<Coordinate, Coordinate>, 4> largest{};
        int largestCount = 0;
        for (auto it = sizes_.rbegin();
             it != sizes_.rend() && largestCount < 4; ++it) {
            if (it->second != tailAt)
                largest[largestCount++] = *it;
        }
        // Every candidate leaves three gaps that fit arbitrary requests.
        if (largestCount == 4 && largest[3].first >= 40)
            return;
        int scenarioCount = 0;
        const auto scenarios = makeScenarios(scenarioCount);
        const auto score = [&](Coordinate candidate, int cutoff) {
            GrowthState state;
            state.tail = horizonCapacity(tailSpace);
            for (int i = 0; i < largestCount; ++i) {
                if (largest[i].second != candidate)
                    retainLargest(state, horizonCapacity(largest[i].first));
            }
            const Coordinate remainder =
                gaps_.at(candidate) - candidate - length;
            if (candidate == tailAt)
                state.tail = horizonCapacity(remainder);
            else
                retainLargest(state, horizonCapacity(remainder));
            int result = 0;
            for (int i = 0; i < scenarioCount; ++i) {
                ++mcRolloutsRun;
                result += scenarios[i].weight *
                          tripleGrowth(state, scenarios[i].lengths);
                if (result >= cutoff)
                    break;
            }
            return result;
        };
        ++mcDecisionsUsed;
        // Eight scenarios, each requiring at most six additional sections.
        int bestScore = score(at, 49);
        if (bestScore == 0)
            return;
        Coordinate bestAt = at;
        for (int i = 1; i < candidateCount; ++i) {
            const int candidateScore = score(candidates[i], bestScore);
            if (candidateScore < bestScore) {
                bestScore = candidateScore;
                bestAt = candidates[i];
                if (bestScore == 0)
                    break;
            }
        }
        at = bestAt;
    }
    std::uint64_t splitPenalty(Coordinate space, int length) const {
        std::uint64_t result = 0;
        for (int k = 1; k <= 40; ++k) {
            if (demand_[k] != 0 && space % k < length % k)
                result += static_cast<std::uint64_t>(demand_[k]) * k;
        }
        return result;
    }
    bool scarcityAllowsExchange(Coordinate smaller, Coordinate larger,
                                int length) const {
        std::size_t fittingGaps = 0;
        long double extraLoss = 0;
        for (int k = 40; k >= 1; --k) {
            fittingGaps += starts_[k].size();
            if (demand_[k] == 0 || fittingGaps == 0)
                continue;
            const int smallerLoses =
                smaller >= k && smaller - length < k;
            const int largerLoses =
                larger >= k && larger - length < k;
            if (smallerLoses != largerLoses) {
                extraLoss += static_cast<long double>(demand_[k]) /
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
            if (neighbor == live_.begin())
                return 0;
            --neighbor;
        } else if (neighbor == live_.end()) {
            return 0;
        }
        const Pipe& p = pipes_[neighbor->second];
        Coordinate releasedSpace = p.length;
        if (releasedSpace >= 40)
            return 0;
        if (rightAligned) {
            auto outside = gaps_.lower_bound(p.start);
            if (outside != gaps_.begin()) {
                --outside;
                if (outside->second == p.start)
                    releasedSpace += outside->second - outside->first;
            }
        } else {
            const auto outside = gaps_.find(p.start + p.length);
            if (outside != gaps_.end())
                releasedSpace += outside->second - outside->first;
        }
        const int before = static_cast<int>(std::min<Coordinate>(
            40, std::max(remainder, releasedSpace)));
        const int after = static_cast<int>(std::min<Coordinate>(
            40, remainder + releasedSpace));
        if (before == after)
            return 0;
        return releaseRate(p.length) *
               static_cast<double>(prefix[after] - prefix[before]);
    }
    void selectReleasePlacement(int length, Coordinate& at,
                                bool& rightAligned) const {
        if (at < 0 || totalDeaths_ == 0)
            return;
        const Coordinate space = gaps_.at(at) - at;
        const Coordinate remainder = space - length;
        if (remainder <= 0 || remainder >= 40)
            return;
        std::array<std::uint32_t, 41> prefix{};
        for (int k = 1; k <= 40; ++k)
            prefix[k] = prefix[k - 1] + demand_[k] * k;
        const auto end = sizes_.upper_bound({
            space, std::numeric_limits<Coordinate>::max()
        });
        const std::array<Coordinate, 2> candidates{
            at, std::prev(end)->second
        };
        double best = 0;
        for (std::size_t i = 0; i < candidates.size(); ++i) {
            if (i != 0 && candidates[i] == candidates[0])
                continue;
            const Coordinate a = candidates[i];
            for (int side = 0; side < 2; ++side) {
                if (side != 0 && a + space == trench_)
                    continue;
                const double value =
                    releaseGain(a, remainder, side != 0, prefix);
                if (value > best) {
                    best = value;
                    at = a;
                    rightAligned = side != 0;
                }
            }
        }
    }
    static int bucket(Coordinate n) {
        return static_cast<int>(std::min<Coordinate>(40, n));
    }
    void add(Coordinate a, Coordinate b) {
        if (a >= b)
            return;
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
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        advanceReleaseClock();
        observeLength(length);
        Coordinate at = -1;
        Coordinate digs = 0;
        if constexpr (false) {
            for (int k = length; k <= 40; ++k) {
                if (!starts_[k].empty() &&
                    (at < 0 || *starts_[k].begin() < at)) {
                    at = *starts_[k].begin();
                }
            }
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) {
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
                at = candidate->second;
            }
        }
        selectHorizonPlacement(length, at);
        bool rightAligned = false;
        selectReleasePlacement(length, at, rightAligned);
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
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
        if (rightAligned)
            at = finish - length;
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