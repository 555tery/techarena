from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


OUT = Path(__file__).resolve().parent / "synthetic"
SEED_BASE = 202610184100
INITIAL = 5000
EVENTS = 100_000


def draw_length(case: int, event: int, placement_index: int,
                rng: random.Random) -> int:
    phase = min(2, event // 33_334)
    if case == 1:
        bands = ((1, 4), (3, 8), (1, 8))
        lo, hi = bands[phase]
        return rng.randint(lo, hi)
    if case == 2:
        bands = ((1, 3), (4, 8), (2, 7))
        lo, hi = bands[phase]
        return rng.randint(lo, hi)
    if case == 3:
        # A small 6% wide-size pulse leaves the recent short-length share
        # above the candidate's 90% gate while varying the demand phase.
        if phase == 1 and placement_index % 16 == 0:
            return rng.randint(9, 16)
        return rng.randint(1, 8)
    bands = ((1, 8), (2, 8), (1, 6))
    lo, hi = bands[phase]
    return rng.randint(lo, hi)


def event_kind(event: int) -> int:
    if event < 20_000:
        pattern = (1, 1, 1, -1)
        return pattern[event % len(pattern)]
    if event < 70_000:
        pattern = (1, -1)
        return pattern[event % len(pattern)]
    pattern = (1, 1, 1, -1, -1)
    return pattern[(event - 70_000) % len(pattern)]


def deletion_index(case: int, event: int, delete_ordinal: int,
                   active: list[int], rng: random.Random) -> int:
    n = len(active)
    newest_five = max(1, n // 20)
    if case == 1:
        return rng.randrange(n - newest_five, n)
    if case == 2:
        return rng.randrange(n - newest_five, n) if delete_ordinal % 20 < 17 else 0
    if case == 3:
        return rng.randrange(n - newest_five, n) if delete_ordinal % 10 < 9 else rng.randrange(n)
    if event < 40_000:
        return rng.randrange(n)
    if event < 60_000:
        return rng.randrange(n - newest_five, n) if rng.random() < 0.5 else 0
    return rng.randrange(n - newest_five, n) if rng.random() < 0.95 else rng.randrange(n)


def generate(case: int) -> tuple[str, dict[str, object]]:
    seed = SEED_BASE + case
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for event in range(INITIAL):
        commands.append(draw_length(case, event, event, rng))
        active.append(next_pid)
        next_pid += 1
    min_active = len(active)
    max_active = len(active)
    delete_count = 0
    for event in range(EVENTS):
        if event_kind(event) > 0:
            commands.append(draw_length(case, event, len(commands), rng))
            active.append(next_pid)
            next_pid += 1
        else:
            index = deletion_index(case, event, delete_count, active, rng)
            commands.append(-active.pop(index))
            delete_count += 1
        min_active = min(min_active, len(active))
        max_active = max(max_active, len(active))
    assert len(commands) == INITIAL + EVENTS
    assert min_active > 4096, (case, min_active)
    descriptions = (
        "phased short lengths; newest-5% deletion every time",
        "low/mid short-size phase shift; 85% newest-5%, otherwise FIFO",
        "short demand with a 6% wide pulse; 90% newest-5%, otherwise random",
        "short-size phases; random then mixed then 95% newest-5% deletion",
    )
    text = f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    raw = text.encode("ascii")
    return text, {
        "name": f"gate_stress_{case:02d}",
        "seed": seed,
        "command_count": len(commands),
        "initial_active": INITIAL,
        "minimum_active_count": min_active,
        "maximum_active_count": max_active,
        "placement_count": len(commands) - delete_count,
        "deletion_count": delete_count,
        "description": descriptions[case - 1],
        "input_sha256": hashlib.sha256(raw).hexdigest(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for case in range(1, 5):
        content, metadata = generate(case)
        (OUT / f"gate_stress_{case:02d}.in").write_text(content)
        records.append(metadata)
    (OUT / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"generated {len(records)} streams; active count > 4096 throughout")


if __name__ == "__main__":
    main()
