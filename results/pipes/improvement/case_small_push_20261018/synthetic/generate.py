#!/usr/bin/env python3
"""Create 16 predeclared mixed-size-LIFO and unit-dominant fresh traces."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def length12(rng, mode, i):
    if mode == "uniform5_39":
        return rng.randint(5, 39)
    if mode == "bimodal5_39":
        return rng.randint(5, 14) if rng.random() < 0.7 else rng.randint(20, 39)
    if mode == "short_skew5_39":
        return rng.randint(5, 12) if rng.random() < 0.65 else rng.randint(13, 39)
    if mode == "phase_mix5_39":
        phase = (i // 500) % 3
        if phase == 0:
            return rng.randint(5, 12)
        if phase == 1:
            return rng.randint(25, 39)
        return rng.randint(5, 39)
    if mode == "cyclic5_39":
        return 5 + ((i * 11 + rng.randrange(5)) % 35)
    if mode == "two_band5_39":
        return rng.randint(10, 20) if rng.random() < 0.5 else rng.randint(28, 39)
    if mode == "alternating_band5_39":
        return rng.randint(5, 14) if (i // 64) % 2 == 0 else rng.randint(24, 39)
    if mode == "uniform_with_blocks5_39":
        base = 5 + ((i // 120) * 7) % 35
        return max(5, min(39, base + rng.randint(-4, 4)))
    raise ValueError(mode)


def length14(rng, unit_rate, i, mode):
    if mode == "unit_iid":
        unit = rng.random() < unit_rate
    elif mode == "unit_bursts":
        unit = (i // 500) % 2 == 0 or rng.random() < unit_rate
    elif mode == "unit_phase_shift":
        phase_rate = unit_rate if (i // 2500) % 2 == 0 else max(0.75, unit_rate - 0.12)
        unit = rng.random() < phase_rate
    elif mode == "unit_periodic":
        unit = (i % 100) < int(unit_rate * 100)
    else:
        raise ValueError(mode)
    return 1 if unit else rng.randint(2, 40)


def generate(seed, count, regime, mode, parameter):
    rng = random.Random(seed)
    commands = []
    live = []
    next_pid = 1
    for i in range(count):
        # Keep a live pipe at EOF; target removal ratios are about 24% (case 12)
        # and 2.7% (case 14).
        if i == count - 1 or not live:
            do_delete = False
        else:
            churn = 0.24 if regime == "case12_mixed_lifo" else 0.027
            do_delete = rng.random() < churn
        if do_delete:
            if regime == "case12_mixed_lifo":
                if rng.random() < 0.87:
                    top = max(1, (len(live) + 4) // 5)
                    idx = rng.randrange(len(live) - top, len(live))
                else:
                    idx = rng.randrange(len(live))
            else:
                if rng.random() < 0.98:
                    top = max(1, (len(live) + 4) // 5)
                    idx = rng.randrange(len(live) - top, len(live))
                else:
                    idx = rng.randrange(len(live))
            commands.append(-live.pop(idx))
            continue

        if regime == "case12_mixed_lifo":
            length = length12(rng, mode, i)
        else:
            length = length14(rng, float(parameter), i, mode)
        commands.append(length)
        live.append(next_pid)
        next_pid += 1

    if not live:
        raise AssertionError("generator must finish with an active pipe")
    return commands


def main():
    specs = [
        ("case12_mixed_lifo", 2026101801, 1500, "uniform5_39", None),
        ("case12_mixed_lifo", 2026101802, 2500, "bimodal5_39", None),
        ("case12_mixed_lifo", 2026101803, 3500, "short_skew5_39", None),
        ("case12_mixed_lifo", 2026101804, 5000, "phase_mix5_39", None),
        ("case12_mixed_lifo", 2026101805, 2000, "cyclic5_39", None),
        ("case12_mixed_lifo", 2026101806, 4000, "two_band5_39", None),
        ("case12_mixed_lifo", 2026101807, 3000, "alternating_band5_39", None),
        ("case12_mixed_lifo", 2026101808, 5000, "uniform_with_blocks5_39", None),
        ("case14_unit_lifo", 2026101811, 10000, "unit_iid", 0.95),
        ("case14_unit_lifo", 2026101812, 12000, "unit_iid", 0.93),
        ("case14_unit_lifo", 2026101813, 15000, "unit_iid", 0.92),
        ("case14_unit_lifo", 2026101814, 20000, "unit_iid", 0.91),
        ("case14_unit_lifo", 2026101815, 10000, "unit_bursts", 0.92),
        ("case14_unit_lifo", 2026101816, 12000, "unit_phase_shift", 0.94),
        ("case14_unit_lifo", 2026101817, 15000, "unit_periodic", 0.90),
        ("case14_unit_lifo", 2026101818, 20000, "unit_iid", 0.88),
    ]
    rows = []
    for regime, seed, count, mode, parameter in specs:
        name = f"{regime}_{seed}"
        commands = generate(seed, count, regime, mode, parameter)
        target = OUT / f"{name}.in"
        target.write_text("\n".join(["4 " + str(len(commands)), *map(str, commands), "0"]) + "\n",
                          encoding="ascii")
        rows.append({
            "name": name,
            "regime": regime,
            "seed": seed,
            "operations": count,
            "length_mode": mode,
            "length_parameter": parameter,
            "deletion_rule": "newest-quintile-biased 87%, otherwise uniform" if regime == "case12_mixed_lifo"
                else "newest-quintile-biased 98%, otherwise uniform",
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    manifest = {
        "created_before_solver_pair_runs": True,
        "count": len(rows),
        "regimes": {
            "case12_mixed_lifo": "lengths 5..39, churn 24%, most deletes sampled from newest PID quintile",
            "case14_unit_lifo": "unit-dominant lengths, churn 2.7%, most deletes sampled from newest PID quintile",
        },
        "streams": rows,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"count": len(rows), "manifest": str(OUT / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
