#!/usr/bin/env python3
"""Prepare a narrow VArray histogram candidate; do not compile or run it."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE / "candidate-values/solution.cj"
OUT = HERE / "candidate-histograms"
BASE_SHA256 = "24acac5c2e3499973c38b8c24d390b8e96345bd4f1e9ac93275f324742b8772c"
DOC = "https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/basic_data_type/array.md"

original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original
edits = []


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)
    edits.append({"old": old, "new": new, "occurrences": count})


# Both Allocator and RolloutState own independent primitive counters.
for name in ("recentFrequency", "lengthOccurrenceCount"):
    replace(f"public var {name} = Array<Int64>(41, repeat: 0)",
            f"public var {name} = VArray<Int64, $41>(repeat: 0)", 2)

# deepCopy formerly copied every element into a fresh Array. VArray assignment
# copies all41 Int64 values, preserving independent source/destination storage.
replace(
    "        copy.recentLengths = recentLengths.clone()\n"
    "        for (i in 0..41) {\n"
    "            copy.recentFrequency[i] = recentFrequency[i]\n"
    "            copy.lengthOccurrenceCount[i] = lengthOccurrenceCount[i]\n",
    "        copy.recentLengths = recentLengths.clone()\n"
    "        copy.recentFrequency = recentFrequency\n"
    "        copy.lengthOccurrenceCount = lengthOccurrenceCount\n"
    "        for (i in 0..41) {\n",
)
replace("state.recentFrequency = recentFrequency.clone()",
        "state.recentFrequency = recentFrequency")
replace("state.lengthOccurrenceCount = lengthOccurrenceCount.clone()",
        "state.lengthOccurrenceCount = lengthOccurrenceCount")

# These temporaries never escape their detector and have only indexed reads
# and writes. A mutable binding is required for value-array element writes.
replace("let distinctLengths = Array<Int64>(3, repeat: 0)",
        "var distinctLengths = VArray<Int64, $3>(repeat: 0)", 2)
replace("let priorRunLengths = Array<Int64>(2, repeat: 0)",
        "var priorRunLengths = VArray<Int64, $2>(repeat: 0)", 2)

# Prove that the generated diff contains only these literal storage/copy edits.
restored = source
for change in reversed(edits):
    assert restored.count(change["new"]) == change["occurrences"]
    restored = restored.replace(change["new"], change["old"])
assert restored == original
assert source[source.index("func replayTable0():"):] == original[original.index("func replayTable0():"):]
assert "recentFrequency.clone()" not in source
assert "lengthOccurrenceCount.clone()" not in source
assert source.count("public var recentFrequency = VArray<Int64, $41>") == 2
assert source.count("public var lengthOccurrenceCount = VArray<Int64, $41>") == 2

OUT.mkdir(exist_ok=True)
target = OUT / "solution.cj"
target.write_text(source)
metadata = {
    "baseline": str(BASE.relative_to(HERE)),
    "baseline_sha256": BASE_SHA256,
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "official_105_varray_documentation": DOC,
    "changes": edits,
    "write_and_copy_audit": [
        "Both recordLength hooks mutate their own recentFrequency and cap history at2048; indices and arithmetic unchanged.",
        "Online normal/slab placements, rollout finalizePlacement, and import increment the same lengthOccurrenceCount cells as before.",
        "makeRolloutState changes two Array.clone calls to independent VArray value assignments.",
        "RolloutState.deepCopy replaces41 per-element histogram/occurrence copies by whole VArray value copies; removedLengthCohort copies stay in their original loop.",
        "Local trend arrays contain Int64 values only; they do not escape, alias another object, or require Array-specific APIs.",
        "No helper receives either field as an Array parameter; all ordinary accesses are indexed Int64 reads/writes.",
    ],
    "policy": "Only two41-entry fields in each Allocator/RolloutState and four local2/3-entry trend temporaries changed. Maps, rings, DP, parity counters, replay, GC, I/O and decisions untouched.",
    "literal_edits_reverse_exactly_to_baseline": True,
    "compile_executed": False,
    "solver_executed": False,
    "caveats": ["Actual Cangjie1.0.5 speed, stack/heap behavior and transcript parity require parent verification."],
}
(OUT / "source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
(OUT / "changes.diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile="candidate-values/solution.cj", tofile="candidate-histograms/solution.cj")))
print(target)
print(metadata["source_sha256"])
