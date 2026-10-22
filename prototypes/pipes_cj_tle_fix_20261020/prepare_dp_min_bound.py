#!/usr/bin/env python3
"""Skip a DP elimination pass only when no active reward can be removed."""
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
for method, next_method in [
    ("rebuildPrimalGapValues", "ensurePrimalGapValues"),
    ("rebuildCausalGapValues", "causalValueAt"),
]:
    start = source.index(f"    public func {method}(")
    stop = source.index(f"    public func {next_method}(", start)
    body = source[start:stop]
    lines = body.splitlines(True)
    result = []
    changes = {"minimum": 0, "initial": 0, "while": 0, "remaining": 0}
    in_elimination = False
    for line in lines:
        indent = line[:len(line) - len(line.lstrip())]
        if line.strip() == "var numerator: Float64 = 0.0":
            result.append(indent + "var minActiveReward = Float64.Inf\n")
            changes["minimum"] += 1
        if line.strip() == "reward.write(request, requestReward)":
            result.append(indent + "if (requestReward < minActiveReward) { minActiveReward = requestReward }\n")
            changes["initial"] += 1
        if line.strip() == "while (true) {":
            result.append(indent + "while (estimate > minActiveReward) {\n")
            result.append(indent + "    minActiveReward = Float64.Inf\n")
            in_elimination = True
            changes["while"] += 1
            continue
        result.append(line)
        if in_elimination and line.strip() == "removed = true":
            # The following line closes the original `if (rr < estimate)`.
            # Add an else branch to track the exact minimum of kept rewards.
            assert lines[lines.index(line) + 1].strip() == "}"
    body = "".join(result)
    old = "removed = true\n"
    at = body.index(old) + len(old)
    end_line = body.index("\n", at)
    closing = body[at:end_line]
    assert closing.strip() == "}"
    indent = closing[:len(closing) - len(closing.lstrip())]
    body = body[:at] + indent + "} else if (rr < minActiveReward) {\n" + indent + "    minActiveReward = rr\n" + closing + body[end_line:]
    changes["remaining"] += 1
    assert changes == {"minimum": 1, "initial": 1, "while": 1, "remaining": 1}, changes
    source = source[:start] + body + source[stop:]

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(source)
args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(args.source), tofile=str(args.output),
)))
args.output.with_suffix(".json").write_text(json.dumps({
    "parent_sha256": hashlib.sha256(original.encode()).hexdigest(),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "changed": "Track the minimum active reward using comparisons; skip a pass when estimate is not greater than that minimum.",
    "proof": [
        "A request is removed iff its active reward is strictly less than estimate. If estimate<=minimum active reward, the original pass performs no numerator/denominator FP update and exits.",
        "Each executed pass still visits requests in the original increasing order, applying exactly the same multiplications/subtractions to numerator and denominator.",
        "The minimum is initialized from written reward values; after each executed pass it is recomputed from precisely the retained active rewards.",
        "Minimum tracking performs comparisons and scalar copies only, no arithmetic or reward recomputation. Equal rewards remain retained as before.",
        "Empty active sets use+Inf. A NaN estimate makes every original rr<estimate false and likewise prevents a new pass; the same final clamp executes.",
    ],
    "status": "Prepared; independent audit, compilation and transcript verification required.",
}, indent=2) + "\n")
print(args.output)
