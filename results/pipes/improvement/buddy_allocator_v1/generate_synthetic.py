#!/usr/bin/env python3
"""Create six fresh, deterministic Pipes stress streams for buddy-v1."""

from collections import deque
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
N = 30_000
SEED = 20261017


def pipe_length(kind, step, placements, rng):
    phase = step / N
    if kind == "stationary_uniform_random":
        return rng.randint(1, 40)
    if kind == "short_to_wide_random":
        return rng.randint(1, 7) if phase < 0.5 else rng.randint(8, 40)
    if kind == "wide_to_short_fifo":
        return rng.randint(25, 40) if phase < 0.5 else rng.randint(1, 8)
    if kind == "bimodal_lifo":
        return rng.choice((2, 3, 4, 34, 37, 40))
    if kind == "periodic_cohort_delete":
        pattern = (1, 2, 3, 5, 8, 13, 21, 34, 13, 5, 2, 1)
        return pattern[placements % len(pattern)]
    if kind == "three_phase_old_bias":
        if phase < 1 / 3:
            return rng.randint(2, 10)
        if phase < 2 / 3:
            return rng.randint(16, 28)
        return rng.randint(30, 40)
    raise ValueError(kind)


def choose_delete(kind, rng, active_ids, active, fifo, lifo):
    if kind == "wide_to_short_fifo":
        while fifo and fifo[0] not in active:
            fifo.popleft()
        return fifo.popleft()
    if kind == "bimodal_lifo":
        while lifo and lifo[-1] not in active:
            lifo.pop()
        return lifo.pop()
    if kind == "periodic_cohort_delete":
        anchor = active[rng.choice(active_ids)]
        same = [pid for pid in active_ids if active[pid] == anchor]
        return min(same) if same else rng.choice(active_ids)
    if kind == "three_phase_old_bias":
        sample = rng.sample(active_ids, min(9, len(active_ids)))
        return min(sample)
    return rng.choice(active_ids)


def generate(kind, index):
    rng = random.Random(SEED + index * 104729)
    commands = []
    active = {}
    active_ids = []
    positions = {}
    fifo = deque()
    lifo = []
    placements = 0
    for step in range(N):
        if len(active) < 2500:
            should_place = True
        elif len(active) > 2500:
            should_place = False
        else:
            should_place = rng.random() < 0.5
        if should_place:
            length = pipe_length(kind, step, placements, rng)
            pid = placements + 1
            placements += 1
            commands.append(length)
            active[pid] = length
            positions[pid] = len(active_ids)
            active_ids.append(pid)
            fifo.append(pid)
            lifo.append(pid)
            continue

        pid = choose_delete(kind, rng, active_ids, active, fifo, lifo)
        commands.append(-pid)
        del active[pid]
        index_in_list = positions.pop(pid)
        last = active_ids.pop()
        if index_in_list < len(active_ids):
            active_ids[index_in_list] = last
            positions[last] = index_in_list

    name = f"{index:02d}_{kind}.in"
    path = OUT / name
    path.write_text("1.0\n" + str(N) + "\n" + "\n".join(map(str, commands)) + "\n", encoding="ascii")
    return {
        "name": name,
        "scenario": kind,
        "seed": SEED + index * 104729,
        "operations": N,
        "placements": placements,
        "active_at_end": len(active),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    kinds = (
        "stationary_uniform_random",
        "short_to_wide_random",
        "wide_to_short_fifo",
        "bimodal_lifo",
        "periodic_cohort_delete",
        "three_phase_old_bias",
    )
    cases = [generate(kind, i + 1) for i, kind in enumerate(kinds)]
    manifest = {
        "seed_base": SEED,
        "operations_per_case": N,
        "generator": "generate_synthetic.py",
        "cases": cases,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
