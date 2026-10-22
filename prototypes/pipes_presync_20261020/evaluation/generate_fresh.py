#!/usr/bin/env python3
"""Generate an independent, deterministic pre-synchronization Pipes suite.

The generator reads only the four public inputs named below, and only the
requested public prefixes plus one following operation. It never reads a
solver, solver output, prior fixed-control input, or evaluation result.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[3]
EVALUATION = Path(__file__).resolve().parent
OUT = EVALUATION / "fresh"
PUBLIC_DIR = ROOT / "data" / "pipes" / "open"
MASTER_SEED = 202610201059
PUBLIC_CASES = (8, 11, 13, 15)
PUBLIC_CUTS = (3, 7, 8, 14, 17, 194, 388, 402, 410, 1000)
MAX_PIPE_LENGTH = 40
MAX_PID = 100_000
MAX_COMMANDS = 200_000
PUBLIC_PREFIX_DIGESTS: dict[str, str] = {}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_public_prefix(case_id: int, cut: int) -> tuple[list[int], int]:
    """Read a public file header and exactly cut+1 commands."""
    path = PUBLIC_DIR / f"{case_id}.in"
    with path.open("r", encoding="ascii") as stream:
        header = stream.readline().split()
        if len(header) != 2:
            raise ValueError(f"unexpected public header in {path}")
        weight, declared_count = map(int, header)
        if cut < 1 or cut + 1 > declared_count:
            raise ValueError(f"cut {cut} unavailable in public case {case_id}")
        commands: list[int] = []
        for _ in range(cut + 1):
            line = stream.readline()
            if not line:
                raise ValueError(f"truncated public case {case_id} before cut {cut}")
            fields = line.split()
            if len(fields) != 1:
                raise ValueError(f"unexpected command line in {path}")
            commands.append(int(fields[0]))
    prefix = commands[:cut]
    following = commands[cut]
    canonical = ("\n".join(map(str, prefix + [following])) + "\n").encode("ascii")
    PUBLIC_PREFIX_DIGESTS[f"{case_id}:{cut}"] = sha256_bytes(canonical)
    return prefix, following


def random_composition(total: int, rng: random.Random, max_parts: int) -> list[int]:
    """Partition total into shuffled integer pieces in [1, 40]."""
    if total <= 0:
        return []
    min_parts = (total + MAX_PIPE_LENGTH - 1) // MAX_PIPE_LENGTH
    max_parts = min(max_parts, total)
    if min_parts > max_parts:
        raise ValueError(f"cannot partition {total} into at most {max_parts} pieces")
    count = rng.randint(min_parts, max_parts)
    left = total
    pieces: list[int] = []
    for index in range(count):
        remaining_slots = count - index - 1
        low = max(1, left - MAX_PIPE_LENGTH * remaining_slots)
        high = min(MAX_PIPE_LENGTH, left - remaining_slots)
        piece = rng.randint(low, high)
        pieces.append(piece)
        left -= piece
    if left != 0:
        raise AssertionError("composition did not consume its total")
    rng.shuffle(pieces)
    return pieces


def near_twenty_volume(rng: random.Random) -> tuple[int, int]:
    """Return a dense volume 40..1000, exact or close to a 20m boundary."""
    boundary = 20 * rng.randint(2, 50)
    offset = rng.choice((0, 0, 0, -19, -10, -5, -2, -1, 1, 2, 5, 10, 19))
    volume = max(40, min(1000, boundary + offset))
    return volume, volume % 20


def add_pipe(commands: list[int], active: dict[int, int], next_pid: int, length: int) -> int:
    if not 1 <= length <= MAX_PIPE_LENGTH:
        raise ValueError(f"pipe length outside [1,40]: {length}")
    if next_pid > MAX_PID:
        raise ValueError("PID ceiling exceeded")
    commands.append(length)
    active[next_pid] = length
    return next_pid + 1


def fill_with_shifted_replacements(
    commands: list[int],
    active: dict[int, int],
    next_pid: int,
    goal_count: int,
    protected: set[int],
    rng: random.Random,
) -> int:
    """Fill to goal using delete/re-add equal-length pieces to shift PID tails."""
    while len(commands) + 2 <= goal_count:
        movable = [pid for pid in active if pid not in protected]
        if not movable:
            movable = list(active)
        if not movable:
            # This path is only reachable for an empty neutral-style state.
            next_pid = add_pipe(commands, active, next_pid, rng.randint(1, MAX_PIPE_LENGTH))
            continue
        old_pid = rng.choice(movable)
        length = active.pop(old_pid)
        commands.append(-old_pid)
        next_pid = add_pipe(commands, active, next_pid, length)
    if len(commands) < goal_count:
        movable = [pid for pid in active if pid not in protected]
        if not movable:
            movable = list(active)
        if not movable:
            next_pid = add_pipe(commands, active, next_pid, rng.randint(1, MAX_PIPE_LENGTH))
        else:
            pid = rng.choice(movable)
            commands.append(-pid)
            del active[pid]
    return next_pid


def make_directed(
    rng: random.Random,
    name: str,
    operations: int,
    divergence: str,
    pin_mode: str,
    duration_class: str,
) -> tuple[list[int], dict]:
    commands = [3, 2]
    active = {1: 3, 2: 2}
    next_pid = 3

    if divergence == "delete_pid1":
        commands.append(-1)
        active.pop(1)
        protected = {2}
    elif divergence == "retain_pid1_pid2":
        max_third = min(MAX_PIPE_LENGTH, 40 - 6)
        first_mutation_length = rng.randint(1, max_third)
        next_pid = add_pipe(commands, active, next_pid, first_mutation_length)
        protected = {1, 2}
    else:
        raise ValueError(divergence)

    target_volume, boundary_offset = near_twenty_volume(rng)
    current_volume = sum(active.values())
    residual = target_volume - current_volume
    if residual <= 0:
        raise AssertionError("directed target must exceed shared-prefix occupancy")
    max_extra = 36 - len(active)
    pieces = random_composition(residual, rng, max_extra)
    for piece in pieces:
        next_pid = add_pipe(commands, active, next_pid, piece)
    if sum(active.values()) != target_volume:
        raise AssertionError("exact target-volume partition was not achieved")

    if operations < 80 or len(commands) >= operations:
        raise ValueError(f"directed case too short for partition and pin schedule: {operations}")

    if pin_mode == "80_percent":
        # PID2 remains present for 80% of the commands after the shared [3,2].
        live_until = 2 + int(0.8 * (operations - 2))
        delete_at = live_until + 1
        if len(commands) >= delete_at:
            raise AssertionError("construction consumed the PID2 pin interval")
        next_pid = fill_with_shifted_replacements(
            commands, active, next_pid, delete_at - 1, protected, rng
        )
        if 2 not in active:
            raise AssertionError("PID2 unexpectedly absent before pin expiry")
        commands.append(-2)
        active.pop(2)
    elif pin_mode != "forever":
        raise ValueError(pin_mode)

    next_pid = fill_with_shifted_replacements(
        commands, active, next_pid, operations, protected, rng
    )
    if len(commands) != operations:
        raise AssertionError("directed operation count mismatch")
    if not active:
        raise AssertionError("directed case has empty final state")

    return commands, {
        "name": name,
        "family": "prefix_3_2_live_pid2",
        "duration_class": duration_class,
        "public_prefix": {"source_cases": [11, 15], "commands": [3, 2]},
        "first_divergence": 3,
        "divergence_mode": divergence,
        "pid2_lifetime": pin_mode,
        "target_live_volume": target_volume,
        "target_volume_mod_20": boundary_offset,
        "partition_piece_count": len(pieces),
        "piece_order": "fresh_seeded_random_composition_1_to_40",
        "operations": operations,
    }


def replay_prefix(prefix: Iterable[int]) -> tuple[dict[int, int], int]:
    active: dict[int, int] = {}
    next_pid = 1
    for command in prefix:
        if command > 0:
            if not 1 <= command <= MAX_PIPE_LENGTH:
                raise ValueError("public prefix contains an invalid pipe length")
            active[next_pid] = command
            next_pid += 1
        else:
            pid = -command
            if pid not in active:
                raise ValueError(f"public prefix deletes inactive PID {pid}")
            del active[pid]
    return active, next_pid


def random_continuation(
    rng: random.Random,
    commands: list[int],
    active: dict[int, int],
    next_pid: int,
    total_operations: int,
    avoid_first_command: int | None = None,
) -> int:
    if avoid_first_command is not None and len(commands) < total_operations:
        # A fresh positive operation always preserves PID validity and ensures
        # the public prefix is followed by a genuine new continuation.
        options = [length for length in range(1, MAX_PIPE_LENGTH + 1)
                   if length != avoid_first_command]
        if avoid_first_command <= 0:
            options = list(range(1, MAX_PIPE_LENGTH + 1))
        if not options:
            options = [1]
        next_pid = add_pipe(commands, active, next_pid, rng.choice(options))

    while len(commands) < total_operations:
        remaining = total_operations - len(commands)
        if remaining == 1 and len(active) <= 1:
            want_add = True
        elif len(active) == 0:
            want_add = True
        elif len(active) >= 40:
            want_add = False
        else:
            want_add = rng.random() < 0.56

        if want_add:
            next_pid = add_pipe(commands, active, next_pid, rng.randint(1, MAX_PIPE_LENGTH))
        else:
            pid = rng.choice(list(active))
            commands.append(-pid)
            del active[pid]
    if not active:
        raise AssertionError("random continuation ended with zero live pipes")
    return next_pid


def validate(commands: list[int], declared_operations: int) -> dict:
    if not 1 <= declared_operations <= MAX_COMMANDS:
        raise ValueError("operation count outside official limit")
    if len(commands) != declared_operations:
        raise ValueError("header command count mismatch")
    active: dict[int, int] = {}
    next_pid = 1
    max_live_volume = 0
    max_active_count = 0
    for index, command in enumerate(commands, start=1):
        if command > 0:
            if command > MAX_PIPE_LENGTH:
                raise ValueError(f"invalid length {command} at command {index}")
            if next_pid > MAX_PID:
                raise ValueError("PID ceiling exceeded")
            active[next_pid] = command
            next_pid += 1
        else:
            pid = -command
            if pid not in active:
                raise ValueError(f"deletion at command {index} uses inactive PID {pid}")
            del active[pid]
        live_volume = sum(active.values())
        max_live_volume = max(max_live_volume, live_volume)
        max_active_count = max(max_active_count, len(active))
    final_volume = sum(active.values())
    if final_volume <= 0:
        raise ValueError("final live volume must be positive")
    if max_live_volume > 100_000_000:
        raise ValueError("live volume exceeds the trench limit")
    return {
        "final_live_pipes": len(active),
        "max_live_pipes": max_active_count,
        "max_live_volume": max_live_volume,
        "final_live_volume": final_volume,
        "highest_assigned_pid": next_pid - 1,
    }


def render_input(commands: list[int]) -> bytes:
    return (f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n").encode("ascii")


def main() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(MASTER_SEED)

    # Confirm the task's shared prefix against both named public sources. Only
    # three commands per source are read; no full source input is loaded.
    prefix11, following11 = read_public_prefix(11, 2)
    prefix15, following15 = read_public_prefix(15, 2)
    if prefix11 != [3, 2] or prefix15 != [3, 2] or following11 != -2 or following15 != -2:
        raise ValueError("the named public sources no longer share the expected [3,2] prefix")

    specs: list[tuple[str, str, str]] = []
    for divergence in ("delete_pid1", "retain_pid1_pid2"):
        for pin_mode in ("80_percent", "forever"):
            specs.extend((divergence, pin_mode, "short") for _ in range(2))
            specs.extend((divergence, pin_mode, "medium") for _ in range(4))
            specs.extend((divergence, pin_mode, "long") for _ in range(2))
    rng.shuffle(specs)

    cases: list[tuple[str, list[int], dict]] = []
    duration_ranges = {
        "short": (80, 256),
        "medium": (1000, 8000),
        "long": (20000, 80000),
    }
    for index, (divergence, pin_mode, duration_class) in enumerate(specs, start=1):
        operations = rng.randint(*duration_ranges[duration_class])
        name = f"trap_{index:02d}"
        commands, metadata = make_directed(
            rng, name, operations, divergence, pin_mode, duration_class
        )
        cases.append((name, commands, metadata))

    # Ensure every requested public cut appears; cuts 3, 7, 8, 14 are the
    # short group, while 17 and all later cuts are medium/long.
    other_specs = [
        ("short", cut) for cut in (3, 7, 8, 14)
    ] + [
        ("medium", cut) for cut in (17, 194, 388, 410, 1000, 3, 14, 194)
    ] + [
        ("long", cut) for cut in (7, 8, 402, 410)
    ]
    rng.shuffle(other_specs)
    for index, (duration_class, cut) in enumerate(other_specs, start=1):
        source_case = rng.choice(PUBLIC_CASES)
        prefix, next_public = read_public_prefix(source_case, cut)
        active, next_pid = replay_prefix(prefix)
        commands = list(prefix)
        operations = rng.randint(*duration_ranges[duration_class])
        # All requested cuts are below the chosen short floor, and medium / long
        # streams are longer than their source prefix.
        if operations <= cut:
            operations = cut + 64
        case_rng = random.Random(rng.getrandbits(64))
        next_pid = random_continuation(
            case_rng, commands, active, next_pid, operations, avoid_first_command=next_public
        )
        name = f"public_{index:02d}"
        metadata = {
            "name": name,
            "family": "new_seeded_public_prefix_branch",
            "duration_class": duration_class,
            "public_prefix": {"source_case": source_case, "commands": cut},
            "first_divergence": cut + 1,
            "operations": operations,
        }
        cases.append((name, commands, metadata))

    for index in range(1, 17):
        duration_class = ("short", "medium", "long")[(index - 1) % 3]
        # Required neutral split: 4 short, 8 medium, 4 long.
        if index <= 4:
            duration_class = "short"
        elif index <= 12:
            duration_class = "medium"
        else:
            duration_class = "long"
        operations = rng.randint(*duration_ranges[duration_class])
        case_rng = random.Random(rng.getrandbits(64))
        commands: list[int] = []
        active: dict[int, int] = {}
        random_continuation(case_rng, commands, active, 1, operations)
        name = f"neutral_{index:02d}"
        metadata = {
            "name": name,
            "family": "neutral_seeded_stream",
            "duration_class": duration_class,
            "public_prefix": None,
            "first_divergence": None,
            "operations": operations,
        }
        cases.append((name, commands, metadata))

    if len(cases) != 64:
        raise AssertionError(f"expected 64 cases, generated {len(cases)}")

    manifest_cases = []
    for index, (name, commands, metadata) in enumerate(cases, start=1):
        stats = validate(commands, len(commands))
        filename = f"{index:03d}_{name}.in"
        payload = render_input(commands)
        (OUT / filename).write_bytes(payload)
        manifest_cases.append({
            **metadata,
            "filename": filename,
            "sha256": sha256_bytes(payload),
            "static_validity": "valid_pid_lengths_1_to_40_positive_final_load",
            "highest_assigned_pid": stats["highest_assigned_pid"],
        })

    manifest = {
        "schema": "pipes-presync-fresh-suite-v1",
        "master_seed": MASTER_SEED,
        "generator": "evaluation/generate_fresh.py",
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "provenance": {
            "public_inputs": "data/pipes/open/{8,11,13,15}.in",
            "selected_prefix_and_next_command_sha256": PUBLIC_PREFIX_DIGESTS,
            "public_prefixes_used": "only requested prefix commands and one following command to force a new branch",
            "synthetic_continuations": "fresh fixed-seed Python random.Random; no solver output or prior fixed-control inputs",
            "historical_context_consulted": "wiki/research/Prefix-lifetime-repairs.md was read for terminology and task context; its historical metrics were not used to choose test cases or parameters",
        },
        "counts": {
            "total": len(manifest_cases),
            "directed_prefix_3_2": 32,
            "other_public_prefixes": 16,
            "neutral": 16,
            "short": sum(case["duration_class"] == "short" for case in manifest_cases),
            "medium": sum(case["duration_class"] == "medium" for case in manifest_cases),
            "long": sum(case["duration_class"] == "long" for case in manifest_cases),
        },
        "duration_ranges": duration_ranges,
        "constraints": {
            "pipe_lengths": [1, 40],
            "monotone_unique_pids": [1, MAX_PID],
            "max_commands": MAX_COMMANDS,
            "positive_final_load": True,
            "solver_runs": 0,
        },
        "cases": manifest_cases,
    }
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "output": str(OUT),
        "cases": len(manifest_cases),
        "counts": manifest["counts"],
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "generator_sha256": manifest["generator_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
