"""Pure Cangjie-only IntRing.clone optimization, no IO/builds on import.

Invariant: for every 0<=i<count, abstract[i] = data[(head+i)%data.size].
The replacement independently copies the complete Int64 backing Array and keeps
head/count. Unused cells and capacity are private, hence unobservable. Array
contains values of Int64, so Array.clone cannot retain any mutable element alias.
Pushing/popping use only copied cells plus head/count; source and clone mutations
remain independent. Verified in the primary v1.0.5 runtime source:
https://github.com/cangjielanguage/cangjie_runtime/blob/v1.0.5/std/libs/std/core/array.cj#L254-L261
Array.clone allocates a new RawArray and intrinsicBuiltInCopyTo copies len values. LengthHistory.clone and Ring<T>.clone are left untouched.

Predeclared pilot gate, before any native results:
* identical complete response hashes on every checked input;
* at least 10 paired heavy native runs;
* geometric mean candidate/current CPU <=0.99;
* every candidate native run CPU <5s and RSS <256MiB.
No adoption from build success or from standalone copy microbenchmarks.
"""

OLD='''    public func clone(): IntRing {
        let result = IntRing(zero)
        for (i in 0..count) { result.pushBack(get(i)) }
        return result
    }'''
NEW='''    public func clone(): IntRing {
        let result = IntRing(zero)
        // Copy Int64 values into independent backing storage; preserve ring order.
        result.data = data.clone()
        result.head = head
        result.count = count
        return result
    }'''


def apply_cj(source):
    if source.count(OLD)!=1:
        raise ValueError(f'Expected one IntRing.clone anchor; found {source.count(OLD)}')
    return source.replace(OLD,NEW,1)
