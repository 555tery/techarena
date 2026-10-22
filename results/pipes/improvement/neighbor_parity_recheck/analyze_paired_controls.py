#!/usr/bin/env python3
"""Recompute paired neighbor-parity/lifetime diagnostics from frozen traces.

This is retrospective analysis only. It does not alter a solver or construct
future-aware placement decisions. Case-cluster bootstrap treats each stream as
the resampling unit because placements within a stream are dependent.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import random
import resource
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
AUDIT = ROOT / "results/pipes/improvement/neighborhood_signal_audit/analyze_temporal_holdout.py"
DATA = ROOT / "data/pipes/synthetic/final-holdout-v2"
OUTPUTS = ROOT / "results/pipes/final/holdout-run-size-cohort-lanes/runs"
BASELINE = ROOT / "results/pipes/final/solution.cpp"
CANONICAL = ROOT / "src/pipes.cpp"
FINAL_MANIFEST = ROOT / "results/pipes/final/manifest.json"
DRAWS = 200_000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clustered_bootstrap_ci(values: list[float], seed: int) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = [statistics.mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(DRAWS)]
    means.sort()
    return [means[int(0.025 * DRAWS)], means[int(0.975 * DRAWS) - 1]]


def grouped_values(rows: list[dict], field: str, predicate=lambda row: True) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        value = row.get(field)
        if value is not None and predicate(row):
            grouped.setdefault(row["case"], []).append(float(value))
    return grouped


def summarize_case_means(grouped: dict[str, list[float]], *, seed: int, min_n: int = 20) -> dict:
    eligible = {case: vals for case, vals in grouped.items() if len(vals) >= min_n}
    case_means = {case: statistics.mean(vals) for case, vals in eligible.items()}
    means = list(case_means.values())
    return {
        "cases": len(eligible),
        "paired_events": sum(len(vals) for vals in eligible.values()),
        "case_means": case_means,
        "equal_case_mean": statistics.mean(means) if means else None,
        "cluster_bootstrap_95pct_ci": clustered_bootstrap_ci(means, seed) if means else None,
    }


def main() -> None:
    started = time.monotonic()
    usage_start = resource.getrusage(resource.RUSAGE_SELF)
    spec = importlib.util.spec_from_file_location("temporal_holdout_audit", AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load audit module: {AUDIT}")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    all_rows: list[dict] = []
    input_hashes: dict[str, str] = {}
    answer_hashes: dict[str, str] = {}
    case_sizes: dict[str, dict] = {}
    for case_path in sorted(DATA.glob("*.in")):
        answer_path = OUTPUTS / case_path.stem / "judge_output.txt"
        input_hashes[case_path.name] = sha(case_path)
        answer_hashes[f"{case_path.stem}/judge_output.txt"] = sha(answer_path)
        summary, rows = audit.replay(case_path, answer_path)
        all_rows.extend(rows)
        case_sizes[case_path.stem] = {
            "operations": summary["operations"],
            "validation_pairs": summary["eligible_validation_pairs"],
        }

    parity_rows = [r for r in all_rows if r["same_parity_error"] is not None and r["opposite_parity_error"] is not None]
    for row in parity_rows:
        row["same_minus_opposite"] = row["same_parity_error"] - row["opposite_parity_error"]

    parity_groups = grouped_values(parity_rows, "same_minus_opposite")
    parity = summarize_case_means(parity_groups, seed=2026101701)
    parity_events = len(parity_rows)
    parity_wins = sum(r["same_minus_opposite"] < 0 for r in parity_rows)
    parity_ties = sum(r["same_minus_opposite"] == 0 for r in parity_rows)
    parity["pooled"] = {
        "events": parity_events,
        "same_parity_lower_mismatch": parity_wins,
        "ties": parity_ties,
        "same_parity_win_rate_excluding_ties": parity_wins / max(1, parity_events - parity_ties),
        "mean_same_minus_opposite_error_commands": statistics.mean(r["same_minus_opposite"] for r in parity_rows),
    }
    parity["cases_where_same_parity_wins"] = sum(value < 0 for value in parity["case_means"].values())

    # Retrospective edge prediction controls on the exact same validation rows.
    model_age = grouped_values(all_rows, "model_minus_age_mismatch")
    model_age_summary = summarize_case_means(model_age, seed=2026101702)
    model_baseline_rows = [
        r for r in all_rows
        if r["used_side"] in ("left", "right") and r["baseline_actual_mismatch"] is not None
    ]
    for row in model_baseline_rows:
        row["model_minus_baseline"] = row["predicted_actual_mismatch"] - row["baseline_actual_mismatch"]
    model_baseline = summarize_case_means(
        grouped_values(model_baseline_rows, "model_minus_baseline"), seed=2026101703
    )
    predicted_gain = summarize_case_means(grouped_values(all_rows, "predicted_side_gain"), seed=2026101704)
    decisive_rows = [r for r in all_rows if r["predicted_side"] != "tie"]
    decisive_baseline_rows = [
        r for r in decisive_rows
        if r["used_side"] in ("left", "right") and r["baseline_actual_mismatch"] is not None
    ]
    for row in decisive_baseline_rows:
        row["model_minus_baseline"] = row["predicted_actual_mismatch"] - row["baseline_actual_mismatch"]
    decisive_model_age = summarize_case_means(
        grouped_values(decisive_rows, "model_minus_age_mismatch"), seed=2026101705
    )
    decisive_model_baseline = summarize_case_means(
        grouped_values(decisive_baseline_rows, "model_minus_baseline"), seed=2026101706
    )
    decisive_gain = summarize_case_means(
        grouped_values(decisive_rows, "predicted_side_gain"), seed=2026101707
    )

    per_case: dict[str, dict] = {}
    for case in sorted({r["case"] for r in all_rows}):
        cr = [r for r in all_rows if r["case"] == case]
        cp = [r for r in parity_rows if r["case"] == case]
        cb = [r for r in model_baseline_rows if r["case"] == case]
        per_case[case] = {
            "eligible_lifetime_rows": len(cr),
            "parity_pairs": len(cp),
            "mean_same_minus_opposite_error": statistics.mean(r["same_minus_opposite"] for r in cp) if cp else None,
            "same_parity_lower_mismatch_fraction": (
                sum(r["same_minus_opposite"] < 0 for r in cp)
                / max(1, sum(r["same_minus_opposite"] != 0 for r in cp))
                if cp else None
            ),
            "model_minus_age_pairs": len(cr),
            "mean_model_minus_age_mismatch": statistics.mean(r["model_minus_age_mismatch"] for r in cr) if cr else None,
            "model_minus_baseline_pairs": len(cb),
            "mean_model_minus_baseline_mismatch": statistics.mean(r["model_minus_baseline"] for r in cb) if cb else None,
            "mean_predicted_side_gain": statistics.mean(r["predicted_side_gain"] for r in cr) if cr else None,
            "decisive_predictions": sum(r["predicted_side"] != "tie" for r in cr),
        }

    summary = {
        "scope": "Retrospective paired replay; no allocator candidate tested",
        "baseline_source_sha256": sha(BASELINE),
        "canonical_source_sha256": sha(CANONICAL),
        "final_run_manifest_sha256": sha(FINAL_MANIFEST),
        "source_audit_sha256": sha(AUDIT),
        "holdout_manifest_sha256": sha(DATA / "manifest.json"),
        "horizon_commands": 128,
        "training_validation_split": "first 50% of commands for completed lifetime history; last 50% validation",
        "parity": parity,
        "lifetime_model_controls": {
            "meaning": "negative mismatch delta favors predicted-lifetime rule over the named control",
            "model_minus_age_only": model_age_summary,
            "model_minus_baseline_chosen_side": model_baseline,
            "predicted_side_gain_vs_other_neighbor": predicted_gain,
            "decisive_predictions_only": {
                "meaning": "rows where the length-and-age predictor strictly preferred one neighbor; negative mismatch delta favors the predictor",
                "predicted_rows": len(decisive_rows),
                "model_minus_age_only": decisive_model_age,
                "model_minus_baseline_chosen_side": decisive_model_baseline,
                "predicted_side_gain_vs_other_neighbor": decisive_gain,
            },
        },
        "per_case": per_case,
        "limits": [
            "holdout-v2 was used in prior finalist comparisons and is not a fresh independent holdout",
            "same/opposite parity and predicted lifetime are retrospective associations on the baseline placement stream",
            "counterfactual edge placement changes future geometry and the later candidate/pair population, so these deltas do not estimate final trench or score",
            "case-cluster bootstrap has only 8-10 eligible stream clusters; intervals are descriptive and not a guarantee of generalization",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (OUT / "per_case.csv").open("w", newline="") as f:
        fields = ["case", *next(iter(per_case.values())).keys()]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for case, values in per_case.items():
            writer.writerow({"case": case, **values})

    elapsed = time.monotonic() - started
    usage_end = resource.getrusage(resource.RUSAGE_SELF)
    manifest = {
        "command": "python3 results/pipes/improvement/neighbor_parity_recheck/analyze_paired_controls.py",
        "platform": __import__("platform").platform(),
        "python": __import__("sys").version.split()[0],
        "elapsed_wall_seconds": elapsed,
        "user_cpu_seconds": usage_end.ru_utime - usage_start.ru_utime,
        "system_cpu_seconds": usage_end.ru_stime - usage_start.ru_stime,
        "max_rss_raw": usage_end.ru_maxrss,
        "max_rss_units": "bytes on macOS; KiB on Linux",
        "bootstrap_draws_per_interval": DRAWS,
        "seed_by_metric": {
            "parity": 2026101701,
            "model_minus_age": 2026101702,
            "model_minus_baseline": 2026101703,
            "predicted_side_gain": 2026101704,
            "decisive_model_minus_age": 2026101705,
            "decisive_model_minus_baseline": 2026101706,
            "decisive_predicted_side_gain": 2026101707,
        },
        "baseline_sha256": sha(BASELINE),
        "canonical_sha256": sha(CANONICAL),
        "final_run_manifest_sha256": sha(FINAL_MANIFEST),
        "audit_script_sha256": sha(AUDIT),
        "analysis_script_sha256": sha(Path(__file__)),
        "input_sha256": input_hashes,
        "baseline_answer_sha256": answer_hashes,
        "case_sizes": case_sizes,
        "output_files": ["summary.json", "per_case.csv", "REPORT.md", "run.json"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"summary": summary, "manifest": manifest}, indent=2))


if __name__ == "__main__":
    main()
