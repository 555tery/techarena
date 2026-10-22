#!/usr/bin/env python3
"""Generate a sealed set of directed Open15-prefix continuation streams.

The generator reads only data/pipes/open/*.in. It never invokes, imports, or
inspects a candidate solver. Fixed seeds and source-prefix hashes are recorded
in manifest.json so the set can be audited after the solver is frozen.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MAX_OPS = 200_000
CASES = (5, 8, 9, 11, 14, 15)
FAMILIES = (
    "prefix_pipe_rank_drain",
    "small_survivors_repeated_refill",
    "alternating_refill_and_drain",
    "phase_shifted_delete_ranks",
)
CUTS = {
    5: (101, 503, 1003, 2003),
    8: (101, 503, 1201, 2003),
    9: (101, 503, 1201, 2003),
    11: (101, 503, 1201, 2003),
    14: (101, 503, 2003, 8003),
    15: (101, 503, 2003, 8003),
}
BASE_SEED = 202610200000


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_input(case: int) -> tuple[float, list[int], bytes]:
    path = ROOT / "data" / "pipes" / "open" / f"{case}.in"
    raw = path.read_bytes()
    tokens = raw.decode("ascii").split()
    assert len(tokens) >= 2
    weight = float(tokens[0])
    n = int(tokens[1])
    payload = [int(value) for value in tokens[2:]]
    if len(payload) == n + 1:
        assert payload[-1] == 0, "unexpected token after the declared command stream"
        payload.pop()
    commands = payload
    assert weight > 0 and n == len(commands) and 0 < n <= MAX_OPS
    return weight, commands, raw


class Stream:
    def __init__(self, prefix: list[int]):
        self.commands = list(prefix)
        self.active: dict[int, int] = {}
        self.next_pid = 0
        self.live_length = 0
        self.peak_live_length = 0
        for index, command in enumerate(prefix):
            if command > 0:
                assert 1 <= command <= 40
                self.next_pid += 1
                self.active[self.next_pid] = command
                self.live_length += command
                self.peak_live_length = max(self.peak_live_length, self.live_length)
            else:
                pid = -command
                assert pid in self.active, ("invalid Open15 prefix", index, pid)
                self.live_length -= self.active.pop(pid)

    def add(self, length: int) -> int:
        assert 1 <= length <= 40
        self.next_pid += 1
        self.active[self.next_pid] = length
        self.commands.append(length)
        self.live_length += length
        self.peak_live_length = max(self.peak_live_length, self.live_length)
        return self.next_pid

    def delete(self, pid: int) -> int:
        assert pid in self.active and len(self.active) > 1
        length = self.active.pop(pid)
        self.commands.append(-pid)
        self.live_length -= length
        return length


def choose_pid(stream: Stream, policy: str, rng: random.Random) -> int:
    ids = list(stream.active)
    assert ids
    if policy == "oldest":
        return min(ids)
    if policy == "youngest":
        return max(ids)
    if policy == "shortest":
        return min(ids, key=lambda pid: (stream.active[pid], pid))
    if policy == "longest":
        return max(ids, key=lambda pid: (stream.active[pid], -pid))
    if policy == "random":
        return rng.choice(ids)
    if policy == "middle-rank":
        ids.sort()
        return ids[len(ids) // 2]
    if policy == "young-short":
        return min(ids, key=lambda pid: (pid, stream.active[pid]))
    raise ValueError(policy)


def diverge_from_open(stream: Stream, next_open: int, rng: random.Random) -> int:
    """Delete a valid prefix PID with an action distinct from Open15's next op."""
    choices = [pid for pid in stream.active if next_open != -pid]
    assert choices, "selected prefix has no legal alternative delete"
    pid = rng.choice(sorted(choices))
    stream.delete(pid)
    assert stream.commands[-1] != next_open
    return pid


def profile_length(profile: str, rng: random.Random, walk: list[int]) -> int:
    if profile == "small":
        return rng.randint(1, 8)
    if profile == "large":
        return rng.randint(25, 40)
    if profile == "bimodal":
        return rng.choice((1, 2, 3, 4, 37, 38, 39, 40))
    if profile == "walk":
        walk[0] = max(1, min(40, walk[0] + rng.choice((-5, -3, -1, 0, 1, 3, 5))))
        return walk[0]
    if profile == "alternating":
        return rng.choice((1, 2, 4, 8, 19, 33, 38, 40))
    if profile == "uniform":
        return rng.randint(1, 40)
    raise ValueError(profile)


