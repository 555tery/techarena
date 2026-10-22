#!/usr/bin/env python3
"""Paired whole-stream bootstrap and predeclared validation slices."""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATION = HERE / "validation"
N_BOOT = 50_000
SEED = 20261017


def interval(values: list[float], rng: random.Random) -> list[float]:
    if not values:
        return [float("nan"), float("nan")]
    means = []
    for _ in range(N_BOOT):
        means.append(sum(values[rng.randrange(len(values))] for _ in values) / len(values))
    means.sort()
    return [means[int(0.025 * (N_BOOT - 1))], means[int(0.975 * (N_BOOT - 1))]]


def summarize(rows: list[dict], rng: random.Random) -> dict:
    dscore = [float(row["delta_kpi_candidate_minus_baseline"]) for row in rows]
    dtrench = [float(row["delta_trench_m_candidate_minus_baseline"]) for row in rows]
    return {
        "n_streams": len(rows),
        "mean_delta_kpi_candidate_minus_frozen": sum(dscore) / len(dscore),
        "delta_kpi_paired_stream_bootstrap_95_ci": interval(dscore, rng),
        "mean_delta_trench_m_candidate_minus_frozen": sum(dtrench) / len(dtrench),
        "delta_trench_paired_stream_bootstrap_95_ci_m": interval(dtrench, rng),
        "improved_kpi_streams": sum(value > 0 for value in dscore),
        "regressed_kpi_streams": sum(value < 0 for value in dscore),
        "unchanged_kpi_streams": sum(value == 0 for value in dscore),
        "improved_trench_streams": sum(value < 0 for value in dtrench),
        "regressed_trench_streams": sum(value > 0 for value in dtrench),
        "unchanged_trench_streams": sum(value == 0 for value in dtrench),
    }


def main() -> None:
    with (VALIDATION / "per_case.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rng = random.Random(SEED)
    result = {
        "method": "paired percentile bootstrap over independent whole streams; equal stream weight",
        "bootstrap_replicates": N_BOOT,
        "bootstrap_seed": SEED,
        "overall": summarize(rows, rng),
        "by_length_profile": {},
        "by_size": {},
        "by_deletion_policy": {},
        "resource_gate": {
            "provisional_cpu_max_s": 4.50,
            "provisional_rss_max_mib": 230.0,
            "basis": "10% margin from official 5s/256MiB limits; adopted after an intermediate 4.407s measurement and before the final matrix case completed",
            "max_candidate_cpu_s": max(float(row["candidate_cpu_s"]) for row in rows),
            "max_candidate_rss_mib": max(float(row["candidate_rss_mib"]) for row in rows),
            "harness_cpu_violations": sum(row["candidate_cpu_limit_exceeded"] == "True" for row in rows),
            "harness_memory_violations": sum(row["candidate_memory_limit_exceeded"] == "True" for row in rows),
        },
    }
    for key, field in (
        ("by_length_profile", "length_profile"),
        ("by_size", "operations"),
        ("by_deletion_policy", "deletion_policy"),
    ):
        for value in sorted({row[field] for row in rows}, key=str):
            subset = [row for row in rows if row[field] == value]
            result[key][str(value)] = summarize(subset, rng)

    with (VALIDATION / "telemetry.json").open(encoding="utf-8") as handle:
        telemetry = json.load(handle)
    result["selector_telemetry"] = {
        "policy_calls": sum(item["counters"].get("policy_calls", 0) for item in telemetry),
        "policy_checks": sum(item["counters"].get("policy_checks", 0) for item in telemetry),
        "frozen_mc_decisions": sum(item["counters"].get("mc_decisions", 0) for item in telemetry),
        "frozen_mc_rollouts": sum(item["counters"].get("mc_rollouts", 0) for item in telemetry),
        "evaluations": sum(item["counters"].get("policy_evaluations", 0) for item in telemetry),
        "p4_choices": sum(item["counters"].get("policy_p4_choices", 0) for item in telemetry),
        "no_pair_fallbacks": sum(item["counters"].get("policy_no_pair", 0) for item in telemetry),
        "nonimproving_fallbacks": sum(item["counters"].get("policy_nonimproving", 0) for item in telemetry),
        "same_action_skips": sum(item["counters"].get("policy_same_action", 0) for item in telemetry),
        "mc_budget_skips": sum(item["counters"].get("policy_skip_mc", 0) for item in telemetry),
        "cadence_skips": sum(item["counters"].get("policy_skip_cadence", 0) for item in telemetry),
        "decision_budget_skips": sum(item["counters"].get("policy_skip_budget", 0) for item in telemetry),
        "history_skips": sum(item["counters"].get("policy_skip_history", 0) for item in telemetry),
        "gap_limit_skips": sum(item["counters"].get("policy_skip_gaps", 0) for item in telemetry),
        "active_limit_skips": sum(item["counters"].get("policy_skip_active", 0) for item in telemetry),
        "changed_reply_cases": sum(item["different_reply_lines_vs_baseline"] > 0 for item in telemetry),
        "sum_changed_reply_lines": sum(item["different_reply_lines_vs_baseline"] for item in telemetry),
    }
    out = VALIDATION / "paired_bootstrap.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
