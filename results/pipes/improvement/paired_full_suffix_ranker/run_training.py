#!/usr/bin/env python3
"""Run the fixed baseline-label, one-round DAgger, and final-fit pipeline."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BIN = HERE / "bin"
TRAIN = HERE / "inputs/train"
RUNS = HERE / "runs"
BASELINE = ROOT / "results/pipes/final/solution.cpp"
NOMC_BINARY = BIN / "frozen_nomc"
LABELER_BINARY = BIN / "full_suffix_labeler"
CANDIDATE_SOURCE = HERE / "src/ranker_candidate.cpp"
CADENCE = 1_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def command_result(cmd: list[str], *, output_path: Path | None = None) -> dict[str, object]:
    started = time.perf_counter()
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    record = {
        "cmd": cmd, "returncode": result.returncode,
        "wall_s": time.perf_counter() - started,
        "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-2000:],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr[-4000:]}")
    return record


def compile_sources() -> None:
    BIN.mkdir(parents=True, exist_ok=True)
    command_result([
        "clang++", "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Werror",
        "-pedantic", "-DMC_ROLLOUT_DISABLED", str(BASELINE), "-o", str(NOMC_BINARY),
    ], output_path=RUNS / "build-log.jsonl")
    command_result([
        "clang++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-Werror", str(HERE / "src/full_suffix_labeler.cpp"),
        "-o", str(LABELER_BINARY),
    ], output_path=RUNS / "build-log.jsonl")


def parse_commands(path: Path) -> list[int]:
    tokens = path.read_text(encoding="ascii").split()
    count = int(tokens[1])
    commands = [int(v) for v in tokens[2:]]
    if len(commands) == count + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != count or any(v == 0 for v in commands):
        raise RuntimeError(f"bad input command vector: {path}")
    return commands


def run_solver(binary: Path, input_path: Path, reply_path: Path) -> dict[str, object]:
    commands = parse_commands(input_path)
    payload = "\n".join(str(value) for value in commands) + "\n0\n"
    started = time.perf_counter()
    result = subprocess.run([str(binary)], input=payload, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"solver failed on {input_path.name}: {result.stderr[-2000:]}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != len(commands):
        raise RuntimeError(f"reply count mismatch {input_path.name}: {len(lines)} vs {len(commands)}")
    reply_path.parent.mkdir(parents=True, exist_ok=True)
    reply_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return {"input": str(input_path.relative_to(ROOT)), "commands": len(commands),
            "binary_sha256": sha256(binary), "reply_sha256": sha256(reply_path),
            "wall_s": elapsed, "reply_lines": len(lines)}


def label_stream(input_path: Path, reply_path: Path, split: str, label_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    result = subprocess.run([
        str(LABELER_BINARY), str(input_path), str(reply_path), split,
        input_path.stem, str(CADENCE), str(label_path),
    ], cwd=ROOT, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"labeler failed for {input_path.name}: {result.stderr[-3000:]}")
    with label_path.open(newline="", encoding="ascii") as stream:
        count = sum(1 for _ in csv.DictReader(stream))
    return {"input": str(input_path.relative_to(ROOT)), "reply": str(reply_path.relative_to(ROOT)),
            "labels": str(label_path.relative_to(ROOT)), "rows": count,
            "label_sha256": sha256(label_path), "wall_s": elapsed}


def collect(input_paths: list[Path], solver: Path, split: str) -> list[dict[str, object]]:
    replies_root = RUNS / f"{split}_replies"
    labels_root = RUNS / f"{split}_labels"
    replies_root.mkdir(parents=True, exist_ok=True)
    labels_root.mkdir(parents=True, exist_ok=True)
    records = []
    for index, input_path in enumerate(input_paths, start=1):
        reply_path = replies_root / f"{input_path.stem}.txt"
        label_path = labels_root / f"{input_path.stem}.csv"
        replay = run_solver(solver, input_path, reply_path)
        label = label_stream(input_path, reply_path, split, label_path)
        records.append({**replay, **label})
        print(f"{split} {index}/{len(input_paths)} {input_path.name}: "
              f"{label['rows']} rows, {label['wall_s']:.2f}s label", flush=True)
    return records


def fit(labels: list[Path], label: str) -> dict[str, object]:
    model_path = RUNS / f"{label}_model.json"
    return command_result([
        sys.executable, str(HERE / "fit_ranker.py"), "--labels",
        *[str(path) for path in labels], "--header", str(HERE / "src/ranker_model.hpp"),
        "--model-json", str(model_path),
    ], output_path=RUNS / "fit-log.jsonl")


def main() -> None:
    os.environ["PYTHONHASHSEED"] = "0"
    if not (HERE / "inputs/manifest.json").exists():
        raise RuntimeError("generate the preregistered streams first")
    input_paths = sorted(TRAIN.glob("*.in"))
    if len(input_paths) != 30:
        raise RuntimeError(f"expected 30 train streams, got {len(input_paths)}")
    compile_sources()

    baseline_records = collect(input_paths, NOMC_BINARY, "train")
    baseline_labels = sorted((RUNS / "train_labels").glob("*.csv"))
    fit(baseline_labels, "initial")
    initial_model_hash = sha256(HERE / "src/ranker_model.hpp")

    initial_binary = BIN / "candidate_initial"
    command_result([
        "clang++", "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Werror",
        "-pedantic", str(CANDIDATE_SOURCE), "-o", str(initial_binary),
    ], output_path=RUNS / "build-log.jsonl")
    dagger_records = collect(input_paths, initial_binary, "dagger")
    dagger_labels = sorted((RUNS / "dagger_labels").glob("*.csv"))
    fit(baseline_labels + dagger_labels, "final")
    final_model_hash = sha256(HERE / "src/ranker_model.hpp")

    final_binary = BIN / "candidate_final"
    command_result([
        "clang++", "-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Werror",
        "-pedantic", str(CANDIDATE_SOURCE), "-o", str(final_binary),
    ], output_path=RUNS / "build-log.jsonl")

    training_manifest = {
        "frozen_source_sha256": sha256(BASELINE),
        "frozen_nomc_binary_sha256": sha256(NOMC_BINARY),
        "labeler_source_sha256": sha256(HERE / "src/full_suffix_labeler.cpp"),
        "labeler_binary_sha256": sha256(LABELER_BINARY),
        "candidate_source_sha256": sha256(CANDIDATE_SOURCE),
        "initial_model_header_sha256": initial_model_hash,
        "final_model_header_sha256": final_model_hash,
        "candidate_initial_binary_sha256": sha256(initial_binary),
        "candidate_final_binary_sha256": sha256(final_binary),
        "cadence_commands": CADENCE,
        "continuation": "deterministic frozen greedy allocator without nested MC, exact future PIDs, to EOF",
        "baseline_train_streams": baseline_records,
        "candidate_trajectory_streams": dagger_records,
        "baseline_label_files": [str(path.relative_to(ROOT)) for path in baseline_labels],
        "candidate_label_files": [str(path.relative_to(ROOT)) for path in dagger_labels],
    }
    manifest_path = RUNS / "training-manifest.json"
    manifest_path.write_text(json.dumps(training_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "baseline_rows": sum(int(r["rows"]) for r in baseline_records),
        "dagger_rows": sum(int(r["rows"]) for r in dagger_records),
        "candidate_final_binary_sha256": training_manifest["candidate_final_binary_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
