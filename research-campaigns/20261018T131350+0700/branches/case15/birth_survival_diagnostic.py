#!/usr/bin/env python3
"""Read-only birth-time feature analysis for the public case-15 request trace.

Features are computed only from information available at each allocation birth.
Deletion outcomes and future insert-run length are retrospective labels for
diagnosis; they must never be copied into a solver policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("/Users/555tery/techarena/data/pipes/open/15.in")
DEFAULT_OUT = Path(__file__).resolve().parent / "birth-survival-diagnostic.json"
HORIZONS = (100, 1_000, 5_000, 20_000)


def bucket_length(length: int) -> str:
    if length == 1:
        return "1"
    if length <= 3:
        return "2-3"
    if length <= 7:
        return "4-7"
    if length <= 15:
        return "8-15"
    if length <= 31:
        return "16-31"
    return "32+"


def bucket_streak(position: int) -> str:
    if position <= 3:
        return str(position)
    if position <= 7:
        return "4-7"
    return "8+"


def bucket_pid_distance(distance: int | None) -> str:
    if distance is None:
        return "no-prior-delete"
    if distance <= 1:
        return "1"
    if distance <= 4:
        return "2-4"
    if distance <= 16:
        return "5-16"
    if distance <= 64:
        return "17-64"
    return "65+"


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(records)
    result: dict[str, Any] = {"n": n}
    if not n:
        return result
    deleted = [r for r in records if r["deleted_by_eof"]]
    result["deleted_by_eof"] = len(deleted)
    result["p_deleted_by_eof"] = len(deleted) / n
    for horizon in HORIZONS:
        eligible = [r for r in records if r["remaining_ops"] >= horizon]
        hits = sum(r["time_to_delete"] is not None and r["time_to_delete"] <= horizon for r in eligible)
        result[f"n_complete_{horizon}"] = len(eligible)
        result[f"deleted_within_{horizon}"] = hits
        result[f"p_deleted_within_{horizon}"] = hits / len(eligible) if eligible else None
    return result


def grouped(records: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        cells[str(record[feature])].append(record)
    return {key: summarise(items) for key, items in sorted(cells.items())}


def cross_grouped(records: list[dict[str, Any]], first: str, second: str) -> dict[str, Any]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        cells[f"{record[first]} | {record[second]}"].append(record)
    return {key: summarise(items) for key, items in sorted(cells.items())}


def triple_grouped(records: list[dict[str, Any]], first: str, second: str, third: str,
                   minimum_n: int = 1) -> dict[str, Any]:
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = f"{record[first]} | {record[second]} | {record[third]}"
        cells[key].append(record)
    return {key: summarise(items) for key, items in sorted(cells.items()) if len(items) >= minimum_n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    raw = args.input.read_bytes()
    input_sha256 = hashlib.sha256(raw).hexdigest()
    tokens = raw.split()
    if len(tokens) < 3:
        raise RuntimeError("input is too short")
    weight, operation_count = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    if len(commands) != operation_count + 1 or commands[-1] != 0:
        raise RuntimeError("unexpected input shape or missing terminal zero")

    births: list[dict[str, Any] | None] = [None]
    latest_pid = 0
    last_deleted_pid: int | None = None
    previous_kind = "start"
    current_streak = 0
    streak_id = 0
    streak_sizes: Counter[int] = Counter()

    # Only the first operation_count commands are operations; final zero ends input.
    for op, command in enumerate(commands[:operation_count], start=1):
        if command > 0:
            if previous_kind == "insert":
                current_streak += 1
            else:
                current_streak = 1
                streak_id += 1
            latest_pid += 1
            distance = None if last_deleted_pid is None else latest_pid - last_deleted_pid
            if distance is not None and distance <= 0:
                raise RuntimeError(f"unexpected nonpositive PID distance at operation {op}")
            item = {
                "pid": latest_pid,
                "birth_op": op,
                "length": command,
                "length_bucket": bucket_length(command),
                "streak_position": current_streak,
                "streak_position_bucket": bucket_streak(current_streak),
                "streak_id": streak_id,
                "distance_from_last_deleted_pid": distance,
                "last_delete_pid_distance_bucket": bucket_pid_distance(distance),
                "preceding_op": previous_kind,
                "death_op": None,
            }
            births.append(item)
            streak_sizes[streak_id] += 1
            previous_kind = "insert"
        elif command < 0:
            pid = -command
            if pid <= 0 or pid > latest_pid or births[pid] is None:
                raise RuntimeError(f"invalid deletion at operation {op}: PID {pid}")
            item = births[pid]
            assert item is not None
            if item["death_op"] is not None:
                raise RuntimeError(f"duplicate deletion for PID {pid}")
            item["death_op"] = op
            last_deleted_pid = pid
            previous_kind = "delete"
            current_streak = 0
        else:
            raise RuntimeError(f"unexpected zero before terminal operation: {op}")

    records: list[dict[str, Any]] = []
    for item in births[1:]:
        assert item is not None
        birth_op = item["birth_op"]
        death_op = item["death_op"]
        remaining = operation_count - birth_op
        record = dict(item)
        record["remaining_ops"] = remaining
        record["deleted_by_eof"] = death_op is not None
        record["time_to_delete"] = None if death_op is None else death_op - birth_op
        record["birth_operation_quartile_diagnostic_only"] = min(4, ((birth_op - 1) * 4) // operation_count + 1)
        record["future_total_insert_run_length_diagnostic_only"] = streak_sizes[item["streak_id"]]
        records.append(record)

    # The whole-run position uses future insertions and is deliberately marked hindsight.
    for record in records:
        run_length = record["future_total_insert_run_length_diagnostic_only"]
        position = record["streak_position"]
        if run_length == 1:
            position_label = "singleton"
        elif position == 1:
            position_label = "first"
        elif position == run_length:
            position_label = "last"
        else:
            position_label = "middle"
        record["completed_run_position_diagnostic_only"] = position_label

    result = {
        "input": str(args.input),
        "input_sha256": input_sha256,
        "weight": weight,
        "operations": operation_count,
        "placements": latest_pid,
        "horizons_ops_after_birth": list(HORIZONS),
        "definitions": {
            "preceding_op": "immediately preceding request operation, available at birth",
            "streak_position_bucket": "number of consecutive positive requests through this birth, available at birth",
            "last_delete_pid_distance_bucket": "new PID minus the PID deleted by the most recent earlier delete, available at birth; ordinal distance, not time",
            "deleted_by_eof": "retrospective outcome; an allocation still live at end is right-censored for eventual-lifetime inference",
            "p_deleted_within_H": "deletion occurs within H following operations; denominator includes only births with at least H operations of follow-up",
            "completed_run_position_diagnostic_only": "first/middle/last/singleton uses the future completed insert run; hindsight diagnostic only, never an online feature",
            "birth_operation_quartile_diagnostic_only": "retrospective quartile of the full declared operation horizon; descriptive control for nonstationarity, not a policy feature",
        },
        "overall": summarise(records),
        "deletion_share_by_length": {
            key: {
                **summary,
                "share_of_all_deletions": summary["deleted_by_eof"] / sum(r["deleted_by_eof"] for r in records),
            }
            for key, summary in grouped(records, "length_bucket").items()
        },
        "by_birth_time_feature": {
            "length": grouped(records, "length_bucket"),
            "consecutive_insert_position": grouped(records, "streak_position_bucket"),
            "preceding_operation": grouped(records, "preceding_op"),
            "distance_from_last_deleted_pid": grouped(records, "last_delete_pid_distance_bucket"),
            "future_completed_run_position_diagnostic_only": grouped(records, "completed_run_position_diagnostic_only"),
            "birth_operation_quartile_diagnostic_only": grouped(records, "birth_operation_quartile_diagnostic_only"),
        },
        "interactions": {
            "length_x_birth_operation_quartile_diagnostic_only": cross_grouped(records, "length_bucket", "birth_operation_quartile_diagnostic_only"),
            "birth_operation_quartile_x_streak_position_diagnostic_only": cross_grouped(records, "birth_operation_quartile_diagnostic_only", "streak_position_bucket"),
            "birth_operation_quartile_x_preceding_operation_diagnostic_only": cross_grouped(records, "birth_operation_quartile_diagnostic_only", "preceding_op"),
            "birth_operation_quartile_x_last_deleted_pid_distance_diagnostic_only": cross_grouped(records, "birth_operation_quartile_diagnostic_only", "last_delete_pid_distance_bucket"),
            "length_x_birth_operation_quartile_x_streak_position_diagnostic_only": triple_grouped(records, "length_bucket", "birth_operation_quartile_diagnostic_only", "streak_position_bucket", minimum_n=50),
            "length_x_birth_operation_quartile_x_preceding_operation_diagnostic_only": triple_grouped(records, "length_bucket", "birth_operation_quartile_diagnostic_only", "preceding_op", minimum_n=50),
            "length_x_birth_operation_quartile_x_last_deleted_pid_distance_diagnostic_only": triple_grouped(records, "length_bucket", "birth_operation_quartile_diagnostic_only", "last_delete_pid_distance_bucket", minimum_n=50),
            "length_x_consecutive_insert_position": cross_grouped(records, "length_bucket", "streak_position_bucket"),
            "length_x_preceding_operation": cross_grouped(records, "length_bucket", "preceding_op"),
            "length_x_last_deleted_pid_distance": cross_grouped(records, "length_bucket", "last_delete_pid_distance_bucket"),
        },
        "scope": "read-only retrospective diagnosis from the public Open15 case-15 request trace; no solver ran; no validation/holdout or platform data used; outcomes and future-run labels are not deployable signals",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.out),
        "input_sha256": input_sha256,
        "placements": latest_pid,
        "overall": result["overall"],
        "deletion_share_by_length": {
            key: {k: v[k] for k in ("n", "deleted_by_eof", "p_deleted_by_eof", "share_of_all_deletions", "p_deleted_within_20000")}
            for key, v in result["deletion_share_by_length"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
