#!/usr/bin/env python3
"""Reconstruct the official case-15 baseline trace and fragmentation statistics."""
from collections import Counter, defaultdict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[5]
INPUT = ROOT / 'data/pipes/open/15.in'
OUTPUT = ROOT / 'results/pipes/final/open-run-alternating-delete-parity/runs/15/judge_output.txt'
OUT = Path(__file__).resolve().with_name('trace_diagnosis.json')

vals = list(map(int, INPUT.read_text().split()))
weight, n = vals[:2]
cmds = vals[2:2+n]
responses = list(map(int, OUTPUT.read_text().split()))
assert len(cmds) == n

# A small Fenwick tree yields active-PID ranks at each removal.
fenwick = [0] * (n + 3)
def addbit(i, d):
    while i < len(fenwick):
        fenwick[i] += d
        i += i & -i
def prefix(i):
    s = 0
    while i:
        s += fenwick[i]
        i -= i & -i
    return s

active = {}
pipe_id = 0
placements = 0
active_len = 0
max_active_len = 0
trench = 0
occ = bytearray()
response_i = 0
expanded_events = []
phase = defaultdict(lambda: {'ops':0,'placements':0,'removals':0,'dug_m':0,'dig_events':0,'dig_with_enough_total_free':0,'dig_with_low_total_free':0,'added_length':0,'removed_length':0})
length_add = Counter()
length_del = Counter()
length_life = defaultdict(list)
rank_milli = []
rank_by_len = defaultdict(list)
lifetime_ops = []
first_dig = None
last_dig = None
samples = []

