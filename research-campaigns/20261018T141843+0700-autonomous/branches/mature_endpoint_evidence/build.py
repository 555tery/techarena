from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
base = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
prefix, s = base.read_text().split('class Allocator {', 1)

def change(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)

change('    CensoredLifetimeModel lifetimeModel;', '''    std::uint64_t matureShortEndpointDecisions = 0;
    std::uint64_t matureShortEndpointChanges = 0;
    CensoredLifetimeModel lifetimeModel;''')
change('''        bool highSide = lifoStackLane || (runLeftActive''', '''        // Reuse the parent's minimum live-population condition for its
        // deletion-confidence model. Beyond warm-up, short length alone
        // does not imply that the opposite edge is a useful recycling lane.
        const bool matureShortEndpoint = activePipeCount >= 128 &&
            length <= kRightEdgeMaxPipeLength && !runLeftActive &&
            !alternatingDeleteMode && !parityCohortMode && !sameSizeRun;
        const bool shortEdgeEvidence = length > kRightEdgeMaxPipeLength ||
            activePipeCount < 128 ||
            hasLifoDeletionConfidence();
        if (matureShortEndpoint) ++matureShortEndpointDecisions;
        bool highSide = lifoStackLane || (runLeftActive''')
change('''                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)))));''', '''                    : ((length <= kRightEdgeMaxPipeLength && shortEdgeEvidence) ||
                       hasSameLengthRecentRun(length)))));''')
change('            start = consumeAtSide(gap, length, highSide);', '''            if (matureShortEndpoint && !shortEdgeEvidence && !highSide &&
                !counterfactualCapacityChoice && gap->second - gap->first > length) {
                ++matureShortEndpointChanges;
            }
            start = consumeAtSide(gap, length, highSide);''')
change('''            std::cerr << "primal_dp_scored_decisions="''', '''            std::cerr << "mature_short_endpoint_decisions="
                      << allocator.matureShortEndpointDecisions
                      << " changed_endpoints=" << allocator.matureShortEndpointChanges << '\\n';
            std::cerr << "primal_dp_scored_decisions="''')
(HERE / 'solution.cpp').write_text(prefix + 'class Allocator {' + s)
print(HERE / 'solution.cpp')
