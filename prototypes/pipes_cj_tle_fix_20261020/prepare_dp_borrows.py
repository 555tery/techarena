#!/usr/bin/env python3
"""Borrow owned stable numeric storage once per bounded DP recurrence."""
import difflib
import hashlib
import json
import re
from pathlib import Path

here = Path(__file__).resolve().parent
source_path = here / "candidate-combined/solution.cj"
original = source_path.read_text()
source = original
marker = "    public func copyFrom(other: FastFloatBuffer): Unit {"
assert source.count(marker) == 1
source = source.replace(
    marker,
    "    // Borrow only while the owning Allocator remains live. The native\n"
    "    // allocation is fixed-size and cannot move during Cangjie GC.\n"
    "    func borrowData(): CPointer<Float64> { data }\n\n" + marker,
)

for method, next_method, buffers in [
    ("rebuildPrimalGapValues", "ensurePrimalGapValues",
     {"rate": "causalRequestRate", "value": "primalGapValue", "reward": "dpRewardScratch"}),
    ("rebuildCausalGapValues", "causalValueAt",
     {"requestRates": "causalRequestRate", "gapValues": "causalGapValue", "reward": "dpRewardScratch"}),
]:
    start = source.index(f"    public func {method}(")
    end = source.index(f"    public func {next_method}(", start)
    body = source[start:end]
    for alias, owner in buffers.items():
        assert body.count(f"let {alias} = {owner}") == 1
        body = body.replace(f"let {alias} = {owner}", f"let {alias} = {owner}.borrowData()")
        body = body.replace(f"{alias}.fill(0.0)", f"{owner}.fill(0.0)")

    # Rewrite stores before loads, keeping each RHS in its original FP order.
    body = body.replace(
        "rate[gap] = Float64(recentRequests[gap]) / Float64(iMax(1, fitting))",
        "rate.write(gap, Float64(recentRequests[gap]) / Float64(iMax(1, fitting)))",
    )
    body = body.replace(
        "value[g] = fMax(value[g], Float64(request) + value[g - request])",
        "value.write(g, fMax(value[g], Float64(request) + value[g - request]))",
    )
    body = body.replace("reward[request] = requestReward", "reward.write(request, requestReward)")
    body = body.replace(
        "value[g] = fMin(fMax(estimate, 0.0), Float64(g))",
        "value.write(g, fMin(fMax(estimate, 0.0), Float64(g)))",
    )
    body = body.replace(
        "gapValues[offset + gap] = fMin(fMax(estimate, 0.0), Float64(gap))",
        "gapValues.write(offset + gap, fMin(fMax(estimate, 0.0), Float64(gap)))",
    )
    for alias in buffers:
        body = re.sub(rf"\b{alias}\[([^\]]+)\]", rf"{alias}.read(\1)", body)
    lines = body.rstrip().splitlines()
    assert lines[-1] == "    }"
    lines = (
        lines[:1]
        + [
            '        if (maxGap < 0 || maxGap > kPrimalGapValueCap) { throw IndexOutOfBoundsException("DP limit") }',
            "        // All indices are within rates/reward[0..40], value[0..512]",
            "        // or causal rows[0..1025]; this owns every buffer throughout.",
            "        unsafe {",
        ]
        + ["    " + line for line in lines[1:-1]]
        + ["        }", "    }"]
    )
    source = source[:start] + "\n".join(lines) + "\n\n" + source[end:]

assert source[source.index("func replayTable0():"):] == original[original.index("func replayTable0():"):]
out = here / "candidate-borrows"
out.mkdir(exist_ok=True)
(out / "solution.cj").write_text(source)
(out / "changes.diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(source_path), tofile=str(out / "solution.cj"),
)))
(out / "source.json").write_text(json.dumps({
    "parent_sha256": hashlib.sha256(original.encode()).hexdigest(),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "change": "Borrow stable owned CPointer once per bounded DP; replace per-cell wrapper calls with equivalent pointer read/write.",
    "bounds": "maxGap in [0,512], requests in [1,min(gap,40)], offset in {0,513}; rate scan [0,40].",
    "ownership": "Allocator is used after both recurrences and retains all fixed native owners; no free or reallocation within borrow.",
}, indent=2) + "\n")
print(out / "solution.cj")
