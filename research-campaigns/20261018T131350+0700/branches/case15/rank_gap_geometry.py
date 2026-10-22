#!/usr/bin/env python3
"""Hindsight-only geometry audit of ordinally close short-pipe neighbors."""
from __future__ import annotations

import bisect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN = ROOT / "research-campaigns/20261018T131350+0700"
INPUT = ROOT / "data/pipes/open/15.in"
OUTPUT = CAMPAIGN / "evaluations/baseline-open15/harness/runs/15/judge_output.txt"
OUT = Path(__file__).resolve().parent / "rank-gap-geometry.json"


def main() -> None:
    tokens = INPUT.read_text().split()
    weight, operation_count = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    responses = [int(x) for x in OUTPUT.read_text().split()]
    if len(commands) != operation_count + 1 or commands[-1] != 0:
        raise RuntimeError("unexpected input shape")

    bit = [0] * (operation_count + 2)
    active_by_start: list[tuple[int, int]] = []
    start_by_pid = [0]
    length_by_pid = [0]
    birth_op = [0]
    death_op = [None]
    pid = 0
    active_count = 0
    response_at = 0
    placement_events = []

    def add(index: int, delta: int) -> None:
        while index < len(bit):
            bit[index] += delta
            index += index & -index

    def prefix(index: int) -> int:
        value = 0
        while index > 0:
            value += bit[index]
            index -= index & -index
        return value

    for op, command in enumerate(commands[:-1], start=1):
        if command > 0:
            digs, start = responses[response_at : response_at + 2]
            response_at += 2
            idx = bisect.bisect_left(active_by_start, (start, -1))
            left = active_by_start[idx - 1] if idx else None
            right = active_by_start[idx] if idx < len(active_by_start) else None
            if left and left[0] + length_by_pid[left[1]] > start:
                raise RuntimeError(f"overlap left of placement at op {op}")
            if right and start + command > right[0]:
                raise RuntimeError(f"overlap right of placement at op {op}")

            if left and right and command >= 8 and \
                    length_by_pid[left[1]] <= 7 and length_by_pid[right[1]] <= 7:
                left_rank = active_count - prefix(left[1])
                right_rank = active_count - prefix(right[1])
                left_rel = left_rank / max(1, active_count - 1)
                right_rel = right_rank / max(1, active_count - 1)
                placement_events.append({
                    "op": op,
                    "pid": pid + 1,
                    "length": command,
                    "start": start,
                    "digs": digs,
                    "gap_length": right[0] - (left[0] + length_by_pid[left[1]]),
                    "left_pid": left[1],
                    "right_pid": right[1],
                    "left_length": length_by_pid[left[1]],
                    "right_length": length_by_pid[right[1]],
                    "left_relative_rank_from_newest": left_rel,
                    "right_relative_rank_from_newest": right_rel,
                    "rank_distance": abs(left_rel - right_rel),
                    "same_active_rank_quintile": int(left_rel * 5) == int(right_rel * 5),
                    "same_fixed_birth_band_20k": (left[1] - 1) // 20_000 ==
                                                    (right[1] - 1) // 20_000,
                })

            pid += 1
            active_count += 1
            start_by_pid.append(start)
            length_by_pid.append(command)
            birth_op.append(op)
            death_op.append(None)
            add(pid, 1)
            bisect.insort(active_by_start, (start, pid))
        elif command < 0:
            removed = -command
            shift = responses[response_at]
            response_at += 1
            if shift != start_by_pid[removed]:
                raise RuntimeError(f"answer and input disagree at deletion op {op}")
            idx = bisect.bisect_left(active_by_start, (shift, removed))
            if idx >= len(active_by_start) or active_by_start[idx] != (shift, removed):
                raise RuntimeError(f"deleted pipe not active at op {op}")
            active_by_start.pop(idx)
            add(removed, -1)
            active_count -= 1
            death_op[removed] = op

    if response_at != len(responses):
        raise RuntimeError("unconsumed answer tokens")

    for event in placement_events:
        left_death = death_op[event["left_pid"]]
        right_death = death_op[event["right_pid"]]
        blocker_death = death_op[event["pid"]]
        boundary_deaths = [x for x in (left_death, right_death) if x is not None]
        event["both_boundaries_delete_eventually"] = len(boundary_deaths) == 2
        event["both_delete_before_blocker"] = (
            len(boundary_deaths) == 2 and
            (blocker_death is None or max(boundary_deaths) < blocker_death))
        event["both_delete_within_20k_after_placement"] = (
            len(boundary_deaths) == 2 and
            max(boundary_deaths) - event["op"] <= 20_000)
        event["same_pid_band_and_both_delete_before_blocker"] = (
            event["same_fixed_birth_band_20k"] and event["both_delete_before_blocker"])

    selected = [e for e in placement_events if e["op"] >= 100_000]
    close_rank = [e for e in selected if e["rank_distance"] <= .05]
    result = {
        "input": str(INPUT),
        "baseline_output": str(OUTPUT),
        "weight": weight,
        "scope": "read-only public Open15 case-15 geometry; future deletion fields are diagnostic hindsight only",
        "placement_events": len(placement_events),
        "second_half_events": len(selected),
        "second_half_boundary_rank_distance_le_5pct": len(close_rank),
        "second_half_both_boundaries_delete_before_blocker": sum(
            e["both_delete_before_blocker"] for e in selected),
        "second_half_rank_close_and_both_delete_before_blocker": sum(
            e["rank_distance"] <= .05 and e["both_delete_before_blocker"] for e in selected),
        "second_half_same_20k_birth_band_and_both_delete_before_blocker": sum(
            e["same_pid_band_and_both_delete_before_blocker"] for e in selected),
        "second_half_both_delete_within_20k": sum(
            e["both_delete_within_20k_after_placement"] for e in selected),
        "events": placement_events,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "events"}, indent=2))


if __name__ == "__main__":
    main()
