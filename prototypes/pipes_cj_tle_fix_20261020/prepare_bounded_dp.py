#!/usr/bin/env python3
"""Suppress integer overflow traps only inside the two already bounded DPs."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--source", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
original = args.source.read_text()
source = original
for name in ("rebuildPrimalGapValues", "rebuildCausalGapValues"):
    marker = f"    public func {name}(maxGap: Int64): Unit {{"
    assert source.count(marker) == 1
    assert "    @OverflowWrapping\n" + marker not in source, "Source is already annotated"
    start = source.index(marker)
    assert 'if (maxGap < 0 || maxGap > kPrimalGapValueCap)' in source[start:start + 300]
    source = source.replace(marker, "    @OverflowWrapping\n" + marker)

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(source)
args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(args.source), tofile=str(args.output),
)))
args.output.with_suffix(".json").write_text(json.dumps({
    "parent_sha256": hashlib.sha256(original.encode()).hexdigest(),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "changed": "Only @OverflowWrapping on rebuildPrimalGapValues and rebuildCausalGapValues.",
    "bounds_proof": [
        "Explicit unchanged guard restricts maxGap to[0,512]; model is0 or1; all DP offsets are between0 and1025.",
        "Request/rate scan indices are between0 and40; active bits are1<<request withrequest<=40, safely below2^63.",
        "fitting sums disjoint free-gap counts. Valid streams have at most200000 commands and hence at most200001 gaps; adding the bucket counts cannot overflowInt64.",
        "primalModelRebuilds is increased once per rebuild, with at most a small constant multiple of the200000 input events including observed-prefix import.",
        "No narrowing integer conversion occurs in these methods. Integer-to-Float64 conversion and every FP update are unchanged.",
        "The annotation does not change called methods, bounds checks, explicit maxGap guards, recurrence order or policy budgets.",
    ],
    "official_105_documentation": "https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/reflect_and_annotation/anno.md",
    "status": "Prepared; performance and full response parity require compilation and execution.",
}, indent=2) + "\n")
print(args.output)
