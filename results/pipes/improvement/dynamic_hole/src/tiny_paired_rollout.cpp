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

constexpr std::size_t kObservedWindow = 256;
constexpr std::size_t kRolloutHorizon = 4;
constexpr std::size_t kRolloutScenarios = 2;
constexpr std::size_t kMinimumPairedSamples = 12;
constexpr std::size_t kMinimumBoundarySamples = 8;
constexpr std::int64_t kRequiredPairedGain = 2;

struct ObservedAllocation {
    std::int64_t serial = 0;
    int length = 0;
    std::int64_t lifetime = 0;
    bool completed = false;
};

struct SimPipe {
    std::int64_t start = 0;
    int length = 0;
    std::int64_t deathAt = 0;
    bool active = true;
};

class Allocator {
public:
    // Free spans are half-open [start, end). The map supports merging after a
    // removal; the set chooses the shortest fitting span, then the lowest start.
    std::map<std::int64_t, std::int64_t> freeByStart;
    std::set<std::pair<std::int64_t, std::int64_t>> freeBySize;
    std::map<std::int64_t, std::int64_t> activeByStart;
    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::array<ObservedAllocation, kObservedWindow> observed{};
    std::int64_t placementCount = 0;
    std::int64_t trenchLength = 0;
    std::deque<int> recentLengths;
    std::array<int, 41> recentFrequency{};

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
        const std::size_t slot = static_cast<std::size_t>(placementCount %
            static_cast<std::int64_t>(kObservedWindow));
        observed[slot] = ObservedAllocation{placementCount, length, 0, false};
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
        const std::size_t slot = static_cast<std::size_t>(pipe.birthPlacement %
            static_cast<std::int64_t>(kObservedWindow));
        if (observed[slot].serial == pipe.birthPlacement) {
            observed[slot].lifetime = placementCount - pipe.birthPlacement;
            observed[slot].completed = true;
        }
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

    static int sizeClass(int length) {
        if (length <= 4) return 0;
        if (length <= 8) return 1;
        if (length <= 16) return 2;
        if (length <= 32) return 3;
        return 4;
    }

    std::vector<ObservedAllocation> recentCompleted() const {
        std::vector<ObservedAllocation> result;
        const std::int64_t first = std::max<std::int64_t>(1,
            placementCount - static_cast<std::int64_t>(kObservedWindow) + 1);
        for (std::int64_t serial = first; serial <= placementCount; ++serial) {
            const std::size_t slot = static_cast<std::size_t>(serial %
                static_cast<std::int64_t>(kObservedWindow));
            if (observed[slot].serial == serial && observed[slot].completed) {
                result.push_back(observed[slot]);
            }
        }
        return result;
    }

    static std::int64_t quantileLifetime(std::vector<std::int64_t> values,
        std::size_t scenario) {
        std::sort(values.begin(), values.end());
        const std::size_t quartile = values.size() / 4U;
        const std::size_t index = scenario == 0U
            ? quartile : std::min(values.size() - 1U, 3U * quartile);
        return values[index];
    }

    static std::int64_t sampleRemaining(const std::vector<ObservedAllocation>& completed,
        int length, std::int64_t age, std::size_t scenario) {
        std::vector<std::int64_t> eligible;
        const int targetClass = sizeClass(length);
        for (const ObservedAllocation& item : completed) {
            if (sizeClass(item.length) == targetClass && item.lifetime >= age) {
                eligible.push_back(item.lifetime - age);
            }
        }
        if (eligible.size() < kMinimumBoundarySamples) return -1;
        return quantileLifetime(std::move(eligible), scenario);
    }

    static std::int64_t sampleNewLifetime(const std::vector<ObservedAllocation>& completed,
        int length, std::size_t scenario) {
        std::vector<std::int64_t> eligible;
        const int targetClass = sizeClass(length);
        for (const ObservedAllocation& item : completed) {
            if (sizeClass(item.length) == targetClass) eligible.push_back(item.lifetime);
        }
        if (eligible.size() < kMinimumPairedSamples) return -1;
        return quantileLifetime(std::move(eligible), scenario);
    }

