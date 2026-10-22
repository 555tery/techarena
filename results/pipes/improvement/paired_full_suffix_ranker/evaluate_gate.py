#!/usr/bin/env python3
"""Run and analyze the single preregistered 60-stream synthetic gate."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASELINE = HERE / "bin/frozen_final_baseline"
CANDIDATE = HERE / "bin/candidate_final"
INTERACTOR = ROOT / "results/pipes/final/bin/interactor"
HARNESS = ROOT / "tools/pipes_harness.py"
INPUT_MANIFEST = HERE / "inputs/manifest.json"
RUN_ROOT = HERE / "runs/validation"
LOCK_PATH = HERE / "runs/candidate-lock.json"
BOOTSTRAP_REPLICATES = 20_000
BOOTSTRAP_SEED = 2_026_101_817


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_harness(solver: Path, output: Path, label: str) -> dict[str, object]:
    command = [
        sys.executable, str(HARNESS), "--solver", str(solver), "--interactor", str(INTERACTOR),
        "--tests", str(HERE / "inputs/validation"), "--out", str(output),
        "--name", label, "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "120",
    ]
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    record = {"command": command, "returncode": result.returncode,
              "wall_s": time.perf_counter() - started,
              "stdout_tail": result.stdout[-3000:], "stderr_tail": result.stderr[-3000:]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "invocation.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    summary_path = output / "summary.json"
    cases_path = output / "cases.csv"
    if not summary_path.exists() or not cases_path.exists():
        raise RuntimeError(f"harness failed before writing complete outputs for {label}: "
                           f"returncode={result.returncode}\n{result.stderr[-4000:]}\n{result.stdout[-1000:]}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {**record, "summary": summary, "summary_sha256": sha256(output / "summary.json"),
            "cases_sha256": sha256(output / "cases.csv")}


def read_cases(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    result: dict[str, dict[str, str]] = {}
    for record in records:
        key = record["test_sha256"]
        if key in result:
            raise RuntimeError(f"duplicate test hash in {path}: {key}")
        result[key] = record
    return result


def percentile(sorted_values: list[float], q: float) -> float:
    index = (len(sorted_values) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = index - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def verify_candidate_lock() -> dict[str, object]:
    if not LOCK_PATH.exists():
        raise RuntimeError("candidate must be frozen with freeze_candidate.py before evaluation")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    actual = {
        "baseline_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "candidate_source_sha256": sha256(HERE / "src/ranker_candidate.cpp"),
        "candidate_model_sha256": sha256(HERE / "src/ranker_model.hpp"),
        "candidate_binary_sha256": sha256(CANDIDATE),
        "input_manifest_sha256": sha256(INPUT_MANIFEST),
    }
    mismatches = {key: {"frozen": lock.get(key), "actual": value}
                  for key, value in actual.items() if lock.get(key) != value}
    if mismatches:
        raise RuntimeError("frozen candidate or inputs changed after lock: " + json.dumps(mismatches))
    return {**lock, "lock_sha256": sha256(LOCK_PATH)}


def main() -> None:
    lock = verify_candidate_lock()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    compile_command = [
        "clang++", "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Werror",
        "-pedantic", str(ROOT / "results/pipes/final/solution.cpp"), "-o", str(BASELINE),
    ]
    compiled = subprocess.run(compile_command, cwd=ROOT, text=True, capture_output=True)
    if compiled.returncode != 0:
        raise RuntimeError(f"baseline compile failed: {compiled.stderr[-3000:]}")
    if not CANDIDATE.exists():
        raise RuntimeError("final candidate binary is missing")
    baseline_record = run_harness(BASELINE, RUN_ROOT / "baseline", "frozen-final-baseline")
    candidate_record = run_harness(CANDIDATE, RUN_ROOT / "candidate", "paired-full-suffix-ranker")

    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    metadata = {record["sha256"]: record for record in manifest["records"]
                if record["split"] == "validation"}
    base_cases = read_cases(RUN_ROOT / "baseline/cases.csv")
    candidate_cases = read_cases(RUN_ROOT / "candidate/cases.csv")
    if set(base_cases) != set(candidate_cases) or set(base_cases) != set(metadata):
        raise RuntimeError("baseline, candidate, and input manifest test hashes differ")

    paired = []
    invalid = []
    for digest in sorted(metadata, key=lambda h: int(metadata[h]["seed"])):
        meta = metadata[digest]
        base = base_cases[digest]
        candidate = candidate_cases[digest]
        if base["status"] != "ok" or candidate["status"] != "ok":
            invalid.append({"input": meta["path"], "baseline_status": base["status"],
                            "candidate_status": candidate["status"],
                            "baseline_detail": base["detail"], "candidate_detail": candidate["detail"]})
        expected_commands = int(meta["operations"]) + 1
        if int(base["judge_commands_seen_including_final_zero"]) != expected_commands or \
                int(candidate["judge_commands_seen_including_final_zero"]) != expected_commands:
            invalid.append({"input": meta["path"], "reason": "command consumption mismatch"})
        for label, record in (("baseline", base), ("candidate", candidate)):
            cpu = float(record["solver_cpu_total_s"])
            rss = float(record["solver_peak_rss_mb"])
            if cpu >= 5.0 or rss >= 256.0:
                invalid.append({"input": meta["path"], "solver": label,
                                "reason": "resource limit exceeded", "cpu_s": cpu, "rss_mb": rss})
        paired.append({
            **meta,
            "baseline_kpi": float(base["kpi"]),
            "candidate_kpi": float(candidate["kpi"]),
            "delta_kpi": float(candidate["kpi"]) - float(base["kpi"]),
            "baseline_trench_m": int(base["trench_length_m"]),
            "candidate_trench_m": int(candidate["trench_length_m"]),
            "baseline_occupied_m": int(base["occupied_length_m"]),
            "candidate_occupied_m": int(candidate["occupied_length_m"]),
            "baseline_cpu_s": float(base["solver_cpu_total_s"]),
            "candidate_cpu_s": float(candidate["solver_cpu_total_s"]),
            "baseline_rss_mb": float(base["solver_peak_rss_mb"]),
            "candidate_rss_mb": float(candidate["solver_peak_rss_mb"]),
            "baseline_status": base["status"],
            "candidate_status": candidate["status"],
        })

    deltas = [row["delta_kpi"] for row in paired]
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap = sorted(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
                       for _ in range(BOOTSTRAP_REPLICATES))
    mean_delta = sum(deltas) / len(deltas)
    low = percentile(bootstrap, 0.025)
    high = percentile(bootstrap, 0.975)
    long_rows = [row for row in paired if int(row["operations"]) == 200_000]
    long_mean = sum(row["delta_kpi"] for row in long_rows) / len(long_rows)
    for label, record in (("baseline", baseline_record), ("candidate", candidate_record)):
        if record["returncode"] != 0:
            invalid.append({"solver": label, "reason": "harness reported a failed or over-limit case",
                            "returncode": record["returncode"]})
    all_ok = len(paired) == 60 and not invalid
    passed = all_ok and low > 0.0 and long_mean >= 0.0

    with (RUN_ROOT / "paired-streams.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paired[0]))
        writer.writeheader()
        writer.writerows(paired)

    slices: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in paired:
        key = (str(row["operations"]), str(row["profile"]),
               str(row["deletion_policy"]), str(row["regime"]))
        slices[key].append(float(row["delta_kpi"]))
    with (RUN_ROOT / "slices.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["operations", "profile", "deletion_policy", "regime", "streams", "mean_delta_kpi"])
        for key, values in sorted(slices.items()):
            writer.writerow([*key, len(values), sum(values) / len(values)])

    gate = {
        "decision": "PASS" if passed else "NO-GO",
        "stream_count": len(paired), "invalid_records": invalid,
        "mean_paired_delta_kpi": mean_delta,
        "whole_stream_bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "whole_stream_bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_95_percentile_ci": [low, high],
        "long_stream_count": len(long_rows), "long_stream_mean_delta_kpi": long_mean,
        "wins": sum(value > 0 for value in deltas),
        "losses": sum(value < 0 for value in deltas),
        "ties": sum(value == 0 for value in deltas),
        "pass_criteria": {"all_transcripts_and_limits": all_ok,
                          "bootstrap_lower_endpoint_strictly_positive": low > 0.0,
                          "long_stream_mean_nonnegative": long_mean >= 0.0},
        "baseline_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "baseline_binary_sha256": sha256(BASELINE),
        "candidate_source_sha256": sha256(HERE / "src/ranker_candidate.cpp"),
        "candidate_model_sha256": sha256(HERE / "src/ranker_model.hpp"),
        "candidate_binary_sha256": sha256(CANDIDATE),
        "candidate_lock_sha256": lock["lock_sha256"],
        "input_manifest_sha256": sha256(INPUT_MANIFEST),
        "baseline_harness_summary_sha256": baseline_record["summary_sha256"],
        "candidate_harness_summary_sha256": candidate_record["summary_sha256"],
        "baseline_harness_wall_s": baseline_record["wall_s"],
        "candidate_harness_wall_s": candidate_record["wall_s"],
    }
    (RUN_ROOT / "gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, indent=2))
    if verify_candidate_lock() != lock:
        raise RuntimeError("candidate lock changed during validation")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
