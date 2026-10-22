#!/usr/bin/env python3
"""Small deterministic correctness fixtures; no quality/performance experiments."""

import argparse
import collections
import hashlib
import json
from pathlib import Path
import random
import selectors
import subprocess
import time


ROOT = Path(__file__).resolve().parent


def gaps_from_cells(cells):
    gaps = []
    start = 0
    while start < len(cells):
        if cells[start] is not None:
            start += 1
            continue
        end = start + 1
        while end < len(cells) and cells[end] is None:
            end += 1
        gaps.append((start, end - start))
        start = end
    return gaps


def reference(commands, policy):
    """Exhaustive cell-derived gaps and literal Phi recomputation, online only."""
    cells = []
    pipes = {}
    next_pid = 1
    outputs = []
    coverage = collections.Counter()
    for command in commands:
        before_length = len(cells)
        if command > 0:
            gaps = gaps_from_cells(cells)
            counts = collections.Counter(h for _, h in gaps)
            candidates = []
            for start, h in gaps:
                if h < command:
                    continue
                if policy == "bf":
                    key = (h, start)
                else:
                    after = counts.copy()
                    after[h] -= 1
                    if h > command:
                        after[h - command] += 1
                    phi_after = sum(c * c for c in after.values())
                    phi_before = sum(c * c for c in counts.values())
                    formula = (1 - 2 * counts[h] if h == command else
                               2 - 2 * counts[h] + 2 * counts[h - command])
                    assert phi_after - phi_before == formula
                    key = (phi_after, h, start)
                candidates.append((key, start, h))
            digs = 0
            if candidates:
                candidates.sort()
                _, start, h = candidates[0]
                coverage["exact_fill" if h == command else "split_gap"] += 1
                coverage["fitting_gap_above_40"] += int(h > 40)
                coverage["equal_length_address_tie"] += int(counts[h] > 1)
                if policy == "ss":
                    best_phi = candidates[0][0][0]
                    coverage["delta_tie_different_lengths"] += int(
                        len({item[2] for item in candidates if item[0][0] == best_phi}) > 1)
                coverage["existing_tail_selected"] += int(start + h == len(cells))
            else:
                tail = gaps[-1][1] if gaps and sum(gaps[-1]) == len(cells) else 0
                start = len(cells) - tail
                digs = (command - tail + 19) // 20
                assert digs > 0
                cells.extend([None] * (20 * digs))
                coverage["extension_with_tail"] += int(tail > 0)
                coverage["extension_without_tail"] += int(tail == 0)
            assert start >= 0 and start + command <= len(cells)
            assert all(cell is None for cell in cells[start:start + command])
            for x in range(start, start + command):
                cells[x] = next_pid
            pipes[next_pid] = (start, command)
            next_pid += 1
            outputs.append(f"{digs} {start}")
        else:
            pid = -command
            start, length = pipes.pop(pid)
            left_free = start > 0 and cells[start - 1] is None
            right_free = start + length < len(cells) and cells[start + length] is None
            coverage["both_neighbor_coalescence"] += int(left_free and right_free)
            assert all(cell == pid for cell in cells[start:start + length])
            cells[start:start + length] = [None] * length
            outputs.append(str(start))
        assert len(cells) >= before_length and len(cells) % 20 == 0
        occupied = sum(length for _, length in pipes.values())
        assert occupied == sum(cell is not None for cell in cells)
        assert occupied + sum(h for _, h in gaps_from_cells(cells)) == len(cells)
    return outputs, coverage


def validate_physical(commands, lines):
    """Validate the produced coordinates independently of policy/reference choice."""
    assert len(lines) == len(commands), (len(lines), len(commands))
    cells = []
    pipes = {}
    pid = 0
    for command, line in zip(commands, lines):
        words = line.split()
        if command > 0:
            assert len(words) == 2
            digs, start = map(int, words)
            assert digs >= 0 and start >= 0
            cells.extend([None] * (20 * digs))
            assert start + command <= len(cells)
            assert all(x is None for x in cells[start:start + command])
            pid += 1
            for x in range(start, start + command):
                cells[x] = pid
            pipes[pid] = (start, command)
        else:
            assert len(words) == 1
            start = int(words[0])
            expected_start, length = pipes.pop(-command)
            assert start == expected_start
            assert all(x == -command for x in cells[start:start + length])
            cells[start:start + length] = [None] * length


def run(binary, commands):
    data = "\n".join(map(str, commands + [0])) + "\n"
    result = subprocess.run([str(binary)], input=data, text=True, capture_output=True,
                            timeout=15, check=True)
    assert not result.stderr, result.stderr
    return result.stdout.splitlines()


