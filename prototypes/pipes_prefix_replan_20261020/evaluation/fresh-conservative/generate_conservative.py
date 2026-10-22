#!/usr/bin/env python3
"""Create an independent, public-input-only set for one-step temporary pipes.

Only Open15 command streams are read. Each generated stream starts with an
exact public prefix, then places and removes a new pipe on consecutive commands
before continuing into a seeded deletion/refill or regime-shift rollout.
No solver or previous evaluation dataset is consulted.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MAX_OPS = 200_000
SEED_BASE = 202610207319

# Prefix choices and strata were fixed before generating or evaluating streams.
# The first nine are the requested short cut lengths; the remaining entries add
# other short and longer prefixes from public Open15 files.
SPECS = [
    (3, 2, "delete_refill", 2600),
    (5, 14, "keep_early", 3000),
    (8, 17, "phase_shift", 6200),
    (9, 67, "long_rollout", 14000),
    (11, 109, "delete_refill", 3200),
    (12, 233, "keep_early", 3600),
    (13, 255, "phase_shift", 7400),
    (14, 303, "long_rollout", 18000),
    (15, 352, "delete_refill", 4000),
    (2, 5, "keep_early", 4200),
    (7, 47, "phase_shift", 8800),
    (10, 31, "long_rollout", 22000),
    (8, 89, "delete_refill", 4400),
    (9, 151, "keep_early", 4800),
    (11, 287, "phase_shift", 9600),
    (12, 401, "long_rollout", 26000),
    (5, 601, "delete_refill", 5200),
    (8, 1009, "keep_early", 5600),
    (9, 2003, "phase_shift", 10400),
    (10, 3011, "long_rollout", 30000),
    (13, 5003, "delete_refill", 6000),
    (14, 8003, "keep_early", 7200),
    (15, 12007, "phase_shift", 12000),
    (15, 20003, "long_rollout", 36000),
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_public(case: int) -> tuple[float, list[int], bytes]:
    path = ROOT / "data" / "pipes" / "open" / f"{case}.in"
    raw = path.read_bytes()
    parts = raw.decode("ascii").split()
    assert len(parts) >= 2
    weight, declared = float(parts[0]), int(parts[1])
    commands = [int(value) for value in parts[2:2 + declared]]
    trailing = parts[2 + declared:]
    assert weight > 0 and 0 < declared <= MAX_OPS and len(commands) == declared
    assert not trailing or trailing == ["0"]
    return weight, commands, raw


class InputBuilder:
    def __init__(self, prefix: list[int]):
        self.commands = list(prefix)
        self.active: dict[int, int] = {}
        self.next_pid = 0
        self.live_volume = 0
        self.peak_volume = 0
        self.temp_pairs = 0
        for index, command in enumerate(prefix):
            if command > 0:
                assert 1 <= command <= 40
                self.next_pid += 1
                self.active[self.next_pid] = command
                self.live_volume += command
                self.peak_volume = max(self.peak_volume, self.live_volume)
            else:
                pid = -command
                assert pid in self.active, (index, pid)
                self.live_volume -= self.active.pop(pid)
        assert self.active and self.live_volume > 0
        self.prefix_last_pid = self.next_pid
        self.prefix_alive_pids = tuple(self.active)

    def place(self, length: int) -> int:
        assert 1 <= length <= 40
        self.next_pid += 1
        self.active[self.next_pid] = length
        self.commands.append(length)
        self.live_volume += length
        self.peak_volume = max(self.peak_volume, self.live_volume)
        return self.next_pid

    def remove(self, pid: int) -> int:
        assert pid in self.active and len(self.active) > 1
        length = self.active.pop(pid)
        self.commands.append(-pid)
        self.live_volume -= length
        return length

    def temporary_pair(self, length: int) -> tuple[int, int]:
        pid = self.place(length)
        self.remove(pid)
        self.temp_pairs += 1
        assert self.commands[-2:] == [length, -pid]
        return length, pid


def rank_pid(builder: InputBuilder, policy: str, rng: random.Random,
             protected: set[int] | None = None) -> int:
    choices = [pid for pid in builder.active if protected is None or pid not in protected]
    assert choices
    if policy == "oldest":
        return min(choices)
    if policy == "youngest":
        return max(choices)
    if policy == "shortest":
        return min(choices, key=lambda pid: (builder.active[pid], pid))
    if policy == "longest":
        return max(choices, key=lambda pid: (builder.active[pid], -pid))
    if policy == "middle":
        choices.sort()
        return choices[len(choices) // 2]
    if policy == "random":
        return rng.choice(choices)
    raise ValueError(policy)


def size(profile: str, rng: random.Random, walk: list[int]) -> int:
    if profile == "short":
        return rng.randint(1, 8)
    if profile == "long":
        return rng.randint(25, 40)
    if profile == "bimodal":
        return rng.choice((1, 2, 3, 4, 37, 38, 39, 40))
    if profile == "walk":
        walk[0] = max(1, min(40, walk[0] + rng.choice((-4, -2, -1, 0, 1, 2, 4))))
        return walk[0]
    if profile == "mixed":
        return rng.choice((1, 3, 7, 12, 19, 27, 34, 40))
    if profile == "uniform":
        return rng.randint(1, 40)
    raise ValueError(profile)


def initial_short_lived_divergence(builder: InputBuilder, rng: random.Random,
                                   open_next: int) -> dict[str, int]:
    length = rng.randint(1, 40)
    if open_next > 0:
        while length == open_next:
            length = rng.randint(1, 40)
    pair = builder.temporary_pair(length)
    assert pair[0] != open_next
    return {"pipe_length": pair[0], "pid": pair[1]}


def delete_refill(builder: InputBuilder, rng: random.Random, steps: int) -> None:
    policies = ("oldest", "longest", "youngest", "shortest", "middle", "random")
    profiles = ("short", "long", "bimodal", "mixed", "uniform")
    walk = [rng.randint(8, 32)]
    # A seeded prefix-pipe drain changes the active lifetime/size ranks first.
    target = max(1, len(builder.active) // 2)
    while len(builder.active) > target:
        builder.remove(rank_pid(builder, policies[rng.randrange(len(policies))], rng))
    for cycle in range(8):
        batch = max(12, steps // 48)
        for index in range(batch):
            builder.place(size(profiles[(cycle + index // 7) % len(profiles)], rng, walk))
        keep = max(1, len(builder.active) // (2 + cycle % 2))
        while len(builder.active) > keep:
            builder.remove(rank_pid(builder, policies[cycle % len(policies)], rng))
        # Repeated short-lived allocations probe the immediate-delete boundary.
        for _ in range(2 + cycle % 3):
            builder.temporary_pair(size(profiles[(cycle + 2) % len(profiles)], rng, walk))


def keep_early(builder: InputBuilder, rng: random.Random, steps: int) -> None:
    early = sorted(builder.prefix_alive_pids)
    protected = set(early[:max(1, min(8, len(early)))])
    # Remove only non-protected prefix pipes during the initial cleanup.
    for pid in sorted(tuple(builder.active), reverse=True):
        if pid not in protected and pid in builder.active and len(builder.active) > len(protected):
            builder.remove(pid)

    profiles = ("short", "long", "mixed", "bimodal")
    policies = ("youngest", "longest", "middle", "random")
    walk = [rng.randint(1, 40)]
    upper = max(80, len(protected) + 140)
    for step in range(steps):
        if step % 137 == 0:
            builder.temporary_pair(size(profiles[(step // 137) % len(profiles)], rng, walk))
            continue
        mutable = [pid for pid in builder.active if pid not in protected]
        add = len(builder.active) <= len(protected) + 12 or len(builder.active) >= upper
        if not add:
            add = rng.random() < .53
        if add:
            builder.place(size(profiles[(step // max(1, steps // 4)) % len(profiles)], rng, walk))
        elif mutable:
            builder.remove(rank_pid(builder, policies[(step // max(1, steps // 4)) % len(policies)], rng, protected))
        else:
            builder.place(size("mixed", rng, walk))


def phase_shift(builder: InputBuilder, rng: random.Random, steps: int) -> None:
    profiles = ("short", "long", "bimodal", "walk", "uniform", "mixed")
    policies = ("oldest", "youngest", "longest", "middle", "shortest", "random")
    add_rates = (.57, .47, .54, .49, .52, .48)
    walk = [rng.randint(4, 36)]
    floor, cap = 24, 360
    phase_len = max(1, steps // len(profiles))
    for step in range(steps):
        phase = min(len(profiles) - 1, step // phase_len)
        if step % 173 == 0:
            builder.temporary_pair(size(profiles[phase], rng, walk))
            continue
        if len(builder.active) <= floor:
            add = True
        elif len(builder.active) >= cap:
            add = False
        else:
            add = rng.random() < add_rates[phase]
        if add:
            builder.place(size(profiles[phase], rng, walk))
        else:
            builder.remove(rank_pid(builder, policies[phase], rng))


def long_rollout(builder: InputBuilder, rng: random.Random, steps: int) -> None:
    profiles = ("uniform", "short", "long", "walk", "bimodal", "mixed")
    policies = ("random", "oldest", "youngest", "longest", "middle", "shortest")
    add_rates = (.51, .55, .46, .53, .48, .52)
    walk = [rng.randint(1, 40)]
    low, high = 48, 1200
    phase_len = max(1, steps // len(profiles))
    for step in range(steps):
        phase = min(len(profiles) - 1, step // phase_len)
        if step % 251 == 0:
            builder.temporary_pair(size(profiles[phase], rng, walk))
            continue
        if len(builder.active) <= low:
            add = True
        elif len(builder.active) >= high:
            add = False
        else:
            add = rng.random() < add_rates[phase]
        if add:
            builder.place(size(profiles[phase], rng, walk))
        else:
            builder.remove(rank_pid(builder, policies[phase], rng))


GENERATORS = {
    "delete_refill": delete_refill,
    "keep_early": keep_early,
    "phase_shift": phase_shift,
    "long_rollout": long_rollout,
}


def validate(path: Path, prefix: list[int], source: list[int], cut: int,
             first_pair: dict[str, int]) -> dict[str, int | float]:
    tokens = path.read_text(encoding="ascii").split()
    assert len(tokens) >= 2 and float(tokens[0]) == 1.0
    n = int(tokens[1])
    commands = [int(value) for value in tokens[2:]]
    assert 1 <= n <= MAX_OPS and len(commands) == n
    assert commands[:cut] == prefix
    assert commands[cut:cut + 2] == [first_pair["pipe_length"], -first_pair["pid"]]
    assert commands[cut] != source[cut]

    active: dict[int, int] = {}
    next_pid = live = peak = peak_count = 0
    for index, command in enumerate(commands):
        if command > 0:
            assert 1 <= command <= 40, (path.name, index, command)
            next_pid += 1
            active[next_pid] = command
            live += command
        else:
            pid = -command
            assert pid > 0 and pid in active, (path.name, index, pid)
            live -= active.pop(pid)
        assert live > 0, (path.name, index)
        peak = max(peak, live)
        peak_count = max(peak_count, len(active))
    final_volume = sum(active.values())
    lower_bound = ((peak + 19) // 20) * 20
    volume_ceiling = final_volume / lower_bound
    assert final_volume > 0 and volume_ceiling >= .95, (path.name, volume_ceiling)
    return {
        "operation_count": n,
        "placement_count": next_pid,
        "deletion_count": n - next_pid,
        "peak_live_pipe_count": peak_count,
        "peak_live_length_m": peak,
        "final_occupied_length_m": final_volume,
        "input_side_volume_ceiling": volume_ceiling,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    all_hashes: set[str] = set()

    for index, (case, cut, family, steps) in enumerate(SPECS):
        weight, public, source_bytes = read_public(case)
        assert 1 <= cut < len(public)
        seed = SEED_BASE + 997 * index
        rng = random.Random(seed)
        prefix = public[:cut]
        builder = InputBuilder(prefix)
        first_pair = initial_short_lived_divergence(builder, rng, public[cut])
        protected_at_prefix = builder.prefix_alive_pids
        GENERATORS[family](builder, rng, steps)

        # End at the peak live volume already reached, avoiding a stream whose
        # input alone forces a low score through an empty final live set.
        missing = builder.peak_volume - builder.live_volume
        while missing > 0:
            length = min(40, missing)
            builder.place(length)
            missing -= length

        assert len(builder.commands) <= MAX_OPS
        identifier = f"C{index + 1:02d}"
        path = OUT / f"{identifier}.in"
        body = "1.0\n" + str(len(builder.commands)) + "\n" + "\n".join(map(str, builder.commands)) + "\n"
        path.write_text(body, encoding="ascii")
        stream_sha = digest(path.read_bytes())
        assert stream_sha not in all_hashes
        all_hashes.add(stream_sha)
        structural = validate(path, prefix, public, cut, first_pair)
        prefix_bytes = ("\n".join(map(str, prefix)) + "\n").encode("ascii")
        rows.append({
            "id": identifier,
            "file": path.name,
            "sha256": stream_sha,
            "seed": seed,
            "source_open_case": case,
            "source_path": f"data/pipes/open/{case}.in",
            "source_sha256": digest(source_bytes),
            "source_weight": weight,
            "shared_prefix_commands": cut,
            "shared_prefix_sha256": digest(prefix_bytes),
            "family": family,
            "rollout_steps_before_final_refill": steps,
            "first_post_prefix_temporary_pipe": first_pair,
            "first_post_prefix_operation_differs_from_open": True,
            "temporary_pair_count": builder.temp_pairs,
            "prefix_alive_pids_protected_in_keep_early_family": list(protected_at_prefix) if family == "keep_early" else [],
            "structural_validation": structural,
        })

    manifest = {
        "dataset": "pipes-prefix-replan-fresh-conservative-20261020",
        "status": "sealed-for-one-use-after-candidate-freeze",
        "scope": "Independent public-prefix evaluation of immediate-delete temporary placements and subsequent rollouts. Known mechanisms with new seeds; not an unseen-distribution claim.",
        "test_count": len(rows),
        "generation": {
            "generator": "generate_conservative.py",
            "generator_sha256": digest((OUT / "generate_conservative.py").read_bytes()),
            "preselected_seed_base": SEED_BASE,
            "per_test_seed_rule": "seed = preselected_seed_base + 997 * zero_based_test_index",
            "only_input_sources": "data/pipes/open/{2,3,5,7,8,9,10,11,12,13,14,15}.in",
            "candidate_solver_or_metrics_read": False,
            "previous_evaluation_set_read": False,
            "candidate_invocations": 0,
            "max_operations": MAX_OPS,
            "pipe_length_range": [1, 40],
            "lifetime_one_trigger": "Every stream begins after its exact Open15 prefix with +L followed immediately by deletion of that new PID; later temporary pairs are also adjacent.",
            "score_guard": "Each stream finishes at its peak live volume; the input-side volume ceiling is checked to be at least 0.95. This is not a solver KPI guarantee.",
        },
        "families": ["delete_refill", "keep_early", "phase_shift", "long_rollout"],
        "tests": rows,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "test_count": len(rows),
        "manifest": (OUT / "manifest.json").relative_to(ROOT).as_posix(),
        "structurally_valid": True,
        "candidate_invocations": 0,
    }))


if __name__ == "__main__":
    main()
