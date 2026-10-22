from __future__ import annotations

import json
import random
from pathlib import Path


OUT = Path("results/pipes/improvement/case9_hole_first_cohorts/synthetic")
SEED = 20261018


SCENARIOS = [
    {
        "name": "fresh_01",
        "sizes": [1, 2, 4, 8, 16, 32],
        "counts": [700] * 6,
        "deletion": "stride2",
        "description": "six geometric runs, 700 per run, alternating PID-parity deletion",
    },
    {
        "name": "fresh_02",
        "sizes": [1, 2, 4, 8, 16, 3, 6, 12, 24],
        "counts": [600] * 9,
        "deletion": "stride2",
        "description": "geometric runs followed by a 3x-shifted geometric phase, alternating deletion",
    },
    {
        "name": "fresh_03",
        "sizes": [1, 2, 4, 8, 16, 32],
        "counts": [500, 520, 480, 520, 500, 520],
        "deletion": "stride2",
        "description": "geometric sizes with modest block-count drift, alternating deletion",
    },
    {
        "name": "fresh_04",
        "sizes": [1, 2, 4, 8, 16, 32],
        "counts": [700] * 6,
        "deletion": "random",
        "description": "six geometric runs, random half-deletions as a no-periodicity control",
    },
]


def generate(spec: dict[str, object]) -> tuple[str, dict[str, object]]:
    rng = random.Random(SEED + SCENARIOS.index(spec))
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for length, count in zip(spec["sizes"], spec["counts"], strict=True):
        block_pids = list(range(next_pid, next_pid + count))
        commands.extend([length] * count)
        active.extend(block_pids)
        next_pid += count

        if spec["deletion"] == "stride2":
            remove_ids = block_pids[::2]
        else:
            remove_ids = rng.sample(block_pids, count // 2)
            remove_ids.sort()
        removed = set(remove_ids)
        commands.extend(-pid for pid in remove_ids)
        active = [pid for pid in active if pid not in removed]

    lines = [f"1.0 {len(commands)}", *(str(command) for command in commands)]
    metadata = {
        "name": spec["name"],
        "seed": SEED + SCENARIOS.index(spec),
        "commands": len(commands),
        "placements": sum(spec["counts"]),
        "final_live": len(active),
        "sizes": spec["sizes"],
        "counts": spec["counts"],
        "deletion": spec["deletion"],
        "description": spec["description"],
    }
    return "\n".join(lines) + "\n", metadata


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for spec in SCENARIOS:
        data, metadata = generate(spec)
        (OUT / f"{spec['name']}.in").write_text(data)
        manifest.append(metadata)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"generated {len(manifest)} new case9 stress streams in {OUT}")


if __name__ == "__main__":
    main()
