"""Deterministic, predeclared LIFO trace variants for the integrated-policy screen."""
from pathlib import Path
import random

OUT = Path(__file__).parent / "synthetic_fresh_lifo"
OUT.mkdir(parents=True, exist_ok=True)


def build(name, seed, initial_count, steps, size_fn, anchor_period=None, phase=None):
    rng = random.Random(seed)
    commands = []
    active = []
    anchors = []
    pid = 0
    for i in range(initial_count):
        pid += 1
        length = size_fn(rng, -initial_count + i)
        commands.append(length)
        active.append(pid)
        if anchor_period and i < max(1, initial_count // 8):
            anchors.append(pid)
    for t in range(steps):
        mode = phase(t) if phase else "lifo"
        if anchor_period and t > 0 and t % anchor_period == 0 and anchors:
            old = anchors.pop(0)
            if old in active:
                active.remove(old)
                commands.append(-old)
                pid += 1
                commands.append(size_fn(rng, t))
                active.append(pid)
                continue
        if mode == "lifo":
            delete_pid = active.pop()
        elif mode == "fifo":
            delete_pid = active.pop(0)
        else:
            raise ValueError(f"unknown deletion mode: {mode}")
        commands.append(-delete_pid)
        pid += 1
        commands.append(size_fn(rng, t))
        active.append(pid)
    path = OUT / f"{name}.in"
    path.write_text(f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n")
    return {"name": name, "seed": seed, "initial_active": initial_count,
            "replacement_steps": steps, "operation_count": len(commands),
            "final_active": len(active), "path": str(path)}


def uniform_5_8(rng, t):
    return rng.randint(5, 8)


def weighted_short(rng, t):
    return rng.choices([5, 6, 7, 8], weights=[5, 4, 3, 2])[0]


def size_phases(rng, t):
    if t < 1800:
        return rng.choice([5, 6])
    if t < 3600:
        return rng.choice([7, 8])
    return rng.choice([5, 6, 7, 8])


def alternating_5_8(rng, t):
    return [5, 8, 6, 7][t % 4]


CASES = [
    build("l01_pool256_uniform_5_8", 881101, 256, 5000, uniform_5_8),
    build("l02_pool768_weighted_5_8", 881102, 768, 7000, weighted_short),
    build("l03_pool320_sparse_anchor_deletes", 881103, 320, 6000, weighted_short,
          anchor_period=113),
    build("l04_lifo_then_fifo_transition", 881104, 384, 6400, uniform_5_8,
          phase=lambda t: "lifo" if t < 4200 else "fifo"),
    build("l05_lifo_size_phase_shift", 881105, 512, 6000, size_phases),
    build("l06_lifo_alternating_sizes", 881106, 256, 5000, alternating_5_8),
    build("l07_pool4205_scale_guard", 881107, 4205, 2400, uniform_5_8),
]
for case in CASES:
    print(case)
