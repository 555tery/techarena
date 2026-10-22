"""Pure independent lifetime hypotheses; no compiler, solver, or data access.

Both switches default False and return the original source byte-for-byte.
 early_lifetime=True: remove only active>4096 from the hazard-fit gate. The
 ordinaryLargeMode caller's 128-active/256-event/32-delete evidence gate and
 ensurePrimalGapValues demand check, age/length priors and confidence stay.
 lifetime_side=True: compare both ends of the final chosen physical gap using
 the existing causalPrimalLoss. Restrict to active>4096, where MC is disabled;
 exclude all structured lane/cohort/alignment modes. Require >=32 recent
 deletions, recent demand, nonzero slack, gap<=512, and freshly ensured model.

No RNG draws, MC calls/budget, gap selection, or digging policy are changed.
C++ optional -DLIFETIME_SIDE_DIAGNOSTICS prints checks/scored/changes to stderr.
Combined mode is deliberately rejected until separately authorized.
"""

def _replace(source,old,new):
 assert source.count(old)==1,(old[:120],source.count(old))
 return source.replace(old,new)

def _switches(early_lifetime,lifetime_side):
 assert isinstance(early_lifetime,bool)and isinstance(lifetime_side,bool)
 if early_lifetime and lifetime_side:raise ValueError('combined lifetime hypotheses are not authorized')

_CPP_HELPER='''    bool chooseCausalLifetimeSide(StartIter gap, int length, bool baselineHighSide) {
#ifdef LIFETIME_SIDE_DIAGNOSTICS
        ++lifetimeSideChecks;
#endif
        if (activePipeCount <= kMcMaxActivePipes || primalRecentDeletes < 32 ||
            !hasRecentPrimalDemand()) return baselineHighSide;
        const auto gapLength = gap->second - gap->first;
        if (gapLength <= length || gapLength > kPrimalGapValueCap) return baselineHighSide;
        const int modelLimit = static_cast<int>(gapLength);
        if (!ensurePrimalGapValues(modelLimit) || !causalRiskReady) return baselineHighSide;
        const double freshRisk = lifetimeModel.newRisk(length);
        const double baselineScore = causalPrimalLoss(
            gap, length, baselineHighSide, modelLimit, freshRisk);
        const double alternativeScore = causalPrimalLoss(
            gap, length, !baselineHighSide, modelLimit, freshRisk);
#ifdef LIFETIME_SIDE_DIAGNOSTICS
        ++lifetimeSideScored;
#endif
        if (alternativeScore + 1e-9 < baselineScore) {
#ifdef LIFETIME_SIDE_DIAGNOSTICS
            ++lifetimeSideChanges;
#endif
            return !baselineHighSide;
        }
        return baselineHighSide;
    }

'''
_CJ_HELPER='''    @OverflowWrapping
    public func chooseCausalLifetimeSide(gap: Int64, length: Int64, baselineHighSide: Bool): Bool {
        if (activePipeCount <= kMcMaxActivePipes || primalRecentDeletes < 32 ||
            !hasRecentPrimalDemand()) { return baselineHighSide }
        let gapLength = freeByStart.value(gap) - freeByStart.keyA(gap)
        if (gapLength <= length || gapLength > kPrimalGapValueCap) { return baselineHighSide }
        if (!ensurePrimalGapValues(gapLength) || !causalRiskReady) { return baselineHighSide }
        // The parent lazily materializes numeric values only for real choices.
        materializePrimalGapValues()
        let freshRisk = lifetimeModel.newRisk(length)
        let baselineScore = causalPrimalLoss(gap, length, baselineHighSide, gapLength, freshRisk)
        let alternativeScore = causalPrimalLoss(gap, length, !baselineHighSide, gapLength, freshRisk)
        return if (alternativeScore + 1e-9 < baselineScore) { !baselineHighSide } else { baselineHighSide }
    }

'''

def apply_cpp(source,early_lifetime=False,lifetime_side=False):
 _switches(early_lifetime,lifetime_side)
 if early_lifetime:
  source=_replace(source,'''        causalRiskReady = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes && expiry > 0.0 &&''',
  '''        causalRiskReady = !parityCohortMode &&
            expiry > 0.0 &&''')
 if lifetime_side:
  source=_replace(source,'class CensoredLifetimeModel {',
  '''#ifdef LIFETIME_SIDE_DIAGNOSTICS
std::uint64_t lifetimeSideChecks = 0;
std::uint64_t lifetimeSideScored = 0;
std::uint64_t lifetimeSideChanges = 0;
#endif

class CensoredLifetimeModel {''')
  source=_replace(source,'    double causalPrimalLoss(StartIter gap, int length, bool highSide,',
  _CPP_HELPER+'    double causalPrimalLoss(StartIter gap, int length, bool highSide,')
  source=_replace(source,'''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);''',
  '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            // MC is disabled above 4096 active pipes. Preserve all special
            // endpoint policies; the helper compares only this chosen gap.
            if (activePipeCount > kMcMaxActivePipes && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice &&
                !alternatingDeleteMode && !parityCohortMode &&
                !cohortSlabActive && !lifoStackLane &&
                observedRunCount < static_cast<int>(kSameLengthRightRun)) {
                highSide = chooseCausalLifetimeSide(gap, length, highSide);
            }
            start = consumeAtSide(gap, length, highSide);''')
  source=_replace(source,'  if(online) cerr<<"reclaimed_reservation_m="',
  '''#ifdef LIFETIME_SIDE_DIAGNOSTICS
  cerr<<"lifetime_side_checks="<<fallback_online::lifetimeSideChecks
      <<" lifetime_side_scored="<<fallback_online::lifetimeSideScored
      <<" lifetime_side_changes="<<fallback_online::lifetimeSideChanges<<'\\n';
#endif
  if(online) cerr<<"reclaimed_reservation_m="''')
 return source

def apply_cj(source,early_lifetime=False,lifetime_side=False):
 _switches(early_lifetime,lifetime_side)
 if early_lifetime:
  source=_replace(source,
  'causalRiskReady = !parityCohortMode && activePipeCount > kMcMaxActivePipes && expiry > 0.0 &&',
  'causalRiskReady = !parityCohortMode && expiry > 0.0 &&')
 if lifetime_side:
  source=_replace(source,
  '    @OverflowWrapping\n    public func causalPrimalLoss(gap: Int64, length: Int64, highSide: Bool, modelLimit: Int64, freshRisk: Float64): Float64 {',
  _CJ_HELPER+'    @OverflowWrapping\n    public func causalPrimalLoss(gap: Int64, length: Int64, highSide: Bool, modelLimit: Int64, freshRisk: Float64): Float64 {')
  source=_replace(source,'''            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }
            start = consumeAtSide(gap, length, highSide)''',
  '''            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }
            // Above 4096 the existing MC call returns without any simulation.
            if (activePipeCount > kMcMaxActivePipes && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice &&
                !alternatingDeleteMode && !parityCohortMode &&
                !cohortSlabActive && !lifoStackLane &&
                observedRunCount < kSameLengthRightRun) {
                highSide = chooseCausalLifetimeSide(gap, length, highSide)
            }
            start = consumeAtSide(gap, length, highSide)''')
 return source
