#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <utility>
#include <vector>

using I = std::int64_t;

class Allocator {
    using U = std::uint64_t;
    static constexpr int SECTION = 20;
    static constexpr int MAX_LENGTH = 40;
    static constexpr int PAGE = SECTION * MAX_LENGTH;
    static constexpr int WORDS = (PAGE + 63) / 64;

    struct Page {
        std::array<U, WORDS> occupied{};
        std::array<unsigned, MAX_LENGTH + 1> returned{};
        unsigned returnedSum = 0;
        int covered = 0;
        int used = 0;
        int owner = 0;
        bool indexed = false;
    };

    using Gaps = std::map<I, I>;
    Gaps gaps;
    std::set<std::pair<I, I>> sizes;
    std::array<std::set<std::pair<int, int>>, MAX_LENGTH + 1> ready;
    std::array<I, MAX_LENGTH + 1> liveCount{};
    std::array<I, MAX_LENGTH + 1> deletedCount{};
    std::vector<Page> pages;
    I trench = 0;

    static int firstRun(const Page& p, int length) {
        int carry = 0;
        const int words = (p.covered + 63) / 64;
        for (int w = 0; w < words; ++w) {
            const int width = std::min(64, p.covered - 64 * w);
            U available = ~p.occupied[w];
            if (width < 64) available &= (U{1} << width) - 1;

            const int prefix = std::countr_one(available);
            if (carry + prefix >= length) return 64 * w - carry;

            U starts = available;
            int span = 1;
            while (2 * span <= length) {
                starts &= starts >> span;
                span *= 2;
            }
            if (span < length) starts &= starts >> (length - span);
            if (starts != 0) return 64 * w + std::countr_zero(starts);

            if (width == 64) {
                const int suffix = std::countl_one(available);
                carry = suffix == 64 ? carry + 64 : suffix;
            } else {
                carry = 0;
            }
        }
        return -1;
    }

    void unindexPage(int id) {
        Page& p = pages[id];
        if (p.indexed) {
            ready[p.owner].erase({-p.used, id});
            p.indexed = false;
        }
    }

    void indexPage(int id) {
        Page& p = pages[id];
        if (p.used > 0 && p.owner > 0 && firstRun(p, p.owner) >= 0) {
            ready[p.owner].insert({-p.used, id});
            p.indexed = true;
        }
    }

    static void noteReturn(Page& p, int length, int amount) {
        p.returned[length] += static_cast<unsigned>(amount);
        p.returnedSum += static_cast<unsigned>(amount);

        // Forget history according to returned volume, not operation count.
        if (p.returnedSum >= 2 * PAGE) {
            p.returnedSum = 0;
            for (int s = 1; s <= MAX_LENGTH; ++s) {
                p.returned[s] /= 2;
                p.returnedSum += p.returned[s];
            }
        }

        int winner = p.owner;
        if (winner != 0 && p.returned[winner] < unsigned(2 * winner)) {
            winner = 0;
        }
        for (int s = 1; s <= MAX_LENGTH; ++s) {
            if (p.returned[s] >= unsigned(2 * s) &&
                (winner == 0 || p.returned[s] > p.returned[winner])) {
                winner = s;
            }
        }
        p.owner = winner;
    }

    void mark(I position, int length, bool placing) {
        int remaining = length;
        while (remaining > 0) {
            const int id = static_cast<int>(position / PAGE);
            const int offset = static_cast<int>(position - I(id) * PAGE);
            const int amount = std::min(remaining, PAGE - offset);
            unindexPage(id);
            Page& p = pages[id];

            int at = offset;
            int left = amount;
            while (left > 0) {
                const int word = at / 64;
                const int shift = at % 64;
                const int n = std::min(left, 64 - shift);
                const U mask = n == 64
                    ? ~U{0}
                    : ((U{1} << n) - 1) << shift;
                if (placing) p.occupied[word] |= mask;
                else p.occupied[word] &= ~mask;
                at += n;
                left -= n;
            }

            if (placing) {
                p.used += amount;
            } else {
                p.used -= amount;
                if (p.used == 0) {
                    // Empty pages immediately lose all class affinity.
                    p.returned.fill(0);
                    p.returnedSum = 0;
                    p.owner = 0;
                } else {
                    noteReturn(p, length, amount);
                }
            }
            indexPage(id);
            position += amount;
            remaining -= amount;
        }
    }