    static std::int64_t simulateLocalRollout(std::int64_t localLength,
        std::int64_t gapStart, std::int64_t gapEnd, int currentLength,
        bool currentRight, std::int64_t currentLifetime,
        int leftLength, std::int64_t leftRemaining,
        int rightLength, std::int64_t rightRemaining,
        const std::vector<ObservedAllocation>& events) {
        std::vector<SimPipe> localPipes;
        if (leftLength > 0) localPipes.push_back(SimPipe{0, leftLength, leftRemaining, true});
        if (rightLength > 0) {
            localPipes.push_back(SimPipe{gapEnd, rightLength, rightRemaining, true});
        }
        const std::int64_t currentStart = currentRight
            ? gapEnd - static_cast<std::int64_t>(currentLength) : gapStart;
        localPipes.push_back(SimPipe{currentStart, currentLength, currentLifetime, true});

        const auto expireBefore = [&localPipes](std::int64_t time) {
            for (SimPipe& pipe : localPipes) {
                if (pipe.active && pipe.deathAt < time) pipe.active = false;
            }
        };
        const auto expireThrough = [&localPipes](std::int64_t time) {
            for (SimPipe& pipe : localPipes) {
                if (pipe.active && pipe.deathAt <= time) pipe.active = false;
            }
        };
        const auto placeLocal = [&localPipes, localLength](int requestLength) {
            std::vector<const SimPipe*> ordered;
            for (const SimPipe& pipe : localPipes) {
                if (pipe.active) ordered.push_back(&pipe);
            }
            std::sort(ordered.begin(), ordered.end(), [](const SimPipe* a, const SimPipe* b) {
                return a->start < b->start;
            });
            std::int64_t cursor = 0;
            std::int64_t bestStart = -1;
            std::int64_t bestLength = std::numeric_limits<std::int64_t>::max();
            const auto consider = [&bestStart, &bestLength, requestLength](
                std::int64_t first, std::int64_t last) {
                const std::int64_t gapLength = last - first;
                if (gapLength >= requestLength && gapLength < bestLength) {
                    bestStart = first;
                    bestLength = gapLength;
                }
            };
            for (const SimPipe* pipe : ordered) {
                consider(cursor, pipe->start);
                cursor = std::max(cursor, pipe->start + pipe->length);
            }
            consider(cursor, localLength);
            if (bestStart < 0) return false;
            const std::int64_t placementStart = requestLength <= kRightEdgeMaxPipeLength
                ? bestStart + bestLength - requestLength : bestStart;
            // Placeholder deathAt is replaced by the caller after insertion.
            localPipes.push_back(SimPipe{placementStart, requestLength, 0, true});
            return true;
        };

        std::int64_t misses = 0;
        for (std::size_t step = 0; step < events.size(); ++step) {
            const std::int64_t time = static_cast<std::int64_t>(step + 1U);
            expireBefore(time);
            if (!placeLocal(events[step].length)) {
                misses += events[step].length;
            } else {
                localPipes.back().deathAt = time + events[step].lifetime;
            }
            expireThrough(time);
        }
        return misses;
    }

