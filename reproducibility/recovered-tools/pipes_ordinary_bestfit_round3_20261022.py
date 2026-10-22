"""Prepared round3 ablation; pure source transformation, no runs or file I/O.

Ordinary requests use Best-Fit over every physically free span (tail included),
then lower address, consume its left end, and bypass both complex gap ranking
and MC. The existing minimal tail-extension branch is retained.

Preserved structured regimes: parity/cohort, alternating deletion, any same-size
run or runLeft/geometric/rearmReverse mode, additive alignment, predicted next
geometric class, LIFO lane and any supported LIFO deletion-confidence regime.
The active cohort-slab branch returns before this choice, exactly as before.
Generic length<=4 right-edge placement is intentionally part of the ablation:
it is overridden with highSide=false for ordinary requests.

Observation updates, physical indexes, merging, PID/lifetime bookkeeping,
replay/import, all structured code, and the remaining MC budget are unchanged.
No claim of quality improvement or target-CPU performance is made before testing.
"""

def _replace(source,old,new):
 assert source.count(old)==1,(old[:120],source.count(old))
 return source.replace(old,new)


def apply_cpp(source):
 source=_replace(source,'''        const int predictedNextClass = predictEarlyNextGeometricSize(length);
        auto gap = bestFittingGap(length, highSide, sizeCohort);''',
 '''        const int predictedNextClass = predictEarlyNextGeometricSize(length);
        const bool ordinaryRequest = !parityCohortMode && !alternatingDeleteMode &&
            !runLeftActive && !additiveNextAlignment && !lifoStackLane &&
            !hasLifoDeletionConfidence() && !sameSizeRun &&
            predictedNextClass <= length;
        if (ordinaryRequest) highSide = false;
        auto gap = freeByStart.end();
        if (ordinaryRequest) {
            const auto fitting = freeBySize.lower_bound({length, 0});
            if (fitting != freeBySize.end()) gap = freeByStart.find(fitting->second);
        } else {
            gap = bestFittingGap(length, highSide, sizeCohort);
        }''')
 source=_replace(source,'''            const std::int64_t selectedStart = (additiveNextAlignment ||
                counterfactualCapacityChoice)''',
 '''            const std::int64_t selectedStart = (ordinaryRequest || additiveNextAlignment ||
                counterfactualCapacityChoice)''')
 return source


def apply_cj(source):
 source=_replace(source,'''        let predictedNextClass = predictEarlyNextGeometricSize(length)
        var gap = bestFittingGap(length, highSide, sizeCohort)''',
 '''        let predictedNextClass = predictEarlyNextGeometricSize(length)
        let ordinaryRequest = !parityCohortMode && !alternatingDeleteMode &&
            !runLeftActive && !additiveNextAlignment && !lifoStackLane &&
            !hasLifoDeletionConfidence() && !sameSizeRun &&
            predictedNextClass <= length
        if (ordinaryRequest) { highSide = false }
        var gap: Int64 = 0
        if (ordinaryRequest) {
            let fitting = freeBySize.lower(Key(length, 0))
            if (fitting != 0) { gap = freeByStart.find(Key(freeBySize.keyB(fitting))) }
        } else {
            gap = bestFittingGap(length, highSide, sizeCohort)
        }''')
 source=_replace(source,'''            let selectedStart = if (additiveNextAlignment || counterfactualCapacityChoice) { freeByStart.keyA(gap) }''',
 '''            let selectedStart = if (ordinaryRequest || additiveNextAlignment || counterfactualCapacityChoice) { freeByStart.keyA(gap) }''')
 return source
