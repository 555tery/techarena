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
using Coord = std::int64_t;
constexpr Coord kSection = 20;
constexpr int kMaxLength = 40;
constexpr std::size_t kHistory = 2048;
constexpr std::size_t kFastHistory = 256;
constexpr std::size_t kCandidates = 6;
constexpr std::size_t kLongRun = 46;
constexpr Coord kNoLimit = std::numeric_limits<Coord>::max() / 4;
struct Pipe {
    Coord start = 0;
    int length = 0;
    int cohort = 0;
    bool active = false;
};
struct Demand {
    std::array<Coord, 41> greater{};
    Coord total = 1;
    Coord cost(Coord size, int length) const {
        const Coord remainder = size - length;
        Coord result = remainder * total;
        if (remainder > 0 && remainder <= kMaxLength) {
            result += 60 * greater[static_cast<std::size_t>(remainder)];
        }
        return result;
    }
};
struct LifeView {
    std::array<int, 41> retention{};
    std::array<bool, 41> learned{};
};
// The tree grows with the PID sequence. Appending a Fenwick node constructs
// its complete covered sum, including insertions made before it existed.
class PidIndex {
public:
    void append() {
        const int index = static_cast<int>(tree_.size());
        const int width = index & -index;
        const int covered = prefix(index - 1) - prefix(index - width);
        tree_.push_back(covered + 1);
        ++active_;
    }
    void erase(int pid) {
        const int limit = static_cast<int>(tree_.size());
        for (int position = pid; position < limit;
             position += position & -position) {
            --tree_[static_cast<std::size_t>(position)];
        }
        --active_;
    }
    int rankFromNewest(int pid) const {
        if (active_ <= 1) return 0;
        const std::size_t newer =
            active_ - static_cast<std::size_t>(prefix(pid));
        return static_cast<int>(newer * 1000 / (active_ - 1));
    }
private:
    int prefix(int index) const {
        int result = 0;
        for (; index > 0; index -= index & -index) {
            result += tree_[static_cast<std::size_t>(index)];
        }
        return result;
    }
    std::vector<int> tree_{0};
    std::size_t active_ = 0;
};
// This is the sole owner of free-space metadata. All changes update the
// address index, size indexes and size counts together.
class GapStore {
public:
    struct Hole {
        Coord start = 0;
        Coord end = 0;
        int owner = -1;
        Coord score = 0;
    };
    struct Range {
        Coord start = 0;
        Coord end = 0;
    };
    void put(Coord start, Coord end, int owner) {
        if (start >= end) return;
        if (owner < 0 || owner > 1) owner = -1;
        auto it = spans_.lower_bound(start);
        if (it != spans_.begin()) {
            auto previous = std::prev(it);
            if (previous->second.end >= start) {
                if (previous->second.owner != owner) owner = -1;
                start = previous->first;
                end = std::max(end, previous->second.end);
                erase(previous);
                it = spans_.lower_bound(start);
            }
        }
        while (it != spans_.end() && it->first <= end) {
            if (it->second.owner != owner) owner = -1;
            end = std::max(end, it->second.end);
            auto victim = it++;
            erase(victim);
        }
        spans_.emplace(start, Span{end, owner});
        const Coord size = end - start;
        all_.emplace(size, start);
        owned_[ownerIndex(owner)].emplace(size, start);
        ++sizeCounts_[size];
    }
    void eraseStart(Coord start) {
        auto it = spans_.find(start);
        if (it != spans_.end()) erase(it);
    }
    std::optional<Hole> tail(Coord trench) const {
        if (spans_.empty()) return std::nullopt;
        const auto it = std::prev(spans_.end());
        if (it->second.end != trench) return std::nullopt;
        return Hole{it->first, it->second.end, it->second.owner, 0};
    }
    Coord consume(Coord gapStart, int length, bool high) {
        auto it = spans_.find(gapStart);
        if (it == spans_.end() || it->second.end - gapStart < length) {
            return -1;
        }
        const Coord start = it->first;
        const Span span = it->second;
        const Coord position = high ? span.end - length : start;
        erase(it);
        if (start < position) put(start, position, span.owner);
        if (position + length < span.end) {
            put(position + length, span.end, span.owner);
        }
        return position;
    }
    // Reservations leave the ordinary free-space index until released.
    std::optional<Range> reserve(Coord bytes) {
        auto it = all_.lower_bound({bytes, 0});
        if (it == all_.end()) return std::nullopt;
        const Coord start = it->second;
        auto address = spans_.find(start);
        const Span span = address->second;
        erase(address);
        put(start + bytes, span.end, span.owner);
        return Range{start, start + bytes};
    }
    // Number of whole requests that free spans can hold, saturated at cap.
    // excluded is a capacity contribution to subtract, typically the tail.
    Coord capacity(int length, Coord cap, Coord excluded = 0) const {
        if (cap <= 0) return 0;
        const Coord target = cap + excluded;
        Coord result = 0;
        for (auto it = sizeCounts_.rbegin(); it != sizeCounts_.rend(); ++it) {
            if (it->first < length) break;
            result += (it->first / length) *
                static_cast<Coord>(it->second);
            if (result >= target) return cap;
        }
        return std::min(cap, std::max<Coord>(0, result - excluded));
    }
    // Only endpoint representatives of each useful size are considered.
    // Neighborhood evaluation is deferred until the shortlist is complete.
    std::vector<Hole> candidates(
        int length, const Demand& demand, bool preferHigh,
        int cohort, bool routing, Coord endLimit = kNoLimit) const {
        std::vector<Hole> result;
        result.reserve(kCandidates + 1);
        const auto better = [preferHigh](const Hole& a, const Hole& b) {
            if (a.score != b.score) return a.score < b.score;
            return preferHigh ? a.start > b.start : a.start < b.start;
        };
        const auto keep = [&](Coord start, Coord size, int owner,
                              Coord surcharge) {
            result.push_back(Hole{
                start, start + size, owner,
                demand.cost(size, length) + surcharge
            });
            std::sort(result.begin(), result.end(), better);
            if (result.size() > kCandidates) result.pop_back();
        };
        const auto scan = [&](const Index& index, int owner,
                              Coord surcharge) {
            auto it = index.lower_bound({length, 0});
            while (it != index.end()) {
                const Coord size = it->first;
                const Coord maximumStart = endLimit - size;
                bool eligible = false;
                if (maximumStart >= 0 && it->second <= maximumStart) {
                    eligible = true;
                    keep(it->second, size, owner, surcharge);
                    auto last = index.upper_bound({size, maximumStart});
                    if (last != index.begin()) {
                        --last;
                        if (last->first == size &&
                            last->second != it->second) {
                            keep(last->second, size, owner, surcharge);
                        }
                    }
                }
                // Above this point there is no remainder penalty, and the
                // size component increases monotonically within this index.
                if (eligible && size - length > kMaxLength) break;
                it = index.upper_bound({
                    size, std::numeric_limits<Coord>::max()
                });
            }
        };
        if (!routing) {
            scan(all_, -1, 0);
        } else {
            // Ownership is advisory: a foreign fitting span can still avoid
            // irreversible growth when preferred space is unavailable.
            scan(owned_[static_cast<std::size_t>(cohort)], cohort, 0);
            scan(owned_[2], -1, 3 * demand.total);
            scan(owned_[static_cast<std::size_t>(cohort ^ 1)],
                 cohort ^ 1, 9 * demand.total);
        }
        return result;
    }
private:
    struct Span {
        Coord end = 0;
        int owner = -1;
    };
    using AddressIndex = std::map<Coord, Span>;
    using Index = std::set<std::pair<Coord, Coord>>;
    static std::size_t ownerIndex(int owner) {
        return owner >= 0 ? static_cast<std::size_t>(owner) : 2;
    }
    void erase(AddressIndex::iterator it) {
        const Coord start = it->first;
        const Coord size = it->second.end - start;
        const int owner = it->second.owner;
        all_.erase({size, start});
        owned_[ownerIndex(owner)].erase({size, start});
        auto count = sizeCounts_.find(size);
        if (--count->second == 0) sizeCounts_.erase(count);
        spans_.erase(it);
    }
    AddressIndex spans_;
    Index all_;
    std::array<Index, 3> owned_;
    std::map<Coord, std::size_t> sizeCounts_;
};
struct PhaseForecast {
    std::size_t expected = 0;
    int deletedParity = 0;
    int nextLength = 0;
};
// All learning is based on completed commands. Exposure includes currently
// live pipes, so lifetime estimates do not use completed lifetimes alone.
class WorkloadModel {
public:
    void tick() {
        if (clock_ != 0 && clock_ % kEpochLength == 0) {
            epoch_ = (epoch_ + 1) % kEpochCount;
            for (int length = 1; length <= kMaxLength; ++length) {
                const auto i = static_cast<std::size_t>(length);
                exposure_[i] -= epochExposure_[epoch_][i];
                deaths_[i] -= epochDeaths_[epoch_][i];
                epochExposure_[epoch_][i] = 0;
                epochDeaths_[epoch_][i] = 0;
            }
            exposureTotal_ -= epochExposureTotal_[epoch_];
            deathTotal_ -= epochDeathTotal_[epoch_];
            epochExposureTotal_[epoch_] = 0;
            epochDeathTotal_[epoch_] = 0;
        }
        ++clock_;
        for (int length = 1; length <= kMaxLength; ++length) {
            const auto i = static_cast<std::size_t>(length);
            exposure_[i] += live_[i];
            epochExposure_[epoch_][i] += live_[i];
        }
        exposureTotal_ += liveTotal_;
        epochExposureTotal_[epoch_] += liveTotal_;
    }
    bool beginRun(int length, int firstPid) {
        if (current_.length == length) return false;
        if (current_.count > 0) {
            completed_.push_back(current_);
            if (completed_.size() > 8) completed_.pop_front();
        }
        current_ = Run{};
        current_.length = length;
        current_.firstPid = firstPid;
        return true;
    }
    int cohort(int length) const {
        return static_cast<int>(
            occurrences_[static_cast<std::size_t>(length)] & 1);
    }
    void inserted(int length) {
        const auto i = static_cast<std::size_t>(length);
        ++occurrences_[i];
        ++live_[i];
        ++liveTotal_;
        ++current_.count;
        recordLength(length);
    }
    void removed(int pid, const Pipe& pipe, int rank) {
        const auto i = static_cast<std::size_t>(pipe.length);
        --live_[i];
        --liveTotal_;
        ++deaths_[i];
        ++epochDeaths_[epoch_][i];
        ++deathTotal_;
        ++epochDeathTotal_[epoch_];
        if (ranks_.size() == 64) {
            removeRank(ranks_.front());
            ranks_.pop_front();
        }
        ranks_.push_back(rank);
        addRank(rank);
        if (lastDeletedPid_ >= 0 &&
            lastDeletedLength_ == pipe.length &&
            pid == lastDeletedPid_ + 2) {
            ++strideTwo_;
        } else {
            strideTwo_ = 0;
            alternating_ = false;
        }
        if (strideTwo_ >= 7) {
            alternating_ = true;
            deletedParity_ = pid & 1;
        }
        lastDeletedPid_ = pid;
        lastDeletedLength_ = pipe.length;
        if (pid >= current_.firstPid) {
            ++current_.deleted[static_cast<std::size_t>(pid & 1)];
        }
        auto& released = cohortDeaths_[i];
        ++released[static_cast<std::size_t>(pipe.cohort)];
        const Coord total = released[0] + released[1];
        if (total >= 8 &&
            std::max(released[0], released[1]) * 100 >= total * 85) {
            cohortEvidence_ = true;
        }
    }
    Demand demand(int currentLength) const {
        Demand result;
        std::array<Coord, 41> weights{};
        if (historySize_ == 0) {
            weights[static_cast<std::size_t>(currentLength)] = 1;
        } else {
            const Coord slow = static_cast<Coord>(historySize_);
            const Coord fast = static_cast<Coord>(
                std::min(historySize_, kFastHistory));
            Coord difference = 0;
            for (int length = 1; length <= kMaxLength; ++length) {
                const auto i = static_cast<std::size_t>(length);
                Coord delta = slowFrequency_[i] * fast -
                    fastFrequency_[i] * slow;
                difference += delta < 0 ? -delta : delta;
            }
            const bool shifted = historySize_ >= kFastHistory &&
                difference * 2 > slow * fast;
            for (int length = 1; length <= kMaxLength; ++length) {
                const auto i = static_cast<std::size_t>(length);
                weights[i] = shifted
                    ? slowFrequency_[i] * fast +
                        3 * fastFrequency_[i] * slow
                    : slowFrequency_[i];
            }
        }
        Coord suffix = 0;
        for (int length = kMaxLength; length >= 0; --length) {
            const auto i = static_cast<std::size_t>(length);
            result.greater[i] = suffix;
            if (length > 0) suffix += weights[i];
        }
        result.total = std::max<Coord>(1, suffix);
        return result;
    }
    LifeView lifetimes() const {
        LifeView result;
        result.retention.fill(512);
        if (deathTotal_ < 48 || exposureTotal_ <= 0) return result;
        const double mean = std::max(
            1.0, static_cast<double>(exposureTotal_) /
                static_cast<double>(deathTotal_));
        for (int length = 1; length <= kMaxLength; ++length) {
            const auto i = static_cast<std::size_t>(length);
            const double exposure = static_cast<double>(exposure_[i]);
            const double deaths = static_cast<double>(deaths_[i]);
            // Shrink sparse classes toward the global deletion intensity.
            const double numerator = exposure + 6.0 * mean;
            const double denominator =
                exposure + (deaths + 12.0) * mean;
            result.retention[i] = std::clamp(
                static_cast<int>(1024.0 * numerator / denominator),
                0, 1024);
            result.learned[i] =
                deaths_[i] >= 8 || exposure >= 16.0 * mean;
        }
        return result;
    }
    bool fifoLike() const {
        return ranks_.size() >= 48 &&
            bottomRanks_ * 100 >= ranks_.size() * 80;
    }
    bool stackLike(int length) const {
        if (length > 8 || liveTotal_ < 128 ||
            ranks_.size() < 48 || historySize_ < 64 ||
            topRanks_ * 100 < ranks_.size() * 80) {
            return false;
        }
        Coord shortCount = 0;
        for (int size = 1; size <= 8; ++size) {
            shortCount += slowFrequency_[static_cast<std::size_t>(size)];
        }
        return shortCount * 100 >=
            static_cast<Coord>(historySize_) * 90;
    }
    bool unitDominant() const {
        return historySize_ >= 128 &&
            slowFrequency_[1] * 100 >=
                static_cast<Coord>(historySize_) * 85;
    }
    int forecastNextSize() const {
        if (completed_.size() < 2) return 0;
        const Run& a = completed_[completed_.size() - 2];
        const Run& b = completed_.back();
        const int length = current_.length;
        if (a.count < kLongRun || b.count < kLongRun ||
            !(a.length < b.length && b.length < length)) {
            return 0;
        }
        int predicted = 0;
        if (b.length - a.length == length - b.length) {
            predicted = length + (length - b.length);
        } else {
            const int product = length * a.length;
            const int square = b.length * b.length;
            const int error = product > square
                ? product - square : square - product;
            if (2 * error <= a.length) {
                predicted =
                    (length * b.length + a.length / 2) / a.length;
            }
        }
        return predicted > length && predicted <= kMaxLength
            ? predicted : 0;
    }
    std::optional<int> deletionParity() const {
        if (completed_.size() >= 2 &&
            forecastNextSize() > current_.length) {
            const int a =
                completed_[completed_.size() - 2].relativeDeletedParity();
            const int b = completed_.back().relativeDeletedParity();
            if (a >= 0 && a == b) {
                return (current_.firstPid & 1) ^ b;
            }
        }
        if (alternating_) return deletedParity_;
        return std::nullopt;
    }
    bool cohortRouting() const {
        return cohortEvidence_ &&
            forecastNextSize() > current_.length;
    }
    bool preferHigh(int length, int pid) const {
        if (stackLike(length)) return true;
        if (fifoLike()) return false;
        if (const auto parity = deletionParity()) {
            return (pid & 1) != *parity;
        }
        if (current_.count >= kLongRun) return (pid & 1) == 0;
        if (cohortRouting()) return cohort(length) == 0;
        return length <= 4;
    }
    std::optional<PhaseForecast> phaseForecast() const {
        if (completed_.size() < 2) return std::nullopt;
        const int next = forecastNextSize();
        const auto parity = deletionParity();
        if (next == 0 || !parity) return std::nullopt;
        const Run& a = completed_[completed_.size() - 2];
        const Run& b = completed_.back();
        const std::size_t difference = a.count > b.count
            ? a.count - b.count : b.count - a.count;
        const std::size_t tolerance = std::max<std::size_t>(
            10, std::max(a.count, b.count) / 10);
        const std::size_t expected = (a.count + b.count) / 2;
        if (expected < 64 || difference > tolerance) {
            return std::nullopt;
        }
        return PhaseForecast{expected, *parity, next};
    }
    std::size_t runCount() const { return current_.count; }
    int firstPid() const { return current_.firstPid; }
private:
    static constexpr std::size_t kEpochCount = 8;
    static constexpr Coord kEpochLength = 256;
    struct Run {
        int length = 0;
        std::size_t count = 0;
        int firstPid = 1;
        std::array<std::size_t, 2> deleted{};
        int relativeDeletedParity() const {
            const std::size_t total = deleted[0] + deleted[1];
            if (total < 8 ||
                std::max(deleted[0], deleted[1]) * 100 < total * 85) {
                return -1;
            }
            const int absolute = deleted[0] > deleted[1] ? 0 : 1;
            return absolute ^ (firstPid & 1);
        }
    };
    void recordLength(int length) {
        if (historySize_ >= kFastHistory) {
            const std::size_t outgoing =
                (historyCursor_ + kHistory - kFastHistory) % kHistory;
            --fastFrequency_[
                static_cast<std::size_t>(history_[outgoing])];
        }
        if (historySize_ == kHistory) {
            --slowFrequency_[
                static_cast<std::size_t>(history_[historyCursor_])];
        } else {
            ++historySize_;
        }
        history_[historyCursor_] = length;
        historyCursor_ = (historyCursor_ + 1) % kHistory;
        ++slowFrequency_[static_cast<std::size_t>(length)];
        ++fastFrequency_[static_cast<std::size_t>(length)];
    }
    void addRank(int rank) {
        if (rank <= 50) ++topRanks_;
        if (rank >= 950) ++bottomRanks_;
    }
    void removeRank(int rank) {
        if (rank <= 50) --topRanks_;
        if (rank >= 950) --bottomRanks_;
    }
    std::array<int, kHistory> history_{};
    std::size_t historyCursor_ = 0;
    std::size_t historySize_ = 0;
    std::array<Coord, 41> slowFrequency_{};
    std::array<Coord, 41> fastFrequency_{};
    std::array<Coord, 41> occurrences_{};
    std::array<std::array<Coord, 2>, 41> cohortDeaths_{};
    std::array<Coord, 41> live_{};
    Coord liveTotal_ = 0;
    Coord clock_ = 0;
    std::size_t epoch_ = 0;
    std::array<std::array<Coord, 41>, kEpochCount> epochExposure_{};
    std::array<std::array<Coord, 41>, kEpochCount> epochDeaths_{};
    std::array<Coord, kEpochCount> epochExposureTotal_{};
    std::array<Coord, kEpochCount> epochDeathTotal_{};
    std::array<Coord, 41> exposure_{};
    std::array<Coord, 41> deaths_{};
    Coord exposureTotal_ = 0;
    Coord deathTotal_ = 0;
    Run current_;
    std::deque<Run> completed_;
    std::deque<int> ranks_;
    std::size_t topRanks_ = 0;
    std::size_t bottomRanks_ = 0;
    bool cohortEvidence_ = false;
    bool alternating_ = false;
    int deletedParity_ = 0;
    int lastDeletedPid_ = -1;
    int lastDeletedLength_ = -1;
    std::size_t strideTwo_ = 0;
};
class Allocator {
public:
    // Retained for the unchanged optional diagnostics in main().
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        model_.tick();
        const int pid = static_cast<int>(pipes_.size());
        Coord digs = 0;
        if (model_.beginRun(length, pid)) {
            closeArena();
            digs += openArena(length, pid);
        }
        const int cohort = model_.cohort(length);
        const Demand demand = model_.demand(length);
        Coord position = -1;
        if (arena_.active) {
            const bool predictedDeleted =
                (pid & 1) == arena_.deletedParity;
            if (!predictedDeleted && arena_.gapSink > 0) {
                const auto choice = chooseGap(
                    length, pid, cohort, false, demand,
                    false, arena_.base);
                if (choice) {
                    position = gaps_.consume(
                        choice->gapStart, length, choice->high);
                    if (position >= 0) --arena_.gapSink;
                }
                if (position < 0) closeArena();
            } else if (arena_.low + length <= arena_.high) {
                if (predictedDeleted) {
                    position = arena_.low;
                    arena_.low += length;
                } else {
                    arena_.high -= length;
                    position = arena_.high;
                }
            } else {
                closeArena();
            }
            if (position >= 0 && arena_.active) {
                ++arena_.used;
                if (arena_.used >= arena_.expected) closeArena();
            }
        }
        if (position < 0) {
            const bool high = model_.preferHigh(length, pid);
            const auto choice = chooseGap(
                length, pid, cohort, high, demand, true, kNoLimit);
            if (choice) {
                position = gaps_.consume(
                    choice->gapStart, length, choice->high);
            }
            if (position < 0) {
                const auto growth = grow(length, cohort, high);
                position = growth.first;
                digs += growth.second;
            }
        }
        pipes_.push_back(Pipe{position, length, cohort, true});
        occupied_.emplace(position, pid);
        pids_.append();
        model_.inserted(length);
        printPlacement(digs, position);
    }
    void remove(std::int64_t pid) {
        model_.tick();
        if (pid <= 0 ||
            static_cast<std::uint64_t>(pid) >=
                static_cast<std::uint64_t>(pipes_.size())) {
            printInvalidPidFallback();
            return;
        }
        const auto index = static_cast<std::size_t>(pid);
        if (!pipes_[index].active) {
            printInvalidPidFallback();
            return;
        }
        const Pipe pipe = pipes_[index];
        const int rank = pids_.rankFromNewest(static_cast<int>(pid));
        pipes_[index].active = false;
        occupied_.erase(pipe.start);
        pids_.erase(static_cast<int>(pid));
        gaps_.put(pipe.start, pipe.start + pipe.length, pipe.cohort);
        model_.removed(static_cast<int>(pid), pipe, rank);
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    struct Choice {
        Coord gapStart = 0;
        Coord position = 0;
        Coord score = 0;
        bool high = false;
    };
    struct Arena {
        bool active = false;
        Coord base = 0;
        Coord low = 0;
        Coord high = 0;
        Coord gapSink = 0;
        std::size_t expected = 0;
        std::size_t used = 0;
        int deletedParity = 0;
    };
    void closeArena() {
        if (arena_.active) {
            gaps_.put(arena_.low, arena_.high, -1);
        }
        arena_ = Arena{};
    }
    Coord openArena(int length, int firstPid) {
        const auto forecast = model_.phaseForecast();
        if (!forecast) return 0;
        const Coord expected = static_cast<Coord>(forecast->expected);
        const Coord wholeBytes = expected * length;
        arena_ = Arena{};
        arena_.expected = forecast->expected;
        arena_.deletedParity = forecast->deletedParity;
        // Prefer grouping inside space that has already been dug.
        if (const auto existing = gaps_.reserve(wholeBytes)) {
            arena_.active = true;
            arena_.base = arena_.low = existing->start;
            arena_.high = existing->end;
            return 0;
        }
        // Avoid speculative expansion when existing holes can already hold
        // a complete predicted next run.
        if (gaps_.capacity(forecast->nextLength, expected) >= expected) {
            arena_ = Arena{};
            return 0;
        }
        const Coord deleted = expected / 2 +
            ((expected & 1) != 0 &&
             (firstPid & 1) == forecast->deletedParity ? 1 : 0);
        const Coord survivors = expected - deleted;
        const auto tail = gaps_.tail(trench_);
        const Coord tailCapacity =
            tail ? (tail->end - tail->start) / length : 0;
        const Coord gapSink =
            gaps_.capacity(length, survivors, tailCapacity);
        const Coord base = tail ? tail->start : trench_;
        const Coord reservedEnd = base + (expected - gapSink) * length;
        const Coord oldTrench = trench_;
        if (tail) gaps_.eraseStart(tail->start);
        trench_ = std::max(
            trench_, ((reservedEnd + kSection - 1) / kSection) * kSection);
        gaps_.put(reservedEnd, trench_, -1);
        arena_.active = true;
        arena_.base = arena_.low = base;
        arena_.high = reservedEnd;
        arena_.gapSink = gapSink;
        const Coord digs = (trench_ - oldTrench) / kSection;
        if (digs > 0) ++expansionGateOpportunities;
        return digs;
    }
    int attachedPid(const GapStore::Hole& hole, bool high) const {
        if (high) {
            const auto it = occupied_.find(hole.end);
            return it == occupied_.end() ? 0 : it->second;
        }
        auto it = occupied_.lower_bound(hole.start);
        if (it == occupied_.begin()) return 0;
        --it;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(it->second)];
        return pipe.start + pipe.length == hole.start ? it->second : 0;
    }
    Coord lifetimePenalty(
        const GapStore::Hole& hole, bool high, int length,
        const LifeView& life, const Demand& demand) const {
        if (hole.end - hole.start == length) return 0;
        const int neighbor = attachedPid(hole, high);
        if (neighbor == 0) return 0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(neighbor)];
        const auto other = static_cast<std::size_t>(pipe.length);
        const auto requested = static_cast<std::size_t>(length);
        if (!life.learned[other] || !life.learned[requested]) return 0;
        int difference = life.retention[requested] - life.retention[other];
        if (difference < 0) difference = -difference;
        difference = std::max(0, difference - 96);
        return static_cast<Coord>(difference) * 8 * demand.total / 1024;
    }
    // Compare capacity LOSS, rather than absolute capacity of cavities of
    // different sizes. The projected release set is inferred from past
    // deletions and is restricted to the current placement run.
    int projectedCapacityLoss(
        Coord position, int length, int nextLength,
        int deletedParity) const {
        const auto released = [&](int pid) {
            const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
            return pid >= model_.firstPid() &&
                pipe.length == length && (pid & 1) == deletedParity;
        };
        auto right = occupied_.lower_bound(position);
        auto left = right;
        Coord leftEnd = 0;
        Coord rightStart = trench_;
        std::size_t scanned = 0;
        while (left != occupied_.begin()) {
            --left;
            if (released(left->second)) {
                if (++scanned > 64) return -1;
                continue;
            }
            const Pipe& pipe =
                pipes_[static_cast<std::size_t>(left->second)];
            leftEnd = pipe.start + pipe.length;
            break;
        }
        scanned = 0;
        for (auto it = right; it != occupied_.end(); ++it) {
            if (released(it->second)) {
                if (++scanned > 64) return -1;
                continue;
            }
            rightStart = it->first;
            break;
        }
        if (leftEnd > position || rightStart < position + length) return -1;
        const Coord before = (rightStart - leftEnd) / nextLength;
        const Coord after = (position - leftEnd) / nextLength +
            (rightStart - position - length) / nextLength;
        return static_cast<int>(before - after);
    }
    std::optional<Choice> chooseGap(
        int length, int pid, int cohort, bool preferHigh,
        const Demand& demand, bool features, Coord endLimit) const {
        const auto holes = gaps_.candidates(
            length, demand, preferHigh, cohort,
            model_.cohortRouting(), endLimit);
        if (holes.empty()) return std::nullopt;
        const auto parity = model_.deletionParity();
        const int nextLength =
            features && model_.runCount() >= kLongRun
                ? model_.forecastNextSize() : 0;
        const bool project = parity && nextLength > length &&
            ((pid & 1) != *parity);
        const bool useLife = features && !parity &&
            !model_.fifoLike() && !model_.stackLike(length);
        const LifeView life = useLife ? model_.lifetimes() : LifeView{};
        const bool bothSides =
            project || (useLife && life.learned[
                static_cast<std::size_t>(length)]);
        std::optional<Choice> best;
        for (const auto& hole : holes) {
            const int sideCount =
                bothSides && hole.end - hole.start > length ? 2 : 1;
            for (int side = 0; side < sideCount; ++side) {
                const bool high = side == 0 ? preferHigh : !preferHigh;
                const Coord position =
                    high ? hole.end - length : hole.start;
                Coord score = hole.score;
                if (useLife) {
                    score += lifetimePenalty(
                        hole, high, length, life, demand);
                }
                if (project) {
                    int loss = projectedCapacityLoss(
                        position, length, nextLength, *parity);
                    // An unfinished bounded scan receives the conservative
                    // two-slot loss, rather than an artificial zero cost.
                    if (loss < 0) loss = 2;
                    score += static_cast<Coord>(loss) *
                        nextLength * demand.total / 2;
                }
                bool better = !best || score < best->score;
                if (best && score == best->score) {
                    const bool preferred = high == preferHigh;
                    const bool oldPreferred = best->high == preferHigh;
                    if (preferred != oldPreferred) {
                        better = preferred;
                    } else {
                        better = preferHigh
                            ? position > best->position
                            : position < best->position;
                    }
                }
                if (better) {
                    best = Choice{hole.start, position, score, high};
                }
            }
        }
        return best;
    }
    bool youngLeftNeighbor(Coord boundary) const {
        auto it = occupied_.lower_bound(boundary);
        if (it == occupied_.begin()) return false;
        --it;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(it->second)];
        return pipe.start + pipe.length == boundary &&
            pids_.rankFromNewest(it->second) <= 50;
    }
    std::pair<Coord, Coord> grow(
        int length, int cohort, bool preferHigh) {
        const auto tail = gaps_.tail(trench_);
        const Coord base = tail ? tail->start : trench_;
        const int owner = tail
            ? tail->owner : (model_.cohortRouting() ? cohort : -1);
        const Coord deficit = std::max<Coord>(
            0, length - (trench_ - base));
        const Coord digs = (deficit + kSection - 1) / kSection;
        const Coord newTrench = trench_ + digs * kSection;
        const bool stackGate = digs > 0 &&
            newTrench > base + length &&
            model_.stackLike(length) && youngLeftNeighbor(base);
        const bool suppressed = stackGate && model_.unitDominant();
        const bool offset = stackGate && !suppressed;
        if (digs > 0) ++expansionGateOpportunities;
        if (suppressed) ++unitProfileSuppressedExpansions;
        if (offset) ++expansionGatePasses;
        if (tail) gaps_.eraseStart(tail->start);
        trench_ = newTrench;
        Coord position;
        if (offset || (model_.cohortRouting() && preferHigh)) {
            position = trench_ - length;
            gaps_.put(base, position, owner);
        } else {
            position = base;
            gaps_.put(position + length, trench_, owner);
        }
        return {position, digs};
    }
    static void printPlacement(Coord digs, Coord position) {
        std::cout << digs << ' ' << position << '\n' << std::flush;
    }
    static void printInvalidPidFallback() {
        std::cout << 0 << '\n' << std::flush;
    }
    GapStore gaps_;
    WorkloadModel model_;
    PidIndex pids_;
    std::vector<Pipe> pipes_{Pipe{}};
    std::map<Coord, int> occupied_;
    Coord trench_ = 0;
    Arena arena_;
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
