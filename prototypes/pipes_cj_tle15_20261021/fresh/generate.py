#!/usr/bin/env python3
"""Predeclared exact-equivalence corpus; never executes a solver."""
from collections import deque
from pathlib import Path
import hashlib
import importlib.util
import json
import random
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("pipes_harness", REPO / "tools/pipes_harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
OPEN15 = REPO / "data/pipes/open/15.in"


class Stream:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.commands = []
        self.live = []
        self.positions = {}
        self.lengths = {}
        self.born = {}
        self.oldest = deque()
        self.newest = []
        self.next_pid = 1
        self.cyclic = 0
        self.pinned = set()
        self.scheduled = {}
        self.survivor_deletions = []
        self.last_deleted = None
        self.adjacent_pid_delete_transitions = 0

    def birth(self, length):
        pid = self.next_pid
        self.next_pid += 1
        self.commands.append(length)
        self.positions[pid] = len(self.live)
        self.live.append(pid)
        self.lengths[pid] = length
        self.born[pid] = len(self.commands)
        self.oldest.append(pid)
        self.newest.append(pid)
        return pid

    def remove(self, pid):
        assert pid in self.positions
        self.commands.append(-pid)
        if self.last_deleted is not None and abs(pid - self.last_deleted) == 1:
            self.adjacent_pid_delete_transitions += 1
        self.last_deleted = pid
        index = self.positions.pop(pid)
        last = self.live.pop()
        if index < len(self.live):
            self.live[index] = last
            self.positions[last] = index
        if pid in self.pinned:
            self.survivor_deletions.append({"pid": pid, "born_event": self.born[pid],
                                           "deleted_event": len(self.commands),
                                           "age_events": len(self.commands) - self.born[pid]})
            self.pinned.remove(pid)
        del self.lengths[pid]
        del self.born[pid]

    def choose(self, policy):
        if policy in ("fifo", "lifo"):
            queue = self.oldest if policy == "fifo" else self.newest
            while queue and (queue[0] if policy == "fifo" else queue[-1]) not in self.positions:
                queue.popleft() if policy == "fifo" else queue.pop()
            for pid in (queue if policy == "fifo" else reversed(queue)):
                if pid in self.positions and pid not in self.pinned:
                    return pid
        for _ in range(24):
            if policy == "random_middle":
                pid = sorted(self.live[self.rng.randrange(len(self.live))] for _ in range(3))[1]
            elif policy == "cyclic":
                pid = self.live[self.cyclic % len(self.live)]
                self.cyclic += 1
            else:
                pid = self.live[self.rng.randrange(len(self.live))]
            if pid not in self.pinned:
                return pid
        return next(pid for pid in self.live if pid not in self.pinned)


def length_at(stream, profile):
    ordinal = stream.next_pid - 1
    if profile == "dense_sparse":
        return 1 + (17 * ordinal + stream.rng.randrange(7)) % (40 if (ordinal // 512) % 2 == 0 else 8)
    if profile == "sparse_dense":
        return 1 + (13 * ordinal + stream.rng.randrange(5)) % (8 if (ordinal // 257) % 2 == 0 else 40)
    if profile == "run_boundary":
        blocks = (45, 46, 47, 2047, 2048, 2049)
        offset = ordinal % sum(blocks)
        for index, size in enumerate(blocks):
            if offset < size:
                return (1, 2, 4, 8, 17, 31)[index]
            offset -= size
    if profile == "sparse":
        return (1, 2, 4, 8)[ordinal % 4]
    return 1 + (ordinal * 17 + stream.rng.randrange(11)) % 40


def generate(case):
    stream = Stream(case["seed"])
    prefix = case.get("open15_prefix", 0)
    original_next = None
    if prefix:
        with OPEN15.open() as source:
            next(source)
            source_prefix = [int(next(source)) for _ in range(prefix + 1)]
        for command in source_prefix[:prefix]:
            stream.birth(command) if command > 0 else stream.remove(-command)
        original_next = source_prefix[prefix]
        stream.birth(39 if original_next == 40 else 40)
    if case["family"] == "long_survivors":
        ages = case["survivor_target_ages"]
        for index, age in enumerate(ages):
            pid = stream.birth((index * 7) % 40 + 1)
            stream.pinned.add(pid)
            due = len(stream.commands) + age
            assert due not in stream.scheduled
            stream.scheduled[due] = pid
    n = case["operations"]
    final_refill = max(625, n // 8)
    warm = min(2048, max(128, n // 20))
    batch = []
    pending = deque()
    while len(stream.commands) < n:
        event = len(stream.commands) + 1
        due = stream.scheduled.pop(event, None)
        if due is not None:
            stream.remove(due)
            continue
        if len(stream.commands) >= n - final_refill:
            stream.birth(stream.rng.randint(32, 40))
            continue
        if case["family"] in ("coalescing_runs", "recycling_permuted"):
            if pending:
                stream.remove(pending.popleft())
                continue
            pid = stream.birth(length_at(stream, case["profile"]))
            batch.append(pid)
            if len(batch) == 512:
                removal = batch[:500]
                if case["family"] == "recycling_permuted":
                    stream.rng.shuffle(removal)
                else:
                    # Adjacent PID runs in permuted 20-pipe blocks.
                    blocks = [removal[i:i + 20] for i in range(0, len(removal), 20)]
                    stream.rng.shuffle(blocks)
                    removal = [pid for block in blocks for pid in block]
                pending.extend(removal)
                batch = []
            continue
        if len(stream.live) <= len(stream.pinned) + warm:
            remove = False
        else:
            remove = stream.rng.random() < 0.505
        if remove:
            stream.remove(stream.choose(case["deletion_policy"]))
        else:
            stream.birth(length_at(stream, case["profile"]))
    assert len(stream.commands) == n and stream.commands[-1] > 0 and stream.live
    assert not stream.scheduled and not stream.pinned
    metadata = {"adjacent_pid_delete_transitions": stream.adjacent_pid_delete_transitions,
                "final_live_pipe_count": len(stream.live),
                "survivor_deletions": stream.survivor_deletions,
                "final_append_only_operations": final_refill,
                "first_suffix_command": stream.commands[prefix] if prefix else None,
                "original_next_open15_command": original_next}
    return stream.commands, metadata


def main():
    cases = []
    def add(family, n, policy="random_middle", profile="dense_sparse", **extra):
        cases.append(dict(id=f"fresh-{len(cases) + 1:02d}", seed=20261021 + len(cases),
                          family=family, operations=n, deletion_policy=policy, profile=profile, **extra))
    for policy in ("fifo", "lifo", "random_middle", "cyclic"):
        add("steady_churn", 200000, policy)
    add("coalescing_runs", 200000, profile="sparse_dense")
    add("recycling_permuted", 200000)
    add("long_survivors", 200000, "random_middle", survivor_target_ages=[16, 64, 256, 1024, 4096, 16384, 65536, 70000])
    add("long_survivors", 200000, "cyclic", "sparse_dense", survivor_target_ages=[15, 63, 255, 1023, 4095, 16383, 65535, 65537])
    for prefix, n, policy in zip((16, 17, 31, 65), (5000, 12000, 25000, 50000), ("fifo", "lifo", "random_middle", "cyclic")):
        add("open15_prefix_sibling", n, policy, open15_prefix=prefix)
    for policy, n in zip(("fifo", "lifo", "random_middle", "cyclic"), (5000, 12000, 25000, 50000)):
        add("run_window_boundaries", n, policy, "run_boundary")
    for family, n, profile in (("coalescing_runs", 5000, "sparse"), ("recycling_permuted", 12000, "sparse_dense"),
                               ("coalescing_runs", 25000, "dense"), ("recycling_permuted", 50000, "dense_sparse")):
        add(family, n, profile=profile)
    for policy, n, profile in (("cyclic", 20000, "sparse"), ("random_middle", 30000, "sparse_dense"),
                               ("fifo", 40000, "dense_sparse"), ("lifo", 45000, "sparse_dense")):
        add("independent_profile_switch", n, policy, profile)
    assert len(cases) == 24 and sum(c["operations"] == 200000 for c in cases) == 8
    # Freeze the case plan before generating or reading any validation result.
    (HERE / "plan.json").write_text(json.dumps(cases, indent=2) + "\n")
    out = HERE / "inputs"
    out.mkdir(exist_ok=True)
    records = []
    for case in cases:
        commands, extra = generate(case)
        path = out / (case["id"] + ".in")
        path.write_text("1 " + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
        parsed = harness.parse_test(path)
        assert parsed["operation_count"] == case["operations"]
        assert parsed["final_occupied_length_m"] > 0
        records.append(dict(case, path=str(path.relative_to(REPO)), sha256=parsed["test_sha256"],
                            static_validation="tools.pipes_harness.parse_test: passed", metadata=parsed,
                            volume_ceiling_below_085=parsed["kpi_upper_bound_from_live_volume"] < 0.85,
                            mechanism_metadata=extra))
    manifest = dict(status="fixed_fresh_corpus_static_validation_complete_no_solver_runs", cases=records,
                    total_cases=len(records), total_commands=sum(c["operations"] for c in cases),
                    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    plan_sha256=hashlib.sha256((HERE / "plan.json").read_bytes()).hexdigest(),
                    provenance={"seed_range": [20261021, 20261044],
                                "method": "New Python Random(seed) streams; no solver output, holdout answers, or result-dependent selection.",
                                "reference_generator_read": "tools/generate_pipes_synthetic.py; independent implementation here avoids O(n) list erasure.",
                                "open15_source": "data/pipes/open/15.in", "open15_sha256": hashlib.sha256(OPEN15.read_bytes()).hexdigest(),
                                "open15_use": "Only first16/17/31/65 commands reused for four labeled siblings; immediate next command deliberately differs.",
                                "random_middle_definition": "Median PID of three uniformly sampled live array slots; biased to middle age, not an exact rank query.",
                                "cyclic_definition": "Cyclic traversal of live slots with deterministic swap deletion.",
                                "coverage_limit": "Coalescing/recycling/two-child AVL deletion are input design targets, not proven internal coverage without solver instrumentation.",
                                "volume_limit": "Live-volume KPI ceiling is only an optimistic bound, not evidence KPI>=0.85 is attainable."})
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"cases": len(records), "commands": manifest["total_commands"],
                      "all_static_legal": True, "minimum_volume_ceiling": min(r["metadata"]["kpi_upper_bound_from_live_volume"] for r in records),
                      "manifest": str(HERE / "manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
