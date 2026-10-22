#!/usr/bin/env python3
"""Independent no-memo exhaustive checker and hand fixtures for exact_oracle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from exact_oracle import solve


FIXTURES = {
    "single_pipe": ([5], 20),
    "two_pipes_fit_one_section": ([6, 7], 20),
    "delete_then_reuse": ([6, 7, -1, 8], 20),
    "simultaneous_volume_exceeds_one_section": ([6, 7, 8], 40),
    "reuse_full_section": ([20, -1, 20], 20),
    "reuse_after_long_pipe": ([12, -1, 28], 40),
}


def naive_min(commands: tuple[int, ...]) -> tuple[int, int]:
    """Enumerate complete placement histories, without memoization or dominance."""
    total = sum(value for value in commands if value > 0)
    bound = ((total + 19) // 20) * 20
    best = bound + 20
    leaves = 0

    def visit(index: int, trench: int, active: dict[int, tuple[int, int]], pid: int) -> None:
        nonlocal best, leaves
        if index == len(commands):
            leaves += 1
            best = min(best, trench)
            return
        command = commands[index]
        if command < 0:
            removed_pid = -command
            assert removed_pid in active
            rest = dict(active)
            del rest[removed_pid]
            visit(index + 1, trench, rest, pid)
            return

        new_pid = pid + 1
        length = command
        # This independent checker iterates the entire bounded integer lattice.
        for start in range(0, bound - length + 1):
            end = start + length
            collides = False
            for other_start, other_length in active.values():
                other_end = other_start + other_length
                if start < other_end and other_start < end:
                    collides = True
                    break
            if collides:
                continue
            furthest_end = max(trench, end)
            next_trench = ((furthest_end + 19) // 20) * 20
            next_active = dict(active)
            next_active[new_pid] = (start, length)
            visit(index + 1, next_trench, next_active, new_pid)

    visit(0, 0, {}, 0)
    if leaves == 0:
        raise AssertionError("naive enumeration found no complete layout")
    return best, leaves


def main() -> int:
    reports = []
    for name, (commands_list, expected) in FIXTURES.items():
        commands = tuple(commands_list)
        dp = solve(commands)
        naive_value, naive_leaves = naive_min(commands)
        if dp["minimum_final_trench_m"] != expected:
            raise AssertionError(f"{name}: DP expected {expected}, got {dp['minimum_final_trench_m']}")
        if naive_value != expected:
            raise AssertionError(f"{name}: naive expected {expected}, got {naive_value}")
        if dp["minimum_final_trench_m"] != naive_value:
            raise AssertionError(f"{name}: DP and naive search disagree")
        reports.append({
            "name": name,
            "commands": list(commands),
            "expected_trench_m": expected,
            "dp_trench_m": dp["minimum_final_trench_m"],
            "naive_trench_m": naive_value,
            "naive_complete_layouts": naive_leaves,
            "dp_transition_count": dp["generated_placement_transitions"],
            "dp_states_per_layer": dp["unique_state_counts_after_each_command"],
        })

    print(json.dumps({"validation": "PASS", "fixtures": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
