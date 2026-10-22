"""Prepared round3 coalescence-side proxy; pure CPP/Cangjie source transforms.

Preserve the same special-mode exclusions as lifetime-side, act only above
4096 active pipes (MC disabled), and reuse an already-fitted hazard model:
causalRiskReady && !primalModelDirty && primalStep-primalModelStep<64.
Never call ensure/fit, numeric DP, materialization, MC, or allocate a shadow.
Require >=32 recent deletions, recent demand, 0<slack, gap<=512, both adjacent
active pipes, and unequal supported relative lifetime risks.

For residual gap r and neighboring pipe plus its outside free gap of length n,
B(r,n)=sum recentFrequency[q] for max(r,n)<q<=min(40,r+n).
This counts newly admitted request sizes after that neighboring pipe dies.
Compare B_left*risk_left with B_right*risk_right. Keep the residual gap by the
larger weighted bonus; strict eps1e-9 only. Weighted ties keep parent side.
Raw equal bonuses with unequal risks can signal a change. Missing-neighbor
cases abstain. This is a one-deletion proxy, not calibrated expected gain.

No current candidate files, histories, gap selection, digging, RNG or MC budget
are modified. The transformer does no I/O, compilation, solver execution or
experiment registration. Intended for a separately authorized future round.
"""

def _replace(source,old,new):
 assert source.count(old)==1,(old[:120],source.count(old))
 return source.replace(old,new)

_CPP_HELPER='''    double coalescenceCapacityBonus(std::int64_t remaining, std::int64_t neighborSpan) const {
        const auto lower = std::max(remaining, neighborSpan) + 1;
        const auto upper = std::min<std::int64_t>(40, remaining + neighborSpan);
        double bonus = 0.0;
        for (auto request = lower; request <= upper; ++request) {
            bonus += static_cast<double>(recentFrequency[static_cast<std::size_t>(request)]);
        }
        return bonus;
    }

    bool chooseCoalescenceSide(StartIter gap, int length, bool baselineHighSide) {
        if (activePipeCount <= kMcMaxActivePipes || !causalRiskReady ||
            primalModelDirty || primalStep - primalModelStep >= 64 ||
            primalRecentDeletes < 32 || !hasRecentPrimalDemand()) return baselineHighSide;
        const auto gapLength = gap->second - gap->first;
        if (gapLength <= length || gapLength > kPrimalGapValueCap) return baselineHighSide;
        const auto left = activeByEnd.find(gap->first);
        if (left == activeByEnd.end()) return baselineHighSide;
        const auto right = activeByEnd.upper_bound(gap->second);
        if (right == activeByEnd.end()) return baselineHighSide;
        const auto& leftPipe = pipes[static_cast<std::size_t>(left->second)];
        const auto& rightPipe = pipes[static_cast<std::size_t>(right->second)];
        if (rightPipe.start != gap->second) return baselineHighSide;
        const double leftRisk = lifetimeModel.existingRisk(left->second);
        const double rightRisk = lifetimeModel.existingRisk(right->second);
        if (leftRisk == rightRisk) return baselineHighSide;
        std::int64_t leftSpan = leftPipe.length;
        auto leftOutside = freeByStart.lower_bound(leftPipe.start);
        if (leftOutside != freeByStart.begin()) {
            --leftOutside;
            if (leftOutside->second == leftPipe.start) {
                leftSpan += leftOutside->second - leftOutside->first;
            }
        }
        std::int64_t rightSpan = rightPipe.length;
        const auto rightOutside = freeByStart.find(rightPipe.start + rightPipe.length);
        if (rightOutside != freeByStart.end()) {
            rightSpan += rightOutside->second - rightOutside->first;
        }
        const auto remaining = gapLength - length;
        const double leftScore = coalescenceCapacityBonus(remaining, leftSpan) * leftRisk;
        const double rightScore = coalescenceCapacityBonus(remaining, rightSpan) * rightRisk;
        // New-left leaves the residual gap adjacent to the right pipe.
        if (rightScore > leftScore + 1e-9) return false;
        if (leftScore > rightScore + 1e-9) return true;
        return baselineHighSide;
    }

'''

