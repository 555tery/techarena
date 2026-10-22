"""Isolated pure Cangjie BoundaryIndex pilot for the 511b core-ring source.

No import-time IO/build/run; existing source/transformers are never mutated.
apply_cj(source) replaces ONLY activeByEnd/activeEndId, all insertion/removal and
import paths, exact left/right boundary lookups, and rare obstacle construction.
MC RolloutState, score/FP/RNG/selection loops remain literal source text.

Primitive native Int32 storage: one hash record [coordinate+1,startPID,endPID],
zero key means empty; coordinate<=100000000 and PID<=200000 fit. A coordinate can
hold both an ending and a starting PID. UInt32 avalanche arithmetic is explicitly
@OverflowWrapping. Capacity is power-of-two and occupancy<=1/2. Linear probing
uses backward-shift deletion; cyclic distances select moves, including wraparound.
Hash home does not change during a deletion. A low load and avalanche reduce
ordinary clusters, but deterministic open addressing has NO worst-case O(1)
guarantee or adversarial-cluster guarantee; only a serial measured pilot is valid.

At <=2*200000 endpoint keys, hash cap<=2^20: steady native hash payload<=12MiB;
rehash old+new<=18MiB. Dense active PIDs + per-total-PID inverse positions each
cap<=2^18 Int32: steady<=2MiB, one expansion's old+new total<=2.5MiB. These buffers
free old allocations immediately; conservative combined transient bound20.5MiB,
excluding small owner objects and rare managed radix scratch. At active<=4096,
radix scratch is two n*Int32 arrays<=32KiB +256 Int64 counts=2KiB +array metadata.
This does not bound total solver RSS; full native qualification remains necessary.

Dense swap-delete is O(1). Rare path copies ONLY dense active PIDs after the
existing active<=4096 gate, then four stable byte passes by start. Nonoverlapping
positive-length pipes have identical strict start/end order, so the old AVL
traversal order is reconstructed exactly. No scan over total PID history occurs
in production. Differential harness references may scan their tiny test history.

Integration touchpoints: allocator fields/init; two normal/slab births; normal
death; import birth/death; hasYoungTailNeighbor; two causal boundary lookups; one
rare obstacle traversal. Final source must contain no activeByEnd/activeEndId.
Use differential_harness() to obtain a standalone Cj1.0.5 test using EXACTLY the
same BoundaryIndex implementation. Required before benchmarks: map differential,
then all Open complete-response hash parity. This module runs neither.
"""

