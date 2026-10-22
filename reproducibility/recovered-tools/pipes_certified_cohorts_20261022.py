#!/usr/bin/env python3
"""Supplemental 12-development + 20-final Pipes cohort streams.

No import-time generation. Depends only on the newly written companion
pipes_certified_streams_20261022.py for the protocol writer/bitmap verifier.
No old inputs, solver, results, benchmark, or compiler are inspected or invoked.

20 mutable corridors, each H=C/2, occupy T=10C. Each ordinary transaction
removes two corridors and fills them in a pair-interleaved PID order. Thus each
corridor subsequently has stride-2 PID deletions, followed by a long uniform
positive run. Early interruptions temporarily renew another corridor and resume
the original run. At most 3H=0.15T can be absent, so F/T >= .85 throughout the
stationary workload, including an arbitrary terminal cut. No terminal filler.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_CORE_PATH = Path(__file__).with_name("pipes_certified_streams_20261022.py")
_name = "pipes_independent_core_20261022"
if _name not in sys.modules:
    _loader = importlib.util.spec_from_file_location(_name, _CORE_PATH)
    core = importlib.util.module_from_spec(_loader)
    sys.modules[_name] = core
    _loader.loader.exec_module(core)
else:
    core = sys.modules[_name]

VERSION = "independent-paired-corridor-cohorts-v1-20261022"
DIVISORS = (12, 14, 15, 16, 18, 20, 21, 24, 28, 30, 35, 36, 40, 4, 5, 6, 7, 8, 9, 10)


def specs():
    rows = []
    dev_families = ("grow_reset", "saw_recovery", "delayed_cascade", "two_cohort")
    final_families = ("grow_reverse_weave", "palindromic_bursts", "residue_returns", "delayed_saw", "alternating_horizons")
    for split, scales, families, seed_base in (
        ("development", (1, 2, 4), dev_families, 0x22C0D100),
        ("sealed_final", (3, 5, 7, 8), final_families, 0x22C0F900),
    ):
        for s, scale in enumerate(scales):
            for f, family in enumerate(families):
                C = 10080 * scale
                rows.append(core.Spec(
                    name=f"cohort_{'dev' if split == 'development' else 'final'}_{s:02d}_{f:02d}",
                    split=split, seed=seed_base + 1009 * s + 65537 * f,
                    n=120000 if split == "development" and s == 0 else 200000,
                    arena=10 * C, family=family,
                    stratum=f"paired_corridors_capacity_{10*C}_scale_{scale}",
                    grammar_order=tuple(str(x) for x in DIVISORS),
                    switches=(0.0, 0.22, 0.51, 0.79) if split == "development" else (0.0, 0.13, 0.37, 0.58, 0.87),
                ))
    assert len(rows) == 32
    return rows


class _Cohorts(core._Build):
    def __init__(self, spec, input_file, witness_file):
        super().__init__(spec, input_file, witness_file)
        self.H = spec.arena // 20
        self.max_exchange = 3 * self.H
        self.corridors = [core.Zone(i * self.H, self.H, -1) for i in range(20)]
        self.max_same_positive_run = self.same_positive_run = 0
        self.previous_length = None
        self.max_stride2_deletions = self.stride2_deletions = 0
        self.previous_delete_pid = None
        self.interruptions = self.growing_transactions = 0
        self.last_served = [-1] * 20
        self.touched = set()
        self.positive_history = []
        self.close_count_growing_blocks = 0

    def _finish_positive(self):
        if self.previous_length is None:
            return
        if len(self.positive_history) >= 2:
            (la, ca), (lb, cb) = self.positive_history[-2:]
            if la < lb < self.previous_length and min(ca, cb) >= 64 and self.same_positive_run >= 64 and max(ca, cb) <= 1.10 * min(ca, cb):
                self.close_count_growing_blocks += 1
        self.positive_history.append((self.previous_length, self.same_positive_run))
        self.positive_history = self.positive_history[-2:]
        self.previous_length = None
        self.same_positive_run = 0

    def _positive(self, pipe):
        super()._positive(pipe)
        if self.previous_length is not None and self.previous_length != pipe.length:
            self._finish_positive()
        self.same_positive_run = self.same_positive_run + 1 if self.previous_length == pipe.length else 1
        self.previous_length = pipe.length
        self.max_same_positive_run = max(self.max_same_positive_run, self.same_positive_run)
        self.previous_delete_pid = None
        self.stride2_deletions = 0

    def _negative(self, pipe):
        super()._negative(pipe)
        self._finish_positive()
        self.stride2_deletions = self.stride2_deletions + 1 if self.previous_delete_pid is not None and pipe.pid - self.previous_delete_pid == 2 else 1
        self.previous_delete_pid = pipe.pid
        self.max_stride2_deletions = max(self.max_stride2_deletions, self.stride2_deletions)
        self.previous_length = None
        self.same_positive_run = 0

    def _uniform(self, z, length):
        assert z.length % length == 0
        return [core.Pipe(z.start + i * length, length) for i in range(z.length // length)]

    def _remove(self, z):
        for p in sorted(z.pipes, key=lambda p: p.pid):
            self._negative(p)
        z.pipes = []

    def _fill_one(self, z, length):
        fresh = self._uniform(z, length)
        self.rng.shuffle(fresh)
        for p in fresh:
            self._positive(p)
            z.pipes.append(p)
        z.born = self.txn

    def _pair_fill(self, a, b, length, interrupt=False):
        left, right = self._uniform(a, length), self._uniform(b, length)
        self.rng.shuffle(left)
        self.rng.shuffle(right)
        # Alternating PIDs map into separate contiguous corridors, in random order.
        fresh = [(z, p) for pa, pb in zip(left, right) for z, p in ((a, pa), (b, pb))]
        cut = 2 * self.rng.randint(4, 31) if interrupt else -1
        for k, (z, p) in enumerate(fresh):
            if k == cut:
                other = [i for i in range(20) if self.corridors[i] is not a and self.corridors[i] is not b]
                ri = min(other, key=lambda i: (self.last_served[i], (i * 17 + self.txn) % 23))
                remote = self.corridors[ri]
                self._remove(remote)
                larger = [x for x in DIVISORS if x > length]
                remote_length = self.rng.choice(larger or DIVISORS[:6])
                self._fill_one(remote, remote_length)
                self.last_served[ri] = self.txn
                self.touched.add(ri)
                self.partial_exchanges += 1
                self.interruptions += 1
            self._positive(p)
            z.pipes.append(p)
        a.born = b.born = self.txn

    def _initial(self):
        initial_length = self.rng.choice((20, 24, 28, 30, 35, 36, 40))
        self.warmup_n = self.s.arena // initial_length
        assert self.warmup_n < self.s.n // 3
        order = list(range(20))
        self.rng.shuffle(order)
        for j in range(0, 20, 2):
            self._pair_fill(self.corridors[order[j]], self.corridors[order[j+1]], initial_length)
        assert self.F == self.s.arena
        self.stationary = True

    def _target_length(self, phase):
        t, family, d = self.txn, self.s.family, DIVISORS
        if t < 10:
            return (12, 14, 15, 16, 18, 20, 21, 24, 28, 30)[t]
        if family in ("grow_reset", "grow_reverse_weave"):
            idx = (t + 3 * phase) % len(d)
        elif family in ("saw_recovery", "palindromic_bursts"):
            k = (t + phase * 5) % (2 * len(d) - 2)
            idx = k if k < len(d) else 2 * len(d) - 2 - k
        elif family in ("delayed_cascade", "residue_returns"):
            idx = (t // 2 + 7 * phase + (t % 2) * 3) % len(d)
        elif family in ("two_cohort", "delayed_saw"):
            idx = (t * 2 + (t // 5) + phase) % len(d)
        else:
            idx = (t // 3 + 4 * (t % 3) + phase * 2) % len(d)
        return d[idx]

    def _exchange(self):
        phase = self._phase()
        # Always serve an oldest corridor; no permanent or intentionally fixed base.
        first = min(range(20), key=lambda i: (self.last_served[i], (i * 13 + phase) % 23))
        remaining = [i for i in range(20) if i != first]
        if self.s.split == "development":
            second = min(remaining, key=lambda i: (self.last_served[i], abs(i - first)))
        else:
            second = min(remaining, key=lambda i: (self.last_served[i], (i - first - 7 - phase) % 20))
        a, b = self.corridors[first], self.corridors[second]
        old_length = max(p.length for z in (a, b) for p in z.pipes)
        length = self._target_length(phase)
        self.growing_transactions += int(length > old_length)
        self._remove(a)
        self._remove(b)
        interrupt = self.txn >= 4 and (self.txn + phase) % (3 if self.s.split == "development" else 4) == 1
        self._pair_fill(a, b, length, interrupt)
        self.last_served[first] = self.last_served[second] = self.txn
        self.touched.update((first, second))
        self.exchanged_volume += 2 * self.H
        self.full_exchanges += 1
        self.txn += 1
        assert self.F == self.s.arena

    def run(self):
        record = super().run()
        self._finish_positive()
        record["source"] = Path(__file__).name
        record["generator_version"] = VERSION
        record["certificate"].update(
            corridor_count=20, corridor_volume=self.H,
            max_same_length_positive_run=self.max_same_positive_run,
            max_stride2_pid_deletion_run=self.max_stride2_deletions,
            interrupted_positive_runs=self.interruptions,
            growing_transactions=self.growing_transactions,
            close_count_growing_blocks=self.close_count_growing_blocks,
            close_count_definition="three increasing uniform lengths; each run>=64; preceding two counts within 10%",
            distinct_corridors_renewed=len(self.touched),
            fixed_background=False,
        )
        assert self.max_same_positive_run >= 64
        assert self.max_stride2_deletions >= 8
        assert self.close_count_growing_blocks >= 1
        assert len(self.touched) == 20
        assert record["certificate"]["initial_pipes_still_live"] == 0
        return record


def generate(output_dir):
    """Create 32 .in + manifest.jsonl in a NEW directory; erase temp witnesses."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    core_sha = hashlib.sha256(_CORE_PATH.read_bytes()).hexdigest()
    manifest = output_dir / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as mf, tempfile.TemporaryDirectory(prefix="pipes-cohort-witness-") as tmp:
        for spec in specs():
            inp = output_dir / f"{spec.name}.in"
            wp = Path(tmp) / "witness.txt"
            with inp.open("wb") as stream, wp.open("wb") as witness:
                record = _Cohorts(spec, stream, witness).run()
            record.update(name=spec.name, input=inp.name, source_sha256=source_sha, companion_source_sha256=core_sha)
            mf.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            mf.flush()
            wp.unlink()
    return manifest


def replay_witness(record, destination):
    raw = dict(record["spec"])
    raw["grammar_order"] = tuple(raw["grammar_order"])
    raw["switches"] = tuple(raw["switches"])
    spec = core.Spec(**raw)
    destination = Path(destination)
    with destination.open("xb") as witness:
        regenerated = _Cohorts(spec, None, witness).run()
    assert regenerated["sha256"] == record["sha256"]
    assert regenerated["witness_sha256"] == record["witness_sha256"]
    return destination


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    args = parser.parse_args()
    print(generate(args.output_dir))
