#!/usr/bin/env python3
"""Constant-size expansion of large-gap request loops, preserving FP order."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path
import textwrap


def close_brace(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("Missing closing brace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    original = args.source.read_text()
    result = original
    changes = []
    for method, next_method, gap in (
        ("rebuildPrimalGapValues", "ensurePrimalGapValues", "g"),
        ("rebuildCausalGapValues", "causalValueAt", "gap"),
    ):
        begin = result.index("    public func " + method + "(")
        end = result.index("    public func " + next_method + "(", begin)
        section = result[begin:end]
        pattern = re.compile(r"^( +)for \(request in firstRequest\.\.=top\) \{", re.M)
        matches = list(pattern.finditer(section))
        assert len(matches) == (3 if gap == "g" else 2)
        rate_pointer = "rate" if gap == "g" else "requestRates"
        for match in reversed(matches):
            closing = close_brace(section, match.end() - 1)
            old = section[match.start():closing + 1]
            body = textwrap.dedent(section[match.end():closing]).strip()
            indent = match[1]
            skip = "if (requestRate == 0.0) { continue }"
            if skip in body:
                assert body.count(skip) == 1
                prefix, suffix = body.split(skip)
                body = prefix + "if (requestRate != 0.0) {\n" + textwrap.indent(suffix.strip(), "    ") + "\n}"
            assert "continue" not in body and "break" not in body
            # For gaps >= 40, every possible request index fits. Missing
            # support entries have exactly zero rate / an unset active bit.
            lines = [indent + f"if ({gap} >= 40) {{\n"]
            for request in range(1, 41):
                constant_body = re.sub(r"\brequest\b", str(request), body)
                constant_body = constant_body.replace(f"{rate_pointer}.read({request})", f"cachedRate{request}")
                constant_body = constant_body.replace(f"reward.write({request}, requestReward)", f"cachedReward{request} = requestReward")
                constant_body = constant_body.replace(f"reward.read({request})", f"cachedReward{request}")
                for variable in ("requestRate", "requestReward", "bit", "rr"):
                    constant_body = re.sub(r"\b" + variable + r"\b", variable + str(request), constant_body)
                lines.append(textwrap.indent(constant_body, indent + "    ") + "\n")
            lines.append(indent + "} else {\n")
            lines.append(textwrap.indent(old, "    ") + "\n")
            lines.append(indent + "}")
            new = "".join(lines)
            changes.append({"method": method, "old": old, "new": new})
            section = section[:match.start()] + new + section[closing + 1:]
        # Rates are immutable throughout each rebuild. Scratch rewards are
        # private to one gap and only read when the corresponding bit is active.
        rate_anchor = f"            for ({gap} in 1..=maxGap) {{" if gap == "g" else "            for (model in 0..2) {"
        assert section.count(rate_anchor) == 1
        cache_rates = "".join(f"            let cachedRate{i} = {rate_pointer}.read({i})\n" for i in range(1, 41))
        new_rate_anchor = cache_rates + rate_anchor
        changes.append({"method": method, "old": rate_anchor, "new": new_rate_anchor})
        section = section.replace(rate_anchor, new_rate_anchor, 1)
        reward_anchor = "                let reward = dpRewardScratch.borrowData()" if gap == "g" else "                    let reward = dpRewardScratch.borrowData()"
        assert section.count(reward_anchor) == 1
        reward_indent = reward_anchor[:len(reward_anchor) - len(reward_anchor.lstrip())]
        cache_rewards = "".join(f"{reward_indent}var cachedReward{i}: Float64 = 0.0\n" for i in range(1, 41))
        new_reward_anchor = cache_rewards + reward_anchor
        changes.append({"method": method, "old": reward_anchor, "new": new_reward_anchor})
        section = section.replace(reward_anchor, new_reward_anchor, 1)
        result = result[:begin] + section + result[end:]
    assert len(changes) == 9
    restored = result
    for change in reversed(changes):
        assert restored.count(change["new"]) == 1
        restored = restored.replace(change["new"], change["old"], 1)
    assert restored == original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), result.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output),
    )))
    meta = {
        "parent": str(args.source.resolve()),
        "parent_sha256": hashlib.sha256(original.encode()).hexdigest(),
        "source_sha256": hashlib.sha256(result.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "modified_loops": 5, "constant_request_blocks": 200,
        "reverse_exact": True,
        "proof": [
            "For gaps below40 the original request loop is retained verbatim.",
            "For gaps>=40 every request1..40 has a valid nonnegative remainder index.",
            "Outside firstRequest..lastRequest every request rate is exactly0.0 by the existing zero-fill and support scan, so the added initial blocks perform no FP update.",
            "Removal blocks outside that support have an unset active bit, so they never read stale reward scratch or change sums.",
            "For each included rate, the exact original body and ascending1..40 update order are retained; continue-at-zero becomes an enclosing !=0 guard.",
            "Rates are loaded into 40 immutable Float64 scalars before each rebuild, after rate calculation and before any value calculation.",
            "For gaps>=40, per-request reward scratch is replaced by 40 Float64 scalars. Every scalar read is guarded by an active bit set only after its write in the same gap. The original scratch is private to these methods and overwritten before every live read.",
            "No change to expiry, rates, rebuild triggers, arithmetic expressions, clamp, model fitting, replay, history, or I/O.",
        ],
        "notes": ["This increases code size. A performance benefit must be measured at both optimization levels."],
    }
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"source_sha256": meta["source_sha256"], "source_bytes": len(result.encode())}))


if __name__ == "__main__":
    main()
