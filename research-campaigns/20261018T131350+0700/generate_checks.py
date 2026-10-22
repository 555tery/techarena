"""Fresh mechanism-based traces; independent of Open inputs and solver results."""
import argparse
import hashlib
import json
from pathlib import Path
import random
from collections import deque

ROOT = Path(__file__).resolve().parent
FAMILIES = ['recent_growth_shift', 'recent_stationary', 'fifo_size_drift',
            'random_mixture', 'cohort_release', 'repeated_sizes']


def specs(split):
    namespace = 98173501 if split == 'dev' else 761490013
    variants = 1 if split == 'dev' else 2
    values = []
    for index, family in enumerate(FAMILIES):
        for variant in range(variants):
            seed = namespace + 7919 * index + 109 * variant
            rng = random.Random(seed)
            n = 12000 if split == 'dev' else ([40000, 200000][variant] if index < 2 else [20000, 60000][variant])
            values.append({'id': f'{split}_{index:02}_{variant}_{family}', 'family': family,
                'seed': seed, 'operations': n, 'short_max': rng.choice([3, 6, 9, 12]),
                'large_min': rng.choice([10, 12, 16]), 'transition_fraction': rng.uniform(.25, .7),
                'recent_span': rng.choice([12, 32, 80, 192]), 'old_delete_probability': rng.choice([.01, .04, .12]),
                'insert_first': rng.uniform(.66, .86), 'insert_second': rng.uniform(.49, .65)})
    return values


def generate(spec):
    rng = random.Random(spec['seed'])
    alive, positions, commands, births = [], {}, [], deque()
    next_id = 0
    last_size = 1
    pending = deque()
    lengths = {}

    def erase(pid):
        pos = positions.pop(pid)
        last = alive.pop()
        if pos < len(alive):
            alive[pos] = last
            positions[last] = pos
        commands.append(-pid)

    while len(commands) < spec['operations']:
        fraction = len(commands) / spec['operations']
        early = fraction < spec['transition_fraction']
        chance = spec['insert_first'] if early else spec['insert_second']
        family = spec['family']
        if family == 'recent_stationary':
            chance = .53
        if family == 'random_mixture':
            chance = .59
        if pending and len(alive) > 2:
            pid = pending.popleft()
            if pid in positions:
                erase(pid)
                continue
        if len(alive) < 4 or rng.random() < chance:
            if family == 'recent_growth_shift':
                lo, hi = (1, spec['short_max']) if early else (spec['large_min'], 40)
            elif family == 'fifo_size_drift':
                lo, hi = (1, 12) if early else (4, 40)
            elif family == 'random_mixture':
                lo, hi = (1, 5) if rng.random() < .6 else (18, 40)
            else:
                lo, hi = 1, 40
            if family == 'repeated_sizes' and rng.random() < .85:
                length = last_size
            else:
                length = rng.randint(lo, hi)
            last_size = length
            next_id += 1
            lengths[next_id] = length
            positions[next_id] = len(alive)
            alive.append(next_id)
            births.append(next_id)
            commands.append(length)
            continue
        if family == 'fifo_size_drift':
            while births and births[0] not in positions:
                births.popleft()
            pid = births[0]
        elif family in ['recent_growth_shift', 'recent_stationary', 'repeated_sizes'] and rng.random() >= spec['old_delete_probability']:
            pid = None
            for attempt in range(32):
                trial = max(1, next_id - rng.randrange(spec['recent_span']))
                if trial in positions:
                    pid = trial
                    break
            if pid is None:
                pid = rng.choice(alive)
        else:
            pid = rng.choice(alive)
        if family == 'cohort_release' and rng.random() < .15:
            pending.extend(i for i in range(max(1, pid-4), pid+5) if i != pid and i in positions)
        erase(pid)
    assert len(commands) == spec['operations'] and alive
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['dev','sealed'], required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    directory = ROOT / 'fresh_checks' / args.split
    directory.mkdir(parents=True, exist_ok=True)
    design = directory / 'design.json'
    values = specs(args.split)
    encoded = json.dumps({'split':args.split,'families':FAMILIES,'specs':values,
        'independent_inputs':True,'open_inputs_read':False,'solver_results_read':False},indent=2)+'\n'
    if design.exists() and design.read_text() != encoded:
        raise ValueError('refusing to replace preregistered design')
    design.write_text(encoded)
    if args.prepare_only:
        print(json.dumps({'split':args.split,'cases':len(values),'inputs_generated':False}))
        return
    rows = []
    for spec in values:
        commands = generate(spec)
        path = directory / (spec['id']+'.in')
        data = ('1\n'+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n').encode()
        if path.exists():
            raise ValueError('refusing to overwrite generated input')
        path.write_bytes(data)
        rows.append({**spec,'file':str(path),'sha256':hashlib.sha256(data).hexdigest()})
    (directory/'manifest.json').write_text(json.dumps({'cases':rows,'case_count':len(rows)},indent=2)+'\n')
    print(json.dumps({'split':args.split,'cases':len(values),'directory':str(directory)}))


if __name__ == '__main__':
    main()
