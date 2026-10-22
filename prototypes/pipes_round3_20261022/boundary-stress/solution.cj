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

func checkNegativeSentinels(index: BoundaryIndex): Unit {
    if (index.startingAt(-1) != 0 || index.endingAt(-1) != 0 ||
        index.startingAt(-37) != 0 || index.endingAt(-37) != 0) { throw Exception("Negative endpoint sentinel") }
}
func checkFullRole(index: BoundaryIndex, alive: Array<Bool>, pid: Int64): Unit {
    let start = 10 + pid * 41
    let length = 1 + pid % 40
    let expected: Int64 = if (alive[pid]) { pid } else { 0 }
    if (index.startingAt(start) != expected || index.endingAt(start + length) != expected ||
        index.endingAt(start) != 0 || index.startingAt(start + length) != 0) { throw Exception("Full-capacity sampled role") }
}
func fullCapacityCase(): Unit {
    let index = BoundaryIndex()
    let alive = Array<Bool>(200001, repeat: false)
    for (pid in 1..=200000) {
        index.addPipe(pid, 10 + pid * 41, 1 + pid % 40)
        alive[pid] = true
        if (pid % 1024 == 0) {
            if (index.activeCount != pid) { throw Exception("Full-capacity birth count") }
            for (k in 0..16) { checkFullRole(index, alive, 1 + (pid * 7919 + k * 104729) % pid) }
        }
    }
    if (index.activeCount != 200000) { throw Exception("Maximum active count") }
    checkNegativeSentinels(index)
    // Linear total work; every key is verified once before deletion.
    for (pid in 1..=200000) {
        if (index.startingAt(10 + pid * 41) != pid || index.endingAt(10 + pid * 41 + 1 + pid % 40) != pid) { throw Exception("Maximum table full reference") }
    }
    // gcd(7919,200000)=1: interior/last dense and hash records are removed in a
    // permutation unrelated to insertion, probing, endpoint or physical order.
    for (step in 0..200000) {
        let pid = 1 + (step * 7919) % 200000
        index.removePipe(pid, 10 + pid * 41, 1 + pid % 40)
        alive[pid] = false
        if (step % 1024 == 0) {
            if (index.activeCount != 199999 - step) { throw Exception("Full-capacity death count") }
            checkFullRole(index, alive, pid)
            for (k in 0..16) { checkFullRole(index, alive, 1 + (step * 104729 + k * 7919) % 200000) }
        }
    }
    if (index.activeCount != 0) { throw Exception("Full-capacity final count") }
    for (pid in 1..=200000) {
        if (index.startingAt(10 + pid * 41) != 0 || index.endingAt(10 + pid * 41 + 1 + pid % 40) != 0) { throw Exception("Full-capacity final nonempty key") }
    }
    println("BOUNDARY_FULL_200000_OK")
}
func checkSlotRole(index: BoundaryIndex, reference: ArrayList<Pipe>, slots: Array<Int64>, slot: Int64): Unit {
    let start = 50000000 + slot * 41
    let pid = slots[slot]
    if (index.startingAt(start) != pid || index.endingAt(start) != 0) { throw Exception("Churn sampled start role") }
    if (pid != 0) {
        let p = reference[pid]
        if (!p.active || index.endingAt(start + p.length) != pid || index.startingAt(start + p.length) != 0) { throw Exception("Churn sampled end role") }
    }
}
func checkSparseRadix(index: BoundaryIndex, reference: ArrayList<Pipe>, slots: Array<Int64>): Unit {
    let actual = index.sortedActiveByStart(reference)
    var expectedCount: Int64 = 0
    for (slot in 0..4096) {
        let pid = slots[slot]
        if (pid == 0) { continue }
        if (expectedCount >= actual.size || Int64(actual[expectedCount]) != pid) { throw Exception("Sparse-history radix reference") }
        checkSlotRole(index, reference, slots, slot)
        expectedCount++
    }
    if (actual.size != expectedCount || index.activeCount != expectedCount) { throw Exception("Sparse-history radix count") }
}
func sparseHistoryCase(): Unit {
    let index = BoundaryIndex()
    let reference = ArrayList<Pipe>(); reference.add(Pipe())
    let slots = Array<Int64>(4096, repeat: 0)
    for (pid in 1..=200000) {
        let slot = (pid - 1) % 4096
        let old = slots[slot]
        var oldLength: Int64 = 0
        if (old != 0) {
            var previous = reference[old]
            oldLength = previous.length
            index.removePipe(old, previous.start, previous.length)
            previous.active = false
            reference[old] = previous
        }
        let start = 50000000 + slot * 41
        let length = 1 + (pid * 17 + slot) % 40
        if (reference.size != pid) { throw Exception("Import-equivalent PID history") }
        reference.add(Pipe(start, length, true, 0))
        index.addPipe(pid, start, length)
        slots[slot] = pid
        if (pid % 997 == 0) {
            let expectedCount: Int64 = if (pid < 4096) { pid } else { 4096 }
            if (index.activeCount != expectedCount) { throw Exception("Churn active count") }
            if (oldLength != 0) {
                let expectedEnd: Int64 = if (oldLength == length) { pid } else { 0 }
                if (index.endingAt(start + oldLength) != expectedEnd) { throw Exception("Reused coordinate old end") }
            }
            for (k in 0..16) { checkSlotRole(index, reference, slots, (pid * 37 + k * 257) % 4096) }
        }
        if (pid == 1024 || pid == 4096 || pid == 65536 || pid == 131072 || pid == 199999 || pid == 200000) {
            checkSparseRadix(index, reference, slots)
        }
    }
    if (reference.size != 200001) { throw Exception("Sparse maximum history") }
    for (slot in 0..4096) { if (slots[slot] <= 190000) { throw Exception("Sparse PID history was not exercised") } }
    checkNegativeSentinels(index)
    // gcd(2053,4096)=1; exercise swap-delete with sparse historical PIDs.
    for (step in 0..4096) {
        let slot = (step * 2053) % 4096
        let pid = slots[slot]
        var pipe = reference[pid]
        index.removePipe(pid, pipe.start, pipe.length)
        pipe.active = false; reference[pid] = pipe; slots[slot] = 0
        if (step % 509 == 0) { checkSparseRadix(index, reference, slots) }
    }
    if (index.activeCount != 0 || index.sortedActiveByStart(reference).size != 0) { throw Exception("Sparse final dense nonempty") }
    for (slot in 0..4096) {
        let start = 50000000 + slot * 41
        if (index.startingAt(start) != 0) { throw Exception("Sparse final start nonempty") }
        for (length in 1..=40) { if (index.endingAt(start + length) != 0) { throw Exception("Sparse final reused end nonempty") } }
    }
    println("BOUNDARY_SPARSE_HISTORY_200000_OK")
}
main() {
    fullCapacityCase()
    sparseHistoryCase()
    println("BOUNDARY_STRESS_DIFFERENTIAL_OK")
}
