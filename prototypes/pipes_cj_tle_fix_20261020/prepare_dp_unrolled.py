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
                lines.append(indent + "    if (true) {\n")
                lines.append(textwrap.indent(constant_body, indent + "        ") + "\n")
                lines.append(indent + "    }\n")
            lines.append(indent + "} else {\n")
            lines.append(textwrap.indent(old, "    ") + "\n")
            lines.append(indent + "}")
            new = "".join(lines)
            changes.append({"method": method, "old": old, "new": new})
            section = section[:match.start()] + new + section[closing + 1:]
        result = result[:begin] + section + result[end:]
    assert len(changes) == 5
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
        "modified_loops": len(changes), "constant_request_blocks": 200,
        "reverse_exact": True,
        "proof": [
            "For gaps below40 the original request loop is retained verbatim.",
            "For gaps>=40 every request1..40 has a valid nonnegative remainder index.",
            "Outside firstRequest..lastRequest every request rate is exactly0.0 by the existing zero-fill and support scan, so the added initial blocks perform no FP update.",
            "Removal blocks outside that support have an unset active bit, so they never read stale reward scratch or change sums.",
            "For each included rate, the exact original body and ascending1..40 update order are retained; continue-at-zero becomes an enclosing !=0 guard.",
            "No change to expiry, rates, rebuild triggers, arithmetic expressions, clamp, model fitting, replay, history, or I/O.",
        ],
        "notes": ["This increases code size. A performance benefit must be measured at both optimization levels."],
    }
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"source_sha256": meta["source_sha256"], "source_bytes": len(result.encode())}))


if __name__ == "__main__":
    main()
