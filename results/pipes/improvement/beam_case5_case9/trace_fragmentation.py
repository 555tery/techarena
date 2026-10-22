#!/usr/bin/env python3
"""Offline audit of growth events and unusable free gaps in exact traces."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIG = 20
ROOT = Path(__file__).resolve().parents[4]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path: Path):
    values = list(map(int, path.read_text().split()))
    return values[2:2 + values[1]]


def answers(ops, path: Path):
    tokens = list(map(int, path.read_text().split()))
    result = []
    cursor = 0
    for op in ops:
        count = 2 if op > 0 else 1
        result.append(tuple(tokens[cursor:cursor + count]))
        cursor += count
    if cursor != len(tokens):
        raise ValueError(f"answer mismatch: consumed {cursor}, have {len(tokens)}")
    return result


def gap_list(pipes, trench):
    occupied = sorted((start, start + length)
                      for item in pipes[1:] if item is not None
                      for start, length in (item,))
    result = []
    cursor = 0
    for left, right in occupied:
        if left > cursor:
            result.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < trench:
        result.append((cursor, trench))
    return result


def audit(case: int):
    input_path = ROOT / f"data/pipes/open/{case}.in"
    trace_path = ROOT / f"results/pipes/final/open-run-size-cohort-lanes/runs/{case}/judge_output.txt"
    ops = parse(input_path)
    output = answers(ops, trace_path)
    pipes = [None]
    trench = live = 0
    by_length = defaultdict(Counter)
    growth_events = []
    peak_live = 0
    peak_op = 0

    for op_index, (op, answer) in enumerate(zip(ops, output), 1):
        if op > 0:
            digs, start = answer
            gaps = gap_list(pipes, trench)
            free_volume = trench - live
            max_gap = max((right - left for left, right in gaps), default=0)
            stranded = sum(right - left for left, right in gaps
                           if right - left < op)
            row = by_length[op]
            row["placements"] += 1
            if digs:
                growth = digs * DIG
                row["growth_events"] += 1
                row["growth_m"] += growth
                if free_volume >= op and max_gap < op:
                    row["fragmented_growth_events"] += 1
                    row["fragmented_growth_m"] += growth
                row["stranded_free_volume_at_growth_m"] += stranded
                growth_events.append({
                    "op": op_index, "length_m": op, "growth_m": growth,
                    "free_volume_before_m": free_volume,
                    "max_gap_before_m": max_gap,
                    "stranded_gap_volume_before_m": stranded,
                    "gap_count_before": len(gaps),
                })
            trench += growth if digs else 0
            live += op
            pipes.append((start, op))
            if live > peak_live:
                peak_live, peak_op = live, op_index
        else:
            pid = -op
            if 0 < pid < len(pipes) and pipes[pid] is not None:
                live -= pipes[pid][1]
                pipes[pid] = None

    total_growth = sum(item["growth_m"] for item in growth_events)
    fragmented = [item for item in growth_events
                  if item["free_volume_before_m"] >= item["length_m"]
                  and item["max_gap_before_m"] < item["length_m"]]
    return {
        "case": case,
        "input": str(input_path.relative_to(ROOT)),
        "input_sha256": sha256(input_path),
        "judge_output": str(trace_path.relative_to(ROOT)),
        "judge_output_sha256": sha256(trace_path),
        "commands": len(ops),
        "placements": sum(op > 0 for op in ops),
        "deletions": sum(op < 0 for op in ops),
        "peak_live_m": peak_live,
        "peak_live_op": peak_op,
        "final_live_m": live,
        "final_trench_m": trench,
        "total_growth_events": len(growth_events),
        "total_growth_m": total_growth,
        "growth_events_with_free_volume_at_least_request_and_max_gap_too_small": len(fragmented),
        "growth_m_with_free_volume_at_least_request_and_max_gap_too_small": sum(
            item["growth_m"] for item in fragmented),
        "by_length": {str(length): dict(row)
                      for length, row in sorted(by_length.items())},
        "growth_events": growth_events,
    }


def main():
    cases = [int(arg) for arg in sys.argv[1:]] or [5, 9]
    payload = {
        "scope": "offline exact-trace geometry audit; no candidate or platform submission",
        "final_source": "results/pipes/final/solution.cpp",
        "final_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "dig_increment_m": DIG,
        "cases": [audit(case) for case in cases],
    }
    out = Path(__file__).with_name("fragmentation.json")
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(out)
    for case in payload["cases"]:
        print(case["case"], case["total_growth_events"],
              case["growth_events_with_free_volume_at_least_request_and_max_gap_too_small"],
              case["total_growth_m"],
              case["growth_m_with_free_volume_at_least_request_and_max_gap_too_small"])


if __name__ == "__main__":
    main()
