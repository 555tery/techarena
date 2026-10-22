#!/usr/bin/env python3
"""Add a direct lexicographic key comparison; no compile or solver runs."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE / "candidate-flat-keys/solution.cj"
OUT = HERE / "candidate-key-compare"
BASE_SHA = "1d905fadb9a91a222b62ed4732b286626a257fc73cb11416f5f18342df08e710"
METHOD = '''    // Same sign as compareKey(wanted, this[index]); later components are
    // read only when every preceding component compares equal.
    public func compareAt(index: Int64, wanted: Key): Int64 {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Key vector index") }
        let offset = index * 3
        let first = unsafe { data.read(offset) }
        if (wanted.a != first) { return if (wanted.a < first) { -1 } else { 1 } }
        let second = unsafe { data.read(offset + 1) }
        if (wanted.b != second) { return if (wanted.b < second) { -1 } else { 1 } }
        let third = unsafe { data.read(offset + 2) }
        if (wanted.c != third) { return if (wanted.c < third) { -1 } else { 1 } }
        return 0
    }

'''


def main():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    assert "func compareAt(" not in original
    start = original.index("public class FastKeyVector {")
    stop = original.index("\n}\n", start) + 2
    before = original[start:stop]
    marker = "    private func reserveForAdd(): Unit {"
    assert before.count(marker) == 1
    after = before.replace(marker, METHOD + marker)
    source = original[:start] + after + original[stop:]
    edits = []
    for marker in ("public class OrderedMap<V>", "public class IntOrderedMap"):
        start = source.index(marker)
        stop = source.index("\n}\n", start) + 2
        body = source[start:stop]
        for name in ("wanted", "k"):
            old = f"compareKey({name}, keys[node])"
            new = f"keys.compareAt(node, {name})"
            assert body.count(old) == 1, (marker, old)
            body = body.replace(old, new)
            edits.append({"tree": marker, "old": old, "new": new})
        # Reversed-operand lower/upper expressions are explicitly unchanged.
        assert body.count("compareKey(keys[node], wanted)") == 2
        source = source[:start] + body + source[stop:]
    restored = source.replace(METHOD, "", 1)
    for edit in reversed(edits):
        # Each exact expression occurs once in each tree, so reverse globally.
        restored = restored.replace(edit["new"], edit["old"])
    assert restored == original
    assert source.count("keys.compareAt(node, wanted)") == 2
    assert source.count("keys.compareAt(node, k)") == 2
    assert source.count("compareKey(keys[node], wanted)") == 4
    OUT.mkdir(exist_ok=True)
    (OUT / "solution.cj").write_text(source)
    (OUT / "changes.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile="candidate-flat-keys/solution.cj", tofile="candidate-key-compare/solution.cj")))
    metadata = {
        "baseline": str(BASE.relative_to(HERE)),
        "baseline_sha256": BASE_SHA,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "added_method": "FastKeyVector.compareAt(index,wanted)",
        "changed_expressions": edits,
        "sign": "compareKey(wanted, storedKey), never the reverse",
        "proof": [
            "Both old compareKey and compareAt test a, then b, then c; the first unequal Int64 returns-1 iff wanted component<stored component; all equal returns0. No subtraction/overflow-dependent ordering.",
            "The old getter checked0<=node<used then read3*node offsets0/1/2. compareAt performs exactly the same bounds check and offsets; later fields are initialized but need not be read after an earlier difference.",
            "Replaced expressions occur only in find and put. wanted/k are primitive-field Key value parameters, node is a stable local, and neither data nor key fields mutate between comparisons. No callback, exception-prone field getter or concurrent writer is introduced.",
            "No ownership/storage mutation, allocation/free, pointer escape, AVL instruction/tie change, DP/FP change or thread operation is added.",
        ],
        "excluded_scope": "lower/upper reversed comparisons, all other compareKey callers, AVL mutation/rotation/repair, storage owners, DP, replay, I/O and GC remain unchanged.",
        "source_reversal_exact": True,
        "compile_executed": False,
        "solver_executed": False,
        "CPU_benchmark_executed": False,
        "caveats": ["Compiler1.0.5 compatibility, actual speed/RSS and complete transcript parity require parent verification."],
    }
    (OUT / "source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    (HERE / "audit/key-compare-equivalence.json").write_text(json.dumps({
        "status": "pass: static equivalence for the existing single-threaded tree call graph",
        **metadata,
        "findings": [],
    }, ensure_ascii=False, indent=2) + "\n")
    print(OUT / "solution.cj")
    print(metadata["source_sha256"])


if __name__ == "__main__":
    main()
