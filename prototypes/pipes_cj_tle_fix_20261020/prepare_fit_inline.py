#!/usr/bin/env python3
"""Inline fit's exposure calls and reuse immutable per-bin scalar values."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
EXPOSURE = """    private func exposure(cell: LifetimeCell, bin: Int64): Int64 {
        let outstanding: Int64 = if (cell.active == 0) { 0 } else { cell.active * (clock - lower[bin]) - cell.birthSum }
        return cell.completedExposure + outstanding
    }
"""


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=BASE / "candidate-dp-flat/solution.cj")
    ap.add_argument("--output", type=Path, default=BASE / "candidate-fit-inline/solution.cj")
    args = ap.parse_args()
    original = args.source.read_text()
    assert original.count(EXPOSURE) == 1
    assert "private let lower: VArray<Int64, $8> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]" in original
    assert all(name not in original for name in ("fitBinLower", "fitOutstanding", "fitExposure"))
    start = original.index("    public func fit(priorHazard: Float64): Bool {")
    end = original.index("    public func existingRisk(", start)
    before = original[start:end]
    after = before
    edits = []

    def change(old, new):
        nonlocal after
        assert after.count(old) == 1, old
        after = after.replace(old, new)
        edits.append({"old": old, "new": new})

    change("""        for (bin in 0..8) {
            var pooledExposure: Float64 = 0.0
""", """        for (bin in 0..8) {
            let fitBinLower = lower[bin]
            var pooledExposure: Float64 = 0.0
""")
    change("""                pooledExposure += Float64(exposure(cells[(length) * 8 + (bin)], bin))
                pooledDeaths += Float64(cells[(length) * 8 + (bin)].deaths)
""", """                let cell = cells[(length) * 8 + (bin)]
                let fitOutstanding: Int64 = if (cell.active == 0) { 0 } else { cell.active * (clock - fitBinLower) - cell.birthSum }
                let fitExposure = cell.completedExposure + fitOutstanding
                pooledExposure += Float64(fitExposure)
                pooledDeaths += Float64(cell.deaths)
""")
    change("""            let pooledError = sqrt(pooledDeaths + priorEvents) / pooledDenominator
            for (length in 1..41) {
                let cell = cells[(length) * 8 + (bin)]
                let borrowedExposure = priorEvents / pooledRate
                let denominator = Float64(exposure(cell, bin)) + borrowedExposure
""", """            let pooledError = sqrt(pooledDeaths + priorEvents) / pooledDenominator
            let borrowedExposure = priorEvents / pooledRate
            for (length in 1..41) {
                let cell = cells[(length) * 8 + (bin)]
                let fitOutstanding: Int64 = if (cell.active == 0) { 0 } else { cell.active * (clock - fitBinLower) - cell.birthSum }
                let fitExposure = cell.completedExposure + fitOutstanding
                let denominator = Float64(fitExposure) + borrowedExposure
""")
    assert "exposure(" not in after
    restored_fit = after
    for edit in reversed(edits):
        assert restored_fit.count(edit["new"]) == 1
        restored_fit = restored_fit.replace(edit["new"], edit["old"])
    assert restored_fit == before
    result = original[:start] + after + original[end:]
    restored = result[:start] + restored_fit + result[start + len(after):]
    assert restored == original
    metadata = {
        "schema": "fit-inline-source-equivalence-v1",
        "parent": str(args.source.resolve()), "parent_sha256": digest(original),
        "source_sha256": digest(result), "generator_sha256": digest(Path(__file__).read_text()),
        "scope": "Only CensoredLifetimeModel.fit; exposure/predict and every other byte unchanged",
        "reverse_exact": restored == original, "reverse_sha256": digest(restored),
        "edits": edits,
        "per_fit_changes": {"exposure_calls_removed": 640, "pooled_cell_reloads_removed": 320,
                            "bin_lower_loads": 8, "borrowed_exposure_divisions": "320 ->8"},
        "proof": [
            "Inline Int64 expressions are the original exposure payload. All multiplications, subtractions, completed-exposure additions and conditional evaluation remain in their original order. clock-fitBinLower is evaluated only when cell.active!=0, exactly as before.",
            "lower is an immutable eight-element VArray, and bin is always0..7; caching lower[bin] performs a pure in-bounds read. No clock-lower subtraction is speculated into inactive-cell paths, preserving checked-overflow behavior even for arbitrary Int64 clocks.",
            "cells and clock are not modified during fit, and there are no callbacks that can mutate them. Reusing the same value-copy cell for pooled exposure/deaths is equivalent to its old two reads.",
            "Each second length loop has exactly40 iterations. priorEvents and pooledRate remain unchanged, so the same Float64 quotient borrowedExposure can be copied after one division instead of recomputed40 times. Its first evaluation stays after pooledError and before the first denominator; all remaining arithmetic and accumulation orders are unchanged.",
            "Neither exposure/predict implementations nor the final population/reference-rate pass change. Reversing the three exact fit edits restores the entire source byte-for-byte.",
        ],
        "limits": [
            "Repeated identical quotient evaluations are removed; the actual instruction count changes, while their binary result is reused. No runtime floating-point environment changes or callbacks occur inside fit.",
            "Source equivalence is not a target-O2 machine-code proof. No Cangjie compile, solver or CPU benchmark was performed and no speedup is promised.",
        ],
        "compiled": False, "solver_executed": False, "CPU_benchmark_executed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assert not args.output.exists(), args.output
    args.output.write_text(result)
    args.output.with_suffix(".diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), result.splitlines(True),
        fromfile=str(args.source), tofile=str(args.output))))
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "sha256": digest(result), "reverse_exact": True}))


if __name__ == "__main__":
    main()
