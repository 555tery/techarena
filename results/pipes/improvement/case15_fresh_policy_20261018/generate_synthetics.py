from __future__ import annotations

import json
import random
from pathlib import Path


OUT = Path(__file__).resolve().parent / "synthetic"
SEED_BASE = 2026101800
INITIAL = 700
EVENTS = 40_000


def draw_length(scenario: int, event: int, rng: random.Random) -> int:
    phase = event // 10_000
    if scenario in (1, 2, 7):
        return rng.randint(1, 40)
    if scenario == 3:
        return rng.randint(1, 8) if phase < 2 else rng.randint(25, 40)
    if scenario == 4:
        return rng.randint(1, 6) if rng.random() < 0.65 else rng.randint(28, 40)
    if scenario == 5:
        return 1 + (event % 40)
    if scenario == 6:
        bands = ((1, 10), (10, 25), (25, 40), (3, 37))
        lo, hi = bands[phase]
        return rng.randint(lo, hi)
    return rng.randint(30, 40) if rng.random() < 0.4 else rng.randint(1, 20)


def deletion_index(scenario: int, phase: int, active: list[int], rng: random.Random) -> int:
    if scenario == 2:
        return len(active) - 1
    if scenario == 3:
        return len(active) - 1
    if scenario == 4:
        return 0
    if scenario == 5:
        return min(len(active) - 1, max(0, len(active) // 2 + rng.randint(-25, 25)))
    if scenario == 6:
        return len(active) - 1 if phase % 2 == 0 else 0
    if scenario == 7:
        if rng.random() < 0.8:
            return rng.randrange(max(1, len(active) - max(1, len(active) // 20)), len(active))
    return rng.randrange(len(active))


def event_kind(scenario: int, position: int) -> int:
    if scenario in (1, 2, 3, 4):
        pattern = (1, 1, -1, -1)
    elif scenario == 5:
        pattern = (1, 1, -1)
    elif scenario == 6:
        pattern = (1, -1)
    elif scenario == 7:
        pattern = (1, 1, 1, -1, -1)
    else:
        pattern = (1, 1, -1, 1, -1)
    return pattern[position % len(pattern)]


def generate(scenario: int) -> tuple[str, dict[str, object]]:
    seed = SEED_BASE + scenario
    rng = random.Random(seed)
    active: list[int] = []
    commands: list[int] = []
    next_pid = 1
    for event in range(INITIAL):
        commands.append(draw_length(scenario, event, rng))
        active.append(next_pid)
        next_pid += 1
    while len(commands) < INITIAL + EVENTS:
        offset = len(commands) - INITIAL
        if event_kind(scenario, offset) > 0:
            commands.append(draw_length(scenario, offset, rng))
            active.append(next_pid)
            next_pid += 1
        else:
            phase = offset // 10_000
            index = deletion_index(scenario, phase, active, rng)
            commands.append(-active.pop(index))
    descriptions = [
        "uniform lengths, random deletion",
        "uniform lengths, strict LIFO deletion",
        "short-to-wide phases, LIFO deletion",
        "small/large bimodal lengths, FIFO deletion",
        "periodic lengths, median-rank deletion",
        "four demand phases, alternating LIFO/FIFO deletion",
        "uniform lengths, 80% newest-5%-biased deletion",
        "long-biased mixture, moderate mixed churn",
    ]
    text = f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    return text, {
        "name": f"fresh_{scenario:02d}",
        "seed": seed,
        "commands": len(commands),
        "initial_live": INITIAL,
        "final_live": len(active),
        "description": descriptions[scenario - 1],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for scenario in range(1, 9):
        content, metadata = generate(scenario)
        (OUT / f"fresh_{scenario:02d}.in").write_text(content)
        rows.append(metadata)
    (OUT / "manifest.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"generated {len(rows)} fixed-seed streams in {OUT}")


if __name__ == "__main__":
    main()
