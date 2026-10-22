#!/usr/bin/env python3
"""Reconstruct first baseline/witness divergence for long-anchor windows."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / 'divergence_diagnostics.json'
CASES = [(5, 1505), (9, 3001)]


def merge_gap(gaps, start, end):
    if start >= end:
        return sorted(gaps)
    merged = []
    inserted = False
    for left, right in sorted(gaps):
        if right < start:
            merged.append((left, right))
        elif end < left:
            if not inserted:
                merged.append((start, end))
                inserted = True
            merged.append((left, right))
        else:
            start = min(start, left)
            end = max(end, right)
    if not inserted:
        merged.append((start, end))
    return merged


def consume_gap(gaps, start, length):
    end = start + length
    containing = next(((a, b) for a, b in gaps if a <= start and end <= b), None)
    if containing is None:
        raise ValueError(f'placement [{start},{end}) is not in a free gap')
    updated = []
    for left, right in gaps:
        if (left, right) != containing:
            updated.append((left, right))
        else:
            if left < start:
                updated.append((left, start))
            if end < right:
                updated.append((end, right))
    return sorted(updated), containing


def gap_lengths(gaps):
    return Counter(right - left for left, right in gaps)


def case_diagnostic(case, start, count=4096):
    data = list(map(int, (ROOT / f'data/pipes/open/{case}.in').read_text().split()))
    n = data[1]
    ops = data[2:2 + n]
    trace_path = ROOT / f'results/pipes/final/open-run-size-cohort-lanes/runs/{case}/judge_output.txt'
    baseline = trace_path.read_text().splitlines()
    witness_path = ROOT / f'results/pipes/improvement/offline_longbeam_longanchors/case{case}_start{start}_n{count}_w3_a4.json'
    witness = json.loads(witness_path.read_text())
    winner = {entry['op']: entry for entry in witness['winner_path']}

    baseline_actions = {}
    for i, (op, line) in enumerate(zip(ops, baseline), 1):
        if op > 0:
            digs, position = map(int, line.split())
            baseline_actions[i] = (digs, position)

    first_diff = None
    matched_prefix = 0
    for i in range(start, start + count):
        if ops[i - 1] <= 0:
            continue
        base_action = baseline_actions[i]
        win_action = (winner[i]['digs'], winner[i]['start'])
        if base_action != win_action:
            first_diff = i
            break
        matched_prefix += 1
    if first_diff is None:
        return {'case': case, 'first_divergence': None}

    # Replay exact baseline actions up to, but not including, first divergence.
    gaps = []
    trench = 0
    active = {}
    next_pid = 0
    active_at_window_start = None
    for i in range(1, first_diff):
        if i == start:
            active_at_window_start = dict(active)
        op = ops[i - 1]
        if op > 0:
            next_pid += 1
            digs, position = baseline_actions[i]
            old_trench = trench
            trench += 20 * digs
            gaps = merge_gap(gaps, old_trench, trench)
            gaps, _ = consume_gap(gaps, position, op)
            active[next_pid] = {
                'pid': next_pid, 'start': position, 'length': op,
                'created_op': i,
            }
        elif op < 0:
            removed = active.pop(-op, None)
            if removed is not None:
                gaps = merge_gap(gaps, removed['start'], removed['start'] + removed['length'])
    if active_at_window_start is None:
        active_at_window_start = dict(active)

    op_length = ops[first_diff - 1]
    base_digs, base_start = baseline_actions[first_diff]
    win_digs = winner[first_diff]['digs']
    win_start = winner[first_diff]['start']
    base_gap = next(((a, b) for a, b in gaps if a <= base_start and base_start + op_length <= b), None)
    win_gap = next(((a, b) for a, b in gaps if a <= win_start and win_start + op_length <= b), None)
    if base_gap is None or win_gap is None:
        raise ValueError('divergent placement not feasible in reconstructed common state')

    def place_one(start_pos, digs):
        local_gaps = list(gaps)
        local_trench = trench
        if digs:
            local_gaps = merge_gap(local_gaps, local_trench, local_trench + 20 * digs)
            local_trench += 20 * digs
        local_gaps, _ = consume_gap(local_gaps, start_pos, op_length)
        return local_trench, local_gaps

    base_after_trench, base_after_gaps = place_one(base_start, base_digs)
    win_after_trench, win_after_gaps = place_one(win_start, win_digs)
    left_pipe = max((p for p in active.values() if p['start'] + p['length'] <= base_gap[0]),
                    key=lambda p: p['start'] + p['length'], default=None)
    right_pipe = min((p for p in active.values() if p['start'] >= base_gap[1]),
                     key=lambda p: p['start'], default=None)

    delete_op = {}
    for i, op in enumerate(ops, 1):
        if op < 0:
            delete_op[-op] = i
    window_end = start + count - 1
    prewindow_live_at_div = [p for p in active.values() if p['created_op'] < start]
    prewindow_survive_block = [p for p in active_at_window_start.values()
                               if delete_op.get(p['pid'], n + 1) > window_end]

    return {
        'case': case,
        'window_start_op_1based': start,
        'window_end_op_1based': window_end,
        'window_count': count,
        'prewindow_active_at_start': len(active_at_window_start),
        'prewindow_active_surviving_through_window_end': len(prewindow_survive_block),
        'baseline_active_pipes_before_first_divergence': len(active),
        'prewindow_anchors_active_before_first_divergence': len(prewindow_live_at_div),
        'first_divergent_placement_op_1based': first_diff,
        'placement_length': op_length,
        'identical_witness_placements_before_divergence': matched_prefix,
        'common_state_before_divergence': {
            'trench_length_m': trench,
            'free_gap_count': len(gaps),
            'fitting_gap_count': sum(1 for a, b in gaps if b - a >= op_length),
            'gap_length_histogram': dict(sorted(gap_lengths(gaps).items())),
            'selected_gap_baseline': {'start': base_gap[0], 'end': base_gap[1], 'length': base_gap[1] - base_gap[0]},
            'selected_gap_witness': {'start': win_gap[0], 'end': win_gap[1], 'length': win_gap[1] - win_gap[0]},
            'immediate_neighbor_pipes': {'left': left_pipe, 'right': right_pipe},
        },
        'baseline_action': {'digs_sections': base_digs, 'start': base_start,
                            'occupied': [base_start, base_start + op_length],
                            'trench_after_m': base_after_trench},
        'witness_action': {'digs_sections': win_digs, 'start': win_start,
                           'occupied': [win_start, win_start + op_length],
                           'trench_after_m': win_after_trench},
        'after_first_divergence': {
            'same_trench_length': base_after_trench == win_after_trench,
            'same_free_gap_count': len(base_after_gaps) == len(win_after_gaps),
            'same_multiset_of_gap_lengths': gap_lengths(base_after_gaps) == gap_lengths(win_after_gaps),
            'baseline_residual_gaps_near_divergent_gap': [g for g in base_after_gaps
                if g[0] >= base_gap[0] - 10 and g[1] <= base_gap[1] + 10],
            'witness_residual_gaps_near_divergent_gap': [g for g in win_after_gaps
                if g[0] >= win_gap[0] - 10 and g[1] <= win_gap[1] + 10],
        },
        'full_replay': {
            'baseline_final_m': witness['baseline_final_trench_m'],
            'baseline_control_replay_m': witness['baseline_control_replay_trench_m'],
            'best_witness_final_m': witness['best_full_suffix_witness_trench_m'],
            'feasible_hindsight_saving_m': witness['full_suffix_witness_saving_m'],
            'baseline_control_exactly_matches_baseline': witness['baseline_control_replay_trench_m'] == witness['baseline_final_trench_m'],
            'feasible_not_optimality_certificate': True,
        },
    }


result = {'cases': [case_diagnostic(case, start) for case, start in CASES]}
OUT.write_text(json.dumps(result, indent=2) + '\n')
print(OUT)
print(json.dumps(result, indent=2))