for op, cmd in enumerate(cmds, start=1):
    ph = (op - 1) // 10000
    phase[ph]['ops'] += 1
    if cmd > 0:
        digs, start = responses[response_i:response_i+2]
        response_i += 2
        free_before = trench - active_len
        placements += 1
        pid = pipe_id + 1
        pipe_id = pid
        if digs:
            if free_before >= cmd:
                phase[ph]['dig_with_enough_total_free'] += 1
            else:
                phase[ph]['dig_with_low_total_free'] += 1
            phase[ph]['dig_events'] += 1
            phase[ph]['dug_m'] += digs * 20
            event = {'op':op,'pid':pid,'length':cmd,'digs':digs,'free_before':free_before,'active_before':active_len,'trench_before':trench,'max_gap_before':None}
            if first_dig is None: first_dig = op
            last_dig = op
            expanded_events.append(event)
        old_trench = trench
        trench += digs * 20
        if trench > len(occ): occ.extend(b'\0' * (trench - len(occ)))
        end = start + cmd
        assert 0 <= start and end <= trench, (op, start, cmd, trench)
        assert not any(occ[start:end]), (op, pid, start, cmd)
        occ[start:end] = b'\1' * cmd
        active[pid] = (start, cmd, op, placements)
        addbit(pid, 1)
        active_len += cmd
        max_active_len = max(max_active_len, active_len)
        phase[ph]['placements'] += 1
        phase[ph]['added_length'] += cmd
        length_add[cmd] += 1
        if digs:
            expanded_events[-1]['trench_after'] = trench
            expanded_events[-1]['end'] = end
            expanded_events[-1]['rounded_peak_lb_after'] = 20*((max_active_len+19)//20)
    elif cmd < 0:
        shift = responses[response_i]
        response_i += 1
        pid = -cmd
        assert pid in active, (op, pid, 'not active')
        start, length, born_op, born_place = active.pop(pid)
        assert start == shift, (op, pid, shift, start)
        assert all(occ[start:start+length]), (op, pid, start, length)
        occ[start:start+length] = b'\0' * length
        before_count = sumbit = prefix(pid)
        live_n = len(active) + 1
        newest_rank = live_n - before_count
        rank_permille = round(1000 * newest_rank / live_n)
        age_places = placements - born_place
        age_ops = op - born_op
        rank_milli.append(rank_permille)
        rank_by_len[length].append(rank_permille)
        lifetime_ops.append(age_ops)
        length_life[length].append(age_places)
        length_del[length] += 1
        phase[ph]['removals'] += 1
        phase[ph]['removed_length'] += length
        active_len -= length
        addbit(pid, -1)
    else:
        break

    if op % 10000 == 0 or op == n:
        free = trench - active_len
        gap_count = 0
        largest = 0
        tail = 0
        gap_hist = Counter()
        run = 0
        for cell in occ:
            if cell:
                if run:
                    gap_count += 1; largest = max(largest, run); gap_hist[run] += 1
                    run = 0
            else:
                run += 1
        if run:
            gap_count += 1; largest = max(largest, run); tail = run; gap_hist[run] += 1
        samples.append({'op':op,'placements':placements,'active_pipes':len(active),'active_m':active_len,'trench_m':trench,'free_m':free,'peak_active_seen_m':max_active_len,'lb_from_peak_m':20*((max_active_len+19)//20),'gap_count':gap_count,'largest_gap_m':largest,'tail_gap_m':tail,'free_in_gaps_lt_40_m':sum(k*v for k,v in gap_hist.items() if k<40),'gap_count_lt_40':sum(v for k,v in gap_hist.items() if k<40),'dig_events_so_far':sum(z['dig_events'] for z in phase.values()),'dig_m_so_far':sum(z['dug_m'] for z in phase.values())})

assert response_i == len(responses), (response_i,len(responses))

phase_rows=[]
for ph in sorted(phase):
    d=phase[ph]
    phase_rows.append({'ops':f'{ph*10000+1}-{min((ph+1)*10000,n)}',**d})

def quantile(xs,q):
    if not xs: return None
    ys=sorted(xs)
    return ys[int((len(ys)-1)*q)]
summary={
 'input_sha256':__import__('hashlib').sha256(INPUT.read_bytes()).hexdigest(),
 'baseline_output_sha256':__import__('hashlib').sha256(OUTPUT.read_bytes()).hexdigest(),
 'weight':weight,'commands':n,'placements':placements,'removals':sum(cmd<0 for cmd in cmds),
 'max_pipe_length':max(length_add),'length_frequency':dict(sorted(length_add.items())),
 'trench_m':trench,'final_active_m':active_len,'peak_active_m':max_active_len,'peak_lb_m':20*((max_active_len+19)//20),'excess_over_peak_lb_m':trench-20*((max_active_len+19)//20),
 'final_free_m':trench-active_len,'first_dig_op':first_dig,'last_dig_op':last_dig,
 'dig_events':sum(d['dig_events'] for d in phase.values()),'dug_m':sum(d['dug_m'] for d in phase.values()),
 'dig_with_enough_total_free':sum(d['dig_with_enough_total_free'] for d in phase.values()),'dig_with_low_total_free':sum(d['dig_with_low_total_free'] for d in phase.values()),
 'removal_rank_newest_permille':{'mean':sum(rank_milli)/len(rank_milli),'p10':quantile(rank_milli,.1),'median':quantile(rank_milli,.5),'p90':quantile(rank_milli,.9)},
 'removal_rank_by_length':{str(k):{'n':len(v),'mean':sum(v)/len(v),'median':quantile(v,.5)} for k,v in sorted(rank_by_len.items())},
 'lifetime_placements_by_length':{str(k):{'n':len(v),'mean':sum(v)/len(v),'median':quantile(v,.5),'p10':quantile(v,.1),'p90':quantile(v,.9)} for k,v in sorted(length_life.items())},
 'lifetime_ops':{'mean':sum(lifetime_ops)/len(lifetime_ops),'median':quantile(lifetime_ops,.5),'p10':quantile(lifetime_ops,.1),'p90':quantile(lifetime_ops,.9)},
 'phases':phase_rows,'samples':samples,'expansion_events':expanded_events,
}
OUT.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('phases','samples','expansion_events','length_frequency','removal_rank_by_length','lifetime_placements_by_length')},indent=2))
print('\nPHASES')
for r in phase_rows: print(r)
print('\nSAMPLES')
for s in samples: print(s)
