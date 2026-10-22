#!/usr/bin/env python3
"""Inline only non-resizing AVL height/parent helpers in six fenced methods."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re


BASE = Path(__file__).resolve().parent
METHODS = ("rotateLeft", "rotateRight", "rebalance")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def closing_brace(source, start):
    # Audited bodies contain no brace characters in strings or comments.
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("Unbalanced method body")


def height_write(node):
    return (f"navHeights.write({node}, 1 + iMax("
            f"navHeights.read(navLeft.read({node})), "
            f"navHeights.read(navRight.read({node}))))")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path,
                    default=BASE / "candidate-avl-direct-fenced/solution.cj")
    ap.add_argument("--output", type=Path,
                    default=BASE / "candidate-avl-inline/solution.cj")
    args = ap.parse_args()
    source = args.source.read_text()
    assert "rotationParent" not in source
    assert source.count("            " + height_write("node") + "\n") == 2
    old_parent = """            let p = navParent.read(oldNode)
            if (p == 0) { root = newNode }
            else if (navLeft.read(p) == oldNode) { navLeft.write(p, newNode) }
            else { navRight.write(p, newNode) }
            if (newNode != 0) { navParent.write(newNode, p) }
"""
    assert source.count(old_parent) == 2
    replacements = []
    for name in METHODS:
        pattern = re.compile(r"    private func " + name + r"\([^{}]*\): \w+ \{")
        matches = list(pattern.finditer(source))
        assert len(matches) == 2, (name, len(matches))
        for class_index, match in enumerate(matches):
            start = match.end()
            stop = closing_brace(source, start - 1)
            old = source[start:stop]
            assert old.count("blackBox(this)") == 1
            new = old
            if name.startswith("rotate"):
                borrow = "        let navParent = parent.borrowData()\n"
                assert new.count(borrow) == 1
                assert "let navHeights" not in new
                new = new.replace(borrow, borrow + "        let navHeights = heights.borrowData()\n")
                call = "            replaceAtParent(node, top)\n"
                assert new.count(call) == 1
                inlined = """            let rotationParent = navParent.read(node)
            if (rotationParent == 0) { root = top }
            else if (navLeft.read(rotationParent) == node) { navLeft.write(rotationParent, top) }
            else { navRight.write(rotationParent, top) }
            if (top != 0) { navParent.write(top, rotationParent) }
"""
                new = new.replace(call, inlined)
                heights = "            fixHeight(node); fixHeight(top)\n"
                assert new.count(heights) == 1
                new = new.replace(heights, "            " + height_write("node") +
                                  "\n            " + height_write("top") + "\n")
            else:
                call = "                fixHeight(node)\n"
                assert new.count(call) == 1
                new = new.replace(call, "                " + height_write("node") + "\n")
            assert "fixHeight(" not in new
            if name.startswith("rotate"):
                assert "replaceAtParent(" not in new
            assert new.count("blackBox(this)") == 1
            assert new.rfind("blackBox(this)") > max(new.rfind(".read("), new.rfind(".write("))
            replacements.append({"method": name,
                                 "class": "OrderedMap" if class_index == 0 else "IntOrderedMap",
                                 "start": start, "stop": stop, "old": old, "new": new})
    assert len(replacements) == 6
    result = source
    for edit in sorted(replacements, key=lambda x: x["start"], reverse=True):
        assert result[edit["start"]:edit["stop"]] == edit["old"]
        result = result[:edit["start"]] + edit["new"] + result[edit["stop"]:]
    # Restore all six edited bodies; every byte outside their spans is retained.
    restored = result
    for name in METHODS:
        pattern = re.compile(r"    private func " + name + r"\([^{}]*\): \w+ \{")
        matches = list(pattern.finditer(restored))
        assert len(matches) == 2
        for class_index in (1, 0):
            match = matches[class_index]
            end = closing_brace(restored, match.end() - 1)
            edit = next(x for x in replacements if x["method"] == name and
                        x["class"] == ("OrderedMap" if class_index == 0 else "IntOrderedMap"))
            assert restored[match.end():end] == edit["new"]
            restored = restored[:match.end()] + edit["old"] + restored[end:]
    assert restored == source
    metadata = {
        "schema": "avl-inline-helpers-equivalence-v1",
        "parent": str(args.source.resolve()), "parent_sha256": digest(source),
        "source_sha256": digest(result), "generator_sha256": digest(Path(__file__).read_text()),
        "changed_methods": [{"method": x["method"], "class": x["class"],
                             "before_sha256": digest(x["old"]), "after_sha256": digest(x["new"])}
                            for x in replacements],
        "source_reverse_exact": restored == source,
        "reverse_sha256": digest(restored),
        "scope": {"method_bodies": 6, "fixHeight_calls_inlined": 10,
                  "replaceAtParent_calls_inlined": 4, "new_height_borrows": 4},
        "proof": [
            "Both original fixHeight payloads are asserted identical to the inlined expression; substituting node/top preserves child reads, iMax argument order, Int64 addition and height writes exactly.",
            "Both original replaceAtParent payloads are asserted identical to the five inlined statements modulo oldNode=node, newNode=top and local p=rotationParent. Branches, reads and writes stay in their original order, including top!=0.",
            "Rotation edge writes remain between the parent replacement and the two height updates. The node height still updates before top height. Rebalance still records oldHeight before updating node height and computing balance.",
            "Only helper call boundaries, redundant helper entry/exit guards, repeated pointer borrows and helper-internal owner fences disappear. In valid AVL states helper indices satisfy the removed guards and owners never resize; no arithmetic, tree decision or rotation call changes.",
            "Each rotation acquires navHeights once before unsafe use. Existing navLeft/navRight/navParent and rebalance navHeights refer to the same owning allocations as the eliminated helper borrows. No owner is changed, freed, shared with a new owner or resized.",
            "Every edited method retains its original final blackBox(this), size check and return. The final opaque strong Map use occurs after all native pointer accesses and reaches every private owner. Eliminating inner helper fences does not shorten this enclosing owner lifetime.",
            "All edits are confined to six method-body spans; reversing them reconstructs the whole original source byte-for-byte. Standalone fixHeight/replaceAtParent, eraseNode, other AVL methods, DP, policy, replay, histories and I/O remain byte-identical.",
        ],
        "limitations": [
            "Invalid/corrupted AVL-state exception behavior is outside equivalence: removed nested guards no longer diagnose those states at the same location.",
            "No measured speedup is claimed. No Cangjie build, solver or CPU benchmark was executed.",
            "blackBox lifetime reasoning follows its documented anti-DCE contract; no generated machine code or target GC was inspected.",
        ],
        "compiled": False, "solver_executed": False, "CPU_benchmark_executed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assert not args.output.exists(), args.output
    args.output.write_text(result)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        source.splitlines(True), result.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output))))
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "sha256": digest(result),
                      "source_reverse_exact": restored == source}))


if __name__ == "__main__":
    main()
