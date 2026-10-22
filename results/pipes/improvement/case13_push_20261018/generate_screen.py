#!/usr/bin/env python3
import hashlib, json, random
from pathlib import Path

OUT = Path('results/pipes/improvement/case13_push_20261018/synthetic/eight_fresh')
OUT.mkdir(parents=True, exist_ok=True)
N_ADD, N_DEL = 3000, 2400

styles = [
    ('alternating_lifo', 20261026),
    ('uniform_mixed_lifo', 20261027),
    ('small_large_phase_shift', 20261028),
    ('uniform_random_delete', 20261029),
    ('bursty_5_10_lifo', 20261030),
    ('class_mixture_fifo', 20261031),
    ('random_walk_top20_delete', 20261032),
    ('three_phase_mixed_delete', 20261033),
]

def choose_size(style, placed, rng):
    if style == 'alternating_lifo':
        if placed % 64 in (31, 32): return rng.randint(11, 20)
        return 5 if placed % 2 == 0 else 10
    if style == 'uniform_mixed_lifo':
        return rng.randint(5, 20)
    if style == 'small_large_phase_shift':
        return rng.randint(5, 10) if placed < 1400 else rng.randint(15, 25)
    if style == 'uniform_random_delete':
        return rng.randint(1, 40)
    if style == 'bursty_5_10_lifo':
        return 5 if (placed // 16) % 2 == 0 else 10
    if style == 'class_mixture_fifo':
        return rng.choices([5, 8, 10, 15, 20, 30], weights=[3, 2, 4, 3, 2, 1])[0]
    if style == 'random_walk_top20_delete':
        phase = (placed // 300) % 4
        return rng.randint(3 + phase * 3, 12 + phase * 5)
    phase = placed // 500
    if phase % 3 == 0: return rng.randint(1, 8)
    if phase % 3 == 1: return rng.randint(9, 20)
    return rng.randint(21, 40)

def choose_delete(style, active, rng, placed, removed):
    if style in ('alternating_lifo', 'uniform_mixed_lifo', 'bursty_5_10_lifo'):
        return len(active) - 1 - rng.randrange(min(len(active), 8))
    if style == 'small_large_phase_shift':
        if removed < 1200: return len(active) - 1 - rng.randrange(min(len(active), 5))
        return rng.randrange(len(active))
    if style == 'uniform_random_delete': return rng.randrange(len(active))
    if style == 'class_mixture_fifo': return min(len(active) - 1, rng.randrange(min(32, len(active))))
    if style == 'random_walk_top20_delete': return len(active) - 1 - rng.randrange(min(len(active), max(1, len(active)//5)))
    mode = (removed // 400) % 3
    if mode == 0: return len(active) - 1 - rng.randrange(min(len(active), 6))
    if mode == 1: return rng.randrange(len(active))
    return min(len(active) - 1, rng.randrange(min(40, len(active))))

manifest = {'generator': 'case13_push_20261018/generate_screen.py', 'operation_target': N_ADD + N_DEL,
            'streams': []}
for style, seed in styles:
    rng = random.Random(seed)
    commands = []
    active = []
    pid = 0
    placed = removed = 0
    while placed < N_ADD or removed < N_DEL:
        can_add = placed < N_ADD
        can_del = removed < N_DEL and bool(active)
        if can_add and (not can_del or rng.random() < .555):
            length = choose_size(style, placed, rng)
            commands.append(length)
            pid += 1
            active.append(pid)
            placed += 1
        else:
            idx = choose_delete(style, active, rng, placed, removed)
            commands.append(-active.pop(idx))
            removed += 1
    data = f'4\n{len(commands)}\n' + '\n'.join(map(str, commands)) + '\n'
    path = OUT / f'{style}_{seed}.in'
    path.write_text(data)
    manifest['streams'].append({'name': path.stem, 'seed': seed, 'operations': len(commands),
        'placements': placed, 'deletions': removed, 'final_active': len(active),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'distribution': style})
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
