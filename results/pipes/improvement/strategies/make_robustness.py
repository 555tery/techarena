#!/usr/bin/env python3
"""Create a new, fixed synthetic diagnostic set after candidate freeze."""
from collections import deque
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "robustness_inputs"
OUT.mkdir(parents=True, exist_ok=True)
MASTER_SEED = 947_192_61


def sample_uniform(rng, pid):
    return rng.randint(1, 40)


def sample_short(rng, pid):
    return rng.randint(1, 5) if rng.random() < 0.82 else rng.randint(6, 40)


def sample_long(rng, pid):
    return rng.randint(30, 40) if rng.random() < 0.82 else rng.randint(1, 29)


def sample_bimodal(rng, pid):
    return 1 if rng.random() < 0.5 else 40


def sample_cycle(rng, pid):
    return 1 + ((pid * 23 + pid // 11) % 40)


def make_stream(name, operation_count, max_live, sampler, delete_mode, seed):
    rng = random.Random(seed)
    commands = []
    alive = deque() if delete_mode == "fifo" else []
    length_by_pid = [0]
    pid = 0

    while len(commands) < operation_count:
        insert = not alive or (len(alive) < max_live and rng.random() < 0.56)
        if insert:
            pid += 1
            length = sampler(rng, pid)
            length_by_pid.append(length)
            commands.append(length)
            if delete_mode == "fifo":
                alive.append(pid)
            else:
                alive.append(pid)
            continue

        if delete_mode == "fifo":
            dead = alive.popleft()
        elif delete_mode == "lifo":
            dead = alive.pop()
        elif delete_mode == "shortest":
            index = min(range(len(alive)), key=lambda i: length_by_pid[alive[i]])
            dead = alive.pop(index)
        elif delete_mode == "longest":
            index = max(range(len(alive)), key=lambda i: length_by_pid[alive[i]])
            dead = alive.pop(index)
        else:
            index = rng.randrange(len(alive))
            dead = alive[index]
            alive[index] = alive[-1]
            alive.pop()
        commands.append(-dead)

    path = OUT / f"{name}.in"
    path.write_text(f"1\n{len(commands)}\n" + "\n".join(map(str, commands)) + "\n", encoding="ascii")
    return {
        "name": name,
        "seed": seed,
        "operation_count": len(commands),
        "max_live": max_live,
        "length_distribution": sampler.__name__,
        "delete_mode": delete_mode,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


specs = [
    ("uniform_random_50k", 50_000, 900, sample_uniform, "random"),
    ("uniform_fifo_50k", 50_000, 900, sample_uniform, "fifo"),
    ("uniform_lifo_50k", 50_000, 900, sample_uniform, "lifo"),
    ("short_skew_random_50k", 50_000, 900, sample_short, "random"),
    ("long_skew_random_50k", 50_000, 800, sample_long, "random"),
    ("bimodal_random_50k", 50_000, 850, sample_bimodal, "random"),
    ("cyclic_fifo_50k", 50_000, 900, sample_cycle, "fifo"),
    ("cyclic_lifo_50k", 50_000, 900, sample_cycle, "lifo"),
    ("uniform_delete_shortest_30k", 30_000, 450, sample_uniform, "shortest"),
    ("uniform_delete_longest_30k", 30_000, 450, sample_uniform, "longest"),
]

manifest = {
    "master_seed": MASTER_SEED,
    "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "purpose": "post-freeze diagnostic only; no policy tuning based on these results",
    "streams": [make_stream(*spec, MASTER_SEED + i) for i, spec in enumerate(specs)],
}
(HERE / "robustness_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
for stream in manifest["streams"]:
    print(stream["name"], stream["operation_count"], stream["seed"], stream["sha256"])
