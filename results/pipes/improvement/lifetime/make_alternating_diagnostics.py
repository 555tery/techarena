#!/usr/bin/env python3
"""Generate fixed exploratory streams with FIFO/LIFO/random policy phases.

These are newly generated diagnostics, not a holdout or score estimate. The
solver sees only ordinary online placement/deletion commands; no phase labels
or generator metadata are included in the input.
"""

from collections import deque
import hashlib
import heapq
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic_alternating"
OUT.mkdir(parents=True, exist_ok=True)
MASTER_SEED = 63_419_087
OPERATION_COUNT = 30_000
MAX_LIVE = 600
PHASE_LENGTH = 5_000
POLICIES = ("fifo", "lifo", "random")


def sample_uniform(rng, pid):
    return rng.randint(1, 40)


def sample_short_skew(rng, pid):
    return rng.randint(1, 5) if rng.random() < 0.82 else rng.randint(6, 40)


def sample_long_skew(rng, pid):
    return rng.randint(30, 40) if rng.random() < 0.82 else rng.randint(1, 29)


def sample_bimodal(rng, pid):
    return 1 if rng.random() < 0.5 else 40


def sample_cycle(rng, pid):
    return 1 + ((pid * 23 + pid // 11) % 40)


SAMPLERS = (
    ("uniform", sample_uniform),
    ("short_skew", sample_short_skew),
    ("long_skew", sample_long_skew),
    ("bimodal", sample_bimodal),
    ("cycle", sample_cycle),
)


def make_stream(name, sampler, seed):
    rng = random.Random(seed)
    commands = []
    active = set()
    active_dense = []
    dense_index = {}
    fifo = deque()
    lifo = []
    fifo_head = 0
    pid = 0
    phases = []
    phase_policy_counts = {policy: {"placements": 0, "deletions": 0} for policy in POLICIES}

    def remove_random(chosen):
        idx = dense_index.pop(chosen)
        last = active_dense.pop()
        if idx < len(active_dense):
            active_dense[idx] = last
            dense_index[last] = idx
        active.remove(chosen)

    for op in range(OPERATION_COUNT):
        phase = op // PHASE_LENGTH
        policy = POLICIES[phase % len(POLICIES)]
        if not phases or phases[-1]["policy"] != policy:
            phases.append({"start_operation_1based": op + 1, "end_operation_1based": None, "policy": policy})
            if len(phases) > 1:
                phases[-2]["end_operation_1based"] = op

        insert = not active or (len(active) < MAX_LIVE and rng.random() < 0.56)
        if insert:
            pid += 1
            length = sampler(rng, pid)
            commands.append(length)
            active.add(pid)
            dense_index[pid] = len(active_dense)
            active_dense.append(pid)
            fifo.append(pid)
            lifo.append(pid)
            phase_policy_counts[policy]["placements"] += 1
            continue

        if policy == "fifo":
            while fifo_head < len(fifo) and fifo[fifo_head] not in active:
                fifo_head += 1
            chosen = fifo[fifo_head]
            fifo_head += 1
        elif policy == "lifo":
            while lifo and lifo[-1] not in active:
                lifo.pop()
            chosen = lifo.pop()
        else:
            chosen = active_dense[rng.randrange(len(active_dense))]
        commands.append(-chosen)
        remove_random(chosen)
        phase_policy_counts[policy]["deletions"] += 1

    if phases:
        phases[-1]["end_operation_1based"] = OPERATION_COUNT
    path = OUT / f"alternating_{name}_30k.in"
    path.write_text(f"1\n{OPERATION_COUNT}\n" + "\n".join(map(str, commands)) + "\n", encoding="ascii")
    return {
        "name": name,
        "file": path.name,
        "seed": seed,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "operation_count": OPERATION_COUNT,
        "max_live": MAX_LIVE,
        "size_distribution": sampler.__name__,
        "policy_phase_length": PHASE_LENGTH,
        "policy_cycle": list(POLICIES),
        "phases": phases,
        "policy_counts_by_policy": phase_policy_counts,
        "purpose": "new exploratory diagnostic only; not a holdout and not used to tune candidate",
    }


manifest = {
    "master_seed": MASTER_SEED,
    "operation_count": OPERATION_COUNT,
    "max_live": MAX_LIVE,
    "phase_length": PHASE_LENGTH,
    "policy_cycle": list(POLICIES),
    "streams": [make_stream(name, sampler, MASTER_SEED + i) for i, (name, sampler) in enumerate(SAMPLERS)],
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
