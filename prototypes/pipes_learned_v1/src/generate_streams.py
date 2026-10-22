#!/usr/bin/env python3
"""Generate the frozen, solver-independent Pipes streams for learned-v1.

Only Python's standard library is used. Stream generation is deterministic
across Python versions because it uses the specified SplitMix64 PRNG rather
than random.Random's higher-level sampling helpers.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve()
PROTOTYPE_ROOT = HERE.parents[1]
REPOSITORY_ROOT = HERE.parents[3]
DATA_ROOT = PROTOTYPE_ROOT / "data"
MANIFEST_PATH = DATA_ROOT / "manifest.json"
DESIGN_PATH = DATA_ROOT / "design_final_prerun.json"
README_PATH = DATA_ROOT / "README.md"
MASK64 = (1 << 64) - 1
UINT64_RANGE = 1 << 64


TRAIN_FAMILIES = [
    {
        "id": "uniform_random_steady",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "near_lifo",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "newest active PID with probability 0.90, otherwise random",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "fifo",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "oldest active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "bounded_bimodal",
        "length_rule": "equal mixture of uniform 1..4 and uniform 37..40",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "ascending_size_phases",
        "length_rule": "four equal operation-index phases: 1..8, 9..16, 17..28, 33..40",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "descending_size_phases",
        "length_rule": "four equal operation-index phases: 33..40, 17..28, 9..16, 1..8",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
    {
        "id": "periodic_drain",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "oldest active PID during drain-heavy subphase",
        "arrival_rule": "period 1000; phase 0..749 add-biased, phase 750..999 delete-biased",
    },
    {
        "id": "geometric_additive_size_blocks",
        "length_rule": "128-placement blocks on geometric ladder 1,2,4,8,16,32,40 with additive cycle offset; 20% +/-1 noise",
        "deletion_rule": "equal mixture of random, oldest, and newest active PID",
        "arrival_rule": "time-homogeneous; split profile controls drift",
    },
]


FINAL_FAMILIES = [
    {
        "id": "cohort_correlated_survivor_stranding",
        "length_rule": "mostly cohort-shared uniform 1..40 length, with 25% independent length noise",
        "deletion_rule": "oldest cohort first in batches; 8% anchors protected for 1024 operations",
        "arrival_rule": "time-homogeneous within growth/bounded split profile",
    },
    {
        "id": "abrupt_size_and_delete_policy_shifts",
        "length_rule": "four equal operation phases: 1..6, 35..40, 7..18, 19..34",
        "deletion_rule": "phase policy changes independently with size: random, newest, oldest, longest",
        "arrival_rule": "time-homogeneous within growth/bounded split profile",
    },
    {
        "id": "bursty_sawtooth_persistent_anchors",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "2048-operation fill/drain cycles; 8% anchors protected for 12288 operations",
        "arrival_rule": "first half fill-biased, second half drain-biased; bounded cap prevents unbounded growth",
    },
    {
        "id": "heavy_tailed_age_mixture_lifetimes",
        "length_rule": "short-heavy mixture: 65% 1..5, 25% 6..20, 10% 21..40",
        "deletion_rule": "70% choose oldest among eight random active samples, 30% uniform random",
        "arrival_rule": "time-homogeneous within growth/bounded split profile",
    },
    {
        "id": "permuted_narrow_alphabet_deleted_longest",
        "length_rule": "seeded permutation of a four-consecutive-length alphabet, repeated in 32-placement blocks",
        "deletion_rule": "longest active pipe; ties by oldest PID",
        "arrival_rule": "time-homogeneous within growth/bounded split profile",
    },
    {
        "id": "cyclic_demand_delayed_cohort_deletes",
        "length_rule": "size ranges cycle by operation phase; deletion targets cohorts at least 1200 operations old",
        "deletion_rule": "matured cohort first during delayed-delete phase, random fallback before a cohort matures",
        "arrival_rule": "cycle 1800; first 1200 operations add-biased, final 600 delete-biased",
    },
    {
        "id": "stationary_bursty_geometric_arrivals",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous alternating add/delete bursts with geometric run lengths (mean 20, cap 256)",
    },
    {
        "id": "alternating_oldest_newest_delete_epochs",
        "length_rule": "uniform integer 1..40, independent of deletion-policy epochs",
        "deletion_rule": "oldest PID for even 512-operation epochs, newest PID for odd epochs",
        "arrival_rule": "time-homogeneous within growth/bounded split profile",
    },
]


DESIGN = {
    "schema": "pipes-learned-v1-synthetic-design",
    "design_revision": "final-prerun-2026-10-17-r1",
    "stream_format": {
        "header": "1 <operation_count>",
        "commands": "one signed integer per line; positive 1..40 inserts, negative PID deletes",
        "terminator": "a trailing 0 sentinel outside operation_count",
        "weight": 1,
    },
    "validity": {
        "max_operations_per_stream": 200000,
        "pipe_lengths": [1, 40],
        "all_deletions_must_reference_live_pid": True,
        "last_counted_operation_is_insert": True,
        "final_occupied_length_must_be_positive": True,
        "peak_live_count_must_be_positive": True,
        "live_profiles": {
            "growth": "time-invariant positive-drift arrival/deletion process; expected live set grows with stream length",
            "bounded": "arrival/deletion process constrained to [max(20, cap//3), cap], with a final insert allowed to reach cap+1",
            "bounded_cap": "min(4000, max(300, floor(operation_count/8)))",
        },
    },
    "prng": {
        "algorithm": "SplitMix64",
        "integer_sampling": "rejection sampling over uint64 range",
        "seed_ranges": {
            "train": {"first": 81733000, "count": 128, "stride": 1},
            "calibration": {"first": 81734000, "count": 24, "stride": 1},
            "final_validation": {"first": 81735000, "count": 24, "stride": 1},
        },
    },
    "splits": {
        "train": {
            "count": 128,
            "family_count": 8,
            "streams_per_family": 16,
            "operation_count_by_replica": {"replicas_0_to_13": 6000, "replicas_14_to_15": 20000},
            "profile_assignment": "replica parity: even=bounded, odd=growth",
            "families": TRAIN_FAMILIES,
        },
        "calibration": {
            "count": 24,
            "family_count": 8,
            "streams_per_family": 3,
            "operation_count": 8000,
            "profile_assignment": "(family_index + replica_index) parity: even=bounded, odd=growth",
            "families": TRAIN_FAMILIES,
            "seed_range_is_disjoint_from_train": True,
        },
        "final_validation": {
            "count": 24,
            "family_count": 8,
            "streams_per_family": 3,
            "operation_counts_by_replica": [12000, 30000, 200000],
            "profile_assignment": "(family_index + replica_index) parity: even=bounded, odd=growth",
            "families": FINAL_FAMILIES,
            "generation": "deferred until a nonempty model freeze ID is supplied",
            "seed_range_is_disjoint_from_train_and_calibration": True,
        },
    },
    "evaluation_boundary": {
        "training_and_calibration_files_generated_before_model_freeze": True,
        "final_validation_files_generated_only_after_model_freeze_id": True,
        "final_validation_scores_not_part_of_generation_or_validation": True,
        "do_not_change_family_rules_seeds_sizes_or_prng_after_freeze": True,
    },
}


class SplitMix64:
    """Small specified PRNG with stable uint64 output and unbiased bounded draws."""

    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64

    def below(self, stop: int) -> int:
        if stop <= 0:
            raise ValueError("stop must be positive")
        limit = UINT64_RANGE - (UINT64_RANGE % stop)
        while True:
            value = self.next_u64()
            if value < limit:
                return value % stop

    def chance(self, numerator: int, denominator: int) -> bool:
        if numerator <= 0:
            return False
        if numerator >= denominator:
            return True
        return self.below(denominator) < numerator

    def shuffle(self, values: list[int]) -> None:
        for index in range(len(values) - 1, 0, -1):
            other = self.below(index + 1)
            values[index], values[other] = values[other], values[index]


class StreamState:
    """Active PID index with O(1) random deletion and lazy policy heaps."""

    def __init__(self):
        self.active: list[int] = []
        self.position: list[int] = [-1]
        self.length: list[int] = [0]
        self.alive = bytearray([0])
        self.insert_op: list[int] = [-1]
        self.anchor_until: list[int] = [-1]
        self.cohort_id: list[int] = [-1]
        self.cohorts: list[list[int]] = []
        self.random_oldest_heap: list[int] = []
        self.random_newest_heap: list[int] = []
        self.longest_heap: list[tuple[int, int]] = []
        self.shortest_heap: list[tuple[int, int]] = []
        self.oldest_cursor = 1
        self.newest_cursor = 0
        self.live_length = 0
        self.peak_live_length = 0
        self.peak_live_count = 0
        self.cohort_scan = 0
        self.cohort_offsets: list[int] = []

    @property
    def live_count(self) -> int:
        return len(self.active)

    @property
    def placement_count(self) -> int:
        return len(self.length) - 1

    def insert(self, pipe_length: int, operation_index: int, cohort: int, anchor_until: int):
        pid = len(self.length)
        self.length.append(pipe_length)
        self.alive.append(1)
        self.insert_op.append(operation_index)
        self.anchor_until.append(anchor_until)
        self.cohort_id.append(cohort)
        self.position.append(len(self.active))
        self.active.append(pid)
        self.live_length += pipe_length
        self.peak_live_length = max(self.peak_live_length, self.live_length)
        self.peak_live_count = max(self.peak_live_count, len(self.active))
        heapq.heappush(self.random_oldest_heap, pid)
        heapq.heappush(self.random_newest_heap, -pid)
        heapq.heappush(self.longest_heap, (-pipe_length, pid))
        heapq.heappush(self.shortest_heap, (pipe_length, pid))
        if cohort >= 0:
            while len(self.cohorts) <= cohort:
                self.cohorts.append([])
                self.cohort_offsets.append(0)
            self.cohorts[cohort].append(pid)
        self.newest_cursor = pid
        return pid

    def remove(self, pid: int) -> None:
        if pid <= 0 or pid >= len(self.alive) or not self.alive[pid]:
            raise ValueError("attempt to remove an absent PID")
        index = self.position[pid]
        last_pid = self.active[-1]
        self.active[index] = last_pid
        self.position[last_pid] = index
        self.active.pop()
        self.position[pid] = -1
        self.alive[pid] = 0
        self.live_length -= self.length[pid]

    def choose_random(self, rng: SplitMix64) -> int:
        return self.active[rng.below(len(self.active))]

    def choose_oldest(self) -> int:
        while self.random_oldest_heap:
            pid = self.random_oldest_heap[0]
            if self.alive[pid]:
                heapq.heappop(self.random_oldest_heap)
                return pid
            heapq.heappop(self.random_oldest_heap)
        raise ValueError("cannot choose an oldest PID from an empty live set")

    def choose_newest(self) -> int:
        while self.random_newest_heap:
            pid = -self.random_newest_heap[0]
            if self.alive[pid]:
                heapq.heappop(self.random_newest_heap)
                return pid
            heapq.heappop(self.random_newest_heap)
        raise ValueError("cannot choose a newest PID from an empty live set")

    def choose_longest(self) -> int:
        while self.longest_heap:
            neg_length, pid = self.longest_heap[0]
            if self.alive[pid]:
                heapq.heappop(self.longest_heap)
                return pid
            heapq.heappop(self.longest_heap)
        raise ValueError("cannot choose a longest PID from an empty live set")

    def choose_cohort(self, operation_index: int, minimum_age: int = 0) -> int | None:
        while self.cohort_scan < len(self.cohorts):
            members = self.cohorts[self.cohort_scan]
            offset = self.cohort_offsets[self.cohort_scan]
            while offset < len(members):
                pid = members[offset]
                if not self.alive[pid]:
                    offset += 1
                    self.cohort_offsets[self.cohort_scan] = offset
                    continue
                if self.anchor_until[pid] > operation_index:
                    offset += 1
                    self.cohort_offsets[self.cohort_scan] = offset
                    continue
                if operation_index - self.insert_op[pid] < minimum_age:
                    # Cohort members are inserted in order, so later members
                    # cannot have reached the age threshold yet either.
                    self.cohort_offsets[self.cohort_scan] = offset
                    return None
                offset += 1
                self.cohort_offsets[self.cohort_scan] = offset
                return pid
            self.cohort_scan += 1
        return None

    def choose_longest_of_sample(self, rng: SplitMix64, sample_count: int = 8) -> int:
        count = min(sample_count, len(self.active))
        selected = self.active[rng.below(len(self.active))]
        for _ in range(count - 1):
            candidate = self.active[rng.below(len(self.active))]
            if (self.length[candidate], -candidate) > (self.length[selected], -selected):
                selected = candidate
        return selected

    def choose_non_anchor(self, operation_index: int, rng: SplitMix64) -> int:
        for _ in range(min(24, len(self.active))):
            pid = self.choose_random(rng)
            if self.anchor_until[pid] <= operation_index:
                return pid
        return self.choose_random(rng)


class BurstProcess:
    def __init__(self):
        self.remaining = 0
        self.add_mode = True

    def next(self, rng: SplitMix64, growth: bool) -> bool:
        if self.remaining <= 0:
            self.add_mode = rng.chance(2, 3) if growth else rng.chance(1, 2)
            run_length = 1
            while run_length < 256 and rng.chance(1, 20):
                run_length += 1
            self.remaining = run_length
        self.remaining -= 1
        return self.add_mode


def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def design_hash() -> str:
    return hashlib.sha256(canonical_json_bytes(DESIGN)).hexdigest()


def script_hash() -> str:
    return hashlib.sha256(HERE.read_bytes()).hexdigest()


def manifest_template() -> dict:
    return {
        "design": DESIGN,
        "design_sha256": design_hash(),
        "generator_sha256_at_design_freeze": script_hash(),
        "artifacts": {
            "train": None,
            "calibration": None,
            "final_validation": None,
        },
    }


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True).encode("ascii") + b"\n")
    temporary.replace(path)


def ensure_design_files() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    design_doc = {"design": DESIGN, "design_sha256": design_hash()}
    for path, expected in ((DESIGN_PATH, design_doc), (MANIFEST_PATH, manifest_template())):
        if path.exists():
            existing = json.loads(path.read_text(encoding="ascii"))
            if path == DESIGN_PATH:
                if existing != expected:
                    raise RuntimeError(f"refusing to replace a different frozen design: {path}")
            else:
                if existing.get("design_sha256") != design_hash() or existing.get("design") != DESIGN:
                    raise RuntimeError(f"manifest design differs from frozen design: {path}")
                if existing.get("generator_sha256_at_design_freeze") != script_hash():
                    raise RuntimeError(f"generator differs from its frozen hash: {path}")
        else:
            write_json_atomic(path, expected)
    if not README_PATH.exists():
        readme = f"""# Pipes learned-v1 synthetic data

