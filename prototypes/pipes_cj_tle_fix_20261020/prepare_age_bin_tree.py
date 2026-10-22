#!/usr/bin/env python3
"""Replace only ageBin with an exact three-comparison Int64 decision tree."""
import argparse
import bisect
import difflib
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
LOWER = "    private let lower: VArray<Int64, $8> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]"
OLD = """    private func ageBin(age: Int64): Int64 {
        var bin: Int64 = 0
        while (bin + 1 < 8 && age >= lower[bin + 1]) { bin++ }
        return bin
    }
"""
NEW = """    private func ageBin(age: Int64): Int64 {
        if (age < 1024) {
            if (age < 64) {
                return if (age < 16) { 0 } else { 1 }
            }
            return if (age < 256) { 2 } else { 3 }
        }
        if (age < 16384) {
            return if (age < 4096) { 4 } else { 5 }
        }
        return if (age < 65536) { 6 } else { 7 }
    }
"""


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def tree(age):
    if age < 1024:
        if age < 64:
            return 0 if age < 16 else 1
        return 2 if age < 256 else 3
    if age < 16384:
        return 4 if age < 4096 else 5
    return 6 if age < 65536 else 7


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path,
                    default=BASE / "candidate-avl-inline/solution.cj")
    ap.add_argument("--output", type=Path,
                    default=BASE / "candidate-age-bin-tree/solution.cj")
    args = ap.parse_args()
    source = args.source.read_text()
    assert source.count(LOWER) == 1, "Immutable lower table changed"
    assert source.count(OLD) == 1, "Expected exact single old ageBin"
    result = source.replace(OLD, NEW)
    assert result.count(NEW) == 1
    assert result.replace(NEW, OLD) == source
    # Both procedures change value only at these seven thresholds. Checking
    # each partition's endpoints proves equality on every signed Int64 input.
    thresholds = [16, 64, 256, 1024, 4096, 16384, 65536]
    minimum, maximum = -(1 << 63), (1 << 63) - 1
    intervals = list(zip([minimum] + thresholds,
                         [x - 1 for x in thresholds] + [maximum]))
    partitions = []
    for expected, (start, end) in enumerate(intervals):
        for age in (start, end):
            assert tree(age) == bisect.bisect_right(thresholds, age) == expected
        partitions.append({"from": start, "through": end, "bin": expected})
    metadata = {
        "schema": "age-bin-balanced-tree-equivalence-v1",
        "parent": str(args.source.resolve()), "parent_sha256": digest(source),
        "source_sha256": digest(result), "generator_sha256": digest(Path(__file__).read_text()),
        "scope": "Only the one ageBin method; lower table and fit/predict unchanged",
        "source_reverse_exact": result.replace(NEW, OLD) == source,
        "thresholds": thresholds, "all_int64_partitions": partitions,
        "comparison_count_per_call": 3,
        "proof": [
            "Original loop returns the number of thresholds from16 through65536 less than or equal to age, with bins0 through7. Negative inputs also return0 because the first tested threshold is16, not lower[0].",
            "Balanced strict-less-than comparisons route each of the eight disjoint signed-Int64 intervals to its identical bin. Threshold equalities go to the upper interval, exactly matching the old age>=lower test.",
            "The eight intervals cover Int64.Min through Int64.Max without gaps or overlaps. No arithmetic, conversion, allocation, pointer access, state update or FP operation occurs in the replacement.",
            "Only ageBin changes. Replacing the new function with the old function reconstructs every original byte, including lower, fit/predict, all model storage and all policies.",
        ],
        "performance": "Exactly three scalar comparisons, replacing up to seven VArray accesses and loop bookkeeping. Actual CPU benefit has not been measured.",
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
                      "source_reverse_exact": metadata["source_reverse_exact"]}))


if __name__ == "__main__":
    main()
