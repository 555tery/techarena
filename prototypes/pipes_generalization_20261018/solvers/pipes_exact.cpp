#include <algorithm>
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <iterator>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

#if defined(POLICY_BF) == defined(POLICY_SS)
#error "Define exactly one of POLICY_BF and POLICY_SS"
#endif

namespace pipes {

constexpr int kMaxRequest = 40;
constexpr int kSection = 20;

struct Choice {
    int length;
    int start;
};

// Both policies use exactly this physical index, including the current free tail.
struct GapIndex {
    std::map<int, int> by_start;
    std::map<int, std::set<int>> by_length;
};

using CountChanges = std::vector<std::pair<int, int>>;

class BestFit {
public:
    void apply_changes(const CountChanges&) {}

    std::optional<Choice> choose(int request, const GapIndex& gaps) const {
        const auto it = gaps.by_length.lower_bound(request);
        if (it == gaps.by_length.end()) return std::nullopt;
        return Choice{it->first, *it->second.begin()};
    }
};

class SumOfSquares {
    struct LengthRecord {
        int length;
        int count = 0;
        std::array<int, kMaxRequest> positions;

        explicit LengthRecord(int h) : length(h) { positions.fill(-1); }
    };

    // A length receives a stable id when it first appears. Heap entries are ids.
    // Only currently present lengths occur in heaps; historical ids keep no gaps.
    std::vector<LengthRecord> records_;
    std::vector<int> id_of_length_;
    std::array<std::vector<int>, kMaxRequest> heaps_;

    int record_id(int length) const {
        if (length < 0 || length >= static_cast<int>(id_of_length_.size())) return -1;
        return id_of_length_[length];
    }

    int ensure_record(int length) {
        if (length >= static_cast<int>(id_of_length_.size())) {
            id_of_length_.resize(length + 1, -1);
        }
        int& id = id_of_length_[length];
        if (id < 0) {
            id = static_cast<int>(records_.size());
            records_.emplace_back(length);
        }
        return id;
    }

    int count(int length) const {
        const int id = record_id(length);
        return id < 0 ? 0 : records_[id].count;
    }

    int delta(int request, int id) const {
        const auto& record = records_[id];
        if (record.length == request) return 1 - 2 * record.count;
        return 2 - 2 * record.count + 2 * count(record.length - request);
    }

    bool better(int request, int lhs, int rhs) const {
        const int a = delta(request, lhs);
        const int b = delta(request, rhs);
        if (a != b) return a < b;
        return records_[lhs].length < records_[rhs].length;
    }

    void exchange(int request, int a, int b) {
        auto& heap = heaps_[request - 1];
        std::swap(heap[a], heap[b]);
        records_[heap[a]].positions[request - 1] = a;
        records_[heap[b]].positions[request - 1] = b;
    }

    void sift_up(int request, int position) {
        auto& heap = heaps_[request - 1];
        while (position > 0) {
            const int parent = (position - 1) / 2;
            if (!better(request, heap[position], heap[parent])) break;
            exchange(request, position, parent);
            position = parent;
        }
    }

    void sift_down(int request, int position) {
        auto& heap = heaps_[request - 1];
        const int size = static_cast<int>(heap.size());
        for (;;) {
            int best = position;
            const int left = 2 * position + 1;
            if (left < size && better(request, heap[left], heap[best])) best = left;
            if (left + 1 < size && better(request, heap[left + 1], heap[best])) best = left + 1;
            if (best == position) break;
            exchange(request, position, best);
            position = best;
        }
    }

    void erase_candidate(int request, int length) {
        const int id = record_id(length);
        if (id < 0) return;
        int position = records_[id].positions[request - 1];
        if (position < 0) return;
        auto& heap = heaps_[request - 1];
        records_[id].positions[request - 1] = -1;
        const int last = heap.back();
        heap.pop_back();
        if (position == static_cast<int>(heap.size())) return;
        heap[position] = last;
        records_[last].positions[request - 1] = position;
        if (position > 0 && better(request, last, heap[(position - 1) / 2])) {
            sift_up(request, position);
        } else {
            sift_down(request, position);
        }
    }

