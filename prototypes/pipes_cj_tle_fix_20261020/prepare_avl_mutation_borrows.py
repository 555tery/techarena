#!/usr/bin/env python3
"""Replace AVL numeric access wrappers within functions that never resize them."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

FIELDS = ("left", "right", "parent", "heights")
METHODS = ("fixHeight", "replaceAtParent", "rotateLeft", "rotateRight", "rebalance", "eraseNode")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def close_at(text, start, opening, closing):
    level = 0
    for i in range(start, len(text)):
        if text[i] == opening:
            level += 1
        elif text[i] == closing:
            level -= 1
            if level == 0:
                return i
    raise ValueError("Unbalanced source")


def accesses(text, fields):
    pattern = re.compile(r"\b(" + "|".join(fields) + r")\[")
    output = []
    pos = 0
    while m := pattern.search(text, pos):
        output.append(text[pos:m.start()])
        end = close_at(text, m.end() - 1, "[", "]")
        index = accesses(text[m.end():end], fields)
        pointer = "nav" + m[1].capitalize()
        after = end + 1
        while after < len(text) and text[after] in " \t":
            after += 1
        if text[after:after + 1] == "=" and text[after:after + 2] != "==":
            finish = after + 1
            while finish < len(text) and text[finish] not in ";\n}":
                finish += 1
            rhs = text[after + 1:finish].strip()
            assert "{" not in rhs, rhs
            output.append(f"{pointer}.write({index}, {accesses(rhs, fields)})")
            # Keep spaces separating a one-line statement and its closing }.
            output.append(text[after + 1:finish][len(text[after + 1:finish].rstrip()):])
            pos = finish
        else:
            output.append(f"{pointer}.read({index})")
            pos = end + 1
    output.append(text[pos:])
    return "".join(output)


def convert_body(name, body):
    used = [field for field in FIELDS if re.search(rf"\b{field}\[", body)]
    assert used
    transformed = accesses(body, used).strip("\n")
    # The sole early return precedes every pointer use in eraseNode.
    if name == "eraseNode":
        assert transformed.startswith("        if (node == 0) { return }\n")
        transformed = transformed.removeprefix("        if (node == 0) { return }\n")
    result_return = None
    if name in ("rotateLeft", "rotateRight"):
        assert transformed.rstrip().endswith("return top")
        transformed = transformed.rstrip().removesuffix("return top").rstrip()
        result_return = "top"
    head = "\n"
    if name == "eraseNode":
        head += "        if (node == 0) { return }\n"
    if name == "rebalance":
        head += "        if (start == 0) { return }\n"
    indices = {
        "fixHeight": ("node",),
        "replaceAtParent": ("oldNode", "newNode"),
        "rotateLeft": ("node",),
        "rotateRight": ("node",),
        "rebalance": ("start",),
        "eraseNode": ("node",),
    }[name]
    head += "        let allocated = keys.size\n"
    condition = " || ".join(f"{v} < 0 || {v} >= allocated" for v in indices)
    head += f'        if ({condition}) {{ throw IndexOutOfBoundsException("AVL node") }}\n'
    for field in used:
        head += f"        let nav{field.capitalize()} = {field}.borrowData()\n"
    head += "        unsafe {\n"
    transformed = "\n".join("    " + line for line in transformed.splitlines())
    tail = (
        "\n            // No helper below resizes these vectors. The owner check\n"
        "            // after the final pointer use keeps all buffers reachable.\n"
        "            blackBox(this)\n"
        '            if (keys.size != allocated) { throw IllegalStateException("AVL storage changed") }\n'
    )
    if result_return:
        tail += f"            return {result_return}\n"
    tail += "        }\n    "
    return head + transformed + tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    source = args.source.read_text()
    assert "func borrowData(): CPointer<Int64>" in source
    result = source
    edits = []
    for name in METHODS:
        expression = re.compile(r"    (?:private|public) func " + name + r"\([^{}]*\): \w+ \{")
        found = list(expression.finditer(result))
        assert len(found) == 2, (name, len(found))
        for m in reversed(found):
            start = m.end() - 1
            end = close_at(result, start, "{", "}")
            old = result[start + 1:end]
            new = convert_body(name, old)
            edits.append({"method": name, "before_sha256": digest(old), "after_sha256": digest(new)})
            result = result[:start + 1] + new + result[end:]
    # Outside the twelve selected method bodies everything is byte-identical.
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "solution.cj").write_text(result)
    (args.output / "solution.diff").write_text("".join(difflib.unified_diff(
        source.splitlines(True), result.splitlines(True), fromfile=str(args.source), tofile="solution.cj",
    )))
    (args.output / "source.json").write_text(json.dumps({
        "parent": str(args.source.resolve()), "parent_sha256": digest(source),
        "source_sha256": digest(result), "generator_sha256": digest(Path(__file__).read_text()),
        "scope": "Borrow left/right/parent/heights only in non-resizing mutation helpers",
        "methods": edits,
        "ownership": [
            "All pointers belong to existing vectors, which these methods and nested helpers never append to.",
            "eraseNode appends only to vacant, whose allocation is distinct and never borrowed.",
            "No pointer is stored, returned, copied to another owner, or used across newNode.",
            "Each selected method calls the documented std.runtime.blackBox(this) after its last pointer access, retaining this and all owning fields even under optimization.",
        ],
        "invariants": [
            "Every reachable child/parent ID is zero or below allocated vector size.",
            "Zero sentinel is allocated in all arrays and maintains height zero.",
            "All writes, rotation calls, branches, tie decisions and height arithmetic retain their original order.",
            "The map is single-threaded; no helper performs callbacks or changes a vector owner.",
        ],
    }, indent=2) + "\n")
    print(digest(result))


if __name__ == "__main__":
    main()
