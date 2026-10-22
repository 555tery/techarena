#!/usr/bin/env python3
"""Offline causal-prefix feature and switching diagnostics; no model fitting."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[0].parent
TRAIN = HERE / "train"
VALIDATION = HERE / "validation"
OUT = HERE / "search/early_identifiability"


def summarize_lengths(values):
    if not values:
        return {"length_mean": 0.0, "length_sd": 0.0, "length_entropy": 0.0,
                "length_distinct": 0, "long_share": 0.0, "short_share": 0.0,
                "periodicity_max_eq": 0.0, "periodicity_lag": 0}
    counts = Counter(values)
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    entropy = -sum((count / n) * math.log2(count / n) for count in counts.values())
    best_lag, best_eq = 0, 0.0
    for lag in range(1, min(16, n - 1) + 1):
        eq = sum(values[i] == values[i - lag] for i in range(lag, n)) / (n - lag)
        if eq > best_eq:
            best_lag, best_eq = lag, eq
    return {
        "length_mean": mean,
        "length_sd": math.sqrt(variance),
        "length_entropy": entropy,
        "length_distinct": len(counts),
        "long_share": sum(x >= 21 for x in values) / n,
        "short_share": sum(x <= 4 for x in values) / n,
        "periodicity_max_eq": best_eq,
        "periodicity_lag": best_lag,
    }


def read_case(input_path: Path, response_path: Path):
    tokens = input_path.read_text().split()
    operations = int(tokens[1])
    commands = list(map(int, tokens[2:2 + operations]))
    responses = [list(map(int, line.split())) for line in response_path.read_text().splitlines()]
    if len(commands) != operations or len(responses) != operations:
        raise ValueError(f"command/response count mismatch for {input_path.name}")

    active = {}
    live_length = 0
    trench = 0
    placed_lengths = []
    recent_event_kind = deque(maxlen=128)
    recent_delete_rank = deque(maxlen=64)
    recent_expansion = deque(maxlen=64)
    history_gate = deque(maxlen=64)
    gate_flips = 0
    gate_on_placements = 0
    placement_total = 0
    deletion_total = 0
    next_checkpoint = 128
    checkpoints = []

    def take_snapshot(prefix_count):
        intervals = sorted((start, start + length) for start, length in active.values())
        gaps = []
        cursor = 0
        for start, end in intervals:
            if start > cursor:
                gaps.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < trench:
            gaps.append((cursor, trench))
        free_total = trench - live_length
        tail_length = 0
        if gaps and gaps[-1][1] == trench:
            tail_length = gaps[-1][1] - gaps[-1][0]
        long_count = sum(x >= 21 for x in list(placed_lengths)[-64:])
        lens = list(placed_lengths)[-64:]
        lf = summarize_lengths(lens)
        deletes = [x for x in recent_event_kind]
        delete_share = (sum(deletes) / len(deletes)) if deletes else 0.0
        ranks = list(recent_delete_rank)
        newest_delete_share = (sum(x >= 0.8 for x in ranks) / len(ranks)) if ranks else 0.0
        expansion = list(recent_expansion)
        expansion_share = (sum(expansion) / len(expansion)) if expansion else 0.0
        active_lengths = [length for _, length in active.values()]
        checkpoints.append({
            "prefix_events": prefix_count,
            "prefix_fraction": prefix_count / operations,
            "active_count": len(active),
            "live_length": live_length,
            "active_mean_length": (live_length / len(active)) if active else 0.0,
            "trench_length": trench,
            "free_length": free_total,
            "free_share": (free_total / trench) if trench else 0.0,
            "free_gap_count": len(gaps),
            "largest_gap": max((b - a for a, b in gaps), default=0),
            "tail_gap": tail_length,
            "gap_count_per_1000_free_m": (1000.0 * len(gaps) / free_total) if free_total else 0.0,
            "recent_delete_share": delete_share,
            "recent_newest_delete_share": newest_delete_share,
            "recent_expansion_share": expansion_share,
            "tree_gate_on": long_count <= 32,
            "recent_long_count": long_count,
            "active_length_min": min(active_lengths, default=0),
            "active_length_max": max(active_lengths, default=0),
            **lf,
        })

    previous_gate = None
    for prefix_count, (command, response) in enumerate(zip(commands, responses), 1):
        if command > 0:
            if len(response) != 2:
                raise ValueError(f"placement response malformed for {input_path.name}")
            digs, start = response
            trench += digs * 20
            # The number of prior placements is the next protocol PID.
            pid = len(placed_lengths) + 1
            active[pid] = (start, command)
            live_length += command
            placed_lengths.append(command)
            placement_total += 1
            recent_expansion.append(int(digs > 0))
            recent_event_kind.append(0)
            hist = list(placed_lengths)[-64:]
            long_count = sum(x >= 21 for x in hist)
            gate = long_count <= 32
            if previous_gate is not None and gate != previous_gate:
                gate_flips += 1
            previous_gate = gate
            gate_on_placements += int(gate)
        else:
            if len(response) != 1:
                raise ValueError(f"deletion response malformed for {input_path.name}")
            pid = -command
            if pid not in active:
                raise ValueError(f"invalid deletion pid while parsing {input_path.name}")
            newer = sum(other_pid > pid for other_pid in active)
            denominator = max(1, len(active) - 1)
            recent_delete_rank.append(newer / denominator)
            start, length = active.pop(pid)
            if response[0] != start:
                raise ValueError(f"delete placement mismatch for {input_path.name}")
            live_length -= length
            deletion_total += 1
            recent_event_kind.append(1)

        if prefix_count == next_checkpoint or prefix_count == operations:
            take_snapshot(prefix_count)
            next_checkpoint *= 2

    return {
        "operations": operations,
        "placements": placement_total,
        "deletions": deletion_total,
        "gate_flips": gate_flips,
        "gate_on_placement_share": gate_on_placements / max(1, placement_total),
        "checkpoints": checkpoints,
    }


def run_case(dataset: str, name: str, input_path: Path, baseline_dir: Path, candidate_dir: Path, delta):
    case = read_case(input_path, baseline_dir / name / "judge_output.txt")
    baseline_summary = json.loads((baseline_dir.parent / "summary.json").read_text())
    baseline_record = next(r for r in baseline_summary["records"] if r["case"] == name)
    candidate_summary = json.loads((candidate_dir.parent / "summary.json").read_text())
    candidate_record = next(r for r in candidate_summary["records"] if r["case"] == name)
    outcome = "positive" if delta > 1e-12 else "negative" if delta < -1e-12 else "neutral"
    rows = []
    for snapshot in case["checkpoints"]:
        rows.append({
            "dataset": dataset,
            "stream": name,
            "outcome": outcome,
            "full_stream_delta": delta,
            "baseline_score": baseline_record["weighted_score"],
            "candidate_score": candidate_record["weighted_score"],
            "gate_flips_over_stream": case["gate_flips"],
            "gate_on_placement_share_over_stream": case["gate_on_placement_share"],
            **snapshot,
        })
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    train_base = TRAIN / "baseline-dynamic/runs"
    train_candidate = HERE / "search/train_runs/policy-033/runs"
    train_base_summary = json.loads((TRAIN / "baseline-dynamic/summary.json").read_text())
    train_cand_summary = json.loads((HERE / "search/train_runs/policy-033/summary.json").read_text())
    rows = []
    for rec in train_base_summary["records"]:
        candidate = next(r for r in train_cand_summary["records"] if r["case"] == rec["case"])
        delta = candidate["weighted_score"] - rec["weighted_score"]
        rows.extend(run_case("train", rec["case"], Path(rec["test_file"]), train_base,
                             train_candidate, delta))

    val_base = VALIDATION / "baseline/runs"
    val_candidate = VALIDATION / "tree-033-simplified/runs"
    val_base_summary = json.loads((VALIDATION / "baseline/summary.json").read_text())
    val_cand_summary = json.loads((VALIDATION / "tree-033-simplified/summary.json").read_text())
    for rec in val_base_summary["records"]:
        candidate = next(r for r in val_cand_summary["records"] if r["case"] == rec["case"])
        delta = candidate["weighted_score"] - rec["weighted_score"]
        rows.extend(run_case("validation", rec["case"], Path(rec["test_file"]), val_base,
                             val_candidate, delta))

    columns = list(rows[0])
    with (OUT / "rolling_prefix_features.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    # The selected tree is a gate, not a stream-level classifier. For a cautious
    # early-identifiability check, use only the first saved prefix and predict
    # positive if its observed long-pipe share is at most one half (32/64).
    first_by_stream = {}
    for row in rows:
        key = (row["dataset"], row["stream"])
        if key not in first_by_stream or row["prefix_events"] < first_by_stream[key]["prefix_events"]:
            first_by_stream[key] = row
    counts = {actual: {pred: 0 for pred in ("positive", "not_positive")} for actual in ("positive", "not_positive")}
    per_stream = []
    for (dataset, stream), row in sorted(first_by_stream.items()):
        actual = "positive" if row["outcome"] == "positive" else "not_positive"
        predicted = "positive" if row["tree_gate_on"] else "not_positive"
        counts[actual][predicted] += 1
        per_stream.append({
            "dataset": dataset,
            "stream": stream,
            "outcome": row["outcome"],
            "prefix_events": row["prefix_events"],
            "recent_long_count": row["recent_long_count"],
            "tree_gate_on": row["tree_gate_on"],
            "active_count": row["active_count"],
            "free_gap_count": row["free_gap_count"],
            "recent_delete_share": row["recent_delete_share"],
            "recent_newest_delete_share": row["recent_newest_delete_share"],
            "recent_expansion_share": row["recent_expansion_share"],
            "periodicity_max_eq": row["periodicity_max_eq"],
            "gate_flips_over_stream": row["gate_flips_over_stream"],
            "gate_on_placement_share_over_stream": row["gate_on_placement_share_over_stream"],
            "delta": row["full_stream_delta"],
        })
    report = {
        "purpose": "causal rolling-prefix descriptive check; no classifier trained or fed to solver",
        "policy_outcome_definition": "tree #33 minus baseline full-stream score, for offline labeling only",
        "positive_prediction_rule": "at first causal prefix snapshot, tree gate is on (at most 32 of last 64 placements have length >=21)",
        "confusion_binary_positive_vs_nonpositive": counts,
        "switching_cost_proxy": "number of changes in the same rolling long-count gate over all placements; does not count lost MC decisions",
        "streams": per_stream,
        "limitations": [
            "14 streams are too few to fit or validate a general regime classifier.",
            "Prefix checkpoints are evaluation-only; final solver never reads future commands, stream length, or absolute operation index.",
            "Tree #33 was selected on train data; validation is independent of tree search but this stream-level outcome audit remains small.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
