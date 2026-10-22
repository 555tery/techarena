#!/usr/bin/env python3
"""Fixed SEARCH-v2 native evaluator; no evolution or work on import."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from cache import ROOT, BASE, native_binary
from build_native import check_reference, digest
from reference import load_frozen


def evaluate(program: Path, out: Path, workers=8):
    if workers not in range(1, 9):
        raise ValueError("workers must be between 1 and 8")
    out = out.resolve()
    if out.is_relative_to(BASE) or out.is_relative_to(ROOT.parent / "runs"):
        raise ValueError("results must be outside existing Shinka runs")
    if (out / "metrics.json").exists() or (out / "harness").exists():
        raise ValueError("results already exist")
    check_reference()
    base = load_frozen("evaluator.py")
    aggregate = load_frozen("synthetic_eval.py", shared=True).aggregate_report
    started = time.monotonic()
    try:
        manifest = base.load_search()
        base.check_candidate(program)
        runner, key = native_binary()
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pipes-native-solver-") as temporary:
            solver = Path(temporary) / "solver"
            result = subprocess.run([shutil.which("g++"), "-O2", "-std=c++20", "-pipe", str(program.resolve()),
                                     "-o", str(solver)], capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise ValueError("compile failed: " + (result.stdout + result.stderr)[-8000:])
            result = subprocess.run([sys.executable, "-B", str(ROOT / "native_harness.py"), "--solver", str(solver),
                                     "--interactor", str(runner), "--tests", str(base.SEARCH),
                                     "--out", str(out / "harness"), "--name", "search-v2",
                                     "--workers", str(workers),
                                     "--response-timeout", "5", "--wall-timeout", "180",
                                     "--cpu-limit", "5", "--memory-limit-mb", "256"],
                                    capture_output=True, text=True, timeout=128 * 180 + 60)
            summary = json.loads((out / "harness/summary.json").read_text())
            try:
                metrics, correct = aggregate(summary, manifest, base.SEARCH, result.returncode)
            except ValueError as exc:
                failed = [record for record in summary.get("records", []) if record["status"] not in ("ok", "skipped")
                          or record.get("solver_cpu_limit_exceeded") or record.get("solver_memory_limit_exceeded")]
                detail = "; ".join(f"{record['case']}: {record['status']}: {record['detail']}" for record in failed[:3])
                raise ValueError(str(exc) + ("; " + detail if detail else "")) from exc
        metrics.update({"program_sha256": digest(program), "manifest_sha256": digest(base.SEARCH / "manifest.json"),
                        "snapshot_sha256": digest(BASE / "snapshot.json"), "evaluator_sha256": digest(ROOT / "evaluate_native.py"),
                        "engine": "native-direct-v1", "native_binary_cache_key": key,
                        "native_workers": workers,
                        "native_binary_sha256": digest(runner),
                        "native_sources_sha256": {name: digest(ROOT / name) for name in
                                                  ("native_runner.cpp", "native_harness.py", "build_native.py", "cache.py")},
                        "evaluator_wall_s": time.monotonic() - started})
        base.write_result(out, metrics, correct)
        return correct
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        base.write_result(out, {"combined_score": 0.0, "suite": "search", "corpus_version": "search-v2",
                               "error": str(exc), "text_feedback": "Candidate rejected: " + str(exc)}, False)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prepare", action="store_true", help="build/check native cache, no candidate evaluation")
    parser.add_argument("--program_path")
    parser.add_argument("--results_dir")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=8,
                        help="parallel SEARCH streams, each with unchanged per-process limits (default: 8)")
    args = parser.parse_args()
    if args.check or args.prepare:
        if args.program_path or args.results_dir:
            parser.error("preparation cannot include a candidate")
        result = {"reference_files": len(check_reference()["checked_files"]), "candidate_evaluations": 0}
        if args.prepare:
            binary, key = native_binary()
            result.update(binary=str(binary), cache_key=key)
        print(json.dumps(result, indent=2))
        return 0
    if not args.program_path or not args.results_dir:
        parser.error("provide --program_path and --results_dir")
    evaluate(Path(args.program_path), Path(args.results_dir), args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
