import random
from pathlib import Path

OUT = Path(__file__).parent / "synthetic"
OUT.mkdir(exist_ok=True)

def stream(name, seed, n, phases, delete_mode):
    rng = random.Random(seed)
    active = []
    commands = []
    pid = 0
    for t in range(n):
        phase = next((spec for stop, spec in phases if t < stop), phases[-1][1])
        place_prob, lo, hi = phase
        if not active or rng.random() < place_prob:
            length = rng.randint(lo, hi)
            pid += 1
            active.append((pid, length))
            commands.append(length)
        else:
            if delete_mode == "lifo":
                window = max(1, len(active) // 10)
                idx = rng.randrange(max(0, len(active) - window), len(active))
            elif delete_mode == "fifo":
                window = max(1, len(active) // 10)
                idx = rng.randrange(min(window, len(active)))
            else:
                idx = rng.randrange(len(active))
            old_pid, _ = active.pop(idx)
            commands.append(-old_pid)
    data = f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    (OUT / f"{name}.in").write_text(data)

stream("s01_small_lifo", 501101, 8000, [(8000,(0.80,1,8))], "lifo")
stream("s02_small_fifo", 501102, 8000, [(8000,(0.80,1,8))], "fifo")
stream("s03_small_random", 501103, 8000, [(8000,(0.80,1,8))], "random")
stream("s04_small_to_wide_lifo", 501104, 10000, [(5000,(0.80,1,8)),(10000,(0.50,9,32))], "lifo")
