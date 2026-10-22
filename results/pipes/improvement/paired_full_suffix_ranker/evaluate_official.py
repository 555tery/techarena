#!/usr/bin/env python3
"""Run the one-time, diagnostic Open15 and holdout-v2 comparison."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASELINE = HERE / "bin/frozen_final_baseline"
CANDIDATE = HERE / "bin/candidate_final"
INTERACTOR = ROOT / "results/pipes/final/bin/interactor"
HARNESS = ROOT / "tools/pipes_harness.py"
LOCK_PATH = HERE / "runs/candidate-lock.json"
GATE_PATH = HERE / "runs/validation/gate.json"
OUT = HERE / "runs/official-diagnostic"
DATASETS = {
    "open15": ROOT / "data/pipes/open",
    "holdout_v2": ROOT / "data/pipes/synthetic/final-holdout-v2",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_lock() -> dict[str, object]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    actual = {
        "baseline_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "candidate_source_sha256": sha256(HERE / "src/ranker_candidate.cpp"),
        "candidate_model_sha256": sha256(HERE / "src/ranker_model.hpp"),
        "candidate_binary_sha256": sha256(CANDIDATE),
    }
    mismatch = {k: {"frozen": lock.get(k), "actual": v}
                for k, v in actual.items() if lock.get(k) != v}
    if mismatch:
        raise RuntimeError("frozen source/binary changed: " + json.dumps(mismatch))
    return {**lock, "lock_sha256": sha256(LOCK_PATH)}


def run_harness(solver: Path, output: Path, name: str, tests: Path) -> dict[str, object]:
    command = [
        sys.executable, str(HARNESS), "--solver", str(solver), "--interactor", str(INTERACTOR),
        "--tests", str(tests), "--out", str(output), "--name", name,
        "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "120",
    ]
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    record = {"command": command, "returncode": result.returncode,
              "wall_s": time.perf_counter() - started,
              "stdout_tail": result.stdout[-3000:], "stderr_tail": result.stderr[-3000:]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "invocation.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if not (output / "summary.json").exists() or not (output / "cases.csv").exists():
        raise RuntimeError(f"harness failed before writing full outputs ({name}): {result.stderr[-3000:]}")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    return {**record, "summary": summary, "summary_sha256": sha256(output / "summary.json"),
            "cases_sha256": sha256(output / "cases.csv")}


def read_cases(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    by_hash: dict[str, dict[str, str]] = {}
    for row in rows:
        digest = row["test_sha256"]
        if digest in by_hash:
            raise RuntimeError(f"duplicate test hash in {path}: {digest}")
        by_hash[digest] = row
    return by_hash


def main() -> None:
    if OUT.exists():
        raise RuntimeError("one-time diagnostic output already exists; refusing a repeat")
    if not GATE_PATH.exists():
        raise RuntimeError("synthetic transcript validation must finish before official diagnostics")
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    if not gate.get("pass_criteria", {}).get("all_transcripts_and_limits", False):
        raise RuntimeError("synthetic transcripts or resource limits failed; official run is not authorized")
    lock = verify_lock()
    if gate.get("candidate_lock_sha256") != lock["lock_sha256"]:
        raise RuntimeError("synthetic gate belongs to a different candidate lock")
    for name, path in DATASETS.items():
        if not path.is_dir() or not list(path.glob("*.in")):
            raise RuntimeError(f"missing input directory or tests: {path}")

    OUT.mkdir(parents=True)
    compiled = subprocess.run([
        "clang++", "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Werror", "-pedantic",
        str(ROOT / "results/pipes/final/solution.cpp"), "-o", str(BASELINE),
    ], cwd=ROOT, text=True, capture_output=True)
    if compiled.returncode != 0:
        raise RuntimeError(f"baseline compile failed: {compiled.stderr[-3000:]}")

    runs: dict[str, dict[str, object]] = {}
    comparisons: dict[str, list[dict[str, object]]] = {}
    for dataset, tests in DATASETS.items():
        base_out = OUT / dataset / "baseline"
        candidate_out = OUT / dataset / "candidate"
        base_run = run_harness(BASELINE, base_out, f"frozen-final-{dataset}", tests)
        candidate_run = run_harness(CANDIDATE, candidate_out, f"paired-full-suffix-ranker-{dataset}", tests)
        runs[dataset] = {"baseline": base_run, "candidate": candidate_run}
        base_rows = read_cases(base_out / "cases.csv")
        candidate_rows = read_cases(candidate_out / "cases.csv")
        if set(base_rows) != set(candidate_rows):
            raise RuntimeError(f"baseline/candidate inputs differ on {dataset}")
        rows = []
        for digest, base in base_rows.items():
            candidate = candidate_rows[digest]
            rows.append({
                "dataset": dataset,
                "test_file": base["case"],
                "test_sha256": digest,
                "baseline_status": base["status"],
                "candidate_status": candidate["status"],
                "baseline_weighted_score": base["weighted_score"],
                "candidate_weighted_score": candidate["weighted_score"],
                "delta_weighted_score": float(candidate["weighted_score"] or 0.0) -
                                        float(base["weighted_score"] or 0.0),
                "baseline_kpi": base["kpi"],
                "candidate_kpi": candidate["kpi"],
                "baseline_trench_m": base["trench_length_m"],
                "candidate_trench_m": candidate["trench_length_m"],
                "baseline_cpu_s": base["solver_cpu_total_s"],
                "candidate_cpu_s": candidate["solver_cpu_total_s"],
                "baseline_rss_mib": base["solver_peak_rss_mb"],
                "candidate_rss_mib": candidate["solver_peak_rss_mb"],
            })
        comparisons[dataset] = rows
        with (OUT / f"{dataset}-per-case.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    if verify_lock() != lock:
        raise RuntimeError("candidate lock changed during official diagnostics")
    summaries = {}
    for dataset, rows in comparisons.items():
        summaries[dataset] = {
            "cases": len(rows),
            "baseline_weighted_score_sum": sum(float(r["baseline_weighted_score"] or 0.0) for r in rows),
            "candidate_weighted_score_sum": sum(float(r["candidate_weighted_score"] or 0.0) for r in rows),
            "delta_weighted_score_sum": sum(float(r["delta_weighted_score"]) for r in rows),
            "all_transcripts_ok": all(r["baseline_status"] == r["candidate_status"] == "ok" for r in rows),
            "baseline_harness_returncode": runs[dataset]["baseline"]["returncode"],
            "candidate_harness_returncode": runs[dataset]["candidate"]["returncode"],
        }
    manifest = {
        "purpose": "one-time diagnostic only; no model selection or refitting",
        "candidate_lock_sha256": lock["lock_sha256"],
        "synthetic_gate_sha256": sha256(GATE_PATH),
        "baseline_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "baseline_binary_sha256": sha256(BASELINE),
        "candidate_source_sha256": sha256(HERE / "src/ranker_candidate.cpp"),
        "candidate_model_sha256": sha256(HERE / "src/ranker_model.hpp"),
        "candidate_binary_sha256": sha256(CANDIDATE),
        "dataset_inputs": {key: {"directory": str(path.relative_to(ROOT)),
                                  "files": sorted(p.name for p in path.glob("*.in")),
                                  "hashes": {p.name: sha256(p) for p in sorted(path.glob("*.in"))}}
                            for key, path in DATASETS.items()},
        "run_records": runs,
        "summary": summaries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