_CLASSES=r'''// Native storage owned by one object; growth releases old memory immediately.
public class BoundaryInt32Vector {
    private var data: CPointer<Int32>
    private var capacity: Int64 = 16
    private var used: Int64 = 0
    public init() {
        data = LibC.malloc<Int32>(count: 16)
        if (data.isNull()) { throw IllegalMemoryException("Boundary vector allocation") }
    }
    ~init() { unsafe { LibC.free(data) } }
    public prop size: Int64 { get() { used } }
    @OverflowWrapping
    public operator func [](index: Int64): Int32 {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Boundary vector index") }
        return unsafe { data.read(index) }
    }
    @OverflowWrapping
    public operator func [](index: Int64, value!: Int32): Unit {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Boundary vector index") }
        unsafe { data.write(index, value) }
    }
    @OverflowWrapping
    public func add(value: Int32): Unit {
        if (used == capacity) {
            let nextCapacity = capacity * 2
            if (nextCapacity > 262144) { throw IllegalMemoryException("Boundary vector cap") }
            let expanded = LibC.malloc<Int32>(count: nextCapacity)
            if (expanded.isNull()) { throw IllegalMemoryException("Boundary vector expansion") }
            unsafe { for (i in 0..used) { expanded.write(i, data.read(i)) } }
            let previous = data
            data = expanded
            capacity = nextCapacity
            unsafe { LibC.free(previous) }
        }
        unsafe { data.write(used, value) }
        used++
    }
    @OverflowWrapping
    public func removeLast(): Int32 {
        if (used == 0) { throw IndexOutOfBoundsException("Boundary vector empty") }
        used--
        return unsafe { data.read(used) }
    }
}

public class BoundaryIndex {
    private var data: CPointer<Int32>
    private var capacity: Int64 = 16
    private var occupied: Int64 = 0
    private let active = BoundaryInt32Vector()
    private let position = BoundaryInt32Vector()
    public init() {
        data = LibC.malloc<Int32>(count: 48)
        if (data.isNull()) { throw IllegalMemoryException("Boundary hash allocation") }
        unsafe { for (i in 0..48) { data.write(i, Int32(0)) } }
        position.add(Int32(-1))
    }
    ~init() { unsafe { LibC.free(data) } }
    public prop activeCount: Int64 { get() { active.size } }
    @OverflowWrapping
    private func home(coordinate: Int64, mask: Int64): Int64 {
        var word = UInt32(coordinate)
        word = (word ^ (word >> 16)) * UInt32(0x7feb352d)
        word = (word ^ (word >> 15)) * UInt32(0x846ca68b)
        word = word ^ (word >> 16)
        return Int64(word & UInt32(mask))
    }
    @OverflowWrapping
    private func slot(coordinate: Int64): Int64 {
        let mask = capacity - 1
        var index = home(coordinate, mask)
        let wanted = Int32(coordinate + 1)
        unsafe {
            while (true) {
                let key = data.read(index * 3)
                if (key == 0 || key == wanted) { break }
                index = (index + 1) & mask
            }
        }
        blackBox(this)
        return index
    }
    @OverflowWrapping
    private func grow(): Unit {
        let nextCapacity = capacity * 2
        if (nextCapacity > 1048576) { throw IllegalMemoryException("Boundary hash cap") }
        let expanded = LibC.malloc<Int32>(count: nextCapacity * 3)
        if (expanded.isNull()) { throw IllegalMemoryException("Boundary hash expansion") }
        unsafe {
            for (i in 0..(nextCapacity * 3)) { expanded.write(i, Int32(0)) }
            let mask = nextCapacity - 1
            for (i in 0..capacity) {
                let key = data.read(i * 3)
                if (key == 0) { continue }
                var target = home(Int64(key) - 1, mask)
                while (expanded.read(target * 3) != 0) { target = (target + 1) & mask }
                expanded.write(target * 3, key)
                expanded.write(target * 3 + 1, data.read(i * 3 + 1))
                expanded.write(target * 3 + 2, data.read(i * 3 + 2))
            }
        }
        let previous = data
        data = expanded
        capacity = nextCapacity
        unsafe { LibC.free(previous) }
        blackBox(this)
    }
    @OverflowWrapping
    private func putBoundary(coordinate: Int64, pid: Int64, role: Int64): Unit {
        if (coordinate < 0 || coordinate > 100000000 || pid <= 0 || pid > 200000) { throw IllegalArgumentException("Boundary domain") }
        var index = slot(coordinate)
        var key = unsafe { data.read(index * 3) }
        if (key == 0 && (occupied + 1) * 2 > capacity) {
            grow()
            index = slot(coordinate)
            key = unsafe { data.read(index * 3) }
        }
        unsafe {
            if (key == 0) {
                data.write(index * 3, Int32(coordinate + 1))
                data.write(index * 3 + 1, Int32(0))
                data.write(index * 3 + 2, Int32(0))
                occupied++
            }
            let previous = data.read(index * 3 + role)
            if (previous != 0) { throw IllegalStateException("Duplicate active endpoint role") }
            data.write(index * 3 + role, Int32(pid))
        }
        blackBox(this)
    }
    @OverflowWrapping
    private func eraseBoundary(coordinate: Int64, pid: Int64, role: Int64): Unit {
        let index = slot(coordinate)
        let mask = capacity - 1
        unsafe {
            if (data.read(index * 3) == 0 || data.read(index * 3 + role) != Int32(pid)) { throw IllegalStateException("Missing endpoint role") }
            data.write(index * 3 + role, Int32(0))
            if (data.read(index * 3 + 1) == 0 && data.read(index * 3 + 2) == 0) {
                var hole = index
                var scan = (hole + 1) & mask
                while (data.read(scan * 3) != 0) {
                    let key = data.read(scan * 3)
                    let origin = home(Int64(key) - 1, mask)
                    if (((scan - origin) & mask) >= ((scan - hole) & mask)) {
                        data.write(hole * 3, key)
                        data.write(hole * 3 + 1, data.read(scan * 3 + 1))
                        data.write(hole * 3 + 2, data.read(scan * 3 + 2))
                        hole = scan
                    }
                    scan = (scan + 1) & mask
                }
                data.write(hole * 3, Int32(0))
                data.write(hole * 3 + 1, Int32(0))
                data.write(hole * 3 + 2, Int32(0))
                occupied--
            }
        }
        blackBox(this)
    }
    @OverflowWrapping
    public func startingAt(coordinate: Int64): Int64 {
        let index = slot(coordinate)
        let result = unsafe { Int64(data.read(index * 3 + 1)) }
        blackBox(this)
        return result
    }
    @OverflowWrapping
    public func endingAt(coordinate: Int64): Int64 {
        let index = slot(coordinate)
        let result = unsafe { Int64(data.read(index * 3 + 2)) }
        blackBox(this)
        return result
    }
    @OverflowWrapping
    public func addPipe(pid: Int64, start: Int64, length: Int64): Unit {
        if (pid != position.size || length <= 0 || length > 40) { throw IllegalStateException("Boundary birth sequence") }
        putBoundary(start, pid, 1)
        putBoundary(start + length, pid, 2)
        position.add(Int32(active.size))
        active.add(Int32(pid))
    }
    @OverflowWrapping
    public func removePipe(pid: Int64, start: Int64, length: Int64): Unit {
        let index = Int64(position[pid])
        if (index < 0 || Int64(active[index]) != pid) { throw IllegalStateException("Boundary inactive PID") }
        eraseBoundary(start, pid, 1)
        eraseBoundary(start + length, pid, 2)
        let last = active.removeLast()
        if (index < active.size) {
            active[index] = last
            position[Int64(last)] = Int32(index)
        }
        position[pid] = Int32(-1)
    }
    @OverflowWrapping
    public func sortedActiveByStart(pipes: ArrayList<Pipe>): Array<Int32> {
        let count = active.size
        if (count > 4096) { throw IllegalStateException("Boundary rare-path scale") }
        var ids = Array<Int32>(count, repeat: Int32(0))
        var scratch = Array<Int32>(count, repeat: Int32(0))
        for (i in 0..count) { ids[i] = active[i] }
        let offsets = Array<Int64>(256, repeat: 0)
        for (pass in 0..4) {
            offsets.fill(0)
            let shift = pass * 8
            for (i in 0..count) {
                let digit = (pipes[Int64(ids[i])].start >> shift) & 255
                offsets[digit]++
            }
            var total: Int64 = 0
            for (digit in 0..256) {
                let frequency = offsets[digit]
                offsets[digit] = total
                total += frequency
            }
            for (i in 0..count) {
                let pid = ids[i]
                let digit = (pipes[Int64(pid)].start >> shift) & 255
                scratch[offsets[digit]] = pid
                offsets[digit]++
            }
            let previous = ids
            ids = scratch
            scratch = previous
        }
        return ids
    }
}

'''


