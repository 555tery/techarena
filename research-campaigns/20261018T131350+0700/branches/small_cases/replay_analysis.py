#!/usr/bin/env python3
"""Replay a saved interactive response transcript to diagnose trench growth.

This is an offline, post-hoc analyzer. It is not linked to the solver and its
full input is never available to candidate code.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gaps(trench: int, active: dict[int, tuple[int, int]]) -> list[dict]:
    spans = sorted((start, start + length, pid, length)
                   for pid, (start, length) in active.items())
    out: list[dict] = []
    cursor = 0
    left_pid = None
    left_length = None
    for start, end, pid, length in spans:
        if start > cursor:
            out.append({"start": cursor, "end": start,
                        "left_pid": left_pid, "left_length": left_length,
                        "right_pid": pid, "right_length": length})
        cursor = max(cursor, end)
        left_pid = pid
        left_length = length
    if cursor < trench:
        out.append({"start": cursor, "end": trench,
                    "left_pid": left_pid, "left_length": left_length,
                    "right_pid": None, "right_length": None})
    return out


def analyze(input_path: Path, transcript_path: Path) -> dict:
    raw_input = input_path.read_text().split()
    if len(raw_input) < 2:
        raise ValueError("input has no header")
    weight, command_count = map(int, raw_input[:2])
    commands = list(map(int, raw_input[2:]))
    if len(commands) == command_count + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != command_count:
        raise ValueError(f"header says {command_count} operations, found {len(commands)}")

    answers = list(map(int, transcript_path.read_text().split()))
    deletion_at = {(-command): operation for operation, command in enumerate(commands, 1)
                   if command < 0}
    answer_at = 0
    active: dict[int, tuple[int, int]] = {}
    trench = 0
    live_volume = 0
    peak_live = 0
    placements = 0
    growth_events: list[dict] = []
    recent_events: list[dict] = []
    growth_steps = 0

    for operation, command in enumerate(commands, start=1):
        if command > 0:
            if answer_at + 2 > len(answers):
                raise ValueError(f"transcript ends before placement {operation}")
            digs, start = answers[answer_at:answer_at + 2]
            answer_at += 2
            length = command
            old_trench = trench
            old_gaps = gaps(trench, active)
            gap_lengths = [gap["end"] - gap["start"] for gap in old_gaps]
            free_before = sum(gap_lengths)
            largest_before = max(gap_lengths, default=0)
            fitting_before = sum(gap_length >= length for gap_length in gap_lengths)
            tail_before = old_gaps[-1]["end"] - old_gaps[-1]["start"] \
                if old_gaps and old_gaps[-1]["end"] == trench else 0
            peak_live_before = peak_live
            trench += 20 * digs
            if start < 0 or start + length > trench:
                raise ValueError(f"invalid placement coordinates at operation {operation}")
            for other_start, other_length in active.values():
                if max(start, other_start) < min(start + length, other_start + other_length):
                    raise ValueError(f"overlap at operation {operation}")
            placements += 1
            active[placements] = (start, length)
            live_volume += length
            peak_live = max(peak_live, live_volume)
            event = {
                "operation": operation,
                "pid": placements,
                "request_m": length,
                "digs": digs,
                "trench_before_m": old_trench,
                "trench_after_m": trench,
                "active_before": len(active) - 1,
                "peak_live_before_m": peak_live_before,
                "free_before_m": free_before,
                "free_gap_count_before": len(old_gaps),
                "largest_gap_before_m": largest_before,
                "fitting_gaps_before": fitting_before,
                "tail_gap_before_m": tail_before,
                "free_ge_request": free_before >= length,
                "largest_gap_lt_request": largest_before < length,
            }
            recent_events.append(event)
            if len(recent_events) > 32:
                recent_events.pop(0)
            if digs:
                growth_steps += digs
                event["growth_step_index"] = growth_steps
                active_before_pids = sorted(
                    (pid for pid in active if pid != placements), reverse=True)
                age_rank = {pid: rank for rank, pid in enumerate(active_before_pids)}
                contextual_gaps = []
                for gap in old_gaps:
                    gap_length = gap["end"] - gap["start"]
                    if gap_length >= length:
                        continue
                    context = {"gap_m": gap_length}
                    for side in ("left", "right"):
                        pid = gap[f"{side}_pid"]
                        pipe_length = gap[f"{side}_length"]
                        if pid is None:
                            context[f"{side}_blocker"] = None
                            continue
                        rank = age_rank[pid]
                        denominator = max(1, len(active_before_pids) - 1)
                        future_delete = deletion_at.get(pid)
                        context[f"{side}_blocker"] = {
                            "pid": pid,
                            "length_m": pipe_length,
                            "rank_from_newest": rank,
                            "rank_permille": rank * 1000 // denominator,
                            "future_delete_delay_commands":
                                None if future_delete is None else future_delete - operation,
                            "gap_if_deleted_m": gap_length + pipe_length,
                        }
                    contextual_gaps.append(context)
                contextual_gaps.sort(key=lambda entry: entry["gap_m"], reverse=True)
                event["near_fit_gaps"] = contextual_gaps[:12]
                event["free_gap_length_histogram"] = {
                    str(gap_length): count
                    for gap_length, count in sorted(Counter(gap_lengths).items())
                }
                event["classification"] = (
                    "fragmentation" if free_before >= length and largest_before < length
                    else "volume_shortage" if free_before < length
                    else "unexpected_fitting_gap"
                )
                event["recent_32_placements"] = [
                    {key: prior[key] for key in
                     ("operation", "request_m", "digs", "trench_after_m", "free_before_m",
                      "largest_gap_before_m", "active_before")}
                    for prior in recent_events[:-1] if prior["digs"] or prior["request_m"] == length
                ][-12:]
                event["input_commands_before_growth"] = commands[max(0, operation - 32):operation]
                growth_events.append(event)
        elif command < 0:
            if answer_at >= len(answers):
                raise ValueError(f"transcript ends before deletion {operation}")
            pid = -command
            if pid not in active:
                raise ValueError(f"deletion references inactive PID {pid} at operation {operation}")
            returned_start = answers[answer_at]
            answer_at += 1
            start, length = active.pop(pid)
            if returned_start != start:
                raise ValueError(f"deletion response mismatch at operation {operation}")
            live_volume -= length

    if answer_at != len(answers):
        raise ValueError(f"transcript has {len(answers) - answer_at} unused integer responses")

    return {
        "input": str(input_path),
        "input_sha256": sha256(input_path),
        "transcript": str(transcript_path),
        "transcript_sha256": sha256(transcript_path),
        "weight": weight,
        "operation_count": command_count,
        "placements": placements,
        "final_active_count": len(active),
        "final_live_volume_m": live_volume,
        "peak_live_volume_m": peak_live,
        "lower_bound_m": ((peak_live + 19) // 20) * 20,
        "final_trench_m": trench,
        "growth_step_count": growth_steps,
        "growth_event_count": len(growth_events),
        "growth_events": growth_events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input, args.transcript)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "input_sha256", "transcript_sha256", "operation_count", "final_trench_m",
        "lower_bound_m", "growth_step_count", "growth_event_count")}, indent=2))


if __name__ == "__main__":
    main()
