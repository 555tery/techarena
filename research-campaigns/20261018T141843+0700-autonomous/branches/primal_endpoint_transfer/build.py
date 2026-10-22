from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
original = (ROOT / 'branches/primal_transfer/primal_gap_dp.cpp').read_text()
prefix, s = original.split('class Allocator {', 1)

def change(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)

change('    std::uint64_t primalFirstActivationEvent = 0;', '''    std::uint64_t primalFirstActivationEvent = 0;
    static constexpr int releaseAgeBands = 16;
    static constexpr int releaseValueCap = 80;
    struct ReleaseStats { int observed = 0; int useful = 0; };
    struct PendingRelease { int pid = 0; int cell = -1; bool deleted = false; };
    std::vector<ReleaseStats> releaseStats = std::vector<ReleaseStats>(41 * 41 * releaseAgeBands);
    std::array<PendingRelease, 2> pendingRelease{};
    std::vector<std::uint64_t> releaseBornStep{0};
    int pendingReleaseNew = 0;
    bool pendingReleaseNewDeleted = false;
    std::array<double, releaseValueCap + 1> releaseValue{};
    bool releaseValueReady = false;
    std::uint64_t releaseValueAt = 0;
    std::uint64_t releaseProbes = 0;
    std::uint64_t releaseEndpointChanges = 0;''')
change('    void place(int length) {', '    void place(int length) {\n        closeReleaseInterval();')
change('            start = consumeAtSide(gap, length, highSide);', '''            if (!additiveNextAlignment && !geometricLaneActive &&
                !counterfactualCapacityChoice && !runLeftActive &&
                !lifoStackLane && !parityCohortMode && !alternatingDeleteMode &&
                activePipeCount > kMcMaxActivePipes) {
                highSide = releaseEndpoint(gap, length, highSide);
            }
            start = consumeAtSide(gap, length, highSide);''')
change('        const Pipe pipe = pipes[index];', '''        if (static_cast<int>(index) == pendingReleaseNew) pendingReleaseNewDeleted = true;
        for (auto& probe : pendingRelease) {
            if (probe.cell >= 0 && probe.pid == static_cast<int>(index)) probe.deleted = true;
        }
        const Pipe pipe = pipes[index];''')
change('    void recordPrimalEvent(int event) {', '''    void recordPrimalEvent(int event) {
        if (event > 0) releaseBornStep.push_back(primalStep + 1);''')

begin = s.index('    void rebuildPrimalGapValues(int maxGap) {')
end = s.index('    bool ensurePrimalGapValues', begin)
kernel = s[begin:end]
kernel = kernel.replace('void rebuildPrimalGapValues(int maxGap)', 'void rebuildReleaseValues()')
kernel = kernel.replace('gap <= maxGap', 'gap <= releaseValueCap')
kernel = kernel.replace('primalGapValue', 'releaseValue')
kernel = kernel.replace('''        primalModelStep = primalStep;
        primalComputedLimit = maxGap;
        primalModelDirty = false;
        ++primalModelRebuilds;''', '''        releaseValueAt = primalStep;
        releaseValueReady = true;''')
assert 'primalComputedLimit' not in kernel

