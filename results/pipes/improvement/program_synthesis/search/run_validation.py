#!/usr/bin/env python3
"""Evaluate only the train-selected tree #33 on the frozen validation suite."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[0].parent
BIN = HERE / "bin/policy_search"
WRAPPER = HERE / "bin/wrappers/tree-033-validation.sh"
VAL = HERE / "validation"
OUT = VAL / "tree-033"


def main():
    WRAPPER.parent.mkdir(parents=True, exist_ok=True)
    WRAPPER.write_text(f"#!/bin/sh\nPIPES_POLICY_ID=33 exec {BIN}\n")
    WRAPPER.chmod(0o755)
    cmd = [
        sys.executable, str(ROOT / "tools/pipes_harness.py"),
        "--solver", str(WRAPPER), "--interactor", str(ROOT / "tools/interactor"),
        "--name", "tree-033-train-selected", "--tests", str(VAL), "--out", str(OUT),
        "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "180",
    ]
    # Keep the already recorded baseline suite out of the input folder by
    # creating a directory containing only the ten generated .in streams.
    from tempfile import TemporaryDirectory
    import shutil
    with TemporaryDirectory(prefix="pipes-tree-validation-") as tmp:
        source_dir = Path(tmp)
        for path in sorted(VAL.glob("seed-*.in")):
            shutil.copy2(path, source_dir / path.name)
        cmd[cmd.index(str(VAL))] = str(source_dir)
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    baseline = json.loads((VAL / "baseline/summary.json").read_text())
    candidate = json.loads((OUT / "summary.json").read_text())
    deltas = []
    for base, cand in zip(baseline["records"], candidate["records"]):
        deltas.append({
            "case": base["case"],
            "baseline_score": base["weighted_score"],
            "candidate_score": cand["weighted_score"],
            "delta": cand["weighted_score"] - base["weighted_score"],
            "baseline_trench_m": base["trench_length_m"],
            "candidate_trench_m": cand["trench_length_m"],
        })
    baseline_score = baseline["weighted_score_sum"]
    candidate_score = candidate["weighted_score_sum"]
    report = {
        "selected_policy_id": 33,
        "selection_set": "four data/pipes/synthetic/development streams",
        "validation_set_count": len(deltas),
        "baseline_score_sum": baseline_score,
        "candidate_score_sum": candidate_score,
        "delta_score_sum": candidate_score - baseline_score,
        "positive_streams": sum(d["delta"] > 0 for d in deltas),
        "negative_streams": sum(d["delta"] < 0 for d in deltas),
        "neutral_streams": sum(d["delta"] == 0 for d in deltas),
        "per_stream": deltas,
    }
    (OUT / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
