#!/usr/bin/env python3
"""Replay saved online solver transcripts to quantify deletion neighborhoods."""

import bisect
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
CASES = (5, 9)
RUN_ROOT = REPO / "results/pipes/final/open-run-alternating-delete-parity/runs"
INPUT_ROOT = REPO / "data/pipes/open"
OUT = ROOT / "analysis"
OUT.mkdir(parents=True, exist_ok=True)


def coalesce(gaps, start, end):
    """Insert and merge [start,end); return lengths of adjacent gaps consumed."""
    starts = sorted(gaps)
    pos = bisect.bisect_left(starts, start)
    merged_starts = []
    merged_lengths = []
    if pos and gaps[starts[pos - 1]] >= start:
        left = starts[pos - 1]
        merged_starts.append(left)
        merged_lengths.append(gaps[left] - left)
        start = left
        end = max(end, gaps[left])
    i = bisect.bisect_left(starts, start)
    while i < len(starts) and starts[i] <= end:
        s = starts[i]
        if s not in merged_starts:
            merged_starts.append(s)
            merged_lengths.append(gaps[s] - s)
        end = max(end, gaps[s])
        i += 1
    for s in merged_starts:
        del gaps[s]
    gaps[start] = end
    return merged_lengths, end - start


def replay(case):
    tokens = list(map(int, (INPUT_ROOT / f"{case}.in").read_text().split()))
    weight, n = tokens[:2]
    commands = tokens[2:]
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    assert len(commands) == n
    responses = (RUN_ROOT / str(case) / "judge_output.txt").read_text().splitlines()
    assert len(responses) == n, (case, len(responses), n)

    pipes = [None]
    active_starts = []
    active_at_start = {}
    free_gaps = {}
    trench = 0
    last_deleted_pid = None
    events = []
    stages = []
    current_stage = None
    last_place_length = None

    for op, (command, response) in enumerate(zip(commands, responses), start=1):
        if command > 0:
            if command != last_place_length:
                if current_stage is not None:
                    stages.append(current_stage)
                current_stage = {
                    "case": case, "length": command, "first_placement_op": op,
                    "placements": 0, "deletions": 0, "freed_length": 0,
                    "merged_with_left_gap_events": 0, "merged_with_right_gap_events": 0,
                    "multi_gap_merges": 0, "max_merge_length": 0,
                    "max_free_gap_before_deletion": 0, "pid_step_2_deletes": 0,
                    "deleted_coordinate_span": 0,
                }
                last_place_length = command
            digs, start = map(int, response.split())
            old_trench = trench
            trench += digs * 20
            if trench > old_trench:
                # Newly dug tail is free before consuming this placement.
                free_gaps[old_trench] = trench
            end = start + command
            containing = None
            for gap_start in sorted(free_gaps):
                if gap_start <= start and end <= free_gaps[gap_start]:
                    containing = gap_start
                    break
            if containing is not None:
                gap_end = free_gaps.pop(containing)
                if containing < start:
                    free_gaps[containing] = start
                if end < gap_end:
                    free_gaps[end] = gap_end
            elif start + command > trench:
                raise AssertionError((case, op, start, command, trench))
            pid = len(pipes)
            pipes.append({"pid": pid, "length": command, "start": start,
                          "end": end, "active": True, "removed_op": None})
            bisect.insort(active_starts, start)
            active_at_start[start] = pid
            current_stage["placements"] += 1
            events.append({"case": case, "op": op, "kind": "place", "pid": pid,
                           "length": command, "start": start, "end": end,
                           "neighbor_left_pid": "", "neighbor_right_pid": "",
                           "left_free_len": 0, "right_free_len": 0,
                           "merged_gap_count": 0, "merged_len": 0,
                           "deletion_rank_step": ""})
        else:
            pid = -command
            pipe = pipes[pid]
            assert pipe and pipe["active"], (case, op, pid)
            start, end = pipe["start"], pipe["end"]
            slot = bisect.bisect_left(active_starts, start)
            left_pid = active_at_start[active_starts[slot - 1]] if slot else None
            right_pid = active_at_start[active_starts[slot + 1]] if slot + 1 < len(active_starts) else None
            left_neighbor = left_pid if left_pid and pipes[left_pid]["end"] == start else None
            right_neighbor = right_pid if right_pid and pipes[right_pid]["start"] == end else None
            left_free_len = 0
            right_free_len = 0
            for gap_start, gap_end in free_gaps.items():
                if gap_end == start:
                    left_free_len = gap_end - gap_start
                if gap_start == end:
                    right_free_len = gap_end - gap_start
            max_free_before = max((b - a for a, b in free_gaps.items()), default=0)
            adjacent_old, merged_len = coalesce(free_gaps, start, end)
            trench_from_response = int(response)
            assert trench_from_response == start, (case, op, pid, response, start)
            pipe["active"] = False
            pipe["removed_op"] = op
            del active_at_start[start]
            active_starts.pop(slot)
            if current_stage is None:
                raise AssertionError("deletion before first placement")
            current_stage["deletions"] += 1
            current_stage["freed_length"] += pipe["length"]
            current_stage["merged_with_left_gap_events"] += int(left_free_len > 0)
            current_stage["merged_with_right_gap_events"] += int(right_free_len > 0)
            current_stage["multi_gap_merges"] += int(len(adjacent_old) >= 2)
            current_stage["max_merge_length"] = max(current_stage["max_merge_length"], merged_len)
            current_stage["max_free_gap_before_deletion"] = max(
                current_stage["max_free_gap_before_deletion"], max_free_before)
            step = pid - last_deleted_pid if last_deleted_pid is not None else ""
            last_deleted_pid = pid
            if step == 2:
                current_stage["pid_step_2_deletes"] += 1
            events.append({"case": case, "op": op, "kind": "delete", "pid": pid,
                           "length": pipe["length"], "start": start, "end": end,
                           "neighbor_left_pid": left_neighbor or "",
                           "neighbor_right_pid": right_neighbor or "",
                           "left_free_len": left_free_len, "right_free_len": right_free_len,
                           "merged_gap_count": len(adjacent_old), "merged_len": merged_len,
                           "deletion_rank_step": step})

    if current_stage is not None:
        stages.append(current_stage)
    return weight, trench, events, stages


all_events = []
all_stages = []
case_rows = []
for case in CASES:
    weight, trench, events, stages = replay(case)
    all_events.extend(events)
    all_stages.extend(stages)
    case_rows.append({"case": case, "weight": weight, "operations": len(events),
                      "deletions": sum(e["kind"] == "delete" for e in events),
                      "trench_m": trench})

for filename, rows in (("historical_neighbor_events.csv", all_events),
                       ("neighbor_stage_summary.csv", all_stages),
                       ("neighbor_cases.csv", case_rows)):
    if not rows:
        continue
    with (OUT / filename).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

payload = {"source": "saved current-final official judge transcripts",
           "cases": case_rows, "stages": all_stages}
(OUT / "neighbor_summary.json").write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps(case_rows, indent=2))
