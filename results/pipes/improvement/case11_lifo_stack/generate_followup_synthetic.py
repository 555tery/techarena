import random
from pathlib import Path

OUT = Path(__file__).parent / "synthetic"
OUT.mkdir(exist_ok=True)

def emit(name, seed, phases, deletion_mode):
    rng = random.Random(seed)
    commands = []
    active = []
    pid = 0
    n = phases[-1][0]
    for t in range(n):
        place_prob, lo, hi = next(spec for stop, spec in phases if t < stop)
        if not active or rng.random() < place_prob:
            length = rng.randint(lo, hi)
            pid += 1
            active.append(pid)
            commands.append(length)
        else:
            if deletion_mode == "lifo":
                width = max(1, len(active) // 10)
                idx = rng.randrange(max(0, len(active) - width), len(active))
            else:
                idx = rng.randrange(len(active))
            commands.append(-active.pop(idx))
    (OUT / f"{name}.in").write_text(
        f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    )

emit("f01_lifo_growth_beyond_scale", 171001, [(12000, (0.80, 1, 8))], "lifo")
emit("f02_lifo_then_stationary", 171002, [(4000, (0.80, 1, 8)), (12000, (0.50, 1, 8))], "lifo")
emit("f03_lifo_small_to_wide", 171003, [(4000, (0.80, 1, 8)), (12000, (0.50, 9, 32))], "lifo")
emit("f04_random_small_balanced", 171004, [(12000, (0.50, 1, 8))], "random")
