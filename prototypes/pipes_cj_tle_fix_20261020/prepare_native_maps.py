#!/usr/bin/env python3
"""Replace AVL backing storage only; no compiler or solver invocation."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

SUPPORT = '''// Native backing vectors for AVL storage. Each Int64 allocation has one
// FastIntVector owner; no managed-array pinning or exported pointer is used.
public class FastIntVector {
    private var data: CPointer<Int64>
    private var capacity: Int64 = 16
    private var used: Int64 = 0

    public init() {
        data = LibC.malloc<Int64>(count: 16)
        if (data.isNull()) { throw IllegalMemoryException("Integer vector allocation failed") }
    }

    ~init() { unsafe { LibC.free(data) } }

    public prop size: Int64 { get() { used } }

    public operator func [](index: Int64): Int64 {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Integer vector index") }
        return unsafe { data.read(index) }
    }

    public operator func [](index: Int64, value!: Int64): Unit {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Integer vector index") }
        unsafe { data.write(index, value) }
    }

    // Package-internal so FastKeyVector can reserve all three columns before
    // committing any component. Failed reservation leaves all sizes intact.
    func reserveForAdd(): Unit {
        if (used < capacity) { return }
        if (capacity > Int64.Max / 2) { throw IllegalMemoryException("Integer vector capacity overflow") }
        let expandedCapacity = capacity * 2
        let expanded = LibC.malloc<Int64>(count: expandedCapacity)
        if (expanded.isNull()) { throw IllegalMemoryException("Integer vector expansion failed") }
        unsafe {
            for (i in 0..used) { expanded.write(i, data.read(i)) }
        }
        let previous = data
        data = expanded
        capacity = expandedCapacity
        unsafe { LibC.free(previous) }
    }

    public func add(value: Int64): Unit {
        reserveForAdd()
        unsafe { data.write(used, value) }
        used++
    }

    public func remove(at!: Int64): Int64 {
        if (used == 0 || at != used - 1) { throw IndexOutOfBoundsException("Only last-element removal is supported") }
        let value = unsafe { data.read(at) }
        used--
        unsafe { data.write(used, 0) }
        return value
    }

    public func clone(): FastIntVector {
        let result = FastIntVector()
        for (i in 0..used) { result.add(unsafe { data.read(i) }) }
        return result
    }
}

public class FastKeyVector {
    private let first = FastIntVector()
    private let second = FastIntVector()
    private let third = FastIntVector()

    public init() {}
    public prop size: Int64 { get() { first.size } }

    public operator func [](index: Int64): Key {
        return Key(first[index], second[index], third[index])
    }

    public operator func [](index: Int64, value!: Key): Unit {
        first[index] = value.a
        second[index] = value.b
        third[index] = value.c
    }

    public func add(value: Key): Unit {
        first.reserveForAdd()
        second.reserveForAdd()
        third.reserveForAdd()
        first.add(value.a)
        second.add(value.b)
        third.add(value.c)
    }

    public func remove(at!: Int64): Key {
        if (size == 0 || at != size - 1) { throw IndexOutOfBoundsException("Only last-key removal is supported") }
        let value = this[at]
        first.remove(at: at)
        second.remove(at: at)
        third.remove(at: at)
        return value
    }

    public func clone(): FastKeyVector {
        let result = FastKeyVector()
        for (i in 0..size) { result.add(this[i]) }
        return result
    }
}

'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = args.source.read_text()
    assert "public class FastIntVector" not in original
    assert "public class FastKeyVector" not in original
    source = original
    edits = []
    for marker, concrete in (("public class OrderedMap<V>", False),
                             ("public class IntOrderedMap", True)):
        start = source.index(marker)
        stop = source.index("\n}\n", start) + 3
        before = source[start:stop]
        after = before
        for name in ("left", "right", "parent", "heights", "vacant"):
            old = f"private var {name} = ArrayList<Int64>()"
            new = f"private var {name} = FastIntVector()"
            assert after.count(old) == 1, (marker, old)
            after = after.replace(old, new)
            edits.append({"tree": marker, "old": old, "new": new})
        old, new = "private var keys = ArrayList<Key>()", "private var keys = FastKeyVector()"
        assert after.count(old) == 1
        after = after.replace(old, new)
        edits.append({"tree": marker, "old": old, "new": new})
        if concrete:
            old, new = "private var values = ArrayList<Int64>()", "private var values = FastIntVector()"
            assert after.count(old) == 1
            after = after.replace(old, new)
            edits.append({"tree": marker, "old": old, "new": new})
        else:
            assert "private var values = ArrayList<V>()" in after
        # The tree code may call only the supported ArrayList subset.
        assert "vacant.remove(at: vacant.size - 1)" in before
        assert before.count(".remove(") == 1
        restored = after
        for edit in reversed([e for e in edits if e["tree"] == marker]):
            restored = restored.replace(edit["new"], edit["old"])
        assert restored == before
        source = source[:start] + after + source[stop:]
    marker = "public class OrderedMap<V>"
    assert source.count(marker) == 1
    source = source.replace(marker, SUPPORT + marker, 1)

    # Full-source reverse proof: no changes to AVL operations, DP, rings,
    # policy, replay tables, native float owner, I/O, GC or other collections.
    restored = source.replace(SUPPORT, "", 1)
    for marker in ("public class OrderedMap<V>", "public class IntOrderedMap"):
        start = restored.index(marker)
        stop = restored.index("\n}\n", start) + 3
        body = restored[start:stop]
        for edit in reversed([e for e in edits if e["tree"] == marker]):
            assert body.count(edit["new"]) == 1
            body = body.replace(edit["new"], edit["old"])
        restored = restored[:start] + body + restored[stop:]
    assert restored == original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output))))
    metadata = {
        "parent_source": str(args.source.resolve()),
        "parent_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "changed_declarations": edits,
        "scope": "Only AVL nav/free arrays and Key storage in both trees; IntOrderedMap values only. Generic values retain ArrayList<V>.",
        "supported_api": ["size", "add", "indexed getter/setter", "remove(at:) only last", "clone"],
        "ownership": [
            "FastIntVector starts with16 native Int64 slots and one private pointer owner; capacity doubles only after overflow and malloc-null checks.",
            "Resize copies only initialized [0,used), commits new pointer/capacity, then frees previous allocation once; failed malloc leaves original owner intact.",
            "Finalizer frees only current allocation. Raw pointers never escape; no managed Array pinning or cross-owner pointer alias exists.",
            "FastKeyVector owns three separate vectors for Key.a/b/c; reserve all three before append, keeping lengths aligned on recoverable allocation failure.",
            "clone creates separate native allocations and copies all logical entries, including inactive-node and sentinel contents; vacant order and node IDs unchanged.",
        ],
        "bounds_and_integer_proof": [
            "Both indexed APIs enforce0<=index<used; Key access delegates bounds to each synchronized column.",
            "Only initialized slots are read or copied; add writes used before increment, remove checks last index and zeroes the removed slot.",
            "capacity>Int64.Max/2 is rejected before multiplication; LibC.malloc<Int64> separately checks count*sizeof(Int64) overflow. used<=capacity is invariant.",
            "For<=200000 commands, even a conservative200002 logical slots including sentinel fit capacity262144, far below integer limits.",
        ],
        "policy_proof": "All tree-method bodies are byte-identical after reversing13 declarations; node allocation, links, rotations, successor transplant, iteration and payload semantics unchanged.",
        "literal_edits_reverse_exactly_to_source": True,
        "compile_executed": False,
        "solver_executed": False,
        "caveats": [
            "Native storage is outside managed-heap-size telemetry but inside process RSS; vectors await owner finalization when unreachable.",
            "Future non-last remove or unsupported ArrayList APIs require extension; the audited AVL bodies use only the supported subset.",
            "Compiler compatibility, timing/RSS and transcript parity require parent verification.",
        ],
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(args.output)
    print(metadata["source_sha256"])


if __name__ == "__main__":
    main()
