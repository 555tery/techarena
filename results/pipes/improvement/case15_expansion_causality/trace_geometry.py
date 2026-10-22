#!/usr/bin/env python3
"""Exact physical-gap replay for the fixed Open15 baseline transcript."""
from bisect import bisect_left, bisect_right
from collections import Counter
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / 'data/pipes/open/15.in'
ANSWER = Path(__file__).with_name('baseline_trace_answer.txt')
PLACEMENTS = ROOT / 'results/pipes/improvement/case15_interval_lineage/replay/placements.csv'
GAP_EPISODES = ROOT / 'results/pipes/improvement/case15_interval_lineage/replay/gap_episodes.csv'
OUT = Path(__file__).with_name('geometry_placements.csv')
EVENTS = Path(__file__).with_name('expansion_events.csv')

vals = INPUT.read_text().split()
weight, n = float(vals[0]), int(vals[1])
commands = list(map(int, vals[2:2+n]))
answers = list(map(int, ANSWER.read_text().split()))
assert len(commands) == n
assert len(answers) == sum(2 if c > 0 else 1 for c in commands)

# sorted half-open free intervals
starts: list[int] = []
gaps: dict[int, int] = {}
active: dict[int, tuple[int,int]] = {}
trench = occupied = 0
pid = 0
ai = 0
rows: dict[int, dict] = {}
event_pre: dict[int, set[tuple[int,int]]] = {}

def add_gap(a: int, b: int) -> None:
    if a >= b: return
    i = bisect_left(starts, a)
    if i and gaps[starts[i-1]] >= a:
        i -= 1
        a = starts[i]
        b = max(b, gaps[starts[i]])
        del gaps[starts[i]]
        starts.pop(i)
    while i < len(starts) and starts[i] <= b:
        k = starts[i]
        b = max(b, gaps[k])
        del gaps[k]
        starts.pop(i)
    starts.insert(i, a)
    gaps[a] = b

def remove_gap(a: int) -> int:
    i = bisect_left(starts, a)
    assert i < len(starts) and starts[i] == a
    starts.pop(i)
    return gaps.pop(a)

def fit_counts() -> list[int]:
    hist = [0] * 42
    for a in starts:
        length = gaps[a] - a
        hist[min(length, 41)] += 1
    counts = [0] * 42
    running = 0
    for q in range(41, 0, -1):
        running += hist[q]
        counts[q] = running
    return counts

for op, cmd in enumerate(commands, 1):
    if cmd > 0:
        digs, start = answers[ai:ai+2]; ai += 2
        before_trench, before_occupied = trench, occupied
        keep_state = op >= 99000
        if keep_state:
            pre_counts = fit_counts()
            pre_max = max((gaps[a]-a for a in starts), default=0)
            pre_free = sum(gaps[a]-a for a in starts)
            pre_tail = trench - starts[-1] if starts and gaps[starts[-1]] == trench else 0
        else:
            pre_counts = [0] * 42
            pre_max = pre_free = pre_tail = 0
        pre_snapshot = tuple((a,gaps[a]) for a in starts) if digs and 100001 <= op <= 110000 else None
        new_trench = trench + digs * 20
        if digs:
            add_gap(trench, new_trench)
            trench = new_trench
        end = start + cmd
        i = bisect_right(starts, start) - 1
        assert i >= 0 and starts[i] <= start and gaps[starts[i]] >= end, (op,cmd,start,trench)
        pa = starts[i]; pb = gaps[pa]
        parent_len = pb-pa
        remove_gap(pa)
        if pa < start: add_gap(pa, start)
        if end < pb: add_gap(end, pb)
        pid += 1
        active[pid] = (start,cmd)
        occupied += cmd
        if op >= 99000:
            # Candidate event lifetime check uses the residual interval from this action.
            residual = (end,pb) if start == pa else ((pa,start) if end == pb else None)
            rows[op] = {
              'op':op,'pid':pid,'length':cmd,'digs':digs,'trench_before':before_trench,
              'free_before':pre_free,'max_gap_before':pre_max,'tail_before':pre_tail,
              'fit_counts':pre_counts,'selected_start':pa,'selected_end':pb,
              'selected_len':parent_len,'pipe_start':start,'slack':parent_len-cmd,
              'residual':residual,'fit_current':pre_counts[cmd],
              'expanded':bool(digs),
            }
        if pre_snapshot is not None:
            event_pre[op] = set(pre_snapshot)
    else:
        reported = answers[ai]; ai += 1
        p = -cmd
        s,l = active.pop(p)
        assert s == reported, (op,p,reported,s)
        occupied -= l
        add_gap(s,s+l)

