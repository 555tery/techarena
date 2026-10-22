#!/usr/bin/env python3
"""Avoid -O0 VArray receiver copies; reuse the exact same DP scratch slots."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = HERE / "candidate-counts/solution.cj"
original = base.read_text()
source = original
for type_name, size, zero in [
    ("Int64", 514, "0"),
    ("Int64", 256, "0"),
    ("Float64", 513, "0.0"),
    ("Float64", 1026, "0.0"),
    ("Float64", 41, "0.0"),
]:
    source = source.replace(
        f"VArray<{type_name}, ${size}>(repeat: {zero})",
        f"Array<{type_name}>({size}, repeat: {zero})",
    )
# With Array this snapshot now shares storage, but the loop is read-only and
# no intervening operation can mutate the source histogram.
start = source.index("    public func rebuildPrimalGapValues(")
stop = source.index("    public func ensurePrimalGapValues(", start)
before = source[start:stop]
assert before.count("            var reward = Array<Float64>(41, repeat: 0.0)\n") == 1
after = before.replace(
    "        var value = Array<Float64>(513, repeat: 0.0)\n",
    "        var value = Array<Float64>(513, repeat: 0.0)\n"
    "        let reward = Array<Float64>(41, repeat: 0.0)\n",
).replace("            var reward = Array<Float64>(41, repeat: 0.0)\n", "")
source = source[:start] + after + source[stop:]
start = source.index("    public func rebuildCausalGapValues(")
stop = source.index("    public func causalValueAt(", start)
before = source[start:stop]
assert before.count("                var reward = Array<Float64>(41, repeat: 0.0)\n") == 1
after = before.replace(
    "        var gapValues = causalGapValue\n",
    "        var gapValues = causalGapValue\n"
    "        let reward = Array<Float64>(41, repeat: 0.0)\n",
).replace("                var reward = Array<Float64>(41, repeat: 0.0)\n", "")
source = source[:start] + after + source[stop:]
# Each reward slot read is protected by an active bit set only after that slot
# has been written for this exact gap. Consequently stale scratch slots are
# never observed, and the arithmetic order is identical.
output = HERE / "candidate-array-dp"
output.mkdir(exist_ok=True)
(output / "solution.cj").write_text(source)
(output / "changes.diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(base), tofile=str(output / "solution.cj"),
)))
(output / "source.json").write_text(json.dumps(dict(
    parent_sha256=hashlib.sha256(original.encode()).hexdigest(),
    source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    changes=["Large numeric VArray storage replaced by Array",
             "One reward scratch array per DP rebuild, with identical active-bit guards"],
    proof="No observation of a stale reward slot; FP operations keep their original order.",
), indent=2) + "\n")
print(output / "solution.cj")
