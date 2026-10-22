#!/usr/bin/env python3
"""Flatten FastKeyVector ownership/storage only; never compile or run it."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE / "candidate-borrows/solution.cj"
OUT = HERE / "candidate-flat-keys"
BASE_SHA = "ee12e7ee8cf506eacbe3558e218af92c6f7a76a13f74604aa49706cbe2d5a8d0"

FLAT = '''public class FastKeyVector {
    private var data: CPointer<Int64>
    private var capacity: Int64 = 16
    private var used: Int64 = 0

    public init() {
        data = LibC.malloc<Int64>(count: 48)
        if (data.isNull()) { throw IllegalMemoryException("Key vector allocation failed") }
    }

    ~init() { unsafe { LibC.free(data) } }

    public prop size: Int64 { get() { used } }

    public operator func [](index: Int64): Key {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Key vector index") }
        let offset = index * 3
        return unsafe { Key(data.read(offset), data.read(offset + 1), data.read(offset + 2)) }
    }

    public operator func [](index: Int64, value!: Key): Unit {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Key vector index") }
        let offset = index * 3
        unsafe {
            data.write(offset, value.a)
            data.write(offset + 1, value.b)
            data.write(offset + 2, value.c)
        }
    }

    private func reserveForAdd(): Unit {
        if (used < capacity) { return }
        if (capacity > Int64.Max / 2) { throw IllegalMemoryException("Key capacity overflow") }
        let expandedCapacity = capacity * 2
        if (expandedCapacity > Int64.Max / 3) { throw IllegalMemoryException("Key payload overflow") }
        let expanded = LibC.malloc<Int64>(count: expandedCapacity * 3)
        if (expanded.isNull()) { throw IllegalMemoryException("Key vector expansion failed") }
        unsafe {
            for (i in 0..(used * 3)) { expanded.write(i, data.read(i)) }
        }
        let previous = data
        data = expanded
        capacity = expandedCapacity
        unsafe { LibC.free(previous) }
    }

    public func add(value: Key): Unit {
        reserveForAdd()
        let offset = used * 3
        unsafe {
            data.write(offset, value.a)
            data.write(offset + 1, value.b)
            data.write(offset + 2, value.c)
        }
        used++
    }

    public func remove(at!: Int64): Key {
        if (used == 0 || at != used - 1) { throw IndexOutOfBoundsException("Only last-key removal is supported") }
        let offset = at * 3
        let value = unsafe { Key(data.read(offset), data.read(offset + 1), data.read(offset + 2)) }
        used--
        unsafe {
            data.write(offset, 0)
            data.write(offset + 1, 0)
            data.write(offset + 2, 0)
        }
        return value
    }

    public func clone(): FastKeyVector {
        let result = FastKeyVector()
        for (i in 0..used) { result.add(this[i]) }
        return result
    }
}'''


def main():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    marker = "public class FastKeyVector {"
    assert original.count(marker) == 1
    start = original.index(marker)
    stop = original.index("\n}\n", start) + 2
    old = original[start:stop]
    assert all(f"private let {name} = FastIntVector()" in old
               for name in ("first", "second", "third"))
    assert old.count("reserveForAdd()") == 3
    source = original[:start] + FLAT + original[stop:]
    assert source[:start] == original[:start]
    assert source[start + len(FLAT):] == original[stop:]
    assert source.replace(FLAT, old, 1) == original
    assert FLAT.count("LibC.malloc<Int64>") == 2
    assert FLAT.count("LibC.free(data)") == 1
    assert FLAT.count("LibC.free(previous)") == 1
    assert FLAT.count("if (index < 0 || index >= used)") == 2

    OUT.mkdir(exist_ok=True)
    (OUT / "solution.cj").write_text(source)
    (OUT / "changes.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile="candidate-borrows/solution.cj", tofile="candidate-flat-keys/solution.cj")))
    meta = {
        "baseline": str(BASE.relative_to(HERE)),
        "baseline_sha256": BASE_SHA,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "changed_class": "FastKeyVector only",
        "source_outside_class_byte_identical": True,
        "layout": "data[3*i]=a, data[3*i+1]=b, data[3*i+2]=c; capacity and size count keys",
        "API": ["size", "checked key getter/setter", "add", "remove(at:) last only", "independent clone"],
        "ownership": [
            "One private pointer owner per FastKeyVector; constructor allocates48 Int64 cells for16 keys.",
            "Resize allocates3*newCapacity cells, copies exactly3*used initialized cells, commits new pointer/capacity, then frees old allocation once.",
            "Null allocation or capacity overflow throws before pointer/size changes. No other operation between allocation and commit has an expected throwing path for validated indices.",
            "Finalizer frees only current pointer; no pointer is exposed, shared with another owner, pinned, or manually closed.",
            "Clone constructs a distinct owner and appends the same three numeric fields for every logical entry; keys at vacant node IDs and sentinel are included.",
        ],
        "bounds": [
            "Getter/setter each check0<=index<used once before accessing allthree cells.",
            "Invariant0<=used<=capacity<=Int64.Max/3 makes3*index+2 and3*used safe. add reserves first, writes three cells, then increments used.",
            "Resize checks capacity*2 and expandedCapacity*3 separately before multiplication; typed malloc additionally checks native byte-count overflow.",
            "remove verifies nonempty and at==used-1 once, reads a/b/c, decrements used and zeros exactly the removed triple. Other removal positions are rejected as before.",
        ],
        "semantic_proof": "The old three columns and new triple layout implement the same indexed Key sequence and deep-clone behavior. Both AVL classes and every other source byte remain unchanged, so node geometry, stable indices, comparison fields, iteration and decisions are preserved conditional on successful allocation.",
        "windows_105": "Uses the same stdlib LibC.malloc/free, CPointer<Int64> read/write and finalizer constructs already present in the source. No OS-specific API or raw managed-array pointer; typed malloc guards32-bit as well as64-bit native-size overflow. Actual Windows compiler/runtime parity remains untested here.",
        "caveats": [
            "Native memory remains outside managed-heap telemetry and inside process RSS; same total Int64 payload capacity, fewer owners/allocations.",
            "Private FastIntVector.reserveForAdd comment still mentions former columns, but FastIntVector itself is deliberately untouched.",
            "Compiler1.0.5 compatibility, FP/response parity and CPU/RSS require parent measurement.",
        ],
        "compile_executed": False,
        "solver_executed": False,
    }
    (OUT / "source.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(OUT / "solution.cj")
    print(meta["source_sha256"])


if __name__ == "__main__":
    main()
