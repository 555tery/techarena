#!/usr/bin/env python3
"""Counterfactual slack-transfer witness scan on a saved exact transcript.

The witness is hindsight-only: after a no-fit tail expansion, shift the new pipe
right by all post-dig slack, joining that slack to the active pipe immediately
left of the tail if it is later deleted. Search for a later baseline expansion
request that this combined gap could fit before either adjacent pipe is removed.
"""
from __future__ import annotations
import bisect, csv, hashlib, json
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
INPUT = ROOT / 'data/pipes/open/15.in'
ANSWER = ROOT / 'results/pipes/improvement/case9_hole_first_cohorts/runs/combined_open15/runs/15/judge_output.txt'
PLACEMENTS = ROOT / 'results/pipes/improvement/case15_expansion_edge_cf/geometry/composite/placements.csv'
OUT = ROOT / 'results/pipes/improvement/case15_expansion_edge_cf/analysis/witness_scan.json'

words = INPUT.read_text().split(); n = int(words[1])
commands = list(map(int, words[2:2+n])); answers = ANSWER.read_text().splitlines()
rows = {int(r['op']): r for r in csv.DictReader(PLACEMENTS.open())}
delete_op = {}; pid = 0
for op, cmd in enumerate(commands, 1):
    if cmd > 0: pid += 1
    else: delete_op[-cmd] = op
max_pid = pid
extensions_by_length = {q: [] for q in range(1, 41)}
placements_by_length = {q: [] for q in range(1, 41)}
for op, cmd in enumerate(commands, 1):
    if cmd > 0:
        placements_by_length[cmd].append(op)
        if int(rows[op]['digs']) > 0: extensions_by_length[cmd].append(op)

bit = [0] * (max_pid + 1)
def fenwick_add(i: int, d: int) -> None:
    while i <= max_pid: bit[i] += d; i += i & -i
def prefix(i: int) -> int:
    s = 0
    while i: s += bit[i]; i -= i & -i
    return s
active = [False] * (max_pid + 1); starts = [0] * (max_pid + 1)
lengths = [0] * (max_pid + 1); birth = [0] * (max_pid + 1)
end_to_pid = {}; active_n = 0; last_deleted_rank = None; last_deleted_pid = None
rank_history: deque[int] = deque(maxlen=64); placements_since_delete = 0
witnesses = []; counts = Counter(); feature_counts = Counter()

for op, cmd in enumerate(commands, 1):
    out = list(map(int, answers[op-1].split()))
    if cmd > 0:
        row = rows[op]; this_pid = int(row['pid']); L = cmd; digs = int(row['digs'])
        gap_start = int(row['selected_gap_start']); gap_end = int(row['selected_gap_end'])
        start = out[1]; slack = gap_end - gap_start - L
        neighbor = end_to_pid.get(gap_start)
        if digs > 0:
            counts['no_fit_expansions'] += 1
            counts['positive_slack_expansions'] += slack > 0
            if slack > 0 and neighbor is not None:
                counts['offset_can_join_left_neighbor'] += 1
                neighbor_delete = delete_op.get(neighbor, n + 1)
                current_delete = delete_op.get(this_pid, n + 1)
                neighbor_len = lengths[neighbor]
                if neighbor_delete < current_delete:
                    counts['neighbor_deleted_before_current_pipe'] += 1
                    counts['neighbor_deleted_within_1_command'] += neighbor_delete == op + 1
                    counts['neighbor_deleted_within_10_commands'] += neighbor_delete <= op + 10
                    cap = min(40, neighbor_len + slack); earliest = None
                    for q in range(neighbor_len + 1, cap + 1):
                        arr = extensions_by_length[q]; j = bisect.bisect_right(arr, neighbor_delete)
                        if j < len(arr) and arr[j] < current_delete:
                            eop = arr[j]
                            if earliest is None or eop < earliest[0]: earliest = (eop, q)
                    if earliest:
                        eop, q = earliest; counts['slack_capacity_future_expansion_witness'] += 1
                        prior_competitor = False
                        for size in range(1, cap + 1):
                            arr = placements_by_length[size]; j = bisect.bisect_right(arr, neighbor_delete)
                            if j < len(arr) and arr[j] < eop: prior_competitor = True; break
                        counts['first_fit_witness_without_earlier_competitor'] += not prior_competitor
                        ranks = list(rank_history); recent = ranks[-16:]
                        witnesses.append({
                            'op': op, 'pid': this_pid, 'length': L, 'digs': digs,
                            'tail_start': gap_start, 'post_dig_gap_end': gap_end,
                            'post_dig_slack': slack, 'selected_start': start,
                            'neighbor_pid': neighbor, 'neighbor_length': neighbor_len,
                            'neighbor_age_commands': op - birth[neighbor],
                            'neighbor_rank_before_arrival': active_n - prefix(neighbor) + 1,
                            'neighbor_delete_op': neighbor_delete,
                            'current_pipe_delete_op': current_delete,
                            'first_future_extension_witness': {'op': eop, 'length': q},
                            'last_deleted_rank': last_deleted_rank,
                            'recent_rank2_fraction_16': (sum(r == 2 for r in recent) / len(recent)) if recent else 0.0,
                            'placements_since_delete': placements_since_delete,
                            'last_deleted_pid': last_deleted_pid,
                            'neighbor_pid_delta_from_last_deleted': neighbor - last_deleted_pid if last_deleted_pid is not None else None,
                        })
                        feature_counts['last_rank2'] += last_deleted_rank == 2
                        feature_counts['placements_since_delete_1'] += placements_since_delete == 1
                        feature_counts['neighbor_age_le_2'] += op - birth[neighbor] <= 2
                        feature_counts['neighbor_pid_delta_2'] += last_deleted_pid is not None and neighbor - last_deleted_pid == 2
                        feature_counts['rank2_majority_recent16'] += bool(recent) and sum(r == 2 for r in recent) * 2 >= len(recent)
        starts[this_pid] = start; lengths[this_pid] = L; birth[this_pid] = op
        active[this_pid] = True; end_to_pid[start + L] = this_pid
        fenwick_add(this_pid, 1); active_n += 1; placements_since_delete += 1
    else:
        target = -cmd; last_deleted_pid = target
        rank = active_n - prefix(target) + 1
        last_deleted_rank = rank; rank_history.append(rank); placements_since_delete = 0
        active[target] = False; fenwick_add(target, -1); active_n -= 1
        end_to_pid.pop(starts[target] + lengths[target], None)

OUT.write_text(json.dumps({
    'scope': 'exact composite case-15 transcript; witnesses are retrospective, not online signals',
    'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    'composite_answer_sha256': hashlib.sha256(ANSWER.read_bytes()).hexdigest(),
    'counts': dict(counts), 'witness_count': len(witnesses),
    'witness_feature_counts': dict(feature_counts), 'witnesses': witnesses,
}, indent=2) + '\n')
print(json.dumps({'counts': dict(counts), 'witness_count': len(witnesses),
                  'witness_feature_counts': dict(feature_counts)}, indent=2))
