#!/usr/bin/env python3
"""Independent physical replay for conditioned Open5/Open9 offline plans."""
from pathlib import Path
from bisect import bisect_left
import hashlib, json, math, sys

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parent
DATA = REPO / 'data/pipes/open'
PREFIX = 125

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def replay(k, plan_path):
    toks = (DATA / f'{k}.in').read_text().split()
    weight = float(toks[0]); n = int(toks[1]); cmds = list(map(int, toks[2:2+n]))
    assert len(cmds) == n and len(toks) in (n + 2, n + 3), (k, len(cmds), len(toks), n)
    if len(toks) == n + 3:
        assert toks[-1] == '0', (k, 'unexpected trailing input token', toks[-1])
    pos = list(map(int, Path(plan_path).read_text().split()))
    allocs = sum(c > 0 for c in cmds)
    assert len(pos) == allocs, (k, len(pos), allocs)
    live = []  # sorted (address, pid)
    active = {}
    size = [0]
    pid_at = [0] * n
    next_pid = 1
    peak_volume = 0
    h = 0
    alloc_count = delete_count = 0
    for t, c in enumerate(cmds):
        if c > 0:
            pid = next_pid; next_pid += 1
            p = pos[pid-1]
            assert p >= 0, (k, t, pid, p)
            at = bisect_left(live, (p, pid))
            if at and live[at-1][0] + size[live[at-1][1]] > p:
                raise AssertionError(f'case{k}: overlap at command {t}, pid{pid} with pid{live[at-1][1]}')
            if at < len(live) and p + c > live[at][0]:
                raise AssertionError(f'case{k}: overlap at command {t}, pid{pid} with pid{live[at][1]}')
            live.insert(at, (p, pid)); active[pid] = p
            size.append(c); pid_at[t] = pid
            alloc_count += 1; h = max(h, p + c)
        else:
            pid = -c
            assert pid in active, (k, t, pid, 'deletion of inactive or unknown pid')
            p = active.pop(pid)
            at = bisect_left(live, (p, pid))
            assert at < len(live) and live[at] == (p, pid), (k, t, pid, 'missing live address')
            live.pop(at); delete_count += 1
        peak_volume = max(peak_volume, sum(size[pid] for pid in active))
    T = 20 * math.ceil(h / 20)
    return {'case': k, 'weight': weight, 'commands': n, 'allocations': alloc_count,
            'deletions': delete_count, 'survivors': len(active), 'H': h,
            'T': T, 'peak_live_volume': peak_volume, 'positions_sha256': sha(plan_path)}

def main():
    pins = list(map(int, (ROOT / 'pins.txt').read_text().split()))
    assert len(pins) == PREFIX and len(set(pins)) == PREFIX
    out = {'scope': 'independent command-by-command physical replay; no native harness',
           'prefix_commands': PREFIX, 'pins': pins,
           'cases': {}, 'sha256': {'input5': sha(DATA/'5.in'), 'input9': sha(DATA/'9.in'),
             'pins': sha(ROOT/'pins.txt')}}
    for k in (5, 9):
        plan = ROOT / f'case{k}_positions.txt'
        result = replay(k, plan)
        vals = list(map(int, plan.read_text().split()))
        assert vals[:PREFIX] == pins, (k, 'prefix positions differ from pins')
        toks = (DATA / f'{k}.in').read_text().split()
        cmds = list(map(int, toks[2:2+int(toks[1])]))
        prefix_allocs = []
        pid = 0
        for t, c in enumerate(cmds):
            if c > 0:
                pid += 1
                if t < PREFIX: prefix_allocs.append((pid,c))
        assert len(prefix_allocs) == PREFIX and all(sz == 1 for _,sz in prefix_allocs)
        assert 0 <= vals[0] <= 19
        result['prefix'] = {'allocation_count':len(prefix_allocs), 'all_sizes_one':True,
                            'pid1_address':vals[0], 'pins_match':True}
        out['cases'][str(k)] = result
    (ROOT/'replay-report.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))

if __name__ == '__main__': main()
