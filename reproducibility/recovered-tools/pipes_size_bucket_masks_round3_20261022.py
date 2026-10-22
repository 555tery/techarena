"""Pure Cangjie next-set-bit pilot AFTER handles -> size_buckets_round3.

No imports, IO, builds, solver runs or changes to prior transformers. This patch
uses primitive UInt64 &, |, !, >>, << only. SDK1.0.5 std.math.trailingZeros(UInt64)
exists, but the installed arm64 library disassembly shows a shift loop; no such
function, intrinsic, foreign API or new dependency is called here.

Two UInt64 occupancy masks represent sizes1..64 and65..80. A bit is set only on
first insertion into an empty bucket and cleared only before erasing its last
member. Changing one endpoint of a still nonempty bucket leaves the bit set.
AVL stable-ID/transplant invariants remain those of the parent; clones copy both
masks along with independent first/last arrays. No fresh arrays or tables.

Lower-bound filtering uses separate low/high branches: low word shifts0..63;
high word shifts0..15; minimum81 goes directly to the old >80 AVL group. There is
NEVER shift64. For a nonzero filtered word, six fixed tests32/16/8/4/2/1 locate
its lowest set bit, then exactly one cached first-node array entry is read.
Returned group IDs, first oversize group, last-node address tie-breaks, age
selection, scores, FP order and RNG are unchanged.

Overheads: two UInt64 fields=16 scalar payload bytes per IntOrderedMap, including
nonpolicy maps; no new heap allocation. Policy empty<->nonempty transitions add
one bit update, map clone adds two scalar copies. Queries replace up to80 empty
bucket probes with at most two word filters plus six binary tests and one array
read. Dense groups can pay more arithmetic than the old immediate array hit;
this is a fixed speed-screen candidate, not a measured speedup.

Touchpoints only: two fields, recordSizeBucket empty case, forgetSizeBucket sole
member case, clone's existing bucket copy block, and the first-group query plus
one private fixed binary helper. Original lookup/score/MC code stays intact.
"""


def _once(source,old,new):
    if source.count(old)!=1:
        raise ValueError(f'Expected one anchor; found {source.count(old)}: {old[:120]!r}')
    return source.replace(old,new,1)


_OLD_QUERY='''    @OverflowWrapping
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
    }'''
_NEW_QUERY='''    // Called only for a nonzero filtered word; base is its legal size origin.
    @OverflowWrapping
    private func firstSetSizeBucket(initialBits: UInt64, base: Int64): Int64 {
        var bits = initialBits
        var length = base
        if ((bits & UInt64(0xffffffff)) == 0) { bits = bits >> 32; length += 32 }
        if ((bits & UInt64(0xffff)) == 0) { bits = bits >> 16; length += 16 }
        if ((bits & UInt64(0xff)) == 0) { bits = bits >> 8; length += 8 }
        if ((bits & UInt64(0xf)) == 0) { bits = bits >> 4; length += 4 }
        if ((bits & UInt64(0x3)) == 0) { bits = bits >> 2; length += 2 }
        if ((bits & UInt64(0x1)) == 0) { length++ }
        return sizeBucketFirst[length]
    }

    @OverflowWrapping
    public func firstSizeGroupAtOrAbove(minimum: Int64): Int64 {
        if (sizeBucketFirst.size == 0 || minimum < 1 || minimum > 81) { throw IllegalStateException("Policy size bucket query") }
        if (root == 0) { return 0 }
        if (minimum <= 64) {
            let bits = sizeBucketMaskLow >> (minimum - 1)
            if (bits != 0) { return firstSetSizeBucket(bits, minimum) }
        }
        if (minimum <= 80) {
            let highMinimum = iMax(65, minimum)
            let bits = sizeBucketMaskHigh >> (highMinimum - 65)
            if (bits != 0) { return firstSetSizeBucket(bits, highMinimum) }
        }
        return lower(Key(81, 0))
    }'''


def apply_cj(source):
    if source.count('public var freeBySize = IntOrderedMap(0, true)')!=1:
        raise ValueError('Apply handles -> size_buckets_round3 before mask transformer')
    a=source.index('public class IntOrderedMap {');b=source.index('public class Ring<T> {',a)
    tree=source[a:b]
    tree=_once(tree,'    private var sizeBucketLast = Array<Int64>()',
        '    private var sizeBucketLast = Array<Int64>()\n'
        '    private var sizeBucketMaskLow: UInt64 = 0\n'
        '    private var sizeBucketMaskHigh: UInt64 = 0')
    tree=_once(tree,'''            sizeBucketFirst[k.a] = node
            sizeBucketLast[k.a] = node
            return''','''            sizeBucketFirst[k.a] = node
            sizeBucketLast[k.a] = node
            if (k.a <= 64) { sizeBucketMaskLow = sizeBucketMaskLow | (UInt64(1) << (k.a - 1)) }
            else { sizeBucketMaskHigh = sizeBucketMaskHigh | (UInt64(1) << (k.a - 65)) }
            return''')
    tree=_once(tree,'''            sizeBucketFirst[length] = 0
            sizeBucketLast[length] = 0
        } else if''','''            sizeBucketFirst[length] = 0
            sizeBucketLast[length] = 0
            if (length <= 64) { sizeBucketMaskLow = sizeBucketMaskLow & (!(UInt64(1) << (length - 1))) }
            else { sizeBucketMaskHigh = sizeBucketMaskHigh & (!(UInt64(1) << (length - 65))) }
        } else if''')
    tree=_once(tree,'''            result.sizeBucketFirst = sizeBucketFirst.clone()
            result.sizeBucketLast = sizeBucketLast.clone()''','''            result.sizeBucketFirst = sizeBucketFirst.clone()
            result.sizeBucketLast = sizeBucketLast.clone()
            result.sizeBucketMaskLow = sizeBucketMaskLow
            result.sizeBucketMaskHigh = sizeBucketMaskHigh''')
    tree=_once(tree,_OLD_QUERY,_NEW_QUERY)
    return source[:a]+tree+source[b:]
