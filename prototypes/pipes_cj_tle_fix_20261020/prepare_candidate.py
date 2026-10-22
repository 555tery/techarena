#!/usr/bin/env python3
"""Mechanical, policy-preserving optimizations of the frozen submitted source."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
BASE_SHA = "fd5fe184cb85bf47c18085a3ef12ceb36ae20168398dd00d8983f16165b8fc9a"
original = (HERE / "baseline/solution.cj").read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
source = original


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)


# The exact same implementations with concrete Int64 storage avoid runtime
# generic type metadata and generic value copies at -O0, including in 1.0.5.
for generic, concrete, parameter in [
    ("OrderedMap", "IntOrderedMap", "V"),
    ("Ring", "IntRing", "T"),
]:
    start = source.index(f"public class {generic}<{parameter}>")
    stop = source.index("\n}\n", start) + 3
    specialized = source[start:stop]
    specialized = specialized.replace(f"{generic}<{parameter}>", concrete)
    specialized = re.sub(rf"\b{parameter}\b", "Int64", specialized)
    source = source[:stop] + "\n// Concrete specialization; identical operations.\n" + specialized + source[stop:]
    source = source.replace(f"{generic}<Int64>", concrete)

# Each detector needs three run values forming a nonzero arithmetic
# progression. Fewer than three distinct sizes cannot satisfy that equation.
# The histogram already covers exactly the same capped history.
replace(
    "    public func hasSteadySizeTrend(): Bool {\n"
    "        if (recentLengths.size < 128) { return false }",
    "    public func hasSteadySizeTrend(): Bool {\n"
    "        if (recentLengths.size < 128) { return false }\n"
    "        var availableSizes: Int64 = 0\n"
    "        for (size in 1..=40) { if (recentFrequency[size] > 0) { availableSizes++ } }\n"
    "        if (availableSizes < 3) { return false }",
    2,
)
replace(
    "    public func hasSmoothSizeTrendWith(currentLength: Int64): Bool {\n"
    "        if (recentLengths.size == 0) { return false }",
    "    public func hasSmoothSizeTrendWith(currentLength: Int64): Bool {\n"
    "        if (recentLengths.size == 0) { return false }\n"
    "        var availableSizes: Int64 = 0\n"
    "        for (size in 1..=40) { if (recentFrequency[size] > 0) { availableSizes++ } }\n"
    "        if (recentFrequency[currentLength] == 0) { availableSizes++ }\n"
    "        if (availableSizes < 3) { return false }",
    2,
)
replace(
    "    public var recentDeleteRanksPermille = IntRing(0)",
    "    public var recentDeleteRanksPermille = IntRing(0)\n"
    "    public var recentTopFivePercent: Int64 = 0",
)
replace(
    "        var topFivePercent: Int64 = 0\n"
    "        for (i in 0..recentDeleteRanksPermille.size) { if (recentDeleteRanksPermille.get(i) <= 50) { topFivePercent++ } }\n"
    "        if (topFivePercent * 100 < recentDeleteRanksPermille.size * 80) { return false }",
    "        if (recentTopFivePercent * 100 < recentDeleteRanksPermille.size * 80) { return false }",
    2,
)
replace(
    "        for (i in 0..recentLengths.size) { if (recentLengths.get(i) <= 8) { shortPlacements++ } }",
    "        for (size in 1..=8) { shortPlacements += recentFrequency[size] }",
    2,
)
replace(
    "        var units: Int64 = 0\n"
    "        for (seen in 0..window) { if (recentLengths.get(recentLengths.size - 1 - seen) == 1) { units++ } }",
    "        // kHistoryWindow is 2048, equal to the full queried window.\n"
    "        let units = recentFrequency[1]",
)
replace(
    "            recentDeleteRanksPermille.pushBack(event.value)\n"
    "            if (recentDeleteRanksPermille.size > 64) { recentDeleteRanksPermille.popFront() }",
    "            recentDeleteRanksPermille.pushBack(event.value)\n"
    "            if (event.value <= 50) { recentTopFivePercent++ }\n"
    "            if (recentDeleteRanksPermille.size > 64) {\n"
    "                if (recentDeleteRanksPermille.get(0) <= 50) { recentTopFivePercent-- }\n"
    "                recentDeleteRanksPermille.popFront()\n"
    "            }",
)

target = HERE / "candidate-v1/solution.cj"
target.parent.mkdir(exist_ok=True)
target.write_text(source)
(HERE / "candidate-v1/source.json").write_text(json.dumps({
    "baseline_sha256": BASE_SHA,
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "changes": [
        "Exact concrete Int64 specialization of OrderedMap and Ring",
        "Histogram early rejection of impossible three-size arithmetic trends",
        "Equivalent histogram query for short placements and unit dominance",
        "Incremental exact count of top-five-percent deletions in the same 64-entry window",
    ],
    "policy": "No thresholds, replay tables, action selection or rollout budget changed",
}, indent=2) + "\n")
print(target)
