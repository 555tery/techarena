#pragma once

#include <algorithm>
#include <cstdint>
#include <limits>
#include <utility>
#include <vector>

// Causal, one-step transport of an already displaced public prefix.
// Allocator must provide T, g.size(), pipes[id] = {start, live_length},
// and fits(start, length). referencePipes is BEFORE the new allocation;
// parentT is AFTER it. Actual and reference use the same PID history.
namespace local_transport {
struct Result {
    bool certificate = false;
    int x = -1, newT = 0, differing = 0;
    std::int64_t centerSum = 0;
    int hullLeft = 0, hullRight = 0;
};

template<class Allocator>
Result choose(Allocator& actual,
              const std::vector<std::pair<int,int>>& referencePipes,
              int refx, int parentT, int n,
              const std::vector<int>* liveIds = nullptr,
              std::size_t scanLimit = 8192) {
    Result failure;
    if (n <= 0 || refx < 0 || parentT < 0 || actual.T < 0 ||
        std::int64_t(refx) + n > parentT ||
        referencePipes.size() != actual.pipes.size() ||
        actual.g.size() > scanLimit) return failure;

    // liveIds, when supplied, MUST enumerate every live PID exactly once.
    // Without it, cap history too: do not repeatedly scan 200k dead records.
    std::vector<int> ids;
    if (liveIds) {
        if (liveIds->size() > scanLimit) return failure;
        ids = *liveIds;
        std::sort(ids.begin(), ids.end());
        if (std::adjacent_find(ids.begin(), ids.end()) != ids.end()) return failure;
    } else {
        if (referencePipes.size() > scanLimit + 1) return failure;
        for (std::size_t id = 1; id < referencePipes.size(); ++id) {
            if ((referencePipes[id].second > 0) != (actual.pipes[id].second > 0))
                return failure;
            if (referencePipes[id].second > 0) ids.push_back(int(id));
        }
    }
    bool hasCenter = false;
    std::int64_t center = 0;
    int left = std::numeric_limits<int>::max(), right = 0, different = 0;
    for (int id : ids) {
        if (id <= 0 || std::size_t(id) >= referencePipes.size()) return failure;
        const auto p = referencePipes[id], a = actual.pipes[id];
        if (p.second <= 0 || p.second != a.second || p.first < 0 || a.first < 0)
            return failure;
        if (std::int64_t(p.first) < std::int64_t(refx) + n &&
            std::int64_t(refx) < std::int64_t(p.first) + p.second) return failure;
        if (p.first == a.first) continue;
        const std::int64_t c = std::int64_t(p.first) + a.first + p.second;
        if (hasCenter && c != center) return failure;
        hasCenter = true; center = c; ++different;
        left = std::min(left, std::min(p.first, a.first));
        right = std::max(right, std::max(p.first, a.first) + p.second);
    }

    auto validHull = [&](int l, int r) {
        if (l >= r) return true;
        if (std::int64_t(l) + r != center) return false;
        for (int id : ids) {
            const auto p = referencePipes[id], a = actual.pipes[id];
            const bool intersects =
                (std::int64_t(p.first) < r && l < std::int64_t(p.first) + p.second) ||
                (std::int64_t(a.first) < r && l < std::int64_t(a.first) + a.second);
            if (intersects) {
                // A fixed pipe inside the reflected segment is permitted
                // only when it is centered at center/2.
                if (std::int64_t(p.first) + a.first + p.second != center) return false;
            } else if (p.first != a.first) return false;
        }
        return true;
    };
    if (hasCenter && !validHull(left, right)) return failure;

    Result best;
    auto tryX = [&](std::int64_t candidate) {
        if (candidate < 0 || candidate + n > 100000000 ||
            candidate > std::numeric_limits<int>::max()) return;
        const int x = int(candidate);
        const auto t64 = std::max<std::int64_t>(actual.T, ((candidate + n + 19) / 20) * 20);
        if (t64 > parentT || !actual.fits(x, n)) return;
        int l = left, r = right;
        const bool differs = x != refx;
        if (differs) {
            if (!hasCenter || std::int64_t(refx) + x + n != center) return;
            l = std::min(l, std::min(refx, x));
            r = std::max(r, std::max(refx, x) + n);
        }
        if (hasCenter) {
            if (!validHull(l, r)) return;
            const bool intersects =
                (std::int64_t(refx) < r && l < std::int64_t(refx) + n) ||
                (candidate < r && l < candidate + n);
            if (intersects && std::int64_t(refx) + x + n != center) return;
        } else { l = r = 0; }
        Result item;
        item.certificate = true; item.x = x; item.newT = int(t64);
        item.differing = different + int(differs);
        item.centerSum = hasCenter ? center : 0;
        item.hullLeft = l; item.hullRight = r;
        const auto key = [](const Result& v) {
            return std::make_pair(std::make_pair(v.newT, v.differing),
                                  std::make_pair(v.hullRight - v.hullLeft, v.x));
        };
        if (!best.certificate || key(item) < key(best)) best = item;
    };
    tryX(refx);
    if (hasCenter) tryX(center - refx - n);
    return best;
}
} // namespace local_transport
