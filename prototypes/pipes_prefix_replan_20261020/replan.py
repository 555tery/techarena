"""Offline public-lifetime repair. Never included in the online submission.

Move individual pipes inside a selected spatial window, preserving every
public lifetime and shared-prefix coordinate. Existing frozen plans are hints.
All changed endpoints are bounded by the old public excavation at birth.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
sys.path.insert(0, str(ROOT / 'prototypes/pipes_open15_overfit_20261019/continuation/local-deps'))
from ortools.sat.python import cp_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', default='11,15')
    ap.add_argument('--left', type=int, default=3)
    ap.add_argument('--right', type=int, default=412)
    ap.add_argument('--prefix', type=int, default=2)
    ap.add_argument('--ratio', type=float, default=1)
    ap.add_argument('--seconds', type=float, default=50)
    ap.add_argument('--name', default='early11')
    ap.add_argument('--source', type=Path, default=ROOT/'prototypes/pipes_g5420_cpu_20261020/solution.cpp')
    a = ap.parse_args()
    dest = HERE / 'repairs' / a.name
    dest.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    j = json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    tables = decode(a.source)
    cases = [int(c)-1 for c in a.cases.split(',')]
    positions = {}
    caps = {}
    bf_caps = {}
    outside = set()
    for ci, case in enumerate(j['cases']):
        commands, pos = tables[ci]
        assert commands == case['commands']
        T = 0
        shadow = None
        if ci in cases:
            import subprocess
            bf = subprocess.run([str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),
                                 'bestfit', str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')],
                                input='\n'.join(map(str, commands+[0]))+'\n', text=True,
                                capture_output=True, check=True).stdout.splitlines()
            shadow = 0
        for step, (c, bid, x) in enumerate(zip(commands, case['block_ids'], pos)):
            if c <= 0:
                continue
            if bid in positions:
                assert positions[bid] == x
            positions[bid] = x
            if ci not in cases:
                outside.add(bid)
                continue
            T = max(T, 20*((x+c+19)//20))
            caps[bid] = min(caps.get(bid, T), T)
            shadow += 20*int(bf[step].split()[0])
            if step < a.prefix:
                bc = 20*int((shadow*a.ratio+1e-8)//20)
                bf_caps[bid] = min(bf_caps.get(bid, bc), bc)

    selected = sorted(bid for bid in caps if bid not in outside and
                      a.left <= positions[bid] and positions[bid]+j['blocks'][bid]['length'] <= a.right)
    assert selected
    fixed = [bid for bid in caps if bid not in set(selected) and
             positions[bid] < a.right and positions[bid]+j['blocks'][bid]['length'] > a.left]
    model = cp_model.CpModel()
    variables = {}
    rect_x, rect_t = [], []
    for bid in selected:
        block = j['blocks'][bid]
        length = block['length']
        cap = min(a.right, caps[bid], bf_caps.get(bid, a.right))-length
        if cap < a.left:
            raise RuntimeError(('empty domain', bid, cap))
        x = model.new_int_var(a.left, cap, f'x{bid}')
        variables[bid] = x
        if a.left <= positions[bid] <= cap:
            model.add_hint(x, positions[bid])
        for l, r, ci in block['intervals']:
            if ci in cases:
                rect_x.append(model.new_fixed_size_interval_var(x, length, f'X{bid}_{ci}'))
                rect_t.append(model.new_fixed_size_interval_var(l, r-l, f'T{bid}_{ci}'))
    for bid in fixed:
        block = j['blocks'][bid]
        for l, r, ci in block['intervals']:
            if ci in cases:
                rect_x.append(model.new_fixed_size_interval_var(positions[bid], block['length'], f'FX{bid}_{ci}'))
                rect_t.append(model.new_fixed_size_interval_var(l, r-l, f'FT{bid}_{ci}'))
    model.add_no_overlap_2d(rect_x, rect_t)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = a.seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20261020
    solver.parameters.log_search_progress = False
    print(json.dumps({'variables': len(variables), 'rectangles': len(rect_x), 'fixed': len(fixed),
                      'prefix_caps': bf_caps, 'window': [a.left, a.right]}), flush=True)
    status = solver.solve(model)
    success = status in (cp_model.FEASIBLE, cp_model.OPTIMAL)
    if success:
        changes = {bid: solver.value(x) for bid, x in variables.items() if solver.value(x) != positions[bid]}
        (dest/'changes.json').write_text(json.dumps(changes, indent=2)+'\n')
    result = {'status': solver.status_name(status), 'success': success,
              'elapsed': time.monotonic()-start, 'changes': len(changes) if success else None,
              'source': str(a.source), 'source_sha256': hashlib.sha256(a.source.read_bytes()).hexdigest(),
              'cases': [c+1 for c in cases], 'window': [a.left,a.right], 'prefix': a.prefix,
              'ratio': a.ratio, 'parameters': str(solver.parameters), 'stats': solver.response_stats(),
              'scope': 'public-only offline exact lifetime feasibility, no hidden inputs'}
    (dest/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
