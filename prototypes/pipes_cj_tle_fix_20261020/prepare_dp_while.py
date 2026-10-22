#!/usr/bin/env python3
"""Replace exactly8 DP range loops with explicit ascending Int64 cursors."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    original = args.source.read_text()
    assert "dpManualCursor" not in original
    source = original
    changes = []
    pattern = re.compile(
        r"^(?P<indent> +)for \((?P<name>g|gap|model|request) in "
        r"(?P<start>\w+)\.\.(?P<inclusive>=?)(?P<end>\w+)\) \{\n", re.M)
    for method, next_method in [
        ("rebuildPrimalGapValues", "ensurePrimalGapValues"),
        ("rebuildCausalGapValues", "causalValueAt"),
    ]:
        start = source.index(f"    public func {method}(")
        stop = source.index(f"    public func {next_method}(", start)
        body = source[start:stop]
        matches = list(pattern.finditer(body))
        assert len(matches) == 4, (method, len(matches))
        # Process from the end so every match retains its original offsets.
        for match in reversed(matches):
            number = len(changes) + 1
            cursor = f"dpManualCursor{number}"
            d = match.groupdict()
            condition = "<=" if d["inclusive"] else "<"
            old = match.group()
            new = (
                f"{d['indent']}var {cursor}: Int64 = {d['start']}\n"
                f"{d['indent']}while ({cursor} {condition} {d['end']}) {{\n"
                f"{d['indent']}    let {d['name']} = {cursor}\n"
                f"{d['indent']}    {cursor}++\n"
            )
            body = body[:match.start()] + new + body[match.end():]
            changes.append({"method": method, "old": old, "new": new,
                            "index": d["name"], "cursor": cursor,
                            "start": d["start"], "end": d["end"],
                            "inclusive": bool(d["inclusive"])})
        source = source[:start] + body + source[stop:]
    assert len(changes) == 8
    restored = source
    for change in reversed(changes):
        assert restored.count(change["new"]) == 1
        restored = restored.replace(change["new"], change["old"])
    assert restored == original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output))))
    metadata = {
        "status": "prepared, exact source/iteration proof; performance unknown",
        "parent_source_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "changed_loop_headers": changes,
        "source_reverse_exact": True,
        "proof": [
            "Each old inclusive/exclusive range has stable local/parameter endpoints. Explicit cursor starts at the same lower endpoint and uses the same comparison, so empty ranges remain empty and iteration indices retain ascending order.",
            "The old index name is a let copy of cursor for that iteration. Cursor increments before body execution, so both normal completion and existing continue statements advance exactly once. No old index binding is assigned by the original body.",
            "Only private integer bookkeeping is moved before each body. No FP statement, FP operand, branch threshold, loop-body ordering or pointer operation is modified. Reversing headers reconstructs the entire input byte-for-byte.",
            "Outer index endpoints are maxGap<=512 and model endpoint2; request endpoints<=40. Cursor increments are at most513/2/41, safely within Int64 and existing OverflowWrapping guards.",
            "No allocator/model cache, scratch lifetime, integer-buffer ownership, AVL, history, replay or I/O change exists.",
        ],
        "performance_scope": "Removes range-loop lowering overhead if present in Cangjie1.0.5-O0. Compiler may already lower ranges efficiently; no25percent gain can be inferred statically.",
        "compile_executed": False,
        "solver_executed": False,
        "CPU_benchmark_executed": False,
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(args.output)
    print(metadata["source_sha256"])


if __name__ == "__main__":
    main()
