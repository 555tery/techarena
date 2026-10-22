#!/usr/bin/env python3
"""Generate predeclared synthetic Pipes streams for baseline-router-v1.

The generator uses only Python's standard library and a specified SplitMix64
PRNG. Final-validation files remain sealed until --freeze-id is provided.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import sys
from pathlib import Path


SOURCE = Path(__file__).resolve()
PROJECT = SOURCE.parents[1]
REPO = SOURCE.parents[3]
DATA = PROJECT / "data"
MANIFEST = DATA / "manifest.json"
DESIGN_FILE = DATA / "design_prerun.json"
README = DATA / "README.md"
MASK64 = (1 << 64) - 1
U64 = 1 << 64


TRAIN_FAMILIES = [
    {
        "id": "uniform_random_steady",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "uniform random active PID",
    },
    {
        "id": "fifo_uniform",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "oldest active PID",
    },
    {
        "id": "lifo_uniform",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "newest active PID",
    },
    {
        "id": "bimodal_short_long",
        "length_rule": "equal mixture of uniform 1..5 and uniform 32..40",
        "deletion_rule": "uniform random active PID",
    },
    {
        "id": "ascending_descending_phases",
        "length_rule": "four equal operation phases across ranges 1..8, 9..16, 17..28, 33..40; direction alternates by replica",
        "deletion_rule": "uniform random active PID",
    },
    {
        "id": "additive_size_runs_policy_sweep",
        "length_rule": "same-size runs of 256 placements; run value advances additively by 3 modulo 40 with 10% +/-1 noise",
        "deletion_rule": "replicas 6/7 use FIFO/LIFO; shorter replicas cover random/FIFO/LIFO/longest",
    },
    {
        "id": "geometric_size_runs_policy_sweep",
        "length_rule": "same-size runs of 256 placements on ladder 1,2,4,8,16,32,40, with additive +2 cycle offsets",
        "deletion_rule": "replicas 6/7 use FIFO/random; shorter replicas cover LIFO/FIFO/random/longest",
    },
    {
        "id": "mixed_additive_geometric_runs",
        "length_rule": "256-placement runs alternate geometric ladder values and additive run values; 15% +/-1 noise",
        "deletion_rule": "replicas 6/7 use random/longest; shorter replicas cover FIFO/LIFO/random/longest",
    },
]


FINAL_FAMILIES = [
    {
        "id": "cohort_lifetimes_survivor_stranding",
        "length_rule": "mostly shared uniform size within 128-placement cohort, with 25% independent lengths",
        "deletion_rule": "oldest cohort first; 8% cohort anchors protected for 1024 operations",
        "arrival_rule": "time-homogeneous within assigned growth/bounded profile",
    },
    {
        "id": "abrupt_size_and_policy_regimes",
        "length_rule": "four equal operation phases: 1..6, 35..40, 7..18, 19..34",
        "deletion_rule": "simultaneous phase changes: random, newest, oldest, longest",
        "arrival_rule": "time-homogeneous within assigned growth/bounded profile",
    },
    {
        "id": "sawtooth_bursts_persistent_anchors",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "2048-operation fill/drain cycles; 8% anchors protected for 12288 operations",
        "arrival_rule": "first half fill-biased and second half drain-biased",
    },
    {
        "id": "heavy_tailed_age_mixture_lifetimes",
        "length_rule": "65% 1..5, 25% 6..20, 10% 21..40",
        "deletion_rule": "70% choose oldest among eight random active samples, otherwise random",
        "arrival_rule": "time-homogeneous within assigned growth/bounded profile",
    },
    {
        "id": "permuted_narrow_alphabet_longest_first",
        "length_rule": "seeded permutation of four consecutive lengths, repeated in 32-placement blocks",
        "deletion_rule": "longest active pipe first, ties by oldest PID",
        "arrival_rule": "time-homogeneous within assigned growth/bounded profile",
    },
    {
        "id": "cyclic_demand_delayed_cohort_deletes",
        "length_rule": "size ranges cycle over four 450-operation phases",
        "deletion_rule": "prefer cohorts at least 1200 operations old during delete-heavy phase",
        "arrival_rule": "1800-operation cycle; first 1200 add-biased, last 600 delete-biased",
    },
    {
        "id": "stationary_geometric_bursts_random_removal",
        "length_rule": "uniform integer 1..40",
        "deletion_rule": "uniform random active PID",
        "arrival_rule": "time-homogeneous alternating add/delete bursts with geometric run lengths, mean 20 capped at 256",
    },
    {
        "id": "alternating_fifo_lifo_epochs",
        "length_rule": "uniform integer 1..40, independent of deletion epochs",
        "deletion_rule": "FIFO in even 512-operation epochs, LIFO in odd epochs",
        "arrival_rule": "time-homogeneous within assigned growth/bounded profile",
    },
]


DESIGN = {
    "schema": "pipes-baseline-router-v1-synthetic-design",
    "revision": "prerun-2026-10-17-r1",
    "stream_format": {
        "header": "1 <n>",
        "commands": "one signed integer per line; positive 1..40 inserts, negative PID deletes",
        "terminator": "one trailing 0 outside n",
        "weight": 1,
    },
    "constraints": {
        "n_max": 200000,
        "length_min": 1,
        "length_max": 40,
        "delete_only_live_pid": True,
        "last_counted_operation_is_insert": True,
        "positive_final_occupancy": True,
        "live_profiles": {
            "growth": "time-invariant positive-drift arrival/deletion probabilities; require nontrivial live-set growth",
            "bounded": "live count held between max(20, cap//3) and cap; final insert may reach cap+1",
            "cap": "min(3000, max(300, floor(n/8)))",
        },
    },
    "prng": {
        "algorithm": "SplitMix64",
        "bounded_integer_sampling": "uint64 rejection sampling",
        "seeds": {
            "train": {"first": 82412000, "count": 64, "stride": 1},
            "calibration": {"first": 82422000, "count": 16, "stride": 1},
            "final_validation": {"first": 82432000, "count": 24, "stride": 1},
        },
    },
    "splits": {
        "train": {
            "count": 64,
            "families": TRAIN_FAMILIES,
            "streams_per_family": 8,
            "operations_per_family": {"replicas_0_to_5": 4000, "replicas_6_to_7": 16000},
            "profile_assignment": "even replica=bounded, odd replica=growth",
        },
        "calibration": {
            "count": 16,
            "families": TRAIN_FAMILIES,
            "streams_per_family": 2,
            "operations_per_stream": 8000,
            "profile_assignment": "(family_index + replica_index) parity: even=bounded, odd=growth",
        },
        "final_validation": {
            "count": 24,
            "families": FINAL_FAMILIES,
            "streams_per_family": 3,
            "operations_per_stream": [12000, 30000, 200000],
            "profile_assignment": "(family_index + replica_index) parity: even=bounded, odd=growth",
            "generation": "sealed until nonempty root model freeze ID is supplied",
        },
    },
    "evaluation_rules": {
        "manifest_and_family_rules_fixed_before_solver_metrics": True,
        "final_inputs_not_generated_before_freeze_id": True,
        "no_official_inputs_or_platform_access": True,
        "do_not_adapt_final_family_rules_to_router_outputs": True,
    },
}


class SplitMix64:
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
        limit = U64 - U64 % stop
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
            j = self.below(index + 1)
            values[index], values[j] = values[j], values[index]


class State:
    def __init__(self):
        self.active: list[int] = []
        self.position: list[int] = [-1]
        self.length: list[int] = [0]
        self.alive = bytearray([0])
        self.insert_op: list[int] = [-1]
        self.anchor_until: list[int] = [-1]
        self.cohorts: list[list[int]] = []
        self.cohort_offsets: list[int] = []
        self.cohort_scan = 0
        self.oldest_heap: list[int] = []
        self.newest_heap: list[int] = []
        self.longest_heap: list[tuple[int, int]] = []
        self.live_length = 0
        self.peak_live_count = 0
        self.peak_live_length = 0
        self.abrupt_phase = 0

    @property
    def live_count(self) -> int:
        return len(self.active)

    @property
    def placements(self) -> int:
        return len(self.length) - 1

    def insert(self, length: int, op: int, cohort: int, anchor_until: int) -> None:
        pid = len(self.length)
        self.length.append(length)
        self.alive.append(1)
        self.insert_op.append(op)
        self.anchor_until.append(anchor_until)
        self.position.append(len(self.active))
        self.active.append(pid)
        self.live_length += length
        self.peak_live_count = max(self.peak_live_count, len(self.active))
        self.peak_live_length = max(self.peak_live_length, self.live_length)
        heapq.heappush(self.oldest_heap, pid)
        heapq.heappush(self.newest_heap, -pid)
        heapq.heappush(self.longest_heap, (-length, pid))
        if cohort >= 0:
            while len(self.cohorts) <= cohort:
                self.cohorts.append([])
                self.cohort_offsets.append(0)
            self.cohorts[cohort].append(pid)

    def remove(self, pid: int) -> None:
        if pid <= 0 or pid >= len(self.alive) or not self.alive[pid]:
            raise ValueError("attempted to remove absent PID")
        index = self.position[pid]
        last = self.active[-1]
        self.active[index] = last
        self.position[last] = index
        self.active.pop()
        self.position[pid] = -1
        self.alive[pid] = 0
        self.live_length -= self.length[pid]

    def random_pid(self, rng: SplitMix64) -> int:
        return self.active[rng.below(len(self.active))]

    def oldest_pid(self) -> int:
        while self.oldest_heap:
            pid = heapq.heappop(self.oldest_heap)
            if self.alive[pid]:
                return pid
        raise ValueError("oldest requested on empty live set")

    def newest_pid(self) -> int:
        while self.newest_heap:
            pid = -heapq.heappop(self.newest_heap)
            if self.alive[pid]:
                return pid
        raise ValueError("newest requested on empty live set")

    def longest_pid(self) -> int:
        while self.longest_heap:
            _, pid = heapq.heappop(self.longest_heap)
            if self.alive[pid]:
                return pid
        raise ValueError("longest requested on empty live set")

    def cohort_pid(self, op: int, minimum_age: int = 0) -> int | None:
        while self.cohort_scan < len(self.cohorts):
            members = self.cohorts[self.cohort_scan]
            offset = self.cohort_offsets[self.cohort_scan]
            while offset < len(members):
                pid = members[offset]
                if not self.alive[pid] or self.anchor_until[pid] > op:
                    offset += 1
                    self.cohort_offsets[self.cohort_scan] = offset
                    continue
                if op - self.insert_op[pid] < minimum_age:
                    self.cohort_offsets[self.cohort_scan] = offset
                    return None
                offset += 1
                self.cohort_offsets[self.cohort_scan] = offset
                return pid
            self.cohort_scan += 1
        return None


class BurstMode:
    def __init__(self):
        self.remaining = 0
        self.adding = True

    def next(self, rng: SplitMix64, growth: bool) -> bool:
        if self.remaining == 0:
            self.adding = rng.chance(2, 3) if growth else rng.chance(1, 2)
            run = 1
            while run < 256 and rng.chance(1, 20):
                run += 1
            self.remaining = run
        self.remaining -= 1
        return self.adding


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def design_sha() -> str:
    return hashlib.sha256(canonical(DESIGN)).hexdigest()


def generator_sha() -> str:
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def initial_manifest() -> dict:
    return {
        "design": DESIGN,
        "design_sha256": design_sha(),
        "generator_sha256_at_design_freeze": generator_sha(),
        "artifacts": {"train": None, "calibration": None, "final_validation": None},
    }


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2).encode("ascii") + b"\n")
    temp.replace(path)


def ensure_design() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    expected_design = {"design": DESIGN, "design_sha256": design_sha()}
    for path, expected in ((DESIGN_FILE, expected_design), (MANIFEST, initial_manifest())):
        if path.exists():
            old = json.loads(path.read_text(encoding="ascii"))
            if path == DESIGN_FILE:
                if old != expected:
                    raise RuntimeError(f"refusing to replace a different design: {path}")
            elif old.get("design") != DESIGN or old.get("design_sha256") != design_sha():
                raise RuntimeError(f"manifest design mismatch: {path}")
            elif old.get("generator_sha256_at_design_freeze") != generator_sha():
                raise RuntimeError(f"generator differs from frozen hash: {path}")
        else:
            write_json(path, expected)
    if not README.exists():
        README.write_text(
            f"""# Pipes baseline-router-v1 synthetic data

