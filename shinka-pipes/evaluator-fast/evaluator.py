#!/usr/bin/env python3
"""Separate SEARCH-v2 evaluator. No live Shinka configuration imports this file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from reference import BASE, ROOT, check_reference, digest, load_frozen

HARNESS = ROOT / "fast_harness.py"
LIMIT_ARGUMENTS = ["--response-timeout", "5", "--wall-timeout", "180",
                   "--cpu-limit", "5", "--memory-limit-mb", "256"]


def evaluate(program: Path, out: Path) -> bool:
    # Prevent an accidental write into the active or historical search runs.
    out = out.resolve()
    if out.is_relative_to(BASE) or out.is_relative_to(ROOT.parent / "runs"):
        raise ValueError("use a separate results directory outside existing Shinka runs")
    if (out / "metrics.json").exists() or (out / "harness").exists():
        raise ValueError("results already exist; refusing to overwrite an evaluation")
    check_reference()
    base = load_frozen("evaluator.py")
    # Use a fresh, pinned copy even if another caller imported synthetic_eval.
    aggregate_report = load_frozen("synthetic_eval.py", shared=True).aggregate_report
    try:
        manifest = base.load_search()
        base.check_candidate(program)
        compiler = shutil.which("g++")
        if not compiler:
            raise ValueError("C++ compiler unavailable")
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pipes-search-v2-fast-") as temporary:
            solver, interactor = Path(temporary) / "solver", Path(temporary) / "interactor"
            for command in (
                [compiler, "-O2", "-std=c++20", "-pipe", str(program.resolve()), "-o", str(solver)],
                [compiler, "-O2", "-std=c++17", "-pipe", "-I", str(base.TASK / "vendor"),
                 str(base.TASK / "vendor/interactor.cpp"), "-o", str(interactor)],
            ):
                result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
                if result.returncode:
                    raise ValueError("compile failed: " + (result.stdout + result.stderr)[-8000:])
            result = subprocess.run([
                sys.executable, str(HARNESS), "--solver", str(solver), "--interactor", str(interactor),
                "--tests", str(base.SEARCH), "--out", str(out / "harness"), "--name", "search-v2",
                *LIMIT_ARGUMENTS,
            ], capture_output=True, text=True, timeout=128 * 180 + 60, check=False)
            summary = json.loads((out / "harness/summary.json").read_text())
            metrics, correct = aggregate_report(summary, manifest, base.SEARCH, result.returncode)
        metrics.update({
            "program_sha256": digest(program),
            "manifest_sha256": digest(base.SEARCH / "manifest.json"),
            "evaluator_sha256": digest(ROOT / "evaluator.py"),
            "snapshot_sha256": digest(BASE / "snapshot.json"),
            "transport": "selector-stdout-v1",
            "transport_sha256": digest(HARNESS),
            "selector_transport_sha256": digest(ROOT / "selector_transport.py"),
            "reference_loader_sha256": digest(ROOT / "reference.py"),
            "reference_evaluator_sha256": digest(BASE / "evaluator.py"),
            "reference_harness_sha256": digest(base.TASK / "tools/pipes_harness.py"),
        })
        base.write_result(out, metrics, correct)
        return correct
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        base.write_result(out, {"combined_score": 0.0, "suite": "search", "corpus_version": "search-v2",
                               "error": str(exc), "text_feedback": "Candidate rejected: " + str(exc)}, False)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify support hashes only; no evaluation")
    parser.add_argument("--program_path")
    parser.add_argument("--results_dir")
    args = parser.parse_args()
    if args.check:
        if args.program_path or args.results_dir:
            parser.error("--check cannot be combined with evaluation arguments")
        result = check_reference()
        print(json.dumps({"support_files_unchanged": len(result["checked_files"]),
                          "snapshot_sha256": result["snapshot_sha256"],
                          "transport": "selector-stdout-v1", "evaluations_started": 0}, indent=2))
        return 0
    if not args.program_path or not args.results_dir:
        parser.error("provide --program_path and --results_dir, or --check")
    evaluate(Path(args.program_path), Path(args.results_dir))
    return 0  # Same Shinka contract: correct.json carries candidate acceptance.


if __name__ == "__main__":
    raise SystemExit(main())
