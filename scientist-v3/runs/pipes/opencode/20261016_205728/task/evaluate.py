#!/usr/bin/env python3
"""Compile and evaluate a Pipes candidate with the official local interactor."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


TASK_DIR = Path(__file__).resolve().parent
SOLVER_CPU_LIMIT = 5.0
SOLVER_MEMORY_LIMIT_MIB = 256.0
EXPECTED_CASES = 15
EXPECTED_WEIGHT_SUM = 32.1


def write_result(results_dir: Path, score: float, correct: bool, **metrics: object) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    payload = {"combined_score": float(score), **metrics}
    (results_dir / "metrics.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (results_dir / "correct.json").write_text(
        json.dumps({"correct": bool(correct)}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    args = parser.parse_args()

    program_path = Path(args.program_path).resolve()
    results_dir = Path(args.results_dir).resolve()
    compiler = shutil.which("g++")
    if compiler is None:
        write_result(results_dir, 0.0, False, error="g++ is unavailable in the evaluator image")
        return 0
    if not program_path.is_file():
        write_result(results_dir, 0.0, False, error="candidate C++ source is missing")
        return 0

    with tempfile.TemporaryDirectory(prefix="pipes-scientist-eval-") as temporary:
        temp_dir = Path(temporary)
        solver_bin = temp_dir / "pipes-solver"
        interactor_bin = temp_dir / "pipes-interactor"
        interactor_source = TASK_DIR / "vendor" / "interactor.cpp"
        include_dir = interactor_source.parent
        build_steps = [
            [compiler, "-O2", "-std=c++20", "-pipe", str(program_path), "-o", str(solver_bin)],
            [
                compiler,
                "-O2",
                "-std=c++17",
                "-pipe",
                "-I",
                str(include_dir),
                str(interactor_source),
                "-o",
                str(interactor_bin),
            ],
        ]
        for command in build_steps:
            try:
                built = subprocess.run(
                    command,
                    cwd=TASK_DIR,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                write_result(results_dir, 0.0, False, error=f"compile failed: {exc}")
                return 0
            if built.returncode != 0:
                write_result(
                    results_dir,
                    0.0,
                    False,
                    error="compile failed",
                    build_output=built.stdout[-12000:],
                )
                return 0

        harness_out = results_dir / "harness"
        harness_command = [
            sys.executable,
            str(TASK_DIR / "tools" / "pipes_harness.py"),
            "--solver",
            str(solver_bin),
            "--name",
            "candidate",
            "--interactor",
            str(interactor_bin),
            "--tests",
            str(TASK_DIR / "data" / "open"),
            "--out",
            str(harness_out),
            "--response-timeout",
            "5",
            "--wall-timeout",
            "180",
            "--cpu-limit",
            str(SOLVER_CPU_LIMIT),
            "--memory-limit-mb",
            str(SOLVER_MEMORY_LIMIT_MIB),
        ]
        try:
            evaluated = subprocess.run(
                harness_command,
                cwd=TASK_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=EXPECTED_CASES * 180 + 60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            write_result(results_dir, 0.0, False, error=f"harness failed: {exc}")
            return 0

        summary_path = harness_out / "summary.json"
        if not summary_path.is_file():
            write_result(
                results_dir,
                0.0,
                False,
                error="harness did not produce summary.json",
                harness_returncode=evaluated.returncode,
                harness_output=evaluated.stdout[-12000:],
            )
            return 0

        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            records = summary.get("records", [])
            if not isinstance(records, list):
                records = []
            score = float(summary["weighted_score_sum"])
            case_count = int(summary["case_count"])
            valid_count = int(summary["ok_count"])
            weight_sum = float(summary["weight_sum"])
            finite = math.isfinite(score)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            write_result(results_dir, 0.0, False, error=f"invalid harness report: {exc}")
            return 0

        cpu_values = [
            float(case["solver_cpu_total_s"])
            for case in records
            if case.get("solver_cpu_total_s") is not None
        ]
        rss_values = [
            float(case["solver_peak_rss_mb"])
            for case in records
            if case.get("solver_peak_rss_mb") is not None
        ]
        resource_ok = all(
            not bool(case.get("solver_cpu_limit_exceeded"))
            and not bool(case.get("solver_memory_limit_exceeded"))
            for case in records
        )
        resources_measured = len(cpu_values) == EXPECTED_CASES and len(rss_values) == EXPECTED_CASES
        resources_finite = all(math.isfinite(value) for value in cpu_values + rss_values)
        correct = (
            finite
            and case_count == EXPECTED_CASES
            and valid_count == EXPECTED_CASES
            and summary.get("is_official_open_test_set") is True
            and math.isclose(weight_sum, EXPECTED_WEIGHT_SUM, rel_tol=0.0, abs_tol=1e-9)
            and evaluated.returncode == 0
            and resources_measured
            and resources_finite
            and resource_ok
        )
        write_result(
            results_dir,
            score if finite else 0.0,
            correct,
            open_test_score=score if finite else 0.0,
            open_test_weight_sum=weight_sum,
            valid_case_count=valid_count,
            case_count=case_count,
            max_solver_cpu_seconds=max(cpu_values) if cpu_values else None,
            max_solver_rss_mib=max(rss_values) if rss_values else None,
            solver_cpu_limit_seconds=SOLVER_CPU_LIMIT,
            solver_memory_limit_mib=SOLVER_MEMORY_LIMIT_MIB,
            harness_returncode=evaluated.returncode,
        )
        print(evaluated.stdout[-12000:])
        print(f"combined_score={score:.12g}; correct={correct}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
