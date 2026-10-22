from __future__ import annotations

import random
from pathlib import Path


OUT = Path("results/pipes/improvement/case15_size_arenas/synthetic")
SEED = 20261017
INITIAL = 400
PAIRS = 10_000  # 4 commands per pair: 40,400 commands per scenario.


def length_for(scenario: int, command: int, rng: random.Random) -> int:
    phase = command // 4_000
    if scenario == 1:  # abrupt short -> long
        return rng.randint(1, 8) if phase < 3 else rng.randint(24, 40)
    if scenario == 2:  # abrupt long -> short
        return rng.randint(24, 40) if phase < 3 else rng.randint(1, 8)
    if scenario == 3:  # medium -> bimodal
        if phase < 3:
            return rng.randint(11, 20)
        return rng.randint(1, 8) if rng.random() < 0.5 else rng.randint(25, 40)
    if scenario == 4:  # alternating short / long phases
        return rng.randint(1, 8) if phase % 2 == 0 else rng.randint(25, 40)
    if scenario == 5:  # persistent bimodal with a medium phase shift
        if phase in (2, 3, 4):
            return rng.randint(11, 20)
        return rng.randint(1, 8) if rng.random() < 0.6 else rng.randint(25, 40)
    # gradual short-to-long drift, distinct from abrupt steps
    fraction = min(1.0, command / 30_000)
    upper = round(8 + 32 * fraction)
    lower = max(1, round(1 + 23 * fraction))
    return rng.randint(lower, upper)


def deletion_index(scenario: int, active: list[int], step: int,
                   rng: random.Random) -> int:
    if scenario == 1:
        return len(active) - 1  # LIFO
    if scenario == 2:
        return 0  # FIFO
    if scenario == 3:
        return rng.randrange(len(active))  # uniform random
    if scenario == 4:
        return len(active) - 1 if (step // 500) % 2 == 0 else 0
    if scenario == 5:
        # Alternate between oldest and newest, with random choices in between.
        mode = (step // 700) % 3
        return 0 if mode == 0 else len(active) - 1 if mode == 1 else rng.randrange(len(active))
    # Periodic middle-age purge approximated by deleting around the median rank.
    return min(len(active) - 1, max(0, len(active) // 2 + rng.randint(-20, 20)))


def make_one(scenario: int) -> tuple[str, dict[str, object]]:
    rng = random.Random(SEED + scenario)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for _ in range(INITIAL):
        length = length_for(scenario, len(commands), rng)
        commands.append(length)
        active.append(next_pid)
        next_pid += 1

    for pair in range(PAIRS):
        for _ in range(2):
            length = length_for(scenario, len(commands), rng)
            commands.append(length)
            active.append(next_pid)
            next_pid += 1
        for _ in range(2):
            index = deletion_index(scenario, active, pair, rng)
            pid = active.pop(index)
            commands.append(-pid)

    lines = [f"1.0 {len(commands)}", *(str(command) for command in commands)]
    metadata = {
        "scenario": scenario,
        "seed": SEED + scenario,
        "commands": len(commands),
        "initial_live": INITIAL,
        "final_live": len(active),
        "description": [
            "short-to-long abrupt with LIFO deletion",
            "long-to-short abrupt with FIFO deletion",
            "medium-to-bimodal abrupt with random deletion",
            "alternating short/long phases with 500-pair FIFO/LIFO switches",
            "persistent bimodal plus medium phase with alternating FIFO/LIFO/random deletion",
            "gradual length drift with median-rank purge",
        ][scenario - 1],
    }
    return "\n".join(lines) + "\n", metadata


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = []
    for scenario in range(1, 7):
        data, info = make_one(scenario)
        (OUT / f"fresh_{scenario:02d}.in").write_text(data)
        metadata.append(info)
    (OUT / "manifest.json").write_text(__import__("json").dumps(metadata, indent=2) + "\n")
    print(f"generated {len(metadata)} streams in {OUT}")


if __name__ == "__main__":
    main()
