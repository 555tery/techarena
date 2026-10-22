#!/usr/bin/env python3
"""Run several existing solver commands on identical Pipes input files."""

import argparse
import csv
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path


def parse_solver(spec):
    if "=" not in spec:
        raise ValueError("each --solver must be LABEL=COMMAND")
    label, command = spec.split("=", 1)
    argv = shlex.split(command)
    if not label or not argv:
        raise ValueError("solver label and command are required")
    first = Path(argv[0])
    if first.exists():
        argv[0] = str(first.resolve())
    return label, command, argv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", action="append", required=True,
                        help="repeat as LABEL=COMMAND for each candidate and baseline")
    parser.add_argument("--tests", required=True, help="one .in file or directory containing fixed tests")
    parser.add_argument("--out", required=True, help="report directory")
    parser.add_argument("--interactor", default="tools/interactor")
    parser.add_argument("--response-timeout", type=float, default=5.0)
    parser.add_argument("--wall-timeout", type=float, default=120.0)
    parser.add_argument("--baseline", help="label used to calculate per-case relative deltas")
    args = parser.parse_args()
    try:
        solvers = [parse_solver(spec) for spec in args.solver]
    except ValueError as exc:
        parser.error(str(exc))
    if len({label for label, _, _ in solvers}) != len(solvers):
        parser.error("solver labels must be unique")
    baseline = args.baseline or solvers[0][0]
    if baseline not in {label for label, _, _ in solvers}:
        parser.error("--baseline must name one of the supplied solver labels")

    tests = Path(args.tests).resolve()
    interactor = Path(args.interactor).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    harness = Path(__file__).resolve().with_name("pipes_harness.py")
    comparison = []
    records_by_label = {}
    for label, command, argv in solvers:
        report_dir = out / label
        run_cmd = [
            sys.executable, str(harness), "--solver", command,
            "--name", label, "--interactor", str(interactor),
            "--tests", str(tests), "--out", str(report_dir),
            "--response-timeout", str(args.response_timeout),
            "--wall-timeout", str(args.wall_timeout),
        ]
        result = subprocess.run(run_cmd, check=False)
        summary_path = report_dir / "summary.json"
        if not summary_path.exists():
            raise RuntimeError("harness did not write " + str(summary_path))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        records = summary["records"]
        records_by_label[label] = {r["case"]: r for r in records}
        binary_sha = None
        if len(argv) == 1 and Path(argv[0]).is_file():
            binary_sha = hashlib.sha256(Path(argv[0]).read_bytes()).hexdigest()
        comparison.append({
            "label": label,
            "command": command,
            "binary_sha256": binary_sha,
            "run_status": "ok" if result.returncode == 0 else "contains-failures-or-limit-exceedance",
            "weighted_score_sum": summary["weighted_score_sum"],
            "weight_sum": summary["weight_sum"],
            "ok_count": summary["ok_count"],
            "case_count": summary["case_count"],
            "mean_kpi_upper_bound": summary["mean_kpi_upper_bound_from_live_volume"],
            "mean_lower_bound_to_actual_trench_ratio": summary["mean_lower_bound_to_actual_trench_ratio"],
            "min_lower_bound_to_actual_trench_ratio": summary["min_lower_bound_to_actual_trench_ratio"],
            "worst_relative_regret_vs_bound": summary["worst_relative_regret_vs_bound"],
            "sum_solver_cpu_s": sum((r["solver_cpu_total_s"] or 0.0) for r in records),
            "max_solver_cpu_s": max((r["solver_cpu_total_s"] or 0.0) for r in records),
            "max_solver_peak_rss_mb": max((r["solver_peak_rss_mb"] or 0.0) for r in records),
            "sum_wall_orchestration_s": sum(r["wall_orchestration_s"] for r in records),
            "report": str(summary_path),
        })

    baseline_records = records_by_label[baseline]
    for row in comparison:
        candidate_records = records_by_label[row["label"]]
        relative = []
        for case, current in candidate_records.items():
            reference = baseline_records.get(case)
            if reference is None:
                continue
            candidate_kpi = current["kpi"]
            baseline_kpi = reference["kpi"]
            if baseline_kpi > 0:
                relative.append({
                    "case": case,
                    "candidate_over_baseline_minus_one": candidate_kpi / baseline_kpi - 1.0,
                    "baseline_over_candidate_minus_one": baseline_kpi / candidate_kpi - 1.0 if candidate_kpi > 0 else None,
                    "candidate_kpi": candidate_kpi,
                    "baseline_kpi": baseline_kpi,
                    "candidate_actual_trench_m": current["trench_length_m"],
                    "baseline_actual_trench_m": reference["trench_length_m"],
                    "candidate_trench_over_baseline_minus_one": (
                        current["trench_length_m"] / reference["trench_length_m"] - 1.0
                        if reference["trench_length_m"] else None
                    ),
                    "baseline_trench_over_candidate_minus_one": (
                        reference["trench_length_m"] / current["trench_length_m"] - 1.0
                        if current["trench_length_m"] else None
                    ),
                    "candidate_lower_bound_to_actual_trench_ratio": current["lower_bound_to_actual_trench_ratio"],
                    "baseline_lower_bound_to_actual_trench_ratio": reference["lower_bound_to_actual_trench_ratio"],
                })
        row["baseline_label"] = baseline
        row["worst_candidate_over_baseline_minus_one"] = max(
            (r["candidate_over_baseline_minus_one"] for r in relative), default=None
        )
        row["worst_baseline_over_candidate_minus_one"] = max(
            (r["baseline_over_candidate_minus_one"] for r in relative
             if r["baseline_over_candidate_minus_one"] is not None), default=None
        )
        row["worst_candidate_trench_over_baseline_minus_one"] = max(
            (r["candidate_trench_over_baseline_minus_one"] for r in relative
             if r["candidate_trench_over_baseline_minus_one"] is not None), default=None
        )
        row["worst_baseline_trench_over_candidate_minus_one"] = max(
            (r["baseline_trench_over_candidate_minus_one"] for r in relative
             if r["baseline_trench_over_candidate_minus_one"] is not None), default=None
        )
        row["per_case_relative_comparison"] = relative

    metadata = {
        "tests": str(tests),
        "tests_sha256": {
            str(path.relative_to(tests)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(tests.glob("*.in"))
        } if tests.is_dir() else {tests.name: hashlib.sha256(tests.read_bytes()).hexdigest()},
        "interactor": str(interactor),
        "interactor_sha256": hashlib.sha256(interactor.read_bytes()).hexdigest(),
        "baseline_label": baseline,
        "measurement_note": "solver CPU/RSS are child-only; wall orchestration includes Python harness and interactor",
        "solvers": comparison,
    }
    (out / "comparison.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    scalar_fields = [key for key, value in comparison[0].items() if not isinstance(value, (dict, list))]
    with (out / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=scalar_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(comparison)
    with (out / "per-case-comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "candidate_label", "baseline_label", "case",
            "candidate_over_baseline_minus_one", "baseline_over_candidate_minus_one",
            "candidate_kpi", "baseline_kpi",
            "candidate_actual_trench_m", "baseline_actual_trench_m",
            "candidate_trench_over_baseline_minus_one",
            "baseline_trench_over_candidate_minus_one",
            "candidate_lower_bound_to_actual_trench_ratio",
            "baseline_lower_bound_to_actual_trench_ratio",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in comparison:
            for item in row["per_case_relative_comparison"]:
                writer.writerow({"candidate_label": row["label"], **item})
    for row in comparison:
        print("%s: %d/%d valid; score %.6f/%g; mean L/T %.6f, min L/T %.6f; worst relative regret vs bound %.6f; CPU sum/max %.4f/%.4fs; max RSS %.3f MiB"
              % (row["label"], row["ok_count"], row["case_count"], row["weighted_score_sum"], row["weight_sum"],
                 row["mean_lower_bound_to_actual_trench_ratio"] or 0.0,
                 row["min_lower_bound_to_actual_trench_ratio"] or 0.0,
                 row["worst_relative_regret_vs_bound"] or 0.0,
                 row["sum_solver_cpu_s"], row["max_solver_cpu_s"], row["max_solver_peak_rss_mb"]))
    print("comparison report: %s" % (out / "comparison.json"))
    return 0 if all(row["run_status"] == "ok" for row in comparison) else 1


if __name__ == "__main__":
    raise SystemExit(main())
