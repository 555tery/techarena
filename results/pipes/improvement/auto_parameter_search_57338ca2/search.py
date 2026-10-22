#!/usr/bin/env python3
"""Reproducible bounded random-Latin-hypercube search for Pipes constants."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "results/pipes/final/solution.cpp"
EXPECTED_BASE_SHA = "57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f"
HARNESS = ROOT / "tools/pipes_harness.py"
INTERACTOR = ROOT / "tools/interactor"
OPEN = ROOT / "data/pipes/open"
FLAGS = [
    "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion",
    "-Wshadow", "-pedantic", "-Werror",
]
SEED = 20261016
SEARCH_COUNT = 20  # includes unchanged baseline as config 00
DOMAINS = {
    "unfit_penalty": ("kUnfitPenaltyScale", [20, 40, 60, 80, 120, 180]),
    "same_length_run": ("kSameLengthRightRun", [24, 32, 40, 46, 56, 72]),
    "right_edge_cap": ("kRightEdgeMaxPipeLength", [0, 2, 4, 6, 8, 12]),
    "mc_min_saving": ("kMcMinimumMeanSavingM", [0, 1, 2, 4, 8, 16]),
    "mc_decision_budget": ("kMcDecisionBudget", [0, 8, 16, 24, 32, 48, 64]),
}
BASE_CONFIG = {
    "unfit_penalty": 60,
    "same_length_run": 46,
    "right_edge_cap": 4,
    "mc_min_saving": 1,
    "mc_decision_budget": 32,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latin_hypercube_configs() -> tuple[list[dict[str, int]], int]:
    """Seeded randomized LHS columns; baseline is a separate control row."""
    n = SEARCH_COUNT - 1
    for attempt in range(100):
        rng = random.Random(SEED + attempt)
        columns: dict[str, list[int]] = {}
        for key, (_, levels) in DOMAINS.items():
            # Jitter each of n equally spaced strata and map it to the finite
            # discrete level set, then permute independently per dimension.
            vals = [levels[min(len(levels) - 1, int((i + rng.random()) * len(levels) / n))]
                    for i in range(n)]
            rng.shuffle(vals)
            columns[key] = vals
        configs = [{key: columns[key][i] for key in DOMAINS} for i in range(n)]
        signatures = [tuple(cfg[k] for k in DOMAINS) for cfg in configs]
        base_sig = tuple(BASE_CONFIG[k] for k in DOMAINS)
        if len(set(signatures)) == n and base_sig not in signatures:
            return [BASE_CONFIG.copy(), *configs], attempt
    raise RuntimeError("Could not sample 19 distinct non-baseline configurations")


def create_source(source: str, cfg: dict[str, int]) -> str:
    result = source
    for key, (constant, _) in DOMAINS.items():
        pattern = rf"(^[^\n]*\b{constant} = )\d+(;[^\n]*)$"
        result, count = re.subn(pattern, rf"\g<1>{cfg[key]}\g<2>", result, count=1, flags=re.M)
        if count != 1:
            raise RuntimeError(f"Expected one declaration for {constant}; got {count}")
    return result


def config_name(index: int, cfg: dict[str, int]) -> str:
    return (
        f"{index:02d}-p{cfg['unfit_penalty']}-run{cfg['same_length_run']}"
        f"-edge{cfg['right_edge_cap']}-save{cfg['mc_min_saving']}"
        f"-budget{cfg['mc_decision_budget']}"
    )


def main() -> None:
    base_hash = sha256(BASE)
    if base_hash != EXPECTED_BASE_SHA:
        raise SystemExit(f"Unexpected base source SHA: {base_hash}")
    OUT.mkdir(parents=True, exist_ok=True)
    configs, sampling_attempt = latin_hypercube_configs()
    base_text = BASE.read_text()
    (OUT / "base-source.cpp").write_text(base_text)
    if sha256(OUT / "base-source.cpp") != EXPECTED_BASE_SHA:
        raise SystemExit("Base source copy hash mismatch")

    records = []
    for index, cfg in enumerate(configs):
        name = config_name(index, cfg)
        d = OUT / "configs" / name
        d.mkdir(parents=True, exist_ok=True)
        source = d / "solution.cpp"
        source.write_text(create_source(base_text, cfg))
        binary = d / "solver"
        build_cmd = ["clang++", *FLAGS, str(source), "-o", str(binary)]
        build = subprocess.run(build_cmd, cwd=ROOT, text=True, capture_output=True)
        (d / "build.stdout").write_text(build.stdout)
        (d / "build.stderr").write_text(build.stderr)
        if build.returncode != 0:
            raise SystemExit(f"Compile failed for {name}; see {d / 'build.stderr'}")
        run_dir = d / "open"
        run_cmd = [
            "python3", str(HARNESS), "--solver", str(binary), "--name", name,
            "--interactor", str(INTERACTOR), "--tests", str(OPEN),
            "--out", str(run_dir), "--cpu-limit", "5", "--memory-limit-mb", "256",
        ]
        run = subprocess.run(run_cmd, cwd=ROOT, text=True, capture_output=True)
        (d / "harness.stdout").write_text(run.stdout)
        (d / "harness.stderr").write_text(run.stderr)
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            raise SystemExit(f"Harness did not produce summary for {name}; rc={run.returncode}")
        summary = json.loads(summary_path.read_text())
        if run.returncode != 0 or summary["case_count"] != 15 or summary["ok_count"] != 15:
            raise SystemExit(f"Open run failed for {name}; see {d}")
        records.append({
            "index": index,
            "name": name,
            "parameters": cfg,
            "source_sha256": sha256(source),
            "binary_sha256": sha256(binary),
            "open_summary_sha256": sha256(summary_path),
            "weighted_score_sum": summary["weighted_score_sum"],
            "case_count": summary["case_count"],
            "ok_count": summary["ok_count"],
            "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in summary["records"]),
            "max_solver_cpu_case": max(summary["records"], key=lambda r: r["solver_cpu_total_s"])["case"],
            "max_solver_peak_rss_mib": max(r["solver_peak_rss_mb"] for r in summary["records"]),
            "max_solver_rss_case": max(summary["records"], key=lambda r: r["solver_peak_rss_mb"])["case"],
            "harness_returncode": run.returncode,
        })
        print(f"{name}: open15={summary['weighted_score_sum']:.12f} "
              f"maxCPU={records[-1]['max_solver_cpu_s']:.6f}s "
              f"maxRSS={records[-1]['max_solver_peak_rss_mib']:.3f}MiB", flush=True)

    records.sort(key=lambda r: (-r["weighted_score_sum"], r["index"]))
    (OUT / "search-results.json").write_text(json.dumps({
        "baseline_source_sha256": base_hash,
        "method": "seeded randomized Latin hypercube over discrete levels",
        "seed": SEED,
        "attempt": sampling_attempt,
        "config_count_including_baseline": len(configs),
        "domains": {k: {"constant": v[0], "levels": v[1]} for k, v in DOMAINS.items()},
        "baseline_parameters": BASE_CONFIG,
        "ranking": records,
    }, indent=2) + "\n")
    with (OUT / "open-ranking.csv").open("w", newline="") as f:
        cols = ["rank", "index", "name", "weighted_score_sum", *DOMAINS.keys(),
                "source_sha256", "binary_sha256", "open_summary_sha256",
                "max_solver_cpu_s", "max_solver_cpu_case", "max_solver_peak_rss_mib",
                "max_solver_rss_case"]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for rank, row in enumerate(records, 1):
            flat = {"rank": rank, **row, **row["parameters"]}
            writer.writerow({k: flat.get(k, "") for k in cols})
    print(f"RANKING: {OUT / 'open-ranking.csv'}", flush=True)


if __name__ == "__main__":
    main()