methods = '''    // Outcomes are completed only at the next observed insertion.
    void closeReleaseInterval() {
        for (auto& probe : pendingRelease) {
            if (probe.cell < 0) continue;
            auto& stats = releaseStats[static_cast<std::size_t>(probe.cell)];
            ++stats.observed;
            if (probe.deleted && !pendingReleaseNewDeleted) ++stats.useful;
            probe = PendingRelease{};
        }
        pendingReleaseNew = 0;
        pendingReleaseNewDeleted = false;
    }

    int releaseCell(int pid, int request) const {
        std::uint64_t age = primalStep + 1 - releaseBornStep[static_cast<std::size_t>(pid)];
        int band = 0;
        while (age >= 4 && band + 1 < releaseAgeBands) { age /= 4; ++band; }
        const int neighbour = pipes[static_cast<std::size_t>(pid)].length;
        return (request * 41 + neighbour) * releaseAgeBands + band;
    }

    std::pair<double, double> releaseBounds(int cell) const {
        const auto& stats = releaseStats[static_cast<std::size_t>(cell)];
        if (stats.observed == 0) return {0.0, 1.0};
        const double n = stats.observed;
        const double p = static_cast<double>(stats.useful) / n;
        const double denominator = 1.0 + 4.0 / n;
        const double center = (p + 2.0 / n) / denominator;
        const double radius = 2.0 * std::sqrt(p * (1.0 - p) / n + 1.0 / (n * n)) / denominator;
        return {std::max(0.0, center - radius), std::min(1.0, center + radius)};
    }

    // Separate cache leaves the parent's gap-size ranking schedule unchanged.
''' + kernel + '''    bool releaseEndpoint(StartIter gap, int length, bool fallback) {
        const std::int64_t begin = gap->first, end = gap->second;
        const std::int64_t remainder = end - begin - length;
        if (remainder <= 0 || end - begin > releaseValueCap) return fallback;
        const auto leftIt = activeByEnd.find(begin);
        const auto rightIt = activeByEnd.upper_bound(end);
        if (leftIt == activeByEnd.end() || rightIt == activeByEnd.end()) return fallback;
        const int left = leftIt->second, right = rightIt->second;
        const Pipe& lp = pipes[static_cast<std::size_t>(left)];
        const Pipe& rp = pipes[static_cast<std::size_t>(right)];
        if (rp.start != end) return fallback;
        const int leftCell = releaseCell(left, length), rightCell = releaseCell(right, length);
        pendingRelease[0] = PendingRelease{left, leftCell, false};
        pendingRelease[1] = PendingRelease{right, rightCell, false};
        pendingReleaseNew = static_cast<int>(pipes.size());
        ++releaseProbes;
        std::int64_t leftFree = lp.length, rightFree = rp.length;
        auto outerLeft = freeByStart.lower_bound(lp.start);
        if (outerLeft != freeByStart.begin()) {
            --outerLeft;
            if (outerLeft->second == lp.start) leftFree += outerLeft->second - outerLeft->first;
        }
        const auto outerRight = freeByStart.find(rp.start + rp.length);
        if (outerRight != freeByStart.end()) rightFree += outerRight->second - outerRight->first;
        if (leftFree + remainder > releaseValueCap || rightFree + remainder > releaseValueCap) return fallback;
        if (!releaseValueReady || primalStep - releaseValueAt >= 64) rebuildReleaseValues();
        const auto value = [&](std::int64_t g) { return releaseValue[static_cast<std::size_t>(g)]; };
        const double leftGain = std::max(0.0, value(leftFree + remainder) - value(leftFree) - value(remainder));
        const double rightGain = std::max(0.0, value(rightFree + remainder) - value(rightFree) - value(remainder));
        const auto lb = releaseBounds(leftCell), rb = releaseBounds(rightCell);
        bool high = fallback;
        if (leftGain * lb.first > rightGain * rb.second + 1e-9) high = true;
        else if (rightGain * rb.first > leftGain * lb.second + 1e-9) high = false;
        if (high != fallback) ++releaseEndpointChanges;
        return high;
    }

'''
change('    bool hasRecentPrimalDemand() const {', methods + '    bool hasRecentPrimalDemand() const {')
change('            std::cerr << "primal_dp_scored_decisions="', '''            std::cerr << "release_endpoint_probes=" << allocator.releaseProbes
                      << " changed_endpoints=" << allocator.releaseEndpointChanges << '\\n';
            std::cerr << "primal_dp_scored_decisions="''')
prefix = prefix.replace('#include <cstdint>', '#include <cstdint>\n#include <cmath>')
(HERE / 'solution.cpp').write_text(prefix + 'class Allocator {' + s)
print(HERE / 'solution.cpp')
