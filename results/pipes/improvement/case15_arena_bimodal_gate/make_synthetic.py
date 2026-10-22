from __future__ import annotations

import json
import random
from pathlib import Path


OUT = Path("results/pipes/improvement/case15_arena_bimodal_gate/synthetic")
SEED_BASE = 20261500
INITIAL = 400
EVENTS = 40_000


def draw_length(scenario: int, event_number: int, rng: random.Random) -> int:
    phase = event_number // 5_000
    if scenario == 1:  # separated bimodal, balanced
        return rng.randint(1, 8) if rng.random() < 0.5 else rng.randint(30, 40)
    if scenario == 2:  # separated bimodal, small mode is a minority
        return rng.randint(2, 6) if rng.random() < 0.35 else rng.randint(25, 32)
    if scenario in (3, 4):  # broad uniform support overlapping all arena classes
        return rng.randint(8, 40)
    if scenario == 5:  # uniform -> bimodal -> uniform, with a phase-aware deletion policy
        if phase < 3 or phase >= 6:
            return rng.randint(8, 40)
        return rng.randint(1, 7) if rng.random() < 0.5 else rng.randint(29, 40)
    # Bimodal -> uniform -> bimodal with a reversed modal balance.
    if phase < 3 or phase >= 6:
        return rng.randint(1, 8) if rng.random() < 0.65 else rng.randint(31, 40)
    return rng.randint(8, 40)


def choose_delete_index(scenario: int, phase: int, active: list[int],
                        event_number: int, rng: random.Random) -> int:
    if scenario == 1:
        return rng.randrange(len(active))
    if scenario == 2:
        return 0  # FIFO
    if scenario == 3:
        return len(active) - 1  # LIFO
    if scenario == 4:
        return rng.randrange(len(active))  # low-churn uniform control
    if scenario == 5:
        return 0 if phase % 2 == 0 else len(active) - 1
    # Purge near median rank, alternating with random deletion by phase.
    if phase % 2 == 0:
        return min(len(active) - 1, max(0, len(active) // 2 + rng.randint(-30, 30)))
    return rng.randrange(len(active))


def event_pattern(scenario: int) -> list[int]:
    if scenario == 4:  # only 20% removals: gate should stay off
        return [1, 1, 1, 1, -1]
    if scenario == 5:
        return [1, -1, 1, 1, -1, 1]  # one-third removals
    return [1, 1, -1, -1]  # half removals


def generate(scenario: int) -> tuple[str, dict[str, object]]:
    seed = SEED_BASE + scenario
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for _ in range(INITIAL):
        commands.append(draw_length(scenario, len(commands), rng))
        active.append(next_pid)
        next_pid += 1

    pattern = event_pattern(scenario)
    pattern_position = 0
    while len(commands) < INITIAL + EVENTS:
        event_number = len(commands) - INITIAL
        kind = pattern[pattern_position % len(pattern)]
        pattern_position += 1
        if kind > 0:
            commands.append(draw_length(scenario, event_number, rng))
            active.append(next_pid)
            next_pid += 1
        else:
            phase = len(commands) // 5_000
            index = choose_delete_index(scenario, phase, active, event_number, rng)
            commands.append(-active.pop(index))

    descriptions = [
        "balanced separated bimodal demand, random deletions",
        "35/65 separated bimodal demand, FIFO deletions",
        "uniform 8-40 demand, LIFO deletions",
        "uniform 8-40 demand, 20% deletion churn control",
        "uniform -> bimodal -> uniform phases, FIFO/LIFO deletions",
        "bimodal -> uniform -> shifted bimodal phases, median/random deletions",
    ]
    lines = [f"1.0 {len(commands)}", *(str(command) for command in commands)]
    return "\n".join(lines) + "\n", {
        "name": f"fresh_{scenario:02d}",
        "seed": seed,
        "commands": len(commands),
        "initial_live": INITIAL,
        "final_live": len(active),
        "description": descriptions[scenario - 1],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for scenario in range(1, 7):
        data, metadata = generate(scenario)
        (OUT / f"fresh_{scenario:02d}.in").write_text(data)
        manifest.append(metadata)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"generated {len(manifest)} new streams in {OUT}")


if __name__ == "__main__":
    main()
