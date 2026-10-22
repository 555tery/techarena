#!/usr/bin/env python3
"""Evaluate the frozen set of 64 depth-2 gates on separate train streams."""

from __future__ import annotations

import concurrent.futures
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[0].parent
BIN = HERE / "bin/policy_search"
TRAIN = HERE / "train"
OUT = HERE / "search/train_runs"
WRAPPERS = HERE / "bin/wrappers"
INTERACTOR = ROOT / "tools/interactor"
HARNESS = ROOT / "tools/pipes_harness.py"


def evaluate(policy_id: int):
    wrapper = WRAPPERS / f"policy-{policy_id:03d}.sh"
    wrapper.write_text(f"#!/bin/sh\nPIPES_POLICY_ID={policy_id} exec {BIN}\n")
    wrapper.chmod(0o755)
    run_dir = OUT / f"policy-{policy_id:03d}"
    cmd = [
        sys.executable, str(HARNESS), "--solver", str(wrapper),
        "--interactor", str(INTERACTOR), "--name", f"tree-{policy_id:03d}",
        "--tests", str(TRAIN), "--out", str(run_dir),
        "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "120",
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    summary_path = run_dir / "summary.json"
    if result.returncode != 0 or not summary_path.exists():
        return {"policy_id": policy_id, "status": "error", "detail": (result.stdout + result.stderr)[-3000:]}
    summary = json.loads(summary_path.read_text())
    return {
        "policy_id": policy_id,
        "status": "ok" if summary["ok_count"] == summary["case_count"] else "invalid",
        "score": summary["weighted_score_sum"],
        "mean_kpi": summary["weighted_score_sum"] / summary["weight_sum"],
        "max_cpu_s": max((r.get("solver_cpu_total_s") or 0) for r in summary["records"]),
        "max_rss_mib": max((r.get("solver_peak_rss_mb") or 0) for r in summary["records"]),
        "max_trench_m": max((r.get("trench_length_m") or 0) for r in summary["records"]),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    WRAPPERS.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((TRAIN / "baseline-dynamic/summary.json").read_text())
    baseline_score = baseline["weighted_score_sum"]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(evaluate, i) for i in range(1, 65)]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            if row["status"] == "ok":
                row["delta_vs_baseline"] = row["score"] - baseline_score
            results.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    results.sort(key=lambda x: x["policy_id"])
    with (OUT / "ranked.csv").open("w", newline="") as f:
        fields = ["policy_id", "status", "score", "delta_vs_baseline", "mean_kpi", "max_cpu_s", "max_rss_mib", "max_trench_m"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    (OUT / "ranked.json").write_text(json.dumps({
        "baseline_score": baseline_score,
        "candidate_count": len(results),
        "results": results,
    }, indent=2) + "\n")
    errors = sum(r["status"] != "ok" for r in results)
    print(f"complete candidates={len(results)} errors={errors} baseline={baseline_score:.12f}")


if __name__ == "__main__":
    main()
