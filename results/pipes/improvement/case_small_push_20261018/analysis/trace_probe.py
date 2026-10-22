#!/usr/bin/env python3
"""Replay selected official traces and count causal LIFO-adjacency choices."""
from __future__ import annotations

import json
import bisect
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUNS = ROOT / "results/pipes/improvement/case5_additive_next_alignment_20261017/runs/AB_open15"


def add_gap(gaps: dict[int, int], start: int, end: int) -> None:
    if start >= end:
        return
    keys = sorted(gaps)
    left = 0
    while left < len(keys) and keys[left] < start:
        left += 1
    if left and gaps[keys[left - 1]] >= start:
        left -= 1
    merged_start, merged_end = start, end
    while left < len(keys) and keys[left] <= merged_end:
        key = keys[left]
        if gaps[key] < merged_start:
            left += 1
            continue
        merged_start = min(merged_start, key)
        merged_end = max(merged_end, gaps[key])
        del gaps[key]
        keys.pop(left)
    gaps[merged_start] = merged_end


def consume(gaps: dict[int, int], start: int, end: int) -> None:
    for key, gap_end in list(gaps.items()):
        if key <= start and end <= gap_end:
            del gaps[key]
            add_gap(gaps, key, start)
            add_gap(gaps, end, gap_end)
            return
    raise ValueError(f"placement [{start},{end}) is not inside a free gap: {gaps}")


def score_gap(gap_len: int, length: int, history_len: int,
              recent_freq: list[int]) -> int:
    slack = gap_len - length
    score = slack * history_len
    if 0 < slack <= 40:
        score += 60 * sum(recent_freq[slack + 1:41])
    return score


def steady_trend(history: deque[int]) -> bool:
    distinct = []
    previous = None
    for value in reversed(history):
        if value == previous:
            continue
        distinct.append(value)
        previous = value
        if len(distinct) == 3:
            break
    return (len(distinct) == 3 and
            distinct[0] - distinct[1] == distinct[1] - distinct[2])


