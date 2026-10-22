from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path('results/pipes/improvement/case15_section_phase/tests')
SEED_BASE = 20261017
INITIAL = 500
EVENTS = 30_000


def draw_length(kind: int, t: int, rng: random.Random) -> int:
    if kind == 1:
        return rng.randint(1, 40)
    if kind == 2:
        return rng.randint(8, 12) if rng.random() < .58 else rng.randint(28, 40)
    if kind == 3:
        return rng.randint(15, 40)
    if kind == 4:
        return rng.randint(1, 7) if t < EVENTS // 2 else rng.randint(8, 40)
    raise ValueError(kind)


def delete_index(kind: int, active: list[int], rng: random.Random) -> int:
    if kind == 1 or kind == 4:
        return rng.randrange(len(active))
    if kind == 2:
        return 0
    return len(active) - 1


def generate(kind: int) -> tuple[str, dict[str, object]]:
    seed = SEED_BASE + kind * 37
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for t in range(INITIAL):
        commands.append(draw_length(kind, t, rng))
        active.append(next_pid)
        next_pid += 1
    # Balanced online churn; command type is independent of current solver state.
    pattern = [1, 1, -1, -1]
    j = 0
    while len(commands) < INITIAL + EVENTS:
        op = pattern[j % len(pattern)]
        j += 1
        t = len(commands) - INITIAL
        if op > 0:
            commands.append(draw_length(kind, t, rng))
            active.append(next_pid)
            next_pid += 1
        else:
            i = delete_index(kind, active, rng)
            commands.append(-active.pop(i))
    name = f'fresh_{kind:02d}'
    body = f'1.0 {len(commands)}\n' + '\n'.join(map(str, commands)) + '\n'
    return body, {
        'name': name, 'seed': seed, 'command_count': len(commands),
        'initial_live': INITIAL, 'final_live': len(active),
        'description': [
            'uniform lengths 1-40, random deletions',
            'bimodal lengths 8-12 or 28-40, FIFO deletions',
            'wide lengths 15-40, LIFO deletions',
            'short-to-wide phase shift, random deletions'
        ][kind - 1]
    }


def main() -> None:
    entries = []
    for kind in range(1, 5):
        body, meta = generate(kind)
        path = OUT / f'fresh_{kind:02d}.in'
        path.write_text(body, encoding='ascii')
        meta['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(meta)
    (OUT / 'synthetic_manifest.json').write_text(json.dumps(entries, indent=2) + '\n')
    print(json.dumps(entries, indent=2))

if __name__ == '__main__':
    main()
