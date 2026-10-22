#!/usr/bin/env python3
"""Skip only leading/trailing zero-rate sizes; preserve every FP operation."""
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

for method, next_method, rates, gap_variable in [
    ("rebuildPrimalGapValues", "ensurePrimalGapValues", "rate", "g"),
    ("rebuildCausalGapValues", "causalValueAt", "requestRates", "gap"),
]:
    start = source.index(f"    public func {method}(")
    end = source.index(f"    public func {next_method}(", start)
    before = source[start:end]
    support = (
        "        var lastRequest: Int64 = 40\n"
        f"        while (lastRequest > 0 && {rates}[lastRequest] == 0.0) {{ lastRequest-- }}\n"
        "        var firstRequest: Int64 = 1\n"
        f"        while (firstRequest <= lastRequest && {rates}[firstRequest] == 0.0) {{ firstRequest++ }}\n"
    )
    if method == "rebuildPrimalGapValues":
        marker = "        let expiry = 2.0 * Float64(primalRecentDeletes)"
    else:
        marker = "        let gapValues = causalGapValue"
    assert before.count(marker) == 1
    after = before.replace(marker, support + marker)
    assert after.count(f"let top = iMin({gap_variable}, 40)") == 1
    after = after.replace(f"let top = iMin({gap_variable}, 40)",
                          f"let top = iMin({gap_variable}, lastRequest)")
    expected = 3 if method == "rebuildPrimalGapValues" else 2
    assert after.count("for (request in 1..=top)") == expected
    after = after.replace("for (request in 1..=top)", "for (request in firstRequest..=top)")
    source = source[:start] + after + source[end:]

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(source)
args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(args.source), tofile=str(args.output),
)))
args.output.with_suffix(".json").write_text(json.dumps(dict(
    parent_sha256=hashlib.sha256(original.encode()).hexdigest(),
    source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    proof="Only sizes with exactly zero rate are excluded. Their original loops skip all FP operations; their active bits are unset. Remaining sizes keep increasing order. Empty ranges leave numerator/denominator and zero-initialized values unchanged.",
), indent=2) + "\n")
print(args.output)
