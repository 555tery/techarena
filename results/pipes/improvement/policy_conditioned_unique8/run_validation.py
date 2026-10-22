#!/usr/bin/env python3
"""Run paired local harness validation against the frozen final binary."""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "inputs" / "validation_manifest.json"
BASELINE = HERE / "bin" / "frozen_final_linux"
CANDIDATE = HERE / "bin" / "policy_conditioned_linux"
DIAGNOSTIC = HERE / "bin" / "policy_conditioned_linux_diag"
INTERACTOR = HERE / "bin" / "interactor_linux"
OUT = HERE / "validation"
COUNTER_RE = re.compile(r"(\w+)=([0-9]+)")
EVAL_RE = re.compile(
    r"policy_eval op=(\d+) baseline_start=(-?\d+) p4_start=(-?\d+) "
    r"unique=(\d+) wins=(\d+) losses=(\d+) delta_sum_m=(-?\d+) choose_p4=(\d+)"
)
UNIQUE_SKIP_RE = re.compile(r"policy_skip_unique op=(\d+) unique=(\d+)")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_harness(binary: Path, item: dict, label: str) -> dict:
    test_path = ROOT / item["file"]
    out = OUT / "runs" / item["case"] / label
    out.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable, str(ROOT / "tools/pipes_harness.py"),
        "--solver", str(binary), "--interactor", str(INTERACTOR),
        "--tests", str(test_path), "--out", str(out), "--name", label,
        "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "240",
    ]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (out / "harness.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (out / "harness.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"harness failed: {item['case']} {label}: {proc.returncode}\n{proc.stderr}")
    summary_path = out / "summary.json"
    if not summary_path.exists():
        raise RuntimeError(f"missing summary: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("case_count") != 1 or summary.get("ok_count") != 1:
        raise RuntimeError(f"transcript not accepted: {item['case']} {label}: {summary}")
    record = summary["records"][0]
    if record.get("judge_commands_seen_including_final_zero") != item["operations"] + 1:
        raise RuntimeError(f"incomplete transcript: {item['case']} {label}: {record}")
    return record


def run_pair(item: dict) -> dict:
    baseline = run_harness(BASELINE, item, "frozen-final")
    candidate = run_harness(CANDIDATE, item, "policy-conditioned")
    if baseline["test_sha256"] != candidate["test_sha256"]:
        raise RuntimeError(f"paired inputs differ for {item['case']}")
    return {
        "case": item["case"],
        "input_sha256": item["sha256"],
        "operations": item["operations"],
        "length_profile": item["length_profile"],
        "deletion_policy": item["deletion_policy"],
        "baseline_status": baseline["status"],
        "candidate_status": candidate["status"],
        "baseline_trench_m": baseline["trench_length_m"],
        "candidate_trench_m": candidate["trench_length_m"],
        "delta_trench_m_candidate_minus_baseline": candidate["trench_length_m"] - baseline["trench_length_m"],
        "baseline_kpi": baseline["kpi"],
        "candidate_kpi": candidate["kpi"],
        "delta_kpi_candidate_minus_baseline": candidate["kpi"] - baseline["kpi"],
        "baseline_cpu_s": baseline["solver_cpu_total_s"],
        "candidate_cpu_s": candidate["solver_cpu_total_s"],
        "baseline_rss_mib": baseline["solver_peak_rss_mb"],
        "candidate_rss_mib": candidate["solver_peak_rss_mb"],
        "candidate_cpu_limit_exceeded": candidate["solver_cpu_limit_exceeded"],
        "candidate_memory_limit_exceeded": candidate["solver_memory_limit_exceeded"],
        "candidate_reply_count": candidate["judge_commands_seen_including_final_zero"] - 1,
        "expected_reply_count": item["operations"],
    }


def replay_diagnostics(item: dict) -> dict:
    path = ROOT / item["file"]
    tokens = path.read_text(encoding="ascii").split()
    count = int(tokens[1])
    commands = [int(token) for token in tokens[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError(f"invalid input transcript: {path}")
    payload = ("\n".join(map(str, commands)) + "\n").encode("ascii")
    baseline = subprocess.run([str(BASELINE)], input=payload, capture_output=True, check=True)
    candidate = subprocess.run([str(DIAGNOSTIC)], input=payload, capture_output=True, check=True)
    baseline_lines = baseline.stdout.splitlines()
    candidate_lines = candidate.stdout.splitlines()
    if len(baseline_lines) != count or len(candidate_lines) != count:
        raise RuntimeError(f"reply count mismatch for {item['case']}")
    changed = [i for i, (a, b) in enumerate(zip(baseline_lines, candidate_lines)) if a != b]
    stderr = candidate.stderr.decode("utf-8", errors="replace")
    counter_line = next((line for line in stderr.splitlines() if line.startswith("mc_decisions=")), "")
    counters = {key: int(value) for key, value in COUNTER_RE.findall(counter_line)}
    evaluations = []
    for match in EVAL_RE.finditer(stderr):
        evaluations.append({
            "op": int(match.group(1)),
            "baseline_start": int(match.group(2)),
            "p4_start": int(match.group(3)),
            "unique_scenarios": int(match.group(4)),
            "paired_wins": int(match.group(5)),
            "paired_losses": int(match.group(6)),
            "paired_delta_sum_m": int(match.group(7)),
            "chose_p4": bool(int(match.group(8))),
        })
    low_unique_rejections = [
        {"op": int(match.group(1)), "unique_scenarios": int(match.group(2))}
        for match in UNIQUE_SKIP_RE.finditer(stderr)
    ]
    return {
        "case": item["case"],
        "input_sha256": item["sha256"],
        "reply_count": count,
        "different_reply_lines_vs_baseline": len(changed),
        "first_different_reply_indexes": changed[:12],
        "baseline_stdout_sha256": sha256(baseline.stdout),
        "candidate_stdout_sha256": sha256(candidate.stdout),
        "counters": counters,
        "evaluations": evaluations,
        "low_unique_rejections": low_unique_rejections,
        "candidate_stderr_sha256": sha256(candidate.stderr),
    }


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite existing validation output: {OUT}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = manifest["records"]
    OUT.mkdir(parents=True)
    (OUT / "logs").mkdir()
    # Run one paired case at a time so solver CPU/RSS measurements have no
    # competing harness child process on this host.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        futures = {pool.submit(run_pair, item): item for item in items}
        rows = []
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            row = future.result()
            rows.append(row)
            print(
                f"finished {row['case']}: dKPI={row['delta_kpi_candidate_minus_baseline']:+.9f}, "
                f"dTrench={row['delta_trench_m_candidate_minus_baseline']:+d}m, "
                f"CPU={row['candidate_cpu_s']:.3f}s, RSS={row['candidate_rss_mib']:.2f}MiB",
                flush=True,
            )
    rows.sort(key=lambda row: (row["operations"], row["length_profile"], row["deletion_policy"]))
    with (OUT / "per_case.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    telemetry = []
    for item in items:
        record = replay_diagnostics(item)
        telemetry.append(record)
        print(
            f"telemetry {item['case']}: calls={record['counters'].get('policy_calls', 0)}, "
            f"evals={record['counters'].get('policy_evaluations', 0)}, "
            f"P4={record['counters'].get('policy_p4_choices', 0)}, "
            f"changed={record['different_reply_lines_vs_baseline']}", flush=True,
        )
    (OUT / "telemetry.json").write_text(json.dumps(telemetry, indent=2) + "\n", encoding="utf-8")

    paired = {
        "case_count": len(rows),
        "ok_pairs": sum(r["baseline_status"] == r["candidate_status"] == "ok" for r in rows),
        "mean_kpi_delta_equal_case_weight": sum(r["delta_kpi_candidate_minus_baseline"] for r in rows) / len(rows),
        "mean_trench_delta_m_equal_case_weight": sum(r["delta_trench_m_candidate_minus_baseline"] for r in rows) / len(rows),
        "candidate_max_cpu_s": max(r["candidate_cpu_s"] for r in rows),
        "candidate_max_rss_mib": max(r["candidate_rss_mib"] for r in rows),
        "candidate_cpu_violations": sum(bool(r["candidate_cpu_limit_exceeded"]) for r in rows),
        "candidate_memory_violations": sum(bool(r["candidate_memory_limit_exceeded"]) for r in rows),
        "candidate_cases_with_different_trench": sum(r["delta_trench_m_candidate_minus_baseline"] != 0 for r in rows),
        "candidate_cases_improved_trench": sum(r["delta_trench_m_candidate_minus_baseline"] < 0 for r in rows),
        "candidate_cases_regressed_trench": sum(r["delta_trench_m_candidate_minus_baseline"] > 0 for r in rows),
        "independent_inputs": len(items),
        "not_platform_tests_or_leaderboard": True,
    }
    (OUT / "summary.json").write_text(json.dumps(paired, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(paired, indent=2), flush=True)


if __name__ == "__main__":
    main()
