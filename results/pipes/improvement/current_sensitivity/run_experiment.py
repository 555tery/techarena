#!/usr/bin/env python3
"""Bounded sensitivity sweep on the current Pipes final source."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "results/pipes/final/solution.cpp"
EXPECTED_BASE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
HARNESS = ROOT / "tools/pipes_harness.py"
INTERACTOR = ROOT / "tools/interactor"
OPEN = ROOT / "data/pipes/open"
FLAGS = [
    "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion",
    "-Wshadow", "-pedantic", "-Werror",
]

DOMAINS = {
    "same_length_run": "kSameLengthRightRun",
    "unfit_penalty": "kUnfitPenaltyScale",
    "mc_decision_budget": "kMcDecisionBudget",
    "mc_min_saving": "kMcMinimumMeanSavingM",
}
BASE_CONFIG = {
    "same_length_run": 46,
    "unfit_penalty": 60,
    "mc_decision_budget": 32,
    "mc_min_saving": 1,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def configs() -> list[tuple[str, dict[str, int], str]]:
    """At most 20 full-open configurations, declared before results."""
    out: list[tuple[str, dict[str, int], str]] = []

    def add(name: str, changes: dict[str, int], note: str) -> None:
        cfg = BASE_CONFIG | changes
        out.append((name, cfg, note))

    add("00-baseline", {}, "current final source, unchanged control")
    for run in (32, 40, 42, 44, 48, 52, 56):
        add(f"run-{run}", {"same_length_run": run}, "one-factor threshold neighborhood")
    for penalty in (40, 80):
        add(f"penalty-{penalty}", {"unfit_penalty": penalty}, "one-factor score-gap penalty")
    for budget in (16, 48):
        add(f"mc-budget-{budget}", {"mc_decision_budget": budget}, "one-factor corrected-MC budget")
    for saving in (0, 4):
        add(f"mc-saving-{saving}", {"mc_min_saving": saving}, "one-factor corrected-MC threshold")
    for run in (40, 56):
        for budget in (16, 48):
            add(f"run-{run}-mc-budget-{budget}", {
                "same_length_run": run,
                "mc_decision_budget": budget,
            }, "two-factor run-threshold x corrected-MC budget")

    if len(out) != 18 or len({name for name, _, _ in out}) != len(out):
        raise RuntimeError(f"Unexpected configuration count or duplicate names: {len(out)}")
    return out


def create_source(base_text: str, cfg: dict[str, int]) -> str:
    result = base_text
    for key, constant in DOMAINS.items():
        pattern = rf"(^[^\n]*\b{constant} = )\d+(;[^\n]*)$"
        result, count = re.subn(
            pattern, rf"\g<1>{cfg[key]}\g<2>", result, count=1, flags=re.M
        )
        if count != 1:
            raise RuntimeError(f"Expected one declaration for {constant}; got {count}")
    return result


def run_checked(args: list[str], cwd: Path, out_prefix: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    out_prefix.with_suffix(".stdout.txt").write_text(proc.stdout)
    out_prefix.with_suffix(".stderr.txt").write_text(proc.stderr)
    return proc


def output_hashes(run_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted((run_dir / "runs").glob("*/judge_output.txt"),
                       key=lambda p: int(p.parent.name)):
        out[path.parent.name] = sha256(path)
    return out


def main() -> None:
    base_hash = sha256(BASE)
    if base_hash != EXPECTED_BASE_SHA:
        raise SystemExit(f"Unexpected base source SHA: {base_hash}")
    if (OUT / "experiment-results.json").exists():
        raise SystemExit("Existing experiment-results.json found; refusing to overwrite a run")

    all_configs = configs()
    base_text = BASE.read_text()
    (OUT / "base-source.cpp").write_text(base_text)
    if sha256(OUT / "base-source.cpp") != EXPECTED_BASE_SHA:
        raise SystemExit("Frozen base source copy hash mismatch")

    input_hashes = {
        path.stem: sha256(path)
        for path in sorted(OPEN.glob("*.in"), key=lambda p: int(p.stem))
    }
    if len(input_hashes) != 15:
        raise SystemExit(f"Expected 15 open inputs; found {len(input_hashes)}")

    records = []
    for index, (name, cfg, note) in enumerate(all_configs):
        run_root = OUT / "configs" / name
        run_root.mkdir(parents=True, exist_ok=False)
        source = run_root / "solution.cpp"
        source.write_text(create_source(base_text, cfg))
        binary = run_root / "solver"

        build = run_checked(
            ["clang++", *FLAGS, str(source), "-o", str(binary)],
            ROOT, run_root / "build",
        )
        if build.returncode != 0:
            raise SystemExit(f"Compile failed for {name}; see {run_root / 'build.stderr.txt'}")

        run_dir = run_root / "open15"
        harness_cmd = [
            sys.executable, str(HARNESS), "--solver", str(binary), "--name", name,
            "--interactor", str(INTERACTOR), "--tests", str(OPEN), "--out", str(run_dir),
            "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "120",
        ]
        run = run_checked(harness_cmd, ROOT, run_root / "harness")
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            raise SystemExit(f"Harness produced no summary for {name}; rc={run.returncode}")
        summary = json.loads(summary_path.read_text())
        if run.returncode != 0 or summary["case_count"] != 15 or summary["ok_count"] != 15:
            raise SystemExit(f"Open15 failed for {name}; see {run_root}")

        rows = summary["records"]
        records.append({
            "index": index,
            "name": name,
            "note": note,
            "parameters": cfg,
            "source_sha256": sha256(source),
            "binary_sha256": sha256(binary),
            "open_summary_sha256": sha256(summary_path),
            "judge_output_sha256_by_case": output_hashes(run_dir),
            "weighted_score_sum": summary["weighted_score_sum"],
            "case_count": summary["case_count"],
            "ok_count": summary["ok_count"],
            "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in rows),
            "max_solver_cpu_case": max(rows, key=lambda r: r["solver_cpu_total_s"])["case"],
            "max_solver_peak_rss_mib": max(r["solver_peak_rss_mb"] for r in rows),
            "per_case": [{
                "case": int(r["case"]),
                "input_sha256": r["test_sha256"],
                "output_sha256": sha256(run_dir / "runs" / str(r["case"]) / "judge_output.txt"),
                "trench_length_m": r["trench_length_m"],
                "occupied_length_m": r["occupied_length_m"],
                "weighted_score": r["weighted_score"],
                "official_weight": r["weight"],
                "solver_cpu_s": r["solver_cpu_total_s"],
                "solver_peak_rss_mib": r["solver_peak_rss_mb"],
            } for r in rows],
            "harness_returncode": run.returncode,
        })
        print(f"{name}: open15={summary['weighted_score_sum']:.12f} "
              f"maxCPU={records[-1]['max_solver_cpu_s']:.6f}s "
              f"maxRSS={records[-1]['max_solver_peak_rss_mib']:.3f}MiB", flush=True)

    baseline = next(r for r in records if r["name"] == "00-baseline")
    previous = json.loads((ROOT / "results/pipes/final/open-run-size-cohort-lanes/summary.json").read_text())
    previous_outputs = output_hashes(ROOT / "results/pipes/final/open-run-size-cohort-lanes")
    baseline_outputs_match_previous = baseline["judge_output_sha256_by_case"] == previous_outputs
    baseline_score_matches_previous = abs(
        baseline["weighted_score_sum"] - previous["weighted_score_sum"]
    ) < 1e-12
    records.sort(key=lambda r: (-r["weighted_score_sum"], r["index"]))

    tool_info = {}
    for name, cmd in (("clang", ["clang++", "--version"]), ("python", [sys.executable, "--version"])):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        tool_info[name] = (proc.stdout + proc.stderr).splitlines()[0]

    results = {
        "baseline_source_sha256": base_hash,
        "method": "predeclared 18-config bounded full official Open15 sensitivity sweep",
        "causality": "Only observed stream history and current command are used; no test ID, future command, file, score, clock, or environment access was introduced.",
        "parameters_varied": DOMAINS,
        "fixed_parameters": {
            "kRightEdgeMaxPipeLength": 4,
            "kHistoryWindow": 2048,
            "kMcHistory": 256,
            "kMcDepth": 4,
            "kMcTrials": 12,
            "kMcMaxGaps": 64,
            "kMcMaxActivePipes": 4096,
        },
        "configuration_count": len(all_configs),
        "declared_configurations": [{"name": n, "parameters": c, "note": note}
                                    for n, c, note in all_configs],
        "open_input_sha256_by_case": input_hashes,
        "interactor_sha256": sha256(INTERACTOR),
        "harness_sha256": sha256(HARNESS),
        "compile_flags": FLAGS,
        "official_limits": {"cpu_seconds": 5, "memory_mib": 256},
        "host": platform.platform(),
        "tool_versions": tool_info,
        "baseline_cross_check_previous_final": {
            "previous_summary_sha256": sha256(ROOT / "results/pipes/final/open-run-size-cohort-lanes/summary.json"),
            "score_matches_within_1e-12": baseline_score_matches_previous,
            "judge_outputs_byte_identical_by_hash": baseline_outputs_match_previous,
            "previous_open_score": previous["weighted_score_sum"],
            "fresh_baseline_open_score": baseline["weighted_score_sum"],
        },
        "ranking": records,
    }
    (OUT / "experiment-results.json").write_text(json.dumps(results, indent=2) + "\n")

    with (OUT / "ranking.csv").open("w", newline="") as f:
        cols = ["rank", "index", "name", "weighted_score_sum", "delta_vs_baseline",
                *DOMAINS.keys(), "source_sha256", "binary_sha256", "max_solver_cpu_s",
                "max_solver_cpu_case", "max_solver_peak_rss_mib"]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for rank, row in enumerate(records, 1):
            flat = {"rank": rank, **row, **row["parameters"],
                    "delta_vs_baseline": row["weighted_score_sum"] - baseline["weighted_score_sum"]}
            writer.writerow({col: flat.get(col, "") for col in cols})

    print(f"RESULTS: {OUT / 'experiment-results.json'}", flush=True)


if __name__ == "__main__":
    main()
