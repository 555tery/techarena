#!/usr/bin/env python3
"""Create preregistered, fresh staircase/cohort profiles for case5 screen."""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent

# name, length sequence, per-block counts, deletion ordering, selected parity
profiles = [
    ("unit_even128_forward", list(range(1, 41)), [128], "forward", 0),
    ("unit_odd129_forward", list(range(1, 41)), [129], "forward", 1),
    ("unit_varcount_128_136_124", list(range(1, 41)), [128, 136, 124], "forward", 0),
    ("step2_even128_forward", list(range(1, 41, 2)), [128], "forward", 0),
    ("unit_even128_reverse", list(range(1, 41)), [128], "reverse", 0),
    ("unit_phase_2_40_then_1_39", list(range(2, 41)) + [1], [128], "forward", 0),
]

for name, lengths, counts, order, parity in profiles:
    commands = []
    pid = 0
    for block_index, length in enumerate(lengths):
        count = counts[block_index % len(counts)]
        first = pid + 1
        commands.extend([length] * count)
        pid += count
        chosen = [p for p in range(first, pid + 1) if p % 2 == parity]
        if order == "reverse":
            chosen.reverse()
        commands.extend([-p for p in chosen])
    # Add a short terminal population so every input has positive final load.
    commands.extend([lengths[-1]] * 8)
    operation_count = len(commands)
    path = ROOT / f"{name}.in"
    path.write_text("\n".join([f"1 {operation_count}", *map(str, commands), "0"]) + "\n")
    print(name, operation_count, "commands", path)
