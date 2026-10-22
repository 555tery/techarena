#!/usr/bin/env python3
"""Prequential audit of adjacent-pipe removal forecasts; no placement policy."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import random
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('.')
OUT = Path('results/pipes/improvement/coalescence_neighbor_hazard')
SYN = OUT / 'synthetic'
SOLVER = Path('results/pipes/final/bin/solution')
MAX_PIPE_PID = 200001

STREAM_SPECS = [
    ('lifo_uniform_s93017', 'lifo', 'uniform', 93017),
    ('fifo_uniform_s93018', 'fifo', 'uniform', 93018),
    ('random_short_s93019', 'random', 'short', 93019),
    ('random_long_s93020', 'random', 'long', 93020),
    ('phase_lifo_fifo_random_s93021', 'phase', 'bimodal', 93021),
    ('age_hazard_bimodal_s93022', 'age_hazard', 'bimodal', 93022),
    ('shortest_fifo_skew_s93023', 'shortest', 'short', 93023),
    ('longest_random_skew_s93024', 'longest', 'long', 93024),
]
N_SYNTH = 20000

class Fenwick:
    def __init__(self, n: int): self.t = [0] * (n + 1)
    def add(self, i: int, x: int):
        while i < len(self.t): self.t[i] += x; i += i & -i
    def prefix(self, i: int) -> int:
        s = 0
        while i > 0: s += self.t[i]; i -= i & -i
        return s

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def draw_length(rng: random.Random, profile: str) -> int:
    if profile == 'uniform': return rng.randint(1, 40)
    if profile == 'short': return rng.randint(1, 8) if rng.random() < .75 else rng.randint(9, 40)
    if profile == 'long': return rng.randint(25, 40) if rng.random() < .75 else rng.randint(1, 24)
    if profile == 'bimodal': return rng.randint(1, 5) if rng.random() < .5 else rng.randint(30, 40)
    raise ValueError(profile)

def choose_delete(policy: str, active: dict[int, dict], op: int, rng: random.Random) -> int:
    ids = list(active)
    if policy == 'phase':
        phase = (op // 2500) % 3
        policy = ('lifo', 'fifo', 'random')[phase]
    if policy == 'fifo': return min(ids)
    if policy == 'lifo': return max(ids)
    if policy == 'random': return rng.choice(ids)
    if policy == 'shortest':
        best = min(active[p]['length'] for p in ids)
        return rng.choice([p for p in ids if active[p]['length'] == best])
    if policy == 'longest':
        best = max(active[p]['length'] for p in ids)
        return rng.choice([p for p in ids if active[p]['length'] == best])
    if policy == 'age_hazard':
        weights = [1.0 + (op - active[p]['birth_op']) / 500.0 for p in ids]
        return rng.choices(ids, weights=weights, k=1)[0]
    raise ValueError(policy)

def make_stream(policy: str, profile: str, seed: int, n: int = N_SYNTH) -> list[int]:
    rng = random.Random(seed)
    commands: list[int] = []
    active: dict[int, dict] = {}
    next_pid = 1
    for op in range(1, n + 1):
        if len(active) < 80:
            do_place = True
        elif len(active) > 500:
            do_place = False
        else:
            do_place = rng.random() < .5
        if do_place:
            length = draw_length(rng, profile)
            commands.append(length)
            active[next_pid] = {'length': length, 'birth_op': op}
            next_pid += 1
        else:
            pid = choose_delete(policy, active, op, rng)
            commands.append(-pid)
            del active[pid]
    return commands

def age_bin(age: int) -> str:
    if age <= 1: return '0-1'
    if age <= 4: return '2-4'
    if age <= 16: return '5-16'
    if age <= 64: return '17-64'
    return '65+'

def length_bin(length: int) -> str:
    if length <= 4: return '1-4'
    if length <= 12: return '5-12'
    if length <= 24: return '13-24'
    return '25-40'

def rank_bin(frac: float) -> str:
    if frac < .05: return 'newest5'
    if frac < .25: return 'newest25'
    if frac < .75: return 'middle'
    if frac < .95: return 'oldest25'
    return 'oldest5'

def recent_mode(hist: list[dict]) -> str:
    vals = [x['rank_frac'] for x in hist[-8:]]
    if not vals: return 'none'
    mean = sum(vals) / len(vals)
    if mean <= .10: return 'lifo_like'
    if mean >= .90: return 'fifo_like'
    return 'mixed'

def run_baseline_and_extract(name: str, commands: list[int], input_path: Path | None):
    command_path = SYN / f'{name}.commands' if input_path else OUT / 'case15.commands'
    answer_path = SYN / f'{name}.answer.txt' if input_path else OUT / 'case15.baseline_answer.txt'
    command_text = '\n'.join(map(str, commands + [0])) + '\n'
    command_path.write_text(command_text)
    started = time.perf_counter()
    proc = subprocess.run([str(SOLVER)], input=command_text, text=True, capture_output=True, check=True)
    wall = time.perf_counter() - started
    answer_path.write_text(proc.stdout)
    responses = proc.stdout.splitlines()
    if len(responses) != len(commands):
        raise RuntimeError(f'{name}: {len(responses)} solver responses for {len(commands)} commands')
    next_positive = [len(commands) + 1] * (len(commands) + 1)
    nxt = len(commands) + 1
    for op in range(len(commands), 0, -1):
        next_positive[op] = nxt
        if commands[op-1] > 0: nxt = op
    # List deletion targets before each next positive placement.
    deleted_before_next: dict[int, set[int]] = {}
    for op, command in enumerate(commands, 1):
        if command <= 0: continue
        nxt_pos = next_positive[op]
        if nxt_pos <= len(commands):
            deleted_before_next[op] = {-commands[j-1] for j in range(op+1, nxt_pos) if commands[j-1] < 0}
        else:
            deleted_before_next[op] = set()
    active: dict[int, dict] = {}
    by_start: dict[int, int] = {}
    by_end: dict[int, int] = {}
    fenwick = Fenwick(MAX_PIPE_PID)
    active_count = 0
    pid = 0
    placement_count = 0
    recent_deletes: list[dict] = []
    rows: list[dict] = []
    trench = 0
    response_i = 0
    for op, command in enumerate(commands, 1):
        tokens = responses[response_i].split(); response_i += 1
        if command > 0:
            if len(tokens) != 2: raise RuntimeError(f'{name}: invalid placement response at {op}')
            digs, start = map(int, tokens)
            trench += 20 * digs
            left_pid = by_end.get(start)
            right_pid = by_start.get(start + command)
            targets = []
            if left_pid is not None: targets.append(('left', left_pid))
            if right_pid is not None and right_pid != left_pid: targets.append(('right', right_pid))
            nxt_pos = next_positive[op]
            for side, target_pid in targets:
                target = active[target_pid]
                newer = active_count - fenwick.prefix(target_pid)
                rank_frac = newer / max(1, active_count - 1)
                label = target_pid in deleted_before_next.get(op, set())
                rows.append({
                    'stream': name, 'op': op, 'current_length': command,
                    'side': side, 'target_pid': target_pid,
                    'target_length': target['length'], 'target_age_ops': op - target['birth_op'],
                    'target_age_placements': placement_count - target['birth_placement'],
                    'active_count': active_count, 'target_newer_rank': newer,
                    'target_rank_frac': rank_frac, 'target_rank_bin': rank_bin(rank_frac),
                    'target_length_bin': length_bin(target['length']),
                    'target_age_bin': age_bin(op - target['birth_op']),
                    'recent_delete_count': len(recent_deletes),
                    'recent_delete_rank_mean8': (sum(x['rank_frac'] for x in recent_deletes[-8:]) / min(8, len(recent_deletes))) if recent_deletes else None,
                    'recent_mode': recent_mode(recent_deletes),
                    'last_delete_rank_frac': recent_deletes[-1]['rank_frac'] if recent_deletes else None,
                    'last_delete_age_ops': recent_deletes[-1]['age_ops'] if recent_deletes else None,
                    'next_positive_op': nxt_pos,
                    'deletes_before_next_positive': max(0, nxt_pos - op - 1) if nxt_pos <= len(commands) else 0,
                    'label_neighbor_removed_before_next_placement': int(label),
                    'resolve_op': nxt_pos,
                })
            if start < 0 or start + command > trench:
                raise RuntimeError(f'{name}: pipe placement outside trench at op {op}')
            # Check non-overlap with current intervals.
            for p, x in active.items():
                if start < x['start'] + x['length'] and x['start'] < start + command:
                    raise RuntimeError(f'{name}: overlap at op {op} with PID {p}')
            pid += 1; placement_count += 1
            info = {'start': start, 'length': command, 'birth_op': op, 'birth_placement': placement_count}
            active[pid] = info; by_start[start] = pid; by_end[start + command] = pid
            fenwick.add(pid, 1); active_count += 1
        elif command < 0:
            if len(tokens) != 1: raise RuntimeError(f'{name}: invalid removal response at {op}')
            start = int(tokens[0]); target_pid = -command
            info = active.get(target_pid)
            if info is None: raise RuntimeError(f'{name}: invalid PID {target_pid} at {op}')
            if info['start'] != start: raise RuntimeError(f'{name}: wrong removal start for PID {target_pid} at {op}')
            newer = active_count - fenwick.prefix(target_pid)
            rank_frac = newer / max(1, active_count - 1)
            recent_deletes.append({'pid': target_pid, 'length': info['length'], 'age_ops': op-info['birth_op'], 'rank_frac': rank_frac, 'op': op})
            by_start.pop(info['start']); by_end.pop(info['start'] + info['length'])
            active.pop(target_pid); fenwick.add(target_pid, -1); active_count -= 1
        else:
            raise ValueError('zero terminator must not be in commands')
    return rows, {'name':name,'input_sha256':sha(input_path) if input_path else None,
                  'commands_sha256':sha(command_path),'answer_sha256':sha(answer_path),
                  'operations':len(commands),'placements':placement_count,'rows':len(rows),
                  'solver_wall_seconds':wall,'solver_returncode':proc.returncode,
                  'trench_m':trench,'final_active':active_count,'solver_stderr':proc.stderr}

def prequential_metrics(rows: list[dict]) -> dict:
    by_op: dict[int,list[dict]] = defaultdict(list)
    for row in rows:
        if row['resolve_op'] <= max(r['op'] for r in rows): by_op[row['op']].append(row)
    global_n=global_y=0
    individual=defaultdict(lambda:[0,0])
    context=defaultdict(lambda:[0,0])
    predictions=[]
    pending=[]
    prior_command_stats=[]
    # When a new placement sample arrives, the prior sample's outcome is now observed.
    for op in sorted(by_op):
        if pending:
            for old in pending:
                key=(old['target_length_bin'],old['target_age_bin'])
                ckey=key+(old['target_rank_bin'],old['recent_mode'])
                y=old['label_neighbor_removed_before_next_placement']
                global_n+=1; global_y+=y
                individual[key][0]+=1; individual[key][1]+=y
                context[ckey][0]+=1; context[ckey][1]+=y
            pending=[]
        batch=by_op[op]
        # Same global prior before any sample from this decision is labeled.
        pglobal=(global_y+1)/(global_n+2)
        for row in batch:
            ikey=(row['target_length_bin'],row['target_age_bin'])
            ckey=ikey+(row['target_rank_bin'],row['recent_mode'])
            ni,yi=individual[ikey]
            p_ind=(yi+20*pglobal)/(ni+20)
            nc,yc=context[ckey]
            p_ctx=(yc+20*p_ind)/(nc+20)
            n=row['active_count']
            # Strictly past estimate of deletion/placement ratio over the previous 64 commands.
            # Only commands before this decision are included; generator-level future mode is hidden.
            past_ops=[x for x in prior_command_stats if op-64 <= x[0] < op]
            dels=sum(1 for _,kind in past_ops if kind=='delete')
            places=sum(1 for _,kind in past_ops if kind=='place')
            expected_dels=(dels+1)/(places+1)
            p_uniform=min(.999999, expected_dels/max(1,n))
            predictions.append({**row,'p_global':pglobal,'p_uniform_active':p_uniform,'p_individual_hazard':p_ind,'p_rank_recent':p_ctx})
            pending.append(row)
        # The full input is not consulted here; rows already include only current/past features.
        prior_command_stats.extend((row['op'],'place') for row in batch[:1])
        # Insert intervening operations as observed past using the provided label horizon count.
        # Exact delete/place ratio is computed in a separate feature below from stream commands only
        # for audit; p_uniform currently sees placement samples, not future events.
    def score(key):
        xs=[x for x in predictions if key in x]
        if not xs: return {'n':0,'positive_rate':None,'brier':None,'logloss':None}
        ys=[x['label_neighbor_removed_before_next_placement'] for x in xs]
        ps=[max(1e-6,min(1-1e-6,x[key])) for x in xs]
        brier=sum((p-y)**2 for p,y in zip(ps,ys))/len(xs)
        ll=-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in zip(ps,ys))/len(xs)
        return {'n':len(xs),'positive_rate':sum(ys)/len(ys),'brier':brier,'logloss':ll}
    result={'global_prior':score('p_global'),'uniform_active_random':score('p_uniform_active'),
            'individual_length_age_hazard':score('p_individual_hazard'),'rank_recent_context':score('p_rank_recent'),
            'predictions':predictions}
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True); SYN.mkdir(parents=True,exist_ok=True)
    raw=Path('data/pipes/open/15.in').read_text().split()
    n=int(raw[1]); case15=[int(x) for x in raw[2:2+n]]
    case_rows, case_meta=run_baseline_and_extract('case15',case15,None)
    all_rows=[('case15',case_rows)]
    manifest=[]
    for name,policy,profile,seed in STREAM_SPECS:
        commands=make_stream(policy,profile,seed)
        in_path=SYN/f'{name}.in'
        in_path.write_text('1.0 '+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n')
        rows,meta=run_baseline_and_extract(name,commands,in_path)
        meta.update({'deletion_policy':policy,'length_profile':profile,'seed':seed})
        manifest.append(meta); all_rows.append((name,rows))
    predictions_by_stream={}
    for name,rows in all_rows:
        predictions_by_stream[name]=prequential_metrics(rows)
    # Exact event around C window.
    event=[r for r in case_rows if r['op']==100146 and r['target_pid']==80252]
    if len(event)!=1: raise RuntimeError(f'expected one target observation at 100146, found {len(event)}')
    # Aggregate per-stream forecast scores, and record event predictions.
    summary={}
    for name,metrics in predictions_by_stream.items():
        summary[name]={k:v for k,v in metrics.items() if k!='predictions'}
    event_row=next((x for x in predictions_by_stream['case15']['predictions'] if x['op']==100146 and x['target_pid']==80252),None)
    if event_row is None: raise RuntimeError('target event has no prequential prediction')
    output={'case15_replay':case_meta,'synthetic_streams':manifest,'stream_metrics':summary,
            'target_event':event_row,
            'pooled_metrics':{}}
    for metric in ('p_global','p_uniform_active','p_individual_hazard','p_rank_recent'):
        xs=[x for stream in predictions_by_stream.values() for x in stream['predictions']]
        ys=[x['label_neighbor_removed_before_next_placement'] for x in xs]
        ps=[max(1e-6,min(1-1e-6,x[metric])) for x in xs]
        output['pooled_metrics'][metric]={'n':len(xs),'positive_rate':sum(ys)/len(ys),
            'brier':sum((p-y)**2 for p,y in zip(ps,ys))/len(xs),
            'logloss':-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in zip(ps,ys))/len(xs)}
    (OUT/'predictive_metrics.json').write_text(json.dumps(output,indent=2)+'\n')
    # Full compact row file: features were observed at decisions; labels resolve at next positive.
    with (OUT/'neighbor_samples.csv').open('w',newline='') as f:
        keys=['stream','op','current_length','side','target_pid','target_length','target_age_ops','target_age_placements','active_count','target_newer_rank','target_rank_frac','target_rank_bin','target_length_bin','target_age_bin','recent_delete_count','recent_delete_rank_mean8','recent_mode','last_delete_rank_frac','last_delete_age_ops','next_positive_op','deletes_before_next_positive','label_neighbor_removed_before_next_placement']
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
        for _,rows in all_rows:
            for r in rows: w.writerow({k:r.get(k) for k in keys})
    man={'title':'Past-only nearest-neighbor deletion forecast audit','frozen_source_sha256':sha(Path('results/pipes/final/solution.cpp')),
         'canonical_source_sha256':sha(Path('src/pipes.cpp')),'frozen_binary_sha256':sha(SOLVER),
         'case15_input_sha256':sha(Path('data/pipes/open/15.in')),'synthetic_spec':{'n_operations':N_SYNTH,'active_bounds':[80,500],
             'placement_probability_when_within_bounds':0.5,'streams':[{'name':x[0],'policy':x[1],'length_profile':x[2],'seed':x[3]} for x in STREAM_SPECS]},
         'output_sha256':sha(OUT/'predictive_metrics.json'),'rows_sha256':sha(OUT/'neighbor_samples.csv'),
         'metrics_method':'strict prequential: previous placement labels resolve before scoring the next placement; context feature from max 8 prior deletion ranks; no future input used in predictors.'}
    (OUT/'manifest.json').write_text(json.dumps(man,indent=2)+'\n')
    print(json.dumps({'target_event':event_row,'pooled_metrics':output['pooled_metrics'],'stream_metrics':summary,'synthetic_files':[m['name'] for m in manifest]},indent=2))

if __name__=='__main__': main()