    void eraseGap(Gaps::iterator it) {
        sizes.erase({it->second - it->first, it->first});
        gaps.erase(it);
    }

    void addGap(I start, I end) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto previous = std::prev(it);
            if (previous->second == start) {
                start = previous->first;
                eraseGap(previous);
            }
        }
        it = gaps.lower_bound(start);
        if (it != gaps.end() && it->first == end) {
            end = it->second;
            eraseGap(it);
        }
        gaps[start] = end;
        sizes.insert({end - start, start});
    }

    void extend(I sections) {
        const I old = trench;
        trench += sections * SECTION;
        addGap(old, trench);

        pages.resize(static_cast<std::size_t>((trench + PAGE - 1) / PAGE));
        const int first = static_cast<int>(old / PAGE);
        const int last = static_cast<int>((trench - 1) / PAGE);
        for (int id = first; id <= last; ++id) {
            unindexPage(id);
            pages[id].covered = static_cast<int>(
                std::min<I>(PAGE, trench - I(id) * PAGE));
            indexPage(id);
        }
    }

public:
    std::pair<I, I> allocate(int length) {
        I digs = 0;
        auto best = sizes.lower_bound({length, -1});
        if (best == sizes.end()) {
            I tail = trench;
            if (!gaps.empty()) {
                const auto last = std::prev(gaps.end());
                if (last->second == trench) tail = last->first;
            }
            digs = (length - (trench - tail) + SECTION - 1) / SECTION;
            extend(digs);
            best = sizes.lower_bound({length, -1});
        }

        auto gap = gaps.find(best->second);
        I start = gap->first;

        // Pages are preferences only. Every gap stays globally available.
        // Global exact fits always win, including their original address ties.
        if (best->first > length && deletedCount[length] > 0 &&
            deletedCount[length] >= liveCount[length] &&
            !ready[length].empty()) {
            const int id = ready[length].begin()->second;
            const I base = I(id) * PAGE;
            const I limit = base + pages[id].covered;

            // Use an endpoint, so page affinity never splits a gap in two.
            auto endpointInPage = [&](Gaps::iterator it, I& position) {
                if (it->first >= base && it->first + length <= limit) {
                    position = it->first;
                    return true;
                }
                if (it->second <= limit && it->second - length >= base) {
                    position = it->second - length;
                    return true;
                }
                return false;
            };

            // Retain global best-fit whenever it already serves this page.
            if (!endpointInPage(gap, start)) {
                const int offset = firstRun(pages[id], length);
                if (offset >= 0) {
                    const I probe = base + offset;
                    auto candidate = gaps.upper_bound(probe);
                    if (candidate != gaps.begin()) {
                        --candidate;
                        if (candidate->first <= probe &&
                            probe + length <= candidate->second) {
                            I preferred = 0;
                            if (endpointInPage(candidate, preferred)) {
                                gap = candidate;
                                start = preferred;
                            }
                        }
                    }
                }
            }
        }

        const I begin = gap->first;
        const I end = gap->second;
        eraseGap(gap);
        addGap(begin, start);
        addGap(start + length, end);
        mark(start, length, true);
        ++liveCount[length];
        return {digs, start};
    }

    void release(I start, int length) {
        --liveCount[length];
        ++deletedCount[length];
        addGap(start, start + length);
        mark(start, length, false);
    }
};

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::vector<std::pair<I, int>> pipes(1);
    I command;
    while (std::cin >> command && command != 0) {
        if (command < 0) {
            const auto pipe = pipes.at(static_cast<std::size_t>(-command));
            std::cout << pipe.first << '\n' << std::flush;
            allocator.release(pipe.first, pipe.second);
        } else {
            const int length = static_cast<int>(command);
            const auto result = allocator.allocate(length);
            pipes.push_back({result.second, length});
            std::cout << result.first << ' ' << result.second
                      << '\n' << std::flush;
        }
    }
}