assert ai == len(answers)
assert trench == 438920 and occupied == 418757
assert sum(gaps[a]-a for a in starts) + occupied == trench

# The original lineage replay independently records gap birth/closure. Use it to
# verify whether a placement's residual remained a distinct gap until expansion.
episodes = list(csv.DictReader(GAP_EPISODES.open(newline='')))
residual_end = {}
for r in episodes:
    key=(int(r['birth_op']),int(r['start']),int(r['end']))
    residual_end[key]=int(r['end_op'])

expansions=[r for r in rows.values() if r['expanded'] and 100001 <= r['op'] <= 110000]
out=[]
for e in expansions:
    E=e['op']; L=e['length']; pre=set(event_pre[E])
    viable=[]
    for p in rows.values():
        if p['op'] >= E or p['residual'] is None: continue
        ra,rb=p['residual']
        if rb-ra >= L or p['selected_len'] < L: continue
        if (p['op'],ra,rb) not in residual_end or residual_end[(p['op'],ra,rb)] < E: continue
        unique_future_capacity = p['fit_counts'][L] == 1
        no_cost_alt = p['fit_current'] > 1
        tail_fit = p['tail_before'] >= p['length']
        if unique_future_capacity:
            viable.append((p, no_cost_alt, tail_fit))
    viable.sort(key=lambda x: x[0]['op'], reverse=True)
    latest=viable[0] if viable else None
    out.append({
      'expansion_op':E,'length':L,'digs_m':e['digs']*20,'free_before_m':e['free_before'],
      'max_gap_before_m':e['max_gap_before'],'tail_before_m':e['tail_before'],
      'unique_lost_gap_predecessors':len(viable),
      'latest_predecessor_op':latest[0]['op'] if latest else '',
      'latest_predecessor_length':latest[0]['length'] if latest else '',
      'latest_parent_gap_m':latest[0]['selected_len'] if latest else '',
      'latest_residual_m':latest[0]['slack'] if latest else '',
      'latest_fit_current':latest[0]['fit_current'] if latest else '',
      'latest_no_cost_alternative':int(latest[1]) if latest else '',
      'latest_tail_fits_predecessor':int(latest[2]) if latest else '',
      'prior_gap_still_exact_before_expansion':int(any(a==latest[0]['residual'][0] and b==latest[0]['residual'][1] for a,b in pre)) if latest else '',
    })

with EVENTS.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)

with OUT.open('w',newline='') as f:
    cols=['op','pid','length','digs','trench_before','free_before','max_gap_before','tail_before','selected_start','selected_end','selected_len','pipe_start','slack','fit_current']
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for r in rows.values(): w.writerow({k:r[k] for k in cols})

print('replay',len(commands),'commands',pid,'placements','trench',trench,'occupied',occupied)
print('expansions in window',len(expansions),'dug_m',sum(e['digs']*20 for e in expansions))
print('max_gap_fit',sum(e['max_gap_before']>=e['length'] for e in expansions))
print('free_volume_fit',sum(e['free_before']>=e['length'] for e in expansions))
print('with unique lost capacity predecessor',sum(x['unique_lost_gap_predecessors']>0 for x in out))
print('with a no-cost alternative at latest predecessor',sum(x['latest_no_cost_alternative']=='1' for x in out))
print('with tail fitting predecessor',sum(x['latest_tail_fits_predecessor']=='1' for x in out))
print('first 15 predecessor links:')
for x in out[:15]: print(x)
