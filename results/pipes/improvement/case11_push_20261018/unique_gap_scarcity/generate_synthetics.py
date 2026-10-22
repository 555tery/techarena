#!/usr/bin/env python3
"""Fresh, deterministic phase/LIFO pipes streams for the unique-gap screen."""
from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parent / "synthetic"
ROOT.mkdir(parents=True, exist_ok=True)
CONFIGS = [
    ("u01_four_band_saw", 91201, 12000, "four_band_saw", "top10"),
    ("u02_random_regime_shift", 91202, 15000, "random_regime_shift", "top30"),
    ("u03_descending_three_phase", 91203, 16000, "descending_three_phase", "top20"),
    ("u04_bimodal_blocks", 91204, 14000, "bimodal_blocks", "top50"),
    ("u05_size_bursts", 91205, 18000, "size_bursts", "top10"),
    ("u06_alternating_bands", 91206, 14000, "alternating_bands", "top30"),
    ("u07_shifting_zipf", 91207, 16000, "shifting_zipf", "top20"),
    ("u08_mixed_phase", 91208, 20000, "mixed_phase", "top50"),
]

def sample_length(rng, profile, i, count):
    q = i / count
    if profile == "four_band_saw":
        bands = ((1, 6), (18, 40), (7, 16), (1, 40))
        band = min(3, int((i % 3000) / 750))
        return rng.randint(*bands[band])
    if profile == "random_regime_shift":
        if q < 0.28: return rng.randint(1, 12)
        if q < 0.63: return rng.randint(16, 40)
        return rng.randint(1, 40)
    if profile == "descending_three_phase":
        if q < 0.36: return rng.randint(9, 40)
        if q < 0.70: return rng.randint(1, 8)
        return rng.randint(12, 32)
    if profile == "bimodal_blocks":
        block = (i // 640) % 2
        return rng.randint(1, 8) if block == 0 else rng.randint(29, 40)
    if profile == "size_bursts":
        block = (i // 360) % 5
        bands = ((1, 4), (5, 12), (22, 40), (1, 40), (13, 28))
        return rng.randint(*bands[block])
    if profile == "alternating_bands":
        if (i // 450) % 2 == 0: return rng.randint(1, 14)
        return rng.randint(10, 40)
    if profile == "shifting_zipf":
        if q < 0.5:
            return rng.randint(1, 8) if rng.random() < 0.72 else rng.randint(9, 40)
        return rng.randint(25, 40) if rng.random() < 0.62 else rng.randint(1, 24)
    if profile == "mixed_phase":
        if q < 0.22: return rng.randint(1, 5)
        if q < 0.49: return rng.randint(20, 40)
        if q < 0.76: return rng.randint(1, 40)
        return rng.randint(1, 10)
    raise ValueError(profile)

def generate(config):
    name, seed, count, profile, deletion = config
    rng = random.Random(seed)
    active = []
    commands = []
    next_pid = 1
    adds = deletes = 0
    for i in range(count):
        if not active or rng.random() < 0.64:
            commands.append(sample_length(rng, profile, i, count))
            active.append(next_pid)
            next_pid += 1
            adds += 1
            continue
        if deletion == "top10":
            window = max(1, (len(active) + 9) // 10)
        elif deletion == "top20":
            window = max(1, (len(active) + 4) // 5)
        elif deletion == "top30":
            window = max(1, (3 * len(active) + 9) // 10)
        elif deletion == "top50":
            window = max(1, (len(active) + 1) // 2)
        else:
            raise ValueError(deletion)
        index = len(active) - 1 - rng.randrange(window)
        commands.append(-active.pop(index))
        deletes += 1
    path = ROOT / f"{name}.in"
    path.write_text(f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n0\n")
    return {"name": name, "seed": seed, "commands": len(commands), "adds": adds,
            "deletes": deletes, "profile": profile, "deletion": deletion}

if __name__ == "__main__":
    rows = [generate(config) for config in CONFIGS]
    with (ROOT / "suite_manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
