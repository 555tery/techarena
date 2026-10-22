#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <optional>
#include <map>
#include <set>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kHistoryWindow = 2048;
constexpr std::int64_t kUnfitPenaltyScale = 60;
constexpr int kRightEdgeMaxPipeLength = 4;
constexpr std::size_t kSameLengthRightRun = 46;

struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    std::int64_t birthPlacement = 0;
};

constexpr std::int64_t kLifetimeBinWidth = 16;
constexpr std::size_t kLifetimeBucketCount = 12501;
constexpr std::int64_t kMaxLifetime = 200000;
constexpr std::int64_t kHazardHorizon = 64;
constexpr int kMinimumAtRiskSamples = 16;

struct HazardEstimate {
    bool known = false;
    double probability = 0.0;
};

class Allocator {
public:
    // Free spans are half-open [start, end). The map supports merging after a
    // removal; the set chooses the shortest fitting span, then the lowest start.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::map<std::int64_t, std::int64_t> activeByStart;
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::array<std::vector<int>, 41> lifetimeFenwick;
    std::array<int, 41> lifetimeSamples{};
    std::int64_t placementCount = 0;
    std::int64_t trenchLength = 0;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};

    Allocator() {
        for (auto& tree : lifetimeFenwick) {
            tree.assign(kLifetimeBucketCount + 1U, 0);
        }
    }

    void place(int length) {
        std::int64_t start = -1;
        const auto gap = bestFittingGap(length);
        if (gap != freeByStart.end()) {
            start = consumeAtStart(gap, length);
        }

        std::int64_t digs = 0;
        if (start < 0) {
            // No existing span fits. Continue from the left edge of the free
            // tail, retaining its unused part as the new expandable tail.
            auto tail = tailGap();
            const std::int64_t tailStart = tail == freeByStart.end()
                ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands can arrive. Each pipe has length at most
            // 40 m, so it can require at most two 20 m sections: total digging
            // is at most 8,000,000 m, below the 100,000,000 m contest cap.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newLength;
            start = tailStart;
            const std::int64_t remainderStart = start + length;
            if (remainderStart < trenchLength) {
                addFreeGap(remainderStart, trenchLength);
            }
        }

        printPlacement(digs, start);
        ++placementCount;
        const std::int64_t pid = static_cast<std::int64_t>(pipes.size());
        pipes.push_back(Pipe{start, length, true, placementCount});
        activeByStart.emplace(start, pid);
        recordLength(length);
    }

    void remove(std::int64_t pid) {
        if (pid <= 0) {
            printInvalidPidFallback();
            return;
        }
        const std::uint64_t unsignedPid = static_cast<std::uint64_t>(pid);
        if (unsignedPid >= static_cast<std::uint64_t>(pipes.size())) {
            printInvalidPidFallback();
            return;
        }
        // The range check above makes this signed-to-unsigned index conversion safe.
        const std::size_t index = static_cast<std::size_t>(unsignedPid);
        if (!pipes[index].active) {
            printInvalidPidFallback();
            return;
        }

        const Pipe pipe = pipes[index];
        std::cout << pipe.start << '\n' << std::flush;
        pipes[index].active = false;
        activeByStart.erase(pipe.start);
        observeLifetime(pipe.length, placementCount - pipe.birthPlacement);
        addFreeGap(pipe.start, pipe.start + pipe.length);
    }

