#!/usr/bin/env python3
"""Create a small, preregistered stress suite for the causal cohort gate."""

import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "input"
MASTER_SEED = 80520261017
GEOM = [(1, 256), (2, 256), (4, 256), (8, 256), (16, 256), (32, 256)]
CASES = [
    ("geom_alt_even_256", GEOM, "alternate", 0),
    ("geom_alt_odd_320", [(s, 320) for s in (1, 2, 4, 8, 16, 32)], "alternate", 1),
    ("geom_count_wobble", [(s, n) for s, n in zip((1, 2, 4, 8, 16, 32), (256, 288, 272, 280, 268, 276))], "alternate", 0),
    ("geom_random_deletes", GEOM, "random", None),
    ("phase_shift_geom_3x", [(s, 256) for s in (1, 2, 4, 8, 16, 3, 6, 12, 24)], "alternate", 1),
    ("phase_shift_to_linear", [(s, 256) for s in (1, 2, 4, 8, 16, 21, 26, 31, 36)], "alternate", 0),
    ("geometric_count_drift", [(s, n) for s, n in zip((1, 2, 4, 8, 16, 32), (256, 384, 256, 384, 256, 384))], "alternate", 0),
    ("irregular_increasing_sizes", [(s, 256) for s in (2, 4, 8, 15, 28, 35)], "alternate", 1),
]

def make_case(name, runs, deletion_mode, parity, case_index):
    rng = random.Random(MASTER_SEED + case_index)
    commands = []
    next_pid = 1
    for length, count in runs:
        pids = list(range(next_pid, next_pid + count))
        next_pid += count
        commands.extend([length] * count)
        if deletion_mode == "alternate":
            selected = [pid for pid in pids if pid % 2 == parity]
        else:
            selected = rng.sample(pids, count // 2)
        commands.extend(-pid for pid in selected)

    target = OUT / f"{name}.in"
    target.write_text(f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n0\n")
    return {
        "name": name,
        "input": str(target.relative_to(HERE)),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "operations": len(commands),
        "placement_runs": runs,
        "deletion_mode": deletion_mode,
        "target_pid_parity": parity,
        "seed": MASTER_SEED + case_index,
    }

OUT.mkdir(parents=True, exist_ok=True)
manifest = {
    "suite": "case9-causal-cohort-gate-stress-v1",
    "master_seed": MASTER_SEED,
    "cases": [make_case(*case, index) for index, case in enumerate(CASES)],
}
(HERE / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"generated {len(manifest['cases'])} streams in {OUT}")
