#!/usr/bin/env python3
"""Fresh-seed follow-up for the geometric next-size capacity guard."""

import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "input_v2"
MASTER_SEED = 202610171
GEOM = [(1, 256), (2, 256), (4, 256), (8, 256), (16, 256), (32, 256)]
CASES = [
    ("phase_shift_3x_256", [(s, 256) for s in (1, 2, 4, 8, 16, 3, 6, 12, 24)], "alternate", 0),
    ("phase_shift_3x_384", [(s, 384) for s in (1, 2, 4, 8, 16, 3, 6, 12, 24)], "alternate", 1),
    ("phase_shift_scale5_256", [(s, 256) for s in (1, 2, 4, 8, 16, 5, 10, 20, 40)], "alternate", 0),
    ("geom_count_wobble_v2", [(s, n) for s, n in zip((1, 2, 4, 8, 16, 32), (192, 216, 200, 224, 208, 232))], "alternate", 1),
    ("geom_random_v2", [(s, 192) for s in (1, 2, 4, 8, 16, 32)], "random", None),
    ("geom_count_drift_v2", [(s, n) for s, n in zip((1, 2, 4, 8, 16, 32), (192, 320, 192, 320, 192, 320))], "alternate", 0),
    ("irregular_sizes_v2", [(s, 288) for s in (2, 4, 8, 15, 28, 35)], "alternate", 0),
    ("phase_shift_linear_v2", [(s, 288) for s in (1, 2, 4, 8, 16, 21, 26, 31, 36)], "alternate", 1),
]

def make_case(name, runs, deletion_mode, parity, index):
    rng = random.Random(MASTER_SEED + index)
    commands = []
    next_pid = 1
    for length, count in runs:
        pids = list(range(next_pid, next_pid + count))
        next_pid += count
        commands.extend([length] * count)
        selected = (
            [pid for pid in pids if pid % 2 == parity]
            if deletion_mode == "alternate"
            else rng.sample(pids, count // 2)
        )
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
        "seed": MASTER_SEED + index,
    }

OUT.mkdir(parents=True, exist_ok=True)
suite = {
    "suite": "case9-geometric-capacity-fresh-stress-v2",
    "master_seed": MASTER_SEED,
    "cases": [make_case(*case, i) for i, case in enumerate(CASES)],
}
(HERE / "inputs_v2.json").write_text(json.dumps(suite, indent=2) + "\n")
print(f"generated {len(suite['cases'])} fresh streams in {OUT}")
