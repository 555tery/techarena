"""Generate candidate-independent Pipes corpora. Never runs solvers or LLMs."""

from __future__ import annotations

from collections import Counter, deque
import hashlib
import heapq
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
VERSION = "synthetic-v1"
SEARCH_FAMILIES = (
    "uniform_churn", "short_heavy", "long_heavy", "bimodal", "section_boundaries",
    "fifo", "lifo", "size_lifetimes", "burst_drain", "distribution_switch",
    "drifting_sizes", "striped_recycling", "geometric_cohorts", "additive_cohorts",
    "large_live_set", "size_biased_deletion",
)
RESERVED_FAMILIES = (
    "pinned_churn", "heavy_tail_lifetimes", "deletion_switch", "nested_cohorts",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Stream:
    def __init__(self, operations: int, rng: random.Random):
        self.limit, self.rng = operations, rng
        self.commands: list[int] = []
        self.live: dict[int, int] = {}
        self.ids: list[int] = []
        self.positions: dict[int, int] = {}
        self.oldest: deque[int] = deque()
        self.newest: list[int] = []
        self.by_length = [deque() for _ in range(41)]
        self.next_pid, self.volume, self.peak = 1, 0, 0

    def insert(self, length: int) -> int | None:
        if len(self.commands) >= self.limit:
            return None
        assert 1 <= length <= 40
        pid = self.next_pid
        self.next_pid += 1
        self.commands.append(length)
        self.live[pid] = length
        self.positions[pid] = len(self.ids)
        self.ids.append(pid)
        self.oldest.append(pid)
        self.newest.append(pid)
        self.by_length[length].append(pid)
        self.volume += length
        self.peak = max(self.peak, self.volume)
        return pid

    def delete(self, pid: int) -> bool:
        if len(self.commands) >= self.limit or pid not in self.live:
            return False
        # Avoid a degenerate zero-final-volume score, without appending extra ops.
        if len(self.commands) == self.limit - 1 and len(self.live) == 1:
            self.insert(self.rng.randint(1, 40))
            return False
        self.commands.append(-pid)
        self.volume -= self.live.pop(pid)
        index = self.positions.pop(pid)
        last = self.ids.pop()
        if index < len(self.ids):
            self.ids[index] = last
            self.positions[last] = index
        return True

    def choose(self, policy: str) -> int:
        if policy == "random":
            return self.rng.choice(self.ids)
        if policy == "fifo":
            while self.oldest[0] not in self.live:
                self.oldest.popleft()
            return self.oldest[0]
        if policy == "lifo":
            while self.newest[-1] not in self.live:
                self.newest.pop()
            return self.newest[-1]
        lengths = range(1, 41) if policy == "shortest" else range(40, 0, -1)
        for length in lengths:
            bucket = self.by_length[length]
            while bucket and bucket[0] not in self.live:
                bucket.popleft()
            if bucket:
                return bucket[0]
        raise ValueError("no live pipe")


def sample_length(rng: random.Random, profile: str, step: int = 0) -> int:
    if profile == "short":
        return rng.randint(1, 6) if rng.random() < 0.8 else rng.randint(7, 40)
    if profile == "long":
        return rng.randint(29, 40) if rng.random() < 0.8 else rng.randint(1, 28)
    if profile == "bimodal":
        return rng.randint(1, 4) if rng.random() < 0.55 else rng.randint(36, 40)
    if profile == "boundary":
        return rng.choice([1, 2, 18, 19, 20, 21, 22, 38, 39, 40])
    if profile == "geometric":
        sizes = [1, 2, 3, 5, 8, 13, 21, 34]
        return sizes[(step // 173) % len(sizes)]
    if profile == "additive":
        return 1 + (step // 137) % 40
    return rng.randint(1, 40)


def make_specs(split: str) -> list[dict]:
    families = SEARCH_FAMILIES if split == "search" else SEARCH_FAMILIES + RESERVED_FAMILIES
    specs = []
    for family_index, family in enumerate(families):
        repeats = 2 if split == "search" or family in RESERVED_FAMILIES else 1
        for repeat in range(repeats):
            seed = int.from_bytes(hashlib.sha256(f"{VERSION}/{split}/{family}/{repeat}".encode()).digest()[:8], "big")
            rng = random.Random(seed ^ 0xA917E3)
            if split == "search":
                operations = (20_000, 80_000)[repeat]
                target = rng.choice([32, 128, 512, 2048])
                deletion_probability = rng.choice([0.28, 0.42, 0.49, 0.57])
            else:
                operations = rng.choice([45_000, 110_000, 160_000])
                target = rng.choice([73, 311, 1103, 3907])
                deletion_probability = rng.choice([0.34, 0.46, 0.53, 0.63])
            if family == "large_live_set":
                operations = 200_000
                target = 12_000 if split == "search" else 27_000
                deletion_probability = 0.19 if split == "search" else 0.25
            if family == "heavy_tail_lifetimes" and repeat == 1:
                operations = 200_000
            specs.append({"id": f"{'s' if split == 'search' else 'v'}{len(specs) + 1:03d}_{family}",
                          "family": family, "seed": seed, "operations": operations,
                          "target_live": target, "deletion_probability": deletion_probability,
                          "held_out_mechanism": family in RESERVED_FAMILIES})
    return specs


def generate(spec: dict) -> list[int]:
    rng = random.Random(spec["seed"])
    stream = Stream(spec["operations"], rng)
    family, target = spec["family"], spec["target_live"]
    profile = {"short_heavy": "short", "long_heavy": "long", "bimodal": "bimodal",
               "section_boundaries": "boundary", "geometric_cohorts": "geometric",
               "additive_cohorts": "additive"}.get(family, "uniform")
    if family in {"size_lifetimes", "heavy_tail_lifetimes"}:
        due: list[tuple[int, int]] = []
        clock = 0
        while len(stream.commands) < stream.limit:
            clock += 1
            if due and due[0][0] <= clock:
                _, pid = heapq.heappop(due)
                stream.delete(pid)
                continue
            length = rng.randint(1, 40)
            pid = stream.insert(length)
            if family == "heavy_tail_lifetimes":
                lifetime = min(500_000, int(target * rng.paretovariate(1.15)))
            else:
                # Size/lifetime correlation changes sign between phases.
                multiplier = length if (clock // 5000) % 2 else 41 - length
                lifetime = max(1, int(rng.expovariate(1 / max(1, target * multiplier / 20))))
            heapq.heappush(due, (clock + lifetime, pid))
    elif family in {"burst_drain", "striped_recycling", "nested_cohorts", "pinned_churn"}:
        pins: set[int] = set()
        if family == "pinned_churn":
            for _ in range(max(3, target // 8)):
                pid = stream.insert(rng.choice([1, 2, 39, 40]))
                if pid is not None:
                    pins.add(pid)
        previous: list[int] = []
        wave = 0
        while len(stream.commands) < stream.limit:
            cohort = []
            batch = rng.randint(max(4, target // 2), max(8, target))
            for index in range(batch):
                length = (rng.randint(1, 5) if index % 2 else rng.randint(30, 40)) if family == "striped_recycling" else rng.randint(1, 40)
                pid = stream.insert(length)
                if pid is not None:
                    cohort.append(pid)
            if family == "striped_recycling":
                victims = cohort[(wave % 3)::3]
            elif family == "nested_cohorts":
                victims = previous if wave % 2 else list(reversed(previous))
                previous = cohort
            elif family == "pinned_churn":
                victims = [pid for pid in stream.ids if pid not in pins]
                rng.shuffle(victims)
                victims = victims[:max(1, int(len(victims) * 0.85))]
            else:
                victims = list(stream.ids)
                rng.shuffle(victims)
                victims = victims[:max(1, int(len(victims) * rng.uniform(0.55, 0.95)))]
            for pid in victims:
                stream.delete(pid)
            wave += 1
    else:
        center = rng.randint(1, 40)
        phase_length = rng.randint(701, 1901)
        while len(stream.commands) < stream.limit:
            step = len(stream.commands)
            policy = "fifo" if family == "fifo" else "lifo" if family == "lifo" else "random"
            current_profile, current_target = profile, target
            if family == "size_biased_deletion":
                policy = "shortest" if (step // phase_length) % 2 else "longest"
            if family == "deletion_switch":
                policy = ["fifo", "shortest", "random", "lifo", "longest"][(step // phase_length) % 5]
            if family == "distribution_switch":
                current_profile = ["short", "long", "bimodal", "uniform"][(step // phase_length) % 4]
                current_target = max(8, int(target * [0.2, 2.0, 0.7, 1.4][(step // phase_length) % 4]))
            remove = bool(stream.live) and (len(stream.live) > current_target or rng.random() < spec["deletion_probability"])
            if remove:
                stream.delete(stream.choose(policy))
            else:
                if family == "drifting_sizes":
                    center = max(1, min(40, center + rng.choice([-1, 0, 0, 1])))
                    length = max(1, min(40, center + rng.randint(-3, 3)))
                else:
                    length = sample_length(rng, current_profile, step)
                stream.insert(length)
    assert len(stream.commands) == spec["operations"] and stream.live
    return stream.commands


def audit_commands(commands: list[int]) -> dict:
    """Independent structural validation, without any allocator execution."""
    if not 1 <= len(commands) <= 200_000:
        raise ValueError("operation count outside official bounds")
    active, next_pid, volume, peak, max_live = {}, 1, 0, 0, 0
    histogram = Counter()
    deletions = 0
    for command in commands:
        if command > 0:
            if command > 40:
                raise ValueError("length outside [1,40]")
            active[next_pid] = command
            next_pid += 1
            histogram[command] += 1
            volume += command
            peak, max_live = max(peak, volume), max(max_live, len(active))
        elif command < 0 and -command in active:
            volume -= active.pop(-command)
            deletions += 1
        else:
            raise ValueError("invalid PID deletion or embedded zero")
    if volume <= 0:
        raise ValueError("zero final volume")
    return {"operation_count": len(commands), "insertions": next_pid - 1, "deletions": deletions,
            "peak_live_count": max_live, "peak_live_volume": peak, "final_live_volume": volume,
            "volume_lower_bound": 20 * math.ceil(peak / 20),
            "length_histogram": {str(k): histogram[k] for k in sorted(histogram)}}


def prepare(destination: Path = ROOT) -> dict:
    search_path = destination / "task-synthetic/data/search"
    validation_path = destination / "validation-v1/data"
    for path in (search_path, validation_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite an existing corpus: {path}")
    report = {"version": VERSION, "solvers_executed": 0, "model_requests": 0, "splits": {}}
    seen_hashes, seen_seeds = set(), set()
    for split, path in (("search", search_path), ("validation", validation_path)):
        path.mkdir(parents=True)
        entries = []
        for spec in make_specs(split):
            commands = generate(spec)
            stats = audit_commands(commands)
            file = path / f"{spec['id']}.in"
            file.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
            digest = sha256(file)
            if digest in seen_hashes or spec["seed"] in seen_seeds:
                raise ValueError("duplicate stream or seed between prepared cases")
            seen_hashes.add(digest)
            seen_seeds.add(spec["seed"])
            entries.append({**spec, "file": file.name, "sha256": digest, "stats": stats})
        manifest = {"version": VERSION, "split": split, "generator_sha256": sha256(Path(__file__)),
                    "python_version": sys.version.split()[0], "weight_per_case": 1,
                    "case_count": len(entries), "families": sorted({e['family'] for e in entries}),
                    "held_out_mechanisms": list(RESERVED_FAMILIES) if split == "validation" else [],
                    "fitness": "mean_over_families(mean_over_cases(rounded_peak_live_volume / trench_length))",
                    "candidate_results_used_in_design": False, "cases": entries}
        (path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        report["splits"][split] = {"cases": len(entries), "families": len(manifest["families"]),
                                    "operations": sum(e['operations'] for e in entries),
                                    "manifest_sha256": sha256(path / "manifest.json")}
    (destination / "corpus-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
