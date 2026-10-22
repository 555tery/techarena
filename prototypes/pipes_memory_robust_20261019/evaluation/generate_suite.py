#!/usr/bin/env python3
"""Build fixed calibration and sealed Pipes streams without invoking a solver."""

from __future__ import annotations

import hashlib
import heapq
import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAL_DIR = HERE / "calibration"
FINAL_DIR = HERE / "sealed-final"
MAX_OPS = 200_000


CALIBRATION: list[dict[str, Any]] = [
    {"id": "C01", "seed": 920501, "family": "iid-uniform-random", "n": 20_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C02", "seed": 920502, "family": "iid-short-heavy", "n": 20_000, "profile": "short", "delete": "random", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C03", "seed": 920503, "family": "iid-long-heavy", "n": 20_000, "profile": "long", "delete": "random", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C04", "seed": 920504, "family": "iid-bimodal", "n": 24_000, "profile": "bimodal", "delete": "random", "p_add": .49, "floor": 32, "cap": 1000},
    {"id": "C05", "seed": 920505, "family": "lifetime-fifo", "n": 30_000, "profile": "uniform", "delete": "fifo", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C06", "seed": 920506, "family": "lifetime-lifo", "n": 30_000, "profile": "uniform", "delete": "lifo", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C07", "seed": 920507, "family": "lifetime-shortest-first", "n": 30_000, "profile": "uniform", "delete": "shortest", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C08", "seed": 920508, "family": "lifetime-longest-first", "n": 30_000, "profile": "uniform", "delete": "longest", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C09", "seed": 920509, "family": "size-regime-short-long-uniform", "n": 40_000, "profile_phases": ["short", "long", "uniform"], "delete": "random", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C10", "seed": 920510, "family": "size-regime-long-short-uniform", "n": 40_000, "profile_phases": ["long", "short", "uniform"], "delete": "random", "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C11", "seed": 920511, "family": "deletion-regime-random-fifo-young", "n": 40_000, "profile": "uniform", "delete_phases": ["random", "fifo", "young"], "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C12", "seed": 920512, "family": "deletion-regime-random-longest-lifo", "n": 40_000, "profile": "bimodal", "delete_phases": ["random", "longest", "lifo"], "p_add": .50, "floor": 32, "cap": 1000},
    {"id": "C13", "seed": 920513, "family": "correlated-arrival-cohort-drain", "n": 45_000, "profile": "uniform", "delete": "random", "correlated": "cohort", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C14", "seed": 920514, "family": "correlated-size-band-drain", "n": 45_000, "profile": "bimodal", "delete": "random", "correlated": "size-band", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C15", "seed": 920515, "family": "correlated-birth-era-drain", "n": 45_000, "profile_phases": ["short", "long", "short"], "delete": "random", "correlated": "birth-era", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C16", "seed": 920516, "family": "correlated-exact-length-drain", "n": 45_000, "profile": "uniform", "delete": "random", "correlated": "exact-length", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C17", "seed": 920517, "family": "stress-200k-high-live-set", "n": 200_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 4_800, "cap": 6_200},
    {"id": "C18", "seed": 920518, "family": "stress-200k-size-regime-many-gaps", "n": 200_000, "profile_phases": ["long", "short", "long", "short"], "delete_phases": ["fifo", "young", "fifo", "random"], "p_add_phases": [.53, .48, .54, .49], "floor": 700, "cap": 1_000},
    {"id": "C19", "seed": 920519, "family": "stress-200k-small-live-rollouts", "n": 200_000, "profile_phases": ["short", "bimodal", "long", "walk"], "delete": "young", "correlated": "exact-length", "p_add": .50, "floor": 32, "cap": 128},
    {"id": "C20", "seed": 920520, "family": "correlated-cohort-drain-long", "n": 80_000, "profile": "uniform", "delete": "random", "correlated": "cohort", "p_add": .53, "floor": 32, "cap": 900},
    {"id": "C21", "seed": 920521, "family": "open-prefix-switch-case5", "n": 20_000, "prefix": {"case": 5, "ops": 1_000}, "profile": "long", "delete": "young", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C22", "seed": 920522, "family": "open-prefix-switch-case8", "n": 24_000, "prefix": {"case": 8, "ops": 1_500}, "profile_phases": ["short", "bimodal", "long"], "delete": "random", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C23", "seed": 920523, "family": "open-prefix-switch-case9", "n": 30_000, "prefix": {"case": 9, "ops": 500}, "profile": "walk", "delete_phases": ["fifo", "random", "longest"], "p_add": .51, "floor": 32, "cap": 1000},
    {"id": "C24", "seed": 920524, "family": "open-prefix-switch-case11", "n": 30_000, "prefix": {"case": 11, "ops": 1_000}, "profile": "short", "delete": "random", "correlated": "size-band", "p_add": .52, "floor": 32, "cap": 1000},
    {"id": "C25", "seed": 920525, "family": "open-prefix-switch-case14", "n": 40_000, "prefix": {"case": 14, "ops": 500}, "profile_phases": ["long", "short", "uniform"], "delete": "young", "p_add": .51, "floor": 32, "cap": 1000},
    {"id": "C26", "seed": 920526, "family": "open-prefix-switch-case15", "n": 50_000, "prefix": {"case": 15, "ops": 500}, "profile": "bimodal", "delete": "random", "correlated": "birth-era", "p_add": .52, "floor": 32, "cap": 1000},
]


# Seed and family metadata are fixed before generation. No solver is called here.
SEALED_FINAL: list[dict[str, Any]] = [
    {"id": "F01", "seed": 930101, "family": "iid-uniform-random", "n": 60_000, "profile": "uniform", "delete": "random", "p_add": .49, "floor": 32, "cap": 900},
    {"id": "F02", "seed": 930102, "family": "unseen-size-regime-order", "n": 80_000, "profile_phases": ["bimodal", "long", "short", "uniform"], "delete": "young", "p_add_phases": [.53, .50, .54, .49], "floor": 32, "cap": 1000},
    {"id": "F03", "seed": 930103, "family": "correlated-cohort-drain", "n": 60_000, "profile": "walk", "delete": "random", "correlated": "cohort", "p_add": .54, "floor": 32, "cap": 900},
    {"id": "F04", "seed": 930104, "family": "correlated-length-and-age", "n": 60_000, "profile": "bimodal", "delete": "longest", "correlated": "exact-length", "p_add": .51, "floor": 32, "cap": 900},
    {"id": "F05", "seed": 930105, "family": "stress-200k-high-live-set", "n": 200_000, "profile": "uniform", "delete": "random", "p_add": .50, "floor": 5_200, "cap": 7_000},
    {"id": "F06", "seed": 930106, "family": "stress-200k-regime-many-gaps", "n": 200_000, "profile_phases": ["long", "short", "bimodal", "walk"], "delete_phases": ["fifo", "young", "random", "lifo"], "correlated": "birth-era", "p_add_phases": [.53, .49, .54, .50], "floor": 700, "cap": 1_050},
    {"id": "F07", "seed": 930107, "family": "open-prefix-switch-case7", "n": 60_000, "prefix": {"case": 7, "ops": 250}, "profile": "long", "delete_phases": ["young", "fifo", "random"], "p_add": .52, "floor": 32, "cap": 900},
    {"id": "F08", "seed": 930108, "family": "open-prefix-switch-case15", "n": 80_000, "prefix": {"case": 15, "ops": 1_500}, "profile": "walk", "delete": "random", "correlated": "cohort", "p_add": .53, "floor": 32, "cap": 1_000},
]


def read_open_prefix(case: int, count: int) -> list[int]:
    path = ROOT / "data" / "pipes" / "open" / f"{case}.in"
    tokens = [int(x) for x in path.read_text().split()]
    # Official open files start with the case weight, then operation count.
    assert len(tokens) >= 2 and tokens[0] > 0
    declared = tokens[1]
    commands = tokens[2:2 + declared]
    assert len(commands) == declared and 0 < count <= declared
    return commands[:count]


def active_from_prefix(commands: list[int]) -> tuple[dict[int, dict[str, int]], int]:
    active: dict[int, dict[str, int]] = {}
    next_pid = 0
    for step, command in enumerate(commands):
        if command > 0:
            assert 1 <= command <= 40
            next_pid += 1
            active[next_pid] = {"length": command, "born": step, "cohort": (next_pid - 1) // 64}
        else:
            pid = -command
            assert pid in active, f"invalid prefix PID {pid} at step {step}"
            del active[pid]
    return active, next_pid


def profile_length(name: str, rng: random.Random, walk_state: list[int]) -> int:
    if name == "uniform":
        return rng.randint(1, 40)
    if name == "short":
        return rng.randint(1, 8)
    if name == "long":
        return rng.randint(25, 40)
    if name == "bimodal":
        return rng.choice((1, 2, 3, 4, 37, 38, 39, 40))
    if name == "walk":
        walk_state[0] = max(1, min(40, walk_state[0] + rng.choice((-4, -2, -1, 0, 1, 2, 4))))
        return walk_state[0]
    raise ValueError(f"unknown length profile: {name}")


def choose_phase(values: list[Any], position: int, total: int) -> Any:
    index = min(len(values) - 1, (position * len(values)) // max(1, total))
    return values[index]


def eligible_for_batch(pipe: dict[str, int], mode: str, target: int) -> bool:
    length = pipe["length"]
    if mode == "cohort":
        return pipe["cohort"] == target
    if mode == "birth-era":
        return pipe["born"] // 1_000 == target
    if mode == "size-band":
        band = 0 if length <= 8 else (1 if length <= 24 else 2)
        return band == target
    if mode == "exact-length":
        return length == target
    raise ValueError(f"unknown correlated-delete mode: {mode}")


def pick_batch(active: dict[int, dict[str, int]], mode: str, rng: random.Random) -> tuple[int, list[int]] | None:
    if mode == "cohort":
        candidates = sorted({p["cohort"] for p in active.values()})
    elif mode == "birth-era":
        candidates = sorted({p["born"] // 1_000 for p in active.values()})
    elif mode == "size-band":
        candidates = sorted({0 if p["length"] <= 8 else (1 if p["length"] <= 24 else 2) for p in active.values()})
    elif mode == "exact-length":
        candidates = sorted({p["length"] for p in active.values()})
    else:
        raise ValueError(f"unknown correlated-delete mode: {mode}")
    if not candidates:
        return None
    target = rng.choice(candidates)
    members = [pid for pid, pipe in active.items() if eligible_for_batch(pipe, mode, target)]
    rng.shuffle(members)
    return target, members[: rng.randint(4, 14)]


def select_delete(active: dict[int, dict[str, int]], policy: str, rng: random.Random,
                  dense: list[int], history: list[int], fifo_head: list[int],
                  lifo_cursor: list[int], min_heap: list[tuple[int, int]],
                  max_heap: list[tuple[int, int]]) -> int:
    if policy == "fifo":
        while fifo_head[0] < len(history) and history[fifo_head[0]] not in active:
            fifo_head[0] += 1
        pid = history[fifo_head[0]]
        fifo_head[0] += 1
        return pid
    if policy == "lifo":
        while lifo_cursor[0] > 0 and lifo_cursor[0] not in active:
            lifo_cursor[0] -= 1
        pid = lifo_cursor[0]
        lifo_cursor[0] -= 1
        return pid
    if policy == "young":
        window = [pid for pid in history[-16:] if pid in active]
        return rng.choice(window if window else dense)
    if policy == "shortest":
        while min_heap[0][1] not in active:
            heapq.heappop(min_heap)
        return min_heap[0][1]
    if policy == "longest":
        while max_heap[0][1] not in active:
            heapq.heappop(max_heap)
        return max_heap[0][1]
    if policy == "random":
        return rng.choice(dense)
    raise ValueError(f"unknown deletion policy: {policy}")


def validate_commands(commands: list[int], expected_n: int, floor: int, floor_start: int = 0) -> dict[str, int]:
    assert len(commands) == expected_n and 1 <= expected_n <= MAX_OPS
    active: dict[int, int] = {}
    next_pid = 0
    peak_live_count = 0
    peak_live_length = 0
    min_live_count = expected_n
    live_length = 0
    first_floor_step: int | None = None
    min_live_after_floor = expected_n
    for index, command in enumerate(commands):
        if index == floor_start and len(active) >= floor:
            first_floor_step = index
            min_live_after_floor = len(active)
        if command > 0:
            assert 1 <= command <= 40
            next_pid += 1
            active[next_pid] = command
            live_length += command
        else:
            pid = -command
            assert pid > 0 and pid in active, f"invalid PID {pid} at command {index}"
            live_length -= active.pop(pid)
        peak_live_count = max(peak_live_count, len(active))
        min_live_count = min(min_live_count, len(active))
        peak_live_length = max(peak_live_length, live_length)
        if index >= floor_start and first_floor_step is None and len(active) >= floor:
            first_floor_step = index + 1
        if first_floor_step is not None:
            min_live_after_floor = min(min_live_after_floor, len(active))
    final_volume = sum(active.values())
    assert first_floor_step is not None, f"live floor {floor} was never reached"
    assert min_live_after_floor >= floor, f"live set dropped below configured floor {floor}"
    assert final_volume > 0, "final live length must be positive"
    assert peak_live_length <= 100_000_000
    return {"operations": len(commands), "placements": next_pid, "deletions": len(commands) - next_pid,
            "configured_live_floor": floor, "first_floor_reached_at": first_floor_step,
            "min_live_count_after_command": min_live_count,
            "min_live_count_after_floor_reached": min_live_after_floor,
            "peak_live_count": peak_live_count, "peak_live_length": peak_live_length,
            "final_live_count": len(active), "final_live_length": final_volume}


def build_one(spec: dict[str, Any]) -> tuple[list[int], dict[str, int]]:
    rng = random.Random(spec["seed"])
    n = int(spec["n"])
    prefix = read_open_prefix(spec["prefix"]["case"], spec["prefix"]["ops"]) if "prefix" in spec else []
    commands = list(prefix)
    active, next_pid = active_from_prefix(commands)
    walk_state = [20]
    batch: list[int] = []
    dense = list(active)
    dense_pos = {pid: index for index, pid in enumerate(dense)}
    history = list(range(1, next_pid + 1))
    fifo_head = [0]
    lifo_cursor = [next_pid]
    min_heap = [(pipe["length"], pid) for pid, pipe in active.items()]
    max_heap = [(-pipe["length"], pid) for pid, pipe in active.items()]
    heapq.heapify(min_heap)
    heapq.heapify(max_heap)

    for step in range(len(commands), n - 1):
        relative_step = step - len(prefix)
        relative_total = max(1, n - len(prefix) - 1)
        if "profile_phases" in spec:
            profile = choose_phase(spec["profile_phases"], relative_step, relative_total)
        else:
            profile = spec.get("profile", "uniform")
        if "delete_phases" in spec:
            delete_policy = choose_phase(spec["delete_phases"], relative_step, relative_total)
        else:
            delete_policy = spec.get("delete", "random")
        if "p_add_phases" in spec:
            p_add = choose_phase(spec["p_add_phases"], relative_step, relative_total)
        else:
            p_add = spec.get("p_add", .5)
        cap = int(spec.get("cap", 3000))

        floor = int(spec.get("floor", 32))
        if "correlated_phases" in spec:
            correlated_mode = choose_phase(spec["correlated_phases"], relative_step, relative_total)
        else:
            correlated_mode = spec.get("correlated")
        if active and len(active) > floor and len(active) < cap and rng.random() < .035 and correlated_mode and not batch:
            selected = pick_batch(active, correlated_mode, rng)
            if selected is not None:
                _, batch = selected

        delete_pid: int | None = None
        force_add = len(active) <= floor
        if batch and not force_add:
            while batch and batch[0] not in active:
                batch.pop(0)
            if batch:
                delete_pid = batch.pop(0)
            else:
                batch = []

        must_delete = bool(active) and (len(active) >= cap or (not force_add and rng.random() >= p_add))
        if delete_pid is None and must_delete:
            delete_pid = select_delete(active, delete_policy, rng, dense, history, fifo_head,
                                       lifo_cursor, min_heap, max_heap)

        if delete_pid is not None and delete_pid in active:
            commands.append(-delete_pid)
            del active[delete_pid]
            index = dense_pos.pop(delete_pid)
            last_pid = dense.pop()
            if index < len(dense):
                dense[index] = last_pid
                dense_pos[last_pid] = index
        else:
            length = profile_length(profile, rng, walk_state)
            next_pid += 1
            commands.append(length)
            active[next_pid] = {"length": length, "born": step, "cohort": (next_pid - 1) // 64}
            dense_pos[next_pid] = len(dense)
            dense.append(next_pid)
            history.append(next_pid)
            lifo_cursor[0] = next_pid
            heapq.heappush(min_heap, (length, next_pid))
            heapq.heappush(max_heap, (-length, next_pid))

    # The final positive command makes F>0 for every generated test.
    final_profile = spec.get("profile", "uniform")
    if "profile_phases" in spec:
        final_profile = spec["profile_phases"][-1]
    final_length = profile_length(final_profile, rng, walk_state)
    commands.append(final_length)

    # Run all structural checks in memory before serialization. No solver or KPI
    # evaluation is involved, including for sealed-final inputs.
    meta = validate_commands(commands, n, int(spec.get("floor", 32)), len(prefix))
    return commands, meta


def write_suite(directory: Path, specs: list[dict[str, Any]], sealed: bool, suite_suffix: str = "") -> None:
    directory.mkdir(parents=True, exist_ok=False)
    entries: list[dict[str, Any]] = []
    total_ops = 0
    for spec in specs:
        commands, validity = build_one(spec)
        stem = f"{spec['id'].lower()}-{spec['family']}"
        path = directory / f"{stem}.in"
        payload = f"1\n{len(commands)}\n" + "\n".join(map(str, commands)) + "\n"
        raw = payload.encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        total_ops += len(commands)
        entries.append({
            "id": spec["id"], "file": path.name, "seed": spec["seed"],
            "family": spec["family"], "sha256": digest,
            "n": len(commands), "parameters": {k: v for k, v in spec.items() if k not in {"id", "seed", "family", "n"}},
            "structural_validity": validity,
        })
        if sealed:
            path.chmod(0o444)

    manifest = {
        "suite": ("pipes-memory-generalization-final" + suite_suffix) if sealed else "pipes-memory-generalization-calibration",
        "status": "sealed-do-not-evaluate-before-parent-freeze" if sealed else "calibration",
        "generator": "generate_suite.py",
        "solver_invoked": False,
        "rules": {"max_operations": MAX_OPS, "pipe_length": [1, 40], "pid": "sequential placements; each deletion references one currently active PID", "final_live_length": "> 0"},
        "test_count": len(entries), "total_operations": total_ops,
        "recommended_short_calibration": ["C01", "C03", "C05", "C07", "C09", "C11", "C13", "C15", "C18", "C19", "C22", "C26"] if not sealed else None,
        "tests": entries,
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if sealed:
        manifest_path.chmod(0o400)


def main() -> None:
    if CAL_DIR.exists() or FINAL_DIR.exists():
        raise SystemExit("Refusing to overwrite existing calibration or sealed-final suite.")
    write_suite(CAL_DIR, CALIBRATION, sealed=False)
    write_suite(FINAL_DIR, SEALED_FINAL, sealed=True)
    print(f"calibration: {len(CALIBRATION)} fixed inputs, generated and structurally checked")
    print(f"sealed final: {len(SEALED_FINAL)} fixed inputs, generated and structurally checked; no solver run")
    print("See calibration/manifest.json and sealed-final/manifest.json for seeds, groups and hashes.")


if __name__ == "__main__":
    main()
