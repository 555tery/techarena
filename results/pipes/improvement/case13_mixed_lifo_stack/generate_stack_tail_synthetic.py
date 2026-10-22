from __future__ import annotations

import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)


def generate(seed: int, mode: str, blocks: int = 180) -> None:
    rng = random.Random(seed)
    commands: list[int] = []
    live: list[int] = []
    next_pid = 0

    def place(length: int) -> int:
        nonlocal next_pid
        next_pid += 1
        live.append(next_pid)
        commands.append(length)
        return next_pid

    def delete(pid: int) -> None:
        live.remove(pid)
        commands.append(-pid)

    for _ in range(180):
        place(rng.randint(3, 20))

    for block in range(blocks):
        batch: list[int] = []
        for j in range(20):
            if mode == "alternating_lifo":
                length = (5, 10, 6, 17, 8, 20)[(block * 20 + j) % 6]
            elif mode == "lifo_phase_shift":
                length = rng.randint(9, 20) if block < 90 else rng.randint(1, 30)
            else:
                length = rng.randint(5, 20)
            batch.append(place(length))

        if mode in {"alternating_lifo", "lifo_phase_shift"} and not (
            mode == "lifo_phase_shift" and block >= 90
        ):
            for pid in reversed(batch):
                delete(pid)
        elif mode == "fifo":
            for _ in range(20):
                delete(live[0])
        else:
            for _ in range(20):
                delete(rng.choice(live))

    path = OUT / f"fresh_{seed}_{mode}.in"
    path.write_text(f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n0\n")


for seed, mode in [
    (20261026, "alternating_lifo"),
    (20261027, "lifo_phase_shift"),
    (20261028, "fifo"),
    (20261029, "random"),
]:
    generate(seed, mode)
