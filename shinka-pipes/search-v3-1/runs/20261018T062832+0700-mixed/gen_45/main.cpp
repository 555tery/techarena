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
namespace {
using Coordinate = std::int64_t;
using SizeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr bool kUseGlobalPackingForecast = true;
constexpr int kForecastHorizon = 8;
constexpr int kForecastScenarios = 4;
constexpr int kForecastCapacity = 40 * kForecastHorizon;
constexpr int kMaskWords = kForecastCapacity / 64 + 1;
constexpr int kDistinctCandidateSizes = 8;
constexpr int kMaximumCandidates = 12;
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    std::uint64_t freeSince = 0;
};
struct Candidate {
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    bool tail = false;
};
struct Change {
    int capacity = 0;
    int delta = 0;
};
// Capacities above the complete forecast volume are interchangeable:
// any one of them can accommodate the entire remaining forecast.
struct Inventory {
    std::array<int, kForecastCapacity + 1> count{};
    std::array<std::uint64_t, kMaskWords> mask{};
    void change(int capacity, int delta) {
        if (capacity <= 0) return;
        int& value = count[static_cast<std::size_t>(capacity)];
        value += delta;
        const std::size_t word =
            static_cast<std::size_t>(capacity >> 6);
        const std::uint64_t bit =
            std::uint64_t{1} << (capacity & 63);
        if (value == 0) {
            mask[word] &= ~bit;
        } else {
            mask[word] |= bit;
        }
    }
    int firstFit(int length) const {
        int word = length >> 6;
        std::uint64_t available =
            mask[static_cast<std::size_t>(word)] &
            (~std::uint64_t{0} << (length & 63));
        while (true) {
            if (available != 0) {
                return word * 64 +
                    static_cast<int>(std::countr_zero(available));
            }
            ++word;
            if (word >= kMaskWords) return 0;
            available = mask[static_cast<std::size_t>(word)];
        }
    }
};
class Allocator {
public:
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        ++tick_;
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        observeLength(length);
        refreshModel(newlyObservedLength);
        Coordinate digs = 0;
        Coordinate chosenStart = 0;
        // Growth is allowed only after checking the complete size index.
        const auto firstFit = bySize_.lower_bound({length, {0, 0}});
        if (firstFit == bySize_.end()) {
            ++expansionGateOpportunities;
            Coordinate start = trenchLength_;
            std::uint64_t freeSince = tick_;
            const auto tail = tailGap();
            if (tail != gaps_.end()) {
                start = tail->first;
                freeSince = tail->second.freeSince;
                eraseGap(tail);
            }
            const Coordinate available = trenchLength_ - start;
            const Coordinate deficit =
                std::max<Coordinate>(0, length - available);
            digs =
                (deficit + kSectionLength - 1) / kSectionLength;
            trenchLength_ += digs * kSectionLength;
            insertGap(start, trenchLength_, freeSince);
            chosenStart = start;
        } else {
            chosenStart = chooseGap(length);
        }
        const auto selected = gaps_.find(chosenStart);
        const Gap gap = selected->second;
        eraseGap(selected);
        // The vector index is the insertion PID.
        pipes_.push_back(Pipe{chosenStart, length, true});
        // Exact-length allocation, anchored at the low end.
        insertGap(
            chosenStart + length, gap.end, gap.freeSince);
        std::cout << digs << ' ' << chosenStart << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const std::size_t pid = static_cast<std::size_t>(pidValue);
        if (!pipes_[pid].active) {
            printInvalidPid();
            return;
        }
        ++tick_;
        const Pipe pipe = pipes_[pid];
        Coordinate start = pipe.start;
        Coordinate end = pipe.start + pipe.length;
        auto right = gaps_.lower_bound(start);
        if (right != gaps_.begin()) {
            const auto left = std::prev(right);
            if (left->second.end == start) {
                start = left->first;
                eraseGap(left);
            }
        }
        right = gaps_.lower_bound(end);
        if (right != gaps_.end() && right->first == end) {
            end = right->second.end;
            eraseGap(right);
        }
        pipes_[pid].active = false;
        insertGap(start, end, tick_);
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    using Scenarios = std::array<
        std::array<int, kForecastHorizon>, kForecastScenarios>;
    GapMap gaps_;
    std::set<SizeKey> bySize_;
    std::vector<Pipe> pipes_{Pipe{}};
    // The expandable tail is represented separately during forecasts.
    Inventory interiorInventory_;
    Coordinate trenchLength_ = 0;
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, 41> requestPrefix_{};
    // Internal sampling state; independent of case identifiers or raw input.
    std::uint64_t randomState_ = 0x243f6a8885a308d3ULL;
    static int capacityBucket(Coordinate capacity) {
        return static_cast<int>(
            std::min<Coordinate>(capacity, kForecastCapacity));
    }
    static bool candidateLess(
        const Candidate& a, const Candidate& b) {
        if (a.span != b.span) return a.span < b.span;
        if (a.tail != b.tail) return !a.tail;
        if (a.freeSince != b.freeSince) {
            return a.freeSince < b.freeSince;
        }
        return a.start < b.start;
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_
            ? last : gaps_.end();
    }
    void insertGap(
        Coordinate start, Coordinate end,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, freeSince});
        bySize_.insert({end - start, {freeSince, start}});
        if (end != trenchLength_) {
            interiorInventory_.change(
                capacityBucket(end - start), 1);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const Coordinate span = gap.end - start;
        if (gap.end != trenchLength_) {
            interiorInventory_.change(capacityBucket(span), -1);
        }
        bySize_.erase({span, {gap.freeSince, start}});
        gaps_.erase(position);
    }
    void observeLength(int length) {
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) {
            return;
        }
        haveModel_ = true;
        modelTick_ = tick_;
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        requestPrefix_[0] = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index =
                static_cast<std::size_t>(length);
            const double probability =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            requestPrefix_[index] =
                requestPrefix_[index - 1] + probability;
        }
        requestPrefix_[40] = 1.0;
    }
    std::uint64_t nextRandom() {
        randomState_ += 0x9e3779b97f4a7c15ULL;
        std::uint64_t value = randomState_;
        value = (value ^ (value >> 30)) *
            0xbf58476d1ce4e5b9ULL;
        value = (value ^ (value >> 27)) *
            0x94d049bb133111ebULL;
        return value ^ (value >> 31);
    }
    double unitRandom() {
        return static_cast<double>(nextRandom() >> 11) *
            (1.0 / 9007199254740992.0);
    }
    int sampleLength(double quantile) const {
        const auto found = std::lower_bound(
            requestPrefix_.begin() + 1,
            requestPrefix_.end(), quantile);
        return static_cast<int>(
            found - requestPrefix_.begin());
    }
    Scenarios makeScenarios() {
        Scenarios scenarios{};
        // Stratification reduces sampling noise. Every candidate receives
        // exactly the same scenarios for this real insertion.
        for (int step = 0; step < kForecastHorizon; ++step) {
            std::array<int, kForecastScenarios> order{};
            for (int i = 0; i < kForecastScenarios; ++i) {
                order[static_cast<std::size_t>(i)] = i;
            }
            for (int i = kForecastScenarios - 1; i > 0; --i) {
                const int j = static_cast<int>(
                    nextRandom() %
                    static_cast<std::uint64_t>(i + 1));
                std::swap(
                    order[static_cast<std::size_t>(i)],
                    order[static_cast<std::size_t>(j)]);
            }
            for (int stratum = 0;
                 stratum < kForecastScenarios; ++stratum) {
                const double quantile =
                    (stratum + unitRandom()) /
                    static_cast<double>(kForecastScenarios);
                const int scenario =
                    order[static_cast<std::size_t>(stratum)];
                scenarios[static_cast<std::size_t>(scenario)]
                         [static_cast<std::size_t>(step)] =
                    sampleLength(quantile);
            }
        }
        return scenarios;
    }
    static void recordChange(
        Inventory& inventory, int capacity, int delta,
        Change* undo, int& undoCount) {
        if (capacity <= 0) return;
        inventory.change(capacity, delta);
        undo[undoCount++] = Change{capacity, delta};
    }
    static void restore(
        Inventory& inventory, const Change* undo,
        int undoCount) {
        while (undoCount > 0) {
            const Change change = undo[--undoCount];
            inventory.change(change.capacity, -change.delta);
        }
    }
    static unsigned forecastGrowth(
        Inventory& inventory, int tailCapacity,
        const std::array<int, kForecastHorizon>& requests) {
        std::array<Change, 2 * kForecastHorizon> undo{};
        int undoCount = 0;
        // At most two sections per request. Terminal growth must
        // dominate every possible prefix-area difference summed
        // across all scenarios; timing only breaks terminal ties.
        constexpr unsigned primaryScale =
            1U + static_cast<unsigned>(
                kForecastScenarios * kForecastHorizon *
                (kForecastHorizon + 1));
        unsigned sections = 0;
        unsigned prefixArea = 0;
        for (int length : requests) {
            const int capacity = inventory.firstFit(length);
            // Virtual successor policy: global best-fit, preferring an
            // interior gap when its capacity ties the expandable tail.
            if (capacity != 0 &&
                (tailCapacity < length ||
                 capacity <= tailCapacity)) {
                recordChange(
                    inventory, capacity, -1,
                    undo.data(), undoCount);
                recordChange(
                    inventory, capacity - length, 1,
                    undo.data(), undoCount);
            } else if (tailCapacity >= length) {
                tailCapacity -= length;
            } else {
                const int deficit = length - tailCapacity;
                const int digs =
                    (deficit + static_cast<int>(kSectionLength) - 1) /
                    static_cast<int>(kSectionLength);
                sections += static_cast<unsigned>(digs);
                tailCapacity +=
                    digs * static_cast<int>(kSectionLength) - length;
            }
            prefixArea += sections;
        }
        restore(inventory, undo.data(), undoCount);
        return sections * primaryScale + prefixArea;
    }
    Coordinate chooseGap(int length) {
        std::array<Candidate, kMaximumCandidates> candidates{};
        int candidateCount = 0;
        const auto addCandidate = [&](Coordinate start) {
            for (int i = 0; i < candidateCount; ++i) {
                if (candidates[static_cast<std::size_t>(i)].start ==
                    start) {
                    return;
                }
            }
            if (candidateCount == kMaximumCandidates) return;
            const auto found = gaps_.find(start);
            if (found == gaps_.end()) return;
            const Coordinate span = found->second.end - start;
            if (span < length) return;
            candidates[static_cast<std::size_t>(candidateCount++)] =
                Candidate{
                    start, span, found->second.freeSince,
                    found->second.end == trenchLength_};
        };
        // Equal-span interior gaps are equivalent to the forecast.
        // Retain the oldest representative, plus the distinct tail case.
        const auto addSizeRepresentatives =
            [&](std::set<SizeKey>::const_iterator position) {
                if (position == bySize_.end()) return;
                addCandidate(position->second.second);
                const auto gap = gaps_.find(position->second.second);
                if (gap->second.end == trenchLength_) {
                    const auto next = std::next(position);
                    if (next != bySize_.end() &&
                        next->first == position->first) {
                        addCandidate(next->second.second);
                    }
                }
            };
        auto current = bySize_.lower_bound({length, {0, 0}});
        const Coordinate fallback = current->second.second;
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const Coordinate span = current->first;
            addSizeRepresentatives(current);
            current = bySize_.upper_bound({
                span,
                {std::numeric_limits<std::uint64_t>::max(),
                 std::numeric_limits<Coordinate>::max()}});
        }
        const Coordinate largestSpan = bySize_.rbegin()->first;
        addSizeRepresentatives(
            bySize_.lower_bound({largestSpan, {0, 0}}));
        Coordinate tailSpan = 0;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            tailSpan = tail->second.end - tail->first;
            if (tailSpan >= length) addCandidate(tail->first);
        }
        // The complete size index has already established a fitting gap.
        if (candidateCount == 0) return fallback;
        std::sort(
            candidates.begin(),
            candidates.begin() + candidateCount,
            candidateLess);
        if (!kUseGlobalPackingForecast || candidateCount == 1) {
            return candidates[0].start;
        }
        const Scenarios scenarios = makeScenarios();
        Inventory working = interiorInventory_;
        ++mcDecisionsUsed;
        Coordinate chosenStart = candidates[0].start;
        unsigned bestScore =
            std::numeric_limits<unsigned>::max();
        for (int index = 0; index < candidateCount; ++index) {
            const Candidate& candidate =
                candidates[static_cast<std::size_t>(index)];
            std::array<Change, 2> undo{};
            int undoCount = 0;
            int virtualTail = capacityBucket(tailSpan);
            if (candidate.tail) {
                virtualTail =
                    capacityBucket(candidate.span - length);
            } else {
                recordChange(
                    working, capacityBucket(candidate.span), -1,
                    undo.data(), undoCount);
                recordChange(
                    working,
                    capacityBucket(candidate.span - length), 1,
                    undo.data(), undoCount);
            }
            unsigned score = 0;
            // Such a gap alone fits the complete forecast volume.
            const bool forecastFits =
                virtualTail >= kForecastCapacity ||
                working.count[kForecastCapacity] != 0;
            if (!forecastFits) {
                for (const auto& scenario : scenarios) {
                    score += forecastGrowth(
                        working, virtualTail, scenario);
                    ++mcRolloutsRun;
                    // Candidates are already ordered by the tie-break.
                    // Further nonnegative costs cannot rescue this one.
                    if (score >= bestScore) break;
                }
            }
            restore(working, undo.data(), undoCount);
            if (score < bestScore) {
                bestScore = score;
                chosenStart = candidate.start;
            }
            // Zero is the global minimum; later ties are less preferred.
            if (bestScore == 0) break;
        }
        return chosenStart;
    }
    static void printInvalidPid() {
        std::cout << 0 << '\n' << std::flush;
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