Схема зафиксирована до solver metrics. Design SHA-256: `{design_sha()}`.

Train содержит 64 потока: для каждого из восьми семейств шесть потоков по 4000 команд и два по 16000. Calibration содержит 16 потоков по 8000 команд на тех же семействах. Final validation заранее описан как 24 потока из восьми новых семейств по 12000, 30000 и 200000 команд; его входы будут созданы только после model freeze ID root.

Заголовок потока имеет вид `1 n`, затем идут `n` команд и отдельный завершающий `0`. Все входы генерируются локально из записанных seed. Перед записью каждый поток проверяется через локальный `parse_test` и собственный валидатор PID, длины, формата и положительной конечной загрузки.

Не меняйте seed, семейства, размеры, профиль или PRNG после фиксации design hash. Новая схема должна получить отдельную версию.
""",
            encoding="utf-8",
        )


def bounded_cap(n: int) -> int:
    return min(3000, max(300, n // 8))


def stream_profile(index: int, split: str) -> str:
    if split == "train":
        replica = index % 8
        return "growth" if replica % 2 else "bounded"
    family, replica = divmod(index, 2 if split == "calibration" else 3)
    return "bounded" if (family + replica) % 2 == 0 else "growth"


def record_spec(split: str, index: int) -> dict:
    if split == "train":
        family_index, replica = divmod(index, 8)
        n = 4000 if replica < 6 else 16000
        first_seed = 82412000
        family = TRAIN_FAMILIES[family_index]
    elif split == "calibration":
        family_index, replica = divmod(index, 2)
        n = 8000
        first_seed = 82422000
        family = TRAIN_FAMILIES[family_index]
    elif split == "final_validation":
        family_index, replica = divmod(index, 3)
        n = (12000, 30000, 200000)[replica]
        first_seed = 82432000
        family = FINAL_FAMILIES[family_index]
    else:
        raise ValueError("unknown split " + split)
    return {
        "index": index,
        "file": f"{index:03d}_{family['id']}.in",
        "family_id": family["id"],
        "family_index": family_index,
        "replica_index": replica,
        "seed": first_seed + index,
        "operation_count": n,
        "profile": stream_profile(index, split),
    }


def sample_range(rng: SplitMix64, lo: int, hi: int) -> int:
    return lo + rng.below(hi - lo + 1)


def sample_length(family: str, op: int, n: int, placement: int, rng: SplitMix64,
                  state: State, replica: int, narrow: list[int], seed: int) -> int:
    if family in ("uniform_random_steady", "fifo_uniform", "lifo_uniform",
                  "sawtooth_bursts_persistent_anchors", "stationary_geometric_bursts_random_removal",
                  "alternating_fifo_lifo_epochs"):
        return sample_range(rng, 1, 40)
    if family == "bimodal_short_long":
        return sample_range(rng, 1, 5) if rng.chance(1, 2) else sample_range(rng, 32, 40)
    if family == "ascending_descending_phases":
        phase = min(3, op * 4 // n)
        ranges = [(1, 8), (9, 16), (17, 28), (33, 40)]
        if replica % 2:
            ranges.reverse()
        return sample_range(rng, *ranges[phase])
    if family == "additive_size_runs_policy_sweep":
        block = (placement - 1) // 256
        value = 1 + ((seed % 11 + block * 3) % 40)
        if rng.chance(1, 10):
            value += -1 if rng.chance(1, 2) else 1
        return min(40, max(1, value))
    if family == "geometric_size_runs_policy_sweep":
        block = (placement - 1) // 256
        ladder = [1, 2, 4, 8, 16, 32, 40]
        cycle, position = divmod(block, len(ladder))
        value = min(40, ladder[position] + 2 * cycle)
        return value
    if family == "mixed_additive_geometric_runs":
        block = (placement - 1) // 256
        if block % 2 == 0:
            ladder = [1, 2, 4, 8, 16, 32, 40]
            value = ladder[(block // 2) % len(ladder)]
        else:
            value = min(40, 2 + (((seed % 13) + (block // 2) * 4) % 39))
        if rng.chance(15, 100):
            value += -1 if rng.chance(1, 2) else 1
        return min(40, max(1, value))
    if family == "cohort_lifetimes_survivor_stranding":
        cohort = (placement - 1) // 128
        if cohort < len(state.cohorts) and state.cohorts[cohort] and rng.chance(3, 4):
            return state.length[state.cohorts[cohort][0]]
        return sample_range(rng, 1, 40)
    if family == "abrupt_size_and_policy_regimes":
        ranges = [(1, 6), (35, 40), (7, 18), (19, 34)]
        return sample_range(rng, *ranges[min(3, op * 4 // n)])
    if family == "heavy_tailed_age_mixture_lifetimes":
        pick = rng.below(100)
        if pick < 65:
            return sample_range(rng, 1, 5)
        if pick < 90:
            return sample_range(rng, 6, 20)
        return sample_range(rng, 21, 40)
    if family == "permuted_narrow_alphabet_longest_first":
        return narrow[((placement - 1) // 32) % len(narrow)]
    if family == "cyclic_demand_delayed_cohort_deletes":
        ranges = [(1, 5), (8, 14), (25, 32), (15, 24)]
        phase = (op % 1800) // 450
        return sample_range(rng, *ranges[phase])
    raise ValueError("no length rule for family " + family)


def add_probability(family: str, op: int, mode: str, burst: BurstMode | None,
                    rng: SplitMix64) -> int:
    if family == "sawtooth_bursts_persistent_anchors":
        return 8200 if op % 2048 < 1024 else 4500
    if family == "cyclic_demand_delayed_cohort_deletes":
        return 7200 if op % 1800 < 1200 else 2500
    if family == "stationary_geometric_bursts_random_removal":
        assert burst is not None
        return 10000 if burst.next(rng, mode == "growth") else 0
    return 6800 if mode == "growth" else 5000


def policy_for(family: str, replica: int) -> str:
    if family == "uniform_random_steady" or family == "bimodal_short_long" or family == "ascending_descending_phases":
        return "random"
    if family == "fifo_uniform":
        return "fifo"
    if family == "lifo_uniform":
        return "lifo"
    if family == "additive_size_runs_policy_sweep":
        return ("random", "fifo", "lifo", "longest", "random", "fifo", "fifo", "lifo")[replica]
    if family == "geometric_size_runs_policy_sweep":
        return ("lifo", "fifo", "random", "longest", "random", "lifo", "fifo", "random")[replica]
    if family == "mixed_additive_geometric_runs":
        return ("fifo", "lifo", "random", "longest", "fifo", "random", "random", "longest")[replica]
    return "random"


def choose_delete(family: str, replica: int, op: int, state: State, rng: SplitMix64,
                  delay: int) -> int:
    if family in ("additive_size_runs_policy_sweep", "geometric_size_runs_policy_sweep",
                  "mixed_additive_geometric_runs"):
        policy = policy_for(family, replica)
    elif family == "abrupt_size_and_policy_regimes":
        policy = ("random", "lifo", "fifo", "longest")[state.abrupt_phase]
    elif family == "cohort_lifetimes_survivor_stranding":
        return state.cohort_pid(op) or state.random_pid(rng)
    elif family == "sawtooth_bursts_persistent_anchors":
        for _ in range(min(24, state.live_count)):
            pid = state.random_pid(rng)
            if state.anchor_until[pid] <= op:
                return pid
        return state.random_pid(rng)
    elif family == "heavy_tailed_age_mixture_lifetimes":
        if rng.chance(7, 10):
            sample = [state.random_pid(rng) for _ in range(min(8, state.live_count))]
            return max(sample, key=lambda pid: (state.insert_op[pid], -pid))
        return state.random_pid(rng)
    elif family == "permuted_narrow_alphabet_longest_first":
        policy = "longest"
    elif family == "cyclic_demand_delayed_cohort_deletes":
        candidate = state.cohort_pid(op, delay)
        return candidate if candidate is not None else state.random_pid(rng)
    elif family == "stationary_geometric_bursts_random_removal":
        policy = "random"
    elif family == "alternating_fifo_lifo_epochs":
        policy = "fifo" if (op // 512) % 2 == 0 else "lifo"
    else:
        policy = policy_for(family, replica)
    if policy == "random":
        return state.random_pid(rng)
    if policy == "fifo":
        return state.oldest_pid()
    if policy == "lifo":
        return state.newest_pid()
    if policy == "longest":
        return state.longest_pid()
    raise ValueError("unknown deletion policy " + policy)


def generate(seed: int, n: int, family: str, replica: int, profile: str) -> tuple[list[int], dict]:
    if not 1 <= n <= 200000:
        raise ValueError("n outside [1, 200000]")
    rng = SplitMix64(seed)
    state = State()
    burst = BurstMode() if family == "stationary_geometric_bursts_random_removal" else None
    cap = bounded_cap(n)
    lower = max(20, cap // 3)
    cohort_width = 128
    delayed_age = 1200
    narrow_start = 1 + rng.below(34)
    narrow = list(range(narrow_start, narrow_start + 4))
    rng.shuffle(narrow)
    commands: list[int] = []
    for op in range(n):
        state.abrupt_phase = min(3, op * 4 // n)
        if op == n - 1:
            add = True
        elif profile == "bounded" and state.live_count <= lower:
            add = True
        elif profile == "bounded" and state.live_count >= cap:
            add = False
        else:
            add = rng.below(10000) < add_probability(family, op, profile, burst, rng)
            if not state.active:
                add = True
            if family == "cyclic_demand_delayed_cohort_deletes" and profile == "growth" and op < delayed_age:
                add = True
        if add:
            placement = state.placements + 1
            length = sample_length(family, op, n, placement, rng, state, replica, narrow, seed)
            cohort = (placement - 1) // cohort_width if family in (
                "cohort_lifetimes_survivor_stranding", "cyclic_demand_delayed_cohort_deletes"
            ) else -1
            anchor_until = -1
            if family == "cohort_lifetimes_survivor_stranding" and rng.chance(8, 100):
                anchor_until = op + 1024
            elif family == "sawtooth_bursts_persistent_anchors" and rng.chance(8, 100):
                anchor_until = op + 12288
            commands.append(length)
            state.insert(length, op, cohort, anchor_until)
        else:
            if not state.active:
                raise AssertionError("delete selected with empty live set")
            pid = choose_delete(family, replica, op, state, rng, delayed_age)
            commands.append(-pid)
            state.remove(pid)
    if state.live_count == 0 or state.live_length <= 0 or commands[-1] <= 0:
        raise AssertionError("invalid zero-occupancy EOF")
    if profile == "growth" and state.live_count < max(2, n // 100):
        raise AssertionError("growth profile did not retain a growing live set")
    if profile == "bounded" and state.peak_live_count > cap + 1:
        raise AssertionError("bounded profile exceeded its live-set cap")
    return commands, {
        "profile": profile,
        "bounded_live_cap": cap if profile == "bounded" else None,
        "peak_live_count": state.peak_live_count,
        "final_live_count": state.live_count,
    }


def stream_bytes(commands: list[int]) -> bytes:
    lines = [f"1 {len(commands)}", *(str(x) for x in commands), "0"]
    return ("\n".join(lines) + "\n").encode("ascii")


def validate(path: Path, expected_n: int) -> dict:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.pipes_harness import parse_test

    parsed = parse_test(path)
    if parsed["operation_count"] != expected_n:
        raise ValueError("harness parser returned unexpected operation count")
    tokens = path.read_text(encoding="ascii").split()
    if len(tokens) != expected_n + 3 or tokens[-1] != "0":
        raise ValueError("bad header/command/sentinel count")
    commands = [int(token) for token in tokens[2:-1]]
    if len(commands) != expected_n or commands[-1] <= 0:
        raise ValueError("last counted operation must be a positive insertion")
    alive: set[int] = set()
    lengths: dict[int, int] = {}
    occupied = 0
    peak = 0
    next_pid = 1
    for command in commands:
        if command > 0:
            if not 1 <= command <= 40:
                raise ValueError("invalid insertion length")
            alive.add(next_pid)
            lengths[next_pid] = command
            occupied += command
            peak = max(peak, occupied)
            next_pid += 1
        else:
            pid = -command
            if pid not in alive:
                raise ValueError("deletion references absent PID")
            alive.remove(pid)
            occupied -= lengths[pid]
    if not alive or occupied <= 0 or peak <= 0:
        raise ValueError("zero final occupancy or peak volume")
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "operation_count": expected_n,
        "placement_count": next_pid - 1,
        "final_live_count": len(alive),
        "final_occupied_length_m": occupied,
        "peak_live_pipe_length_m": peak,
    }


def specs(split: str) -> list[dict]:
    count = {"train": 64, "calibration": 16, "final_validation": 24}[split]
    return [record_spec(split, index) for index in range(count)]


def record_artifacts(split: str, records: list[dict], freeze_id: str | None) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    if manifest.get("design_sha256") != design_sha():
        raise RuntimeError("design hash mismatch in manifest")
    if manifest.get("generator_sha256_at_design_freeze") != generator_sha():
        raise RuntimeError("generator hash mismatch in manifest")
    entry = {
        "files": records,
        "stream_count": len(records),
        "total_operations": sum(record["operation_count"] for record in records),
    }
    if freeze_id is not None:
        entry["model_freeze_id"] = freeze_id
    manifest["artifacts"][split] = entry
    write_json(MANIFEST, manifest)


def generate_split(split: str, freeze_id: str | None) -> None:
    ensure_design()
    if split == "final_validation" and not freeze_id:
        raise ValueError("final_validation is sealed until --freeze-id is provided")
    if split != "final_validation" and freeze_id:
        raise ValueError("--freeze-id is reserved for final_validation")
    out = DATA / split
    if split == "final_validation":
        stamp = out / "freeze_id.txt"
        if stamp.exists() and stamp.read_text(encoding="utf-8").strip() != freeze_id:
            raise RuntimeError("final validation is already tied to another freeze ID")
        out.mkdir(parents=True, exist_ok=True)
        if not stamp.exists():
            stamp.write_text(freeze_id + "\n", encoding="utf-8")
    else:
        out.mkdir(parents=True, exist_ok=True)

    family_list = TRAIN_FAMILIES if split != "final_validation" else FINAL_FAMILIES
    artifacts = []
    for spec in specs(split):
        family = family_list[spec["family_index"]]["id"]
        commands, coverage = generate(spec["seed"], spec["operation_count"], family,
                                       spec["replica_index"], spec["profile"])
        path = out / spec["file"]
        payload = stream_bytes(commands)
        if path.exists():
            if path.read_bytes() != payload:
                raise RuntimeError(f"refusing to overwrite different stream: {path}")
        else:
            path.write_bytes(payload)
        checked = validate(path, spec["operation_count"])
        artifacts.append({
            **spec,
            **coverage,
            "sha256": checked["sha256"],
            "placement_count": checked["placement_count"],
        })
    record_artifacts(split, artifacts, freeze_id)
    if split == "final_validation":
        write_json(out / "manifest.json", {
            "design_sha256": design_sha(),
            "model_freeze_id": freeze_id,
            "streams": artifacts,
        })
    print(f"validated {len(artifacts)} {split} streams; design_sha256={design_sha()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init-design", action="store_true", help="write design and manifest before data generation")
    parser.add_argument("--split", choices=("train", "calibration", "final_validation"))
    parser.add_argument("--freeze-id", help="required for sealed final_validation")
    args = parser.parse_args()
    if args.init_design:
        if args.split or args.freeze_id:
            parser.error("--init-design cannot be combined with split options")
        ensure_design()
        print(f"design_sha256={design_sha()}; generator_sha256={generator_sha()}")
        return 0
    if not args.split:
        parser.error("select --init-design or --split")
    try:
        generate_split(args.split, args.freeze_id)
    except (ValueError, RuntimeError, AssertionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