def analyze(case: int) -> dict:
    inp = list(map(int, (ROOT / f"data/pipes/open/{case}.in").read_text().split()))
    weight, n = inp[:2]
    commands = inp[2:]
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    responses = (RUNS / f"runs/{case}/judge_output.txt").read_text().splitlines()
    assert len(commands) == n == len(responses), (case, len(commands), n, len(responses))

    active: dict[int, tuple[int, int, int]] = {}
    active_starts: dict[int, int] = {}
    gaps: dict[int, int] = {}
    active_ends: dict[int, int] = {}
    active_pids: list[int] = []
    recent_freq = [0] * 41
    next_pid = 1
    trench = 0
    occurrences = [0] * 41
    removed_cohort = [[0, 0] for _ in range(41)]
    history: deque[int] = deque(maxlen=2048)
    delete_ranks: deque[int] = deque(maxlen=64)
    lifo_history_counts = []
    rank_profile = Counter()
    adjacency = Counter()
    placement_profile = Counter()
    expansion_events = []
    current_runs = Counter()
    last_length = None
    run_length = 0
    parity_mode = False
    chosen_candidate_diffs = []

    for op, (command, response) in enumerate(zip(commands, responses), 1):
        if command > 0:
            length = command
            parts = list(map(int, response.split()))
            assert len(parts) == 2, (case, op, command, response)
            digs, start = parts
            if digs:
                old = trench
                trench += digs * 20
                tails = [s for s, e in gaps.items() if e == old]
                if tails:
                    tail = max(tails)
                    gaps[tail] = trench
                else:
                    add_gap(gaps, old, trench)

            cohort = occurrences[length] % 2
            fitting = []
            young_adjacent = []
            nactive = len(active)
            lifo = (len(delete_ranks) >= 24 and
                    sum(rank <= 200 for rank in delete_ranks) * 100 >= len(delete_ranks) * 70)
            if not digs:
                for gs, ge in gaps.items():
                    gl = ge - gs
                    if gl < length:
                        continue
                    value = score_gap(gl, length, len(history), recent_freq)
                    fitting.append((value, gl, gs, ge))
                    right_pid = active_starts.get(ge)
                    left_neighbor = active_ends.get(gs)
                    for side, pid in (("low", left_neighbor), ("high", right_pid)):
                        if pid is None or active[pid][1] != length:
                            continue
                        idx = bisect.bisect_right(active_pids, pid)
                        newer = nactive - idx
                        rank = newer * 1000 // max(1, nactive - 1)
                        if rank <= 200:
                            young_adjacent.append((value, gl, gs, ge, pid, rank, side))
            if fitting:
                best_score = min(x[0] for x in fitting)
                chosen_score = next((v for v, gl, gs, ge in fitting
                                     if gs <= start and start + length <= ge), None)
                same_score_young = [x for x in young_adjacent if x[0] == chosen_score]
                not_worse_young = [x for x in young_adjacent if x[0] <= chosen_score]
                if lifo:
                    adjacency["lifo_placement_ops"] += 1
                    if young_adjacent:
                        adjacency["lifo_any_young_adj_fit"] += 1
                    if same_score_young:
                        adjacency["lifo_same_local_score"] += 1
                    if not_worse_young:
                        adjacency["lifo_no_worse_than_chosen"] += 1
                if young_adjacent:
                    adjacency["all_any_young_adj_fit"] += 1
                if same_score_young:
                    adjacency["all_same_local_score"] += 1
                if chosen_score is not None and chosen_score > best_score:
                    chosen_candidate_diffs.append((op, length, best_score, chosen_score))
            if digs:
                # Evaluate free space before consumption for expansion diagnostics.
                free_total = sum(e - s for s, e in gaps.items())
                max_gap = max((e - s for s, e in gaps.items()), default=0)
                expansion_events.append({"op": op, "length": length, "digs": digs,
                                         "trench_before": trench - 20*digs,
                                         "free_before": free_total,
                                         "max_gap_before": max_gap,
                                         "active_before": len(active),
                                         "lifo": bool(lifo)})
            consume(gaps, start, start + length)
            pid_new = next_pid
            next_pid += 1
            active[pid_new] = (start, length, cohort)
            active_starts[start] = pid_new
            active_ends[start + length] = pid_new
            bisect.insort(active_pids, pid_new)
            occurrences[length] += 1
            if len(history) == history.maxlen:
                recent_freq[history[0]] -= 1
            history.append(length)
            recent_freq[length] += 1
            if last_length == length:
                run_length += 1
            else:
                if last_length is not None:
                    current_runs[run_length] += 1
                run_length = 1
                last_length = length
            placement_profile[length] += 1
            if length == 1:
                placement_profile["unit_lifo_run"] += int(lifo)
        else:
            pid = -command
            start_response = int(response.strip())
            assert pid in active and active[pid][0] == start_response, (case, op, pid, response, active.get(pid))
            start, length, cohort = active.pop(pid)
            active_starts.pop(start)
            active_ends.pop(start + length)
            pid_pos = bisect.bisect_left(active_pids, pid)
            del active_pids[pid_pos]
            newer = len(active_pids) - pid_pos
            rank = newer * 1000 // max(1, len(active_pids))
            delete_ranks.append(rank)
            rank_profile[rank // 100 * 100] += 1
            add_gap(gaps, start, start + length)
            removed_cohort[length][cohort] += 1
            total = sum(removed_cohort[length])
            dominant = max(removed_cohort[length])
            if total >= 8 and dominant * 100 >= total * 85 and steady_trend(history):
                parity_mode = True

    if last_length is not None:
        current_runs[run_length] += 1
    return {
        "case": case, "weight": weight, "ops": n, "placements": sum(placement_profile[k] for k in range(1,41)),
        "placement_length_hist": {str(k): placement_profile[k] for k in range(1,41) if placement_profile[k]},
        "run_length_hist": dict(sorted(current_runs.items())),
        "lifo_rank_bins": {str(k): rank_profile[k] for k in sorted(rank_profile)},
        "adjacency_opportunities": dict(adjacency),
        "expansion_count": len(expansion_events),
        "expansion_events_last": expansion_events[-15:],
        "events": expansion_events,
        "suboptimal_response_ops": chosen_candidate_diffs[:50],
    }


recent_freq = [0] * 41
all_results = {}
for case in (12, 14):
    result = analyze(case)
    all_results[str(case)] = result
out = Path(__file__).with_name("trace_probe.json")
out.write_text(json.dumps(all_results, indent=2) + "\n")
for case, result in all_results.items():
    print(json.dumps({k: v for k, v in result.items() if k not in ("events", "suboptimal_response_ops")}, indent=2))
