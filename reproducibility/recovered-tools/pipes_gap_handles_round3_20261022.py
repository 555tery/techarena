"""Pure Cangjie round3 speed transformer; no writes/builds/solver runs.

Size/age/cohort policy indices already have one Int64 value per entry. Store the
stable freeByStart node ID there rather than unused zero. Candidate Key.c carries
that same ID through selection; Key.a/b, iteration/address order, scores, floating
point operations and RNG are unchanged. No new tables or fields are introduced.

Handle invariant for every READABLE live policy entry: value is a live stable
freeByStart ID whose key is the policy key's start and whose length is its size.
* addFreeGap erases merged nodes/indices, then puts every new index with added ID.
* consumeAtSide erases old index entries, preserves the freeByStart node ID while
  shrinking its key/end between neighbors, then inserts indices with that ID.
* eraseGap removes every readable index entry before erasing/reusing start ID.
* enableParityCohortMode walks stable live start IDs, builds new policy handles,
  then makes one-way transition. Frozen full/age trees may contain stale values
  afterwards, but no subsequent path reads those trees (existing invariant).
* importObserved constructs gaps only through addFreeGap; no alternate rebuild.
* bestFittingGapFromSet and chooseCausalLifetimeGap do not mutate gap geometry.
* recycleRecent takes BOTH address and handle from the selected age entry.

Proof concerns logical equality. Full response hashes and native resource/speed
checks remain necessary before adoption. The frozen release is never modified.
"""


def _once(source,old,new):
    if source.count(old)!=1:
        raise ValueError(f'Expected one anchor, found {source.count(old)}: {old[:120]!r}')
    return source.replace(old,new,1)


def _method(source,begin,end,replacements):
    if source.count(begin)!=1:raise ValueError(f'Method anchor not unique: {begin!r}')
    a=source.index(begin);b=source.index(end,a);part=source[a:b]
    for old,new in replacements:part=_once(part,old,new)
    return source[:a]+part+source[b:]


def apply_cj(source):
    # Every policy-index creation/replacement site. Stable start-node handles,
    # not policy-node handles, are the payloads of the synchronized indices.
    for old,new in [
        ('freeBySizeCohort[cohort].put(Key(remainderLength, remainderStart), 0)',
         'freeBySizeCohort[cohort].put(Key(remainderLength, remainderStart), it)'),
        ('freeBySizeShared.put(Key(remainderLength, remainderStart), 0)',
         'freeBySizeShared.put(Key(remainderLength, remainderStart), it)'),
        ('freeBySize.put(Key(remainderLength, remainderStart), 0)',
         'freeBySize.put(Key(remainderLength, remainderStart), it)'),
        ('freeBySizeAge.put(Key(remainderLength, freedAt, remainderStart), 0)',
         'freeBySizeAge.put(Key(remainderLength, freedAt, remainderStart), it)'),
        ('freeBySizeCohort[cohort].put(Key(gapLength, start), 0)',
         'freeBySizeCohort[cohort].put(Key(gapLength, start), it)'),
        ('freeBySizeShared.put(Key(gapLength, start), 0)',
         'freeBySizeShared.put(Key(gapLength, start), it)'),
        ('freeBySizeCohort[mergedCohort].put(Key(gapLength, mergedStart), 0)',
         'freeBySizeCohort[mergedCohort].put(Key(gapLength, mergedStart), added)'),
        ('freeBySizeShared.put(Key(gapLength, mergedStart), 0)',
         'freeBySizeShared.put(Key(gapLength, mergedStart), added)'),
        ('freeBySize.put(Key(gapLength, mergedStart), 0)',
         'freeBySize.put(Key(gapLength, mergedStart), added)'),
        ('freeBySizeAge.put(Key(gapLength, mergedFreedAt, mergedStart), 0)',
         'freeBySizeAge.put(Key(gapLength, mergedFreedAt, mergedStart), added)'),
    ]:source=_once(source,old,new)
    source=_method(source,
        '    public func bestFittingGapFromSet(gaps: IntOrderedMap, length: Int64, highSide: Bool): Int64 {',
        '    public func hasSameLengthRecentRun(length: Int64): Bool {',[
            ('if (recentLengths.size == 0) { return freeByStart.find(Key(gaps.keyB(it))) }',
             'if (recentLengths.size == 0) { return gaps.value(it) }'),
            ('            var representativeStart = gaps.keyB(candidate)',
             '            var representativeStart = gaps.keyB(candidate)\n'
             '            var representativeNode = gaps.value(candidate)'),
            ('                representativeStart = freeBySizeAge.keyC(age)',
             '                representativeStart = freeBySizeAge.keyC(age)\n'
             '                representativeNode = freeBySizeAge.value(age)'),
            ('            candidates.add(Key(gapLength, representativeStart))',
             '            candidates.add(Key(gapLength, representativeStart, representativeNode))'),
            ('                legacyBest = freeByStart.find(Key(representativeStart))',
             '                legacyBest = candidateKey.c'),
            ('                            primalBest = freeByStart.find(Key(candidateKey.b))',
             '                            primalBest = candidateKey.c'),
        ])
    source=_method(source,
        '    public func chooseCausalLifetimeGap(candidates: ArrayList<Key>, length: Int64, highSide: Bool, baselineGap: Int64): Int64 {',
        '    public func primalGapLoss(gapLength: Int64, length: Int64): Float64 {',[
            ('                challenger = freeByStart.find(Key(representativeStart))',
             '                challenger = candidate.c'),
        ])
    return source