def _once(source,old,new,count=1):
    if source.count(old)!=count:
        raise ValueError(f'Expected {count} anchors, found {source.count(old)}: {old[:120]!r}')
    return source.replace(old,new)


def apply_cj(source):
    source=_once(source,'// Source: allocator.cj\n',_CLASSES+'// Source: allocator.cj\n')
    source=_once(source,'''    public var activeByEnd = IntOrderedMap(0)
    // Synchronized with pipes, including slot 0; inactive PIDs hold 0.
    // AVL erase transplants nodes, so every other live handle remains valid.
    public let activeEndId = FastIntVector()''','''    public let activeEndpoints = BoundaryIndex()''')
    source=_once(source,'pipes.add(Pipe()); activeEndId.add(0); gapOwner.add(0)',
        'pipes.add(Pipe()); gapOwner.add(0)')
    source=_once(source,'activeEndId.add(activeByEnd.put(Key(start + length), pid))',
        'activeEndpoints.addPipe(pid, start, length)',2)
    source=_once(source,'''        activeByEnd.eraseNode(activeEndId[pid])
        activeEndId[pid] = 0''','''        activeEndpoints.removePipe(pid, pipe.start, pipe.length)''')
    source=_once(source,'''        let it = activeByEnd.find(Key(tailStart))
        return it != 0 && rankFromNewestPermille(activeByEnd.value(it)) <= 50''','''        let pid = activeEndpoints.endingAt(tailStart)
        return pid != 0 && rankFromNewestPermille(pid) <= 50''')
    source=_once(source,'''        let left = activeByEnd.find(Key(start))
        if (left != 0) { leftRisk = lifetimeModel.existingRisk(activeByEnd.value(left)) }
        let right = activeByEnd.upper(Key(end))
        if (right != 0 && pipes[activeByEnd.value(right)].start == end) { rightRisk = lifetimeModel.existingRisk(activeByEnd.value(right)) }''','''        let left = activeEndpoints.endingAt(start)
        if (left != 0) { leftRisk = lifetimeModel.existingRisk(left) }
        let right = activeEndpoints.startingAt(end)
        if (right != 0) { rightRisk = lifetimeModel.existingRisk(right) }''')
    source=_once(source,'''        // Non-overlapping positive-length pipes have the same start/end order.
        // Iterating activeByEnd directly yields the C++ sorted obstacle vector.
        var obstacleNode = activeByEnd.first()
        while (obstacleNode != 0) {
            let pid = activeByEnd.value(obstacleNode)
            let pipe = pipes[pid]
            if (pipe.active && !(pipe.length == length && (pid & 1) == predictedDeletedParity)) {
                obstacles.add(Key(pipe.start, pipe.start + pipe.length))
            }
            obstacleNode = activeByEnd.next(obstacleNode)
        }''','''        // The gate above bounds this dense traversal and radix sort by active.
        let obstaclePids = activeEndpoints.sortedActiveByStart(pipes)
        for (obstaclePid in obstaclePids) {
            let pid = Int64(obstaclePid)
            let pipe = pipes[pid]
            if (pipe.active && !(pipe.length == length && (pid & 1) == predictedDeletedParity)) {
                obstacles.add(Key(pipe.start, pipe.start + pipe.length))
            }
        }''')
    source=_once(source,'out.activeEndId.add(out.activeByEnd.put(Key(x + command), id))',
        'out.activeEndpoints.addPipe(id, x, command)')
    source=_once(source,'''            out.activeByEnd.eraseNode(out.activeEndId[id])
            out.activeEndId[id] = 0''','''            out.activeEndpoints.removePipe(id, p.start, p.length)''')
    if 'activeByEnd' in source or 'activeEndId' in source:
        raise ValueError('An endpoint AVL reference remains uncovered')
    return source


