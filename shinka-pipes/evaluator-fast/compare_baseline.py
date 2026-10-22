#!/usr/bin/env python3
"""Run exactly two fixed SEARCH-v2 baseline evaluations, without evolution."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

from reference import BASE, ROOT, check_reference, digest


def write_json(path: Path, value, *, exclusive=False):
    with path.open("x" if exclusive else "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def run_one(label: str, script: Path, baseline: Path, directory: Path, root: Path):
    command = [sys.executable, "-B", "-u", str(script), "--program_path", str(baseline),
               "--results_dir", str(directory)]
    started, monotonic_start = now(), time.monotonic()
    with (root / (label + ".log")).open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        last_update = 0
        while process.poll() is None:
            elapsed = time.monotonic() - monotonic_start
            if elapsed - last_update >= 10 or last_update == 0:
                # The reference harness writes solver_stderr only after a case
                # has finished. This reads output metadata, never input streams.
                finished = sum(1 for _ in (directory / "harness/runs").glob("*/solver_stderr.txt"))
                status = {"phase": label, "pid": process.pid, "elapsed_s": elapsed,
                          "finished_case_artifacts": finished, "total_cases": 128, "updated_at": now()}
                write_json(root / "status.json", status)
                print(f"{label}: {finished}/128, elapsed={elapsed:.1f}s", flush=True)
                last_update = elapsed
            time.sleep(1)
        returncode = process.wait()
    elapsed = time.monotonic() - monotonic_start
    result = {"command": command, "started_at": started, "finished_at": now(),
              "end_to_end_wall_s": elapsed, "returncode": returncode, "results_dir": str(directory)}
    write_json(root / (label + "-timing.json"), result, exclusive=True)
    if returncode != 0:
        raise RuntimeError(f"{label} entrypoint failed: returncode={returncode}; see {label}.log")
    correct = json.loads((directory / "correct.json").read_text())
    metrics = json.loads((directory / "metrics.json").read_text())
    if correct != {"correct": True}:
        raise RuntimeError(f"{label} baseline rejected: {metrics.get('error', 'see metrics.json')}")
    print(f"{label}: complete, score={metrics['combined_score']:.17g}, wall={elapsed:.3f}s", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.is_relative_to(BASE) or out.is_relative_to(ROOT.parent / "runs"):
        parser.error("use a separate output directory outside existing Shinka runs")
    before = check_reference()
    active_pointer = BASE / "active-run.json"
    active = json.loads(active_pointer.read_text())
    run = Path(active["run_dir"])
    run_manifest = json.loads((run / "run-manifest.json").read_text())
    source = run / "gen_0/main.cpp"
    source_sha = digest(source)
    if (run_manifest["suite"] != "search-v2" or source_sha != run_manifest["source_sha256"]
            or source_sha != run_manifest["seed_origin"]["sha256"]):
        raise ValueError("saved baseline does not match the active run's seed provenance")
    saved = run / "gen_0/results"
    historical_metrics = json.loads((saved / "metrics.json").read_text())
    if historical_metrics["program_sha256"] != source_sha:
        raise ValueError("saved baseline metrics refer to another source")
    search = BASE / "task/data/search"
    manifest = json.loads((search / "manifest.json").read_text())
    if manifest["version"] != "search-v2" or manifest["case_count"] != 128:
        raise ValueError("only the 128-case SEARCH-v2 suite is authorized")
    out.mkdir(parents=True, exist_ok=False)
    baseline = out / "baseline.cpp"
    baseline.write_bytes(source.read_bytes())
    write_json(out / "search-manifest.json", manifest, exclusive=True)
    protected = [source, saved / "metrics.json", saved / "harness/summary.json", active_pointer]
    protected_before = {str(path): digest(path) for path in protected}
    implementation = {str(path): digest(path) for path in ROOT.glob("*.py")}
    compiler = shutil.which("g++")
    preflight = {
        "started_at": now(), "purpose": "one reference and one accelerated evaluation; fixed baseline; no evolution",
        "baseline_origin": str(source), "baseline_sha256": source_sha,
        "source_seed_origin": run_manifest["seed_origin"],
        "saved_baseline_score": historical_metrics["combined_score"],
        "search_manifest_sha256": digest(search / "manifest.json"), "case_count": 128,
        "reference": before, "protected_artifacts_before": protected_before,
        "implementation_sha256": implementation, "python_version": sys.version,
        "platform": platform.platform(), "compiler": compiler,
        "compiler_version": subprocess.run([compiler, "--version"], capture_output=True, text=True, check=True).stdout,
        "evolution_started": False, "model_calls": 0, "generations_consumed": 0,
        "validation_accessed": False, "open15_accessed": False,
        "ordering": ["reference", "accelerated"],
        "timing_caveat": "one pair, fixed order; background load and filesystem cache uncontrolled; active Shinka is not paused",
        "active_run_manifest_before": run_manifest,
    }
    write_json(out / "preflight.json", preflight, exclusive=True)
    try:
        timings = {}
        for label, script in (("reference", BASE / "task/evaluate.py"), ("accelerated", ROOT / "evaluate.py")):
            if check_reference() != before or digest(baseline) != source_sha:
                raise ValueError("support files or baseline changed")
            timings[label] = run_one(label, script, baseline, out / label, out)
        from compare_reports import compare
        comparison = compare(out / "reference", out / "accelerated", manifest, search)
        comparison["timings"] = timings
        comparison["end_to_end_speedup"] = timings["reference"]["end_to_end_wall_s"] / timings["accelerated"]["end_to_end_wall_s"]
        comparison["end_to_end_time_reduction_fraction"] = 1 - timings["accelerated"]["end_to_end_wall_s"] / timings["reference"]["end_to_end_wall_s"]
        comparison["historical_baseline_score_matches"] = all(
            json.loads((out / label / "metrics.json").read_text())["combined_score"] == historical_metrics["combined_score"]
            for label in timings)
        historical_records = {Path(record["test_file"]).name: record for record in
                              json.loads((saved / "harness/summary.json").read_text())["records"]}
        historical_mismatches = []
        for label in timings:
            for record in json.loads((out / label / "harness/summary.json").read_text())["records"]:
                name = Path(record["test_file"]).name
                previous = historical_records[name]
                for key in ("trench_length_m", "minimum_trench_lower_bound_m", "kpi", "weighted_score"):
                    if record[key] != previous[key]:
                        historical_mismatches.append({"evaluator": label, "case": name, "field": key})
        comparison["historical_per_case_mismatches"] = historical_mismatches
        write_json(out / "comparison.json", comparison, exclusive=True)
        protected_after = {str(path): digest(path) for path in protected}
        after = check_reference()
        preservation = {"checked_at": now(), "reference_unchanged": before == after,
                        "reference_files": len(after["checked_files"]),
                        "baseline_copy_unchanged": digest(baseline) == source_sha,
                        "protected_artifacts_unchanged": protected_before == protected_after,
                        "protected_artifacts_after": protected_after,
                        "implementation_unchanged": implementation == {str(path): digest(path) for path in ROOT.glob("*.py")},
                        "active_run_manifest_after": json.loads((run / "run-manifest.json").read_text()),
                        "validation_accessed": False, "open15_accessed": False}
        write_json(out / "preservation.json", preservation, exclusive=True)
        success = (not comparison["mismatches"] and comparison["historical_baseline_score_matches"]
                   and not historical_mismatches and before == after and protected_before == protected_after)
        write_json(out / "status.json", {"phase": "complete" if success else "mismatch", "updated_at": now(),
                                         "comparison": str(out / "comparison.json")})
        print(json.dumps({"success": success, "end_to_end_speedup": comparison["end_to_end_speedup"],
                          "report": str(out / "comparison.json")}, indent=2), flush=True)
        return 0 if success else 1
    except Exception as exc:
        write_json(out / "status.json", {"phase": "failed", "updated_at": now(), "error": repr(exc)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