def generate_rank_drain(stream: Stream, rng: random.Random) -> None:
    counts = Counter(stream.active.values())
    mode = max(counts, key=lambda length: (counts[length], length))
    target = max(2, len(stream.active) // 3)
    while len(stream.active) > target:
        ids = list(stream.active)
        pid = min(ids, key=lambda p: (stream.active[p] != mode, p if rng.random() < .5 else -p))
        stream.delete(pid)

    policies = ("young-short", "longest", "oldest", "shortest")
    patterns = ("small", "large", "bimodal", "alternating")
    walk = [20]
    for phase in range(8):
        for step in range(90):
            if step % 3 != 2 or len(stream.active) < target + 3:
                stream.add(profile_length(patterns[phase % len(patterns)], rng, walk))
            elif len(stream.active) > target:
                stream.delete(choose_pid(stream, policies[phase % len(policies)], rng))


def generate_small_survivors(stream: Stream, rng: random.Random) -> None:
    target = min(7, max(2, len(stream.active) // 15))
    while len(stream.active) > target:
        pid = min(stream.active, key=lambda p: (stream.active[p], p))
        stream.delete(pid)

    wave = (1, 2, 3, 4, 7, 37, 38, 39, 40, 20, 21, 19)
    policies = ("youngest", "longest", "oldest", "middle-rank", "shortest")
    for cycle in range(7):
        for offset in range(56):
            length = wave[(offset + 3 * cycle) % len(wave)]
            stream.add(length)
        keep = min(5, max(2, target + (cycle % 2)))
        while len(stream.active) > keep:
            stream.delete(choose_pid(stream, policies[cycle % len(policies)], rng))


def generate_refill_cycles(stream: Stream, rng: random.Random) -> None:
    profiles = ("alternating", "large", "small", "bimodal", "uniform", "walk")
    policies = ("oldest", "youngest", "longest", "shortest", "middle-rank", "random")
    walk = [rng.randint(10, 30)]
    for cycle in range(10):
        batch = 72 + 8 * (cycle % 5)
        profile = profiles[cycle % len(profiles)]
        for _ in range(batch):
            stream.add(profile_length(profile, rng, walk))
        target = max(3, len(stream.active) // (3 + cycle % 2))
        while len(stream.active) > target:
            stream.delete(choose_pid(stream, policies[cycle % len(policies)], rng))
        # A smaller refill after the drain makes rank and size effects interact.
        for _ in range(18 + 4 * (cycle % 3)):
            stream.add(profile_length(profiles[(cycle + 2) % len(profiles)], rng, walk))


def generate_phase_shift(stream: Stream, rng: random.Random) -> None:
    profiles = ("small", "large", "bimodal", "walk", "uniform")
    policies = ("oldest", "youngest", "longest", "middle-rank", "shortest")
    add_probabilities = (.58, .46, .54, .48, .52)
    walk = [rng.randint(1, 40)]
    lower, upper = 32, 240
    for phase in range(len(profiles)):
        for _ in range(900):
            if len(stream.active) <= lower:
                add = True
            elif len(stream.active) >= upper:
                add = False
            else:
                add = rng.random() < add_probabilities[phase]
            if add:
                stream.add(profile_length(profiles[phase], rng, walk))
            else:
                stream.delete(choose_pid(stream, policies[phase], rng))


def refill_to_peak_volume(stream: Stream) -> None:
    """Finish at the largest live volume already reached in this stream."""
    missing = stream.peak_live_length - stream.live_length
    while missing > 0:
        length = min(40, missing)
        stream.add(length)
        missing -= length
    assert stream.live_length == stream.peak_live_length


GENERATORS: tuple[Callable[[Stream, random.Random], None], ...] = (
    generate_rank_drain,
    generate_small_survivors,
    generate_refill_cycles,
    generate_phase_shift,
)


def validate_file(path: Path, expected_prefix: list[int], source_commands: list[int],
                  cut: int, first_changed: int) -> dict[str, int]:
    tokens = path.read_text(encoding="ascii").split()
    assert len(tokens) >= 2 and float(tokens[0]) > 0
    n = int(tokens[1])
    commands = [int(value) for value in tokens[2:]]
    assert len(commands) == n and 1 <= n <= MAX_OPS
    assert commands[:cut] == expected_prefix
    assert commands[cut] == first_changed and first_changed != source_commands[cut]

    active: dict[int, int] = {}
    next_pid = 0
    live_length = peak_length = peak_count = 0
    for index, command in enumerate(commands):
        if command > 0:
            assert 1 <= command <= 40, (path.name, index, command)
            next_pid += 1
            active[next_pid] = command
            live_length += command
        else:
            pid = -command
            assert pid > 0 and pid in active, (path.name, index, pid)
            live_length -= active.pop(pid)
        assert live_length > 0, (path.name, index, "empty live set")
        peak_length = max(peak_length, live_length)
        peak_count = max(peak_count, len(active))
    assert sum(active.values()) > 0
    final_volume = sum(active.values())
    volume_lower_bound = ((peak_length + 19) // 20) * 20
    input_side_score_upper_bound = final_volume / volume_lower_bound
    assert input_side_score_upper_bound >= .95, (path.name, input_side_score_upper_bound)
    return {
        "operation_count": n,
        "placement_count": next_pid,
        "deletion_count": n - next_pid,
        "peak_live_pipe_count": peak_count,
        "peak_live_length_m": peak_length,
        "final_occupied_length_m": final_volume,
        "input_side_score_upper_bound": input_side_score_upper_bound,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    generated_hashes: set[str] = set()

    for case_index, case in enumerate(CASES):
        source_weight, source_commands, source_bytes = open_input(case)
        source_path = ROOT / "data" / "pipes" / "open" / f"{case}.in"
        for family_index, family in enumerate(FAMILIES):
            cut = CUTS[case][family_index]
            assert 1 <= cut < len(source_commands)
            seed = BASE_SEED + case_index * 10_000 + family_index * 101 + case
            rng = random.Random(seed)
            prefix = source_commands[:cut]
            stream = Stream(prefix)
            first_changed = -diverge_from_open(stream, source_commands[cut], rng)
            GENERATORS[family_index](stream, rng)
            refill_to_peak_volume(stream)
            assert len(stream.commands) <= MAX_OPS

            identifier = f"P{case_index + 1:02d}{family_index + 1:02d}"
            path = OUT / f"{identifier}.in"
            body = "1.0\n" + str(len(stream.commands)) + "\n" + "\n".join(map(str, stream.commands)) + "\n"
            path.write_text(body, encoding="ascii")
            test_hash = sha_bytes(path.read_bytes())
            assert test_hash not in generated_hashes
            generated_hashes.add(test_hash)
            structural = validate_file(path, prefix, source_commands, cut, first_changed)
            prefix_bytes = ("\n".join(map(str, prefix)) + "\n").encode("ascii")
            rows.append({
                "id": identifier,
                "file": path.name,
                "sha256": test_hash,
                "source_open_case": case,
                "source_path": source_path.relative_to(ROOT).as_posix(),
                "source_sha256": sha_bytes(source_bytes),
                "source_weight": source_weight,
                "shared_prefix_commands": cut,
                "shared_prefix_sha256": sha_bytes(prefix_bytes),
                "first_post_prefix_command": first_changed,
                "source_next_open_command": source_commands[cut],
                "first_post_prefix_command_is_divergent": first_changed != source_commands[cut],
                "family": family,
                "seed": seed,
                "seed_rule": "BASE_SEED + case_index*10000 + family_index*101 + open_case_number",
                "structural_validation": structural,
            })

    manifest = {
        "dataset": "pipes-open15-directed-prefix-replan-fresh-20261020",
        "status": "sealed-for-one-use-after-candidate-freeze",
        "scope": "New seeds and generated continuations for known trap mechanisms; not an unseen-distribution claim.",
        "test_count": len(rows),
        "generation": {
            "generator": "generate.py",
            "generator_sha256": sha_bytes((OUT / "generate.py").read_bytes()),
            "only_input_sources": "data/pipes/open/{5,8,9,11,14,15}.in",
            "source_data_policy": "Exact public Open15 command prefixes plus seeded synthetic suffixes. No candidate source, binary, output, hidden data, or candidate metrics are read.",
            "candidate_invocations": 0,
            "max_operations": MAX_OPS,
            "pipe_length_range": [1, 40],
            "first_appended_operation": "A legal delete from the prefix-active set, chosen to differ from the corresponding Open15 next command.",
            "weight_in_generated_input": 1.0,
        },
        "mechanism_families": list(FAMILIES),
        "tests": rows,
    }
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "test_count": len(rows),
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "all_valid": True,
        "candidate_invocations": 0,
    }))


if __name__ == "__main__":
    main()
