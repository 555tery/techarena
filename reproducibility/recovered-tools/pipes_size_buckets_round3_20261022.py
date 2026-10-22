"""Pure Cangjie fixed pilot AFTER gap_handles_round3; no I/O/build/solver.

Enable first/last policy-node-ID buckets for exact integer sizes1..80 in only
four policy maps: full, shared, cohort0, cohort1. freeByStart/age/active maps keep
empty Arrays, hence no bucket backing allocations. Existing map payloads still
hold stable freeByStart IDs from the preceding handles transformer.

Touchpoints: two empty-array fields and one constructor overload; four enabled
constructor expressions; put after insertion; eraseNode before erase/reuse;
clone copying the two arrays; two read-only bucket query methods; the group
traversal block in bestFittingGapFromSet. No changes to score/FP/RNG/age policy.
The freeByStart-only setKeyValuePreservingOrder path never touches enabled maps.
clear delegates to eraseNode. Existing-key put changes payload only, not bounds.

Exact overheads: each enabled map has2*81 Int64 cells=1296 payload bytes,
four maps=5184 payload bytes, eight backing arrays plus normal Array metadata.
Every IntOrderedMap gains two Array descriptors; nonpolicy descriptors are empty
and allocate no payload. Array-header/descriptor ABI bytes are not assumed here.
Every newly inserted node/erase tests whether the map is bucket-enabled;
nonpolicy maps skip the helper call. New policy insertion compares against at
most2 cached endpoint keys; existing-key put skips maintenance. Erasing an interior member touches no endpoint; deleting a
sole member clears2 cells; deleting one endpoint calls next/prev once before
transplant. Queries linearly inspect a fixed subset of buckets1..80. With sparse
sizes this fixed scan may lose to AVL; no adaptive tuning is included. A policy
map clone copies162 Int64 cells; MC clones OrderedMap<SimGap>, not these maps.

Ordering: enumerate ascending sizes, append EXACTLY the first group whose size
exceeds length+40, then stop. Such oversize group can itself be<=80. Once the
bucket range is exhausted, AVL lower(Key(81,0)) obtains the first >80 group;
confidentRecentAddress obtains its last member with the original upper/prev.
For cached sizes, last is exact lexicographic max (same start tie ordering).
recycleRecent still uses unchanged age upper/prev, address AND handle from age.

Stable-ID proof: AVL rotations/transplant retain IDs of other live nodes. put
registers the new ID after rebalancing; erase updates endpoints before removal
or reuse. clone preserves every node ID and independently copies bound arrays.
No bucket handle survives deletion of the node it references. Production and
current-round sources are never changed. Native response/speed gate is pending.
"""


def _once(source,old,new):
    if source.count(old)!=1:
        raise ValueError(f'Expected one anchor; got {source.count(old)}: {old[:120]!r}')
    return source.replace(old,new,1)


_HELPERS='''    // Bounds contain policy-tree node IDs, not freeByStart payload IDs.
    @OverflowWrapping
    private func recordSizeBucket(node: Int64, k: Key): Unit {
        if (sizeBucketFirst.size == 0 || k.a < 1 || k.a > 80) { return }
        let first = sizeBucketFirst[k.a]
        if (first == 0) {
            sizeBucketFirst[k.a] = node
            sizeBucketLast[k.a] = node
            return
        }
        if (compareKey(k, key(first)) < 0) { sizeBucketFirst[k.a] = node }
        let last = sizeBucketLast[k.a]
        if (compareKey(k, key(last)) > 0) { sizeBucketLast[k.a] = node }
    }

    @OverflowWrapping
    private func forgetSizeBucket(node: Int64): Unit {
        if (sizeBucketFirst.size == 0) { return }
        let length = keyA(node)
        if (length < 1 || length > 80) { return }
        let first = sizeBucketFirst[length]
        let last = sizeBucketLast[length]
        if (first == node && last == node) {
            sizeBucketFirst[length] = 0
            sizeBucketLast[length] = 0
        } else if (first == node) {
            let following = next(node)
            if (following == 0 || keyA(following) != length) { throw IllegalStateException("Size bucket successor") }
            sizeBucketFirst[length] = following
        } else if (last == node) {
            let preceding = prev(node)
            if (preceding == 0 || keyA(preceding) != length) { throw IllegalStateException("Size bucket predecessor") }
            sizeBucketLast[length] = preceding
        }
    }

    @OverflowWrapping
    public func firstSizeGroupAtOrAbove(minimum: Int64): Int64 {
        if (sizeBucketFirst.size == 0 || minimum < 1 || minimum > 81) { throw IllegalStateException("Policy size bucket query") }
        if (root == 0) { return 0 }
        var length = minimum
        while (length <= 80) {
            let node = sizeBucketFirst[length]
            if (node != 0) { return node }
            length++
        }
        return lower(Key(81, 0))
    }

    @OverflowWrapping
    public func lastNodeInSizeGroup(node: Int64): Int64 {
        if (sizeBucketLast.size == 0) { throw IllegalStateException("Policy size bucket last") }
        let length = keyA(node)
        if (length >= 1 && length <= 80) { return sizeBucketLast[length] }
        return prev(upper(Key(length, Int64.Max)))
    }

'''


