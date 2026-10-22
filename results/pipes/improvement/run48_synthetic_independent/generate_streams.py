#!/usr/bin/env python3
"""Generate a fixed, causal synthetic qualification set for run-48.

The scenario list and seeds are committed before solver comparison. Generation
uses only the current phase, PRNG state, and currently active pipes.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import random
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "inputs"

SCENARIOS = [
    {
        "name": "small_short_oldest",
        "operations": 2_000,
        "seed": 41021,
        "phases": [{"start": 0, "end": 2_000, "length_profile": "short-heavy", "churn": 0.20,
                    "deletion_policy": "oldest", "batch": 96, "repeat_probability": 0.0}],
    },
    {
        "name": "medium_uniform_random",
        "operations": 12_000,
        "seed": 41039,
        "phases": [{"start": 0, "end": 12_000, "length_profile": "uniform", "churn": 0.38,
                    "deletion_policy": "random", "batch": 320, "repeat_probability": 0.0}],
    },
    {
        "name": "medium_long_newest",
        "operations": 24_000,
        "seed": 41057,
        "phases": [{"start": 0, "end": 24_000, "length_profile": "long-heavy", "churn": 0.45,
                    "deletion_policy": "newest", "batch": 240, "repeat_probability": 0.0}],
    },
    {
        "name": "medium_bimodal_sticky_shortest",
        "operations": 30_000,
        "seed": 41077,
        "phases": [{"start": 0, "end": 30_000, "length_profile": "bimodal", "churn": 0.50,
                    "deletion_policy": "shortest", "batch": 280, "repeat_probability": 0.78}],
    },
    {
        "name": "phase_short_to_long",
        "operations": 40_000,
        "seed": 41113,
        "phases": [
            {"start": 0, "end": 20_000, "length_profile": "short-heavy", "churn": 0.22,
             "deletion_policy": "random", "batch": 0, "repeat_probability": 0.15},
            {"start": 20_000, "end": 40_000, "length_profile": "long-heavy", "churn": 0.58,
             "deletion_policy": "longest", "batch": 400, "repeat_probability": 0.10},
        ],
    },
    {
        "name": "phase_long_to_short",
        "operations": 70_000,
        "seed": 41131,
        "phases": [
            {"start": 0, "end": 35_000, "length_profile": "long-heavy", "churn": 0.48,
             "deletion_policy": "oldest", "batch": 520, "repeat_probability": 0.08},
            {"start": 35_000, "end": 70_000, "length_profile": "short-heavy", "churn": 0.34,
             "deletion_policy": "newest", "batch": 260, "repeat_probability": 0.20},
        ],
    },
    {
        "name": "three_phase_mixed_removals",
        "operations": 110_000,
        "seed": 41179,
        "phases": [
            {"start": 0, "end": 36_667, "length_profile": "uniform", "churn": 0.36,
             "deletion_policy": "random", "batch": 640, "repeat_probability": 0.0},
            {"start": 36_667, "end": 73_334, "length_profile": "bimodal", "churn": 0.53,
             "deletion_policy": "oldest", "batch": 0, "repeat_probability": 0.82},
            {"start": 73_334, "end": 110_000, "length_profile": "short-heavy", "churn": 0.45,
             "deletion_policy": "shortest", "batch": 360, "repeat_probability": 0.12},
        ],
    },
    {
        "name": "large_four_phase_shift",
        "operations": 180_000,
        "seed": 41201,
        "phases": [
            {"start": 0, "end": 45_000, "length_profile": "long-heavy", "churn": 0.30,
             "deletion_policy": "random", "batch": 720, "repeat_probability": 0.05},
            {"start": 45_000, "end": 90_000, "length_profile": "short-heavy", "churn": 0.56,
             "deletion_policy": "oldest", "batch": 360, "repeat_probability": 0.15},
            {"start": 90_000, "end": 135_000, "length_profile": "long-heavy", "churn": 0.46,
             "deletion_policy": "newest", "batch": 600, "repeat_probability": 0.20},
            {"start": 135_000, "end": 180_000, "length_profile": "uniform", "churn": 0.39,
             "deletion_policy": "longest", "batch": 0, "repeat_probability": 0.0},
        ],
    },
]


class LivePipes:
    """Active pipes with efficient causal deletion-policy selection."""

    def __init__(self):
        self.lengths: dict[int, int] = {}
        self.items: list[int] = []
        self.position: dict[int, int] = {}
        self.oldest: deque[int] = deque()
        self.newest: list[int] = []
        self.shortest_heap: list[tuple[int, int]] = []
        self.longest_heap: list[tuple[int, int]] = []

    def __len__(self):
        return len(self.lengths)

    def add(self, pid: int, length: int) -> None:
        self.lengths[pid] = length
        self.position[pid] = len(self.items)
        self.items.append(pid)
        self.oldest.append(pid)
        self.newest.append(pid)
        heapq.heappush(self.shortest_heap, (length, pid))
        heapq.heappush(self.longest_heap, (-length, pid))

    def remove(self, pid: int) -> int:
        length = self.lengths.pop(pid)
        index = self.position.pop(pid)
        last_pid = self.items.pop()
        if index < len(self.items):
            self.items[index] = last_pid
            self.position[last_pid] = index
        return length

    def choose(self, policy: str, rng: random.Random) -> int:
        if policy == "random":
            return self.items[rng.randrange(len(self.items))]
        if policy == "oldest":
            while self.oldest and self.oldest[0] not in self.lengths:
                self.oldest.popleft()
            return self.oldest[0]
        if policy == "newest":
            while self.newest and self.newest[-1] not in self.lengths:
                self.newest.pop()
            return self.newest[-1]
        if policy == "shortest":
            while self.shortest_heap and self.shortest_heap[0][1] not in self.lengths:
                heapq.heappop(self.shortest_heap)
            return self.shortest_heap[0][1]
        if policy == "longest":
            while self.longest_heap and self.longest_heap[0][1] not in self.lengths:
                heapq.heappop(self.longest_heap)
            return self.longest_heap[0][1]
        raise ValueError(f"unknown deletion policy: {policy}")


def sample_length(rng: random.Random, profile: str, previous: int | None,
                  repeat_probability: float) -> int:
    if previous is not None and rng.random() < repeat_probability:
        return previous
    pick = rng.random()
    if profile == "uniform":
        return rng.randint(1, 40)
    if profile == "short-heavy":
        if pick < 0.65:
            return rng.randint(1, 5)
        if pick < 0.90:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "long-heavy":
        if pick < 0.10:
            return rng.randint(1, 5)
        if pick < 0.35:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "bimodal":
        if pick < 0.44:
            return rng.randint(1, 4)
        if pick < 0.56:
            return rng.randint(18, 23)
        return rng.randint(37, 40)
    raise ValueError(f"unknown length profile: {profile}")


def phase_for(scenario: dict, operation_index: int) -> tuple[int, dict]:
    for index, phase in enumerate(scenario["phases"]):
        if phase["start"] <= operation_index < phase["end"]:
            return index, phase
    raise ValueError(f"no phase covers operation {operation_index}")


def generate(scenario: dict) -> tuple[list[int], dict]:
    operations = scenario["operations"]
    rng = random.Random(scenario["seed"])
    live = LivePipes()
    commands: list[int] = []
    next_pid = 1
    previous_length = None
    previous_phase = None
    drain_remaining = 0
    peak_live_count = 0
    added_length_counts = [0] * 41
    deleted_by_policy: dict[str, int] = {}

    for operation_index in range(operations):
        phase_index, phase = phase_for(scenario, operation_index)
        if phase_index != previous_phase:
            previous_length = None
            previous_phase = phase_index

        # Keep the final state nonempty for the official scorer.
        force_add = operation_index == operations - 1
        must_drain = drain_remaining > 0 and len(live) > 0
        should_delete = (not force_add and bool(live) and
                         (must_drain or rng.random() < phase["churn"]))

        if should_delete:
            pid = live.choose(phase["deletion_policy"], rng)
            live.remove(pid)
            commands.append(-pid)
            deleted_by_policy[phase["deletion_policy"]] = deleted_by_policy.get(phase["deletion_policy"], 0) + 1
            if must_drain:
                drain_remaining -= 1
            if not len(live):
                drain_remaining = 0
            continue

        length = sample_length(rng, phase["length_profile"], previous_length,
                               phase["repeat_probability"])
        previous_length = length
        live.add(next_pid, length)
        commands.append(length)
        added_length_counts[length] += 1
        next_pid += 1
        peak_live_count = max(peak_live_count, len(live))
        if phase["batch"] > 0 and len(live) >= phase["batch"] and drain_remaining == 0:
            drain_remaining = max(1, (phase["batch"] * 3) // 4)

    if len(commands) != operations or len(live) == 0:
        raise ValueError("generator invariant failed")
    return commands, {
        "operations": operations,
        "placements": sum(command > 0 for command in commands),
        "deletions": sum(command < 0 for command in commands),
        "peak_live_pipes": peak_live_count,
        "final_live_pipes": len(live),
        "final_occupied_pipe_length_m": sum(live.lengths.values()),
        "placement_length_counts": {str(i): count for i, count in enumerate(added_length_counts) if count},
        "deletions_by_policy": dict(sorted(deleted_by_policy.items())),
    }


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(INPUT_DIR.glob("*.in"))
    if existing:
        raise SystemExit(f"refusing to overwrite existing synthetic inputs: {existing[0]}")

    all_inputs = {}
    for scenario in SCENARIOS:
        commands, stats = generate(scenario)
        path = INPUT_DIR / f"{scenario['name']}.in"
        lines = [f"1.0 {len(commands)}", *map(str, commands), "0"]
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        all_inputs[scenario["name"]] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha(path),
            "scenario": scenario,
            "stream_stats": stats,
        }

    manifest = {
        "purpose": "Previously unused causal synthetic streams for paired frozen-final vs run-48 comparison",
        "weight_per_stream": 1.0,
        "generation_rule": "At each operation, use only the current operation-index phase, seeded PRNG, active-pipe set and configured causal deletion rule. The final command is forced to be a placement so final occupancy is positive.",
        "generator_sha256": sha(Path(__file__)),
        "inputs": all_inputs,
    }
    (ROOT / "input_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(all_inputs)} fixed synthetic streams")
    for name, info in all_inputs.items():
        stats = info["stream_stats"]
        print(f"{name}: n={stats['operations']} adds={stats['placements']} "
              f"deletes={stats['deletions']} peak_live={stats['peak_live_pipes']} "
              f"final_live={stats['final_live_pipes']} sha256={info['sha256']}")


if __name__ == "__main__":
    main()