_CJ_HELPER='''    @OverflowWrapping
    public func coalescenceCapacityBonus(remaining: Int64, neighborSpan: Int64): Float64 {
        let lower = iMax(remaining, neighborSpan) + 1
        let upper = iMin(40, remaining + neighborSpan)
        var bonus: Float64 = 0.0
        if (lower <= upper) {
            for (request in lower..(upper + 1)) { bonus += Float64(recentFrequency[request]) }
        }
        return bonus
    }

    @OverflowWrapping
    public func chooseCoalescenceSide(gap: Int64, length: Int64, baselineHighSide: Bool): Bool {
        if (activePipeCount <= kMcMaxActivePipes || !causalRiskReady ||
            primalModelDirty || primalStep - primalModelStep >= 64 ||
            primalRecentDeletes < 32 || !hasRecentPrimalDemand()) { return baselineHighSide }
        let start = freeByStart.keyA(gap)
        let end = freeByStart.value(gap)
        let gapLength = end - start
        if (gapLength <= length || gapLength > kPrimalGapValueCap) { return baselineHighSide }
        let left = activeByEnd.find(Key(start))
        if (left == 0) { return baselineHighSide }
        let right = activeByEnd.upper(Key(end))
        if (right == 0) { return baselineHighSide }
        let leftPipe = pipes[activeByEnd.value(left)]
        let rightPipe = pipes[activeByEnd.value(right)]
        if (rightPipe.start != end) { return baselineHighSide }
        let leftRisk = lifetimeModel.existingRisk(activeByEnd.value(left))
        let rightRisk = lifetimeModel.existingRisk(activeByEnd.value(right))
        if (leftRisk == rightRisk) { return baselineHighSide }
        var leftSpan = leftPipe.length
        var leftOutside = freeByStart.lower(Key(leftPipe.start))
        if (leftOutside != freeByStart.first()) {
            leftOutside = freeByStart.prev(leftOutside)
            if (freeByStart.value(leftOutside) == leftPipe.start) {
                leftSpan += freeByStart.value(leftOutside) - freeByStart.keyA(leftOutside)
            }
        }
        var rightSpan = rightPipe.length
        let rightOutside = freeByStart.find(Key(rightPipe.start + rightPipe.length))
        if (rightOutside != 0) {
            rightSpan += freeByStart.value(rightOutside) - freeByStart.keyA(rightOutside)
        }
        let remaining = gapLength - length
        let leftScore = coalescenceCapacityBonus(remaining, leftSpan) * leftRisk
        let rightScore = coalescenceCapacityBonus(remaining, rightSpan) * rightRisk
        if (rightScore > leftScore + 1e-9) { return false }
        if (leftScore > rightScore + 1e-9) { return true }
        return baselineHighSide
    }

'''


def apply_cpp(source):
 source=_replace(source,'    double causalPrimalLoss(StartIter gap, int length, bool highSide,',
 _CPP_HELPER+'    double causalPrimalLoss(StartIter gap, int length, bool highSide,')
 source=_replace(source,'''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);''',
 '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            if (activePipeCount > kMcMaxActivePipes && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice &&
                !alternatingDeleteMode && !parityCohortMode &&
                !cohortSlabActive && !lifoStackLane &&
                observedRunCount < static_cast<int>(kSameLengthRightRun)) {
                highSide = chooseCoalescenceSide(gap, length, highSide);
            }
            start = consumeAtSide(gap, length, highSide);''')
 return source


def apply_cj(source):
 source=_replace(source,
 '    @OverflowWrapping\n    public func causalPrimalLoss(gap: Int64, length: Int64, highSide: Bool, modelLimit: Int64, freshRisk: Float64): Float64 {',
 _CJ_HELPER+'    @OverflowWrapping\n    public func causalPrimalLoss(gap: Int64, length: Int64, highSide: Bool, modelLimit: Int64, freshRisk: Float64): Float64 {')
 source=_replace(source,'''            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }
            start = consumeAtSide(gap, length, highSide)''',
 '''            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }
            if (activePipeCount > kMcMaxActivePipes && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice &&
                !alternatingDeleteMode && !parityCohortMode &&
                !cohortSlabActive && !lifoStackLane &&
                observedRunCount < kSameLengthRightRun) {
                highSide = chooseCoalescenceSide(gap, length, highSide)
            }
            start = consumeAtSide(gap, length, highSide)''')
 return source
