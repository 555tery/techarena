#!/usr/bin/env python3
"""Independent qualification runs for the frozen run-48 Pipes candidate."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "results/pipes/final/solution.cpp"
CANDIDATE = ROOT / "results/pipes/improvement/current_sensitivity/configs/run-48/solution.cpp"
PREVIOUS_SWEEP = ROOT / "results/pipes/improvement/current_sensitivity/experiment-results.json"
HARNESS = ROOT / "tools/pipes_harness.py"
INTERACTOR = ROOT / "results/pipes/final/bin/interactor"
DATASETS = {
    "open15": ROOT / "data/pipes/open",
    "holdout_v2": ROOT / "data/pipes/synthetic/final-holdout-v2",
    "development_4": ROOT / "data/pipes/synthetic/development",
}
FLAGS = [
    "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion",
    "-Wshadow", "-pedantic", "-Werror",
]
EXPECTED_BASE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
EXPECTED_CANDIDATE_SHA = "95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run(args: list[str], cwd: Path, log_stem: Path) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    log_stem.with_suffix(".stdout.txt").write_text(p.stdout)
    log_stem.with_suffix(".stderr.txt").write_text(p.stderr)
    return p


def judge_output_hashes(run_dir: Path, summary: dict) -> dict[str, str]:
    result = {}
    for record in summary["records"]:
        path = Path(record["judge_output_file"])
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            alt = run_dir / "runs" / str(record["case"]) / "judge_output.txt"
            path = alt
        result[str(record["case"])] = sha(path)
    return result


def summarize_run(dataset: str, variant: str, run_dir: Path, summary: dict) -> dict:
    records = summary["records"]
    return {
        "dataset": dataset,
        "variant": variant,
        "run_dir": str(run_dir.relative_to(ROOT)),
        "summary_sha256": sha(run_dir / "summary.json"),
        "cases": summary["case_count"],
        "ok_cases": summary["ok_count"],
        "weight_sum": summary["weight_sum"],
        "weighted_score_sum": summary["weighted_score_sum"],
        "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in records),
        "max_solver_cpu_case": max(records, key=lambda r: r["solver_cpu_total_s"])["case"],
        "max_solver_rss_mib": max(r["solver_peak_rss_mb"] for r in records),
        "cpu_limit_exceeded_cases": [r["case"] for r in records if r["solver_cpu_limit_exceeded"]],
        "memory_limit_exceeded_cases": [r["case"] for r in records if r["solver_memory_limit_exceeded"]],
        "judge_output_sha256_by_case": judge_output_hashes(run_dir, summary),
        "per_case": [{
            "case": str(r["case"]),
            "input_sha256": r["test_sha256"],
            "trench_length_m": r["trench_length_m"],
            "occupied_length_m": r["occupied_length_m"],
            "weighted_score": r["weighted_score"],
            "weight": r["weight"],
            "solver_cpu_s": r["solver_cpu_total_s"],
            "solver_peak_rss_mib": r["solver_peak_rss_mb"],
        } for r in records],
    }


def main() -> None:
    if (OUT / "qualification.json").exists():
        raise SystemExit("Existing qualification.json found; refusing to overwrite")
    if sha(BASE) != EXPECTED_BASE_SHA:
        raise SystemExit(f"Final source changed unexpectedly: {sha(BASE)}")
    if sha(CANDIDATE) != EXPECTED_CANDIDATE_SHA:
        raise SystemExit(f"Stored run-48 source changed unexpectedly: {sha(CANDIDATE)}")

    base_bytes = BASE.read_bytes()
    candidate_bytes = CANDIDATE.read_bytes()
    pattern = re.compile(rb"(kSameLengthRightRun\s*=\s*)46(;)")
    modified, count = pattern.subn(rb"\g<1>48\2", base_bytes, count=1)
    if count != 1 or modified != candidate_bytes:
        raise SystemExit("Candidate is not exactly the frozen source with only run threshold 46 -> 48")

    source_dir = OUT / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    frozen_base = source_dir / "baseline.cpp"
    frozen_candidate = source_dir / "run-48.cpp"
    shutil.copyfile(BASE, frozen_base)
    shutil.copyfile(CANDIDATE, frozen_candidate)

    binaries_dir = OUT / "binaries"
    binaries_dir.mkdir(parents=True, exist_ok=False)
    binaries = {}
    builds = {}
    for variant, source in (("baseline", frozen_base), ("run-48", frozen_candidate)):
        binary = binaries_dir / variant
        p = run(["clang++", *FLAGS, str(source), "-o", str(binary)], ROOT,
                OUT / f"build-{variant}")
        if p.returncode != 0:
            raise SystemExit(f"Strict build failed for {variant}; inspect build-{variant}.stderr.txt")
        binaries[variant] = binary
        builds[variant] = {
            "source_sha256": sha(source),
            "binary_sha256": sha(binary),
            "command": ["clang++", *FLAGS, str(source), "-o", str(binary)],
            "returncode": p.returncode,
        }

    runs = []
    for dataset, test_path in DATASETS.items():
        if not test_path.is_dir():
            raise SystemExit(f"Missing requested dataset: {test_path}")
        for variant in ("baseline", "run-48"):
            run_dir = OUT / "runs" / dataset / variant
            run_dir.mkdir(parents=True, exist_ok=False)
            cmd = [
                sys.executable, str(HARNESS), "--solver", str(binaries[variant]),
                "--name", f"run48-qualification-{variant}-{dataset}",
                "--interactor", str(INTERACTOR), "--tests", str(test_path),
                "--out", str(run_dir), "--cpu-limit", "5", "--memory-limit-mb", "256",
                "--wall-timeout", "120",
            ]
            p = run(cmd, ROOT, run_dir / "harness")
            summary_path = run_dir / "summary.json"
            if p.returncode != 0 or not summary_path.is_file():
                raise SystemExit(f"Harness failed for {variant}/{dataset}; inspect {run_dir}")
            summary = json.loads(summary_path.read_text())
            if summary["ok_count"] != summary["case_count"]:
                raise SystemExit(f"Not all cases were accepted for {variant}/{dataset}")
            runs.append(summarize_run(dataset, variant, run_dir, summary))
            print(f"{dataset}/{variant}: {summary['weighted_score_sum']:.12f} "
                  f"({summary['ok_count']}/{summary['case_count']}) "
                  f"CPUmax={runs[-1]['max_solver_cpu_s']:.6f}s "
                  f"RSSmax={runs[-1]['max_solver_rss_mib']:.3f}MiB", flush=True)

    by_key = {(r["dataset"], r["variant"]): r for r in runs}
    comparisons = {}
    for dataset in DATASETS:
        baseline = by_key[(dataset, "baseline")]
        candidate = by_key[(dataset, "run-48")]
        cases = []
        b_by_case = {r["case"]: r for r in baseline["per_case"]}
        c_by_case = {r["case"]: r for r in candidate["per_case"]}
        for case in sorted(b_by_case, key=lambda s: (int(s.split("-")[-1]) if s.split("-")[-1].isdigit() else 0, s)):
            b = b_by_case[case]
            c = c_by_case[case]
            cases.append({
                "case": case,
                "baseline_weighted_score": b["weighted_score"],
                "candidate_weighted_score": c["weighted_score"],
                "delta_weighted_score": c["weighted_score"] - b["weighted_score"],
                "baseline_trench_m": b["trench_length_m"],
                "candidate_trench_m": c["trench_length_m"],
                "delta_trench_m": c["trench_length_m"] - b["trench_length_m"],
                "baseline_output_sha256": baseline["judge_output_sha256_by_case"][case],
                "candidate_output_sha256": candidate["judge_output_sha256_by_case"][case],
                "outputs_identical": baseline["judge_output_sha256_by_case"][case] == candidate["judge_output_sha256_by_case"][case],
            })
        comparisons[dataset] = {
            "baseline_score": baseline["weighted_score_sum"],
            "candidate_score": candidate["weighted_score_sum"],
            "delta_score": candidate["weighted_score_sum"] - baseline["weighted_score_sum"],
            "baseline_cases": baseline["ok_cases"],
            "candidate_cases": candidate["ok_cases"],
            "max_candidate_cpu_s": candidate["max_solver_cpu_s"],
            "max_candidate_rss_mib": candidate["max_solver_rss_mib"],
            "score_nonregression": candidate["weighted_score_sum"] >= baseline["weighted_score_sum"] - 1e-12,
            "per_case_score_regressions": [x["case"] for x in cases if x["delta_weighted_score"] < -1e-12],
            "changed_output_cases": [x["case"] for x in cases if not x["outputs_identical"]],
            "per_case": cases,
        }

    prior = json.loads(PREVIOUS_SWEEP.read_text())
    prior_candidate = next(r for r in prior["ranking"] if r["name"] == "run-48")
    prior_screen_candidate = {
        p.parent.name: sha(p)
        for p in sorted((ROOT / "results/pipes/improvement/current_sensitivity/configs/run-48/open15/runs").glob("*/judge_output.txt"),
                        key=lambda q: q.parent.name)
    }
    fresh_open_base = by_key[("open15", "baseline")]["judge_output_sha256_by_case"]
    fresh_open_candidate = by_key[("open15", "run-48")]["judge_output_sha256_by_case"]
    open_base_previous = {
        p.parent.name: sha(p)
        for p in sorted((ROOT / "results/pipes/final/open-run-size-cohort-lanes/runs").glob("*/judge_output.txt"),
                        key=lambda q: q.parent.name)
    }
    # Source summary uses case keys 1..15, so normalize all case labels to strings.
    screen_keys = set(prior_screen_candidate)
    previous_keys = set(open_base_previous)
    old_candidate_matches_fresh = all(
        prior_screen_candidate.get(k) == fresh_open_candidate.get(k) for k in screen_keys
    ) and screen_keys == set(fresh_open_candidate)
    old_base_matches_fresh = all(
        open_base_previous.get(k) == fresh_open_base.get(k) for k in previous_keys
    ) and previous_keys == set(fresh_open_base)

    qualification = {
        "candidate_confirmed_open_repeat": (
            old_candidate_matches_fresh and old_base_matches_fresh and
            abs(comparisons["open15"]["candidate_score"] - prior_candidate["weighted_score_sum"]) < 1e-12
        ),
        "holdout_nonregression": comparisons["holdout_v2"]["score_nonregression"],
        "development_nonregression": comparisons["development_4"]["score_nonregression"],
        "all_cases_accepted": all(r["ok_cases"] == r["cases"] for r in runs),
        "within_limits": all(not r["cpu_limit_exceeded_cases"] and not r["memory_limit_exceeded_cases"] for r in runs),
    }
    qualification["qualified"] = all(qualification.values())

    if qualification["qualified"]:
        ready = OUT / "submission-ready"
        ready.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(frozen_candidate, ready / "solution.cpp")
        qualification["submission_ready_source_sha256"] = sha(ready / "solution.cpp")

    manifest = {
        "experiment": "Independent run-48 qualification; no platform upload",
        "date": "2026-10-17",
        "base_source_sha256": sha(frozen_base),
        "candidate_source_sha256": sha(frozen_candidate),
        "candidate_parameter_change": {"kSameLengthRightRun": {"from": 46, "to": 48}},
        "only_change_verified_bytewise": modified == candidate_bytes,
        "strict_compile_flags": FLAGS,
        "builds": builds,
        "harness_sha256": sha(HARNESS),
        "interactor_sha256": sha(INTERACTOR),
        "datasets_input_sha256": {
            name: {p.name: sha(p) for p in sorted(path.glob("*.in"))}
            for name, path in DATASETS.items()
        },
        "runs": runs,
        "comparisons": comparisons,
        "open_repeat_crosscheck": {
            "previous_screen_candidate_source_sha256": prior_candidate["source_sha256"],
            "previous_screen_candidate_score": prior_candidate["weighted_score_sum"],
            "fresh_candidate_outputs_match_previous_screen": old_candidate_matches_fresh,
            "previous_final_outputs_match_fresh_baseline": old_base_matches_fresh,
            "previous_base_screen_source_sha256": prior["baseline_source_sha256"],
        },
        "qualification": qualification,
        "environment": platform.platform(),
        "caveat": "Open15 is the tuning set; an independent rerun confirms reproducibility, not generalization. Holdout-v2 and development inputs are local robustness checks, not the official hidden set.",
    }
    (OUT / "qualification.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("QUALIFICATION:", json.dumps(qualification, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
