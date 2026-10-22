#!/usr/bin/env python3
"""Create paired per-case and per-regime comparisons for the frozen candidate."""

import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
STRATEGIES = ("p4", "s50", "transition")
SUITES = ("open", "development")


def read_records(suite, strategy):
    path = HERE / "runs" / suite / strategy / "summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["ok_count"] != data["case_count"]:
        raise SystemExit(f"non-ok cases in {path}")
    return {str(row["case"]): row for row in data["records"]}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    detailed = []
    regime_rows = []
    suite_summaries = {}
    for suite in SUITES:
        by_strategy = {name: read_records(suite, name) for name in STRATEGIES}
        test_names = list(by_strategy["transition"])
        if any(set(rows) != set(test_names) for rows in by_strategy.values()):
            raise SystemExit(f"case mismatch in suite {suite}")
        for case in test_names:
            rows = {name: by_strategy[name][case] for name in STRATEGIES}
            input_hashes = {row["test_sha256"] for row in rows.values()}
            if len(input_hashes) != 1:
                raise SystemExit(f"test hash mismatch: {suite}/{case}")
            common = {
                "suite": suite,
                "case": case,
                "input_sha256": next(iter(input_hashes)),
                "weight": rows["transition"]["official_weight"],
                "commands_including_terminator": rows["transition"]["judge_commands_seen_including_final_zero"],
            }
            for name, row in rows.items():
                common[f"{name}_status"] = row["status"]
                common[f"{name}_kpi"] = row["kpi"]
                common[f"{name}_weighted_score"] = row["weighted_score"]
                common[f"{name}_trench_m"] = row["trench_length_m"]
                common[f"{name}_cpu_s"] = row.get("solver_cpu_total_s")
                common[f"{name}_rss_mib"] = row.get("solver_peak_rss_mb")
            common["transition_minus_p4_score"] = (
                rows["transition"]["weighted_score"] - rows["p4"]["weighted_score"]
            )
            common["transition_minus_s50_score"] = (
                rows["transition"]["weighted_score"] - rows["s50"]["weighted_score"]
            )
            detailed.append(common)

        scores = {
            name: sum(float(row["weighted_score"] or 0.0) for row in by_strategy[name].values())
            for name in STRATEGIES
        }
        suite_summaries[suite] = {
            "case_count": len(test_names),
            "weight_sum": sum(float(row["official_weight"]) for row in by_strategy["transition"].values()),
            "weighted_score_sums": scores,
            "transition_minus_p4": scores["transition"] - scores["p4"],
            "transition_minus_s50": scores["transition"] - scores["s50"],
            "per_strategy": {},
        }
        for strategy in STRATEGIES:
            recs = list(by_strategy[strategy].values())
            suite_summaries[suite]["per_strategy"][strategy] = {
                "mean_kpi": sum(float(row["kpi"]) for row in recs) / len(recs),
                "max_solver_cpu_s": max(float(row["solver_cpu_total_s"] or 0.0) for row in recs),
                "max_solver_rss_mib": max(float(row["solver_peak_rss_mb"] or 0.0) for row in recs),
                "total_judge_commands_including_terminators": sum(
                    int(row["judge_commands_seen_including_final_zero"]) for row in recs
                ),
            }

        groups = [(suite, "all", test_names)] if suite == "open" else [
            (suite, case, [case]) for case in test_names
        ]
        for group_suite, regime, cases in groups:
            group = {name: [by_strategy[name][case] for case in cases] for name in STRATEGIES}
            row = {
                "suite": group_suite,
                "regime": regime,
                "case_count": len(cases),
                "weight_sum": sum(float(x["official_weight"]) for x in group["transition"]),
            }
            for strategy in STRATEGIES:
                row[f"{strategy}_weighted_score_sum"] = sum(float(x["weighted_score"] or 0.0) for x in group[strategy])
                row[f"{strategy}_mean_kpi"] = sum(float(x["kpi"]) for x in group[strategy]) / len(group[strategy])
                row[f"{strategy}_max_cpu_s"] = max(float(x["solver_cpu_total_s"] or 0.0) for x in group[strategy])
                row[f"{strategy}_max_rss_mib"] = max(float(x["solver_peak_rss_mb"] or 0.0) for x in group[strategy])
            row["transition_minus_p4_score"] = row["transition_weighted_score_sum"] - row["p4_weighted_score_sum"]
            row["transition_minus_s50_score"] = row["transition_weighted_score_sum"] - row["s50_weighted_score_sum"]
            regime_rows.append(row)

    with (HERE / "per_case.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detailed[0]))
        writer.writeheader()
        writer.writerows(detailed)
    with (HERE / "per_regime.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(regime_rows[0]))
        writer.writeheader()
        writer.writerows(regime_rows)
    (HERE / "comparison_summary.json").write_text(
        json.dumps(suite_summaries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(suite_summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
