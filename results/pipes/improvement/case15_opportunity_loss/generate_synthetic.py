from pathlib import Path
import random

ROOT = Path('results/pipes/improvement/case15_opportunity_loss/synthetic')
ROOT.mkdir(parents=True, exist_ok=True)
SEED = 913733
N = 40000


def draw_length(rng, mode):
    if mode == 'small':
        return rng.randint(1, 7)
    if mode == 'large':
        return rng.randint(8, 40)
    if mode == 'bimodal':
        return 8 if rng.random() < 0.5 else 40
    return rng.randint(1, 40)


def make(name, first, second, delete_mode):
    rng = random.Random(SEED + sum(map(ord, name)))
    commands = []
    active = []
    pid = 0
    for op in range(N):
        phase = first if op < N // 2 else second
        place = not active or rng.random() < 0.56
        if place:
            length = draw_length(rng, phase)
            pid += 1
            active.append(pid)
            commands.append(length)
        else:
            if delete_mode == 'older':
                idx = rng.randrange(max(1, len(active) // 3))
            elif delete_mode == 'newer':
                begin = (2 * len(active)) // 3
                idx = rng.randrange(begin, len(active))
            else:
                idx = rng.randrange(len(active))
            dead = active.pop(idx)
            commands.append(-dead)
    path = ROOT / f'{name}.in'
    path.write_text(f'1 {N}\n' + '\n'.join(map(str, commands)) + '\n', encoding='ascii')
    return path


cases = [
    ('short_to_wide_random', 'small', 'large', 'random'),
    ('short_to_bimodal_old_deletes', 'small', 'bimodal', 'older'),
    ('stationary_wide_recent_deletes', 'wide', 'wide', 'newer'),
    ('wide_to_short_random', 'large', 'small', 'random'),
]
for c in cases:
    print(make(*c))
