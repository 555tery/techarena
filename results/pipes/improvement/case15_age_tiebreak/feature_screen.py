#!/usr/bin/env python3
"""Summarize age contrast for exact same-size shadowed EOF survivor gaps."""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
AUDIT = ROOT / "results/pipes/improvement/case15_survivor_rank"
LINEAGE = ROOT / "results/pipes/improvement/case15_interval_lineage/replay"

survivors = {
    int(row["id"]): row
    for row in csv.DictReader((LINEAGE / "current_gaps.csv").open())
}
episodes = list(csv.DictReader((LINEAGE / "gap_episodes.csv").open()))
by_span = {}
for row in episodes:
    key = (int(row["start"]), int(row["end"]))
    by_span.setdefault(key, []).append(row)

shadowed = []
lineage_rows = Counter()
unmatched = 0
trace = AUDIT / "run_exact/runs/15/solver_stderr.txt"
for line in trace.read_text().splitlines():
    if not line.startswith("SVDIAG "):
        continue
    fields = line.split()
    op, gap_id, _, start, end, length, birth_op = map(int, fields[1:8])
    eligibility = fields[15]
    if eligibility != "same_size_shadowed":
        continue
    representative_start = int(fields[16])
    current = survivors[gap_id]
    age_target = op - birth_op
    candidates = [
        row for row in by_span.get(
            (representative_start, representative_start + length), []
        )
        if int(row["birth_op"]) < op <= int(row["end_op"])
    ]
    if not candidates:
        unmatched += 1
        continue
    representative = candidates[0]
    age_rep = op - int(representative["birth_op"])
    shadowed.append((age_target - age_rep, age_target, age_rep))
    lineage_rows[int(current["lineage_mask"])] += 1

age_delta = [row[0] for row in shadowed]
out = {
    "shadowed_rows": len(shadowed),
    "unmatched_exact_representatives": unmatched,
    "target_older_rows": sum(delta > 0 for delta in age_delta),
    "equal_age_rows": sum(delta == 0 for delta in age_delta),
    "target_younger_rows": sum(delta < 0 for delta in age_delta),
    "target_older_fraction": sum(delta > 0 for delta in age_delta) / len(age_delta),
    "target_minus_representative_age_ops": {
        "min": min(age_delta),
        "median": statistics.median(age_delta),
        "p90_nearest_lower": sorted(age_delta)[int((len(age_delta) - 1) * 0.9)],
        "max": max(age_delta),
    },
    "target_lineage_mask_rows": dict(lineage_rows),
    "age_definition": "operation_index - current_gap_birth_op; age resets on interval split/merge",
    "selection_bias_note": "Targets were selected retrospectively by EOF survival and prior fitting demand; age contrast is a hypothesis screen, not causal evidence.",
}
(OUT / "feature_screen.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
