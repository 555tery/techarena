#!/usr/bin/env python3
"""Full fixed-baseline SEARCH-v2 comparisons, never evolution or heldouts."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
FAST = ROOT.parent / "evaluator-fast"
sys.path[:0] = [str(ROOT), str(FAST)]
from reference import BASE, check_reference, digest
from compare_reports import compare


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def main():
    if (OUT / "preflight.json").exists():
        raise ValueError("benchmark output exists")
    prior = FAST / "comparisons/20261018-baseline-search-v2"
    serial = ROOT / "comparisons/20261018-baseline"
    reference = check_reference()
    active = json.loads((BASE / "active-run.json").read_text())
    run = Path(active["run_dir"])
    protected = {name: digest(run / name) for name in ("run-manifest.json", "programs.sqlite")}
    assert json.loads((run / "run-manifest.json").read_text())["status"] == "paused_by_user"
    assert subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode != 0
    baseline = OUT / "baseline.cpp"
    baseline.write_bytes((prior / "baseline.cpp").read_bytes())
    assert digest(baseline) == "e3ee5b3551a2b46fe166ca29414c5c1703aa6f9397b49aa776c9c3e8f4f4de7e"
    corpus = BASE / "task/data/search"
    manifest = json.loads((corpus / "manifest.json").read_text())
    sources = {p.name: digest(p) for p in [*ROOT.glob("*.py"), ROOT / "native_runner.cpp"]}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.monotonic()
    preparation = subprocess.run([sys.executable, "-B", str(ROOT / "evaluate.py"), "--prepare"],
                                 capture_output=True, text=True, env=env, timeout=120, check=True)
    prepare_wall = time.monotonic() - started
    prepared = json.loads(preparation.stdout)
    save("preflight.json", {"at": datetime.now(timezone.utc).isoformat(), "reference": reference,
                           "implementation_sha256": sources, "baseline_sha256": digest(baseline),
                           "manifest_sha256": digest(corpus / "manifest.json"), "protected_main_run": protected,
                           "native_preparation": prepared, "native_prepare_wall_s": prepare_wall,
                           "workers_order": [2, 4, 8], "model_calls": 0, "evolution_generations": 0,
                           "validation_accessed": False, "open15_accessed": False})
    profiles = {}
    for workers in (2, 4, 8):
        label = f"workers-{workers}"
        command = [sys.executable, "-B", str(ROOT / "evaluate.py"), "--program_path", str(baseline),
                   "--results_dir", str(OUT / label), "--workers", str(workers)]
        started = time.monotonic()
        with (OUT / (label + ".log")).open("x") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
            update = -20
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed - update >= 15:
                    count = len(list((OUT / label / "harness/runs").glob("*/native_report.json")))
                    save("status.json", {"phase": label, "finished": count, "cases": 128, "elapsed_s": elapsed})
                    print(f"{label}: {count}/128, wall={elapsed:.1f}s", flush=True)
                    update = elapsed
                time.sleep(0.25)
            returncode = process.wait()
        wall = time.monotonic() - started
        assert returncode == 0, label
        assert json.loads((OUT / label / "correct.json").read_text())["correct"], label
        metrics = json.loads((OUT / label / "metrics.json").read_text())
        assert metrics["native_binary_cache_key"] == prepared["cache_key"]
        comparison = compare(prior / "reference-paused", OUT / label, manifest, corpus)
        save(label + "-comparison.json", comparison)
        assert comparison["ok"], comparison["mismatches"]
        profiles[str(workers)] = {"end_to_end_wall_s": wall, "evaluator_wall_s": metrics["evaluator_wall_s"],
                                  "score": metrics["combined_score"], "counts": comparison["counts"],
                                  "resources": comparison["resources"]["fast"], "command": command}
        save(label + "-timing.json", profiles[str(workers)])
        print(f"{label}: full parity OK; end-to-end={wall:.3f}s", flush=True)
    old = json.loads((prior / "controlled-comparison.json").read_text())
    old_wall = old["timings"]["reference_paused"]["end_to_end_wall_s"]
    selector_wall = old["timings"]["accelerated"]["end_to_end_wall_s"]
    serial_wall = json.loads((serial / "summary.json").read_text())["wall_s"]["native_fresh"]
    best = min(profiles, key=lambda key: profiles[key]["end_to_end_wall_s"])
    best_wall = profiles[best]["end_to_end_wall_s"]
    result = {"completed_at": datetime.now(timezone.utc).isoformat(), "profiles": profiles,
              "fastest_observed_workers": int(best), "fastest_observed_wall_s": best_wall,
              "previous_wall_s": {"original": old_wall, "selector": selector_wall, "native_serial": serial_wall},
              "speedup_over_original": old_wall / best_wall, "speedup_over_selector": selector_wall / best_wall,
              "speedup_over_native_serial": serial_wall / best_wall,
              "score": profiles[best]["score"],
              "timing_scope": "one fresh full run at 2/4/8 workers in that order; prior serial/original/selector timings from saved runs, no concurrent main Shinka; timings are host-dependent, no universal speedup claim",
              "reference_unchanged": check_reference() == reference,
              "implementation_unchanged": all(digest(ROOT / name) == sha for name, sha in sources.items()),
              "main_run_unchanged": all(digest(run / name) == sha for name, sha in protected.items()),
              "baseline_unchanged": digest(baseline) == "e3ee5b3551a2b46fe166ca29414c5c1703aa6f9397b49aa776c9c3e8f4f4de7e",
              "main_process_absent": subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode != 0,
              "candidate_evaluations": 3, "evolution_generations": 0, "model_calls": 0,
              "validation_accessed": False, "open15_accessed": False}
    save("summary.json", result)
    success = all(result[key] for key in ("reference_unchanged", "implementation_unchanged", "main_run_unchanged", "baseline_unchanged", "main_process_absent"))
    save("status.json", {"phase": "complete" if success else "mismatch", "summary": str(OUT / "summary.json")})
    print(json.dumps({key: value for key, value in result.items() if key != "profiles"}, indent=2), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
