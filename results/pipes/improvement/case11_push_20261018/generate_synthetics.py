#!/usr/bin/env python3
"""Deterministic fresh LIFO/phase traces for the case11 mixed-phase policy gate."""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent / 'synthetic'
ROOT.mkdir(parents=True, exist_ok=True)
CONFIGS = [
    ('s01_narrow_wide_lifo', 90111, 12000, 0.36, 'narrow_wide', 'lifo'),
    ('s02_narrow_wide_large_lifo', 90112, 12000, 0.42, 'narrow_wide_large', 'lifo'),
    ('s03_narrow_wide_moderate_lifo', 90113, 16000, 0.50, 'narrow_wide', 'moderate_lifo'),
    ('s04_narrow_wide_fifo', 90114, 12000, 0.38, 'narrow_wide', 'fifo'),
    ('s05_narrow_wide_random', 90115, 14000, 0.40, 'narrow_wide', 'random'),
    ('s06_wide_narrow_lifo', 90116, 14000, 0.55, 'wide_narrow', 'lifo'),
    ('s07_narrow_wide_narrow_lifo', 90117, 18000, 0.30, 'three_phase', 'lifo'),
    ('s08_narrow_bimodal_lifo', 90118, 14000, 0.28, 'narrow_bimodal', 'lifo'),
]

def length_for(rng, phase):
    if phase == 'narrow': return rng.randint(1, 8)
    if phase == 'wide': return rng.randint(1, 40)
    if phase == 'wide_large': return rng.randint(9, 40)
    if phase == 'bimodal': return rng.randint(1, 8) if rng.random() < 0.5 else rng.randint(24, 40)
    raise ValueError(phase)

def phase_at(i, count, transition, profile):
    q = i / count
    if profile in ('narrow_wide', 'narrow_wide_large'):
        return 'narrow' if q < transition else ('wide_large' if profile.endswith('_large') else 'wide')
    if profile == 'wide_narrow': return 'wide' if q < transition else 'narrow'
    if profile == 'three_phase':
        if q < transition: return 'narrow'
        if q < 0.70: return 'wide'
        return 'narrow'
    if profile == 'narrow_bimodal': return 'narrow' if q < transition else 'bimodal'
    raise ValueError(profile)

def generate(config):
    name, seed, count, transition, profile, deletion = config
    rng = random.Random(seed)
    active = []
    next_pid = 1
    commands = []
    for i in range(count):
        if not active or rng.random() < 0.65:
            commands.append(str(length_for(rng, phase_at(i, count, transition, profile))))
            active.append(next_pid)
            next_pid += 1
            continue
        if deletion == 'lifo':
            window = max(1, (len(active) + 4) // 5)
            index = len(active) - 1 - rng.randrange(window)
        elif deletion == 'moderate_lifo':
            if rng.random() < 0.75:
                window = max(1, (len(active) + 4) // 5)
                index = len(active) - 1 - rng.randrange(window)
            else: index = rng.randrange(len(active))
        elif deletion == 'fifo':
            window = max(1, (len(active) + 4) // 5)
            index = rng.randrange(window)
        elif deletion == 'random': index = rng.randrange(len(active))
        else: raise ValueError(deletion)
        commands.append(str(-active.pop(index)))
    commands.append('0')
    (ROOT / f'{name}.in').write_text(f'1 {len(commands) - 1}\n' + '\n'.join(commands) + '\n')
    return name, seed, count, sum(int(x) > 0 for x in commands[:-1]), sum(int(x) < 0 for x in commands[:-1]), profile, deletion

if __name__ == '__main__':
    rows = [generate(c) for c in CONFIGS]
    (ROOT / 'suite_manifest.csv').write_text('name,seed,commands,placements,deletions,phase_profile,deletion_profile\n' + '\n'.join(','.join(map(str,r)) for r in rows) + '\n')