    void insert_candidate(int request, int length) {
        const int id = record_id(length);
        if (id < 0 || records_[id].count == 0) return;
        if (records_[id].positions[request - 1] >= 0) return;
        auto& heap = heaps_[request - 1];
        records_[id].positions[request - 1] = static_cast<int>(heap.size());
        heap.push_back(id);
        sift_up(request, static_cast<int>(heap.size()) - 1);
    }

public:
    SumOfSquares() { records_.reserve(200001); }

    void apply_changes(const CountChanges& changes) {
        // Changing c_h affects the candidate h for every request r <= h and the
        // candidate h+r for request r. Remove them with all OLD keys still valid.
        for (const auto& [h, ignored] : changes) {
            (void)ignored;
            for (int request = 1; request <= kMaxRequest; ++request) {
                if (request <= h) erase_candidate(request, h);
                erase_candidate(request, h + request);
            }
        }
        for (const auto& [h, change] : changes) {
            const int id = ensure_record(h);
            records_[id].count += change;
            assert(records_[id].count >= 0);
        }
        // All new counts are now final. Duplicate candidates are ignored.
        for (const auto& [h, ignored] : changes) {
            (void)ignored;
            for (int request = 1; request <= kMaxRequest; ++request) {
                if (request <= h) insert_candidate(request, h);
                insert_candidate(request, h + request);
            }
        }
    }

    std::optional<Choice> choose(int request, const GapIndex& gaps) const {
        const auto& heap = heaps_[request - 1];
        if (heap.empty()) return std::nullopt;
        const int length = records_[heap.front()].length;
        const auto it = gaps.by_length.find(length);
        assert(it != gaps.by_length.end() && !it->second.empty());
        return Choice{length, *it->second.begin()};
    }
};

#if defined(POLICY_BF)
using SelectedPolicy = BestFit;
#else
using SelectedPolicy = SumOfSquares;
#endif

struct Pipe {
    int start;
    int length;
    bool live;
};

class Allocator {
    GapIndex gaps_;
    SelectedPolicy policy_;
    std::vector<Pipe> pipes_{{-1, 0, false}};
    CountChanges changes_;
    int trench_ = 0;

    void add_gap(int start, int length) {
        if (length == 0) return;
        assert(length > 0);
        const bool fresh_start = gaps_.by_start.emplace(start, length).second;
        const bool fresh_length_start = gaps_.by_length[length].insert(start).second;
        assert(fresh_start && fresh_length_start);
        (void)fresh_start;
        (void)fresh_length_start;
        changes_.emplace_back(length, 1);
    }

    void remove_gap(std::map<int, int>::iterator it) {
        const int start = it->first;
        const int length = it->second;
        auto by_length = gaps_.by_length.find(length);
        assert(by_length != gaps_.by_length.end());
        by_length->second.erase(start);
        if (by_length->second.empty()) gaps_.by_length.erase(by_length);
        gaps_.by_start.erase(it);
        changes_.emplace_back(length, -1);
    }

    void finish_changes() {
        std::sort(changes_.begin(), changes_.end());
        std::size_t write = 0;
        for (std::size_t read = 0; read < changes_.size();) {
            const int h = changes_[read].first;
            int change = 0;
            do {
                change += changes_[read].second;
                ++read;
            } while (read < changes_.size() && changes_[read].first == h);
            if (change != 0) changes_[write++] = {h, change};
        }
        changes_.resize(write);
        policy_.apply_changes(changes_);
        changes_.clear();
#ifdef PIPE_ALLOCATOR_SELF_CHECK
        verify();
#endif
    }

#ifdef PIPE_ALLOCATOR_SELF_CHECK
    [[noreturn]] static void fail() { std::abort(); }

