#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <set>
#include <vector>

namespace {

constexpr int kMaxOrder = 26;
constexpr std::int64_t kDigLength = 20;

struct Pipe {
    std::int64_t start = 0;
    int order = -1;
    bool active = false;
};

class BuddyAllocator {
public:
    std::array<std::set<std::int64_t>, kMaxOrder + 1> freeBlocks;
    std::vector<Pipe> pipes{Pipe{}};
    std::int64_t trenchLength = 0;

    static std::int64_t blockLength(int order) {
        return std::int64_t{1} << order;
    }

    static int floorLog2(std::int64_t value) {
        int order = 0;
        while ((std::int64_t{1} << (order + 1)) <= value) ++order;
        return order;
    }

    static int trailingZeroOrder(std::int64_t value) {
        int order = 0;
        while (order < kMaxOrder && (value & (std::int64_t{1} << order)) == 0) {
            ++order;
        }
        return order;
    }

    void addBlock(std::int64_t start, int order) {
        while (order < kMaxOrder) {
            const std::int64_t buddy = start ^ blockLength(order);
            auto it = freeBlocks[static_cast<std::size_t>(order)].find(buddy);
            if (it == freeBlocks[static_cast<std::size_t>(order)].end()) break;
            freeBlocks[static_cast<std::size_t>(order)].erase(it);
            start = std::min(start, buddy);
            ++order;
        }
        freeBlocks[static_cast<std::size_t>(order)].insert(start);
    }

    void addRange(std::int64_t start, std::int64_t end) {
        while (start < end) {
            const std::int64_t remaining = end - start;
            const int byLength = floorLog2(remaining);
            const int byAlignment = start == 0 ? kMaxOrder : trailingZeroOrder(start);
            const int order = std::min(byLength, byAlignment);
            addBlock(start, order);
            start += blockLength(order);
        }
    }

    bool takeBlock(int requiredOrder, std::int64_t& start) {
        for (int order = requiredOrder; order <= kMaxOrder; ++order) {
            auto& bin = freeBlocks[static_cast<std::size_t>(order)];
            if (bin.empty()) continue;
            start = *bin.begin();
            bin.erase(bin.begin());
            while (order > requiredOrder) {
                --order;
                const std::int64_t right = start + blockLength(order);
                addBlock(right, order);
            }
            return true;
        }
        return false;
    }

    static int requiredOrder(int length) {
        int order = 0;
        while (blockLength(order) < length) ++order;
        return order;
    }

    void place(int length) {
        const int order = requiredOrder(length);
        std::int64_t start = 0;
        std::int64_t digs = 0;
        while (!takeBlock(order, start)) {
            const std::int64_t oldLength = trenchLength;
            trenchLength += kDigLength;
            addRange(oldLength, trenchLength);
            ++digs;
        }
        std::cout << digs << ' ' << start << '\n' << std::flush;
        pipes.push_back(Pipe{start, order, true});
    }

    void remove(std::int64_t pid) {
        if (pid <= 0 || static_cast<std::uint64_t>(pid) >= pipes.size() ||
            !pipes[static_cast<std::size_t>(pid)].active) {
            std::cout << "0\n" << std::flush;
            return;
        }
        Pipe& pipe = pipes[static_cast<std::size_t>(pid)];
        std::cout << pipe.start << '\n' << std::flush;
        pipe.active = false;
        addBlock(pipe.start, pipe.order);
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    BuddyAllocator allocator;
    std::int64_t command = 0;
    while (std::cin >> command) {
        if (command == 0) return 0;
        if (command > 0) allocator.place(static_cast<int>(command));
        else allocator.remove(-command);
    }
    return 0;
}
