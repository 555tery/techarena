from __future__ import annotations
import hashlib, json, random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "synthetic"
SEEDS = [20261018101, 20261018113, 20261018127, 20261018139, 20261018151, 20261018163]
INITIAL = 700
EVENTS = 40_000

def gen_case(i: int):
    rng = random.Random(SEEDS[i-1])
    live: list[int] = []
    commands: list[int] = []
    next_pid = 1
    for _ in range(INITIAL):
        length = rng.randint(1, 40) if i != 4 else (rng.randint(1, 8) if rng.random() < .8 else rng.randint(25, 40))
        commands.append(length); live.append(next_pid); next_pid += 1
    def place_len(t: int) -> int:
        phase = t // 10_000
        if i == 1: return rng.randint(1, 40)
        if i == 2: return rng.randint(1, 40)
        if i == 3: return rng.randint(1, 8) if phase < 2 else rng.randint(25, 40)
        if i == 4: return rng.randint(1, 8) if rng.random() < .8 else rng.randint(25, 40)
        if i == 5: return 1 + (t % 40)
        bands = ((1, 10), (10, 25), (25, 40), (3, 37))
        lo, hi = bands[phase]
        return rng.randint(lo, hi)
    patterns = {
      1: (1, -1),
      2: (1, 1, 1, -1, -1, -1),
      3: (1, 1, -1, -1),
      4: (1, -1, -1, 1),
      5: (1, 1, -1, -1),
      6: (1, -1, 1, -1, -1, 1),
    }
    descriptions = {
      1: "uniform lengths, random deletions, balanced one-for-one churn",
      2: "uniform lengths, bursts of three installs then three strict-LIFO deletes",
      3: "small-to-wide phase shift, FIFO deletes, balanced pair churn",
      4: "small-heavy bimodal lengths, newest-5%-biased deletes, reverse bursts",
      5: "periodic length cycle, alternating median/newest deletion ranks",
      6: "four length phases, alternating FIFO/LIFO/mid-rank deletions",
    }
    pat = patterns[i]
    for t in range(EVENTS):
        op = pat[t % len(pat)]
        if op > 0:
            commands.append(place_len(t))
            live.append(next_pid); next_pid += 1
        else:
            phase = t // 10_000
            if i == 2: idx = len(live) - 1
            elif i == 3: idx = 0
            elif i == 4:
                if rng.random() < .85:
                    idx = rng.randrange(max(0, len(live)-max(1,len(live)//20)), len(live))
                else: idx = rng.randrange(len(live))
            elif i == 5:
                if (t // 100) % 2 == 0: idx = len(live) // 2 + rng.randint(-min(15,len(live)//3), min(15,len(live)//3))
                else: idx = len(live)-1
                idx = max(0, min(len(live)-1, idx))
            elif i == 6: idx = len(live)-1 if phase % 2 == 0 else 0
            else: idx = rng.randrange(len(live))
            commands.append(-live.pop(idx))
    data = f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
    path = OUT / f"age_case_{i:02d}.in"
    path.write_text(data)
    return {"name": path.stem, "seed": SEEDS[i-1], "commands": len(commands), "initial_live": INITIAL,
            "final_live": len(live), "description": descriptions[i],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

OUT.mkdir(parents=True, exist_ok=True)
rows = [gen_case(i) for i in range(1, 7)]
(OUT / "manifest.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
