#!/usr/bin/env python3
"""Generate a fresh unit-dominant, strict-LIFO screen for scale-gate suppression."""
import hashlib
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "unit_profile_v2"


def is_unit(rng, index, rate, mode):
    if mode == "iid":
        return rng.random() < rate
    if mode == "periodic":
        return (index % 1000) < int(rate * 1000)
    if mode == "phase":
        phase_rate = rate if (index // 4000) % 2 == 0 else max(0.65, rate - 0.13)
        return rng.random() < phase_rate
    if mode == "bursts":
        return (index // 750) % 2 == 0 or rng.random() < rate
    raise ValueError(mode)


def generate(seed, operations, rate, mode):
    rng = random.Random(seed)
    commands = []
    live = []
    next_pid = 1
    for i in range(operations):
        should_delete = bool(live) and i != operations - 1 and rng.random() < 0.027
        if should_delete:
            if rng.random() < 0.98:
                idx = len(live) - 1
            else:
                idx = rng.randrange(len(live))
            commands.append(-live.pop(idx))
            continue
        if is_unit(rng, i, rate, mode):
            length = 1
        else:
            length = rng.randint(2, 8) if rng.random() < 0.8 else rng.randint(9, 40)
        commands.append(length)
        live.append(next_pid)
        next_pid += 1
    assert live
    return commands


def main():
    specs = [
        (2026101821, 10000, 0.95, "iid"),
        (2026101822, 12000, 0.93, "iid"),
        (2026101823, 15000, 0.91, "iid"),
        (2026101824, 18000, 0.90, "iid"),
        (2026101825, 22000, 0.88, "iid"),
        (2026101826, 25000, 0.85, "iid"),
        (2026101827, 12000, 0.92, "periodic"),
        (2026101828, 20000, 0.94, "phase"),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed, operations, rate, mode in specs:
        name = f"unit_scale_{seed}"
        path = OUT / f"{name}.in"
        commands = generate(seed, operations, rate, mode)
        path.write_text("\n".join(["4 " + str(len(commands)), *map(str, commands), "0"]) + "\n",
                        encoding="ascii")
        rows.append({
            "name": name,
            "seed": seed,
            "operations": operations,
            "target_unit_probability": rate,
            "length_mode": mode,
            "deletion": "2.7% churn; 98% strict newest active PID, 2% uniform",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    manifest = {"created_before_paired_runs": True, "streams": rows, "count": len(rows)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"count": len(rows), "manifest": str(OUT / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
