#!/usr/bin/env python3
"""Create independent short command streams for the interior-action probe."""

from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "tiny_inputs"
OUT.mkdir(parents=True, exist_ok=True)


def make(seed: int) -> list[int]:
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    lengths: dict[int, int] = {}

    # The first 16 placements form a mixed, irregular layout.
    for _ in range(16):
        length = rng.choice([2, 3, 4, 5, 6, 7])
        commands.append(length)
        pid = len(lengths) + 1
        lengths[pid] = length
        active.append(pid)

    # Remove separated pipes to create several interior gaps, then place again
    # so the solver has a 32-event causal history before the probe request.
    for pid in list(active)[1::2][:8]:
        commands.append(-pid)
        active.remove(pid)
    for _ in range(8):
        length = rng.choice([2, 3, 4, 5, 6, 7])
        commands.append(length)
        pid = len(lengths) + 1
        lengths[pid] = length
        active.append(pid)
    assert len(commands) == 32

    # The first request is the decision under study. The remaining short
    # continuation intentionally mixes another placement with two removals.
    probe_length = rng.choice([2, 3, 4, 5, 6])
    commands.append(probe_length)
    delete1 = rng.choice(active)
    commands.append(-delete1)
    active.remove(delete1)
    add1 = rng.choice([2, 3, 4, 5, 6, 7])
    commands.append(add1)
    new_pid = len(lengths) + 1
    lengths[new_pid] = add1
    active.append(new_pid)
    delete2 = rng.choice(active)
    commands.append(-delete2)
    active.remove(delete2)
    add2 = rng.choice([2, 3, 4, 5, 6, 7])
    commands.append(add2)
    return commands


manifest = []
for seed in range(81001, 81013):
    commands = make(seed)
    name = f"tiny_{seed}.in"
    (OUT / name).write_text(
        f"1.0\n{len(commands)}\n" + "\n".join(map(str, commands)) + "\n",
        encoding="ascii",
    )
    manifest.append({"seed": seed, "path": f"tiny_inputs/{name}", "commands": len(commands)})

(ROOT / "tiny_inputs_manifest.json").write_text(
    json.dumps({"generator_seed_range": [81001, 81012], "streams": manifest}, indent=2) + "\n",
    encoding="utf-8",
)