    void verify() const {
        // Independent unit-cell occupancy, physical coalescence and index checks.
        std::vector<int> cells(trench_, 0);
        for (std::size_t pid = 1; pid < pipes_.size(); ++pid) {
            const auto& pipe = pipes_[pid];
            if (!pipe.live) continue;
            if (pipe.start < 0 || pipe.start + pipe.length > trench_) fail();
            for (int x = pipe.start; x < pipe.start + pipe.length; ++x) {
                if (cells[x] != 0) fail();
                cells[x] = static_cast<int>(pid);
            }
        }
        std::map<int, int> expected_gaps;
        std::map<int, int> counts;
        for (int x = 0; x < trench_;) {
            if (cells[x] != 0) { ++x; continue; }
            const int start = x;
            while (x < trench_ && cells[x] == 0) ++x;
            expected_gaps[start] = x - start;
            ++counts[x - start];
        }
        if (expected_gaps != gaps_.by_start) fail();
        std::map<int, std::set<int>> expected_by_length;
        for (const auto& [start, h] : expected_gaps) expected_by_length[h].insert(start);
        if (expected_by_length != gaps_.by_length) fail();

        // Exhaustive physical-gap selection for ALL 40 requests after each command.
        // It recomputes Phi after placement instead of using the closed-form delta.
        for (int request = 1; request <= kMaxRequest; ++request) {
            std::optional<Choice> expected;
#if defined(POLICY_SS)
            long long best_phi = 0;
#endif
            for (const auto& [start, h] : expected_gaps) {
                if (h < request) continue;
                bool take = false;
#if defined(POLICY_BF)
                take = !expected || std::pair(h, start) < std::pair(expected->length, expected->start);
#else
                auto after = counts;
                --after[h];
                if (h > request) ++after[h - request];
                long long phi = 0;
                for (const auto& [ignored_h, c] : after) {
                    (void)ignored_h;
                    phi += static_cast<long long>(c) * c;
                }
                take = !expected || phi < best_phi ||
                    (phi == best_phi && std::pair(h, start) < std::pair(expected->length, expected->start));
                if (take) best_phi = phi;
#endif
                if (take) expected = Choice{h, start};
            }
            const auto actual = policy_.choose(request, gaps_);
            if (actual.has_value() != expected.has_value()) fail();
            if (actual && (actual->length != expected->length || actual->start != expected->start)) fail();
        }
    }
#endif

public:
    Allocator() {
        pipes_.reserve(200001);
        changes_.reserve(3);
    }

    std::pair<int, int> insert(int length) {
        assert(1 <= length && length <= kMaxRequest);
        int digs = 0;
        int start = 0;
        const auto choice = policy_.choose(length, gaps_);
        if (choice) {
            start = choice->start;
            remove_gap(gaps_.by_start.find(start));
            add_gap(start + length, choice->length - length);
        } else {
            // No current gap fits. Reuse the entire current tail before adding the
            // minimum positive number of sections, and place at its LEFT edge.
            start = trench_;
            int tail = 0;
            if (!gaps_.by_start.empty()) {
                auto last = std::prev(gaps_.by_start.end());
                if (last->first + last->second == trench_) {
                    start = last->first;
                    tail = last->second;
                    remove_gap(last);
                }
            }
            assert(tail < length);
            digs = (length - tail + kSection - 1) / kSection;
            trench_ += kSection * digs;
            add_gap(start + length, tail + kSection * digs - length);
        }
        pipes_.push_back(Pipe{start, length, true});
        finish_changes();
        return {digs, start};
    }

    int erase(int pid) {
        assert(pid > 0 && pid < static_cast<int>(pipes_.size()) && pipes_[pid].live);
        auto& pipe = pipes_[pid];
        const int original_start = pipe.start;
        int start = pipe.start;
        int length = pipe.length;
        auto right = gaps_.by_start.lower_bound(start);
        if (right != gaps_.by_start.begin()) {
            auto left = std::prev(right);
            if (left->first + left->second == start) {
                start = left->first;
                length += left->second;
                remove_gap(left);
            }
        }
        if (right != gaps_.by_start.end() && start + length == right->first) {
            length += right->second;
            remove_gap(right);
        }
        add_gap(start, length);
        pipe.live = false;
        finish_changes();
        return original_start;
    }
};

}  // namespace pipes

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    pipes::Allocator allocator;
    int command;
    while (std::cin >> command && command != 0) {
        if (command > 0) {
            const auto [digs, start] = allocator.insert(command);
            std::cout << digs << ' ' << start << '\n' << std::flush;
        } else {
            std::cout << allocator.erase(-command) << '\n' << std::flush;
        }
    }
}
