#!/usr/bin/env python3
"""Build a sealed, fixed-seed set of directed Pipes continuation streams.

The generator reads only data/pipes/open/{case}.in. It never reads a solver,
candidate output, prior fresh suite, or placement coordinates.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OPEN = ROOT / "data" / "pipes" / "open"
SEED = 202610201943
MAX_COMMANDS = 200_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_open(case: int) -> tuple[int, list[int], str]:
    path = OPEN / f"{case}.in"
    raw = path.read_bytes()
    tokens = raw.decode("ascii").split()
    if len(tokens) < 2:
        raise ValueError(f"bad public input header: {path}")
    count = int(tokens[1])
    commands = list(map(int, tokens[2 : 2 + count]))
    if len(commands) != count:
        raise ValueError(f"truncated public input: {path}")
    return count, commands, sha256(raw)


def apply_command(command: int, pid: int, active: dict[int, int]) -> int:
    if command > 0:
        pid += 1
        active[pid] = command
    else:
        target = -command
        if target not in active:
            raise ValueError(f"invalid deletion {command}")
        del active[target]
    return pid


def replay_prefix(commands: list[int]) -> tuple[int, dict[int, int]]:
    pid = 0
    active: dict[int, int] = {}
    for command in commands:
        pid = apply_command(command, pid, active)
    return pid, active


def pick_length(rng: random.Random, profile: str, tick: int) -> int:
    if profile == "large":
        return rng.choice((40, 40, 39, 38, 37, 36, 32, 29))
    if profile == "small":
        return rng.choice((1, 1, 2, 3, 4, 5, 6, 8, 10))
    if profile == "edge-mix":
        return (1, 39, 40, 2, 38, 3, 37, 4, 36, 20)[tick % 10]
    if profile == "uniform":
        return rng.randint(1, 40)
    raise ValueError(profile)


PHASE_ORDERS = (
    ("dense-large", "sparse-small", "dense-mixed", "sparse-large"),
    ("sparse-small", "dense-large", "sparse-mixed", "dense-edge"),
    ("dense-mixed", "sparse-large", "dense-small", "sparse-edge"),
    ("dense-edge", "sparse-mixed", "dense-large", "sparse-small"),
)


def phase_config(name: str, step: int) -> tuple[float, str]:
    if name == "dense-large":
        return 0.74, "large"
    if name == "dense-small":
        return 0.70, "small"
    if name == "dense-edge":
        return 0.68, "edge-mix"
    if name == "dense-mixed":
        return 0.69, "uniform"
    if name == "sparse-small":
        return 0.39, "small"
    if name == "sparse-large":
        return 0.43, "large"
    if name == "sparse-edge":
        return (0.78 if (step // 96) % 2 == 0 else 0.34), "edge-mix"
    if name == "sparse-mixed":
        return (0.72 if (step // 128) % 2 == 0 else 0.42), "uniform"
    raise ValueError(name)


class ActiveIndex:
    """Dynamic PID rank and length index for linearithmic tail generation."""

    def __init__(self, initial: dict[int, int], capacity: int = MAX_COMMANDS + 1):
        self.capacity = capacity
        self.tree = [0] * (capacity + 1)
        self.active: dict[int, int] = {}
        self.min_heap: list[tuple[int, int]] = []
        self.max_heap: list[tuple[int, int]] = []
        for pid, length in initial.items():
            self.add(pid, length)

    def _update(self, pid: int, delta: int) -> None:
        i = pid
        while i <= self.capacity:
            self.tree[i] += delta
            i += i & -i

    def add(self, pid: int, length: int) -> None:
        import heapq

        self.active[pid] = length
        self._update(pid, 1)
        heapq.heappush(self.min_heap, (length, pid))
        heapq.heappush(self.max_heap, (-length, pid))

    def remove(self, pid: int) -> None:
        if pid not in self.active:
            raise ValueError(f"inactive indexed PID {pid}")
        del self.active[pid]
        self._update(pid, -1)

    def kth(self, k: int) -> int:
        if k < 1 or k > len(self.active):
            raise ValueError(f"rank outside active range: {k}")
        idx = 0
        bit = 1 << (self.capacity.bit_length() - 1)
        while bit:
            nxt = idx + bit
            if nxt <= self.capacity and self.tree[nxt] < k:
                idx = nxt
                k -= self.tree[nxt]
            bit >>= 1
        return idx + 1

    def choose(self, rng: random.Random, rank_kind: str) -> int:
        import heapq

        count = len(self.active)
        if count == 0:
            raise ValueError("no active PID to delete")
        if rank_kind == "oldest":
            return self.kth(1)
        if rank_kind == "newest":
            return self.kth(count)
        if rank_kind == "middle":
            return self.kth((count + 1) // 2)
        if rank_kind == "random-rank":
            return self.kth(rng.randrange(1, count + 1))
        if rank_kind == "shortest":
            while self.min_heap[0][1] not in self.active:
                heapq.heappop(self.min_heap)
            return self.min_heap[0][1]
        if rank_kind == "longest":
            while self.max_heap[0][1] not in self.active:
                heapq.heappop(self.max_heap)
            return self.max_heap[0][1]
        raise ValueError(rank_kind)


def build_tail(
    prefix: list[int],
    target_count: int,
    rng: random.Random,
    profile_id: int,
    rank_rotation: int,
) -> tuple[list[int], dict[str, object]]:
    pid, active = replay_prefix(prefix)
    if target_count <= len(prefix) or target_count > MAX_COMMANDS:
        raise ValueError("invalid target command count")

    guards = set(active)
    all_index = ActiveIndex(active)
    tail_index = ActiveIndex({})
    tail: list[int] = []
    rank_order = list(("oldest", "newest", "shortest", "longest", "middle", "random-rank"))
    rng.shuffle(rank_order)
    rank_order = rank_order[rank_rotation % len(rank_order) :] + rank_order[: rank_rotation % len(rank_order)]
    delete_number = 0
    phase_order = PHASE_ORDERS[profile_id % len(PHASE_ORDERS)]
    remaining = target_count - len(prefix)

    for step in range(remaining):
        phase = min(3, (4 * step) // max(1, remaining))
        add_probability, length_profile = phase_config(phase_order[phase], step)
        allow_guard = step >= int(remaining * 0.82)
        want_add = rng.random() < add_probability
        last_command = step == remaining - 1
        if want_add or last_command:
            length = pick_length(rng, length_profile, step)
            pid += 1
            all_index.add(pid, length)
            tail_index.add(pid, length)
            tail.append(length)
            continue

        delete_index = all_index if allow_guard else tail_index
        if not delete_index.active:
            length = pick_length(rng, length_profile, step)
            pid += 1
            all_index.add(pid, length)
            tail_index.add(pid, length)
            tail.append(length)
        else:
            rank_kind = rank_order[delete_number % len(rank_order)]
            target_pid = delete_index.choose(rng, rank_kind)
            all_index.remove(target_pid)
            if target_pid not in guards:
                tail_index.remove(target_pid)
            tail.append(-target_pid)
            delete_number += 1

    if not all_index.active:
        raise AssertionError("forced final placement did not preserve positive load")
    metadata = {
        "target_commands": target_count,
        "phase_order": list(phase_order),
        "delete_rank_permutation": rank_order,
        "guard_release_after_tail_fraction": 0.82,
        "final_active_count": len(all_index.active),
    }
    return tail, metadata


def write_stream(name: str, commands: list[int]) -> str:
    if not commands or len(commands) > MAX_COMMANDS:
        raise ValueError(f"invalid operation count for {name}")
    # Check PID validity and positive final occupancy without invoking a solver.
    pid, active = replay_prefix(commands)
    if pid < 1 or not active:
        raise ValueError(f"non-positive final occupancy for {name}")
    body = "1 {}\n{}\n".format(len(commands), "\n".join(map(str, commands))).encode("ascii")
    path = OUT / f"{name}.in"
    path.write_bytes(body)
    return sha256(body)


TARGETED = [
    # The two short case-11 branches are deliberately fully synthetic after
    # the shared public prefix 3,2; they are independent of solver coordinates.
    {"name": "d08-e002", "base": 8, "prefix": 2, "class": "short", "target": 8000, "profile": 0},
    {"name": "d08-m194", "base": 8, "prefix": 194, "class": "short", "target": 10000, "profile": 1},
    {"name": "d08-m402", "base": 8, "prefix": 402, "class": "short", "target": 12000, "profile": 2},
    {"name": "d08-l1000", "base": 8, "prefix": 1000, "class": "long", "target": 50000, "profile": 3},
    {"name": "d08-l2500", "base": 8, "prefix": 2500, "class": "long", "target": 80000, "profile": 0},
    {"name": "d08-l6000", "base": 8, "prefix": 6000, "class": "long", "target": 120000, "profile": 1},

    {"name": "d11-cap-pid1", "base": 11, "prefix": 2, "class": "short", "special": "delete-pid1", "profile": 0},
    {"name": "d11-cap-pid2", "base": 11, "prefix": 2, "class": "short", "special": "delete-pid2", "profile": 1},
    {"name": "d11-m388", "base": 11, "prefix": 388, "class": "short", "target": 12000, "profile": 2},
    {"name": "d11-l2003", "base": 11, "prefix": 2003, "class": "long", "target": 50000, "profile": 3},
    {"name": "d11-l5000", "base": 11, "prefix": 5000, "class": "long", "target": 80000, "profile": 0},
    {"name": "d11-l9000", "base": 11, "prefix": 9000, "class": "long", "target": 120000, "profile": 1},

    {"name": "d13-e003", "base": 13, "prefix": 3, "class": "short", "target": 8000, "profile": 2},
    {"name": "d13-e007", "base": 13, "prefix": 7, "class": "short", "target": 10000, "profile": 3},
    {"name": "d13-m410", "base": 13, "prefix": 410, "class": "short", "target": 12000, "profile": 0},
    {"name": "d13-l1000", "base": 13, "prefix": 1000, "class": "long", "target": 50000, "profile": 1},
    {"name": "d13-l2003", "base": 13, "prefix": 2003, "class": "long", "target": 80000, "profile": 2},
    {"name": "d13-l9000", "base": 13, "prefix": 9000, "class": "long", "target": 120000, "profile": 3},

    {"name": "d15-e008", "base": 15, "prefix": 8, "class": "short", "target": 8000, "profile": 1},
    {"name": "d15-e014", "base": 15, "prefix": 14, "class": "short", "target": 10000, "profile": 2},
    {"name": "d15-m194", "base": 15, "prefix": 194, "class": "short", "target": 12000, "profile": 3},
    {"name": "d15-l2003", "base": 15, "prefix": 2003, "class": "long", "target": 50000, "profile": 0},
    {"name": "d15-l50000", "base": 15, "prefix": 50000, "class": "long", "target": 100000, "profile": 1},
    {"name": "d15-l150000", "base": 15, "prefix": 150000, "class": "long", "target": 199900, "profile": 2},
]


NEUTRAL = [
    {"name": "n02-e002", "base": 2, "prefix": 2, "class": "short", "target": 6000, "profile": 3},
    {"name": "n02-e007", "base": 2, "prefix": 7, "class": "short", "target": 8000, "profile": 0},
    {"name": "n02-l014", "base": 2, "prefix": 14, "class": "long", "target": 50000, "profile": 1},
    {"name": "n03-e002", "base": 3, "prefix": 2, "class": "short", "target": 6000, "profile": 2},
    {"name": "n03-l003", "base": 3, "prefix": 3, "class": "long", "target": 50000, "profile": 3},
    {"name": "n03-l007", "base": 3, "prefix": 7, "class": "long", "target": 80000, "profile": 0},
    {"name": "n05-m194", "base": 5, "prefix": 194, "class": "short", "target": 8000, "profile": 1},
    {"name": "n05-m1000", "base": 5, "prefix": 1000, "class": "short", "target": 10000, "profile": 2},
    {"name": "n05-l7000", "base": 5, "prefix": 7000, "class": "long", "target": 50000, "profile": 3},
    {"name": "n07-e002", "base": 7, "prefix": 2, "class": "short", "target": 6000, "profile": 0},
    {"name": "n07-m194", "base": 7, "prefix": 194, "class": "long", "target": 50000, "profile": 1},
    {"name": "n07-m300", "base": 7, "prefix": 300, "class": "long", "target": 80000, "profile": 2},
    {"name": "n09-m388", "base": 9, "prefix": 388, "class": "short", "target": 8000, "profile": 3},
    {"name": "n09-m1000", "base": 9, "prefix": 1000, "class": "short", "target": 10000, "profile": 0},
    {"name": "n09-l8000", "base": 9, "prefix": 8000, "class": "long", "target": 50000, "profile": 1},
    {"name": "n10-m410", "base": 10, "prefix": 410, "class": "short", "target": 8000, "profile": 2},
    {"name": "n10-l2003", "base": 10, "prefix": 2003, "class": "long", "target": 50000, "profile": 3},
    {"name": "n10-l9000", "base": 10, "prefix": 9000, "class": "long", "target": 80000, "profile": 0},
    {"name": "n12-m194", "base": 12, "prefix": 194, "class": "short", "target": 6000, "profile": 1},
    {"name": "n12-m1000", "base": 12, "prefix": 1000, "class": "short", "target": 8000, "profile": 2},
    {"name": "n12-l1400", "base": 12, "prefix": 1400, "class": "long", "target": 50000, "profile": 3},
    {"name": "n14-e014", "base": 14, "prefix": 14, "class": "short", "target": 6000, "profile": 0},
    {"name": "n14-m2003", "base": 14, "prefix": 2003, "class": "long", "target": 50000, "profile": 1},
    {"name": "n14-l20000", "base": 14, "prefix": 20000, "class": "long", "target": 80000, "profile": 2},
]


def make_special(row: dict[str, object], prefix: list[int]) -> tuple[list[int], dict[str, object]]:
    if prefix != [3, 2]:
        raise ValueError("capacity probes require the exact public prefix 3,2")
    if row["special"] == "delete-pid1":
        suffix = [-1, 40, 40, 40, 40, 40, 29, 9]
    elif row["special"] == "delete-pid2":
        suffix = [-2, 40, 39, 39, 40, 40, 30, 9]
    else:
        raise ValueError(row["special"])
    commands = prefix + suffix
    _, active = replay_prefix(commands)
    if sum(active.values()) != 240:
        raise AssertionError("capacity branch must end at a 20-aligned live volume")
    return commands, {"mechanism_tag": "small-synthetic-exact-capacity", "target_live_volume_m": 240}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.glob("*.in")):
        raise SystemExit("refusing to overwrite an existing fresh suite")

    source_cache: dict[int, tuple[int, list[int], str]] = {
        case: load_open(case) for case in sorted({int(row["base"]) for row in TARGETED + NEUTRAL})
    }
    rows = TARGETED + NEUTRAL
    manifest_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        case = int(row["base"])
        source_count, public_commands, source_hash = source_cache[case]
        prefix_len = int(row["prefix"])
        if prefix_len < 1 or prefix_len > source_count:
            raise ValueError(f"prefix outside public case {case}: {prefix_len}")
        prefix = public_commands[:prefix_len]
        stream_seed = SEED + (index + 1) * 1_000_003
        rng = random.Random(stream_seed)

        if "special" in row:
            commands, metadata = make_special(row, prefix)
        else:
            tail, metadata = build_tail(
                prefix,
                int(row["target"]),
                rng,
                int(row["profile"]),
                index,
            )
            commands = prefix + tail

        input_hash = write_stream(str(row["name"]), commands)
        manifest_rows.append(
            {
                "id": row["name"],
                "group": "directed" if row in TARGETED else "neutral",
                "short_or_long": row["class"],
                "public_case": case,
                "public_prefix_commands": prefix_len,
                "public_input_sha256": source_hash,
                "operation_count": len(commands),
                "input_file": f"{row['name']}.in",
                "input_sha256": input_hash,
                "stream_seed": stream_seed,
                "metadata": metadata,
            }
        )

    counts = {
        "total": len(manifest_rows),
        "short": sum(row["short_or_long"] == "short" for row in manifest_rows),
        "long": sum(row["short_or_long"] == "long" for row in manifest_rows),
        "directed": sum(row["group"] == "directed" for row in manifest_rows),
        "neutral": sum(row["group"] == "neutral" for row in manifest_rows),
    }
    if counts != {"total": 48, "short": 24, "long": 24, "directed": 24, "neutral": 24}:
        raise AssertionError(f"unexpected suite balance: {counts}")

    manifest = {
        "schema": "pipes-directed-fresh-v1",
        "created_date": "2026-10-20",
        "status": "sealed_not_evaluated",
        "seed": SEED,
        "source_scope": "data/pipes/open only",
        "candidate_or_prior_fresh_inputs_read": False,
        "purpose": "one-time paired evaluation after candidate freeze",
        "interpretation": "fresh seeds of known mechanisms; not a hidden-distribution sample",
        "evaluation_rule": "Do not inspect candidate-relative results or tune against these inputs before selecting and freezing one candidate.",
        "counts": counts,
        "streams": manifest_rows,
        "generator_sha256": sha256(Path(__file__).read_bytes()),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (OUT / "manifest.json").write_bytes(manifest_bytes)
    readme = (
        "# Sealed fresh evaluation set\n\n"
        "This directory contains fixed-seed public-prefix continuations for a one-time paired evaluation. "
        "The generator reads only `data/pipes/open/`; it does not read candidates, solver outputs, or prior fresh sets. "
        "Use only after freezing a single candidate. These are fresh seeds of known mechanisms, not samples from the hidden distribution.\n\n"
        "The `.in` files use the local harness format: weight `1`, declared operation count, then commands. "
        "The generator checks PID validity and positive final live volume without running any solver.\n"
    ).encode("utf-8")
    (OUT / "README.md").write_bytes(readme)


if __name__ == "__main__":
    main()
