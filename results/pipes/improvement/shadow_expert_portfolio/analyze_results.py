#!/usr/bin/env python3
"""Validate shadow fidelity and evaluate the frozen stream-level gate."""
from __future__ import annotations

import csv
import json
import re
import statistics
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs/matrix"
BOOTSTRAPS = 20_000
BOOTSTRAP_SEED = 87_102_317


def percentile(sorted_values: list[float], p: float) -> float:
    position = (len(sorted_values) - 1) * p
    lo = int(position)
    hi = min(lo + 1, len(sorted_values) - 1)
    fraction = position - lo
    return sorted_values[lo] * (1.0 - fraction) + sorted_values[hi] * fraction


def shadow_values(stderr_file: str) -> dict[str, int]:
    text = Path(stderr_file).read_text(encoding="utf-8")
    match = re.search(r"shadow_final_trench=(\d+) shadow_pid46_trench=(\d+) "
                      r"real_trench=(\d+) frozen_picks=(\d+) pid46_picks=(\d+) "
                      r"switches=(\d+) real_mc_rollouts=(\d+)", text)
    if not match:
        raise ValueError(f"missing portfolio diagnostics in {stderr_file}")
    keys = ("shadow_frozen_trench", "shadow_pid46_trench", "real_trench",
            "frozen_picks", "pid46_picks", "switches", "real_mc_rollouts")
    return dict(zip(keys, map(int, match.groups()), strict=True))