_HARNESS_PREFIX='''package boundary_differential
import std.collection.*
import std.math.*
import std.env.*
import std.runtime.*
public struct Pipe {
    public var start: Int64 = 0
    public var length: Int64 = 0
    public var active: Bool = false
    public var sizeCohort: Int64 = 0
    public init() {}
    public init(start: Int64, length: Int64, active: Bool, sizeCohort: Int64) {
        this.start = start; this.length = length; this.active = active; this.sizeCohort = sizeCohort
    }
}
'''
_HARNESS_TESTS=r'''func birth(index: BoundaryIndex, reference: ArrayList<Pipe>, start: Int64, length: Int64): Int64 {
    let pid = reference.size
    reference.add(Pipe(start, length, true, 0))
    index.addPipe(pid, start, length)
    return pid
}
func death(index: BoundaryIndex, reference: ArrayList<Pipe>, pid: Int64): Unit {
    var pipe = reference[pid]
    if (!pipe.active) { throw Exception("Reference inactive PID") }
    index.removePipe(pid, pipe.start, pipe.length)
    pipe.active = false
    reference[pid] = pipe
}
func expectedRole(reference: ArrayList<Pipe>, coordinate: Int64, startRole: Bool): Int64 {
    for (pid in 1..reference.size) {
        let p = reference[pid]
        if (p.active && (if (startRole) { p.start == coordinate } else { p.start + p.length == coordinate })) { return pid }
    }
    return 0
}
func verify(index: BoundaryIndex, reference: ArrayList<Pipe>): Unit {
    let expected = ArrayList<Int64>()
    for (pid in 1..reference.size) {
        let pipe = reference[pid]
        if (index.startingAt(pipe.start) != expectedRole(reference, pipe.start, true) ||
            index.endingAt(pipe.start) != expectedRole(reference, pipe.start, false) ||
            index.startingAt(pipe.start + pipe.length) != expectedRole(reference, pipe.start + pipe.length, true) ||
            index.endingAt(pipe.start + pipe.length) != expectedRole(reference, pipe.start + pipe.length, false)) { throw Exception("Endpoint reference mismatch") }
        if (pipe.active) { expected.add(pid) }
    }
    if (index.activeCount != expected.size) { throw Exception("Dense active count") }
    // Independent stable insertion sort by start, not the production radix code.
    var i: Int64 = 1
    while (i < expected.size) {
        let pid = expected[i]
        var j = i
        while (j > 0 && reference[expected[j - 1]].start > reference[pid].start) {
            expected[j] = expected[j - 1]; j--
        }
        expected[j] = pid; i++
    }
    let actual = index.sortedActiveByStart(reference)
    if (actual.size != expected.size) { throw Exception("Radix size") }
    for (j in 0..actual.size) { if (Int64(actual[j]) != expected[j]) { throw Exception("Radix order") } }
    if (index.startingAt(99999998) != 0 || index.endingAt(99999998) != 0) { throw Exception("Absent endpoint") }
}
@OverflowWrapping
func testHome(coordinate: Int64): Int64 {
    var word = UInt32(coordinate)
    word = (word ^ (word >> 16)) * UInt32(0x7feb352d)
    word = (word ^ (word >> 15)) * UInt32(0x846ca68b)
    word = word ^ (word >> 16)
    return Int64(word & UInt32(15))
}
main() {
    let index = BoundaryIndex()
    let reference = ArrayList<Pipe>(); reference.add(Pipe())
    // Shared boundary: startPID and endPID must survive independent erasure.
    let a = birth(index, reference, 1000, 7)
    let b = birth(index, reference, 1007, 13)
    verify(index, reference)
    death(index, reference, a); verify(index, reference)
    death(index, reference, b); verify(index, reference)
    let reused = birth(index, reference, 1000, 7)
    death(index, reference, reused); verify(index, reference)
    // Four start keys with home15 in the initial16 table force a probe wrap.
    let collisions = ArrayList<Int64>(); var coordinate: Int64 = 10000
    while (collisions.size < 4) {
        if (testHome(coordinate) == 15) { collisions.add(birth(index, reference, coordinate, 1)) }
        coordinate += 100
    }
    verify(index, reference)
    death(index, reference, collisions[1]); verify(index, reference)
    death(index, reference, collisions[3]); verify(index, reference)
    death(index, reference, collisions[0]); verify(index, reference)
    death(index, reference, collisions[2]); verify(index, reference)
    // Repeated growth and import-equivalent sequential births/deaths.
    for (j in 0..256) { birth(index, reference, 100000 + j * 41, 1 + j % 40) }
    verify(index, reference)
    for (pid in 8..reference.size) { if (reference[pid].active && pid % 3 == 0) { death(index, reference, pid) } }
    verify(index, reference)
    for (j in 0..160) {
        let pid = 8 + (j * 53) % 256
        if (reference[pid].active) { death(index, reference, pid) }
        birth(index, reference, 2000000 + j * 41, 1 + j % 40)
    }
    verify(index, reference)
    // Coordinate zero and upper declared bound are legal encoded keys.
    let zero = birth(index, reference, 0, 1)
    let upper = birth(index, reference, 99999999, 1)
    if (index.startingAt(0) != zero || index.endingAt(100000000) != upper) { throw Exception("Coordinate limits") }
    verify(index, reference)
    death(index, reference, zero); death(index, reference, upper)
    verify(index, reference)
    println("BOUNDARY_INDEX_DIFFERENTIAL_OK")
}
'''


def differential_harness():
    return _HARNESS_PREFIX+_CLASSES+_HARNESS_TESTS
