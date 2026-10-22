#!/usr/bin/env python3
"""Exact DP oracle for the bounded Pipes model in MODEL.md."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DIG_LENGTH = 20
MAX_PLACEMENTS = 3
MAX_TOTAL_LENGTH = 40


@dataclass(frozen=True)
class State:
    trench: int
    # Sorted triples (PID, start, length).
    active: tuple[tuple[int, int, int], ...]
    # Placement witnesses (command_index, PID, start, digs, trench_after).
    path: tuple[tuple[int, int, int, int, int], ...]


def _ceil20(value: int) -> int:
    return ((value + DIG_LENGTH - 1) // DIG_LENGTH) * DIG_LENGTH


def validate_commands(commands: Iterable[int]) -> tuple[int, int]:
    values = tuple(int(x) for x in commands)
    if not values:
        raise ValueError("the bounded class requires at least one command")
    if 0 in values:
        raise ValueError("omit the final protocol terminator 0")

    pid_lengths: dict[int, int] = {}
    active: set[int] = set()
    placements = 0
    total_length = 0
    for command_index, command in enumerate(values, 1):
        if command > 0:
            if command > 40:
                raise ValueError(f"command {command_index}: length outside 1..40")
            placements += 1
            pid = placements
            pid_lengths[pid] = command
            active.add(pid)
            total_length += command
        else:
            pid = -command
            if pid not in active:
                raise ValueError(f"command {command_index}: PID {pid} is not active")
            active.remove(pid)

    if placements > MAX_PLACEMENTS:
        raise ValueError(f"more than {MAX_PLACEMENTS} placements")
    if total_length > MAX_TOTAL_LENGTH:
        raise ValueError(f"sum of placement lengths exceeds {MAX_TOTAL_LENGTH} m")
    return placements, total_length


def solve(commands: Iterable[int]) -> dict[str, object]:
    values = tuple(int(x) for x in commands)
    placements, total_length = validate_commands(values)
    coordinate_bound = _ceil20(total_length)

    # For each active geometry keep only its least trench length. A larger
    # trench with identical live intervals is dominated, as shown in MODEL.md.
    states: dict[tuple[tuple[int, int, int], ...], State] = {
        (): State(trench=0, active=(), path=())
    }
    generated_transitions = 0
    state_counts = [1]
    next_pid = 1

    for command_index, command in enumerate(values, 1):
        next_states: dict[tuple[tuple[int, int, int], ...], State] = {}
        if command < 0:
            pid = -command
            for state in states.values():
                new_active = tuple(pipe for pipe in state.active if pipe[0] != pid)
                if len(new_active) == len(state.active):
                    raise AssertionError(f"validated PID {pid} absent from DP state")
                candidate = State(state.trench, new_active, state.path)
                previous = next_states.get(new_active)
                if previous is None or candidate.trench < previous.trench:
                    next_states[new_active] = candidate
        else:
            length = command
            for state in states.values():
                for start in range(coordinate_bound - length + 1):
                    end = start + length
                    if any(
                        start < other_start + other_length
                        and other_start < end
                        for _, other_start, other_length in state.active
                    ):
                        continue
                    generated_transitions += 1
                    new_trench = _ceil20(max(state.trench, end))
                    digs = (new_trench - state.trench) // DIG_LENGTH
                    new_active = tuple(sorted(
                        state.active + ((next_pid, start, length),)
                    ))
                    path = state.path + (
                        (command_index, next_pid, start, digs, new_trench),
                    )
                    candidate = State(new_trench, new_active, path)
                    previous = next_states.get(new_active)
                    if previous is None or candidate.trench < previous.trench:
                        next_states[new_active] = candidate
                    elif candidate.trench == previous.trench and candidate.path < previous.path:
                        next_states[new_active] = candidate
            next_pid += 1
        states = next_states
        state_counts.append(len(states))
        if not states:
            raise AssertionError(f"no feasible state after command {command_index}")

    best = min(states.values(), key=lambda state: (state.trench, state.path, state.active))
    return {
        "commands": list(values),
        "class": {
            "max_placements": MAX_PLACEMENTS,
            "max_total_placement_length_m": MAX_TOTAL_LENGTH,
            "coordinate_bound_m": coordinate_bound,
        },
        "placements": placements,
        "minimum_final_trench_m": best.trench,
        "witness": [
            {
                "command_index_1based": index,
                "pid": pid,
                "start_m": start,
                "digs_sections": digs,
                "trench_after_m": trench_after,
            }
            for index, pid, start, digs, trench_after in best.path
        ],
        "terminal_active": [
            {"pid": pid, "start_m": start, "length_m": length}
            for pid, start, length in best.active
        ],
        "generated_placement_transitions": generated_transitions,
        "unique_state_counts_after_each_command": state_counts,
    }


def read_commands(path: Path) -> list[int]:
    tokens = [int(token) for token in path.read_text(encoding="ascii").split()]
    return tokens


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: python3 exact_oracle.py COMMANDS_FILE")
    result = solve(read_commands(Path(argv[1])))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
