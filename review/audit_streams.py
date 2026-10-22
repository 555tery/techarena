#!/usr/bin/env python3
"""Independent interactive protocol and interval-invariant audit for Pipes.

This script compiles no downloaded executable and has no third-party runtime
dependencies. It sends one command at a time, waits for the corresponding
newline-terminated response, and validates the response against an independent
sparse interval model of the official interactor.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import selectors
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


MAX_COMMANDS = 200_000
MAX_TRENCH = 100_000_000
PIPE_LENGTHS = range(1, 41)


@dataclass
class TestCase:
    name: str
    weight: float
    commands: list[int]


def parse_test(path: Path) -> TestCase:
    values = path.read_text().split()
    if len(values) < 2:
        raise ValueError(f"{path}: missing weight or command count")
    weight = float(values[0])
    n = int(values[1])
    if n < 0 or n > MAX_COMMANDS:
        raise ValueError(f"{path}: invalid command count {n}")
    if len(values) not in (2 + n, 3 + n):
        raise ValueError(f"{path}: expected {n} commands, got {len(values) - 2}")
    commands = list(map(int, values[2:2 + n]))
    if len(values) == 3 + n and int(values[-1]) != 0:
        raise ValueError(f"{path}: trailing token is not sentinel 0")
    validate_command_stream(commands, path.name)
    return TestCase(path.name, weight, commands)


def validate_command_stream(commands: list[int], name: str) -> None:
    if len(commands) > MAX_COMMANDS:
        raise ValueError(f"{name}: exceeds {MAX_COMMANDS} commands")
    active: set[int] = set()
    next_pid = 1
    for index, command in enumerate(commands, 1):
        if command == 0 or command < -MAX_COMMANDS:
            raise ValueError(f"{name}: invalid operation {command} at {index}")
        if command > 0:
            if command not in PIPE_LENGTHS:
                raise ValueError(f"{name}: pipe length {command} outside [1,40]")
            active.add(next_pid)
            next_pid += 1
        else:
            pid = -command
            if pid not in active:
                raise ValueError(f"{name}: removal of inactive/future PID {pid} at {index}")
            active.remove(pid)


@dataclass
class IntervalNode:
    start: int
    end: int
    pid: int
    priority: int
    left: Optional["IntervalNode"] = None
    right: Optional["IntervalNode"] = None


def _split(root: Optional[IntervalNode], key: int):
    if root is None:
        return None, None
    if root.start < key:
        root.right, other = _split(root.right, key)
        return root, other
    other, root.left = _split(root.left, key)
    return other, root


def _merge(left: Optional[IntervalNode], right: Optional[IntervalNode]):
    if left is None:
        return right
    if right is None:
        return left
    if left.priority > right.priority:
        left.right = _merge(left.right, right)
        return left
    right.left = _merge(left, right.left)
    return right


def _insert(root: Optional[IntervalNode], node: IntervalNode):
    if root is None:
        return node
    if node.priority > root.priority:
        node.left, node.right = _split(root, node.start)
        return node
    if node.start < root.start:
        root.left = _insert(root.left, node)
    else:
        root.right = _insert(root.right, node)
    return root


def _delete(root: Optional[IntervalNode], key: int):
    if root is None:
        raise KeyError(key)
    if key == root.start:
        return _merge(root.left, root.right)
    if key < root.start:
        root.left = _delete(root.left, key)
    else:
        root.right = _delete(root.right, key)
    return root


class SparseIntervals:
    """Treap of occupied half-open intervals, keyed by start coordinate."""

    def __init__(self):
        self.root: Optional[IntervalNode] = None
        self._serial = 1

    def _priority(self) -> int:
        # SplitMix64 gives reproducible, well-distributed treap priorities.
        x = self._serial + 0x9E3779B97F4A7C15
        self._serial += 1
        x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9 & ((1 << 64) - 1)
        x = (x ^ (x >> 27)) * 0x94D049BB133111EB & ((1 << 64) - 1)
        return x ^ (x >> 31)

    def predecessor(self, key: int) -> Optional[IntervalNode]:
        cur, best = self.root, None
        while cur is not None:
            if cur.start < key:
                best, cur = cur, cur.right
            else:
                cur = cur.left
        return best

    def successor(self, key: int) -> Optional[IntervalNode]:
        cur, best = self.root, None
        while cur is not None:
            if cur.start >= key:
                best, cur = cur, cur.left
            else:
                cur = cur.right
        return best

    def at(self, key: int) -> Optional[IntervalNode]:
        cur = self.root
        while cur is not None:
            if key == cur.start:
                return cur
            cur = cur.left if key < cur.start else cur.right
        return None

    def insert(self, start: int, end: int, pid: int) -> None:
        prev = self.predecessor(start)
        nxt = self.successor(start)
        if prev is not None and prev.end > start:
            raise ValueError(f"pipe {pid} overlaps PID {prev.pid}")
        if nxt is not None and end > nxt.start:
            raise ValueError(f"pipe {pid} overlaps PID {nxt.pid}")
        if self.at(start) is not None:
            raise ValueError(f"duplicate interval start {start}")
        node = IntervalNode(start, end, pid, self._priority())
        self.root = _insert(self.root, node)

    def remove(self, start: int, pid: int) -> IntervalNode:
        node = self.at(start)
        if node is None or node.pid != pid:
            raise ValueError(f"no occupied interval for PID {pid} at {start}")
        self.root = _delete(self.root, start)
        return node


class InteractiveAuditor:
    def __init__(self, binary: Path, per_reply_timeout: float = 2.0):
        self.binary = binary
        self.per_reply_timeout = per_reply_timeout
        self.selector = selectors.DefaultSelector()
        self.output_buffer = bytearray()
        self.next_pid = 1
        self.pipes: list[Optional[tuple[int, int]]] = [None]
        self.occupied = SparseIntervals()
        self.trench_length = 0
        self.occupied_length = 0
        self.responses = 0

    def _read_line(self, proc: subprocess.Popen, test_name: str) -> bytes:
        deadline = time.monotonic() + self.per_reply_timeout
        while True:
            newline = self.output_buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self.output_buffer[:newline])
                del self.output_buffer[:newline + 1]
                return line.rstrip(b"\r")
            if proc.poll() is not None:
                tail = bytes(self.output_buffer)
                raise ValueError(f"{test_name}: solver exited before reply; pending={tail!r}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{test_name}: no flushed response within {self.per_reply_timeout}s")
            self.selector.register(proc.stdout, selectors.EVENT_READ)
            events = self.selector.select(remaining)
            self.selector.unregister(proc.stdout)
            if not events:
                raise TimeoutError(f"{test_name}: no flushed response within {self.per_reply_timeout}s")
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise ValueError(f"{test_name}: stdout closed before expected reply")
            self.output_buffer.extend(chunk)

    @staticmethod
    def _parse_answer(line: bytes, count: int, case_name: str, op_index: int) -> list[int]:
        try:
            parts = line.decode("ascii").split()
            if len(parts) != count:
                raise ValueError(f"expected {count} integer(s), got {len(parts)} token(s): {line!r}")
            if any(part.startswith(("+", "-")) and len(part) == 1 for part in parts):
                raise ValueError(f"malformed integer token in {line!r}")
            return [int(part, 10) for part in parts]
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"{case_name}: malformed reply at command {op_index}: {exc}") from exc

    def _apply(self, command: int, answer: list[int], case_name: str, op_index: int) -> None:
        if command > 0:
            digs, start = answer
            if not (0 <= digs <= MAX_TRENCH and 0 <= start <= MAX_TRENCH):
                raise ValueError(f"{case_name}: command {op_index}: N or D outside [0,{MAX_TRENCH}]")
            new_length = self.trench_length + digs * 20
            if new_length > MAX_TRENCH:
                raise ValueError(f"{case_name}: command {op_index}: trench {new_length} exceeds {MAX_TRENCH}")
            end = start + command
            if end > new_length:
                raise ValueError(f"{case_name}: command {op_index}: pipe ends at {end}, trench is {new_length}")
            pid = self.next_pid
            self.occupied.insert(start, end, pid)
            if pid != len(self.pipes):
                raise AssertionError("PID accounting failure")
            self.pipes.append((start, command))
            self.next_pid += 1
            self.trench_length = new_length
            self.occupied_length += command
        elif command < 0:
            [start] = answer
            pid = -command
            if not (0 <= start <= MAX_TRENCH):
                raise ValueError(f"{case_name}: command {op_index}: removal coordinate outside range")
            if pid <= 0 or pid >= len(self.pipes) or self.pipes[pid] is None:
                raise ValueError(f"{case_name}: command {op_index}: invalid removal PID {pid}")
            expected_start, length = self.pipes[pid]
            if start != expected_start:
                raise ValueError(f"{case_name}: command {op_index}: PID {pid} at {expected_start}, solver returned {start}")
            node = self.occupied.remove(start, pid)
            if node.end - node.start != length:
                raise AssertionError("occupied interval and PID table disagree")
            self.pipes[pid] = None
            self.occupied_length -= length

    def run(self, case: TestCase) -> dict:
        stderr_file = tempfile.TemporaryFile()
        proc = subprocess.Popen(
            [str(self.binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=stderr_file, bufsize=0,
        )
        try:
            for op_index, command in enumerate(case.commands, 1):
                try:
                    proc.stdin.write(f"{command}\n".encode("ascii"))
                    proc.stdin.flush()
                except (BrokenPipeError, OSError) as exc:
                    raise ValueError(f"{case.name}: solver closed stdin at command {op_index}") from exc
                count = 2 if command > 0 else 1
                line = self._read_line(proc, case.name)
                answer = self._parse_answer(line, count, case.name, op_index)
                self._apply(command, answer, case.name, op_index)
                self.responses += 1

            proc.stdin.write(b"0\n")
            proc.stdin.flush()
            proc.stdin.close()
            deadline = time.monotonic() + 2.0
            trailing = bytearray(self.output_buffer)
            self.output_buffer.clear()
            while proc.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"{case.name}: solver did not terminate after sentinel 0")
                self.selector.register(proc.stdout, selectors.EVENT_READ)
                events = self.selector.select(min(remaining, 0.05))
                self.selector.unregister(proc.stdout)
                if events:
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if chunk:
                        trailing.extend(chunk)
                        if len(trailing) > 4096:
                            raise ValueError(f"{case.name}: excessive stdout after sentinel 0")
            # Drain bytes already buffered in the pipe after process exit.
            while True:
                self.selector.register(proc.stdout, selectors.EVENT_READ)
                events = self.selector.select(0)
                self.selector.unregister(proc.stdout)
                if not events:
                    break
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                trailing.extend(chunk)
                if len(trailing) > 4096:
                    break
            if trailing:
                raise ValueError(f"{case.name}: unexpected stdout after sentinel 0: {bytes(trailing[:160])!r}")
            if proc.returncode != 0:
                raise ValueError(f"{case.name}: solver exited with status {proc.returncode}")
            if self.trench_length <= 0:
                raise ValueError(f"{case.name}: official interactor rejects empty trench")
            kpi = self.occupied_length / self.trench_length
            return {
                "name": case.name,
                "commands": len(case.commands),
                "responses": self.responses,
                "dug_m": self.trench_length,
                "occupied_m": self.occupied_length,
                "kpi": kpi,
                "weighted_score": kpi * case.weight,
                "verdict": "OK",
            }
        except Exception:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            raise
        finally:
            stderr_file.seek(0)
            err = stderr_file.read()
            stderr_file.close()
            proc.stdout.close()
            self.selector.close()
            if err:
                sys.stderr.write(err.decode("utf-8", errors="replace")[-4000:])


def make_random_case(seed: int, n: int, mode: str = "mixed") -> TestCase:
    """Generate a legal sequence without reproducing any official test pattern."""
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for _ in range(n):
        delete_probability = 0.47 if mode == "fragment" else 0.32
        if active and rng.random() < delete_probability:
            # Bias toward old PIDs occasionally to challenge stale PID mappings.
            if rng.random() < 0.5:
                i = rng.randrange(len(active))
            else:
                i = rng.randrange(max(1, len(active) // 5))
            pid = active.pop(i)
            commands.append(-pid)
            continue
        if mode == "short":
            length = rng.choices([1, 2, 3, 4, 5, 10, 20, 40], [28, 18, 13, 9, 8, 8, 8, 8])[0]
        elif mode == "long":
            length = rng.choices([1, 2, 5, 10, 19, 20, 21, 39, 40], [3, 3, 5, 9, 9, 14, 12, 20, 25])[0]
        elif mode == "fragment":
            length = rng.randint(1, 40)
        else:
            length = rng.randint(1, 40)
        commands.append(length)
        active.append(next_pid)
        next_pid += 1
    validate_command_stream(commands, f"random-{seed}-{mode}")
    return TestCase(f"random-{seed}-{mode}", 1.0, commands)


def make_coalescing_case(seed: int, rounds: int = 1200) -> TestCase:
    """Create adjacent removals, partial reuse and later coalescing opportunities."""
    rng = random.Random(seed)
    commands: list[int] = []
    live: list[int] = []
    next_pid = 1
    # Burst inserts create neighboring segments regardless of exact coordinates.
    for i in range(rounds):
        length = 1 + ((i * 17 + seed) % 40)
        commands.append(length)
        live.append(next_pid)
        next_pid += 1
    # Remove runs of neighboring insertion PIDs, retaining separators. The actual
    # placement policy may put them elsewhere, but this systematically exercises
    # repeated free-interval merges and PID stability without using open-test data.
    for base in range(0, rounds, 11):
        for pid in live[base:base + 7]:
            commands.append(-pid)
        for _ in range(rng.randint(1, 5)):
            commands.append(rng.randint(1, 40))
            live.append(next_pid)
            next_pid += 1
    # Remove every still-live pipe in shuffled order so endpoint and interior
    # merges, including a large tail merge, are all encountered.
    remaining = [pid for pid in live if -pid not in commands]
    rng.shuffle(remaining)
    commands.extend(-pid for pid in remaining)
    validate_command_stream(commands, f"coalesce-{seed}")
    return TestCase(f"coalesce-{seed}", 1.0, commands)


def make_lifetime_case(seed: int, n: int, discipline: str) -> TestCase:
    """Generate legal streams with different pipe-lifetime distributions."""
    rng = random.Random(seed)
    commands: list[int] = []
    active: dict[int, int] = {}
    next_pid = 1
    for step in range(n):
        if active and rng.random() < 0.43:
            pids = list(active)
            if discipline == "fifo":
                pid = min(pids)
            elif discipline == "lifo":
                pid = max(pids)
            elif discipline == "random-delete":
                pid = rng.choice(pids)
            elif discipline == "short-lived-small":
                # Short pipes are preferentially removed, creating size-biased
                # lifetime distributions while keeping every deletion legal.
                pid = rng.choices(pids, weights=[41 - active[p] for p in pids])[0]
            elif discipline == "short-lived-large":
                pid = rng.choices(pids, weights=[active[p] for p in pids])[0]
            else:
                raise ValueError(f"unknown lifetime discipline {discipline}")
            commands.append(-pid)
            del active[pid]
        else:
            phase = step * 4 // max(1, n)
            if phase == 0:
                length = rng.randint(1, 5)
            elif phase == 1:
                length = rng.randint(32, 40)
            elif phase == 2:
                length = rng.choice([1, 19, 20, 21, 39, 40])
            else:
                length = rng.randint(1, 40)
            commands.append(length)
            active[next_pid] = length
            next_pid += 1
    validate_command_stream(commands, f"lifetime-{seed}-{discipline}")
    return TestCase(f"lifetime-{seed}-{discipline}", 1.0, commands)


def make_alternating_holes_case(seed: int, width: int = 800) -> TestCase:
    """Produce alternating occupied/free runs, then pack mixed lengths into holes."""
    rng = random.Random(seed)
    commands: list[int] = []
    first_batch = list(range(1, width + 1))
    for _ in first_batch:
        commands.append(20)
    anchors = []
    for i, pid in enumerate(first_batch):
        if i % 2 == 0:
            commands.append(-pid)
        else:
            anchors.append(pid)
    for length in ([20] * (width // 3) + [40] * (width // 8) + [1, 39, 21, 19] * (width // 24)):
        commands.append(length)
    rng.shuffle(anchors)
    commands.extend(-pid for pid in anchors)
    # The second wave checks that newly opened holes and the free tail can both
    # be consumed after many old PIDs have become inactive.
    for _ in range(width // 2):
        commands.append(rng.choice([1, 2, 19, 20, 21, 39, 40]))
    validate_command_stream(commands, f"alternating-holes-{seed}")
    return TestCase(f"alternating-holes-{seed}", 1.0, commands)


def make_tail_and_pid_case(seed: int, batch: int = 1200) -> TestCase:
    """Free a changing tail, allocate again, and retain stable historical PIDs."""
    rng = random.Random(seed)
    commands: list[int] = []
    active: list[int] = []
    next_pid = 1
    for _ in range(batch):
        commands.append(rng.randint(1, 40))
        active.append(next_pid)
        next_pid += 1
    # Remove a recent suffix first, then delete sparse old PIDs. PID values are
    # never reused when later pipes are laid.
    suffix = active[-batch // 3:]
    commands.extend(-pid for pid in reversed(suffix))
    active = active[:-batch // 3]
    for pid in active[::3]:
        commands.append(-pid)
    active = [pid for i, pid in enumerate(active) if i % 3 != 0]
    for _ in range(batch // 2):
        commands.append(rng.randint(1, 40))
        active.append(next_pid)
        next_pid += 1
    rng.shuffle(active)
    commands.extend(-pid for pid in active)
    validate_command_stream(commands, f"tail-pid-{seed}")
    return TestCase(f"tail-pid-{seed}", 1.0, commands)


def run_case(binary: Path, case: TestCase, timeout: float) -> dict:
    auditor = InteractiveAuditor(binary, timeout)
    return auditor.run(case)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--official-dir", type=Path, default=Path("/Users/555tery/Downloads/2-2/tests"))
    parser.add_argument("--random-cases", type=int, default=12)
    parser.add_argument("--random-commands", type=int, default=6000)
    parser.add_argument("--response-timeout", type=float, default=2.0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--skip-official", action="store_true")
    parser.add_argument("--large-stress", action="store_true",
                        help="add one independent 200,000-command random-fragmentation stream")
    args = parser.parse_args()

    cases: list[TestCase] = []
    if not args.skip_official:
        cases.extend(parse_test(path) for path in sorted(args.official_dir.glob("*.in"), key=lambda p: int(p.stem)))
    modes = ["mixed", "short", "long", "fragment"]
    for i in range(args.random_cases):
        mode = modes[i % len(modes)]
        n = args.random_commands if i % 3 else min(MAX_COMMANDS, args.random_commands * 3)
        cases.append(make_random_case(0xC0FFEE + i, n, mode))
    cases.extend([
        make_lifetime_case(0xF1F0, 12000, "fifo"),
        make_lifetime_case(0x11F0, 12000, "lifo"),
        make_lifetime_case(0xA11, 12000, "random-delete"),
        make_lifetime_case(0x5A11, 12000, "short-lived-small"),
        make_lifetime_case(0x10A6, 12000, "short-lived-large"),
        make_alternating_holes_case(0xA17E),
        make_tail_and_pid_case(0x7A11),
    ])
    cases.extend(make_coalescing_case(0x51A7 + i) for i in range(3))
    if args.large_stress:
        stress = make_random_case(0xF1A1, MAX_COMMANDS, "fragment")
        stress.name = "max-200k-fragment-seed-f1a1"
        cases.append(stress)

    results = []
    for case in cases:
        try:
            result = run_case(args.binary.resolve(), case, args.response_timeout)
        except Exception as exc:
            result = {"name": case.name, "verdict": "FAIL", "error": str(exc)}
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            break
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    report = {"binary": str(args.binary.resolve()), "cases": results,
              "pass": sum(r["verdict"] == "OK" for r in results),
              "fail": sum(r["verdict"] != "OK" for r in results)}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0 if report["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
