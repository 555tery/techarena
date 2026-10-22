"""Shared local evaluator for fixed synthetic suites; no work on import."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
TASK = ROOT / "task-synthetic"
SEARCH = TASK / "data/search"
VALIDATION = ROOT / "validation-v1/data"
CPU_LIMIT, RSS_LIMIT = 5.0, 256.0


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_suite(path: Path, expected_split: str) -> dict:
    if expected_split not in {"search", "validation"}:
        raise ValueError("only synthetic search and validation are supported")
    protocol = json.loads((ROOT / "corpus-protocol.json").read_text())
    if digest(path / "manifest.json") != protocol["manifest_sha256"][expected_split]:
        raise ValueError("corpus manifest differs from the frozen protocol")
    manifest = json.loads((path / "manifest.json").read_text())
    if manifest["split"] != expected_split or manifest["version"] != "synthetic-v1":
        raise ValueError("unexpected corpus split or version")
    cases = manifest["cases"]
    names = [c["file"] for c in cases]
    if (len(cases) != manifest["case_count"] or len(set(names)) != len(names)
            or any(Path(name).name != name for name in names)
            or set(names) != {p.name for p in path.glob("*.in")}):
        raise ValueError("incomplete, duplicate or unexpected suite inputs")
    for case in cases:
        if digest(path / case["file"]) != case["sha256"]:
            raise ValueError(f"input checksum mismatch: {case['file']}")
    return manifest


def check_prepared_suites() -> dict:
    search, validation = load_suite(SEARCH, "search"), load_suite(VALIDATION, "validation")
    hashes = [{c["sha256"] for c in suite["cases"]} for suite in (search, validation)]
    seeds = [{c["seed"] for c in suite["cases"]} for suite in (search, validation)]
    if hashes[0] & hashes[1] or seeds[0] & seeds[1]:
        raise ValueError("search/validation overlap")
    if any(len(values) != suite["case_count"] for values, suite in zip(hashes, (search, validation))):
        raise ValueError("duplicate input content within a suite")
    if not set(validation["held_out_mechanisms"]).isdisjoint(search["families"]):
        raise ValueError("reserved validation mechanism leaked into search")
    if (TASK / "data/open").exists() or VALIDATION.is_relative_to(TASK):
        raise ValueError("non-search inputs inside the active task")
    protocol = json.loads((ROOT / "corpus-protocol.json").read_text())
    for name, expected in protocol["open15_sha256"].items():
        if digest(ROOT.parent / name) != expected:
            raise ValueError("Open15 preservation check failed")
    return {"search_cases": search["case_count"], "search_families": len(search["families"]),
            "validation_cases": validation["case_count"], "validation_families": len(validation["families"]),
            "validation_reserved_families": validation["held_out_mechanisms"],
            "overlapping_streams": 0, "open15_preserved": True, "open15_used_in_search": False}


def aggregate_report(summary: dict, manifest: dict, suite_path: Path, returncode: int) -> tuple[dict, bool]:
    """Normalize terminal KPI by its volume upper bound, then balance families."""
    records = summary.get("records", [])
    expected = {c["file"]: c for c in manifest["cases"]}
    grouped, raw, feedback = defaultdict(list), [], []
    seen, cpu, rss = set(), [], []
    if returncode != 0 or len(records) != len(expected):
        raise ValueError("harness failed or case coverage is incomplete")
    for record in records:
        file = Path(record["test_file"])
        if (file.name not in expected or file.name in seen
                or file.resolve() != (suite_path / file.name).resolve()):
            raise ValueError("unexpected or duplicate case in harness report")
        seen.add(file.name)
        spec = expected[file.name]
        if record["test_sha256"] != spec["sha256"] or record["status"] != "ok":
            raise ValueError("wrong input or invalid solver result")
        cpu_s, rss_mb = float(record["solver_cpu_total_s"]), float(record["solver_peak_rss_mb"])
        trench, lower = float(record["trench_length_m"]), spec["stats"]["volume_lower_bound"]
        kpi = float(record["kpi"])
        if not all(math.isfinite(x) for x in (cpu_s, rss_mb, trench, kpi)):
            raise ValueError("nonfinite score or resource measurement")
        if (not 0 <= cpu_s < CPU_LIMIT or not 0 <= rss_mb < RSS_LIMIT
                or record.get("solver_cpu_limit_exceeded") or record.get("solver_memory_limit_exceeded")):
            raise ValueError("solver resource limit exceeded")
        if (trench < lower or trench <= 0 or trench % 20 != 0
                or record["minimum_trench_lower_bound_m"] != lower
                or record["final_occupied_length_m"] != spec["stats"]["final_live_volume"]
                or not math.isclose(kpi, spec["stats"]["final_live_volume"] / trench, abs_tol=1e-10)):
            raise ValueError("inconsistent trench, volume bound or KPI")
        ratio = lower / trench
        grouped[spec["family"]].append(ratio)
        raw.append(kpi)
        cpu.append(cpu_s)
        rss.append(rss_mb)
        feedback.append(f"case={spec['id']} family={spec['family']} normalized={ratio:.9f} "
                        f"trench={int(trench)} bound={lower} cpu_s={cpu_s:.6f} rss_mib={rss_mb:.3f}")
    family_scores = {family: sum(values) / len(values) for family, values in sorted(grouped.items())}
    if seen != set(expected) or set(family_scores) != set(manifest["families"]):
        raise ValueError("family or case coverage mismatch")
    fitness = sum(family_scores.values()) / len(family_scores)
    return {
        "combined_score": fitness, "suite": manifest["split"], "corpus_version": manifest["version"],
        "public": {"valid_cases": len(seen), "family_count": len(family_scores),
                   "worst_family_score": min(family_scores.values()), "mean_raw_kpi": sum(raw) / len(raw),
                   "max_solver_cpu_seconds": max(cpu), "max_solver_rss_mib": max(rss)},
        "family_scores": family_scores, "text_feedback": "\n".join(feedback),
        "fitness_definition": "family-balanced mean of rounded peak live volume / trench length",
    }, True


def check_candidate(path: Path) -> None:
    initial, candidate = (TASK / "initial.cpp").read_text(), path.read_text()
    start, end = "// EVOLVE-BLOCK-START", "// EVOLVE-BLOCK-END"
    for text in (initial, candidate):
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            raise ValueError("expected one ordered mutable region")
    prefix, rest = initial.split(start)
    _, suffix = rest.split(end)
    if not candidate.startswith(prefix + start) or not candidate.endswith(end + suffix):
        raise ValueError("immutable source code changed")


def write_result(out: Path, metrics: dict, correct: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    (out / "correct.json").write_text(json.dumps({"correct": correct}) + "\n")


def evaluate(program: Path, out: Path, split: str = "search") -> bool:
    """Called only by a real authorized search or explicit validation invocation."""
    try:
        suite = SEARCH if split == "search" else VALIDATION if split == "validation" else None
        if suite is None:
            raise ValueError("unknown split; Open15 is not an evaluation option")
        manifest = load_suite(suite, split)
        check_candidate(program)
        compiler = shutil.which("g++")
        if not compiler:
            raise ValueError("C++ compiler unavailable")
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pipes-synthetic-") as temporary:
            solver, interactor = Path(temporary) / "solver", Path(temporary) / "interactor"
            builds = [[compiler, "-O2", "-std=c++20", "-pipe", str(program.resolve()), "-o", str(solver)],
                      [compiler, "-O2", "-std=c++17", "-pipe", "-I", str(TASK / "vendor"),
                       str(TASK / "vendor/interactor.cpp"), "-o", str(interactor)]]
            for command in builds:
                result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
                if result.returncode:
                    raise ValueError("compile failed: " + (result.stdout + result.stderr)[-8000:])
            result = subprocess.run([
                sys.executable, str(TASK / "tools/pipes_harness.py"), "--solver", str(solver),
                "--interactor", str(interactor), "--tests", str(suite), "--out", str(out / "harness"),
                "--name", f"synthetic-{split}", "--response-timeout", "5", "--wall-timeout", "180",
                "--cpu-limit", str(CPU_LIMIT), "--memory-limit-mb", str(RSS_LIMIT),
            ], capture_output=True, text=True, timeout=len(manifest["cases"]) * 180 + 60, check=False)
            summary = json.loads((out / "harness/summary.json").read_text())
            metrics, correct = aggregate_report(summary, manifest, suite, result.returncode)
        metrics["program_sha256"] = digest(program)
        metrics["manifest_sha256"] = digest(suite / "manifest.json")
        write_result(out, metrics, correct)
        print(f"suite={split} combined_score={metrics['combined_score']:.12g} correct={correct}")
        return correct
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        write_result(out, {"combined_score": 0.0, "suite": split, "error": str(exc),
                           "text_feedback": "Candidate rejected: " + str(exc)}, False)
        return False
