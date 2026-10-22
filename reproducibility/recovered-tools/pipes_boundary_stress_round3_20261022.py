"""Second independent Cj stress harness for the pinned BoundaryIndex pilot.

No import-time work, no build/run, no solver and no production transformation.
second_harness() reuses EXACTLY the unchanged pinned BoundaryIndex class literal.

Case A:200000 live PIDs ->400000 unique endpoint keys, forcing cap1048576 and
both Int32 vectors to their maximum needed powers. Reference alive flags plus
closed-form coordinates give O(1) expected roles. Deletes are a coprime
permutation, sampled roles are checked during mutation, and every original key
is checked empty afterwards. No O(history^2) reference verification.

Case B:200000 sequential historical PIDs, at most4096 active slots, repeated
coordinate reuse and varying lengths. Exact sampled endpoint roles use the slot
PID and its Pipe record. Rare radix order is compared to increasing slot order
in O(active), including after sparse late historical IDs and swap-deletions.
At the end every possible reused endpoint coordinate is checked empty.

The two instances are independent; both use the production bound PID<=200000.
Common negative sentinels -1/-37 are checked. Current production lookups use
nonnegative gap boundaries; arbitrary out-of-Int32-domain negative queries are
NOT promised to work, since truncated coordinates can alias valid positive keys.
These stress sources carry no native timing or correctness claim until evaluator
compiles/runs them. Parent transformer and its first harness remain byte-identical.
"""
from pathlib import Path
import hashlib
import importlib.util

PARENT=Path('/tmp/pipes_boundary_hash_round3_20261022.py')
PARENT_SHA='0ba2a1116f5307e5db4598e78a95d9e5757a0695a44601f36ab390de49415805'

_TESTS=r'''func checkNegativeSentinels(index: BoundaryIndex): Unit {
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
'''


def second_harness():
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA,'BoundaryIndex parent changed'
    spec=importlib.util.spec_from_file_location('boundary_stress_pinned_parent',PARENT)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    return parent._HARNESS_PREFIX+parent._CLASSES+_TESTS
