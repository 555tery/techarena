"""Coordinator's independent protocol, prefix causality, and replay checks."""
import hashlib
import json
from pathlib import Path
import random
import subprocess

ROOT = Path(__file__).resolve().parent
LABELS = ['incumbent', 'planner_off', 'planner_on', 'learned_off', 'learned_gen8']


def check(commands, output):
    rows = output.strip().splitlines()
    assert len(rows) == len(commands), (len(rows), len(commands))
    active, born, trench = {}, 0, 0
    for command, row in zip(commands, rows):
        fields = list(map(int, row.split()))
        if command > 0:
            assert len(fields) == 2
            digs, start = fields
            assert digs >= 0 and start >= 0
            trench += 20 * digs
            assert start + command <= trench <= 100000000
            assert all(start + command <= left or start >= left + size
                       for left, size in active.values())
            born += 1
            active[born] = (start, command)
        else:
            assert len(fields) == 1 and -command in active
            assert fields[0] == active[-command][0]
            del active[-command]
    return {'F': sum(size for _, size in active.values()), 'T': trench}


def main():
    rng = random.Random(2026101809)
    prefix, active, born = [], [], 0
    for _ in range(512):
        if active and rng.random() < .38:
            pid = active.pop(rng.randrange(len(active)))
            prefix.append(-pid)
        else:
            born += 1
            active.append(born)
            prefix.append(rng.randrange(1, 41))
    paths = [prefix + [3, 37, 3, 37] * 16,
             prefix + [-pid for pid in reversed(active)] + [40, 1, 1, 39] * 16]
    report = {'fixture_seed': 2026101809, 'prefix_length': len(prefix), 'variants': {}}
    for label in LABELS:
        outputs, totals = [], []
        for commands in paths:
            text = '\n'.join(map(str, commands + [0])) + '\n'
            p = subprocess.run([str(ROOT / 'builds' / label / 'solver')], input=text,
                               text=True, capture_output=True, timeout=30, check=True)
            outputs.append(p.stdout)
            totals.append(check(commands, p.stdout))
        assert outputs[0].splitlines()[:len(prefix)] == outputs[1].splitlines()[:len(prefix)]
        repeat = subprocess.run([str(ROOT / 'builds' / label / 'solver')],
                                input='\n'.join(map(str, paths[0] + [0])) + '\n',
                                text=True, capture_output=True, timeout=30, check=True)
        assert repeat.stdout == outputs[0]
        report['variants'][label] = {'legal': True, 'prefix_equal': True,
            'deterministic': True, 'totals': totals,
            'transcript_sha256': [hashlib.sha256(s.encode()).hexdigest() for s in outputs]}
    (ROOT / 'audit-fixtures.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
