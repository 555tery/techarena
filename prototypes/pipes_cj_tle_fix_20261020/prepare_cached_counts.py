#!/usr/bin/env python3
"""Cache exact capped-history counts; never compile or run a solver."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = HERE / "candidate-fast/solution.cj"
OUT = HERE / "candidate-counts"
BASE_SHA = "a2b415c6b98ab7c1d2bcce1d7c0935dd3b3fad69a2b3598f3a7443dbc1ba16a7"
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
source = original
edits = []


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)
    edits.append({"old": old, "new": new, "occurrences": count})


replace("    public var recentFrequency = VArray<Int64, $41>(repeat: 0)",
        "    public var recentFrequency = VArray<Int64, $41>(repeat: 0)\n"
        "    public var recentDistinctCount: Int64 = 0\n"
        "    public var recentShortCount: Int64 = 0", 2)

# Both former hooks have the same operations but different line wrapping.
pattern = re.compile(r"    public func recordLength\(length: Int64\): Unit \{\n"
                     r"        recentLengths\.pushBack\(length\)\n"
                     r"        recentFrequency\[length\]\+\+\n"
                     r"        if \(recentLengths\.size > kHistoryWindow\) \{\s*"
                     r"recentFrequency\[recentLengths\.get\(0\)\]--;?\s*"
                     r"recentLengths\.popFront\(\)\s*\}\n    \}")
matches = list(pattern.finditer(source))
assert len(matches) == 2
new_hook = """    public func recordLength(length: Int64): Unit {
        recentLengths.pushBack(length)
        if (recentFrequency[length] == 0) { recentDistinctCount++ }
        if (length <= 8) { recentShortCount++ }
        recentFrequency[length]++
        if (recentLengths.size > kHistoryWindow) {
            let oldest = recentLengths.get(0)
            recentFrequency[oldest]--
            if (recentFrequency[oldest] == 0) { recentDistinctCount-- }
            if (oldest <= 8) { recentShortCount-- }
            recentLengths.popFront()
        }
    }"""
# Save each old spelling, so reverse checking can reconstruct both exactly.
for match in reversed(matches):
    old = match.group()
    source = source[:match.start()] + new_hook + source[match.end():]
    edits.append({"old": old, "new": new_hook, "occurrences": 1,
                  "same_replacement_multiple_spellings": True})

replace("        copy.recentFrequency = recentFrequency\n",
        "        copy.recentFrequency = recentFrequency\n"
        "        copy.recentDistinctCount = recentDistinctCount\n"
        "        copy.recentShortCount = recentShortCount\n")
replace("        state.recentFrequency = recentFrequency\n",
        "        state.recentFrequency = recentFrequency\n"
        "        state.recentDistinctCount = recentDistinctCount\n"
        "        state.recentShortCount = recentShortCount\n")
replace("        var availableSizes: Int64 = 0\n"
        "        for (size in 1..=40) { if (recentFrequency[size] > 0) { availableSizes++ } }",
        "        var availableSizes: Int64 = recentDistinctCount", 4)
replace("        var shortPlacements: Int64 = 0\n"
        "        for (size in 1..=8) { shortPlacements += recentFrequency[size] }\n"
        "        return recentLengths.size >= 64 && shortPlacements * 100 >= recentLengths.size * 90",
        "        return recentLengths.size >= 64 && recentShortCount * 100 >= recentLengths.size * 90", 2)

# Reverse other literal edits first, then restore each hook by its source order.
restored = source
for edit in reversed(edits):
    if edit.get("same_replacement_multiple_spellings"):
        continue
    assert restored.count(edit["new"]) == edit["occurrences"]
    restored = restored.replace(edit["new"], edit["old"])
old_hooks = [m.group() for m in matches]
assert restored.count(new_hook) == 2
for old in old_hooks:
    restored = restored.replace(new_hook, old, 1)
assert restored == original
assert source[source.index("func replayTable0():"):] == original[original.index("func replayTable0():"):]
assert source.count("public var recentDistinctCount: Int64 = 0") == 2
assert source.count("public var recentShortCount: Int64 = 0") == 2
assert source.count("recentDistinctCount++") == source.count("recentDistinctCount--") == 2
assert source.count("recentShortCount++") == source.count("recentShortCount--") == 2
assert "out.recordLength(command)" in source

OUT.mkdir(exist_ok=True)
(OUT / "solution.cj").write_text(source)
metadata = {
    "baseline": str(BASE.relative_to(HERE)),
    "baseline_sha256": BASE_SHA,
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "changes": edits,
    "invariants": [
        "recentDistinctCount equals number of positive recentFrequency[1..40] entries.",
        "recentShortCount equals sum(recentFrequency[1..8]).",
        "Both start at0 beside empty histories. Both recordLength hooks update them on append and exact same front eviction at2048.",
        "When old/new sizes coincide, append+evict deltas cancel correctly; when one unique class disappears and another appears, both transitions are counted.",
        "RolloutState.deepCopy and Allocator.makeRolloutState copy both counters together with cloned history and copied histogram.",
        "Import uses the same recordLength hook for every accepted placement. Replay shadow runs ordinary place/remove. Physical replay does not own these counters.",
        "No other source assignment modifies history/histogram independently; deletions do not alter placement history.",
    ],
    "policy": "Only exact cached bookkeeping and its query/copy sites; detector thresholds and remaining scans, maps, rings, DP, replay, GC, I/O, parity and action choices unchanged.",
    "literal_edits_reverse_exactly_to_baseline": True,
    "compile_executed": False,
    "solver_executed": False,
    "caveats": ["Cangjie1.0.5 transcript parity and resource measurements require parent verification."],
}
(OUT / "source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
(OUT / "changes.diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile="candidate-fast/solution.cj", tofile="candidate-counts/solution.cj")))
print(OUT / "solution.cj")
print(metadata["source_sha256"])
