#!/usr/bin/env python3
"""Run one bounded Pipes offline-oracle window and preserve provenance."""

import hashlib
import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[3]
RUNNER = ROOT / "results/pipes/improvement/offline_longbeam/longbeam"
RUNNER_SOURCE = ROOT / "results/pipes/improvement/offline_longbeam/longbeam.cpp"
BASELINE_SOURCE = ROOT / "results/pipes/final/solution.cpp"
EXPECTED_BASELINE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
EXPECTED_RUNNER_SHA = "9e6c9f360381b6fc6f868d9fbaf687dc5d5a352def45579f95c5b2ae00ba904a"
MEMORY_BUDGET_BYTES = 256 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 8:
        raise SystemExit(
            "usage: run_window.py NAME INPUT TRACE START COUNT WIDTH ACTION_CAP"
        )
    name = sys.argv[1]
    input_path = (ROOT / sys.argv[2]).resolve()
    trace_path = (ROOT / sys.argv[3]).resolve()
    start, count, width, action_cap = map(int, sys.argv[4:])

    baseline_sha = sha256(BASELINE_SOURCE)
    runner_sha = sha256(RUNNER)
    if baseline_sha != EXPECTED_BASELINE_SHA:
        raise SystemExit(f"frozen source SHA mismatch: {baseline_sha}")
    if runner_sha != EXPECTED_RUNNER_SHA:
        raise SystemExit(f"runner binary SHA mismatch: {runner_sha}")

    result_dir = WORK / "runs"
    log_dir = WORK / "logs"
    resource_dir = WORK / "resources"
    for directory in (result_dir, log_dir, resource_dir):
        directory.mkdir(parents=True, exist_ok=True)
    output_path = result_dir / f"{name}.json"
    log_path = log_dir / f"{name}.log"
    resource_path = resource_dir / f"{name}.json"
    command = [
        str(RUNNER), str(input_path), str(trace_path), str(output_path),
        str(start), str(count), str(width), str(action_cap),
    ]

    started = time.monotonic()
    with log_path.open("w") as log:
        log.write(json.dumps({"command": command}, indent=2) + "\n")
        log.flush()
        child = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        return_code = child.wait()
    wall_seconds = time.monotonic() - started
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    rss_bytes = usage.ru_maxrss if platform.system() == "Darwin" else usage.ru_maxrss * 1024
    metadata = {
        "name": name,
        "command": command,
        "return_code": return_code,
        "wall_seconds": round(wall_seconds, 3),
        "child_cpu_seconds": round(usage.ru_utime + usage.ru_stime, 3),
        "peak_rss_bytes": int(rss_bytes),
        "peak_rss_mib": round(rss_bytes / (1024 * 1024), 3),
        "memory_budget_bytes": MEMORY_BUDGET_BYTES,
        "memory_limit_enforced": platform.system() != "Darwin",
        "baseline_source_sha256": baseline_sha,
        "runner_source_sha256": sha256(RUNNER_SOURCE),
        "runner_binary_sha256": runner_sha,
        "input_path": str(input_path.relative_to(ROOT)),
        "input_sha256": sha256(input_path),
        "trace_path": str(trace_path.relative_to(ROOT)),
        "trace_sha256": sha256(trace_path),
        "output_path": str(output_path.relative_to(ROOT)) if output_path.exists() else None,
        "log_path": str(log_path.relative_to(ROOT)),
    }
    resource_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
