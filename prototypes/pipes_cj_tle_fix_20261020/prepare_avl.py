#!/usr/bin/env python3
"""Stop AVL repair once its subtree height is unchanged."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--source", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
original = args.source.read_text()
source = original
changes = 0
position = 0
marker = "    private func rebalance(start: Int64): Unit {"
while True:
    start = source.find(marker, position)
    if start < 0:
        break
    end = source.index("    private func newNode(", start)
    before = source[start:end]
    assert before.count("            fixHeight(node)") == 1
    assert before.count("            node = parent[node]") == 1
    after = before.replace(
        "            fixHeight(node)",
        "            let oldHeight = heights[node]\n            fixHeight(node)",
    ).replace(
        "            node = parent[node]",
        "            // The repaired subtree has the same height as before the\n"
        "            // mutation. Ancestors retain their heights and balances.\n"
        "            if (heights[node] == oldHeight) { break }\n"
        "            node = parent[node]",
    )
    source = source[:start] + after + source[end:]
    position = start + len(after)
    changes += 1
assert changes == 2  # generic rollout tree and concrete online Int64 tree
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(source)
args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile=str(args.source), tofile=str(args.output),
)))
args.output.with_suffix(".json").write_text(json.dumps(dict(
    parent_source=str(args.source.resolve()),
    parent_source_sha256=hashlib.sha256(original.encode()).hexdigest(),
    source_sha256=hashlib.sha256(source.encode()).hexdigest(),
    changes="AVL repair stops only after balancing when subtree height is unchanged",
    unchanged="Node IDs, successor transplantation, rotations, ordering, payloads, policy",
), indent=2) + "\n")
print(args.output)
