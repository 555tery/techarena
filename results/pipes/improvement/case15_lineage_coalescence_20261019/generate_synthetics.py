#!/usr/bin/env python3
"""Generate a fresh, pre-run suite for local coalescence-lineage screening."""
from pathlib import Path
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic_fresh"
OUT.mkdir(parents=True, exist_ok=True)

profiles = [
    {"name":"uniform_lifo35_s7319", "seed":7319, "batches":6, "count":3000, "sizes":"uniform", "delete":"lifo", "fraction":0.25},
    {"name":"small_heavy_random40_s9411", "seed":9411, "batches":6, "count":3500, "sizes":"small_heavy", "delete":"random_active", "fraction":0.40},
    {"name":"bimodal_fifo35_s1187", "seed":1187, "batches":6, "count":3000, "sizes":"bimodal", "delete":"fifo_active", "fraction":0.35},
    {"name":"phase_mixed_s4217", "seed":4217, "batches":4, "count":4000, "sizes":"phase", "delete":"random_batch", "fraction":0.30},
    {"name":"geometric_parity_s6301", "seed":6301, "batches":6, "count":2500, "sizes":"geometric", "delete":"pid_parity", "fraction":0.50},
    {"name":"fixed_size_churn_s8513", "seed":8513, "batches":6, "count":3500, "sizes":"fixed_cycle", "delete":"random_batch", "fraction":0.40},
    {"name":"uniform_fifo30_s2069", "seed":2069, "batches":5, "count":5000, "sizes":"uniform", "delete":"fifo_active", "fraction":0.30},
    {"name":"reversal_lifo50_s3821", "seed":3821, "batches":4, "count":4000, "sizes":"reversal", "delete":"lifo", "fraction":0.50},
]

phase_values = [
    (1, 5), (24, 40), (6, 18), (1, 40)
]
fixed_cycle = [7, 11, 23, 5, 33, 2]
geom = [1, 2, 4, 8, 16, 32]

def sample_size(rng, mode, batch, index):
    if mode == "uniform":
        return rng.randint(1, 40)
    if mode == "small_heavy":
        values = list(range(1, 13))
        weights = [1.0 / value for value in values]
        return rng.choices(values, weights=weights, k=1)[0]
    if mode == "bimodal":
        return 2 if rng.random() < 0.55 else 32
    if mode == "phase":
        lo, hi = phase_values[batch]
        return rng.randint(lo, hi)
    if mode == "geometric":
        return geom[batch]
    if mode == "fixed_cycle":
        return fixed_cycle[batch]
    if mode == "reversal":
        if batch == 0:
            return rng.randint(1, 10)
        if batch == 1:
            return rng.randint(30, 40)
        if batch == 2:
            return rng.randint(2, 8)
        return rng.randint(1, 40)
    raise ValueError(mode)

manifest = {"title":"Fresh independent synthetic screen for generation-aware one-step coalescence tie-break", "generated_before_solver_runs":True, "profiles":[]}
for profile in profiles:
    rng = random.Random(profile["seed"])
    commands = []
    active = []
    next_pid = 1
    for batch in range(profile["batches"]):
        batch_pids = []
        for index in range(profile["count"]):
            commands.append(sample_size(rng, profile["sizes"], batch, index))
            batch_pids.append(next_pid)
            active.append(next_pid)
            next_pid += 1
        n_delete = int(profile["count"] * profile["fraction"])
        mode = profile["delete"]
        if mode == "lifo":
            selected = batch_pids[-n_delete:]
        elif mode == "fifo_active":
            selected = active[:n_delete]
        elif mode == "random_active":
            selected = rng.sample(active, min(n_delete, len(active)))
        elif mode == "random_batch":
            selected = rng.sample(batch_pids, n_delete)
        elif mode == "pid_parity":
            parity = (batch + 1) & 1
            pool = [pid for pid in batch_pids if pid & 1 == parity]
            selected = pool[:n_delete]
        else:
            raise ValueError(mode)
        selected_set = set(selected)
        commands.extend(-pid for pid in selected)
        active = [pid for pid in active if pid not in selected_set]
    path = OUT / f"{profile['name']}.in"
    path.write_text(f"1.0 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
    raw = path.read_bytes()
    manifest["profiles"].append({**profile, "path":str(path.relative_to(ROOT)), "operations":len(commands), "sha256":hashlib.sha256(raw).hexdigest()})
(OUT.parent / "synthetic_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
