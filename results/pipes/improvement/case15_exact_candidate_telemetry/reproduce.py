#!/usr/bin/env python3
"""Build and run the read-only exact replay plus gap-lineage replay."""
from __future__ import annotations

import hashlib
import gzip
import os
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INPUT = ROOT / "data/pipes/open/15.in"
BASELINE_ANSWER = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/judge_output.txt"
COST_LOG = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/solver_stderr.txt"
RUNS = HERE / "runs"
GEOMETRY = HERE / "geometry"
BUILD = HERE / "build"
EXPECTED_ANSWER_SHA256 = "0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run(args: list[str], **kwargs) -> None:
    subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main() -> None:
    RUNS.mkdir(exist_ok=True)
    GEOMETRY.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    words = INPUT.read_text().split()
    count = int(words[1])
    commands = list(map(int, words[2 : 2 + count]))
    if len(commands) != count or len(words) <= count + 2 or int(words[count + 2]) != 0:
        raise RuntimeError("case 15 input header or terminator changed")

    run([
        "g++", "-O2", "-std=c++17", "-pipe", "-Wall", "-Wextra", "-Wpedantic",
        str(HERE / "interval_origin_replay.cpp"), "-o", str(BUILD / "interval_origin_replay"),
    ])

    # Reconstruct exact pre-expansion gap episodes from the frozen output first;
    # these coordinates define the bounded first-successor lineage audit.
    run([
        str(BUILD / "interval_origin_replay"), str(INPUT), str(BASELINE_ANSWER),
        str(COST_LOG), str(GEOMETRY),
    ])
    run(["python3", str(HERE / "prepare_targets.py")])

    run([
        "g++", "-O2", "-std=c++17", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-Werror", "-DEOF_SURVIVOR_DIAG",
        str(HERE / "solver_replay.cpp"), "-o", str(BUILD / "solver_replay"),
    ])

    env = os.environ.copy()
    env["PIPE_SURVIVOR_TARGETS"] = str(HERE / "targets.tsv")
    env["PIPE_EXPANSION_LOG"] = str(RUNS / "extensions.csv")
    env["PIPE_EXPANSION_CANDIDATES"] = str(RUNS / "extension_candidates.csv")
    env["PIPE_CANDIDATE_SUMMARY"] = str(RUNS / "candidate_ops.csv")
    env["PIPE_CANDIDATE_TARGETS"] = str(RUNS / "candidate_targets.csv")
    env["PIPE_CANDIDATE_SCORES"] = str(RUNS / "candidate_scores.csv")
    with (RUNS / "judge_output.txt").open("wb") as stdout, (RUNS / "solver_stderr.txt").open("wb") as stderr:
        run([str(BUILD / "solver_replay")], input=("\n".join(map(str, commands)) + "\n0\n").encode(),
            stdout=stdout, stderr=stderr, env=env)
    if sha(RUNS / "judge_output.txt") != EXPECTED_ANSWER_SHA256:
        raise RuntimeError("instrumented exact replay differs from the frozen-final answer")

    if sha(RUNS / "judge_output.txt") != sha(BASELINE_ANSWER):
        raise RuntimeError("candidate audit replay differs from the frozen baseline output")
    for name in ("candidate_targets.csv", "candidate_scores.csv"):
        source = RUNS / name
        destination = RUNS / f"{name}.gz"
        with source.open("rb") as inp, gzip.open(destination, "wb", compresslevel=9) as out:
            shutil.copyfileobj(inp, out)
        source.unlink()
    run(["python3", str(HERE / "analyze.py")])
    run(["python3", str(HERE / "summarize_candidate_audit.py")])
    print("Exact replay and interval-lineage replay completed; frozen judge output matched.")


if __name__ == "__main__":
    main()