private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    StartIter tailGap() {
        if (freeByStart.empty()) return freeByStart.end();
        auto it = std::prev(freeByStart.end());
        return it->second == trenchLength ? it : freeByStart.end();
    }

    StartIter bestFittingGap(int length) {
        auto it = freeBySize.lower_bound({length, 0});
        if (it == freeBySize.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        while (it != freeBySize.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            std::int64_t score = slack * historySize;
            if (slack > 0 && slack <= 40) {
                int misses = 0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                    misses += recentFrequency[static_cast<std::size_t>(request)];
                }
                score += kUnfitPenaltyScale * misses;
            }

            // Iteration is by size and then start, so keeping the first tie
            // implements the smaller-gap, then lower-address tie-break.
            if (score < bestScore) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = freeBySize.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
        }
        return best;
    }

    bool hasSameLengthRecentRun(int length) const {
        if (recentLengths.size() < kSameLengthRightRun) return false;
        auto it = recentLengths.rbegin();
        for (std::size_t seen = 0; seen < kSameLengthRightRun; ++seen, ++it) {
            if (*it != length) return false;
        }
        return true;
    }

    std::optional<std::int64_t> medianLifetime(int length, std::int64_t age) const {
        const std::size_t lengthIndex = static_cast<std::size_t>(length);
        if (lifetimeSamples[lengthIndex] < kMinimumAtRiskSamples) return std::nullopt;
        const std::int64_t clampedAge = std::clamp<std::int64_t>(age, 0, kMaxLifetime);
        const std::size_t lowBucket = static_cast<std::size_t>(clampedAge / kLifetimeBinWidth);
        const int below = lifetimePrefix(lengthIndex, lowBucket);
        const int atRisk = lifetimeSamples[lengthIndex] - below;
        if (atRisk < kMinimumAtRiskSamples) return std::nullopt;
        const int target = below + (atRisk + 1) / 2;
        std::size_t low = lowBucket;
        std::size_t high = kLifetimeBucketCount - 1U;
        while (low < high) {
            const std::size_t middle = low + (high - low) / 2U;
            if (lifetimePrefix(lengthIndex, middle + 1U) >= target) high = middle;
            else low = middle + 1U;
        }
        const std::int64_t median = static_cast<std::int64_t>(low) * kLifetimeBinWidth +
            kLifetimeBinWidth / 2;
        return std::max<std::int64_t>(0, median - clampedAge);
    }

    std::optional<bool> survivalPreferredRight(std::int64_t start, std::int64_t end,
        int newLength) const {
        const std::optional<std::int64_t> newMedian = medianLifetime(newLength, 0);
        if (!newMedian.has_value()) return std::nullopt;
        std::optional<std::int64_t> leftRemaining;
        std::optional<std::int64_t> rightRemaining;
        const auto rightIt = activeByStart.lower_bound(end);
        if (rightIt != activeByStart.end() && rightIt->first == end) {
            const std::size_t pid = static_cast<std::size_t>(rightIt->second);
            const Pipe& pipe = pipes[pid];
            rightRemaining = medianLifetime(pipe.length,
                placementCount - pipe.birthPlacement);
        } else if (end == trenchLength) {
            rightRemaining = 0;
        }

        const auto atOrAfterStart = activeByStart.lower_bound(start);
        if (atOrAfterStart != activeByStart.begin()) {
            const auto leftIt = std::prev(atOrAfterStart);
            const std::size_t pid = static_cast<std::size_t>(leftIt->second);
            const Pipe& pipe = pipes[pid];
            if (leftIt->first + pipe.length == start) {
                leftRemaining = medianLifetime(pipe.length,
                    placementCount - pipe.birthPlacement);
            }
        } else if (start == 0) {
            leftRemaining = 0;
        }
        if (!leftRemaining.has_value() || !rightRemaining.has_value()) return std::nullopt;
        const std::int64_t leftDistance = std::llabs(*newMedian - *leftRemaining);
        const std::int64_t rightDistance = std::llabs(*newMedian - *rightRemaining);
        if (leftDistance + 16 < rightDistance) return false;
        if (rightDistance + 16 < leftDistance) return true;
        return std::nullopt;
    }

    HazardEstimate estimateHazard(int length, std::int64_t age) const {
        HazardEstimate estimate;
        const std::size_t lengthIndex = static_cast<std::size_t>(length);
        if (lifetimeSamples[lengthIndex] < kMinimumAtRiskSamples) return estimate;
        const std::int64_t clampedAge = std::clamp<std::int64_t>(age, 0, kMaxLifetime);
        const std::size_t firstBucket = static_cast<std::size_t>(clampedAge / kLifetimeBinWidth);
        const std::int64_t horizonEnd = std::min(kMaxLifetime, clampedAge + kHazardHorizon);
        const std::size_t lastBucket = static_cast<std::size_t>(horizonEnd / kLifetimeBinWidth);
        const int below = lifetimePrefix(lengthIndex, firstBucket);
        const int throughHorizon = lifetimePrefix(lengthIndex, lastBucket + 1U);
        const int atRisk = lifetimeSamples[lengthIndex] - below;
        if (atRisk < kMinimumAtRiskSamples) return estimate;
        const int events = throughHorizon - below;
        estimate.known = true;
        estimate.probability = static_cast<double>(events) / static_cast<double>(atRisk);
        return estimate;
    }

    int lifetimePrefix(std::size_t length, std::size_t bucketCount) const {
        int result = 0;
        std::size_t index = bucketCount;
        while (index > 0U) {
            result += lifetimeFenwick[length][index];
            index -= index & (~index + 1U);
        }
        return result;
    }

    void observeLifetime(int length, std::int64_t age) {
        const std::size_t lengthIndex = static_cast<std::size_t>(length);
        const std::int64_t clampedAge = std::clamp<std::int64_t>(age, 0, kMaxLifetime);
        const std::size_t bucket = static_cast<std::size_t>(clampedAge / kLifetimeBinWidth);
        std::size_t index = bucket + 1U;
        while (index < lifetimeFenwick[lengthIndex].size()) {
            ++lifetimeFenwick[lengthIndex][index];
            index += index & (~index + 1U);
        }
        ++lifetimeSamples[lengthIndex];
    }

    std::int64_t consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const bool baselineRight = length <= kRightEdgeMaxPipeLength
            || hasSameLengthRecentRun(length);
        const std::optional<bool> predictedRight = survivalPreferredRight(start, end, length);
        const bool placeRight = predictedRight.value_or(baselineRight);
        const std::int64_t placementStart = placeRight
            ? end - static_cast<std::int64_t>(length) : start;
        eraseGap(it);
        if (start < placementStart) addFreeGap(start, placementStart);
        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);
        if (placementEnd < end) addFreeGap(placementEnd, end);
        return placementStart;
    }

    void recordLength(int length) {
        recentLengths.push_back(length);
        ++recentFrequency[static_cast<std::size_t>(length)];
        if (recentLengths.size() > kHistoryWindow) {
            --recentFrequency[static_cast<std::size_t>(recentLengths.front())];
            recentLengths.pop_front();
        }
    }

    void eraseGap(StartIter it) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        freeBySize.erase({end - start, start});
        freeByStart.erase(it);
    }

    void addFreeGap(std::int64_t start, std::int64_t end) {
        if (start >= end) return;
        auto it = freeByStart.lower_bound(start);
        if (it != freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                start = previous->first;
                end = std::max(end, previous->second);
                eraseGap(previous);
                it = freeByStart.lower_bound(start);
            }
        }
        while (it != freeByStart.end() && it->first <= end) {
            end = std::max(end, it->second);
            auto next = it++;
            eraseGap(next);
        }
        freeByStart.emplace(start, end);
        freeBySize.emplace(end - start, start);
    }

    static void printPlacement(std::int64_t digs, std::int64_t start) {
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }

    static void printInvalidPidFallback() {
        // Contest inputs guarantee an active PID. This keeps a malformed input
        // from causing an out-of-bounds access while preserving protocol shape.
        std::cout << 0 << '\n' << std::flush;
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) return 0;
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
    }
    return 0;
}
