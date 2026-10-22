#!/usr/bin/env python3
"""Tiny independent legality and export checks; never reads full train/dev/final streams."""
import argparse
import json
import math
import subprocess
from pathlib import Path

base = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--solver', type=Path, default=base / 'bin/zero')
p.add_argument('--weights', type=Path, default=base / 'training/zero.weights')
p.add_argument('--out', type=Path, default=base / 'training/tiny_verification.json')
a = p.parse_args()
commands = [8,12,7,13,-2,-4,15,10,-1,20,5,-3,11,-5,7,19,-6,17,2,-7,18,12,-8,9,4,-9,20,6,13,-10,1,40]

def run(binary, seq, extra=()):
    result = subprocess.run([str(binary), *map(str, extra)], input='\n'.join(map(str, seq + [0])) + '\n',
                            text=True, capture_output=True, check=True, cwd=base)
    return result.stdout, result.stderr

def legality(seq, output):
    lines = output.splitlines()
    assert len(lines) == len(seq)
    live = {}; pid = 0; trench = 0
    for command, line in zip(seq, lines):
        values = list(map(int, line.split()))
        if command > 0:
            assert len(values) == 2
            digs, start = values
            assert digs >= 0 and start >= 0
            assert digs == (max(0, start + command - trench) + 19) // 20
            trench += digs * 20
            assert start + command <= trench
            assert all(start + command <= pos or pos + length <= start for pos, length in live.values())
            pid += 1; live[pid] = (start, command)
        else:
            assert len(values) == 1 and values[0] == live[-command][0]
            del live[-command]
    return {'F': sum(length for _, length in live.values()), 'T': trench}

if not a.weights.exists():
    a.weights.write_text('0\n' * 105)
stdout, stderr = run(a.solver.resolve(), commands)
native, _ = run(base / 'bin/check', commands, [a.weights.resolve()])
assert stdout == native, 'embedded/native checkpoint action mismatch'
terminal = legality(commands, stdout)
prefix = commands[:20]
left, _ = run(a.solver.resolve(), prefix + [1,2,3,4])
right, _ = run(a.solver.resolve(), prefix + [40,39,38,37])
assert left.splitlines()[:len(prefix)] == right.splitlines()[:len(prefix)]

control, _ = run(base / 'bin/control', commands)
zero, _ = run(base / 'bin/check', commands, [base / 'training/zero.weights'])
assert control == zero, 'zero actor does not reproduce same physical BF control'
run(base / 'bin/check', commands)
weights = [math.sin(j+1)*0.3 for j in range(105)]
max_error = 0
rows = (base / 'parity_rows.tsv').read_text().splitlines()
for row in rows:
    values = list(map(float, row.split()))
    cpp, features = values[0], values[1:]
    predicted = weights[-1]
    for hidden in range(4):
        z = weights[96+hidden]
        for j in range(24):
            z += weights[hidden*24+j]*features[j]
        predicted += weights[100+hidden]*math.tanh(z)
    max_error = max(max_error, abs(predicted-cpp))
assert max_error < 1e-12
report = {'scope': 'tiny fixtures only, excluded from training budget', 'commands': len(commands),
          'legality': True, 'native_export_action_parity': True, 'zero_actor_control_parity': True,
          'shared_prefix_causality': True, 'score_parity_rows': len(rows),
          'score_parity_max_abs_error': max_error, 'terminal': terminal,
          'solver_stderr': stderr.strip()}
a.out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, sort_keys=True))
