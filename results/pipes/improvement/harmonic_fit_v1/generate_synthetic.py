#!/usr/bin/env python3
"""Generate fresh mixed-size/deletion streams for harmonic-fit v1."""

from collections import deque
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
N = 30_000
SEED = 20261018


def size_for(kind, step, placement_no, rng):
    phase = step / N
    if kind == "stationary_uniform_random":
        return rng.randint(1, 40)
    if kind == "short_to_wide_lifo":
        return rng.randint(1, 8) if phase < 0.5 else rng.randint(21, 40)
    if kind == "wide_to_short_fifo":
        return rng.randint(21, 40) if phase < 0.5 else rng.randint(1, 10)
    if kind == "harmonic_boundary_mixed":
        values = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 20, 21, 39, 40)
        return rng.choice(values)
    if kind == "periodic_class_cohort":
        pattern = (1, 7, 8, 13, 14, 20, 21, 28, 29, 39, 40, 20)
        return pattern[placement_no % len(pattern)]
    if kind == "three_phase_old_bias":
        if phase < 1 / 3:
            return rng.randint(1, 10)
        if phase < 2 / 3:
            return rng.randint(14, 27)
        return rng.randint(28, 40)
    raise ValueError(kind)


def pick_delete(kind, rng, active_ids, active, fifo, lifo):
    if kind == "wide_to_short_fifo":
        while fifo and fifo[0] not in active:
            fifo.popleft()
        return fifo.popleft()
    if kind == "short_to_wide_lifo":
        while lifo and lifo[-1] not in active:
            lifo.pop()
        return lifo.pop()
    if kind == "periodic_class_cohort":
        anchor_length = active[rng.choice(active_ids)]
        sample = rng.sample(active_ids, min(24, len(active_ids)))
        same = [pid for pid in sample if active[pid] == anchor_length]
        return min(same) if same else rng.choice(active_ids)
    if kind == "three_phase_old_bias":
        return min(rng.sample(active_ids, min(13, len(active_ids))))
    if kind == "harmonic_boundary_mixed":
        sample = rng.sample(active_ids, min(7, len(active_ids)))
        return max(sample) if rng.random() < 0.6 else rng.choice(active_ids)
    return rng.choice(active_ids)


def generate(kind, ordinal):
    rng = random.Random(SEED + ordinal * 104729)
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
            length = size_for(kind, step, placements, rng)
            pid = placements + 1
            placements += 1
            commands.append(length)
            active[pid] = length
            positions[pid] = len(active_ids)
            active_ids.append(pid)
            fifo.append(pid)
            lifo.append(pid)
        else:
            pid = pick_delete(kind, rng, active_ids, active, fifo, lifo)
            commands.append(-pid)
            del active[pid]
            index = positions.pop(pid)
            last = active_ids.pop()
            if index < len(active_ids):
                active_ids[index] = last
                positions[last] = index

    name = f"{ordinal:02d}_{kind}.in"
    path = OUT / name
    path.write_text(
        "1.0\n" + str(N) + "\n" + "\n".join(map(str, commands)) + "\n",
        encoding="ascii",
    )
    return {
        "name": name,
        "scenario": kind,
        "seed": SEED + ordinal * 104729,
        "operations": N,
        "placements": placements,
        "active_at_end": len(active),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    kinds = (
        "stationary_uniform_random",
        "short_to_wide_lifo",
        "wide_to_short_fifo",
        "harmonic_boundary_mixed",
        "periodic_class_cohort",
        "three_phase_old_bias",
    )
    cases = [generate(kind, ordinal) for ordinal, kind in enumerate(kinds, 1)]
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
