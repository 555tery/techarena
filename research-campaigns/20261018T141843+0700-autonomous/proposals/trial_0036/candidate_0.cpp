#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

using I = std::int64_t;

class Allocator {
    static constexpr int MaxLength = 40;
    static constexpr I Section = 20;
    static constexpr I PageSize = 4 * MaxLength;
    using Key = std::pair<I, I>;

    struct Gap {
        I end;
        int leftCap;
        int rightCap;
    };

    struct Page {
        I used = 0;
        I peak = 0;
        bool draining = false;
    };

    using GapMap = std::map<I, Gap>;
    GapMap gaps;
    std::set<Key> sizes;

    // Entry: {whole gap length, 2 * gap start + endpoint}.
    // The bucket gives the maximum clear endpoint length, capped at 40.
    std::array<std::set<Key>, MaxLength + 1> eligible;
    std::vector<Page> pages;
    I trench = 0;

    std::uint64_t ordinaryAllocations = 0;
    std::uint64_t placementChanges = 0;
    std::uint64_t largerHoleChoices = 0;
    std::uint64_t skippedExactFits = 0;
    std::uint64_t drainStarts = 0;
    std::uint64_t closedDrains = 0;
    std::uint64_t cancelledDrains = 0;

    bool isDraining(I page) const {
        return page >= 0 &&
               static_cast<std::size_t>(page) < pages.size() &&
               pages[static_cast<std::size_t>(page)].draining;
    }

    int clearCapacity(I start, I end, bool right) const {
        const I available = std::min<I>(MaxLength, end - start);
        const I edge = right ? end - 1 : start;
        const I page = edge / PageSize;
        if (isDraining(page)) return 0;

        const I within = right ? edge % PageSize + 1
                               : PageSize - edge % PageSize;
        if (available <= within) return static_cast<int>(available);

        // A request spans at most two pages.
        const I adjacent = right ? page - 1 : page + 1;
        if (isDraining(adjacent)) return static_cast<int>(within);
        return static_cast<int>(available);
    }

    void eraseGap(GapMap::iterator it) {
        const I start = it->first;
        const Gap gap = it->second;
        const I length = gap.end - start;
        sizes.erase({length, start});
        if (gap.leftCap > 0)
            eligible[gap.leftCap].erase({length, 2 * start});
        if (gap.rightCap > 0)
            eligible[gap.rightCap].erase({length, 2 * start + 1});
        gaps.erase(it);
    }

    void insertGap(I start, I end) {
        const I length = end - start;
        const int left = clearCapacity(start, end, false);
        const int right = clearCapacity(start, end, true);
        gaps.emplace(start, Gap{end, left, right});
        sizes.insert({length, start});
        if (left > 0) eligible[left].insert({length, 2 * start});
        if (right > 0) eligible[right].insert({length, 2 * start + 1});
    }

    void addFree(I start, I end) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto previous = std::prev(it);
            if (previous->second.end == start) {
                start = previous->first;
                eraseGap(previous);
            }
        }
        it = gaps.lower_bound(start);
        if (it != gaps.end() && it->first == end) {
            end = it->second.end;
            eraseGap(it);
        }
        insertGap(start, end);
    }

    void refreshGap(GapMap::iterator it) {
        const I start = it->first;
        Gap& gap = it->second;
        const I length = gap.end - start;
        const int left = clearCapacity(start, gap.end, false);
        const int right = clearCapacity(start, gap.end, true);

        if (left != gap.leftCap) {
            if (gap.leftCap > 0)
                eligible[gap.leftCap].erase({length, 2 * start});
            gap.leftCap = left;
            if (left > 0) eligible[left].insert({length, 2 * start});
        }
        if (right != gap.rightCap) {
            if (gap.rightCap > 0)
                eligible[gap.rightCap].erase({length, 2 * start + 1});
            gap.rightCap = right;
            if (right > 0)
                eligible[right].insert({length, 2 * start + 1});
        }
    }

    void refreshPage(I page) {
        // Only endpoints within 40m of this page can change eligibility.
        const I low = std::max<I>(0, page * PageSize - MaxLength);
        const I high = (page + 1) * PageSize + MaxLength;
        auto it = gaps.lower_bound(low);
        if (it != gaps.begin()) --it;
        for (; it != gaps.end() && it->first < high; ++it)
            refreshGap(it);
    }

    void changeUsage(I start, I length, bool insertion) {
        std::array<I, 2> changed{};
        int changedCount = 0;
        const I end = start + length;

        for (I position = start; position < end;) {
            const I pageIndex = position / PageSize;
            const I next = std::min(end, (pageIndex + 1) * PageSize);
            const I amount = next - position;
            Page& page = pages[static_cast<std::size_t>(pageIndex)];
            const bool wasDraining = page.draining;

            if (insertion) {
                page.used += amount;
                if (wasDraining) {
                    // Forced reuse ends this evacuation attempt.
                    page.draining = false;
                    page.peak = page.used;
                    ++cancelledDrains;
                } else {
                    page.peak = std::max(page.peak, page.used);
                }
            } else {
                page.used -= amount;
                if (page.used == 0) {
                    if (wasDraining) ++closedDrains;
                    page.draining = false;
                    page.peak = 0;
                } else if (!page.draining && 2 * page.used <= page.peak) {
                    page.draining = true;
                    ++drainStarts;
                }
            }

            if (page.draining != wasDraining)
                changed[changedCount++] = pageIndex;
            position = next;
        }

        // Update indices after both affected page states are final.
        for (int i = 0; i < changedCount; ++i)
            refreshPage(changed[i]);
    }

