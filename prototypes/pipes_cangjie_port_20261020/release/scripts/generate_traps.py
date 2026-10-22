#!/usr/bin/env python3
"""Freeze fresh port-equivalence inputs without loading or running a solver.

These are new seeded instances of known mechanisms, not new independent
algorithm families. Labels name intended probes; branch coverage is unmeasured.
"""
from __future__ import annotations

import collections
import hashlib
import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "fresh_tests"
SOURCE_SHA256 = "f7b285eee9d59f443b015de581c4622668dd1a321e0cb9ef00d4baf10412f5db"
FAMILIES = (
    "fragmentation_bounds", "merge_adjacency", "deletion_policy_switches",
    "mc_gap64", "mc_active4096", "geometric46_history2048",
    "dp512_residuals", "uint32_seed_wrap",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Stream:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.commands: list[int] = []
        self.live: dict[int, int] = {}
        self.ids: list[int] = []
        self.positions: dict[int, int] = {}
        self.fifo: collections.deque[int] = collections.deque()
        self.lifo: list[int] = []
        self.next_pid = 1
        self.volume = self.peak_volume = self.peak_count = 0

    def add(self, length: int) -> int:
        assert 1 <= length <= 40
        pid = self.next_pid
        self.next_pid += 1
        self.positions[pid] = len(self.ids)
        self.ids.append(pid)
        self.fifo.append(pid)
        self.lifo.append(pid)
        self.live[pid] = length
        self.commands.append(length)
        self.volume += length
        self.peak_volume = max(self.peak_volume, self.volume)
        self.peak_count = max(self.peak_count, len(self.live))
        return pid

    def delete(self, pid: int):
        assert pid in self.live
        self.commands.append(-pid)
        self.volume -= self.live.pop(pid)
        index = self.positions.pop(pid)
        last = self.ids.pop()
        if index < len(self.ids):
            self.ids[index] = last
            self.positions[last] = index

    def choose(self, policy: str) -> int:
        assert self.live
        if policy == "fifo":
            while self.fifo[0] not in self.live:
                self.fifo.popleft()
            return self.fifo[0]
        if policy == "lifo":
            while self.lifo[-1] not in self.live:
                self.lifo.pop()
            return self.lifo[-1]
        return self.ids[self.rng.randrange(len(self.ids))]


def prelude(s: Stream, family: str, variant: int):
    r = s.rng
    if family == "fragmentation_bounds":
        ids = [s.add(r.choice([7, 11, 19, 23, 29, 37, 40])) for _ in range(360 + 29 * variant)]
        for pid in ids[1::2]:
            s.delete(pid)
        for length in [1, 8, 12, 20, 24, 30, 38, 40] * 17:
            s.add(length)
    elif family == "merge_adjacency":
        # 40m pipes initially leave no remainder. Deletions deliberately include
        # adjacent insertion IDs and opposite orders, without asserting geometry.
        ids = [s.add(40) for _ in range(180)]
        for offset in range(0, 156, 12):
            for j in [4, 6, 5, 9, 8, 7, 1, 2, 3, 0, 10]:
                s.delete(ids[offset + j])
        for length in [39, 1, 38, 2, 37, 3, 40, 17, 23] * 13:
            s.add(length)
    elif family == "deletion_policy_switches":
        for _ in range(200):
            s.add(r.randint(1, 40))
        for policy in ["fifo", "lifo", "random", "lifo", "fifo", "random"]:
            for _ in range(93):
                s.delete(s.choose(policy))
                s.add(r.randint(1, 40))
    elif family == "mc_gap64":
        ids = [s.add(20) for _ in range(130)]
        for pid in ids[0::2]:
            s.delete(pid)
        # 65 disconnected exact 20m holes, then 64/63 in the physical model
        # produced by the initial exact-size sequence; later varied candidates.
        s.add(20)
        s.add(20)
        for length in [9, 11, 8, 12, 7, 13, 6, 14] * 18:
            s.add(length)
        for pid in ids[1::4]:
            if pid in s.live:
                s.delete(pid)
    elif family == "mc_active4096":
        for _ in range(4095):
            s.add(r.choice([8, 12, 20, 28, 32, 40]))
        s.add(17)  # active 4096
        s.add(23)  # active 4097
        s.delete(s.choose("random"))
        s.delete(s.choose("random"))
        for _ in range(81):
            s.delete(s.choose("random"))
        for _ in range(84):
            s.add(r.choice([7, 11, 19, 23, 31, 39]))
    elif family == "geometric46_history2048":
        for length, count in [(2, 45), (4, 46), (8, 47), (16, 46), (32, 47),
                              (3, 45), (6, 46), (12, 47), (24, 46)]:
            for _ in range(count):
                s.add(length)
        for _ in range(1607):
            s.add(1 + ((s.next_pid * 17 + variant) % 40))
        for length in [3, 6, 12, 24]:
            for _ in range(47):
                s.add(length)
            for _ in range(19):
                s.delete(s.choose("fifo"))
    elif family == "dp512_residuals":
        ids = [s.add(40) for _ in range(260)]
        for base in [1, 40, 80, 120, 160]:
            for pid in ids[base:base + 13]:
                s.delete(pid)
        # 520m coalesced blocks, residual targets 511/512/513 after 9/8/7m.
        for length in [9, 8, 7, 39, 1, 37, 3, 31, 11, 23, 17] * 29:
            s.add(length)
    elif family == "uint32_seed_wrap":
        ids = [s.add(20 + (i % 4)) for i in range(290)]
        for pid in ids[1::3]:
            s.delete(pid)
        for length in [2, 3, 7, 13, 19, 23, 29, 31, 37, 40] * 19:
            s.add(length)
        # The reference seed's products wrap modulo 2**32 even at small PID
        # and length values; repeated churn supplies many differing operands.


def build(family: str, seed: int, n: int, variant: int) -> Stream:
    s = Stream(seed)
    prelude(s, family, variant)
    reserve = max(120, n // 20)
    assert len(s.commands) < n - reserve
    phase = 257 + variant * 37
    target = 260 if family != "mc_active4096" else 4096
    if n == 200000 and family == "fragmentation_bounds":
        target = 7500
    while len(s.commands) < n - reserve:
        t = len(s.commands)
        policy = ["fifo", "lifo", "random"][(t // phase) % 3]
        if family == "geometric46_history2048":
            run = [2, 4, 8, 16, 32, 3, 6, 12, 24][(t // (45 + (t // 911) % 3)) % 9]
            length = run if rando(s, 20) else s.rng.randint(1, 40)
        elif family == "dp512_residuals":
            length = [1, 7, 8, 9, 17, 23, 31, 39, 40][s.rng.randrange(9)]
        else:
            length = s.rng.randint(1, 40)
        deletion_probability = 0.58 if len(s.live) > target else 0.39
        if s.live and s.rng.random() < deletion_probability:
            s.delete(s.choose(policy))
        else:
            s.add(length)
    # A substantial final live population avoids empty/near-empty terminal KPI.
    while len(s.commands) < n:
        s.add(1 + ((s.next_pid * 13 + seed) % 40))
    assert s.volume > 0 and len(s.commands) == n <= 200000
    return s


def rando(s: Stream, denominator: int) -> bool:
    return s.rng.randrange(denominator) != 0


def validate(commands: list[int]) -> tuple[int, int, int, int]:
    # Independent bookkeeping pass through the serialized logical events.
    live: dict[int, int] = {}
    next_pid = 1
    volume = peak = peak_count = 0
    for command in commands:
        if command > 0:
            assert 1 <= command <= 40
            live[next_pid] = command
            next_pid += 1
            volume += command
        else:
            assert command < 0 and -command in live
            volume -= live.pop(-command)
        peak = max(peak, volume)
        peak_count = max(peak_count, len(live))
    return volume, peak, len(live), peak_count


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "manifest.json").exists(), "Inputs already frozen; do not overwrite"
    script_hash = sha(Path(__file__).read_bytes())
    cases = []
    for family_index, family in enumerate(FAMILIES):
        for variant in range(4):
            seed = 202610204170001 + family_index * 1009 + variant * 100003
            n = [5201, 13007, 24019, 200000][variant]
            if family == "mc_active4096" and variant == 0:
                n = 8009
            case_id = f"port-{family_index:02d}-{variant}"
            stream = build(family, seed, n, variant)
            metrics = validate(stream.commands)
            assert metrics == (stream.volume, stream.peak_volume, len(stream.live), stream.peak_count)
            raw = (f"1 {n}\n" + "\n".join(map(str, stream.commands)) + "\n").encode()
            filename = case_id + ".in"
            (OUT / filename).write_bytes(raw)
            cases.append({"id": case_id, "file": filename, "family": family,
                "variant": variant, "seed": seed, "operations": n, "weight": 1,
                "sha256": sha(raw), "final_live_volume": metrics[0],
                "peak_live_volume": metrics[1], "final_active_pipes": metrics[2],
                "peak_active_pipes": metrics[3], "final_fill_operations": max(120, n // 20),
                "provenance": "generated_fresh_for_language_port_equivalence_without_solver_outcomes"})
    manifest = {"schema_version": 1, "purpose": "C++ versus native Cangjie port equivalence",
        "frozen_before_first_cangjie_solver_run": True,
        "solver_execution_or_kpi_measurement": False,
        "mechanism_novelty_claim": False,
        "branch_coverage_status": "intended probes only; actual branches not measured",
        "reference_cpp_sha256": SOURCE_SHA256, "generator": "scripts/generate_traps.py",
        "generator_sha256": script_hash, "case_count": len(cases),
        "small_medium_count": 24, "maximum_size_count": 8,
        "input_validation": "all serialized commands checked independently; valid PID lifecycle and lengths",
        "cases": cases}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"case_count": len(cases), "operations": sum(c["operations"] for c in cases),
        "manifest_sha256": sha((OUT / "manifest.json").read_bytes()),
        "generator_sha256": script_hash}))


if __name__ == "__main__":
    main()
