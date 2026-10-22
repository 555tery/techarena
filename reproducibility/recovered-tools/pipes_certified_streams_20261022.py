#!/usr/bin/env python3
"""Independent Pipes streams with constructive placement certificates.

No import-time writes. generate(output_dir) creates exactly 64 input files plus
manifest.jsonl in a NEW directory. It does not invoke any solver or interactor.
Witnesses exist only in TemporaryDirectory during generation, then are removed.
replay_witness(record, destination) deterministically reconstructs one witness.
All seeds and parameters are fixed in specs(), independently of solver behavior.

Input: 1\nN\ncommand...; positive PID counts only positive commands, starting at 1.
Witness: positive => digs start; negative => start. First placement digs all T.
Offline coordinates are NEVER serialized to .in or manifest.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import BinaryIO

VERSION = "independent-contiguous-exchange-v1-20261022"


@dataclass(frozen=True)
class Spec:
    name: str
    split: str
    seed: int
    n: int
    arena: int
    family: str
    stratum: str
    grammar_order: tuple[str, ...]
    switches: tuple[float, ...]


def specs() -> list[Spec]:
    """24 development + 40 final; held-out scheduler and grammar compositions.

    These are predetermined stream strata, not a statistical population model.
    Final seeds can be sealed by the caller; this public generator is not itself
    a secrecy boundary. Do not use final outcomes to select solver parameters.
    """
    rows = []
    dev_families = ("forward_sweep", "random_windows", "parity_cohort", "renewal_overlap")
    final_families = ("reverse_dyadic", "staggered_waves", "coprime_stride", "two_front_braid", "renewal_bursts")
    dev_scales = (1280, 5120, 20480, 81920, 327680, 655360)
    final_scales = (1920, 7680, 15360, 46080, 122880, 245760, 491520, 614400)
    for split, scales, families, base in (
        ("development", dev_scales, dev_families, 0x22D3A710),
        ("sealed_final", final_scales, final_families, 0x22F1A900),
    ):
        for s, arena in enumerate(scales):
            for f, family in enumerate(families):
                i = len(rows)
                if split == "development":
                    n = (24000, 60000, 200000, 200000, 200000, 200000)[s]
                    grams = ("uniform", "complements", "saw", "tiny_heavy")
                    switches = (0.0, 0.21, 0.47, 0.76)
                else:
                    n = (36000, 90000, 200000, 200000, 200000, 200000, 200000, 200000)[s]
                    grams = ("residue", "geometric", "antiphase", "jitter_pairs", "micro_cohorts")
                    switches = (0.0, 0.11, 0.33, 0.52, 0.84)
                shift = (s + 2 * f) % len(grams)
                grams = grams[shift:] + grams[:shift]
                rows.append(Spec(
                    name=f"{'dev' if split == 'development' else 'final'}_{s:02d}_{f:02d}",
                    split=split, seed=base + 1009 * s + 65537 * f,
                    n=n, arena=arena, family=family,
                    stratum=f"live_capacity_{arena}_n_{n}",
                    grammar_order=grams, switches=switches,
                ))
    assert len(rows) == 64
    return rows


@dataclass
class Pipe:
    start: int
    length: int
    pid: int = 0
    born: int = 0


@dataclass
class Zone:
    start: int
    length: int
    born: int
    pipes: list[Pipe] = field(default_factory=list)


class _Complete(Exception):
    pass


class _Build:
    def __init__(self, spec: Spec, input_file: BinaryIO | None, witness_file: BinaryIO):
        self.s = spec
        self.rng = random.Random(spec.seed)
        self.input_file = input_file
        self.witness_file = witness_file
        self.ih, self.wh = hashlib.sha256(), hashlib.sha256()
        self.count = self.pid = self.F = self.peak = 0
        self.active: dict[int, Pipe] = {}
        self.occupied = bytearray(spec.arena)
        self.zones: list[Zone] = []
        self.txn = self.full_exchanges = self.partial_exchanges = 0
        self.merges = self.splits = self.exchanged_volume = 0
        self.max_exchange = 20 * int(0.06 * spec.arena / 20)
        self.nominal = max(20, 20 * (spec.arena // (80 * 20)))
        self.min_stationary = spec.arena
        self.warmup_n = 0
        self.stationary = False
        self.seen_sizes: set[int] = set()
        self.max_lifetime = self.lifetime_total = self.deletions = 0
        self._input(f"1\n{spec.n}\n".encode())

    def _input(self, value: bytes):
        self.ih.update(value)
        if self.input_file is not None:
            self.input_file.write(value)

    def _room(self):
        if self.count == self.s.n:
            raise _Complete

    def _positive(self, pipe: Pipe):
        self._room()
        a, b = pipe.start, pipe.start + pipe.length
        assert 1 <= pipe.length <= 40 and 0 <= a < b <= self.s.arena
        assert not any(self.occupied[a:b]), "certificate overlap"
        self.occupied[a:b] = b'\1' * pipe.length
        self.pid += 1
        pipe.pid, pipe.born = self.pid, self.count
        self.active[pipe.pid] = pipe
        self._input(f"{pipe.length}\n".encode())
        digs = self.s.arena // 20 if self.pid == 1 else 0
        answer = f"{digs} {a}\n".encode()
        self.witness_file.write(answer)
        self.wh.update(answer)
        self.F += pipe.length
        self.peak = max(self.peak, self.F)
        self.seen_sizes.add(pipe.length)
        self.count += 1
        if self.stationary:
            self.min_stationary = min(self.min_stationary, self.F)

    def _negative(self, pipe: Pipe):
        self._room()
        assert self.active.pop(pipe.pid) is pipe
        a, b = pipe.start, pipe.start + pipe.length
        assert all(self.occupied[a:b]), "certificate invalid deletion"
        self.occupied[a:b] = b'\0' * pipe.length
        self._input(f"{-pipe.pid}\n".encode())
        answer = f"{a}\n".encode()
        self.witness_file.write(answer)
        self.wh.update(answer)
        age = self.count - pipe.born
        self.max_lifetime = max(self.max_lifetime, age)
        self.lifetime_total += age
        self.deletions += 1
        self.F -= pipe.length
        self.count += 1
        if self.stationary:
            self.min_stationary = min(self.min_stationary, self.F)

    def _phase(self) -> int:
        # Grammar switches are measured in stationary commands, excluding warmup.
        progress = max(0, self.count - self.warmup_n) / max(1, self.s.n - self.warmup_n)
        return max(i for i, p in enumerate(self.s.switches) if progress >= p)

    def _partition(self, start: int, length: int, grammar: str) -> list[Pipe]:
        ans, remain, step = [], length, 0
        while remain:
            r, j = self.rng, step
            if grammar == "warmup":
                size = r.randint(25, 40)
            elif grammar == "uniform":
                size = r.randint(1, 40)
            elif grammar == "complements":
                size = (self.txn * 7 + j // 2 * 11) % 39 + 1
                if j % 2:
                    size = 40 - size
            elif grammar == "saw":
                size = 1 + (j * 7 + self.txn * 3) % 40
            elif grammar == "tiny_heavy":
                size = r.randint(1, 7) if (j + self.txn) % 4 else r.randint(32, 40)
            elif grammar == "residue":
                size = r.choice((3, 9, 15, 21, 27, 33, 39))
            elif grammar == "geometric":
                size = min(40, 1 + int(r.expovariate(1 / (5 if self.txn % 2 else 22))))
            elif grammar == "antiphase":
                size = r.choice((1, 2, 3, 4)) if (j // 3 + self.txn) % 2 else r.choice((34, 36, 38, 40))
            elif grammar == "jitter_pairs":
                size = max(1, min(40, (13 if j % 2 else 27) + r.choice((-4, -1, 2, 5))))
            elif grammar == "micro_cohorts":
                size = r.choice((2, 5, 8)) if (j // 8 + self.txn) % 3 else r.choice((29, 31, 37))
            else:
                raise ValueError(grammar)
            size = min(size, remain)
            ans.append(Pipe(start + length - remain, size))
            remain -= size
            step += 1
        assert sum(p.length for p in ans) == length
        return ans

    def _initial(self):
        pos = 0
        while pos < self.s.arena:
            length = min(self.nominal, self.s.arena - pos)
            z = Zone(pos, length, -1)
            z.pipes = self._partition(pos, length, "warmup")
            self.zones.append(z)
            pos += length
        initial = [p for z in self.zones for p in z.pipes]
        assert len(initial) < self.s.n // 3
        self.warmup_n = len(initial)
        self.rng.shuffle(initial)
        for p in initial:
            self._positive(p)
        assert self.F == self.s.arena
        self.stationary = True

    def _choose(self, phase: int) -> tuple[int, int]:
        zs, r, t = self.zones, self.rng, self.txn
        m, family = len(zs), self.s.family
        # A periodic oldest-zone service prevents an intentionally fixed background.
        if t % 3 == 0:
            i = min(range(m), key=lambda j: (zs[j].born, (j * 7919 + t) % m))
        elif family == "forward_sweep":
            i = (t * (1 + phase)) % m
        elif family == "random_windows":
            i = r.randrange(m)
        elif family == "parity_cohort":
            i = (2 * t + (t // max(1, m // 2)) % 2) % m
        elif family == "renewal_overlap":
            i = (t // 5 * 7 + t % 5) % m
        elif family == "reverse_dyadic":
            i = (m - 1 - (t ^ (t >> 1))) % m
        elif family == "staggered_waves":
            i = (t * 5 + (t // max(1, m)) ** 2) % m
        elif family == "coprime_stride":
            stride = max(1, m // 3)
            while math.gcd(stride, m) != 1:
                stride += 1
            i = (t * stride + phase) % m
        elif family == "two_front_braid":
            i = ((t // 2) if t % 2 else (m - 1 - t // 2)) % m
        elif family == "renewal_bursts":
            i = ((t // 9) * 11 + (t % 9) ** 2) % m
        else:
            raise ValueError(family)
        cap = self.max_exchange
        assert zs[i].length <= cap
        j, total = i + 1, zs[i].length
        want = 1 + r.randrange(4 if self.s.split == "development" else 6)
        while j < m and j - i < want and total + zs[j].length <= cap:
            total += zs[j].length
            j += 1
        return i, j

    def _new_zones(self, start: int, length: int, phase: int) -> list[Zone]:
        # Full transactions alternate merging and splitting; boundaries can migrate.
        ans, pos, remaining = [], start, length
        if (self.txn + phase) % 2 == 0:
            return [Zone(start, length, self.txn)]
        low = max(1, self.nominal // 40)
        high = max(low, self.nominal // 10)
        while remaining:
            units = self.rng.randint(low, high)
            if self.s.split == "sealed_final":
                units = max(low, units + (1 if units % 2 == 0 else 0))
            size = min(20 * units, remaining, self.max_exchange)
            ans.append(Zone(pos, size, self.txn))
            pos += size
            remaining -= size
        return ans

    def _exchange(self):
        phase = self._phase()
        i, j = self._choose(phase)
        chosen = self.zones[i:j]
        pipes = [p for z in chosen for p in z.pipes]
        length, start = sum(z.length for z in chosen), chosen[0].start
        assert length <= self.max_exchange
        self.exchanged_volume += length
        # Correlate lifetime with size and transaction cohort; orders vary by split.
        if self.s.split == "development":
            pipes.sort(key=lambda p: ((p.length + self.txn) % 2, p.born, -p.start))
        else:
            pipes.sort(key=lambda p: ((p.pid // (3 + phase)) % 3, -p.length, p.start))
        partial = (self.txn + phase) % (5 if self.s.split == "development" else 7) == 1
        if partial:
            # Deliberately interrupt cohort deletion, retaining interleaved pipes.
            removed = pipes[::2]
            selected = {p.pid for p in removed}
            for p in removed:
                self._negative(p)
            for z in chosen:
                new = [p for p in z.pipes if p.pid not in selected]
                holes = [p for p in z.pipes if p.pid in selected]
                self.rng.shuffle(holes)
                for hole in holes:
                    replacement = self._partition(hole.start, hole.length, self.s.grammar_order[self._phase()])
                    for p in replacement:
                        self._positive(p)
                    new.extend(replacement)
                z.pipes = sorted(new, key=lambda p: p.start)
                # Retained old pipes keep this zone old for the next full exchange.
            self.partial_exchanges += 1
        else:
            for p in pipes:
                self._negative(p)
            zs = self._new_zones(start, length, phase)
            self.merges += max(0, len(chosen) - len(zs))
            self.splits += max(0, len(zs) - len(chosen))
            for z in zs:
                z.pipes = self._partition(z.start, z.length, self.s.grammar_order[self._phase()])
            fresh = [p for z in zs for p in z.pipes]
            self.rng.shuffle(fresh)
            for p in fresh:
                self._positive(p)
            self.zones[i:j] = zs
            self.full_exchanges += 1
        assert self.F == self.s.arena
        self.txn += 1

    def run(self) -> dict:
        self._initial()
        try:
            while True:
                self._exchange()
        except _Complete:
            pass
        assert self.count == self.s.n
        assert self.F >= self.s.arena - self.max_exchange
        assert self.min_stationary >= self.s.arena - self.max_exchange
        assert self.peak == self.s.arena and self.F == sum(p.length for p in self.active.values())
        return {
            "source": Path(__file__).name, "generator_version": VERSION,
            "seed": self.s.seed, "sha256": self.ih.hexdigest(), "n": self.count,
            "F": self.F, "T": self.s.arena, "bound": self.s.arena,
            "bound_definition": "20*ceil(peak_live/20); attained by this witness",
            "attainable_KPI": self.F / self.s.arena, "split": self.s.split,
            "stratum": self.s.stratum, "family": self.s.family,
            "witness_sha256": self.wh.hexdigest(), "spec": asdict(self.s),
            "certificate": {
                "warmup_n": self.warmup_n,
                "stationary_commands": self.count - self.warmup_n,
                "stationary_min_density": self.min_stationary / self.s.arena,
                "max_exchange_volume": self.max_exchange,
                "full_exchanges_completed": self.full_exchanges,
                "partial_exchanges_completed": self.partial_exchanges,
                "zone_merges": self.merges, "zone_splits": self.splits,
                "exchanged_volume_including_last": self.exchanged_volume,
                "distinct_lengths": sorted(self.seen_sizes),
                "deletions": self.deletions, "max_deleted_lifetime_commands": self.max_lifetime,
                "mean_deleted_lifetime_commands": self.lifetime_total / max(1, self.deletions),
                "initial_pipes_still_live": sum(p.born < self.warmup_n for p in self.active.values()),
                "coordinates_in_input": False,
            },
        }


def generate(output_dir: str | Path) -> Path:
    """Create a NEW folder containing 64 .in + manifest.jsonl, with no witnesses.

    A generation error leaves the new directory for inspection; it never replaces
    an existing path. The caller may separately replay witnesses for validation
    with the official interactor, then delete those temporary witness files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest = output_dir / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as mf, tempfile.TemporaryDirectory(prefix="pipes-witness-") as tmp:
        for spec in specs():
            inp = output_dir / f"{spec.name}.in"
            temporary_witness = Path(tmp) / "witness.txt"
            with inp.open("wb") as stream, temporary_witness.open("wb") as witness:
                record = _Build(spec, stream, witness).run()
            record.update(name=spec.name, input=inp.name, source_sha256=source_sha)
            mf.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            mf.flush()
            temporary_witness.unlink()
    return manifest


def replay_witness(record: dict, destination: str | Path) -> Path:
    """Reconstruct one temporary answer file from its manifest record.

    Does not create an input file and never runs a solver/interactor. Checks both
    stream and witness hashes before returning. Parent may use this file solely
    as an offline feasibility certificate with the official interactor.
    """
    raw = dict(record["spec"])
    raw["grammar_order"] = tuple(raw["grammar_order"])
    raw["switches"] = tuple(raw["switches"])
    spec = Spec(**raw)
    destination = Path(destination)
    with destination.open("xb") as witness:
        regenerated = _Build(spec, None, witness).run()
    assert regenerated["sha256"] == record["sha256"]
    assert regenerated["witness_sha256"] == record["witness_sha256"]
    return destination


if __name__ == "__main__":
    # Explicit invocation only; importing this module never generates data.
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="new, nonexistent destination directory")
    args = parser.parse_args()
    print(generate(args.output_dir))
