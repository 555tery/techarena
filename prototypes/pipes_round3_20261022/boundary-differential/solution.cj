package boundary_differential
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
// Native storage owned by one object; growth releases old memory immediately.
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

func birth(index: BoundaryIndex, reference: ArrayList<Pipe>, start: Int64, length: Int64): Int64 {
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
