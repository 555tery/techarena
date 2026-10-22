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
// NAME: horizon_confirmed_scarcity
// DESCRIPTION: Confirm scarcity exchanges by exact static three-request
// packing costs on eight causal, marginally stratified scenarios.
// Preserve residual-fit on ties and retain exposure-guided splitting.
// Ablation: kEnableHorizonConfirmation=false restores the current parent.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kEnableExposureSplit = true;
    static constexpr bool kEnableScarceCapacityExchange = true;
    static constexpr bool kEnableHorizonConfirmation = true;
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
    // Homogeneous capacity of internal holes; the tail is added on demand.
    std::array<std::int64_t, kMaxLength + 1> holeCapacity_{};
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
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] += length / k;
            }
        }
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
        if constexpr (kEnableScarceCapacityExchange) {
            for (int k = 1; k <= kMaxLength; ++k) {
                holeCapacity_[k] -= length / k;
            }
        }
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
    std::pair<int, int> chooseScarcityExchange(
        int length, std::pair<int, int> parent) const {
        if (!kEnableScarceCapacityExchange ||
            parent.first < 0 || parent.second == length) {
            return parent;
        }
        std::pair<int, int> bestFit = parent;
        const std::uint64_t fittingLow =
            lowMask_ & (~std::uint64_t{0} << length);
        if (fittingLow != 0) {
            const int size = std::countr_zero(fittingLow);
            bestFit = {*bins_[size].begin(), size};
        } else if (highMask_ != 0) {
            const int size = 64 + std::countr_zero(highMask_);
            bestFit = {*bins_[size].begin(), size};
        } else if (!large_.empty()) {
            const auto candidate = *large_.begin();
            bestFit = {candidate.second, candidate.first};
        }
        if (bestFit.second >= parent.second) {
            return parent;
        }
        const int tail = trench_ - frontier_;
        const std::int64_t freeVolume = holeCapacity_[1] + tail;
        long double difference =
            static_cast<long double>(totalWeight_)
            * (std::min(bestFit.second - length, kMaxLength)
               - std::min(parent.second - length, kMaxLength));
        for (int k = 2; k <= kMaxLength; ++k) {
            const int remainder = length % k;
            if (remainder == 0) {
                continue;
            }
            // For s >= length, splitting loses an extra homogeneous
            // slot precisely when s % k < length % k.
            const int carryDifference =
                static_cast<int>(bestFit.second % k < remainder)
                - static_cast<int>(parent.second % k < remainder);
            if (carryDifference == 0) {
                continue;
            }
            const std::int64_t capacity =
                holeCapacity_[k] + tail / k;
            const std::int64_t pooledCapacity = freeVolume / k;
            // Different carry indicators imply a hole of size >= k,
            // hence capacity is positive. Pooled capacity is >= capacity.
            const long double penalty =
                static_cast<long double>(kRegretScale)
                * static_cast<long double>(weights_[k]) * k
                * static_cast<long double>(pooledCapacity)
                / static_cast<long double>(capacity);
            difference += carryDifference * penalty;
        }
        return difference < 0.0L ? bestFit : parent;
    }
    static int horizonSections(
        const std::array<int, 3>& holes, int tail,
        const std::array<int, 3>& request) {
        // Requests and hole capacities are sorted in descending order.
        const int total = request[0] + request[1] + request[2];
        int best = (std::max(0, total - tail) + 19) / 20;
        if (best == 0) {
            return 0;
        }
        // Each subset is assigned to internal holes; its complement
        // is appended to the existing tail.
        for (int mask = 7; mask != 0; --mask) {
            std::array<int, 3> packed{};
            int count = 0;
            int tailUsed = 0;
            for (int i = 0; i < 3; ++i) {
                if ((mask & (1 << i)) != 0) {
                    packed[count++] = request[i];
                } else {
                    tailUsed += request[i];
                }
            }
            const int sections =
                (std::max(0, tailUsed - tail) + 19) / 20;
            if (sections >= best) {
                continue;
            }
            bool fits;
            if (count == 1) {
                fits = holes[0] >= packed[0];
            } else if (count == 2) {
                fits = holes[0] >= packed[0] + packed[1]
                    || (holes[0] >= packed[0]
                        && holes[1] >= packed[1]);
            } else {
                const int a = packed[0];
                const int b = packed[1];
                const int c = packed[2];
                // Enumerate all five partitions of three requests.
                fits = holes[0] >= a + b + c
                    || (holes[0] >= a + b && holes[1] >= c)
                    || (holes[0] >= a + c && holes[1] >= b)
                    || (holes[0] >= std::max(a, b + c)
                        && holes[1] >= std::min(a, b + c))
                    || (holes[0] >= a && holes[1] >= b
                        && holes[2] >= c);
            }
            if (fits) {
                best = sections;
                if (best == 0) {
                    return 0;
                }
            }
        }
        return best;
    }
    std::pair<int, int> confirmScarcityExchange(
        int length, std::pair<int, int> parent,
        std::pair<int, int> exchange) const {
        if (!kEnableHorizonConfirmation || exchange == parent) {
            return exchange;
        }
        const int tail = trench_ - frontier_;
        if (tail >= 3 * kMaxLength) {
            return parent;
        }
        // Removing one chosen hole requires at most four original
        // holes to recover the three largest remaining capacities.
        std::array<std::pair<int, int>, 4> largest{};
        int count = 0;
        for (auto it = large_.rbegin();
             it != large_.rend() && count < 4; ++it) {
            largest[count++] = {it->second, it->first};
        }
        for (int size = kSmallLimit - 1;
             size > 0 && count < 4; --size) {
            for (auto it = bins_[size].begin();
                 it != bins_[size].end() && count < 4; ++it) {
                largest[count++] = {*it, size};
            }
        }
        const auto remaining = [&](std::pair<int, int> choice) {
            std::array<int, 5> sizes{};
            int used = 0;
            for (int i = 0; i < count; ++i) {
                if (largest[i].first != choice.first) {
                    sizes[used++] = largest[i].second;
                }
            }
            sizes[used++] = choice.second - length;
            std::sort(sizes.begin(), sizes.end(),
                      [](int a, int b) { return a > b; });
            return std::array<int, 3>{sizes[0], sizes[1], sizes[2]};
        };
        const auto parentHoles = remaining(parent);
        const auto exchangeHoles = remaining(exchange);
        if (parentHoles == exchangeHoles) {
            return parent;
        }
        std::array<int, 8> q{};
        int size = 1;
        std::int64_t cumulative = weights_[1];
        for (int i = 0; i < 8; ++i) {
            const std::int64_t target =
                (totalWeight_ * (2 * i + 1) + 15) / 16;
            while (size < kMaxLength && cumulative < target) {
                cumulative += weights_[++size];
            }
            q[i] = size;
        }
        std::array<std::array<int, 3>, 8> scenarios{};
        for (int i = 0; i < 4; ++i) {
            const int repeated = q[2 * i + 1];
            scenarios[2 * i] = {repeated, repeated, repeated};
            scenarios[2 * i + 1] = {
                q[2 * i],
                q[2 * ((i + 1) % 4)],
                q[2 * ((i + 3) % 4)]
            };
        }
        int parentCost = 0;
        int exchangeCost = 0;
        for (auto request : scenarios) {
            std::sort(request.begin(), request.end(),
                      [](int a, int b) { return a > b; });
            parentCost += horizonSections(parentHoles, tail, request);
            exchangeCost += horizonSections(exchangeHoles, tail, request);
        }
        return exchangeCost < parentCost ? exchange : parent;
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
        const auto parent = chooseHole(length);
        const auto chosen = confirmScarcityExchange(
            length, parent, chooseScarcityExchange(length, parent));
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