Дизайн потоков зафиксирован до генерации наборов и до любых solver scores. SHA-256: `{design_hash()}`.

`design_final_prerun.json` содержит неизменяемую схему, `manifest.json` — ту же схему и контрольные суммы созданных файлов.

Train и calibration созданы сейчас из собственных фиксированных seed. Final validation содержит восемь новых семейств и 24 заранее заданных потока; сами входы будут созданы только после передачи непустого model freeze ID. Их seed, длины и правила уже записаны в схеме.

В каждом потоке `n` считает только команды; завершающий `0` не входит в `n`. Длина траншеи здесь не симулируется. Все PID проверяются на корректность, каждый поток заканчивается живой трубой, а оба профиля live set представлены в каждом train family.

Не меняйте семейства, seed ranges, operation counts, profile assignment или PRNG после фиксации hash. Любой новый дизайн требует отдельной версии.
"""
        README_PATH.write_text(readme, encoding="utf-8")


def family_index_for(seed_index: int, split: str) -> tuple[int, int, int, str]:
    if split == "train":
        family_index, replica = divmod(seed_index, 16)
        operations = 20000 if replica >= 14 else 6000
        mode = "growth" if replica % 2 == 1 else "bounded"
    elif split == "calibration":
        family_index, replica = divmod(seed_index, 3)
        operations = 8000
        mode = "bounded" if (family_index + replica) % 2 == 0 else "growth"
    elif split == "final_validation":
        family_index, replica = divmod(seed_index, 3)
        operations = (12000, 30000, 200000)[replica]
        mode = "bounded" if (family_index + replica) % 2 == 0 else "growth"
    else:
        raise ValueError("unknown split: " + split)
    return family_index, replica, operations, mode


def _range_length(rng: SplitMix64, low: int, high: int) -> int:
    return low + rng.below(high - low + 1)


def sample_length(family_id: str, operation_index: int, placement_index: int, operation_count: int,
                  rng: SplitMix64, state: StreamState, cohort_size: int,
                  narrow_alphabet: list[int]) -> int:
    if family_id in ("uniform_random_steady", "near_lifo", "fifo", "periodic_drain",
                     "bursty_sawtooth_persistent_anchors", "stationary_bursty_geometric_arrivals",
                     "alternating_oldest_newest_delete_epochs"):
        return _range_length(rng, 1, 40)
    if family_id == "bounded_bimodal":
        return _range_length(rng, 1, 4) if rng.chance(1, 2) else _range_length(rng, 37, 40)
    if family_id in ("ascending_size_phases", "descending_size_phases"):
        phase = min(3, (operation_index * 4) // operation_count)
        ranges = [(1, 8), (9, 16), (17, 28), (33, 40)]
        if family_id == "descending_size_phases":
            ranges.reverse()
        return _range_length(rng, *ranges[phase])
    if family_id == "geometric_additive_size_blocks":
        block_index = (placement_index - 1) // 128
        ladder = [1, 2, 4, 8, 16, 32, 40]
        cycle, in_cycle = divmod(block_index, 14)
        ladder_index = in_cycle if in_cycle < 7 else 13 - in_cycle
        base = min(40, ladder[ladder_index] + cycle * 2)
        if rng.chance(1, 5):
            base += -1 if rng.chance(1, 2) else 1
        return min(40, max(1, base))
    if family_id == "cohort_correlated_survivor_stranding":
        cohort = (placement_index - 1) // cohort_size
        if cohort >= len(state.cohorts):
            return _range_length(rng, 1, 40)
        prior = state.cohorts[cohort]
        if prior:
            base_pid = prior[0]
            base = state.length[base_pid]
            if rng.chance(3, 4):
                return base
        return _range_length(rng, 1, 40)
    if family_id == "abrupt_size_and_delete_policy_shifts":
        phase = min(3, (operation_index * 4) // operation_count)
        return _range_length(rng, *((1, 6), (35, 40), (7, 18), (19, 34))[phase])
    if family_id == "heavy_tailed_age_mixture_lifetimes":
        pick = rng.below(100)
        if pick < 65:
            return _range_length(rng, 1, 5)
        if pick < 90:
            return _range_length(rng, 6, 20)
        return _range_length(rng, 21, 40)
    if family_id == "permuted_narrow_alphabet_deleted_longest":
        return narrow_alphabet[(placement_index - 1) // 32 % len(narrow_alphabet)]
    if family_id == "cyclic_demand_delayed_cohort_deletes":
        phase = (operation_index % 1800) // 450
        ranges = [(1, 5), (8, 14), (25, 32), (15, 24)]
        return _range_length(rng, *ranges[phase])
    raise ValueError("no length rule for family: " + family_id)


def add_probability(family_id: str, operation_index: int, operation_count: int,
                    mode: str, burst_process: BurstProcess | None, rng: SplitMix64) -> int:
    if family_id == "periodic_drain":
        return 7200 if operation_index % 1000 < 750 else 2000
    if family_id == "bursty_sawtooth_persistent_anchors":
        phase = operation_index % 2048
        return 8200 if phase < 1024 else 4500
    if family_id == "cyclic_demand_delayed_cohort_deletes":
        return 7200 if operation_index % 1800 < 1200 else 2500
    if family_id == "stationary_bursty_geometric_arrivals":
        assert burst_process is not None
        return 10000 if burst_process.next(rng, mode == "growth") else 0
    if mode == "growth":
        return 6800
    return 5000


def bounded_cap(operation_count: int) -> int:
    return min(4000, max(300, operation_count // 8))


def choose_delete(family_id: str, operation_index: int, state: StreamState, rng: SplitMix64,
                  cohort_min_age: int) -> int:
    if family_id in ("uniform_random_steady", "bounded_bimodal", "ascending_size_phases",
                     "descending_size_phases", "stationary_bursty_geometric_arrivals"):
        return state.choose_random(rng)
    if family_id == "near_lifo":
        return state.choose_newest() if rng.chance(9, 10) else state.choose_random(rng)
    if family_id == "fifo":
        return state.choose_oldest()
    if family_id == "periodic_drain":
        return state.choose_oldest() if operation_index % 1000 >= 750 else state.choose_random(rng)
    if family_id == "geometric_additive_size_blocks":
        policy = rng.below(3)
        if policy == 0:
            return state.choose_random(rng)
        if policy == 1:
            return state.choose_oldest()
        return state.choose_newest()
    if family_id == "cohort_correlated_survivor_stranding":
        return state.choose_cohort(operation_index) or state.choose_random(rng)
    if family_id == "abrupt_size_and_delete_policy_shifts":
        # Phase boundaries are supplied as metadata on the state by the caller.
        phase = getattr(state, "abrupt_phase", 0)
        if phase == 0:
            return state.choose_random(rng)
        if phase == 1:
            return state.choose_newest()
        if phase == 2:
            return state.choose_oldest()
        return state.choose_longest()
    if family_id == "bursty_sawtooth_persistent_anchors":
        return state.choose_non_anchor(operation_index, rng)
    if family_id == "heavy_tailed_age_mixture_lifetimes":
        return state.choose_longest_of_sample(rng, 8) if rng.chance(7, 10) else state.choose_random(rng)
    if family_id == "permuted_narrow_alphabet_deleted_longest":
        return state.choose_longest()
    if family_id == "cyclic_demand_delayed_cohort_deletes":
        candidate = state.choose_cohort(operation_index, cohort_min_age)
        return candidate if candidate is not None else state.choose_random(rng)
    if family_id == "alternating_oldest_newest_delete_epochs":
        return state.choose_oldest() if (operation_index // 512) % 2 == 0 else state.choose_newest()
    raise ValueError("no deletion rule for family: " + family_id)


def generate_commands(seed: int, operations: int, family_id: str, mode: str) -> tuple[list[int], dict]:
    if not (1 <= operations <= 200000):
        raise ValueError("operations must be in [1, 200000]")
    rng = SplitMix64(seed)
    state = StreamState()
    burst_process = BurstProcess() if family_id == "stationary_bursty_geometric_arrivals" else None
    cohort_size = 256
    cohort_delay = 1200
    narrow_low = 1 + rng.below(34)
    narrow_alphabet = list(range(narrow_low, narrow_low + 4))
    rng.shuffle(narrow_alphabet)
    commands: list[int] = []
    cap = bounded_cap(operations)
    low = max(20, cap // 3)

    for operation_index in range(operations):
        state.abrupt_phase = min(3, (operation_index * 4) // operations)
        if operation_index == operations - 1:
            should_add = True
        elif mode == "bounded" and state.live_count <= low:
            should_add = True
        elif mode == "bounded" and state.live_count >= cap:
            should_add = False
        else:
            probability = add_probability(family_id, operation_index, operations, mode, burst_process, rng)
            should_add = rng.below(10000) < probability
            if not state.active:
                should_add = True
            if (family_id == "cyclic_demand_delayed_cohort_deletes"
                    and operation_index < cohort_delay and mode == "growth"):
                should_add = True

        if should_add:
            placement_index = state.placement_count + 1
            length = sample_length(family_id, operation_index, placement_index, operations,
                                   rng, state, cohort_size, narrow_alphabet)
            cohort = (placement_index - 1) // cohort_size
            if family_id in ("cohort_correlated_survivor_stranding", "cyclic_demand_delayed_cohort_deletes"):
                anchor_until = operation_index + 1024 if family_id == "cohort_correlated_survivor_stranding" and rng.chance(8, 100) else -1
            elif family_id == "bursty_sawtooth_persistent_anchors" and rng.chance(8, 100):
                anchor_until = operation_index + 12288
            else:
                anchor_until = -1
            if family_id not in ("cohort_correlated_survivor_stranding", "cyclic_demand_delayed_cohort_deletes"):
                cohort = -1
            commands.append(length)
            state.insert(length, operation_index, cohort, anchor_until)
        else:
            if not state.active:
                raise AssertionError("delete chosen with empty live set")
            pid = choose_delete(family_id, operation_index, state, rng, cohort_delay)
            commands.append(-pid)
            state.remove(pid)

    if not state.live_length or not state.peak_live_length:
        raise AssertionError("generated zero final occupancy or zero peak live length")
    minimum_growth = max(1, operations // 100)
    if mode == "growth" and state.peak_live_count < minimum_growth:
        raise AssertionError(f"growth stream failed minimum live-set coverage: {state.peak_live_count}")
    if mode == "bounded" and state.peak_live_count > cap + 1:
        raise AssertionError(f"bounded stream exceeded cap: {state.peak_live_count} > {cap + 1}")
    return commands, {
        "profile": mode,
        "bounded_live_cap": cap if mode == "bounded" else None,
        "peak_live_count": state.peak_live_count,
        "final_live_count": state.live_count,
    }


def stream_bytes(commands: list[int]) -> bytes:
    lines = [f"1 {len(commands)}"]
    lines.extend(str(command) for command in commands)
    lines.append("0")
    return ("\n".join(lines) + "\n").encode("ascii")


def validate_stream(path: Path, expected_operations: int) -> dict:
    if str(REPOSITORY_ROOT) not in sys.path:
        sys.path.insert(0, str(REPOSITORY_ROOT))
    from tools.pipes_harness import parse_test

    parsed = parse_test(path)
    if parsed["operation_count"] != expected_operations:
        raise ValueError(f"{path}: harness parsed {parsed['operation_count']} operations, expected {expected_operations}")
    raw_tokens = path.read_text(encoding="ascii").split()
    if len(raw_tokens) != expected_operations + 3 or raw_tokens[-1] != "0":
        raise ValueError(f"{path}: expected header, n commands, and one trailing zero")
    commands = [int(token) for token in raw_tokens[2:-1]]
    if len(commands) != expected_operations or commands[-1] <= 0:
        raise ValueError(f"{path}: final counted command must insert a pipe")

    alive: set[int] = set()
    lengths: dict[int, int] = {}
    final_length = 0
    peak_length = 0
    next_pid = 1
    for command in commands:
        if command > 0:
            if not 1 <= command <= 40:
                raise ValueError(f"{path}: invalid pipe length {command}")
            alive.add(next_pid)
            lengths[next_pid] = command
            final_length += command
            peak_length = max(peak_length, final_length)
            next_pid += 1
        else:
            pid = -command
            if pid not in alive:
                raise ValueError(f"{path}: deletion references absent PID {pid}")
            alive.remove(pid)
            final_length -= lengths[pid]
    if final_length <= 0 or peak_length <= 0 or not alive:
        raise ValueError(f"{path}: zero final KPI or zero peak volume")
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "operation_count": expected_operations,
        "placement_count": next_pid - 1,
        "final_live_count": len(alive),
        "final_occupied_length_m": final_length,
        "peak_live_pipe_length_m": peak_length,
    }


def split_records(split: str) -> list[dict]:
    if split == "train":
        count, seed_first = 128, 81733000
    elif split == "calibration":
        count, seed_first = 24, 81734000
    elif split == "final_validation":
        count, seed_first = 24, 81735000
    else:
        raise ValueError("unknown split: " + split)
    families = TRAIN_FAMILIES if split != "final_validation" else FINAL_FAMILIES
    records = []
    for index in range(count):
        family_index, replica, operations, mode = family_index_for(index, split)
        records.append({
            "index": index,
            "file": f"{index:03d}_{families[family_index]['id']}.in",
            "family_id": families[family_index]["id"],
            "family_index": family_index,
            "replica_index": replica,
            "seed": seed_first + index,
            "operation_count": operations,
            "profile": mode,
        })
    return records


def update_artifact_manifest(split: str, artifact_records: list[dict], freeze_id: str | None = None) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="ascii"))
    if manifest.get("design_sha256") != design_hash():
        raise RuntimeError("manifest design hash mismatch")
    manifest["generator_sha256_at_design_freeze"] = script_hash()
    manifest["artifacts"][split] = {
        "files": artifact_records,
        "stream_count": len(artifact_records),
        "total_operations": sum(item["operation_count"] for item in artifact_records),
    }
    if freeze_id is not None:
        manifest["artifacts"][split]["model_freeze_id"] = freeze_id
    write_json_atomic(MANIFEST_PATH, manifest)


def generate_split(split: str, freeze_id: str | None) -> None:
    ensure_design_files()
    if split == "final_validation" and not freeze_id:
        raise ValueError("final_validation is sealed until a nonempty --freeze-id is supplied")
    if split != "final_validation" and freeze_id:
        raise ValueError("--freeze-id is only valid for final_validation")

    if split == "final_validation":
        freeze_path = DATA_ROOT / "final_validation" / "freeze_id.txt"
        if freeze_path.exists() and freeze_path.read_text(encoding="utf-8").strip() != freeze_id:
            raise RuntimeError("final validation already belongs to another freeze ID")
        if not freeze_path.exists():
            freeze_path.parent.mkdir(parents=True, exist_ok=True)
            freeze_path.write_text(freeze_id + "\n", encoding="utf-8")

    output_dir = DATA_ROOT / split
    output_dir.mkdir(parents=True, exist_ok=True)
    family_list = TRAIN_FAMILIES if split != "final_validation" else FINAL_FAMILIES
    generated_metadata: list[dict] = []
    for record in split_records(split):
        family = family_list[record["family_index"]]
        commands, generated_profile = generate_commands(
            record["seed"], record["operation_count"], family["id"], record["profile"]
        )
        output_path = output_dir / record["file"]
        data = stream_bytes(commands)
        if output_path.exists():
            if output_path.read_bytes() != data:
                raise RuntimeError(f"refusing to overwrite different stream: {output_path}")
        else:
            output_path.write_bytes(data)
        validated = validate_stream(output_path, record["operation_count"])
        generated_metadata.append({
            **record,
            **generated_profile,
            "sha256": validated["sha256"],
            "placement_count": validated["placement_count"],
        })

    update_artifact_manifest(split, generated_metadata, freeze_id)
    if split == "final_validation":
        sidecar = {
            "design_sha256": design_hash(),
            "model_freeze_id": freeze_id,
            "streams": generated_metadata,
        }
        write_json_atomic(DATA_ROOT / split / "manifest.json", sidecar)
    print(f"validated {len(generated_metadata)} {split} streams; design_sha256={design_hash()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init-manifest", action="store_true", help="write the frozen design and data README only")
    parser.add_argument("--split", choices=("train", "calibration", "final_validation"))
    parser.add_argument("--freeze-id", help="required to generate the sealed final validation split")
    args = parser.parse_args()
    if args.init_manifest:
        if args.split or args.freeze_id:
            parser.error("--init-manifest cannot be combined with --split or --freeze-id")
        ensure_design_files()
        print(f"frozen design_sha256={design_hash()}")
        return 0
    if not args.split:
        parser.error("specify --init-manifest or --split")
    try:
        generate_split(args.split, args.freeze_id)
    except (ValueError, RuntimeError, AssertionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
