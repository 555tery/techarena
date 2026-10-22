#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

using I = std::int64_t;

struct FreeIndex {
    using Map = std::map<I, I>;
    Map gaps;
    std::set<std::pair<I, I>> sizes;

    void erase(Map::iterator it) {
        sizes.erase({it->second - it->first, it->first});
        gaps.erase(it);
    }

    void add(I start, I end) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto left = std::prev(it);
            assert(left->second <= start);
            if (left->second == start) {
                start = left->first;
                erase(left);
            }
        }
        it = gaps.lower_bound(start);
        assert(it == gaps.end() || end <= it->first);
        if (it != gaps.end() && it->first == end) {
            end = it->second;
            erase(it);
        }
        gaps.emplace(start, end);
        sizes.emplace(end - start, start);
    }

    std::pair<I, I> best(I length) const {
        auto it = sizes.lower_bound({length, -1});
        if (it == sizes.end()) return {-1, -1};
        return {it->second, it->second + it->first};
    }

    I tail_start(I trench) const {
        if (!gaps.empty()) {
            auto it = std::prev(gaps.end());
            if (it->second == trench) return it->first;
        }
        return trench;
    }

    bool consume(I start, I length) {
        auto it = gaps.upper_bound(start);
        assert(it != gaps.begin());
        --it;
        const I left = it->first;
        const I right = it->second;
        assert(left <= start && start + length <= right);
        erase(it);
        add(left, start);
        add(start + length, right);
        return left < start && start + length < right;
    }
};

struct Counters {
    I physical_exact = 0;
    I cache_hits = 0;
    I pool_hits = 0;
    I reclaim_events = 0;
    I reclaimed_blocks = 0;
    I reclaimed_bytes = 0;
    I same_state_overrides = 0;
    I interior_allocations = 0;
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    // Physical covers every free byte, including cached footprints.
    FreeIndex physical;
    // Pool excludes cached footprints, preserving their boundaries.
    FreeIndex pool;
    std::array<std::set<I>, 41> exact;
    std::map<I, int> cached;
    std::vector<std::pair<I, I>> pipes(1);
    Counters stats;
    I trench = 0;
    I live_volume = 0;
    I command = 0;

    // Revoke cache ownership only inside this physical free interval.
    // Every cached block is wholly contained in one physical gap.
    auto reclaim = [&](I start, I end) {
        I released = 0;
        auto it = cached.lower_bound(start);
        while (it != cached.end() && it->first < end) {
            const I address = it->first;
            const int length = it->second;
            assert(address + length <= end);
            exact[static_cast<std::size_t>(length)].erase(address);
            it = cached.erase(it);
            pool.add(address, address + length);
            ++released;
            ++stats.reclaimed_blocks;
            stats.reclaimed_bytes += length;
        }
        if (released != 0) ++stats.reclaim_events;
    };

    while (std::cin >> command && command != 0) {
        if (command < 0) {
            const auto p = pipes.at(static_cast<std::size_t>(-command));
            std::cout << p.first << '\n' << std::flush;
            physical.add(p.first, p.first + p.second);
            cached.emplace(p.first, static_cast<int>(p.second));
            exact[static_cast<std::size_t>(p.second)].insert(p.first);
            live_volume -= p.second;
            continue;
        }

        assert(command >= 1 && command <= 40);
        const int length = static_cast<int>(command);
        const auto eager = physical.best(length);
        const I reference_start = eager.first >= 0
            ? eager.first : physical.tail_start(trench);
        I digs = 0;
        I start = 0;

        if (eager.first >= 0 && eager.second - eager.first == length) {
            // Preserve the parent's lowest-address physical exact fit.
            start = eager.first;
            reclaim(eager.first, eager.second);
            pool.consume(start, length);
            ++stats.physical_exact;
        } else if (!exact[static_cast<std::size_t>(length)].empty()) {
            // Reuse an original footprint inside a possibly merged gap.
            auto& bin = exact[static_cast<std::size_t>(length)];
            auto it = bin.begin();
            start = *it;
            bin.erase(it);
            cached.erase(start);
            ++stats.cache_hits;
        } else {
            auto available = pool.best(length);
            if (available.first >= 0) {
                start = available.first;
                pool.consume(start, length);
                ++stats.pool_hits;
            } else {
                auto whole = eager;
                if (whole.first < 0) {
                    // Growth is allowed only after querying ALL free space.
                    const I tail = physical.tail_start(trench);
                    const I missing = length - (trench - tail);
                    assert(missing > 0);
                    digs = (missing + 19) / 20;
                    const I old = trench;
                    trench += digs * 20;
                    physical.add(old, trench);
                    pool.add(old, trench);
                    whole = physical.best(length);
                }
                assert(whole.first >= 0);
                start = whole.first;
                reclaim(whole.first, whole.second);
                pool.consume(start, length);
            }
        }

        if (start != reference_start) ++stats.same_state_overrides;
        if (physical.consume(start, length)) ++stats.interior_allocations;
        pipes.emplace_back(start, length);
        live_volume += length;
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }

#ifdef ALLOCATOR_DIAGNOSTICS
    std::cerr << "physical_exact=" << stats.physical_exact
              << " cache_hits=" << stats.cache_hits
              << " pool_hits=" << stats.pool_hits
              << " reclaim_events=" << stats.reclaim_events
              << " reclaimed_blocks=" << stats.reclaimed_blocks
              << " reclaimed_bytes=" << stats.reclaimed_bytes
              << " same_state_overrides=" << stats.same_state_overrides
              << " interior_allocations=" << stats.interior_allocations
              << " cached_blocks=" << cached.size()
              << " live_volume=" << live_volume
              << " trench=" << trench << '\n';
#endif
}
