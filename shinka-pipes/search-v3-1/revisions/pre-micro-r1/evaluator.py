"""Prepared F/T evaluator. No evaluation on import or --check; fixed main route."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from fitness import aggregate_report
from support import ROOT, PARENT, digest, frozen_v2, native_cache, reference, verify_dependencies

SEARCH = ROOT / "task/data/search"


def verify_snapshot():
    snapshot = json.loads((ROOT / "snapshot.json").read_text())
    for name, sha in snapshot["files"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or digest(path) != sha:
            raise ValueError(f"SEARCH-v3.1 support changed: {name}")
    verify_dependencies()
    reference()
    return len(snapshot["files"])


def load_search():
    verify_snapshot()
    protocol = json.loads((ROOT / "protocol.json").read_text())
    if digest(SEARCH / "manifest.json") != protocol["manifest_sha256"]["search"]:
        raise ValueError("main manifest differs from frozen protocol")
    manifest = json.loads((SEARCH / "manifest.json").read_text())
    from collections import Counter
    cases = manifest["cases"]
    names = [c["file"] for c in cases]
    if (manifest["version"] != "search-v3.1" or manifest["split"] != "search" or manifest["role"] != "fitness"
            or manifest["case_count"] != 128 or manifest["cases_per_family"] != 4
            or len(manifest["families"]) != 32 or len(set(manifest["families"])) != 32
            or len(cases) != 128 or len(set(names)) != 128
            or any(Path(n).name != n or not n.endswith(".in") for n in names)
            or set(names) != {p.name for p in SEARCH.glob("*.in")}
            or Counter(c["family"] for c in cases) != {f: 4 for f in manifest["families"]}
            or len({c["seed"] for c in cases}) != 128 or len({c["sha256"] for c in cases}) != 128
            or manifest["weight_per_case"] != 1):
        raise ValueError("main coverage, namespace or weighting changed")
    for case in cases:
        stats = case["stats"]
        alpha = stats["final_live_volume"] / stats["volume_lower_bound"]
        valid_regime = (case["regime"] == "high" and .95 <= alpha <= 1
                        or case["regime"] == "moderate" and .60 <= alpha < .95
                        or case["regime"] == "rounding" and 0 < alpha <= 1)
        if (not valid_regime or stats["operation_count"] != case["operations"]
                or digest(SEARCH / case["file"]) != case["sha256"]):
            raise ValueError(f"main input or metadata changed: {case['file']}")
    return manifest


def write_result(out, metrics, correct):
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    (out / "correct.json").write_text(json.dumps({"correct": correct}) + "\n")


def evaluate(program, out, workers=2):
    """Future authorized execution only; never selects or evaluates stress inputs."""
    if workers != 2:
        raise ValueError("SEARCH-v3.1 uses the prepared two-worker policy")
    out = Path(out).resolve()
    # Limit all outputs to this new namespace, excluding prepared support/data.
    if not out.is_relative_to(ROOT / "evaluations") or out.exists():
        raise ValueError("use a fresh results directory below search-v3-1/evaluations")
    started = time.monotonic()
    try:
        manifest = load_search()
        frozen_v2("evaluator.py").check_candidate(Path(program))
        compiler = shutil.which("g++")
        if not compiler:
            raise ValueError("g++ unavailable")
        runner, cache_key = native_cache()
        with tempfile.TemporaryDirectory(prefix="pipes-search-v3.1-") as temporary:
            solver = Path(temporary) / "solver"
            compile_result = subprocess.run([compiler, "-O2", "-std=c++20", "-pipe", str(Path(program).resolve()),
                                             "-o", str(solver)], capture_output=True, text=True, timeout=120)
            if compile_result.returncode:
                raise ValueError("compile failed: " + (compile_result.stdout + compile_result.stderr)[-8000:])
            result = subprocess.run([
                sys.executable, "-B", str(PARENT / "evaluator-native/native_harness.py"),
                "--solver", str(solver), "--interactor", str(runner), "--tests", str(SEARCH),
                "--out", str(out / "harness"), "--name", "search-v3.1", "--workers", "2",
                "--response-timeout", "5", "--wall-timeout", "180", "--cpu-limit", "5", "--memory-limit-mb", "256",
            ], capture_output=True, text=True, timeout=128 * 180 + 60)
            summary = json.loads((out / "harness/summary.json").read_text())
            metrics, correct = aggregate_report(summary, manifest, SEARCH, result.returncode)
        metrics.update(program_sha256=digest(program), manifest_sha256=digest(SEARCH / "manifest.json"),
                       snapshot_sha256=digest(ROOT / "snapshot.json"), evaluator_sha256=digest(ROOT / "evaluator.py"),
                       engine="native-direct-v1",
                       native_workers=2, native_binary_cache_key=cache_key, native_binary_sha256=digest(runner),
                       evaluator_wall_s=time.monotonic() - started)
        metrics["private"]["research_manifest_sha256"] = metrics["manifest_sha256"]
        write_result(out, metrics, correct)
        return correct
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        write_result(out, {"combined_score": 0.0, "suite": "search", "corpus_version": "search-v3.1",
                           "error": str(exc), "text_feedback": "Candidate rejected: " + str(exc)}, False)
        return False
