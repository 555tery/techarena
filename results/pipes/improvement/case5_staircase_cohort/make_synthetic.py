from __future__ import annotations

import json
import random
from pathlib import Path


OUT = Path("results/pipes/improvement/case5_staircase_cohort/synthetic")
BASE_SEED = 20261029

SCENARIOS = [
    {
        "name": "unit_stride2",
        "sizes": list(range(1, 17)),
        "counts": [128] * 16,
        "deletion": "stride2",
        "description": "unit staircase, stable blocks, alternating within-block PID deletions",
    },
    {
        "name": "unit_random",
        "sizes": list(range(1, 17)),
        "counts": [120] * 16,
        "deletion": "random_half",
        "description": "unit staircase with random half-deletions as a deletion-pattern control",
    },
    {
        "name": "unit_fifo",
        "sizes": list(range(1, 17)),
        "counts": [128] * 16,
        "deletion": "fifo_half",
        "description": "unit staircase with FIFO removal of the oldest live pipes",
    },
    {
        "name": "step2_stride2",
        "sizes": list(range(1, 32, 2)),
        "counts": [128] * 16,
        "deletion": "stride2",
        "description": "step-2 staircase with alternating within-block PID deletions",
    },
]


def generate(spec: dict[str, object], seed: int) -> tuple[str, dict[str, object]]:
    rng = random.Random(seed)
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
        elif spec["deletion"] == "random_half":
            remove_ids = sorted(rng.sample(block_pids, count // 2))
        else:
            remove_ids = active[: count // 2]
        removed = set(remove_ids)
        commands.extend(-pid for pid in remove_ids)
        active = [pid for pid in active if pid not in removed]

    lines = [f"1.0 {len(commands)}", *(str(command) for command in commands)]
    metadata = {
        "name": spec["name"],
        "seed": seed,
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
    for index, spec in enumerate(SCENARIOS):
        seed = BASE_SEED + index
        data, metadata = generate(spec, seed)
        (OUT / f"{spec['name']}.in").write_text(data)
        manifest.append(metadata)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"generated {len(manifest)} case5 staircase stress streams in {OUT}")


if __name__ == "__main__":
    main()
