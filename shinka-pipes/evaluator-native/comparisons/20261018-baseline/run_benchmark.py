#!/usr/bin/env python3
"""Full SEARCH-v2 verification of the native transport, fixed saved baseline."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
FAST = ROOT.parent / "evaluator-fast"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(FAST))
from reference import BASE, check_reference, digest
from compare_reports import compare


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def main():
    prior = FAST / "comparisons/20261018-baseline-search-v2"
    pre = json.loads((prior / "preflight.json").read_text())
    reference_before = check_reference()
    assert reference_before == pre["reference"]
    active = json.loads((BASE / "active-run.json").read_text())
    run = Path(active["run_dir"])
    paused_before = (run / "run-manifest.json").read_bytes()
    assert json.loads(paused_before)["status"] == "paused_by_user"
    assert subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode != 0
    baseline = OUT / "baseline.cpp"
    if baseline.exists() or (OUT / "native").exists():
        raise ValueError("benchmark output exists")
    baseline.write_bytes((prior / "baseline.cpp").read_bytes())
    assert digest(baseline) == pre["baseline_sha256"]
    manifest = json.loads((BASE / "task/data/search/manifest.json").read_text())
    sources = {p.name: digest(p) for p in [*ROOT.glob("*.py"), ROOT / "native_runner.cpp"]}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    prepare_start = time.monotonic()
    prepare = subprocess.run([sys.executable, "-B", str(ROOT / "evaluate.py"), "--prepare"],
                             capture_output=True, text=True, env=env, timeout=120, check=True)
    prepare_wall = time.monotonic() - prepare_start
    save("preflight.json", {"at": datetime.now(timezone.utc).isoformat(), "baseline_sha256": digest(baseline),
                            "manifest_sha256": digest(BASE / "task/data/search/manifest.json"),
                            "reference": reference_before, "implementation_sha256": sources,
                            "native_preparation": json.loads(prepare.stdout), "native_prepare_wall_s": prepare_wall,
                            "main_shinka_paused": True, "model_calls": 0, "evolution_generations": 0,
                            "validation_accessed": False, "open15_accessed": False})
    started = time.monotonic()
    command = [sys.executable, "-B", str(ROOT / "evaluate.py"), "--program_path", str(baseline),
               "--results_dir", str(OUT / "native")]
    with (OUT / "native.log").open("x") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        update = -10
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed - update >= 10:
                count = len(list((OUT / "native/harness/runs").glob("*/native_report.json")))
                status = {"phase": "native-baseline", "pid": process.pid, "finished": count, "cases": 128, "elapsed_s": elapsed}
                save("status.json", status)
                print(f"native: {count}/128, wall={elapsed:.1f}s", flush=True)
                update = elapsed
            time.sleep(0.5)
        returncode = process.wait()
    elapsed = time.monotonic() - started
    save("native-timing.json", {"wall_s": elapsed, "returncode": returncode, "command": command})
    assert returncode == 0
    correct = json.loads((OUT / "native/correct.json").read_text())
    assert correct["correct"], json.loads((OUT / "native/metrics.json").read_text())
    old = compare(prior / "reference-paused", OUT / "native", manifest, BASE / "task/data/search")
    selector = compare(prior / "accelerated", OUT / "native", manifest, BASE / "task/data/search")
    save("comparison-original.json", old)
    save("comparison-selector.json", selector)
    previous = json.loads((prior / "controlled-comparison.json").read_text())
    old_time = previous["timings"]["reference_paused"]["end_to_end_wall_s"]
    selector_time = previous["timings"]["accelerated"]["end_to_end_wall_s"]
    summary = {"completed_at": datetime.now(timezone.utc).isoformat(),
               "correct": old["ok"] and selector["ok"], "counts": old["counts"],
               "score": old["score"]["fast"]["combined_score"],
               "wall_s": {"original_saved": old_time, "selector_saved": selector_time, "native_fresh": elapsed},
               "speedup_over_original": old_time / elapsed, "speedup_over_selector": selector_time / elapsed,
               "time_reduction_over_original": 1 - elapsed / old_time,
               "time_reduction_over_selector": 1 - elapsed / selector_time,
               "native_resources": old["resources"]["fast"], "prepare_wall_s": prepare_wall,
               "timing_scope": "native full run is fresh; old timings are saved from earlier controlled comparison; no main Shinka runs concurrently",
               "reference_unchanged": check_reference() == reference_before,
               "implementation_unchanged": all(digest(ROOT / name) == sha for name, sha in sources.items()),
               "main_run_unchanged": (run / "run-manifest.json").read_bytes() == paused_before,
               "baseline_unchanged": digest(baseline) == pre["baseline_sha256"],
               "validation_accessed": False, "open15_accessed": False}
    save("summary.json", summary)
    success = all(summary[key] for key in ("correct", "reference_unchanged", "implementation_unchanged", "main_run_unchanged", "baseline_unchanged"))
    save("status.json", {"phase": "complete" if success else "mismatch", "summary": str(OUT / "summary.json")})
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
