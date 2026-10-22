#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <tuple>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kPageLength = 40;
constexpr std::int64_t kDigSection = 20;
constexpr int kClassCount = 40;

struct Page {
    int harmonicClass = 0;
    int livePipes = 0;
    std::map<int, int> freeByStart;
};

struct Pipe {
    int page = -1;
    int offset = 0;
    int length = 0;
    bool active = false;
};

class HarmonicAllocator {
public:
    std::vector<Page> pages;
    std::vector<Pipe> pipes{Pipe{}};
    std::array<std::set<std::tuple<int, int, int>>, kClassCount + 1> freeByClass;
    std::set<int> emptyPages;
    std::int64_t trenchLength = 0;

    static int harmonicClass(int length) {
        // Harmonic type j is (40/(j+1), 40/j]. For integral lengths,
        // j=floor(40/length); length 1 is the terminal type j=40.
        return std::clamp(40 / length, 1, kClassCount);
    }

    void place(int length) {
        const int type = harmonicClass(length);
        auto candidate = findGap(type, length);
        std::int64_t digs = 0;
        if (!candidate.has_value()) {
            const int page = acquirePage(type, digs);
            candidate = std::make_pair(page, 0);
        }

        const int pageIndex = candidate->first;
        const int offset = candidate->second;
        Page& page = pages[static_cast<std::size_t>(pageIndex)];
        if (page.livePipes >= type) {
            // The Harmonic invariant bounds a type-j page to j live pipes.
            // A fresh page is acquired if a state ever reaches this guard.
            const int newPage = acquirePage(type, digs);
            allocateFromPage(newPage, 0, length);
            emitPlacement(digs, static_cast<std::int64_t>(newPage) * kPageLength);
            pipes.push_back(Pipe{newPage, 0, length, true});
            return;
        }

        consumeGap(pageIndex, offset, length);
        emitPlacement(digs, static_cast<std::int64_t>(pageIndex) * kPageLength + offset);
        pipes.push_back(Pipe{pageIndex, offset, length, true});
    }

    void remove(std::int64_t pid) {
        if (pid <= 0 || static_cast<std::uint64_t>(pid) >= pipes.size() ||
            !pipes[static_cast<std::size_t>(pid)].active) {
            std::cout << "0\n" << std::flush;
            return;
        }
        Pipe& pipe = pipes[static_cast<std::size_t>(pid)];
        std::cout << static_cast<std::int64_t>(pipe.page) * kPageLength + pipe.offset
                  << '\n' << std::flush;
        Page& page = pages[static_cast<std::size_t>(pipe.page)];
        pipe.active = false;
        --page.livePipes;
        addFreeGap(pipe.page, pipe.offset, pipe.offset + pipe.length);
        if (page.livePipes == 0) releaseEmptyPage(pipe.page);
    }

private:
    using GapKey = std::tuple<int, int, int>;

    int acquirePage(int type, std::int64_t& digs) {
        int pageIndex = -1;
        if (!emptyPages.empty()) {
            auto it = emptyPages.begin();
            pageIndex = *it;
            emptyPages.erase(it);
            Page& page = pages[static_cast<std::size_t>(pageIndex)];
            page.harmonicClass = type;
            page.livePipes = 0;
            page.freeByStart.clear();
            addFreeGap(pageIndex, 0, static_cast<int>(kPageLength));
        } else {
            pageIndex = static_cast<int>(pages.size());
            const std::int64_t newLength = trenchLength + kPageLength;
            digs = (newLength - trenchLength + kDigSection - 1) / kDigSection;
            trenchLength += digs * kDigSection;
            pages.emplace_back();
            Page& page = pages.back();
            page.harmonicClass = type;
            addFreeGap(pageIndex, 0, static_cast<int>(kPageLength));
        }
        return pageIndex;
    }

    std::optional<std::pair<int, int>> findGap(int type, int length) {
        auto& gaps = freeByClass[static_cast<std::size_t>(type)];
        auto it = gaps.lower_bound(GapKey{length, -1, -1});
        while (it != gaps.end()) {
            const auto [gapLength, pageIndex, start] = *it;
            if (pages[static_cast<std::size_t>(pageIndex)].livePipes < type) {
                return std::make_pair(pageIndex, start);
            }
            it = gaps.upper_bound(GapKey{gapLength, pageIndex, start});
        }
        return std::nullopt;
    }

    void consumeGap(int pageIndex, int start, int length) {
        Page& page = pages[static_cast<std::size_t>(pageIndex)];
        auto it = page.freeByStart.find(start);
        if (it == page.freeByStart.end()) return;
        const int end = it->second;
        eraseGap(pageIndex, it);
        if (start + length < end) addFreeGap(pageIndex, start + length, end);
        ++page.livePipes;
    }

    void allocateFromPage(int pageIndex, int start, int length) {
        consumeGap(pageIndex, start, length);
    }

    void addFreeGap(int pageIndex, int start, int end) {
        if (start >= end) return;
        Page& page = pages[static_cast<std::size_t>(pageIndex)];
        auto it = page.freeByStart.lower_bound(start);
        if (it != page.freeByStart.begin()) {
            auto previous = std::prev(it);
            if (previous->second >= start) {
                start = previous->first;
                end = std::max(end, previous->second);
                eraseGap(pageIndex, previous);
                it = page.freeByStart.lower_bound(start);
            }
        }
        while (it != page.freeByStart.end() && it->first <= end) {
            end = std::max(end, it->second);
            auto current = it++;
            eraseGap(pageIndex, current);
        }
        page.freeByStart.emplace(start, end);
        const int type = page.harmonicClass;
        freeByClass[static_cast<std::size_t>(type)].emplace(end - start, pageIndex, start);
    }

    void eraseGap(int pageIndex, std::map<int, int>::iterator it) {
        Page& page = pages[static_cast<std::size_t>(pageIndex)];
        const int start = it->first;
        const int end = it->second;
        const int type = page.harmonicClass;
        freeByClass[static_cast<std::size_t>(type)].erase(GapKey{end - start, pageIndex, start});
        page.freeByStart.erase(it);
    }

    void releaseEmptyPage(int pageIndex) {
        Page& page = pages[static_cast<std::size_t>(pageIndex)];
        for (auto it = page.freeByStart.begin(); it != page.freeByStart.end();) {
            auto current = it++;
            eraseGap(pageIndex, current);
        }
        page.harmonicClass = 0;
        page.freeByStart.clear();
        emptyPages.insert(pageIndex);
    }

    static void emitPlacement(std::int64_t digs, std::int64_t start) {
        std::cout << digs << ' ' << start << '\n' << std::flush;
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    HarmonicAllocator allocator;
    std::int64_t command = 0;
    while (std::cin >> command) {
        if (command == 0) return 0;
        if (command > 0) allocator.place(static_cast<int>(command));
        else allocator.remove(-command);
    }
    return 0;
}
