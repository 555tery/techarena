#!/usr/bin/env python3
"""Descriptive summaries for the instrumented case-15 interval replay."""
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "interval_origin_case15"


def read_csv(name):
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


def number(row, key):
    return float(row[key])


def quantile(values, q):
    if not values:
        return None
    xs = sorted(values)
    x = (len(xs) - 1) * q
    lo = math.floor(x)
    hi = math.ceil(x)
    return xs[lo] + (xs[hi] - xs[lo]) * (x - lo)


def stats(rows, get):
    xs = [get(r) for r in rows]
    return {
        "n": len(xs),
        "mean": sum(xs) / len(xs) if xs else None,
        "median": quantile(xs, .5),
        "p90": quantile(xs, .9),
        "sum": sum(xs),
    }


episodes = read_csv("gap_episodes.csv")
current = read_csv("current_gaps.csv")
placements = read_csv("placements.csv")
meta = json.loads((DATA / "replay_meta.json").read_text())

category_stats = {}
for category in ("placement_residual", "deletion_hole", "mixed_merged"):
    es = [r for r in episodes if r["reason"] == category]
    cs = [r for r in current if r["reason"] == category]
    cause_counts = Counter(r["close_cause"] for r in es)
    category_stats[category] = {
        "episodes": len(es),
        "close_causes": dict(sorted(cause_counts.items())),
        "lifetime_ops": stats(es, lambda r: number(r, "lifetime_ops")),
        "episode_length_m": stats(es, lambda r: number(r, "length")),
        "right_censored_share": sum(int(r["right_censored"]) for r in es) / len(es) if es else None,
        "whole_trace_demand_fit_fraction": stats(es, lambda r: number(r, "whole_trace_fit_fraction")),
        "current_gaps": len(cs),
        "current_free_m": sum(int(r["length"]) for r in cs),
        "current_length_m": stats(cs, lambda r: number(r, "length")),
        "current_whole_trace_fit_fraction": stats(cs, lambda r: number(r, "whole_trace_fit_fraction")),
        "current_recent2048_fit_fraction": stats(cs, lambda r: number(r, "recent_fit_fraction")),
        "current_any_recent_fit_share": sum(int(r["recent2048_demands_fit"]) > 0 for r in cs) / len(cs) if cs else None,
        "lineage_mask_counts_episodes": dict(sorted(Counter(r["lineage_mask"] for r in es).items())),
        "lineage_mask_counts_current": dict(sorted(Counter(r["lineage_mask"] for r in cs).items())),
    }

placement_by_op = {int(r["op"]): r for r in placements}
cost_rows = []
cost_re = re.compile(r"^COST\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s*$")
cost_log = ROOT / "cost_runs/runs/15/solver_stderr.txt"
for line in cost_log.read_text().splitlines():
    m = cost_re.match(line)
    if not m:
        continue
    (op, length, highside, cohort, parity, baseline_start, baseline_len,
     baseline_score, chosen_start, chosen_len, history, slack, misses) = map(int, m.groups())
    p = placement_by_op[op]
    if int(p["length"]) != length:
        raise ValueError(f"length mismatch at operation {op}")
    if int(p["selected_gap_start"]) != chosen_start or int(p["selected_gap_end"]) - int(p["selected_gap_start"]) != chosen_len:
        raise ValueError(f"chosen gap mismatch at operation {op}")
    if int(p["bestfit_gap_start"]) != baseline_start or int(p["bestfit_gap_length"]) != baseline_len:
        raise ValueError(f"baseline gap mismatch at operation {op}")
    cost_rows.append({
        "op": op,
        "length": length,
        "baseline_reason": p["bestfit_reason"],
        "chosen_reason": p["selected_gap_reason"],
        "baseline_score": baseline_score,
        "chosen_score": int(p["total_cost"]),
        "score_delta_chosen_minus_baseline": int(p["total_cost"]) - baseline_score,
        "chosen_slack": int(p["slack"]),
        "chosen_misses": int(p["misses"]),
        "chosen_slack_cost": int(p["slack_cost"]),
        "chosen_penalty_cost": int(p["penalty_cost"]),
        "override": baseline_start != chosen_start,
    })

cost_by_actual_category = {}
for category in ("placement_residual", "deletion_hole", "mixed_merged"):
    rs = [r for r in cost_rows if r["chosen_reason"] == category]
    cost_by_actual_category[category] = {
        "count": len(rs),
        "slack_cost": sum(r["chosen_slack_cost"] for r in rs),
        "unfit_penalty_cost": sum(r["chosen_penalty_cost"] for r in rs),
        "selected_score": stats(rs, lambda r: r["chosen_score"]),
        "slack": stats(rs, lambda r: r["chosen_slack"]),
        "misses": stats(rs, lambda r: r["chosen_misses"]),
        "override_count": sum(r["override"] for r in rs),
    }

cost_by_baseline_category = {}
for category in ("placement_residual", "deletion_hole", "mixed_merged"):
    rs = [r for r in cost_rows if r["baseline_reason"] == category]
    cost_by_baseline_category[category] = {
        "count": len(rs),
        "baseline_score": stats(rs, lambda r: r["baseline_score"]),
        "override_count": sum(r["override"] for r in rs),
    }

overrides = [r for r in cost_rows if r["override"]]
actual_placement_reasons = Counter(r["selected_gap_reason"] for r in placements)
actual_lineages = Counter(r["lineage_mask"] for r in placements)
out = {
    "meta": meta,
    "episode_categories": category_stats,
    "current_free_length_share": {
        c: category_stats[c]["current_free_m"] / meta["free_length_m"]
        for c in category_stats
    },
    "actual_placement_gap_reasons_all_placements": dict(actual_placement_reasons),
    "actual_placement_lineages_all_placements": dict(actual_lineages),
    "cost_eligible_placements": len(cost_rows),
    "placements_without_cost_choice": len(placements) - len(cost_rows),
    "cost_eligible_actual_categories": cost_by_actual_category,
    "cost_eligible_baseline_categories": cost_by_baseline_category,
    "local_cost": {
        "override_count": len(overrides),
        "override_share_of_cost_eligible": len(overrides) / len(cost_rows) if cost_rows else None,
        "override_category_transitions": dict(sorted(Counter(f"{r['baseline_reason']}->{r['chosen_reason']}" for r in overrides).items())),
        "chosen_minus_baseline_score": stats(cost_rows, lambda r: r["score_delta_chosen_minus_baseline"]),
        "sum_chosen_slack_cost": sum(int(r["slack_cost"]) for r in placements),
        "sum_chosen_unfit_penalty_cost": sum(int(r["penalty_cost"]) for r in placements),
        "sum_chosen_cost_all_placements": sum(int(r["total_cost"]) for r in placements),
        "sum_chosen_slack_cost_cost_eligible": sum(r["chosen_slack_cost"] for r in cost_rows),
        "sum_chosen_unfit_penalty_cost_cost_eligible": sum(r["chosen_penalty_cost"] for r in cost_rows),
        "sum_baseline_score": sum(r["baseline_score"] for r in cost_rows),
    },
    "cost_by_actual_category": cost_by_actual_category,
    "cost_by_baseline_category": cost_by_baseline_category,
}
(DATA / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
