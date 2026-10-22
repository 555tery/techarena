#!/usr/bin/env python3
"""Build comparison tables from already-finished interactive harness runs."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"


def load(name):
    with (RUNS / name / "cases.csv").open(newline="", encoding="utf-8") as f:
        return {row["case"]: row for row in csv.DictReader(f)}


def metric(row, key):
    value = row.get(key, "")
    return float(value) if value not in (None, "") else ""


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def joined_rows(base_name, trend_name, owner_name, group):
    base, trend, owner = load(base_name), load(trend_name), load(owner_name)
    rows = []
    for case in sorted(base, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x)):
        b, t, o = base[case], trend[case], owner[case]
        row = {"scope": group, "case": case, "weight": metric(b, "official_weight")}
        for label, rec in (("t46", b), ("trend", t), ("owner", o)):
            row[f"{label}_status"] = rec["status"]
            row[f"{label}_weighted_score"] = metric(rec, "weighted_score")
            row[f"{label}_trench_m"] = metric(rec, "trench_length_m")
            row[f"{label}_kpi"] = metric(rec, "kpi")
            row[f"{label}_solver_cpu_s"] = metric(rec, "solver_cpu_total_s")
            row[f"{label}_solver_rss_mib"] = metric(rec, "solver_peak_rss_mb")
        row["trend_delta_vs_t46"] = metric(t, "weighted_score") - metric(b, "weighted_score")
        row["owner_delta_vs_t46"] = metric(o, "weighted_score") - metric(b, "weighted_score")
        rows.append(row)
    return rows


def main():
    official = joined_rows("t46_baseline", "t46_cohort_trend", "t46_cohort_owner", "official_open")
    holdout = joined_rows("synthetic_baseline", "synthetic_cohort_trend", "synthetic_cohort_owner", "synthetic_final_holdout_v2_known_reused")
    robustness = joined_rows("robustness_baseline", "robustness_cohort", "robustness_cohort_owner", "synthetic_robustness_inputs_known_reused")
    alternating = joined_rows("alternating_baseline", "alternating_trend", "alternating_owner", "synthetic_alternating_policy_new_exploratory")
    write(ROOT / "official_open_comparison.csv", official)
    write(ROOT / "secondary_synthetic_comparison.csv", holdout + robustness + alternating)
    print(f"official_rows={len(official)} synthetic_rows={len(holdout) + len(robustness) + len(alternating)}")


if __name__ == "__main__":
    main()
