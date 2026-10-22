#!/usr/bin/env python3
"""Generate fixed, independent Pipes traces for coalescence-policy validation.

Only Python's standard library is required. Sealed inputs require an explicit
freeze identifier and are deliberately generated as a separate later step.
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "tools" / "pipes_harness.py").is_file())
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from tools.pipes_harness import parse_test  # noqa: E402


MANIFEST_PATH = HERE / "manifest.json"
WEIGHT = 1
DEVELOPMENT = [
    ("dev01", 71527001, "mixed_iid_uniform", 20000),
    ("dev02", 71527002, "near_lifo_local", 18000),
    ("dev03", 71527003, "fifo_control", 22000),
    ("dev04", 71527004, "random_deletion_control", 19000),
    ("dev05", 71527005, "increasing_size_regime_blocks", 24000),
    ("dev06", 71527006, "decreasing_size_regime_blocks", 16000),
    ("dev07", 71527007, "random_size_regime_blocks", 21000),
    ("dev08", 71527008, "batched_cohorts_noisy_survivors", 25000),
    ("dev09", 71527009, "mixed_iid_uniform", 17000),
    ("dev10", 71527010, "near_lifo_local", 23000),
    ("dev11", 71527011, "fifo_control", 15000),
    ("dev12", 71527012, "random_deletion_control", 20000),
]
SEALED = [
    ("seal01", 71527101, "mixed_iid_uniform", 30000),
    ("seal02", 71527102, "near_lifo_local", 200000),
    ("seal03", 71527103, "fifo_control", 30000),
    ("seal04", 71527104, "random_deletion_control", 30000),
    ("seal05", 71527105, "increasing_size_regime_blocks", 30000),
    ("seal06", 71527106, "decreasing_size_regime_blocks", 30000),
    ("seal07", 71527107, "random_size_regime_blocks", 30000),
    ("seal08", 71527108, "batched_cohorts_noisy_survivors", 200000),
    ("seal09", 71527109, "mixed_iid_uniform", 30000),
    ("seal10", 71527110, "near_lifo_local", 30000),
    ("seal11", 71527111, "fifo_control", 30000),
    ("seal12", 71527112, "random_deletion_control", 30000),
]


def pipe_length(profile, op_index, n, rng, random_bands):
    if profile not in {
        "increasing_size_regime_blocks",
        "decreasing_size_regime_blocks",
        "random_size_regime_blocks",
    }:
        return rng.randint(1, 40)
    block = min(4, (op_index * 5) // max(1, n))
    low_bands = [(1, 9), (7, 17), (14, 24), (21, 32), (28, 40)]
    bands = list(reversed(low_bands)) if profile == "decreasing_size_regime_blocks" else low_bands
    if profile == "random_size_regime_blocks":
        bands = random_bands
    low, high = bands[block]
    return rng.randint(low, high)


def generate_commands(seed, profile, n):
    rng = random.Random(seed)
    random_bands = [rng.choice([(1, 9), (7, 17), (14, 24), (21, 32), (28, 40)]) for _ in range(5)]
    alive = [False]
    live_ids = []
    live_pos = {}
    commands = []
    fifo_cursor = 1
    cohort = []
    pending_batch = []
    cohort_target = rng.randint(90, 180)
    next_pid = 1

    def place(op_index):
        nonlocal next_pid
        size = pipe_length(profile, op_index, n, rng, random_bands)
        pid = next_pid
        next_pid += 1
        alive.append(True)
        live_pos[pid] = len(live_ids)
        live_ids.append(pid)
        commands.append(size)
        return pid

    def delete(pid):
        pos = live_pos.pop(pid)
        last = live_ids.pop()
        if pos < len(live_ids):
            live_ids[pos] = last
            live_pos[last] = pos
        alive[pid] = False
        commands.append(-pid)

    def random_live():
        return live_ids[rng.randrange(len(live_ids))]

    def oldest_live():
        nonlocal fifo_cursor
        while fifo_cursor < len(alive) and not alive[fifo_cursor]:
            fifo_cursor += 1
        if fifo_cursor >= len(alive):
            return random_live()
        return fifo_cursor

    def choose_regular_deletion():
        if profile == "fifo_control":
            return oldest_live()
        if profile == "near_lifo_local" and rng.random() < 0.88:
            recent = [pid for pid in range(max(1, next_pid - 65), next_pid) if alive[pid]]
            if recent:
                return recent[-rng.randint(1, min(12, len(recent)))]
        return random_live()

    # Reserve the final operation as a placement so every trace has live pipes.
    for op_index in range(n - 1):
        if profile == "batched_cohorts_noisy_survivors":
            if not pending_batch:
                cohort_alive = [pid for pid in cohort if alive[pid]]
                if len(cohort_alive) >= cohort_target:
                    keep_fraction = rng.uniform(0.12, 0.27)
                    delete_count = max(1, min(len(cohort_alive) - 1, round(len(cohort_alive) * (1 - keep_fraction))))
                    pending_batch = rng.sample(cohort_alive, delete_count)
                    cohort = []  # unselected members survive as noisy long-lived pipes
                    cohort_target = rng.randint(90, 180)
            if pending_batch and rng.random() >= 0.08:
                pid = pending_batch.pop()
                if alive[pid]:
                    delete(pid)
                else:
                    place(op_index)
            elif live_ids and rng.random() < 0.035:
                delete(random_live())
            else:
                cohort.append(place(op_index))
            continue

        live_count = len(live_ids)
        if live_count < 180:
            do_delete = False
        elif live_count > 1800:
            do_delete = True
        else:
            delete_probability = 0.56 if profile == "random_deletion_control" else 0.5
            do_delete = rng.random() < delete_probability
        if do_delete and live_ids:
            delete(choose_regular_deletion())
        else:
            place(op_index)

    # The terminal positive command also keeps the declared operation count exact.
    place(n - 1)
    return commands


def validate_file(path, expected_n):
    tokens = path.read_text(encoding="ascii").split()
    if len(tokens) < 3 or tokens[0] != "1":
        raise ValueError(f"{path}: expected header '1 n'")
    n = int(tokens[1])
    if n != expected_n or n > 200000:
        raise ValueError(f"{path}: wrong or excessive operation count")
    if len(tokens) != n + 3 or tokens[-1] != "0":
        raise ValueError(f"{path}: command count or trailing sentinel mismatch")
    commands = [int(token) for token in tokens[2:-1]]
    alive = [False]
    pipe_lengths = [0]
    total = 0
    peak = 0
    for command in commands:
        if command > 0:
            if command > 40:
                raise ValueError(f"{path}: pipe length outside 1..40")
            alive.append(True)
            pipe_lengths.append(command)
            total += command
            peak = max(peak, total)
        elif command < 0:
            pid = -command
            if pid >= len(alive) or not alive[pid]:
                raise ValueError(f"{path}: deleting absent or already-deleted PID {pid}")
            alive[pid] = False
            total -= pipe_lengths[pid]
        else:
            raise ValueError(f"{path}: embedded zero command")
        if total < 0 or peak > 100_000_000:
            raise ValueError(f"{path}: occupancy bounds violated")
    if total <= 0:
        raise ValueError(f"{path}: no live pipe at end")
    # Independent of parse_test's validation, verify the repository harness too.
    parsed = parse_test(path)
    if parsed["operation_count"] != n or parsed["final_occupied_length_m"] != total:
        raise ValueError(f"{path}: harness metadata disagrees with local replay")
    return parsed


def make_manifest(freeze_id=None):
    def entries(specs, suite):
        old_rows = {
            row["id"]: row
            for row in old.get(suite, [])
        }
        return [
            {
                **old_rows.get(case_id, {}),
                "id": case_id,
                "seed": seed,
                "profile": profile,
                "operation_count": n,
                "path": f"inputs/{suite}/{case_id}.in",
                "sha256": old_rows.get(case_id, {}).get("sha256"),
                "generated": old_rows.get(case_id, {}).get("generated", False),
                "validation": old_rows.get(case_id, {}).get("validation"),
            }
            for case_id, seed, profile, n in specs
        ]

    old = {}
    if MANIFEST_PATH.exists():
        old = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "purpose": "Independent synthetic validation for general causal hole-coalescence behavior.",
        "design_fixed_before_solver_metrics": True,
        "generator": "generate.py; Python standard library random.Random (MT19937)",
        "python_version": sys.version.split()[0],
        "generation_parameters": {
            "non_cohort_live_pipe_floor": 180,
            "non_cohort_live_pipe_ceiling": 1800,
            "baseline_deletion_probability": 0.5,
            "random_deletion_control_probability": 0.56,
            "near_lifo_selection_probability": 0.88,
            "near_lifo_pid_window": 64,
            "near_lifo_choice_among_most_recent_live_pids": 12,
            "cohort_size_range": [90, 180],
            "cohort_survivor_fraction_range": [0.12, 0.27],
            "cohort_batch_noisy_operation_probability": 0.08,
            "cohort_background_random_delete_probability": 0.035,
            "size_regime_block_count": 5,
        },
        "development": entries(DEVELOPMENT, "development"),
        "sealed_validation": entries(SEALED, "sealed_validation"),
        "sealed_generation_gate": {
            "required_cli_argument": "--freeze-id",
            "freeze_id": freeze_id or old.get("sealed_generation_gate", {}).get("freeze_id"),
            "generated_after_freeze": old.get("sealed_generation_gate", {}).get("generated_after_freeze"),
        },
        "rationale": [
            "Pipes commands expose insertions and deletions; deletion turns occupied intervals into reusable holes, and nearby later deletions can merge them.",
            "The suite includes cohort bursts and near-LIFO locality to exercise that mechanism, while IID, FIFO, and random-delete controls test whether gains survive different lifetimes.",
            "Length regimes vary over whole blocks and the seeds are newly fixed in the 71527001+ range; no official input, PID sequence, prefix, or case-specific value is used.",
            "Each case is a fresh PRNG trace with no solver feedback. Development and sealed-validation seeds are disjoint; each suite contains all eight profile families, with one or two cases per family.",
        ],
        "score_policy": "No scores are generated here. Select up to two candidates using development only, freeze, then evaluate once on sealed_validation.",
    }


def generate_suite(suite, freeze_id=None):
    specs = DEVELOPMENT if suite == "development" else SEALED
    if suite == "sealed_validation" and not freeze_id:
        raise SystemExit("sealed_validation generation requires --freeze-id after candidate freeze")
    out_dir = HERE / "inputs" / suite
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {}
    for case_id, seed, profile, n in specs:
        path = out_dir / f"{case_id}.in"
        commands = generate_commands(seed, profile, n)
        if len(commands) != n:
            raise RuntimeError(f"{case_id}: generator produced {len(commands)} commands, expected {n}")
        body = " ".join(map(str, commands))
        path.write_text(f"{WEIGHT} {n}\n{body}\n0\n", encoding="ascii")
        validation = validate_file(path, n)
        by_id[case_id] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "generated": True,
            "validation": {
                "operation_count": validation["operation_count"],
                "placement_count": validation["placement_count"],
                "peak_live_pipe_length_m": validation["peak_live_pipe_length_m"],
                "final_occupied_length_m": validation["final_occupied_length_m"],
                "minimum_trench_lower_bound_m": validation["minimum_trench_lower_bound_m"],
            },
        }
    manifest = make_manifest(freeze_id)
    cases = manifest[suite]
    for case in cases:
        case.update(by_id.get(case["id"], {}))
    if suite == "sealed_validation":
        manifest["sealed_generation_gate"]["generated_after_freeze"] = True
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated and validated {len(specs)} {suite} streams in {out_dir}")
    for case in cases:
        if case["generated"]:
            print(f"{case['id']} {case['operation_count']} {case['sha256']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["development", "sealed_validation"], required=True)
    parser.add_argument("--freeze-id", help="required label/hash identifying the frozen candidate set for sealed generation")
    args = parser.parse_args()
    generate_suite(args.suite, args.freeze_id)


if __name__ == "__main__":
    main()
