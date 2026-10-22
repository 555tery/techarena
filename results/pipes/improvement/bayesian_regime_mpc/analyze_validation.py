#!/usr/bin/env python3
"""Evaluate frozen stream-level gate; do not tune candidate from this output."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs/validation"
BOOTSTRAPS = 20_000
BOOTSTRAP_SEED = 9_801_702_026


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(sorted_values: list[float], p: float) -> float:
    pos = (len(sorted_values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    fraction = pos - lo
    return sorted_values[lo] * (1.0 - fraction) + sorted_values[hi] * fraction


def main() -> None:
    frozen = json.loads((RUNS / "frozen/summary.json").read_text(encoding="utf-8"))
    candidate = json.loads((RUNS / "bayesian/summary.json").read_text(encoding="utf-8"))
    data_manifest = json.loads((ROOT / "input_manifest.json").read_text(encoding="utf-8"))
    freeze = json.loads((ROOT / "freeze_manifest.json").read_text(encoding="utf-8"))
    freeze_checks = {
        "candidate_source_unchanged": sha(ROOT / "source/bayesian_regime_mpc.cpp") ==
            freeze["candidate_source_sha256"],
        "frozen_source_unchanged": sha(ROOT / "source/frozen_final.cpp") ==
            freeze["frozen_source_sha256"],
        "model_params_unchanged": sha(ROOT / "model_params.json") ==
            freeze["fitted_model_parameters_sha256"],
        "validation_manifest_unchanged": sha(ROOT / "input_manifest.json") ==
            freeze["training_manifest_sha256"],
        "gate_unchanged": sha(ROOT / "PREREGISTERED.md") ==
            freeze["preregistered_gate_sha256"],
    }
    if not all(freeze_checks.values()):
        raise SystemExit(f"freeze integrity failure: {freeze_checks}")

    frozen_rows = {row["case"]: row for row in frozen["records"]}
    candidate_rows = {row["case"]: row for row in candidate["records"]}
    validation = data_manifest["validation"]
    rows = []
    for case, base in frozen_rows.items():
        current = candidate_rows[case]
        scenario = validation[case]["scenario"]
        input_sha = validation[case]["sha256"]
        if base["test_sha256"] != input_sha or current["test_sha256"] != input_sha:
            raise SystemExit(f"paired input hash mismatch: {case}")
        if base["test_sha256"] != current["test_sha256"]:
            raise SystemExit(f"baseline/candidate input mismatch: {case}")
        rows.append({
            "case": case,
            "family": next(name for name in data_manifest["families"]
                           if case.startswith(name + "_n")),
            "operations": scenario["operations"],
            "seed": scenario["seed"],
            "input_sha256": input_sha,
            "frozen_kpi": base["kpi"],
            "candidate_kpi": current["kpi"],
            "delta_kpi": current["kpi"] - base["kpi"],
            "frozen_trench_m": base["trench_length_m"],
            "candidate_trench_m": current["trench_length_m"],
            "delta_trench_m": current["trench_length_m"] - base["trench_length_m"],
            "frozen_status": base["status"],
            "candidate_status": current["status"],
            "candidate_cpu_s": current["solver_cpu_total_s"],
            "candidate_rss_mib": current["solver_peak_rss_mb"],
            "cpu_limit_exceeded": current["solver_cpu_limit_exceeded"],
            "memory_limit_exceeded": current["solver_memory_limit_exceeded"],
        })
    if len(rows) != 28:
        raise SystemExit(f"expected 28 paired streams, found {len(rows)}")

    strata: dict[tuple[str, int], list[dict]] = {}
    families: dict[str, list[dict]] = {}
    for row in rows:
        strata.setdefault((row["family"], row["operations"]), []).append(row)
        families.setdefault(row["family"], []).append(row)
    if len(strata) != 14 or any(len(values) != 2 for values in strata.values()):
        raise SystemExit("validation split does not match preregistered 14x2 strata")

    mean_delta = statistics.fmean(row["delta_kpi"] for row in rows)
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    ordered_strata = [strata[key] for key in sorted(strata)]
    for _ in range(BOOTSTRAPS):
        draw = [rng.choice(group) for group in ordered_strata for _ in range(2)]
        samples.append(statistics.fmean(row["delta_kpi"] for row in draw))
    samples.sort()
    ci = [percentile(samples, 0.025), percentile(samples, 0.975)]
    size_means = {
        str(size): statistics.fmean(row["delta_kpi"] for row in rows
                                    if row["operations"] == size)
        for size in (16_384, 200_000)
    }
    family_means = {name: statistics.fmean(row["delta_kpi"] for row in group)
                    for name, group in sorted(families.items())}
    all_ok = (frozen["ok_count"] == 28 and candidate["ok_count"] == 28 and
              all(row["frozen_status"] == "ok" and row["candidate_status"] == "ok"
                  and not row["cpu_limit_exceeded"] and not row["memory_limit_exceeded"]
                  for row in rows))
    mean_200k_nonnegative = size_means["200000"] >= 0.0
    family_guard_count = sum(value >= 0.0 for value in family_means.values())
    gate = (mean_delta > 0.0 and ci[0] > 0.0 and mean_200k_nonnegative and
            family_guard_count >= 5 and all_ok)
    result = {
        "status": "PASS" if gate else "NO-GO",
        "streams": len(rows),
        "mean_paired_delta_kpi": mean_delta,
        "paired_bootstrap": {"replicates": BOOTSTRAPS, "seed": BOOTSTRAP_SEED,
                              "stratification": "family x size; 2 stream resamples per cell",
                              "ci95": ci},
        "size_mean_delta_kpi": size_means,
        "family_mean_delta_kpi": family_means,
        "family_guard_nonnegative_count": family_guard_count,
        "mean_200k_nonnegative": mean_200k_nonnegative,
        "all_protocol_and_resource_checks_ok": all_ok,
        "shadow_integrity_checks": freeze_checks,
        "frozen_weighted_score_sum": frozen["weighted_score_sum"],
        "candidate_weighted_score_sum": candidate["weighted_score_sum"],
        "candidate_max_cpu_s": max(row["candidate_cpu_s"] for row in rows),
        "candidate_max_rss_mib": max(row["candidate_rss_mib"] for row in rows),
        "better_worse_tied_streams": {
            "better": sum(row["delta_kpi"] > 0 for row in rows),
            "worse": sum(row["delta_kpi"] < 0 for row in rows),
            "tied": sum(row["delta_kpi"] == 0 for row in rows),
        },
        "gate_rule": "mean delta > 0; stratified paired bootstrap lower 95% CI > 0; "
                     "200k mean >= 0; >=5/7 family means >=0; all protocol/resource checks ok",
        "rows": rows,
    }
    (ROOT / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    with (ROOT / "stream_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report = [
        "# Bayesian latent-regime MPC — synthetic validation",
        "",
        f"Gate: **{result['status']}**. 28 paired streams; all sizes/profiles were preregistered.",
        f"Mean Δ KPI: **{mean_delta:+.9f}**; stratified paired 95% CI: "
        f"**[{ci[0]:+.9f}, {ci[1]:+.9f}]**.",
        f"Per-stream: {result['better_worse_tied_streams']['better']} improved, "
        f"{result['better_worse_tied_streams']['worse']} regressed, "
        f"{result['better_worse_tied_streams']['tied']} tied.",
        f"Maximum candidate CPU **{result['candidate_max_cpu_s']:.6f} s**; "
        f"maximum RSS **{result['candidate_max_rss_mib']:.3f} MiB**; "
        f"protocol/resource checks: **{'pass' if all_ok else 'fail'}**.",
        "",
        "## По размерам",
        "",
        "| Команд | Mean paired Δ KPI |",
        "|---:|---:|",
    ]
    report.extend(f"| {size} | {delta:+.9f} |" for size, delta in size_means.items())
    report.extend(["", "## По профилям", "", "| Профиль | Mean paired Δ KPI |", "|---|---:|"])
    report.extend(f"| {family} | {delta:+.9f} |" for family, delta in family_means.items())
    report.extend([
        "",
        "Holdout-v2/Open15 разрешены только при PASS; параметры после freeze не меняются.",
        "Точные входные hashes и fitted params — `input_manifest.json` / `model_params.json`; "
        "per-stream outcomes — `stream_results.csv`.",
        "",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"gate={result['status']} mean_delta={mean_delta:+.9f} "
          f"ci95=[{ci[0]:+.9f},{ci[1]:+.9f}] 200k={size_means['200000']:+.9f} "
          f"families_nonnegative={family_guard_count}/7 "
          f"max_cpu={result['candidate_max_cpu_s']:.6f}s "
          f"max_rss={result['candidate_max_rss_mib']:.3f}MiB")


if __name__ == "__main__":
    main()
