#!/usr/bin/env python3
"""Offline-only local beam diagnostic on exact case-15 suffix windows.

The initial layout is the frozen online solver's exact state before a window.
The beam may see deletion IDs later inside that window to rank layouts. It does
not alter the online candidate and is only a feasible hindsight witness.
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
    free: tuple[tuple[int, int], ...]
    # Preserve coordinates after a later deletion for cohort diagnostics.
    new_positions: tuple[tuple[int, int], ...]
    new_alive: tuple[bool, ...]


def parse_case(path: Path):
    raw = list(map(int, path.read_text().split()))
    return raw[2:2 + raw[1]]


def parse_answers(ops, path: Path):
    tokens = list(map(int, path.read_text().split()))
    answers = []
    cursor = 0
    for op in ops:
        count = 2 if op > 0 else 1
        answers.append(tuple(tokens[cursor:cursor + count]))
        cursor += count
    if cursor != len(tokens):
        raise ValueError(f"answer token mismatch: consumed {cursor}, have {len(tokens)}")
    return answers


def make_gaps(pipes, trench):
    occupied = sorted((start, start + length) for item in pipes[1:]
                      if item is not None for start, length in (item,))
    result = []
    cursor = 0
    for left, right in occupied:
        if left > cursor:
            result.append((cursor, left))
        cursor = max(cursor, right)
    if cursor < trench:
        result.append((cursor, trench))
    return tuple(result)


def add_free(gaps, left, right):
    if left >= right:
        return gaps
    result = list(gaps)
    i = 0
    while i < len(result) and result[i][1] < left:
        i += 1
    while i < len(result) and result[i][0] <= right:
        left = min(left, result[i][0])
        right = max(right, result[i][1])
        result.pop(i)
    result.insert(i, (left, right))
    return tuple(result)


def consume(gaps, left, right):
    result = list(gaps)
    for i, (a, b) in enumerate(result):
        if a <= left and right <= b:
            result.pop(i)
            if a < left:
                result.insert(i, (a, left))
                i += 1
            if right < b:
                result.insert(i, (right, b))
            return tuple(result)
    raise ValueError(f"placement [{left},{right}) is not in a free interval")


def extend_and_place(state: State, start: int, length: int, new_h: int):
    gaps = state.free
    if new_h > state.trench:
        tail_left = gaps[-1][0] if gaps and gaps[-1][1] == state.trench else state.trench
        if gaps and gaps[-1][1] == state.trench:
            gaps = gaps[:-1] + ((tail_left, new_h),)
        else:
            gaps = gaps + ((state.trench, new_h),)
    gaps = consume(gaps, start, start + length)
    return State(new_h, gaps,
                 state.new_positions + ((start, length),),
                 state.new_alive + (True,))


def candidate_actions(state: State, length: int, baseline_answer,
                      gap_cap: int):
    fitting = [(right - left, left, right) for left, right in state.free
               if right - left >= length]
    actions = set()
    if fitting:
        # Keep a diverse but bounded set of exact feasible gaps. The baseline
        # move is always included, so the beam retains a valid control path.
        selected = set()
        ordered = sorted(fitting, key=lambda g: (g[0] - length, g[1]))
        selected.update((g[1], g[2]) for g in ordered[:gap_cap // 3 + 1])
        selected.update((g[1], g[2]) for g in sorted(fitting, reverse=True)[:gap_cap // 3 + 1])
        selected.update((g[1], g[2]) for g in fitting[:gap_cap // 3 + 1])
        selected.update((g[1], g[2]) for g in fitting[-gap_cap // 3 - 1:])
        for left, right in selected:
            actions.add((left, state.trench))
            actions.add((right - length, state.trench))
            if right - left > length + 1:
                actions.add(((left + right - length) // 2, state.trench))
        digs, baseline_start = baseline_answer
        if digs == 0:
            actions.add((baseline_start, state.trench))
        else:
            # Some policies voluntarily extend. Preserve the exact baseline
            # answer as a feasible control action even when an old gap fits.
            actions.add((baseline_start, state.trench + digs * DIG))
    else:
        tail_left = state.free[-1][0] if state.free and state.free[-1][1] == state.trench else state.trench
        tail_length = state.trench - tail_left
        grown = state.trench + max(0, math.ceil((length - tail_length) / DIG)) * DIG
        # Every integer start in the newly extended tail is feasible. Its span
        # is at most one dig unit after minimum required growth.
        for start in range(tail_left, grown - length + 1):
            actions.add((start, grown))
        digs, baseline_start = baseline_answer
        if digs > 0:
            actions.add((baseline_start, state.trench + digs * DIG))
    valid = []
    for start, new_h in actions:
        if start < 0 or start + length > new_h:
            continue
        try:
            extend_and_place(state, start, length, new_h)
            valid.append((start, new_h))
        except ValueError:
            pass
    return sorted(set(valid))


def projected_gaps(state: State, future_pids, base_positions, base_count):
    intervals = list(state.free)
    for pid in future_pids:
        if pid <= base_count:
            item = base_positions.get(pid)
        else:
            i = pid - base_count - 1
            item = state.new_positions[i] if 0 <= i < len(state.new_positions) and state.new_alive[i] else None
        if item is not None:
            start, length = item
            intervals.append((start, start + length))
    intervals.sort()
    result = []
    for left, right in intervals:
        if not result or left > result[-1][1]:
            result.append([left, right])
        else:
            result[-1][1] = max(result[-1][1], right)
    return tuple((a, b) for a, b in result)


def rank_state(state, future_pids, future_lengths, base_positions, base_count):
    gs = projected_gaps(state, future_pids, base_positions, base_count)
    capacity = sum(count * ((right - left) // length)
                   for length, count in future_lengths.items()
                   for left, right in gs)
    max_gap = max((right - left for left, right in gs), default=0)
    tail = next((right - left for left, right in reversed(gs)
                 if right == state.trench), 0)
    return (state.trench, -capacity, len(gs), -max_gap, -tail,
            state.free, state.new_positions)


def state_signature(state):
    return (state.trench, state.free, state.new_positions, state.new_alive)


def metrics(state, live, base_count, deleted_new):
    gs = state.free
    tail = next((b - a for a, b in reversed(gs) if b == state.trench), 0)
    groups = {}
    for label, wants_deleted in (("deleted_in_window", True), ("survive_window", False)):
        cells = [(start, start + length)
                 for i, (start, length) in enumerate(state.new_positions, 1)
                 if ((base_count + i) in deleted_new) == wants_deleted]
        if cells:
            cells.sort()
            span = cells[-1][1] - cells[0][0]
            union = []
            for left, right in cells:
                if not union or left > union[-1][1]:
                    union.append([left, right])
                else:
                    union[-1][1] = max(union[-1][1], right)
            union_length = sum(right - left for left, right in union)
            historical_length_sum = sum(b - a for a, b in cells)
        else:
            span = union_length = historical_length_sum = 0
        groups[label] = {
            "pipes": len(cells),
            "historical_length_sum_m": historical_length_sum,
            "coordinate_union_m": union_length,
            "coordinate_span_m": span,
            "span_void_after_union_m": span - union_length,
            "reused_coordinate_overlap_m": historical_length_sum - union_length,
        }
    return {"trench_m": state.trench, "active_volume_m": live,
            "free_volume_m": state.trench - live, "gap_count": len(gs),
            "max_gap_m": max((b - a for a, b in gs), default=0),
            "tail_m": tail, "new_pipe_cohorts": groups,
            "new_pipe_count": len(state.new_positions),
            "background_pipe_count_at_cut": base_count}


def run_window(ops, answers, start, count, width, gap_cap):
    stop = start + count
    pipes = [None]
    h = live = peak = 0
    token_index = 0
    placement_count = 0
    for op_index, op in enumerate(ops[:start - 1], 1):
        answer = answers[op_index - 1]
        if op > 0:
            digs, position = answer
            h += digs * DIG
            placement_count += 1
            pipes.append((position, op))
            live += op
            peak = max(peak, live)
        else:
            pid = -op
            if 0 < pid < len(pipes) and pipes[pid] is not None:
                live -= pipes[pid][1]
                pipes[pid] = None
    base_count = placement_count
    base_positions = {pid: item for pid, item in enumerate(pipes[1:], 1)
                      if item is not None}
    base_free = make_gaps(pipes, h)
    initial = State(h, base_free, (), ())

    window_ops = ops[start - 1:stop - 1]
    window_answers = answers[start - 1:stop - 1]
    future_del_by_step = []
    deleted_pids = set()
    for op in window_ops:
        if op < 0:
            deleted_pids.add(-op)
    future = set(deleted_pids)
    for op in window_ops:
        if op < 0:
            future.discard(-op)
        future_del_by_step.append(frozenset(future))

    live0 = live
    current = [initial]
    expanded = 0
    next_pid = base_count
    pid_by_op = []
    for op in window_ops:
        if op > 0:
            next_pid += 1
            pid_by_op.append(next_pid)
        else:
            pid_by_op.append(-op)

    for i, (op, answer) in enumerate(zip(window_ops, window_answers)):
        if op > 0:
            pid = pid_by_op[i]
            generated = []
            for state in current:
                for start_pos, new_h in candidate_actions(state, op, answer, gap_cap):
                    try:
                        child = extend_and_place(state, start_pos, op, new_h)
                    except ValueError:
                        continue
                    generated.append(child)
            expanded += len(generated)
            live += op
            peak = max(peak, live)
        else:
            pid = -op
            generated = []
            for state in current:
                if pid <= base_count:
                    item = base_positions.get(pid)
                    if item is None:
                        generated.append(state)
                    else:
                        start_pos, length = item
                        generated.append(State(state.trench,
                                               add_free(state.free, start_pos, start_pos + length),
                                               state.new_positions, state.new_alive))
                else:
                    j = pid - base_count - 1
                    if j < 0 or j >= len(state.new_positions) or not state.new_alive[j]:
                        generated.append(state)
                    else:
                        start_pos, length = state.new_positions[j]
                        alive = list(state.new_alive)
                        alive[j] = False
                        generated.append(State(state.trench,
                                               add_free(state.free, start_pos, start_pos + length),
                                               state.new_positions, tuple(alive)))
            # live is identical for every state; compute it once from the input.
            if pid <= base_count:
                item = base_positions.get(pid)
                if item is not None:
                    live -= item[1]
            else:
                live -= next(window_ops[j] for j in range(i - 1, -1, -1)
                             if window_ops[j] > 0 and pid_by_op[j] == pid)

        unique = {}
        for state in generated:
            unique.setdefault(state_signature(state), state)
        generated = list(unique.values())
        future_lengths = Counter(x for x in window_ops[i + 1:] if x > 0)
        future_pids = future_del_by_step[i]
        # Fast causal-space shortlist, then rank only a bounded set with the
        # oracle's remaining deletion IDs.
        next_len = (future_lengths.most_common(1)[0][0] if future_lengths else 1)
        def quick_key(s):
            fit = sum((b - a) // next_len for a, b in s.free)
            maxg = max((b - a for a, b in s.free), default=0)
            tail = next((b - a for a, b in reversed(s.free) if b == s.trench), 0)
            return (s.trench, -fit, len(s.free), -maxg, -tail, s.free)
        generated.sort(key=quick_key)
        shortlist = generated[:max(width * 8, width)]
        current = sorted(shortlist,
                         key=lambda s: rank_state(s, future_pids, future_lengths,
                                                  base_positions, base_count))[:width]
        if not current:
            raise RuntimeError(f"beam exhausted at suffix offset {i}")

    # Build the exact baseline layout through the same free-interval model.
    baseline = initial
    baseline_live = live0
    pid_now = base_count
    for op, answer in zip(window_ops, window_answers):
        if op > 0:
            digs, start_pos = answer
            new_h = baseline.trench + digs * DIG
            baseline = extend_and_place(baseline, start_pos, op, new_h)
            baseline_live += op
            pid_now += 1
        else:
            pid = -op
            if pid <= base_count:
                item = base_positions.get(pid)
                if item is not None:
                    baseline = State(baseline.trench,
                                     add_free(baseline.free, item[0], item[0] + item[1]),
                                     baseline.new_positions, baseline.new_alive)
                    baseline_live -= item[1]
            else:
                j = pid - base_count - 1
                if 0 <= j < len(baseline.new_positions) and baseline.new_alive[j]:
                    item = baseline.new_positions[j]
                    alive = list(baseline.new_alive); alive[j] = False
                    baseline = State(baseline.trench,
                                     add_free(baseline.free, item[0], item[0] + item[1]),
                                     baseline.new_positions, tuple(alive))
                    baseline_live -= item[1]

    oracle = current[0]
    # live is deterministic; calculate from baseline rather than beam bookkeeping.
    final_live = baseline_live
    baseline_metrics = metrics(baseline, final_live, base_count, deleted_pids)
    oracle_metrics = metrics(oracle, final_live, base_count, deleted_pids)
    return {
        "window_start_op_1based": start,
        "window_commands": count,
        "placements": sum(op > 0 for op in window_ops),
        "deletions": sum(op < 0 for op in window_ops),
        "future_deletion_ids_available_to_oracle": len(deleted_pids),
        "beam_width": width,
        "endpoint_gap_cap": gap_cap,
        "expanded_states": expanded,
        "active_volume_at_cut_m": live0,
        "lower_bound_after_window_m": math.ceil(final_live / DIG) * DIG,
        "initial": metrics(initial, live0, base_count, set()),
        "baseline": baseline_metrics,
        "oracle": oracle_metrics,
        "oracle_saving_m": baseline.trench - oracle.trench,
        "baseline_high_water_growth_m": baseline.trench - initial.trench,
        "oracle_high_water_growth_m": oracle.trench - initial.trench,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--judge-output", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--windows", type=int, nargs="+", default=[100000, 120000, 160000])
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--width", type=int, default=16)
    parser.add_argument("--gap-cap", type=int, default=12)
    args = parser.parse_args()
    ops = parse_case(args.input)
    answers = parse_answers(ops, args.judge_output)
    rows = [run_window(ops, answers, start, args.count, args.width, args.gap_cap)
            for start in args.windows]
    payload = {
        "scope": "offline oracle only; exact baseline state at each window start; known future deletion IDs only inside that window",
        "action_space": "feasible integer starts at selected gap edges/centres; all starts in a newly extended tail; baseline answer retained",
        "input": str(args.input),
        "window_results": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    for row in rows:
        print(row["window_start_op_1based"], "baseline", row["baseline"]["trench_m"],
              "oracle", row["oracle"]["trench_m"], "saved", row["oracle_saving_m"],
              "growth", row["baseline_high_water_growth_m"], "->",
              row["oracle_high_water_growth_m"], "expanded", row["expanded_states"])
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
