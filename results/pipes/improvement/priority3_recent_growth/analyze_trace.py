#!/usr/bin/env python3
"""Replay an official Pipes input/output pair and explain each trench extension."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

DIG_LENGTH = 20


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def round_up_20(value: int) -> int:
    return ((value + DIG_LENGTH - 1) // DIG_LENGTH) * DIG_LENGTH


def add_gap(gaps: dict[int, int], start: int, end: int) -> None:
    if start >= end:
        return
    keys = sorted(gaps)
    left = 0
    while left < len(keys) and keys[left] < start:
        left += 1
    if left > 0:
        prev = keys[left - 1]
        if gaps[prev] >= start:
            start = prev
            end = max(end, gaps.pop(prev))
    while True:
        next_key = next((k for k in sorted(gaps) if k >= start), None)
        if next_key is None or next_key > end:
            break
        end = max(end, gaps.pop(next_key))
    gaps[start] = end


def top_gap_records(gaps: dict[int, int], pipes: dict[int, tuple[int, int, bool]], limit: int = 6) -> list[dict]:
    active = sorted((s, s + length, pid, length) for pid, (s, length, on) in pipes.items() if on)
    out = []
    for start, end in sorted(gaps.items(), key=lambda p: (-(p[1] - p[0]), p[0]))[:limit]:
        left = next(((pid, length) for ps, pe, pid, length in reversed(active) if pe <= start), None)
        right = next(((pid, length) for ps, pe, pid, length in active if ps >= end), None)
        out.append({
            "start": start,
            "end": end,
            "length": end - start,
            "left_blocker": None if left is None else {"pid": left[0], "length": left[1]},
            "right_blocker": None if right is None else {"pid": right[0], "length": right[1]},
        })
    return out


def analyze(test: Path, output: Path, expected: dict[str, str]) -> tuple[dict, list[dict]]:
    raw = test.read_text().split()
    declared_count = int(raw[1])
    commands = [int(x) for x in raw[2:]]
    if len(commands) == declared_count + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != declared_count:
        raise ValueError(f"declared operation count mismatch in {test}")
    answers = output.read_text().splitlines()
    answer_index = 0
    trench = 0
    pipes: dict[int, tuple[int, int, bool]] = {}
    gaps: dict[int, int] = {}
    pid = 0
    active_volume = 0
    peak_volume = 0
    operation = 0
    dig_total = 0
    growths: list[dict] = []
    for command in commands:
        operation += 1
        if command > 0:
            length = command
            parts = answers[answer_index].split()
            answer_index += 1
            if len(parts) != 2:
                raise ValueError(f"expected 'digs start' at op={operation}, got {parts!r}")
            digs, start = map(int, parts)
            gaps_before = dict(gaps)
            free_before = sum(end - left for left, end in gaps_before.items())
            fitting = sorted(end - left for left, end in gaps_before.items() if end - left >= length)
            max_gap = max((end - left for left, end in gaps_before.items()), default=0)
            tail_start = trench
            tail_length = 0
            if gaps_before:
                last = max(gaps_before)
                if gaps_before[last] == trench:
                    tail_start = last
                    tail_length = trench - last
            expected_digs = 0
            if not fitting:
                deficit = max(0, length - tail_length)
                expected_digs = (deficit + DIG_LENGTH - 1) // DIG_LENGTH
            if digs != expected_digs:
                raise ValueError(f"digs mismatch at case={test.stem}, op={operation}: output={digs}, replay={expected_digs}")

            if digs:
                old_trench = trench
                new_trench = trench + digs * DIG_LENGTH
                live_before = active_volume
                fitting_sizes = sorted((end - left for left, end in gaps_before.items()), reverse=True)
                growths.append({
                    "case": int(test.stem),
                    "operation": operation,
                    "pid_being_placed": pid + 1,
                    "pipe_length": length,
                    "digs": digs,
                    "before_trench_m": old_trench,
                    "after_trench_m": new_trench,
                    "tail_start_m": tail_start,
                    "tail_gap_before_m": tail_length,
                    "free_volume_before_m": free_before,
                    "largest_gap_before_m": max_gap,
                    "gap_count_before": len(gaps_before),
                    "fitting_gap_lengths_before_m": fitting,
                    "largest_gap_lengths_before_m": fitting_sizes[:8],
                    "fragmentation_or_capacity": "fragmentation_with_enough_total_free" if free_before >= length else "free_volume_shortfall",
                    "live_volume_after_placement_m": live_before + length,
                    "volume_lb_after_placement_m": round_up_20(live_before + length),
                    "headroom_after_growth_vs_live_lb_m": new_trench - round_up_20(live_before + length),
                    "largest_free_fragments": top_gap_records(gaps_before, pipes),
                })
                if tail_length:
                    gaps.pop(tail_start)
                trench = new_trench
                if start != tail_start:
                    raise ValueError(f"growth placement not at tail start at op={operation}: {start} != {tail_start}")
                add_gap(gaps, start + length, trench)
                dig_total += digs
            else:
                owner = next(((gstart, gend) for gstart, gend in gaps.items() if gstart <= start and start + length <= gend), None)
                if owner is None:
                    raise ValueError(f"placement not covered by free span at op={operation}: [{start},{start + length})")
                gstart, gend = owner
                gaps.pop(gstart)
                add_gap(gaps, gstart, start)
                add_gap(gaps, start + length, gend)
            pid += 1
            pipes[pid] = (start, length, True)
            active_volume += length
            peak_volume = max(peak_volume, active_volume)
        else:
            remove_pid = -command
            if remove_pid not in pipes or not pipes[remove_pid][2]:
                raise ValueError(f"invalid removal pid={remove_pid} at op={operation}")
            actual_start = int(answers[answer_index].split()[0])
            answer_index += 1
            start, length, _ = pipes[remove_pid]
            if actual_start != start:
                raise ValueError(f"removal location mismatch at op={operation}: output={actual_start}, replay={start}")
            pipes[remove_pid] = (start, length, False)
            active_volume -= length
            add_gap(gaps, start, start + length)

    if answer_index != len(answers):
        raise ValueError(f"unused judge outputs: consumed={answer_index} total={len(answers)}")
    final_volume = sum(length for _, length, on in pipes.values() if on)
    if final_volume != active_volume:
        raise ValueError("active volume mismatch")
    lower_bound = round_up_20(peak_volume)
    surplus = trench - lower_bound
    if surplus < 0 or surplus % DIG_LENGTH:
        raise ValueError(f"invalid lower-bound difference: trench={trench}, lb={lower_bound}")
    for event in growths:
        overlap = max(0, min(event["after_trench_m"], trench) - max(event["before_trench_m"], lower_bound))
        event["final_excess_sections_attributed"] = overlap // DIG_LENGTH
    contributing = [x for x in growths if x["final_excess_sections_attributed"] > 0]
    latest = contributing[-3:]
    record = {
        "case": int(test.stem),
        "test_sha256": sha(test),
        "judge_output_sha256": sha(output),
        "operation_count": operation,
        "placement_count": pid,
        "dig_sections": dig_total,
        "growth_event_count": len(growths),
        "peak_live_volume_m": peak_volume,
        "live_volume_lower_bound_m": lower_bound,
        "final_occupied_length_m": final_volume,
        "final_trench_m": trench,
        "excess_sections_over_lb": surplus // DIG_LENGTH,
        "excess_m_over_lb": surplus,
        "last_growths_contributing_to_final_excess": [
            {k: x[k] for k in (
                "operation", "pid_being_placed", "pipe_length", "digs", "before_trench_m", "after_trench_m",
                "tail_gap_before_m", "free_volume_before_m", "largest_gap_before_m", "gap_count_before",
                "fragmentation_or_capacity", "live_volume_after_placement_m", "volume_lb_after_placement_m",
                "headroom_after_growth_vs_live_lb_m", "final_excess_sections_attributed", "fitting_gap_lengths_before_m",
                "largest_gap_lengths_before_m", "largest_free_fragments")}
            for x in latest
        ],
        "status": expected.get("status", "unknown"),
        "official_weight": float(expected.get("official_weight", 0)),
        "kpi": float(expected.get("kpi", 0)),
        "weighted_score": float(expected.get("weighted_score", 0)),
        "solver_cpu_total_s": float(expected.get("solver_cpu_total_s", 0)),
        "solver_peak_rss_mb": float(expected.get("solver_peak_rss_mb", 0)),
    }
    return record, growths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with (args.runs / "cases.csv").open(newline="") as stream:
        expected = {row["case"]: row for row in csv.DictReader(stream)}
    case_records = []
    growth_records = []
    for test in sorted(args.tests.glob("*.in"), key=lambda p: int(p.stem)):
        row = expected[test.stem]
        output = Path(row["judge_output_file"])
        if not output.is_absolute():
            output = Path.cwd() / output
        record, growths = analyze(test, output, row)
        if record["final_trench_m"] != int(row["trench_length_m"]):
            raise ValueError(f"trench mismatch for case {test.stem}")
        if record["live_volume_lower_bound_m"] != int(row["minimum_trench_lower_bound_m"]):
            raise ValueError(f"lower bound mismatch for case {test.stem}")
        if record["final_occupied_length_m"] != int(row["occupied_length_m"]):
            raise ValueError(f"occupied mismatch for case {test.stem}")
        case_records.append(record)
        growth_records.extend(growths)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "trace_diagnosis.json").write_text(json.dumps(case_records, indent=2, ensure_ascii=False) + "\n")
    (args.out / "growth_events.json").write_text(json.dumps(growth_records, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps([
        {k: r[k] for k in ("case", "final_trench_m", "live_volume_lower_bound_m", "excess_sections_over_lb", "excess_m_over_lb", "growth_event_count", "dig_sections")}
        for r in case_records
    ], ensure_ascii=False))


if __name__ == "__main__":
    main()
