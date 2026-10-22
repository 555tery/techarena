#!/usr/bin/env python3
"""Convert exactly three primal integer tables to fixed native owners."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re

BUFFER = '''// Fixed-size native Int64 owner. No raw pointer export or ownership copy.
public class FastIntBuffer {
    private let data: CPointer<Int64>
    public let size: Int64

    public init(capacity: Int64) {
        if (capacity <= 0) { throw IllegalArgumentException("Invalid integer buffer capacity") }
        this.size = capacity
        this.data = LibC.malloc<Int64>(count: capacity)
        if (data.isNull()) { throw IllegalMemoryException("Integer buffer allocation failed") }
        unsafe {
            for (i in 0..capacity) { data.write(i, 0) }
        }
    }

    ~init() { unsafe { LibC.free(data) } }

    public operator func [](index: Int64): Int64 {
        if (index < 0 || index >= size) { throw IndexOutOfBoundsException("Integer buffer index") }
        return unsafe { data.read(index) }
    }

    public operator func [](index: Int64, value!: Int64): Unit {
        if (index < 0 || index >= size) { throw IndexOutOfBoundsException("Integer buffer index") }
        unsafe { data.write(index, value) }
    }
}

'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    original = args.source.read_text()
    assert "public class FastIntBuffer" not in original
    assert "public let kPrimalGapValueCap: Int64 = 512" in original
    source = original
    changes = []
    fields = [("primalGapCounts", 514), ("primalEventHistory", 256),
              ("primalRecentRequests", 41)]
    for name, capacity in fields:
        old = f"public var {name} = VArray<Int64, ${capacity}>(repeat: 0)"
        new = f"private let {name} = FastIntBuffer({capacity})"
        assert source.count(old) == 1
        assert source.count(name + " =") == 1
        assert name + ".clone(" not in source
        assert "out." + name not in source
        source = source.replace(old, new)
        changes.append({"old": old, "new": new})

    # A VArray snapshot becomes a class alias. Check the read-only phase:
    # it must neither mutate either source table nor call a writer hook.
    start = original.index("    public func rebuildPrimalGapValues(")
    stop = original.index("\n    }", start) + len("\n    }")
    primal = original[start:stop]
    assert primal.count("let gapCounts = primalGapCounts") == 1
    assert primal.count("let recentRequests = primalRecentRequests") == 1
    last_read = max(primal.rfind("gapCounts["), primal.rfind("recentRequests["))
    alias_start = min(primal.index("let gapCounts ="), primal.index("let recentRequests ="))
    last_read_line_end = primal.index("\n", last_read)
    phase = primal[alias_start:last_read_line_end]
    forbidden_calls = ["addFreeGap(", "eraseGap(", "recordPrimalEvent(",
                       "recordLength(", "lifetimeModel.fit(", ".place(", ".remove("]
    assert not any(call in phase for call in forbidden_calls)
    assert not re.search(
        r"(?:primalGapCounts|gapCounts|primalRecentRequests|recentRequests)"
        r"\[[^\n]*?\]\s*(?:\+\+|--|[+*/-]?=(?!=))", phase)
    assert "causalRequestRate.fill(0.0)" in phase

    marker = "public class FastFloatBuffer {"
    assert source.count(marker) == 1
    source = source.replace(marker, BUFFER + marker, 1)
    restored = source.replace(BUFFER, "", 1)
    for change in reversed(changes):
        assert restored.count(change["new"]) == 1
        restored = restored.replace(change["new"], change["old"])
    assert restored == original

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output))))
    audit = {
        "status": "pass: storage-only change with read-only snapshot aliases",
        "parent_source": str(args.source.resolve()),
        "parent_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "changed_declarations": changes,
        "source_reverses_exactly": True,
        "allocations_per_allocator": 3,
        "native_payload_bytes_per_allocator": 6488,
        "ownership": [
            "Each private let field constructs a separate fixed owner; no clone, reassignment, pointer export or borrowed pointer API exists.",
            "Constructor checks positive capacity and malloc null, then zeroes exactly0..capacity-1. Typed LibC.malloc checks count*sizeof(Int64) overflow.",
            "One finalizer frees the owner's only allocation. Local aliases keep the class owner reachable; no second object owns the same pointer.",
        ],
        "bounds_and_counts": [
            "Both indexed accessors check0<=index<size before unsafe pointer access.",
            "Gap histogram uses min(513,positive gapLength), so indices1..513 fit514 slots; slot0 is initialized0 as before.",
            "Event position starts0 and advances modulo unchanged size256. Event entries are0,positive1..40 or deletion marker-1.",
            "Request histogram indexes only positive events/old values1..40 or scan1..40, fitting41 slots; slot0 remains0.",
            "All integer arithmetic and increment/decrement order remain unchanged; only backing storage changes.",
        ],
        "snapshot_alias_audit": [
            "gapCounts/recentRequests aliases are created inside rebuildPrimalGapValues. Their final reads occur in the initial descending512..1 loop while deriving rate.",
            "Between alias creation and those reads, the only external helpers are borrowData/fill on distinct causalRequestRate Float64 storage, pure iMax and primitive Float64 conversion. None mutates either integer owner.",
            "The integer owners are mutated only by ordinary recordPrimalEvent and gap add/erase hooks, not called during this rate-building phase. lifetimeModel.fit occurs after their last read and has no Allocator reference.",
            "Existing main is single-threaded and neither owner exposes pointers/callbacks. A class alias therefore yields identical values to the old VArray snapshot.",
        ],
        "other_paths": [
            "Import still uses unchanged recordPrimalEvent/addFreeGap hooks on its fresh Allocator. Shadow/live Allocators own separate buffers.",
            "No RolloutState table copies are affected: these three owners exist only in Allocator and are never cloned into simulations.",
            "DP loops/FP expressions, map/ring storage, recent history caches, replay, GC and I/O are untouched.",
        ],
        "caveats": [
            "Native payload6488bytes per Allocator is outside managed-heap telemetry but counted in process RSS; owner finalization timing is unspecified.",
            "If future code adds concurrent mutation or callbacks in the rate-building phase, snapshot/alias equivalence needs review.",
            "Actual1.0.5 compilation, transcript parity and resource measurements remain parent checks.",
        ],
        "compile_executed": False,
        "solver_executed": False,
        "CPU_benchmark_executed": False,
    }
    args.output.with_suffix(".json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(args.output)
    print(audit["source_sha256"])


if __name__ == "__main__":
    main()
