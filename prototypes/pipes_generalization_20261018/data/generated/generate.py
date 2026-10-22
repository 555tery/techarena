#!/usr/bin/env python3
"""Frozen, allocation-policy-blind input generator. No solver is imported or read."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import heapq
import json
from pathlib import Path
import random
import secrets
import shutil
import sys

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Bag:
    def __init__(self):
        self.ids, self.pos = [], {}

    def add(self, x):
        self.pos[x] = len(self.ids)
        self.ids.append(x)

    def remove(self, x):
        p = self.pos.pop(x)
        y = self.ids.pop()
        if p < len(self.ids):
            self.ids[p] = y
            self.pos[y] = p

    def pick(self, rng):
        return self.ids[rng.randrange(len(self.ids))] if self.ids else None

    def __len__(self):
        return len(self.ids)


class State:
    def __init__(self, rng):
        self.rng, self.commands = rng, []
        self.active, self.groups = Bag(), {}
        self.sizes, self.tags = [0], [None]
        self.queue, self.stack, self.due = deque(), [], []
        self.volume = 0

    def add(self, size, tag="background", lifetime=None):
        assert 1 <= size <= 40
        pid = len(self.sizes)
        self.sizes.append(size)
        self.tags.append(tag)
        self.active.add(pid)
        self.groups.setdefault(tag, Bag()).add(pid)
        self.queue.append(pid)
        self.stack.append(pid)
        if lifetime is not None:
            heapq.heappush(self.due, (len(self.commands) + lifetime, pid))
        self.volume += size
        self.commands.append(size)
        return pid

    def pick(self, mode="random", tag=None):
        if tag is not None:
            group = self.groups.get(tag)
            if group and len(group):
                return group.pick(self.rng)
        if mode == "fifo":
            while self.queue and self.queue[0] not in self.active.pos:
                self.queue.popleft()
            return self.queue[0] if self.queue else None
        if mode == "lifo":
            while self.stack and self.stack[-1] not in self.active.pos:
                self.stack.pop()
            return self.stack[-1] if self.stack else None
        if mode == "deadline":
            while self.due and self.due[0][1] not in self.active.pos:
                heapq.heappop(self.due)
            return self.due[0][1] if self.due else self.active.pick(self.rng)
        return self.active.pick(self.rng)

    def delete(self, mode="random", tag=None, pid=None):
        pid = self.pick(mode, tag) if pid is None else pid
        if pid is None:
            return False
        self.active.remove(pid)
        self.groups[self.tags[pid]].remove(pid)
        self.volume -= self.sizes[pid]
        self.commands.append(-pid)
        return True

    def step(self, probability, size, mode="random", tag="background", delete_tag=None, lifetime=None):
        if not len(self.active) or self.rng.random() < probability:
            return self.add(size, tag, lifetime)
        self.delete(mode, delete_tag)
        return None


def phase_at(i, n):
    return sum(i >= x for x in (n // 4, n // 2, 65 * n // 100, 75 * n // 100))


def pareto_int(rng, minimum, maximum, shape=1.35):
    return min(maximum, max(minimum, int(minimum * rng.paretovariate(shape))))


def build_stream(family, n, seed, rep=0):
    """Also accepts tiny n for tests; production lengths come only from design.json."""
    if n < 40 or n > 200000:
        raise ValueError("n must be in [40, 200000]")
    rng = random.Random(seed)
    st = State(rng)
    extras = {}
    balanced = list(range(1, 41))
    rng.shuffle(balanced)
    arrival_no = 0
    burst_end, burst_grow = 0, False
    cohort_heap, cohort_seen = [], set()
    period = max(4, n // 80)
    motif_ids, motif_size, motif_added, motif_deleted, motif_no = [], 0, 0, 0, 0
    micro_queue, micro_pair = [], []
    branch = rep % 4
    if family == "prefix_branch":
        extras.update(branch_id=branch, branch_assignment="rep modulo 4", common_prefix_commands=n // 4)
    for i in range(n):
        p = phase_at(i, n)
        if family == "size_lifetime_inversion":
            small = rng.random() < .5
            size = rng.randint(1, 10) if small else rng.randint(25, 40)
            preferred = "large" if p == 0 else "small"
            st.step([.60, .50, .62, .10, .75][p], size,
                    tag="small" if small else "large",
                    delete_tag=preferred if rng.random() < .88 else None)
        elif family == "fifo_lifo_reversal":
            size = balanced[arrival_no % 40]
            pid = st.step([.58, .58, .58, .20, .58][p], size,
                          mode=["fifo", "lifo", "fifo", "lifo", "fifo"][p])
            if pid is not None:
                arrival_no += 1
        elif family == "renewal_deadlines":
            if i >= burst_end:
                burst_grow = not burst_grow
                scale = 3 if p == 0 else 12
                burst_end = i + pareto_int(rng, scale, max(scale, n // 40))
            probability = .92 if burst_grow else .12
            if p == 3 or i >= 90 * n // 100:
                probability = 0
            minimum = 4 if p == 0 else 40
            lifetime = pareto_int(rng, minimum, max(minimum, n // 5), 1.20)
            mode = "deadline" if p == 0 or p == 3 or rng.random() < .35 else "lifo"
            st.step(probability, rng.randint(1, 40), mode=mode, lifetime=lifetime)
        elif family == "moving_support_aba":
            lo, hi, tag = [(1, 8, "A"), (27, 40, "B"), (1, 8, "A"),
                           (1, 8, "A"), (13, 24, "C")][p]
            preferred = [None, "A", "B", "A", "B"][p]
            st.step([.62, .62, .62, .08, .70][p], rng.randint(lo, hi), tag=tag,
                    delete_tag=preferred if rng.random() < .85 else None)
        elif family == "asynchronous_cohorts":
            cohort = i // period
            tag = f"c{cohort}"
            if cohort not in cohort_seen:
                cohort_seen.add(cohort)
                delay = rng.choice([2, 3, 5, 8] if p == 0 else [1, 4, 7, 11])
                heapq.heappush(cohort_heap, (i + period * delay, tag))
            while cohort_heap and not len(st.groups.get(cohort_heap[0][1], ())):
                # An as-yet-unallocated current cohort must keep its planned retirement.
                if cohort_heap[0][1] == tag:
                    break
                heapq.heappop(cohort_heap)
            target = cohort_heap[0][1] if cohort_heap and cohort_heap[0][0] <= i else None
            survivor = rng.random() < .12
            support = [(1, 10), (11, 25), (26, 40)][cohort % 3]
            probability = [.60, .54, .60, 0, .47][p]
            if i >= 90 * n // 100:
                probability = 0
            st.step(probability, rng.randint(*support), tag="survivor" if survivor else tag,
                    delete_tag=target if rng.random() < .90 else "survivor")
        elif family == "anchor_replacement":
            anchor = p == 0 and rng.random() < .18
            young = p >= 2 and rng.random() < .20
            tag = "old_anchor" if anchor else "young_anchor" if young else "background"
            size = rng.randint(25, 40) if anchor else rng.randint(13, 24) if p == 1 else rng.randint(1, 10)
            target = ["background", "old_anchor", "background", "young_anchor", "background"][p]
            st.step([.60, .54, .60, .08, .70][p], size, tag=tag,
                    delete_tag=target if rng.random() < .94 else None)
        elif family == "avalanche_regrowth":
            epoch = max(12, n // (20 if p == 0 else 35))
            grow = i % epoch < 2 * epoch // 3
            probability = .92 if grow else 0
            if p == 3 or i >= 85 * n // 100:
                probability = 0
            large = (i // epoch + p) % 2
            size = rng.randint(30, 40) if large else rng.randint(1, 6)
            st.step(probability, size, mode="fifo" if p == 0 else "lifo")
        elif family == "reservoir_growth_drain":
            cap = max(4, n // 100)
            probability = (1 if len(st.active) < cap else 0) if p == 0 else [.0, .82, .58, 0, .78][p]
            size = rng.randint(9, 12) if p == 0 else rng.randint(16, 24) if p == 2 else rng.randint(1, 40)
            st.step(probability, size, mode="fifo" if p < 3 else "lifo")
        elif family == "jittered_motifs":
            if p == 3 or i >= 90 * n // 100:
                if not st.delete("fifo"):
                    st.add(1)
                continue
            if motif_added == motif_size and motif_deleted >= max(0, motif_size - 2):
                motif_no += 1
                motif_size = rng.randint(12, 48)
                motif_added = motif_deleted = 0
                motif_ids = []
            if motif_added < motif_size:
                pattern = [3, 17, 6, 14, 9, 11, 20, 5, 15, 8, 12, 1, 19]
                size = max(1, min(40, pattern[motif_added % len(pattern)] + rng.randint(-2, 2)))
                motif_ids.append(st.add(size, f"m{motif_no}"))
                motif_added += 1
            else:
                live = [x for x in motif_ids if x in st.active.pos]  # bounded by 48
                if live:
                    pid = live[0] if p == 0 else live[-1] if p == 1 else max(live, key=lambda x: st.sizes[x]) if p == 2 else rng.choice(live)
                    st.delete(pid=pid)
                elif not st.delete("fifo"):
                    st.add(1)
                motif_deleted += 1
        elif family == "prefix_branch":
            if p == 0:
                probability, mode, size = .60, "random", rng.choice([3, 7, 13, 17, 23, 27, 33, 37])
            else:
                probability = [.72, .42, .56, .80][branch]
                mode = ["fifo", "lifo", "fifo", "lifo"][branch]
                small = (branch + (p == 2)) % 2 == 0
                size = rng.randint(1, 10) if small else rng.randint(25, 40)
                if p == 3:
                    probability, mode = .10, "lifo" if mode == "fifo" else "fifo"
                if branch == 1 and i >= 85 * n // 100:
                    probability = 0
            st.step(probability, size, mode=mode)
        elif family == "micro_rank_bursts":
            cap = [rng.choice([20, 40, 60]), 60, 40, 20, 60][p]
            size = rng.randint(1, 12) if p == 0 else rng.randint(1, 25)
            probability = .80 if (i // 5) % 2 == 0 else .20
            if p == 3 or rep % 2 == 0 and i >= 90 * n // 100:
                probability = 0
            if len(st.active) and (st.volume + size > cap or rng.random() >= probability):
                ranked = sorted(st.active.ids)  # at most 60 live unit objects
                low_rank = rng.randrange(max(1, (len(ranked) + 3) // 4))
                pid = ranked[low_rank] if p == 0 else ranked[-1 - low_rank]
                st.delete(pid=pid)
            else:
                st.add(min(size, cap))
        elif family == "micro_complements":
            if p == 3 or rep % 2 == 1 and i >= 90 * n // 100:
                if not st.delete("random"):
                    st.add(1)
                continue
            if not micro_queue:
                target = rng.choice([20, 40, 60])
                a = rng.randint(max(1, target - 40), min(40, target - 1))
                micro_queue = [a, target - a]
                if p > 0:
                    rng.shuffle(micro_queue)
                micro_pair = []
            if st.volume + micro_queue[0] <= 60:
                micro_pair.append(st.add(micro_queue.pop(0)))
            else:
                candidates = [x for x in micro_pair if x in st.active.pos]
                if candidates and p == 1:
                    st.delete(pid=candidates[-1])
                else:
                    st.delete("random")
        else:
            raise ValueError(f"unknown family: {family}")
    if family == "prefix_branch":
        extras["common_prefix_sha256"] = sha(("\n".join(map(str, st.commands[:n // 4])) + "\n").encode())
        extras["counterfactual_caveat"] = "One branch per independent base; no paired-branch comparison is sampled."
    assert len(st.commands) == n
    return st.commands, extras


def analyse_commands(commands, checkpoints):
    """Independent replay for generator metadata; does not inspect placements or scores."""
    live, next_pid, volume, peak_volume, peak_count = {}, 0, 0, 0, 0
    arrivals = deletions = 0
    lengths = [0] * 41
    snapshots = {}
    checkpoints = set(checkpoints)
    for k, command in enumerate(commands, 1):
        if command > 0:
            if not 1 <= command <= 40:
                raise ValueError("invalid size")
            next_pid += 1
            live[next_pid] = command
            volume += command
            lengths[command] += 1
            arrivals += 1
        else:
            if command == 0 or -command not in live:
                raise ValueError("invalid deletion")
            volume -= live.pop(-command)
            deletions += 1
        peak_volume, peak_count = max(peak_volume, volume), max(peak_count, len(live))
        if k in checkpoints:
            snapshots[str(k)] = dict(live_volume=volume, live_count=len(live),
                                     live_volume_sections_lower_bound=(volume + 19) // 20,
                                     zero_final_volume=volume == 0,
                                     max_live_volume=peak_volume, max_live_count=peak_count,
                                     arrivals=arrivals, deletions=deletions,
                                     arrival_size_histogram=lengths[1:].copy())
    return snapshots


def encoded_input(commands):
    return ("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n").encode()


def read_freeze(path):
    raw = path.read_bytes()
    freeze = json.loads(raw)
    expected = {"generator_sha256": sha(Path(__file__).read_bytes()),
                "design_sha256": sha((HERE / "design.json").read_bytes())}
    if freeze.get("schema_version") != 1 or freeze.get("design_approved") is not True:
        raise ValueError("freeze must explicitly approve schema version 1 design")
    for key, value in expected.items():
        if freeze.get(key) != value:
            raise ValueError(f"freeze mismatch: {key}")
    solvers = freeze.get("solver_sha256", {})
    for label in ("trial22", "bf", "ss"):
        digest = solvers.get(label, "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"missing frozen solver hash: {label}")
    return freeze, sha(raw), expected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output exists; refusing overwrite")
    if not args.freeze.is_file():
        parser.error("freeze is missing; no seeds or inputs generated")
    try:
        freeze, freeze_hash, hashes = read_freeze(args.freeze)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    design = json.loads((HERE / "design.json").read_text())
    # Entropy is drawn only after all freeze checks have succeeded.
    master_seed = secrets.token_hex(32)
    base_seeds = [secrets.token_hex(32) for _ in range(48)]
    manifest = dict(schema_version=1, master_seed=master_seed,
                    seed_derivation="independent secrets.token_hex(32) per base; master is provenance entropy, not a derivation key",
                    freeze_sha256=freeze_hash, freeze=freeze, **hashes,
                    design=design, bases=[], cases=[])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "bases").mkdir()
    (args.output / "tests").mkdir()
    # Persist entropy before generation; a crash leaves an explicitly incomplete dataset.
    (args.output / "seeds.json").write_text(json.dumps(dict(master_seed=master_seed, base_seeds=base_seeds), indent=2) + "\n")
    (args.output / "STATUS").write_text("INCOMPLETE\n")
    shutil.copyfile(args.freeze, args.output / "freeze.json")
    shutil.copyfile(HERE / "design.json", args.output / "design.json")
    shutil.copyfile(Path(__file__), args.output / "generate.py")
    for fidx, spec in enumerate(design["families"]):
        for rep, n in enumerate(design["micro_lengths"] if spec["scale"] == "micro" else design["long_lengths"]):
            base_id = f"{fidx + 1:02d}_{spec['id']}_r{rep}"
            seed = base_seeds[4 * fidx + rep]
            commands, extras = build_stream(spec["id"], n, int(seed, 16), rep)
            cuts = [n * fraction // 100 for fraction in design["stop_percentages"]]
            boundaries = [n // 4, n // 2, 65 * n // 100, 75 * n // 100]
            stats = analyse_commands(commands, cuts + boundaries)
            payload = encoded_input(commands)
            base_path = f"bases/{base_id}.txt"
            (args.output / base_path).write_bytes(payload)
            base = dict(base_id=base_id, family=spec["id"], rep=rep, replicate=rep, seed=seed, n=n,
                        path=base_path, sha256=sha(payload), parameters=spec,
                        phase_boundaries=boundaries, checkpoints=stats, **extras)
            manifest["bases"].append(base)
            for percent, role, cut in zip(design["stop_percentages"], design["stop_roles"], cuts):
                payload = encoded_input(commands[:cut])
                test_id = f"{base_id}_p{percent:03d}"
                test_path = f"tests/{test_id}.txt"
                (args.output / test_path).write_bytes(payload)
                manifest["cases"].append(dict(test_id=test_id, base_id=base_id, family=spec["id"],
                                               seed=seed, cutpoint=cut, cutoff_percent=percent,
                                               replicate=rep, stop_fraction=percent / 100,
                                               stop_role=role, cutpoint_role=role,
                                               file=test_path, path=test_path, sha256=sha(payload),
                                               stats=stats[str(cut)]))
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (args.output / "STATUS").write_text("COMPLETE\n")
    print(json.dumps(dict(output=str(args.output), bases=48, tests=240,
                          manifest_sha256=sha((args.output / "manifest.json").read_bytes()))))


if __name__ == "__main__":
    sys.exit(main())
