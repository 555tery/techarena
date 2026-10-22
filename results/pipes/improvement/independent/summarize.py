#!/usr/bin/env python3
"""Build paired open-test comparisons from official harness reports."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
CONFIGS = [
    ("demand-w32-b10", 32, 10, "demand_w32_b10"),
    ("demand-w32-b40", 32, 40, "demand_w32_b40"),
    ("demand-w128-b10", 128, 10, "demand_w128_b10"),
    ("demand-w128-b40", 128, 40, "demand_w128_b40"),
    ("demand-w512-b10", 512, 10, "demand_w512_b10"),
    ("demand-w512-b40", 512, 40, "demand_w512_b40"),
]


def load_run(name: str) -> dict:
    return json.loads((RUNS / name / "summary.json").read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resource_summary(report: dict) -> tuple[float, float]:
    return (max(r["solver_cpu_total_s"] for r in report["records"]),
            max(r["solver_peak_rss_mb"] for r in report["records"]))


baseline = load_run("baseline-policy4")
hybrid = load_run("hybrid-age-interior-5")
candidate_reports = {name: load_run(name) for name, _, _, _ in CONFIGS}
all_reports = {"baseline-policy4": baseline,
               "hybrid-age-interior-5": hybrid,
               **candidate_reports}

for name, report in all_reports.items():
    assert report["case_count"] == report["ok_count"] == 15, name
    assert report["weight_sum"] == 32.1, name

baseline_cases = {str(r["case"]): r for r in baseline["records"]}
hybrid_cases = {str(r["case"]): r for r in hybrid["records"]}
for name, report in all_reports.items():
    for record in report["records"]:
        case = str(record["case"])
        assert record["test_sha256"] == baseline_cases[case]["test_sha256"], (name, case)

per_case = []
for case in sorted(baseline_cases, key=int):
    base = baseline_cases[case]
    h = hybrid_cases[case]
    row = {
        "case": int(case),
        "weight": base["weight"],
        "test_sha256": base["test_sha256"],
        "baseline_kpi": base["kpi"],
        "baseline_trench_m": base["trench_length_m"],
        "hybrid_kpi": h["kpi"],
        "hybrid_trench_m": h["trench_length_m"],
        "hybrid_weighted_delta_vs_baseline": h["weighted_score"] - base["weighted_score"],
    }
    for name, _, _, _ in CONFIGS:
        candidate = {str(r["case"]): r for r in candidate_reports[name]["records"]}[case]
        row[f"{name}_kpi"] = candidate["kpi"]
        row[f"{name}_trench_m"] = candidate["trench_length_m"]
        row[f"{name}_weighted_delta_vs_baseline"] = candidate["weighted_score"] - base["weighted_score"]
        row[f"{name}_weighted_delta_vs_hybrid"] = candidate["weighted_score"] - h["weighted_score"]
    per_case.append(row)

with (ROOT / "per_case_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(per_case[0]))
    writer.writeheader()
    writer.writerows(per_case)

candidate_rows = []
for name, window, bonus, binary_name in CONFIGS:
    report = candidate_reports[name]
    max_cpu, max_rss = resource_summary(report)
    candidate_rows.append({
        "candidate": name,
        "window": window,
        "bonus_m": bonus,
        "weighted_score": report["weighted_score_sum"],
        "delta_vs_policy4": report["weighted_score_sum"] - baseline["weighted_score_sum"],
        "delta_vs_hybrid_age": report["weighted_score_sum"] - hybrid["weighted_score_sum"],
        "ok_count": report["ok_count"],
        "max_solver_cpu_s": max_cpu,
        "max_solver_rss_mib": max_rss,
        "cpu_limit_pass": all(r["solver_cpu_total_s"] < 5.0 for r in report["records"]),
        "memory_limit_pass": all(r["solver_peak_rss_mb"] < 256.0 for r in report["records"]),
        "source_sha256": sha256(ROOT / "source" / "demand_aware.cpp"),
        "binary_sha256": sha256(ROOT / "bin" / binary_name),
        "official_report": str((RUNS / name / "summary.json").relative_to(ROOT)),
    })

base_cpu, base_rss = resource_summary(baseline)
hybrid_cpu, hybrid_rss = resource_summary(hybrid)
best = max(candidate_rows, key=lambda r: r["weighted_score"])
manifest = {
    "experiment": "online empirical-demand residual scoring for interval placement",
    "scope": "official open tests 1-15 only; frozen holdout-v2 not read or run",
    "baseline": {
        "name": "policy4 bestfit-including-tail left endpoint",
        "source": "source/baseline_policy4.cpp",
        "source_sha256": sha256(ROOT / "source" / "baseline_policy4.cpp"),
        "binary_sha256": sha256(ROOT / "bin" / "baseline_policy4"),
        "weighted_score": baseline["weighted_score_sum"],
        "ok_count": baseline["ok_count"],
        "max_solver_cpu_s": base_cpu,
        "max_solver_rss_mib": base_rss,
    },
    "comparison_reference": {
        "name": "hybrid age-newest for L<=5, policy4 otherwise",
        "solver_path": "results/pipes/improvement/age/hybrid-age-interior-5/solver",
        "weighted_score": hybrid["weighted_score_sum"],
        "ok_count": hybrid["ok_count"],
        "max_solver_cpu_s": hybrid_cpu,
        "max_solver_rss_mib": hybrid_rss,
    },
    "candidate_source": "source/demand_aware.cpp",
    "candidate_source_sha256": sha256(ROOT / "source" / "demand_aware.cpp"),
    "configurations": candidate_rows,
    "best_open_candidate": best["candidate"],
    "best_open_weighted_score": best["weighted_score"],
    "best_delta_vs_policy4": best["delta_vs_policy4"],
    "best_delta_vs_hybrid_age": best["delta_vs_hybrid_age"],
    "all_candidate_cases_ok": all(r["ok_count"] == 15 for r in candidate_rows),
    "all_candidate_resource_limits_pass": all(r["cpu_limit_pass"] and r["memory_limit_pass"] for r in candidate_rows),
    "per_case_comparison_csv": "per_case_comparison.csv",
    "reports": {name: str((RUNS / name / "summary.json").relative_to(ROOT)) for name in all_reports},
}
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"baseline_score": baseline["weighted_score_sum"],
                  "hybrid_score": hybrid["weighted_score_sum"],
                  "candidates": candidate_rows,
                  "best_open_candidate": best["candidate"],
                  "best_open_score": best["weighted_score"]}, indent=2, ensure_ascii=False))