def apply_cj(source):
    if 'var representativeNode = gaps.value(candidate)' not in source or 'legacyBest = candidateKey.c' not in source:
        raise ValueError('Apply gap_handles_round3 before size_buckets_round3')
    a=source.index('public class IntOrderedMap {');b=source.index('public class Ring<T> {',a)
    tree=source[a:b]
    tree=_once(tree,'    private var vacant = FastIntVector()',
        '    private var vacant = FastIntVector()\n'
        '    private var sizeBucketFirst = Array<Int64>()\n'
        '    private var sizeBucketLast = Array<Int64>()')
    original='''    public init(defaultValue: Int64) {
        zero = defaultValue
        nodes.addNode(Key(0), defaultValue, 0, 0)
    }'''
    tree=_once(tree,original,original+'''
    public init(defaultValue: Int64, policySizeBuckets: Bool) {
        zero = defaultValue
        nodes.addNode(Key(0), defaultValue, 0, 0)
        if (policySizeBuckets) {
            sizeBucketFirst = Array<Int64>(81, repeat: 0)
            sizeBucketLast = Array<Int64>(81, repeat: 0)
        }
    }''')
    tree=_once(tree,'        rebalance(p)\n        return added',
        '        rebalance(p)\n        if (sizeBucketFirst.size != 0) { recordSizeBucket(added, k) }\n        return added')
    begin=tree.index('    public func eraseNode(node: Int64): Unit {')
    finish=tree.index('    public func clone(): IntOrderedMap {',begin)
    erase=tree[begin:finish]
    erase=_once(erase,'        let nodeData = nodes.borrowData()',
        '        if (sizeBucketFirst.size != 0) { forgetSizeBucket(node) }\n        let nodeData = nodes.borrowData()')
    tree=tree[:begin]+erase+tree[finish:]
    tree=_once(tree,'    @OverflowWrapping\n    public func clone(): IntOrderedMap {',
        _HELPERS+'    @OverflowWrapping\n    public func clone(): IntOrderedMap {')
    tree=_once(tree,'        result.vacant = vacant.clone()\n        return result',
        '        result.vacant = vacant.clone()\n'
        '        if (sizeBucketFirst.size != 0) {\n'
        '            result.sizeBucketFirst = sizeBucketFirst.clone()\n'
        '            result.sizeBucketLast = sizeBucketLast.clone()\n'
        '        }\n        return result')
    source=source[:a]+tree+source[b:]
    for old,new in [
        ('public var freeBySize = IntOrderedMap(0)','public var freeBySize = IntOrderedMap(0, true)'),
        ('public var freeBySizeCohort = [IntOrderedMap(0), IntOrderedMap(0)]',
         'public var freeBySizeCohort = [IntOrderedMap(0, true), IntOrderedMap(0, true)]'),
        ('public var freeBySizeShared = IntOrderedMap(0)','public var freeBySizeShared = IntOrderedMap(0, true)'),
    ]:source=_once(source,old,new)
    a=source.index('    public func bestFittingGapFromSet(gaps: IntOrderedMap, length: Int64, highSide: Bool): Int64 {')
    b=source.index('    public func hasSameLengthRecentRun(length: Int64): Bool {',a)
    method=source[a:b]
    method=_once(method,'        let it = gaps.lower(Key(length, 0))',
        '        let it = gaps.firstSizeGroupAtOrAbove(length)')
    method=_once(method,'''            var nextGroup: Int64 = 0
            if (confidentRecentAddress) {
                nextGroup = gaps.upper(Key(gaps.keyA(candidate), Int64.Max))
                candidate = gaps.prev(nextGroup)
            }''','''            if (confidentRecentAddress) {
                candidate = gaps.lastNodeInSizeGroup(candidate)
            }''')
    method=_once(method,'            candidate = if (confidentRecentAddress) { nextGroup } else { gaps.upper(Key(gapLength, Int64.Max)) }',
        '            candidate = gaps.firstSizeGroupAtOrAbove(gapLength + 1)')
    source=source[:a]+method+source[b:]
    return source