    std::optional<bool> rolloutPreferredRight(std::int64_t start, std::int64_t end,
        int length) const {
        const std::vector<ObservedAllocation> completed = recentCompleted();
        if (completed.size() < 2U * kRolloutHorizon) return std::nullopt;
        const std::int64_t newLifetime0 = sampleNewLifetime(completed, length, 0U);
        const std::int64_t newLifetime1 = sampleNewLifetime(completed, length, 1U);
        if (newLifetime0 < 0 || newLifetime1 < 0) return std::nullopt;

        int leftLength = 0;
        int rightLength = 0;
        std::int64_t leftStart = start;
        std::int64_t rightStart = end;
        std::vector<std::int64_t> leftRemaining(kRolloutScenarios, 0);
        std::vector<std::int64_t> rightRemaining(kRolloutScenarios, 0);
        const auto atOrAfterStart = activeByStart.lower_bound(start);
        if (atOrAfterStart != activeByStart.begin()) {
            const auto leftIt = std::prev(atOrAfterStart);
            const std::size_t pid = static_cast<std::size_t>(leftIt->second);
            const Pipe& pipe = pipes[pid];
            if (leftIt->first + pipe.length == start) {
                leftLength = pipe.length;
                leftStart = leftIt->first;
                for (std::size_t scenario = 0; scenario < kRolloutScenarios; ++scenario) {
                    leftRemaining[scenario] = sampleRemaining(completed, pipe.length,
                        placementCount - pipe.birthPlacement, scenario);
                    if (leftRemaining[scenario] < 0) return std::nullopt;
                }
            }
        }
        const auto rightIt = activeByStart.lower_bound(end);
        if (rightIt != activeByStart.end() && rightIt->first == end) {
            const std::size_t pid = static_cast<std::size_t>(rightIt->second);
            const Pipe& pipe = pipes[pid];
            rightLength = pipe.length;
            rightStart = rightIt->first;
            for (std::size_t scenario = 0; scenario < kRolloutScenarios; ++scenario) {
                rightRemaining[scenario] = sampleRemaining(completed, pipe.length,
                    placementCount - pipe.birthPlacement, scenario);
                if (rightRemaining[scenario] < 0) return std::nullopt;
            }
        }

        std::array<std::vector<ObservedAllocation>, kRolloutScenarios> events;
        const std::size_t firstEvent = completed.size() - 2U * kRolloutHorizon;
        for (std::size_t scenario = 0; scenario < kRolloutScenarios; ++scenario) {
            const std::size_t firstForScenario = firstEvent + scenario * kRolloutHorizon;
            for (std::size_t j = 0; j < kRolloutHorizon; ++j) {
                events[scenario].push_back(completed[firstForScenario + j]);
            }
        }

        const std::int64_t origin = leftLength > 0 ? leftStart : start;
        const std::int64_t localEnd = rightLength > 0
            ? rightStart + rightLength : end;
        const std::int64_t localLength = localEnd - origin;
        const std::int64_t localGapStart = start - origin;
        const std::int64_t localGapEnd = end - origin;
        int leftWins = 0;
        int rightWins = 0;
        std::int64_t leftTotal = 0;
        std::int64_t rightTotal = 0;
        for (std::size_t scenario = 0; scenario < kRolloutScenarios; ++scenario) {
            const std::int64_t currentLifetime = scenario == 0U
                ? newLifetime0 : newLifetime1;
            const std::int64_t leftCost = simulateLocalRollout(localLength,
                localGapStart, localGapEnd, length, false, currentLifetime,
                leftLength, leftRemaining[scenario], rightLength,
                rightRemaining[scenario], events[scenario]);
            const std::int64_t rightCost = simulateLocalRollout(localLength,
                localGapStart, localGapEnd, length, true, currentLifetime,
                leftLength, leftRemaining[scenario], rightLength,
                rightRemaining[scenario], events[scenario]);
            leftTotal += leftCost;
            rightTotal += rightCost;
            if (leftCost < rightCost) ++leftWins;
            else if (rightCost < leftCost) ++rightWins;
        }
        if (leftWins == static_cast<int>(kRolloutScenarios) &&
            rightTotal - leftTotal >= kRequiredPairedGain) return false;
        if (rightWins == static_cast<int>(kRolloutScenarios) &&
            leftTotal - rightTotal >= kRequiredPairedGain) return true;
        return std::nullopt;
    }

    std::int64_t consumeAtStart(StartIter it, int length) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const bool baselineRight = length <= kRightEdgeMaxPipeLength
            || hasSameLengthRecentRun(length);
        const std::optional<bool> rolloutRight = rolloutPreferredRight(start, end, length);
        const bool placeRight = rolloutRight.value_or(baselineRight);
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
