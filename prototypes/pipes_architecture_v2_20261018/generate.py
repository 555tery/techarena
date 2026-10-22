"""Coordinator-owned synthetic data. No reads from official or historical tests."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import random
import secrets
import time

ROOT = Path(__file__).resolve().parent
TRAIN_FAMILIES = ['stationary_churn', 'recent_growth', 'cohort_retirement',
                  'size_blocks', 'fifo_bursts', 'mixed_survival']
FINAL_FAMILIES = ['reversed_modes', 'noisy_cohorts', 'delayed_echo',
                  'ambiguous_shift', 'anchor_switch', 'heavy_tail_rank']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_stream(family, n, seed):
    rng = random.Random(seed)
    active, positions, lengths = [], {}, [0]
    oldest = collections.deque()
    newest = []
    commands = []
    phase_width = rng.randint(90, 260)
    size_low, size_high = rng.randint(1, 5), rng.randint(25, 40)
    profile = rng.randrange(3)

    def add(length):
        pid = len(lengths)
        lengths.append(length)
        positions[pid] = len(active)
        active.append(pid)
        oldest.append(pid)
        newest.append(pid)
        commands.append(length)

    def remove(mode, phase):
        if mode == 'oldest':
            while oldest[0] not in positions:
                oldest.popleft()
            pid = oldest.popleft()
        elif mode == 'newest':
            while newest[-1] not in positions:
                newest.pop()
            pid = newest.pop()
        else:
            sample = [active[rng.randrange(len(active))] for _ in range(12)]
            if mode == 'recent':
                pid = max(sample)
            elif mode == 'old':
                pid = min(sample)
            elif mode == 'cohort':
                parity = phase % 2
                eligible = [p for p in sample if p % 2 == parity]
                pid = max(eligible or sample)
            elif mode == 'short':
                pid = min(sample, key=lambda p: (lengths[p], -p))
            else:
                pid = sample[0]
        index = positions.pop(pid)
        last = active.pop()
        if index < len(active):
            active[index] = last
            positions[last] = index
        commands.append(-pid)

    for step in range(n):
        phase, within = divmod(step, phase_width)
        ratio = step / n
        p_delete, mode = .34, 'random'
        if family == 'stationary_churn':
            length = rng.randint(1, 40) if profile == 0 else (
                rng.randint(1, 11) if profile == 1 else rng.randint(18, 40))
            p_delete = (.22, .38, .46)[seed % 3]
        elif family == 'recent_growth':
            length = rng.randint(1, 6) if ratio < .35 else rng.randint(5, 40)
            mode, p_delete = 'recent', .42 if ratio < .7 else .2
        elif family == 'cohort_retirement':
            length = min(40, 2 + (phase % 7) * (2 + seed % 4))
            mode, p_delete = 'cohort', .78 if within > phase_width * .65 else .04
        elif family == 'size_blocks':
            length = min(40, size_low + (phase % 6) * (2 + seed % 5))
            mode, p_delete = 'random', .64 if within > phase_width * .7 else .08
        elif family == 'fifo_bursts':
            length = rng.randint(1, 40)
            mode, p_delete = 'oldest', .72 if phase % 3 == 1 else .12
        elif family == 'mixed_survival':
            length = rng.randint(1, 10) if rng.random() < .65 else rng.randint(11, 40)
            mode, p_delete = 'short', .43
        elif family == 'reversed_modes':
            length = rng.randint(1, 9) if phase % 2 == 0 else rng.randint(12, 40)
            mode, p_delete = ('recent' if (phase // 3) % 2 == 0 else 'oldest'), .43
            if rng.random() < .12:
                mode = 'random'
        elif family == 'noisy_cohorts':
            length = max(1, min(40, size_low + (phase % 5) * 6 + rng.choice([-2, 0, 0, 1, 3])))
            mode = 'cohort' if rng.random() < .77 else 'random'
            p_delete = .68 if within > phase_width * .6 else .08
        elif family == 'delayed_echo':
            cycle = phase % 9
            length = rng.randint(1, 8) if cycle < 3 or cycle >= 7 else rng.randint(14, 40)
            mode = 'old' if cycle >= 7 else 'recent'
            p_delete = .44 if cycle >= 3 else .18
        elif family == 'ambiguous_shift':
            length = rng.randint(1, 7) if ratio < .42 else rng.randint(4, 40)
            mode = 'recent' if ratio < .42 else ('oldest' if seed % 2 else 'random')
            p_delete = .4
        elif family == 'anchor_switch':
            short = rng.random() < .6
            length = rng.randint(1, 8) if short else rng.randint(17, 40)
            mode = 'short' if ratio < .5 else 'old'
            p_delete = .4
        elif family == 'heavy_tail_rank':
            length = rng.choice([size_low, size_high]) if phase % 4 == 0 else rng.randint(1, 40)
            mode = rng.choices(['newest', 'oldest', 'random'], [5, 2, 3])[0]
            p_delete = .46 if phase % 5 else .18
        else:
            raise ValueError(family)
        # Keep a substantial final live set; do not make every stream stationary.
        if ratio > .88:
            p_delete *= .35
        if active and len(active) > 2 and rng.random() < p_delete:
            remove(mode, phase)
        else:
            add(length)
    return commands


def write_suite(phase):
    out = ROOT / 'data' / phase
    out.mkdir(parents=True, exist_ok=False)
    if phase == 'final':
        freeze = ROOT / 'freeze.json'
        if not freeze.exists():
            raise ValueError('Freeze all candidates before creating final seeds')
        pinned = json.loads(freeze.read_text())
        for relative, expected in pinned['files'].items():
            if sha(ROOT / relative) != expected:
                raise ValueError('Freeze hash mismatch: ' + relative)
        families, sizes = FINAL_FAMILIES, [2000, 12000, 50000, 200000]
        samples = list(enumerate(sizes))
    else:
        families = TRAIN_FAMILIES
        samples = list(enumerate([2000] * 4 if phase == 'train' else [4000] * 2))
    master_seed = secrets.randbits(64)
    master = random.Random(master_seed)
    rows = []
    for family in families:
        for replicate, n in samples:
            seed = master.getrandbits(64)
            commands = make_stream(family, n, seed)
            path = out / f'{family}_{replicate:02d}.in'
            path.write_text('1\n' + str(n) + '\n' + '\n'.join(map(str, commands)) + '\n')
            rows.append({'name': path.stem, 'path': str(path), 'family': family,
                         'replicate': replicate, 'n': n, 'seed': seed, 'sha256': sha(path)})
    value = {'phase': phase, 'created_at': time.time(), 'master_seed': master_seed,
             'generator_sha256': sha(__file__), 'streams': rows,
             'count': len(rows), 'official_inputs_read': False,
             'scope': 'Procedural pilot; final mechanisms held apart from this training, not a prediction of hidden distribution'}
    (out / 'manifest.json').write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'phase': phase, 'count': len(rows), 'manifest': str(out / 'manifest.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['train', 'dev', 'final'])
    write_suite(parser.parse_args().phase)
