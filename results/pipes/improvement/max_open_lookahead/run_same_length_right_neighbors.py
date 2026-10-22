#!/usr/bin/env python3
"""Run the neighboring T=44/52/56/64/72 candidates on all official opens."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent

generator = subprocess.run(
    ["python3", str(HERE / "make_same_length_right_candidates.py")],
    cwd=ROOT,
    check=True,
    text=True,
    capture_output=True,
)
print(generator.stdout, end="")

for threshold in (44, 52, 56, 64, 72):
    source = HERE / f"candidate_adaptive_right4_w2048_s60_recent{threshold}_right.cpp"
    binary = HERE / "bin" / f"candidate_adaptive_right4_w2048_s60_recent{threshold}_right"
    report = HERE / f"official-open-recent{threshold}-right"
    build_command = [
        "g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-Werror", str(source), "-o", str(binary),
    ]
    build = subprocess.run(build_command, cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        raise SystemExit(build.stderr)
    run_command = [
        "python3", str(ROOT / "tools/pipes_harness.py"),
        "--solver", str(binary),
        "--name", f"adaptive_right4_w2048_s60_recent{threshold}_right",
        "--interactor", str(ROOT / "tools/interactor"),
        "--tests", str(ROOT / "data/pipes/open"),
        "--out", str(report),
    ]
    run = subprocess.run(run_command, cwd=ROOT, capture_output=True, text=True)
    print(f"=== T={threshold}: build=ok, run_exit={run.returncode} ===")
    print(run.stdout, end="")
    if run.stderr:
        print(run.stderr, end="")
    if run.returncode:
        raise SystemExit(run.returncode)
