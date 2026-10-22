#!/usr/bin/env python3
"""Use the identical lexicographic comparison in lower/upper as in find."""
import difflib
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
original = (here / "candidate-key-compare/solution.cj").read_text()
source = original
changes = [
    ("compareKey(keys[node], wanted) >= 0", "keys.compareAt(node, wanted) <= 0"),
    ("compareKey(keys[node], wanted) > 0", "keys.compareAt(node, wanted) < 0"),
]
for old, new in changes:
    assert source.count(old) == 2
    source = source.replace(old, new)
out = here / "candidate-key-search"
out.mkdir(exist_ok=True)
(out / "solution.cj").write_text(source)
(out / "changes.diff").write_text("".join(difflib.unified_diff(
    original.splitlines(True), source.splitlines(True),
    fromfile="candidate-key-compare/solution.cj", tofile="candidate-key-search/solution.cj",
)))
(out / "source.json").write_text(json.dumps({
    "parent_sha256": hashlib.sha256(original.encode()).hexdigest(),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "proof": "Lexicographic comparison of primitive Int64 triples is antisymmetric; compareAt(node,wanted)=compareKey(wanted,keys[node]). Reverse operand inequalities by reversing their direction; equality and traversal order remain identical.",
    "changed": "Only the lower and upper comparison predicates in both AVL classes (4 expressions). No FP, tree mutation or ownership change.",
}, indent=2) + "\n")
print(out / "solution.cj")
