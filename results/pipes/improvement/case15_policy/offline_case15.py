#!/usr/bin/env python3
"""Small offline-only beam diagnostic on exact prefixes of official case 15.

The oracle receives the full future deletion schedule inside each prefix. It is
diagnostic only and is never included in the online candidate.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DIG = 20


@dataclass(frozen=True)
class State:
    trench: int
    placements: tuple[tuple[int, int], ...]  # keep coordinates after deletion
    alive: tuple[bool, ...]


def gaps(state: State):
    items = sorted((start, start + length) for pid, (start, length)
                   in enumerate(state.placements[1:], 1) if state.alive[pid])
    result = []
    cursor = 0
    for start, end in items:
        if start > cursor:
            result.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < state.trench:
        result.append((cursor, state.trench))
    return result


def add_actions(state: State, length: int):
    free = gaps(state)
    actions = set()
    fitting = [(left, right) for left, right in free if right - left >= length]
    if fitting:
        for left, right in fitting:
            actions.add((left, state.trench))
            actions.add((right - length, state.trench))
    else:
        tail_left = free[-1][0] if free and free[-1][1] == state.trench else state.trench
        tail_len = state.trench - tail_left
        new_trench = state.trench + max(0, math.ceil((length - tail_len) / DIG)) * DIG
        actions.add((tail_left, new_trench))
        actions.add((new_trench - length, new_trench))
    pid = len(state.placements)
    result = []
    for start, new_trench in actions:
        result.append(State(new_trench,
                            state.placements + ((start, length),),
                            state.alive + (True,)))
    return result


def delete(state: State, pid: int):
    if pid <= 0 or pid >= len(state.alive) or not state.alive[pid]:
        return state
    alive = list(state.alive)
    alive[pid] = False
    return State(state.trench, state.placements, tuple(alive))


def future_gap_stats(state: State, removed: set[int]):
    projected = state
    for pid in sorted(removed):
        projected = delete(projected, pid)
    gs = gaps(projected)
    return {
        "future_max_gap_m": max((b - a for a, b in gs), default=0),
        "future_gap_count": len(gs),
        "future_total_free_m": sum(b - a for a, b in gs),
        "future_tail_m": next((b - a for a, b in reversed(gs)
                                if b == projected.trench), 0),
    }


def cohort_metrics(state: State, removed: set[int]):
    groups = {}
    for label, pids in (("removed_in_prefix", removed),
                        ("survive_prefix", set(range(1, len(state.placements))) - removed)):
        cells = []
        for pid in pids:
            if pid >= len(state.placements):
                continue
            start, length = state.placements[pid]
            cells.append((start, start + length))
        if cells:
            cells.sort()
            occupied = sum(b - a for a, b in cells)
            groups[label] = {
                "pipes": len(cells),
                "occupied_m": occupied,
                "span_m": cells[-1][1] - cells[0][0],
                "within_cohort_void_m": cells[-1][1] - cells[0][0] - occupied,
            }
        else:
            groups[label] = {"pipes": 0, "occupied_m": 0,
                             "span_m": 0, "within_cohort_void_m": 0}
    return groups


def rank(state: State, removed: set[int], next_length: int):
    stats = future_gap_stats(state, removed)
    fit_capacity = sum((b - a) // next_length for a, b in gaps(
        State(state.trench, state.placements,
              tuple(False if pid in removed else alive
                    for pid, alive in enumerate(state.alive)))))
    return (state.trench, -fit_capacity, stats["future_gap_count"],
            stats["future_tail_m"])


def beam(ops, width: int, next_length: int):
    removed = { -op for op in ops if op < 0 }
    placements_count = sum(op > 0 for op in ops)
    current = [State(0, (None,), (False,))]
    expanded = 0
    for op in ops:
        if op > 0:
            generated = [child for state in current
                         for child in add_actions(state, op)]
            expanded += len(generated)
        else:
            generated = [delete(state, -op) for state in current]
        unique = {}
        for state in generated:
            signature = (state.trench, state.placements, state.alive)
            unique.setdefault(signature, state)
        current = sorted(unique.values(), key=lambda s: rank(s, removed, next_length))[:width]
    best = min(current, key=lambda s: (s.trench, rank(s, removed, next_length)[1:]))
    return best, removed, placements_count, expanded


def replay_official(ops, output_tokens):
    state = State(0, (None,), (False,))
    token = 0
    live_volume = peak_live = 0
    peak_op = 0
    for op_index, op in enumerate(ops, 1):
        if op > 0:
            digs = int(output_tokens[token]); start = int(output_tokens[token + 1]); token += 2
            h = state.trench + digs * DIG
            pid = len(state.placements)
            state = State(h, state.placements + ((start, op),), state.alive + (True,))
            live_volume += op
            if live_volume > peak_live:
                peak_live, peak_op = live_volume, op_index
        else:
            pid = -op
            _start = int(output_tokens[token]); token += 1
            if pid < len(state.alive) and state.alive[pid]:
                live_volume -= state.placements[pid][1]
                state = delete(state, pid)
    if token != len(output_tokens):
        raise ValueError((token, len(output_tokens)))
    return state, live_volume, peak_live, peak_op


def make_prefix_metrics(ops, state, peak_live, peak_op, removed, expanded,
                        oracle_state, width, next_length):
    def layout(s):
        gs = gaps(s)
        live = sum(length for pid, (_start, length) in enumerate(s.placements[1:], 1)
                   if s.alive[pid])
        tail = next((b - a for a, b in reversed(gs) if b == s.trench), 0)
        return {
            "trench_m": s.trench,
            "active_volume_m": live,
            "gap_count": len(gs),
            "free_volume_m": sum(b - a for a, b in gs),
            "max_gap_m": max((b - a for a, b in gs), default=0),
            "tail_m": tail,
            "future_deletion_cohorts": cohort_metrics(s, removed),
            **future_gap_stats(s, removed),
        }

    return {
        "commands": len(ops),
        "placements": sum(x > 0 for x in ops),
        "deletions": sum(x < 0 for x in ops),
        "future_deleted_pids": len(removed),
        "peak_live_m": peak_live,
        "peak_command": peak_op,
        "lower_bound_m": math.ceil(peak_live / DIG) * DIG,
        "next_length_for_capacity_probe": next_length,
        "beam_width": width,
        "expanded_states": expanded,
        "current": layout(state),
        "oracle": layout(oracle_state),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--judge-output", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prefixes", type=int, nargs="+", default=[96, 192])
    parser.add_argument("--width", type=int, default=32)
    args = parser.parse_args()
    data = list(map(int, args.input.read_text().split()))
    commands = data[2:2 + data[1]]
    output_tokens = args.judge_output.read_text().split()
    rows = []
    for count in args.prefixes:
        ops = commands[:count]
        # The comparison starts from an empty trench. Commands are exact case-15
        # prefixes, so every deletion PID remains valid.
        pstate, peak_live, peak_op = None, 0, 0
        baseline, final_live, peak_live, peak_op = replay_official(
            ops, output_tokens_for_prefix(ops, commands, output_tokens))
        request_lengths = [op for op in ops if op > 0]
        next_length = Counter(request_lengths[-32:]).most_common(1)[0][0]
        oracle, removed, _placements, expanded = beam(ops, args.width, next_length)
        rows.append(make_prefix_metrics(ops, baseline, peak_live, peak_op, removed,
                                        expanded, oracle, args.width, next_length))
    payload = {
        "scope": "offline oracle only; known deletion IDs within each exact case-15 prefix",
        "candidate_policy": "endpoint actions only (left or right edge of each fit gap; tail edge after growth)",
        "input": str(args.input),
        "prefix_results": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    for row in rows:
        print(row["commands"], "current", row["current"]["trench_m"],
              "oracle", row["oracle"]["trench_m"],
              "gap", row["current"]["trench_m"] - row["oracle"]["trench_m"],
              "expanded", row["expanded_states"])
    print(f"saved {args.out}")


def output_tokens_for_prefix(ops, all_ops, all_tokens):
    # Convert full judge output to the token prefix matching a command prefix.
    token_count = sum(2 if op > 0 else 1 for op in ops)
    return all_tokens[:token_count]


if __name__ == "__main__":
    main()
