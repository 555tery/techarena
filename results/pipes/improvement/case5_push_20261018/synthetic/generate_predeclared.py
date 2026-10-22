from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TRACES = ROOT / "traces"
TRACES.mkdir(parents=True, exist_ok=True)


SPECS = [
    {
        "name": "strict_parity_1",
        "seed": 20261081,
        "sizes": list(range(3, 20)),
        "counts": [100] * 17,
        "delete": "alternating_parity",
        "truncate_fraction": 1.0,
    },
    {
        "name": "strict_parity_varcounts",
        "seed": 20261082,
        "sizes": list(range(5, 23)),
        "counts": [92, 100, 108, 96, 104, 92, 108, 100, 96, 104, 92, 108, 100, 96, 104, 92, 108, 100],
        "delete": "alternating_parity",
        "truncate_fraction": 1.0,
    },
    {
        "name": "ascending_lifo",
        "seed": 20261083,
        "sizes": list(range(4, 20)),
        "counts": [100] * 16,
        "delete": "lifo_half",
        "truncate_fraction": 1.0,
    },
    {
        "name": "ascending_fifo",
        "seed": 20261084,
        "sizes": list(range(4, 20)),
        "counts": [100] * 16,
        "delete": "fifo_half",
        "truncate_fraction": 1.0,
    },
    {
        "name": "ascending_random",
        "seed": 20261085,
        "sizes": list(range(4, 20)),
        "counts": [100] * 16,
        "delete": "random_half",
        "truncate_fraction": 1.0,
    },
    {
        "name": "two_phase_stride2",
        "seed": 20261086,
        "sizes": list(range(4, 12)) + list(range(15, 23)),
        "counts": [100] * 16,
        "delete": "alternating_parity",
        "truncate_fraction": 1.0,
    },
    {
        "name": "one_repeat_stride2",
        "seed": 20261087,
        "sizes": [4, 5, 6, 7, 7, 8, 9, 10, 11, 12, 13, 14],
        "counts": [100] * 12,
        "delete": "alternating_parity",
        "truncate_fraction": 1.0,
    },
    {
        "name": "phase_shift_random_counts",
        "seed": 20261088,
        "sizes": list(range(3, 9)) + list(range(11, 18)) + list(range(20, 25)),
        "counts": [92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108, 96, 104, 92, 100, 108],
        "delete": "random_half",
        "truncate_fraction": 1.0,
    },
]


def generate(spec: dict) -> list[int]:
    rng = random.Random(spec["seed"])
    commands: list[int] = []
    next_pid = 1
    for block_index, (size, count) in enumerate(
        zip(spec["sizes"], spec["counts"], strict=True)
    ):
        block = list(range(next_pid, next_pid + count))
        commands.extend([size] * count)
        half = count // 2
        if spec["delete"] == "alternating_parity":
            target_parity = block_index & 1
            removed = [pid for pid in block if pid % 2 == target_parity][:half]
            if len(removed) < half:
                removed.extend(pid for pid in block if pid % 2 != target_parity)
                removed = removed[:half]
        elif spec["delete"] == "lifo_half":
            removed = block[-half:]
        elif spec["delete"] == "fifo_half":
            removed = block[:half]
        else:
            removed = sorted(rng.sample(block, half))
        commands.extend(-pid for pid in removed)
        next_pid += count
    keep = int(len(commands) * spec["truncate_fraction"])
    return commands[:keep]


manifest = {
    "prepared_before_any_candidate_run": True,
    "suite": "eight fresh causal staircase and phase-shift traces",
    "seed_range": [SPECS[0]["seed"], SPECS[-1]["seed"]],
    "streams": [],
}
for spec in SPECS:
    commands = generate(spec)
    data = f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    path = TRACES / f"{spec['name']}.in"
    path.write_text(data)
    item = {key: value for key, value in spec.items() if key != "truncate_fraction"}
    item.update(
        {
            "commands": len(commands),
            "placements": sum(command > 0 for command in commands),
            "sha256": hashlib.sha256(data.encode()).hexdigest(),
        }
    )
    manifest["streams"].append(item)
(ROOT / "predeclared_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