def check_flush(binary, commands, expected):
    proc = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        for command, line in zip(commands, expected):
            proc.stdin.write(f"{command}\n".encode())
            proc.stdin.flush()
            assert selector.select(timeout=2), "no flushed answer before next command"
            assert proc.stdout.readline().decode().strip() == line
        proc.stdin.write(b"0\n")
        proc.stdin.flush()
        proc.stdin.close()
        assert proc.wait(timeout=2) == 0
        assert proc.stdout.read() == b""
        assert proc.stderr.read() == b""
    finally:
        selector.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def fixtures():
    cases = [
        ("empty", []),
        ("tail_extension", [7, 14, 39, -3, 38, 1, -5, -4, -2, -1, 40]),
        ("exact_and_address_ties", [10] * 6 + [-2, -4, 10, 10]),
        ("both_neighbors", [5] * 4 + [-2, -4, -3, 15, -1, -5, 40]),
        ("large_all_gap_domain", [40] * 12 + list(range(-1, -11, -1)) + [39, 40, 1, 2, 17]),
        ("all_lengths", list(range(1, 41)) + [-i for i in range(1, 41, 2)] + list(range(40, 0, -1))),
    ]
    for seed in range(32):
        rng = random.Random(0x5A710000 + seed)
        commands = []
        live = []
        pid = 0
        for step in range(96):
            if live and rng.random() < (0.7 if 32 <= step < 64 else 0.25):
                i = rng.randrange(len(live))
                commands.append(-live.pop(i))
            else:
                commands.append(rng.randint(1, 40))
                pid += 1
                live.append(pid)
        cases.append((f"random_{seed:02d}", commands))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "correctness_report.json")
    args = parser.parse_args()
    started = time.time()
    source = ROOT / "pipes_exact.cpp"
    compile_flags = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic"]
    compiler = subprocess.check_output(["c++", "--version"], text=True).splitlines()[0]
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    cases = fixtures()
    report = {"status": "passed", "kind": "tiny_correctness_only", "compiler": compiler,
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "fixtures": len(cases), "commands_per_policy": sum(len(c) for _, c in cases),
              "all_40_requests_checked_in_self_check_after_each_command": True,
              "policies": {}}
    for policy in ("bf", "ss"):
        production = build / f"pipes_{policy}"
        checked = build / f"pipes_{policy}_checked"
        macro = f"-DPOLICY_{policy.upper()}"
        subprocess.run(["c++", *compile_flags, "-DNDEBUG", macro, str(source), "-o", str(production)], check=True)
        subprocess.run(["c++", *compile_flags, "-DPIPE_ALLOCATOR_SELF_CHECK", macro,
                        str(source), "-o", str(checked)], check=True)
        coverage = collections.Counter()
        prefix_runs = 0
        for name, commands in cases:
            expected, covered = reference(commands, policy)
            coverage.update(covered)
            normal = run(production, commands)
            assert normal == expected, (policy, name, "reference")
            validate_physical(commands, normal)
            assert run(checked, commands) == expected, (policy, name, "incremental full scan")
            assert run(production, commands) == normal, (policy, name, "repeat")
            for stop in sorted({0, 1, 7, 31, len(commands) // 2, len(commands)}):
                stop = min(stop, len(commands))
                assert run(production, commands[:stop]) == normal[:stop], (policy, name, stop)
                prefix_runs += 1
        flush_commands = [7, 14, -1, 3, -2, 40, -3, -4]
        flush_expected, _ = reference(flush_commands, policy)
        check_flush(production, flush_commands, flush_expected)
        required = ["exact_fill", "split_gap", "fitting_gap_above_40", "equal_length_address_tie",
                    "existing_tail_selected", "extension_with_tail", "extension_without_tail",
                    "both_neighbor_coalescence"]
        if policy == "ss":
            required.append("delta_tie_different_lengths")
        assert all(coverage[key] > 0 for key in required), (policy, coverage)
        report["policies"][policy] = {"prefix_runs": prefix_runs, "repeat": True,
                                      "immediate_flush": True, "coverage": dict(sorted(coverage.items())),
                                      "production_flags": compile_flags + ["-DNDEBUG", macro],
                                      "checked_flags": compile_flags + ["-DPIPE_ALLOCATOR_SELF_CHECK", macro],
                                      "binary_sha256": hashlib.sha256(production.read_bytes()).hexdigest()}
    report["elapsed_seconds_for_compilation_and_correctness"] = round(time.time() - started, 3)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "fixtures": report["fixtures"],
                      "commands_per_policy": report["commands_per_policy"], "report": str(args.output)}))


if __name__ == "__main__":
    main()
