"""Pure Cangjie exact-speed candidate; only skip a redundant gap lookup.

The audited release names the Monte Carlo selector chooseGapWithRollout.
Its real allocator writes are only mcDecisionsUsed, mcRolloutsRun and randomState;
topGapCandidates/sampleScenario read real gap/history state. makeRolloutState
creates a separate gaps tree populated with value-type SimGap records, and every
trial mutates base.deepCopy(). No real gap is erased, inserted, resized or reused
between the original gap selection and consumeAtSide. Alignment shortcuts also
return the current gap's start without changing gap geometry.

Inside the existing `gap != 0` block, when selectedStart equals keyA(gap), the
pure old find(Key(selectedStart)) must return that same live stable node ID.
Retain the known ID in that case; otherwise execute the exact old lookup.
Negative-result behavior is unchanged. No MC/score/FP/RNG or history code changes.
There are no new fields or tables. On the common unchanged choice, one constant
key read replaces an AVL search; changed choices add one key read before lookup.
This does not by itself establish a measured speedup. No import-time IO/builds.
"""

OLD='            if (selectedStart >= 0) { gap = freeByStart.find(Key(selectedStart)) }'
NEW='            if (selectedStart >= 0 && selectedStart != freeByStart.keyA(gap)) { gap = freeByStart.find(Key(selectedStart)) }'


def apply_cj(source):
    if source.count(OLD)!=1:
        raise ValueError(f'Expected one selectedStart lookup anchor, found {source.count(OLD)}')
    a=source.index('public class Allocator {')
    a=source.index('    public func place(length: Int64): Unit {',a)
    b=source.index('    public func remove(pid: Int64): Unit {',a)
    if source[a:b].count(OLD)!=1:
        raise ValueError('Lookup anchor is outside Allocator.place')
    return source.replace(OLD,NEW,1)
