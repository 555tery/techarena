#!/usr/bin/env python3
"""Compile the selector policies in src/pipes.cpp and compare them locally."""

import argparse
import csv
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path


POLICY_NAMES = {
    0: "bestfit-preserve-tail",
    1: "firstfit-coordinate",
    2: "worstfit-interior",
    3: "largest-coordinate-interior",
    4: "bestfit-including-tail",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="src/pipes.cpp")
    parser.add_argument("--tests", default="data/pipes/open")
    parser.add_argument("--interactor", default="tools/interactor")
    parser.add_argument("--out", default="results/pipes/policy-comparison")
    parser.add_argument("--cxx", default="clang++")
    parser.add_argument("--flags", default="-O2 -std=c++17 -pipe")
    parser.add_argument("--policies", default="0,1,2,3,4")
    parser.add_argument("--response-timeout", type=float, default=5.0)
    parser.add_argument("--wall-timeout", type=float, default=120.0)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    tests = Path(args.tests).resolve()
    interactor = Path(args.interactor).resolve()
    out = Path(args.out).resolve()
    build = out / "binaries"
    build.mkdir(parents=True, exist_ok=True)
    policies = [int(x.strip()) for x in args.policies.split(",") if x.strip()]
    if not policies or any(policy not in POLICY_NAMES for policy in policies):
        parser.error("--policies must be a comma-separated subset of 0,1,2,3,4")

    compiler_version = subprocess.run(shlex.split(args.cxx) + ["--version"], check=True,
                                      text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.splitlines()[0]
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    summaries = []
    for policy in policies:
        name = POLICY_NAMES[policy]
        binary = build / ("pipes-policy-%d" % policy)
        compile_cmd = shlex.split(args.cxx) + shlex.split(args.flags) + ["-DPIPE_POLICY=%d" % policy,
                                                                        str(source), "-o", str(binary)]
        print("compile %s: %s" % (name, " ".join(shlex.quote(x) for x in compile_cmd)))
        subprocess.run(compile_cmd, check=True)
        report_dir = out / name
        run_cmd = [
            sys.executable,
            str(Path(__file__).resolve().with_name("pipes_harness.py")),
            "--solver", str(binary),
            "--name", name,
            "--interactor", str(interactor),
            "--tests", str(tests),
            "--out", str(report_dir),
            "--response-timeout", str(args.response_timeout),
            "--wall-timeout", str(args.wall_timeout),
        ]
        result = subprocess.run(run_cmd, check=False)
        summary_path = report_dir / "summary.json"
        if not summary_path.exists():
            raise RuntimeError("harness did not write " + str(summary_path))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        records = summary["records"]
        summaries.append({
            "policy": policy,
            "strategy": name,
            "compile_command": compile_cmd,
            "compiler_version": compiler_version,
            "source_sha256": source_sha256,
            "solver_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "status": "ok" if result.returncode == 0 else "contains-failures-or-limit-exceedance",
            "weighted_score_sum": summary["weighted_score_sum"],
            "weight_sum": summary["weight_sum"],
            "normalized_weighted_score": (summary["weighted_score_sum"] / summary["weight_sum"]
                                          if summary["weight_sum"] else None),
            "ok_count": summary["ok_count"],
            "case_count": summary["case_count"],
            "sum_solver_cpu_s": sum((r["solver_cpu_total_s"] or 0.0) for r in records),
            "max_solver_cpu_s": max((r["solver_cpu_total_s"] or 0.0) for r in records),
            "max_solver_peak_rss_mb": max((r["solver_peak_rss_mb"] or 0.0) for r in records),
            "sum_wall_orchestration_s": sum(r["wall_orchestration_s"] for r in records),
            "mean_trench_length_m": sum(r["trench_length_m"] or 0 for r in records) / len(records),
            "mean_live_volume_lower_bound_m": sum(r["minimum_trench_lower_bound_m"] for r in records) / len(records),
            "mean_trench_to_lower_bound_ratio": sum(
                (r["trench_length_m"] / r["minimum_trench_lower_bound_m"])
                for r in records if r["minimum_trench_lower_bound_m"]
            ) / max(1, sum(r["minimum_trench_lower_bound_m"] > 0 for r in records)),
            "mean_kpi_upper_bound": sum(r["kpi_upper_bound_from_live_volume"] for r in records) / len(records),
            "mean_lower_bound_to_actual_trench_ratio": sum(
                r["fraction_of_bound"] for r in records if r["fraction_of_bound"] is not None
            ) / max(1, sum(r["fraction_of_bound"] is not None for r in records)),
            "min_lower_bound_to_actual_trench_ratio": min(
                (r["lower_bound_to_actual_trench_ratio"] for r in records
                 if r["lower_bound_to_actual_trench_ratio"] is not None),
                default=None,
            ),
            "worst_relative_regret_vs_bound": max(
                (1.0 - r["fraction_of_bound"] for r in records if r["fraction_of_bound"] is not None),
                default=None,
            ),
            "per_test_kpis": {r["case"]: r["kpi"] for r in records},
            "report": str(summary_path),
        })

    best_kpi_by_case = {}
    for row in summaries:
        for case, kpi in row["per_test_kpis"].items():
            best_kpi_by_case[case] = max(best_kpi_by_case.get(case, 0.0), kpi)
    for row in summaries:
        weighted_gaps = []
        case_records = json.loads(Path(row["report"]).read_text(encoding="utf-8"))["records"]
        for rec in case_records:
            best_kpi = best_kpi_by_case[rec["case"]]
            loss = (best_kpi - rec["kpi"]) * rec["official_weight"]
            if loss > 1e-12:
                weighted_gaps.append({
                    "case": rec["case"],
                    "score_gap_vs_best_policy": loss,
                    "policy_kpi": rec["kpi"],
                    "best_kpi": best_kpi,
                    "trench_length_m": rec["trench_length_m"],
                    "live_volume_lower_bound_m": rec["minimum_trench_lower_bound_m"],
                })
        row["largest_weighted_gaps_vs_best_policy"] = sorted(
            weighted_gaps, key=lambda item: item["score_gap_vs_best_policy"], reverse=True
        )[:5]

    out.mkdir(parents=True, exist_ok=True)
    metadata = {
        "source": str(source),
        "source_sha256": source_sha256,
        "interactor": str(interactor),
        "interactor_sha256": hashlib.sha256(interactor.read_bytes()).hexdigest(),
        "compiler_version": compiler_version,
        "test_set": str(tests),
        "policies": summaries,
    }
    (out / "comparison.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    with (out / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    print("\nPolicy comparison:")
    for row in summaries:
        print("%-30s weighted=%9.5f/%-8.5f (%6.2f%%) valid=%d/%d CPU-sum=%.4fs wall-sum=%.3fs RSS-max=%.3fMiB"
              % (row["strategy"], row["weighted_score_sum"], row["weight_sum"],
                 100.0 * row["normalized_weighted_score"], row["ok_count"], row["case_count"],
                 row["sum_solver_cpu_s"], row["sum_wall_orchestration_s"], row["max_solver_peak_rss_mb"]))
    print("JSON: %s" % (out / "comparison.json"))
    print("CSV:  %s" % (out / "comparison.csv"))
    return 0 if all(row["status"] == "ok" for row in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
