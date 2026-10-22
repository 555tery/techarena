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
// NAME: endpoint_demand_unlock
// DESCRIPTION: Preserve parent size selection and capacity-guarded tail.
// Compare both placement edges at the first and last addresses of the
// selected bin using demand newly served by an adjacent release.
// Ablation: kEnableEndpointUnlock=false restores parent placements.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    static constexpr bool kEnableEndpointUnlock = true;
    static constexpr long double kHazardPriorReleases = 2.0L;
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
    std::array<std::int64_t, kMaxLength + 1> demandPrefix_{};
    std::int64_t totalWeight_ = 0;
    // Exposure is accumulated in live-pipe command steps.
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
        demandPrefix_[0] = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            weights_[k] = observations_[k] + 1;
            const std::int64_t weight = weights_[k];
            totalWeight_ += weight;
            demandPrefix_[k] = demandPrefix_[k - 1] + weight * k;
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
        return tailCost < holeCost;
    }
    // Called only for a selected hole smaller than kSmallLimit.
    int largestOtherHole(int selectedSize) const {
        if (!large_.empty()) {
            return large_.rbegin()->first;
        }
        std::uint64_t low = lowMask_;
        std::uint64_t high = highMask_;
        if (bins_[selectedSize].size() == 1) {
            if (selectedSize < 64) {
                low &= ~(std::uint64_t{1} << selectedSize);
            } else {
                high &= ~(std::uint64_t{1} << (selectedSize - 64));
            }
        }
        if (high != 0) {
            return 64 + 63 - std::countl_zero(high);
        }
        return low == 0 ? 0 : 63 - std::countl_zero(low);
    }
    long double unlockScore(
        const Pipe& neighbor,
        int outerFree,
        int residual,
        int available,
        long double priorExposure) const {
        // Without joining the residual, this release already creates
        // an interval containing the neighbor and its outer free space.
        const int base = neighbor.length + outerFree;
        const int lower =
            std::min(kMaxLength, std::max(available, base));
        const int upper =
            std::min(kMaxLength, base + residual);
        if (upper <= lower) {
            return 0.0L;
        }
        const std::int64_t unlockedDemand =
            demandPrefix_[upper] - demandPrefix_[lower];
        const long double rate =
            (static_cast<long double>(
                 releasesByLength_[neighbor.length])
             + kHazardPriorReleases)
            / (exposureAt(neighbor.length) + priorExposure);
        return rate * static_cast<long double>(unlockedDemand);
    }
    // Returns {original hole start, actual pipe start}.
    std::pair<int, int> choosePlacement(
        int initialStart, int size, int length) const {
        std::pair<int, int> best{initialStart, initialStart};
        const int residual = size - length;
        if (!kEnableEndpointUnlock ||
            residual == 0 ||
            residual >= kMaxLength ||
            totalReleases_ == 0) {
            return best;
        }
        // residual < 40 and length <= 40 imply size < 80.
        const int available = std::max(
            residual,
            std::max(trench_ - frontier_, largestOtherHole(size)));
        if (available >= kMaxLength) {
            return best;
        }
        const long double priorExposure =
            kHazardPriorReleases * totalExposure_
            / static_cast<long double>(totalReleases_);
        long double bestScore = 0.0L;
        const auto considerPlacement =
            [&](int holeStart, int pipeStart, long double score) {
                const std::pair<int, int> candidate{
                    holeStart, pipeStart};
                if (score > bestScore ||
                    (score == bestScore && candidate < best)) {
                    bestScore = score;
                    best = candidate;
                }
            };
        const auto considerHole = [&](int holeStart) {
            const auto right = live_.lower_bound(holeStart);
            // Place at the left edge, leaving the residual on the right.
            long double rightScore = 0.0L;
            if (right != live_.end()) {
                const Pipe& neighbor = pipes_[right->second];
                if (neighbor.start == holeStart + size) {
                    const int neighborEnd =
                        neighbor.start + neighbor.length;
                    int outerFree = 0;
                    if (neighborEnd == frontier_) {
                        outerFree = trench_ - frontier_;
                    } else {
                        const auto outer = holes_.find(neighborEnd);
                        if (outer != holes_.end()) {
                            outerFree = outer->second;
                        }
                    }
                    rightScore = unlockScore(
                        neighbor, outerFree, residual,
                        available, priorExposure);
                }
            }
            considerPlacement(holeStart, holeStart, rightScore);
            // Place at the right edge, leaving the residual on the left.
            long double leftScore = 0.0L;
            if (right != live_.begin()) {
                const auto left = std::prev(right);
                const Pipe& neighbor = pipes_[left->second];
                if (neighbor.start + neighbor.length == holeStart) {
                    int outerFree = 0;
                    const auto afterOuter =
                        holes_.lower_bound(neighbor.start);
                    if (afterOuter != holes_.begin()) {
                        const auto outer = std::prev(afterOuter);
                        if (outer->first + outer->second ==
                            neighbor.start) {
                            outerFree = outer->second;
                        }
                    }
                    leftScore = unlockScore(
                        neighbor, outerFree, residual,
                        available, priorExposure);
                }
            }
            considerPlacement(
                holeStart, holeStart + residual, leftScore);
        };
        const auto& bin = bins_[size];
        const int first = *bin.begin();
        const int last = *bin.rbegin();
        considerHole(first);
        if (last != first) {
            considerHole(last);
        }
        return best;
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
        if (chosen.first >= 0 &&
            !preferFreeTail(length, chosen.second)) {
            const int size = chosen.second;
            const auto placement =
                choosePlacement(chosen.first, size, length);
            const int holeStart = placement.first;
            start = placement.second;
            eraseHole(holes_.find(holeStart));
            if (start == holeStart) {
                addHole(start + length, size - length);
            } else {
                addHole(holeStart, size - length);
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