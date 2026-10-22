#!/usr/bin/env python3
"""Create fresh small streams for the LIFO single-unit-lane mechanism."""
from __future__ import annotations

import random
from pathlib import Path

OUT = Path(__file__).parent

def write(name: str, commands: list[int]) -> None:
    (OUT / f"{name}.in").write_text(
        f"1 {len(commands)}\n" + "\n".join(map(str, commands + [0])) + "\n"
    )

def common_prefix() -> tuple[list[int], int]:
    commands: list[int] = []
    pid = 0
    for _ in range(64):
        pid += 1
        commands.extend((1, -pid))
    run_start = pid + 1
    commands.extend([1] * 4000)
    pid += 4000
    return commands, run_start

# Causal witness: observed LIFO deletions, a long same-size run, then a partial
# newest cohort release that can expose either one 10 m gap or two smaller gaps.
commands, first_run_pid = common_prefix()
commands.extend(-pid for pid in range(4000 + 64, 4000 + 64 - 10, -1))
commands.append(10)
write("lifo_release_10_then_pipe10", commands)

# Regime-shift stress: after an observed LIFO prefix, remove the oldest members
# of the unit run and then request a medium pipe.
commands, first_run_pid = common_prefix()
commands.extend(-pid for pid in range(first_run_pid, first_run_pid + 10))
commands.append(10)
write("lifo_to_fifo_shift", commands)

# Same shift with a seeded random deletion subset; no generator metadata reaches
# the solver, and the fixed seed is recorded only for reproducibility.
commands, first_run_pid = common_prefix()
rng = random.Random(2026101702)
selected = sorted(rng.sample(range(first_run_pid, first_run_pid + 4000), 10))
commands.extend(-pid for pid in selected)
commands.append(10)
write("lifo_to_random_shift_seed2026101702", commands)

# Control: no LIFO prefix; random removals should not enable the new gate.
commands = [1] * 4000
rng = random.Random(2026101703)
selected = sorted(rng.sample(range(1, 4001), 10))
commands.extend(-pid for pid in selected)
commands.append(10)
write("random_control_seed2026101703", commands)

print("wrote 4 streams; each uses only ordinary placement/removal commands")