public:
    std::pair<I, I> allocate(I length) {
        I digs = 0;
        auto best = sizes.lower_bound({length, -1});
        const bool growing = best == sizes.end();

        if (growing) {
            I tail = trench;
            if (!gaps.empty()) {
                auto last = std::prev(gaps.end());
                if (last->second.end == trench) tail = last->first;
            }
            digs = (length - (trench - tail) + Section - 1) / Section;
            const I old = trench;
            trench += digs * Section;
            pages.resize(static_cast<std::size_t>(
                (trench + PageSize - 1) / PageSize));
            addFree(old, trench);
            best = sizes.lower_bound({length, -1});
        }

        const I baselineLength = best->first;
        const I baselineStart = best->second;
        Key chosen{baselineLength, 2 * baselineStart};

        if (!growing) {
            ++ordinaryAllocations;
            bool found = false;
            Key preferred{};
            for (int capacity = static_cast<int>(length);
                 capacity <= MaxLength; ++capacity) {
                if (eligible[capacity].empty()) continue;
                // Every entry in this bucket already fits the request.
                const Key candidate = *eligible[capacity].begin();
                if (!found || candidate < preferred) {
                    preferred = candidate;
                    found = true;
                }
            }
            if (found && preferred.first <= baselineLength + Section)
                chosen = preferred;
        }

        const I gapStart = chosen.second / 2;
        const bool right = (chosen.second & 1) != 0;
        auto gap = gaps.find(gapStart);
        const I gapEnd = gap->second.end;
        const I start = right ? gapEnd - length : gapStart;

        if (!growing && start != baselineStart) {
            ++placementChanges;
            if (chosen.first > baselineLength) ++largerHoleChoices;
            if (baselineLength == length && chosen.first > length)
                ++skippedExactFits;
        }

        eraseGap(gap);
        addFree(gapStart, start);
        addFree(start + length, gapEnd);
        changeUsage(start, length, true);
        return {digs, start};
    }

    void release(I start, I length) {
        addFree(start, start + length);
        changeUsage(start, length, false);
    }

    void diagnostics() const {
#ifdef ALLOCATOR_DIAGNOSTICS
        std::cerr << "trench=" << trench
                  << " ordinary_allocations=" << ordinaryAllocations
                  << " placement_changes=" << placementChanges
                  << " larger_hole_choices=" << largerHoleChoices
                  << " skipped_exact_fits=" << skippedExactFits
                  << " drain_starts=" << drainStarts
                  << " closed_drains=" << closedDrains
                  << " cancelled_drains=" << cancelledDrains << '\n';
#endif
    }
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::vector<std::pair<I, I>> pipes(1);
    I command;
    while (std::cin >> command && command) {
        if (command < 0) {
            const auto pipe = pipes.at(static_cast<std::size_t>(-command));
            std::cout << pipe.first << '\n' << std::flush;
            allocator.release(pipe.first, pipe.second);
        } else {
            const auto result = allocator.allocate(command);
            pipes.push_back({result.second, command});
            std::cout << result.first << ' ' << result.second
                      << '\n' << std::flush;
        }
    }
    allocator.diagnostics();
}
