#!/usr/bin/env python3
"""Compare causal phase policies on case15 prefixes plus bootstrapped suffixes."""

import csv
import hashlib
import random
import subprocess
import time
from pathlib import Path


ROOT = Path("results/pipes/improvement/case15_fast_candidates/phase_micro")
INPUT = Path("data/pipes/open/15.in")
OUT = ROOT / "micro_replay.csv"
COMMAND_COUNT = 8_192
BLOCK_SIZE = 128
PREFIXES = {"before_shift": 99_999, "after_shift": 150_000}
SEEDS = (1501, 1502, 1503, 1504)
SOLVERS = {
    "baseline": Path("results/pipes/improvement/case15_fast_candidates/bin/baseline"),
    "phase_high_address_tie": ROOT / "bin/phase_high_address_tie",
    "preserve_large_gaps": ROOT / "bin/preserve_large_gaps",
}


class Fenwick:
    def __init__(self, size):
        self.size = size
        self.tree = [0] * (size + 1)

    def add(self, index, delta):
        while index <= self.size:
            self.tree[index] += delta
            index += index & -index

    def prefix(self, index):
        total = 0
        while index > 0:
            total += self.tree[index]
            index -= index & -index
        return total

    def kth(self, rank):
        index = 0
        bit = 1 << (self.size.bit_length() - 1)
        while bit:
            candidate = index + bit
            if candidate <= self.size and self.tree[candidate] < rank:
                index = candidate
                rank -= self.tree[candidate]
            bit >>= 1
        result = index + 1
        if result > self.size:
            raise ValueError("Fenwick rank outside active population")
        return result


def read_input():
    tokens = list(map(int, INPUT.read_text().split()))
    count = tokens[1]
    commands = tokens[2:]
    if len(commands) == count + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != count:
        raise ValueError("case15 declared command count mismatch")
    return commands


def source_suffix_events(commands, start_op):
    tree = Fenwick(200_001)
    active = 0
    next_pid = 0
    events = []
    for zero_index, command in enumerate(commands):
        if command > 0:
            next_pid += 1
            tree.add(next_pid, 1)
            active += 1
            if zero_index >= start_op:
                events.append((1, command, 0.0))
        else:
            pid = -command
            rank_newest = active - tree.prefix(pid)
            fraction = rank_newest / max(1, active - 1)
            if zero_index >= start_op:
                events.append((-1, 0, fraction))
            tree.add(pid, -1)
            active -= 1
    if not events:
        raise ValueError("no source events for phase bootstrap")
    return events


def prefix_state(commands, cut):
    tree = Fenwick(200_001)
    active = 0
    next_pid = 0
    for command in commands[:cut]:
        if command > 0:
            next_pid += 1
            tree.add(next_pid, 1)
            active += 1
        else:
            tree.add(-command, -1)
            active -= 1
    return tree, active, next_pid


def make_trace(commands, source_events, cut, seed):
    tree, active, next_pid = prefix_state(commands, cut)
    generated = []
    rng = random.Random(seed)
    blocks_needed = (COMMAND_COUNT + BLOCK_SIZE - 1) // BLOCK_SIZE
    starts = [rng.randrange(len(source_events) - BLOCK_SIZE + 1)
              for _ in range(blocks_needed)]
    sampled = []
    for start in starts:
        sampled.extend(source_events[start:start + BLOCK_SIZE])
    for kind, length, rank_fraction in sampled[:COMMAND_COUNT]:
        if kind > 0:
            next_pid += 1
            tree.add(next_pid, 1)
            active += 1
            generated.append(length)
        else:
            if active <= 0:
                raise ValueError("bootstrap tried to delete from empty active set")
            rank_newest = int(rank_fraction * (active - 1) + 0.5)
            pid = tree.kth(active - rank_newest)
            tree.add(pid, -1)
            active -= 1
            generated.append(-pid)
    result = commands[:cut] + generated
    digest = hashlib.sha256("\n".join(map(str, result)).encode()).hexdigest()
    return result, digest


def trace_stats(commands):
    alive = [0]
    lengths = [0]
    live = peak = placements = 0
    for command in commands:
        if command > 0:
            placements += 1
            lengths.append(command)
            alive.append(1)
            live += command
            peak = max(peak, live)
        else:
            pid = -command
            if pid <= 0 or pid >= len(alive) or not alive[pid]:
                raise ValueError(f"invalid generated delete PID {pid}")
            alive[pid] = 0
            live -= lengths[pid]
    return placements, peak, live


def run_solver(path, commands):
    payload = "\n".join(map(str, commands + [0])) + "\n"
    start = time.perf_counter()
    run = subprocess.run([str(path)], input=payload, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         check=True)
    elapsed = time.perf_counter() - start
    lines = run.stdout.splitlines()
    if len(lines) != len(commands):
        raise ValueError(f"{path.name}: expected {len(commands)} response lines, got {len(lines)}")
    trench = 0
    for command, line in zip(commands, lines):
        values = line.split()
        if command > 0:
            if len(values) != 2:
                raise ValueError(f"bad placement response: {line!r}")
            trench += int(values[0]) * 20
        elif len(values) != 1:
            raise ValueError(f"bad removal response: {line!r}")
    return trench, elapsed


def main():
    commands = read_input()
    shift_start = next(i for i, c in enumerate(commands) if c > 7)
    source = source_suffix_events(commands, shift_start)
    rows = []
    for prefix_name, cut in PREFIXES.items():
        for seed in SEEDS:
            trace, digest = make_trace(commands, source, cut, seed)
            placements, peak_live, final_live = trace_stats(trace)
            results = {}
            for solver_name, solver in SOLVERS.items():
                trench, elapsed = run_solver(solver, trace)
                results[solver_name] = (trench, elapsed)
            baseline_trench = results["baseline"][0]
            for solver_name, (trench, elapsed) in results.items():
                rows.append({
                    "prefix": prefix_name,
                    "prefix_ops": cut,
                    "seed": seed,
                    "trace_sha256": digest,
                    "continuation_ops": COMMAND_COUNT,
                    "placements": placements,
                    "peak_live_m": peak_live,
                    "final_live_m": final_live,
                    "solver": solver_name,
                    "trench_m": trench,
                    "delta_trench_vs_baseline_m": trench - baseline_trench,
                    "final_kpi": final_live / trench if trench else 0.0,
                    "wall_s": elapsed,
                })
            print(prefix_name, seed, "baseline", baseline_trench,
                  "phase", results["phase_high_address_tie"][0],
                  "preserve", results["preserve_large_gaps"][0],
                  "trace", digest[:12], flush=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
