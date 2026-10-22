"""Fixed SEARCH-v2 evaluator; importing it never evaluates a candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
TASK = ROOT / "task"
SEARCH = TASK / "data/search"
sys.path.insert(0, str(PARENT))
from synthetic_eval import aggregate_report


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_search() -> dict:
    protocol = json.loads((ROOT / "protocol.json").read_text())
    if digest(SEARCH / "manifest.json") != protocol["manifest_sha256"]:
        raise ValueError("SEARCH-v2 manifest differs from frozen protocol")
    manifest = json.loads((SEARCH / "manifest.json").read_text())
    if (manifest["version"] != "search-v2" or manifest["split"] != "search"
            or manifest["case_count"] != 128 or manifest["cases_per_family"] != 8
            or len(manifest["families"]) != 16):
        raise ValueError("expected only SEARCH-v2: 128 cases, 16 families")
    cases = manifest["cases"]
    names = [case["file"] for case in cases]
    from collections import Counter
    if (len(cases) != 128 or len(set(names)) != 128
            or any(Path(name).name != name or not name.endswith(".in") for name in names)
            or set(names) != {p.name for p in SEARCH.glob("*.in")}
            or Counter(c["family"] for c in cases) != {f: 8 for f in manifest["families"]}
            or len({c["seed"] for c in cases}) != 128
            or len({c["sha256"] for c in cases}) != 128):
        raise ValueError("wrong SEARCH-v2 coverage, duplicate or unexpected files")
    for case in cases:
        if digest(SEARCH / case["file"]) != case["sha256"]:
            raise ValueError(f"SEARCH-v2 input checksum mismatch: {case['file']}")
    return manifest


def check_candidate(program: Path) -> None:
    initial, candidate = (TASK / "initial.cpp").read_text(), program.read_text()
    start, end = "// EVOLVE-BLOCK-START", "// EVOLVE-BLOCK-END"
    for text in (initial, candidate):
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            raise ValueError("expected one ordered mutable region")
    # Shinka's diff applier removes the optional final newline from the entire
    # source. Ignore exactly that terminator, while preserving all protected code.
    prefix_equal = initial.split(start)[0] == candidate.split(start)[0]
    suffix_equal = initial.split(end)[1].removesuffix("\n") == candidate.split(end)[1].removesuffix("\n")
    if not prefix_equal or not suffix_equal:
        raise ValueError("candidate changed source outside EVOLVE region")


def write_result(out: Path, metrics: dict, correct: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (out / "correct.json").write_text(json.dumps({"correct": correct}) + "\n")


def evaluate(program: Path, out: Path) -> bool:
    """Future explicitly authorized evaluations use this one fixed SEARCH path."""
    try:
        manifest = load_search()
        check_candidate(program)
        compiler = shutil.which("g++")
        if not compiler:
            raise ValueError("C++ compiler unavailable")
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pipes-search-v2-") as temporary:
            solver, interactor = Path(temporary) / "solver", Path(temporary) / "interactor"
            for command in (
                [compiler, "-O2", "-std=c++20", "-pipe", str(program.resolve()), "-o", str(solver)],
                [compiler, "-O2", "-std=c++17", "-pipe", "-I", str(TASK / "vendor"),
                 str(TASK / "vendor/interactor.cpp"), "-o", str(interactor)],
            ):
                result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
                if result.returncode:
                    raise ValueError("compile failed: " + (result.stdout + result.stderr)[-8000:])
            result = subprocess.run([
                sys.executable, str(TASK / "tools/pipes_harness.py"),
                "--solver", str(solver), "--interactor", str(interactor),
                "--tests", str(SEARCH), "--out", str(out / "harness"), "--name", "search-v2",
                "--response-timeout", "5", "--wall-timeout", "180", "--cpu-limit", "5",
                "--memory-limit-mb", "256",
            ], capture_output=True, text=True, timeout=128 * 180 + 60, check=False)
            summary = json.loads((out / "harness/summary.json").read_text())
            metrics, correct = aggregate_report(summary, manifest, SEARCH, result.returncode)
        metrics["program_sha256"] = digest(program)
        metrics["manifest_sha256"] = digest(SEARCH / "manifest.json")
        metrics["evaluator_sha256"] = digest(ROOT / "evaluator.py")
        metrics["snapshot_sha256"] = digest(ROOT / "snapshot.json")
        write_result(out, metrics, correct)
        return correct
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        write_result(out, {"combined_score": 0.0, "suite": "search", "corpus_version": "search-v2",
                           "error": str(exc), "text_feedback": "Candidate rejected: " + str(exc)}, False)
        return False