def main() -> None:
    summaries = {}
    for label in ("frozen", "pid46", "portfolio"):
        path = RUNS / label / "summary.json"
        summaries[label] = json.loads(path.read_text(encoding="utf-8"))
    records = {label: {row["case"]: row for row in summary["records"]}
               for label, summary in summaries.items()}
    manifest = json.loads((ROOT / "input_manifest.json").read_text(encoding="utf-8"))
    scenarios = {name: row["scenario"] for name, row in manifest["streams"].items()}
    rows = []
    fidelity_errors = []
    for case, frozen in records["frozen"].items():
        pid = records["pid46"][case]
        port = records["portfolio"][case]
        diag = shadow_values(port["candidate_stderr_file"])
        if diag["shadow_frozen_trench"] != frozen["trench_length_m"]:
            fidelity_errors.append({"case": case, "expert": "frozen",
                                    "shadow": diag["shadow_frozen_trench"],
                                    "harness": frozen["trench_length_m"]})
        if diag["shadow_pid46_trench"] != pid["trench_length_m"]:
            fidelity_errors.append({"case": case, "expert": "pid46",
                                    "shadow": diag["shadow_pid46_trench"],
                                    "harness": pid["trench_length_m"]})
        scenario = scenarios[case]
        family = next((name for name in manifest["families"]
                       if case.startswith(name + "_n")), None)
        if family is None:
            raise ValueError(f"cannot map stream to registered family: {case}")
        rows.append({
            "case": case, "family": family,
            "operations": scenario["operations"], "seed": scenario["seed"],
            "input_sha256": frozen["test_sha256"],
            "frozen_kpi": frozen["kpi"], "pid46_kpi": pid["kpi"],
            "portfolio_kpi": port["kpi"],
            "delta_portfolio_minus_frozen": port["kpi"] - frozen["kpi"],
            "frozen_trench_m": frozen["trench_length_m"],
            "pid46_trench_m": pid["trench_length_m"],
            "portfolio_trench_m": port["trench_length_m"],
            "shadow_frozen_trench_m": diag["shadow_frozen_trench"],
            "shadow_pid46_trench_m": diag["shadow_pid46_trench"],
            "frozen_picks": diag["frozen_picks"], "pid46_picks": diag["pid46_picks"],
            "switches": diag["switches"],
            "portfolio_cpu_s": port["solver_cpu_total_s"],
            "portfolio_rss_mib": port["solver_peak_rss_mb"],
            "status": port["status"],
            "cpu_limit_exceeded": port["solver_cpu_limit_exceeded"],
            "memory_limit_exceeded": port["solver_memory_limit_exceeded"],
        })
    if len(rows) != 36:
        raise SystemExit(f"expected 36 paired streams, found {len(rows)}")

    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    deltas = [row["delta_portfolio_minus_frozen"] for row in rows]
    mean_delta = statistics.fmean(deltas)
    rng = random.Random(BOOTSTRAP_SEED)
    bootstrap_means = []
    for _ in range(BOOTSTRAPS):
        sample = []
        for family_rows in by_family.values():
            sample.extend(rng.choice(family_rows) for _ in range(len(family_rows)))
        bootstrap_means.append(statistics.fmean(
            row["delta_portfolio_minus_frozen"] for row in sample))
    bootstrap_means.sort()
    ci = [percentile(bootstrap_means, 0.025), percentile(bootstrap_means, 0.975)]
    size_means = {}
    for size in (5_000, 50_000, 200_000):
        size_means[str(size)] = statistics.fmean(
            row["delta_portfolio_minus_frozen"] for row in rows
            if row["operations"] == size)
    family_means = {name: statistics.fmean(
        row["delta_portfolio_minus_frozen"] for row in group)
        for name, group in sorted(by_family.items())}
    all_ok = all(row["status"] == "ok" and not row["cpu_limit_exceeded"] and
                 not row["memory_limit_exceeded"] for row in rows)
    gate_pass = mean_delta > 0 and ci[0] > 0 and not fidelity_errors and all_ok
    result = {
        "streams": len(rows), "mean_paired_kpi_delta": mean_delta,
        "stratified_paired_bootstrap": {"replicates": BOOTSTRAPS,
                                        "seed": BOOTSTRAP_SEED,
                                        "percentile_95_ci": ci},
        "size_mean_deltas": size_means, "family_mean_deltas": family_means,
        "shadow_fidelity_errors": fidelity_errors,
        "all_protocol_and_resource_limits_ok": all_ok,
        "portfolio_max_cpu_s": max(row["portfolio_cpu_s"] for row in rows),
        "portfolio_max_rss_mib": max(row["portfolio_rss_mib"] for row in rows),
        "gate_pass": gate_pass,
        "gate_rule": "mean delta > 0, lower 95% stratified paired bootstrap CI > 0, "
                     "exact shadow trench fidelity, all harness cases/resources ok",
        "stream_rows": rows,
    }
    (ROOT / "analysis.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    with (ROOT / "stream_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report = ["# Shadow expert portfolio — synthetic screen",
              "", f"Gate: **{'PASS' if gate_pass else 'NO-GO'}**",
              "", f"36 streams; mean paired KPI delta (portfolio − frozen): **{mean_delta:+.9f}**.",
              f"Stratified paired 95% bootstrap CI: **[{ci[0]:+.9f}, {ci[1]:+.9f}]**.",
              f"Shadow fidelity mismatches: **{len(fidelity_errors)}**. Protocol/resource failures: **{sum(not (r['status'] == 'ok' and not r['cpu_limit_exceeded'] and not r['memory_limit_exceeded']) for r in rows)}**.",
              f"Portfolio maximum CPU: **{result['portfolio_max_cpu_s']:.6f} s**; maximum RSS: **{result['portfolio_max_rss_mib']:.3f} MiB**.",
              "", "## По размерам", "", "| Команд | Средняя paired Δ KPI |",
              "|---:|---:|"]
    report.extend(f"| {size} | {delta:+.9f} |" for size, delta in size_means.items())
    report.extend(["", "## По семействам", "", "| Семейство | Средняя paired Δ KPI |",
                   "|---|---:|"])
    report.extend(f"| {name} | {delta:+.9f} |" for name, delta in family_means.items())
    report.extend(["", "Все seed, параметры и входные hashes находятся в `input_manifest.json`; ",
                   "покейсовые ресурсы, shadow fidelity и switch counts — в `stream_results.csv`.",
                   "Gate parameters and split were frozen in `PREREGISTERED.md` before runs.", ""])
    (ROOT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"gate={'PASS' if gate_pass else 'NO-GO'} mean_delta={mean_delta:+.9f} "
          f"ci95=[{ci[0]:+.9f},{ci[1]:+.9f}] shadow_errors={len(fidelity_errors)} "
          f"max_cpu={result['portfolio_max_cpu_s']:.6f}s "
          f"max_rss={result['portfolio_max_rss_mib']:.3f}MiB")
    if fidelity_errors:
        raise SystemExit(f"shadow fidelity mismatch(es): {fidelity_errors[:4]}")


if __name__ == "__main__":
    main()
