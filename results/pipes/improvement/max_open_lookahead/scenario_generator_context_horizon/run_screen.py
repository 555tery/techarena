#!/usr/bin/env python3
"""Build and screen three predeclared causal-history MC variants."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "results/pipes/final/solution.cpp"
BASE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
FLAGS = ["-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion", "-Wshadow", "-pedantic", "-Werror"]
SCREEN_CASES = [5, 9, 15]
VARIANTS = {
    "A-context6-depth4": {"context": 6, "depth": 4},
    "B-context3-depth8": {"context": 3, "depth": 8},
    "C-context6-depth8": {"context": 6, "depth": 8},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_integer(source: str, constant: str, old: int, new: int) -> str:
    pattern = rf"(^[^\n]*\b{re.escape(constant)} = ){old}(;[^\n]*$)"
    out, count = re.subn(pattern, rf"\g<1>{new}\g<2>", source, count=1, flags=re.M)
    if count != 1:
        raise RuntimeError(f"Expected exactly one `{constant} = {old}` declaration, got {count}")
    return out


def make_source(base: str, context: int, depth: int) -> str:
    out = base
    if context != 3:
        old_line = "const std::size_t maxContext = std::min<std::size_t>(3, n - 1);"
        new_line = f"const std::size_t maxContext = std::min<std::size_t>({context}, n - 1);"
        if out.count(old_line) != 1:
            raise RuntimeError("Could not find exact maxContext line")
        out = out.replace(old_line, new_line)
    if depth != 4:
        out = set_integer(out, "kMcDepth", 4, depth)
    return out


def main() -> None:
    if sha(BASE) != BASE_SHA:
        raise SystemExit(f"Unexpected frozen final source hash: {sha(BASE)}")
    OUT.mkdir(parents=True, exist_ok=True)
    source_text = BASE.read_text()
    base_copy_dir = OUT / "baseline"
    base_copy_dir.mkdir(exist_ok=True)
    base_copy = base_copy_dir / "solution.cpp"
    base_copy.write_text(source_text)
    screen_input = OUT / "inputs" / "open_5_9_15"
    screen_input.mkdir(parents=True, exist_ok=True)
    for case in SCREEN_CASES:
        link = screen_input / f"{case}.in"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(ROOT / "data/pipes/open" / f"{case}.in")

    configs = [{"name": "00-baseline", "context": 3, "depth": 4, "directory": base_copy_dir}]
    for name, params in VARIANTS.items():
        d = OUT / "variants" / name
        d.mkdir(parents=True, exist_ok=True)
        candidate = d / "solution.cpp"
        candidate.write_text(make_source(source_text, params["context"], params["depth"]))
        configs.append({"name": name, **params, "directory": d})

    results = []
    for cfg in configs:
        d = cfg["directory"]
        source = d / "solution.cpp"
        binary = d / "solver"
        build_command = ["clang++", *FLAGS, str(source), "-o", str(binary)]
        build = subprocess.run(build_command, cwd=ROOT, text=True, capture_output=True)
        (d / "build.stdout.txt").write_text(build.stdout)
        (d / "build.stderr.txt").write_text(build.stderr)
        if build.returncode:
            raise SystemExit(f"Build failed for {cfg['name']}; inspect {d / 'build.stderr.txt'}")
        run_dir = d / "screen_5_9_15"
        run_command = [
            "python3", str(ROOT / "tools/pipes_harness.py"),
            "--solver", str(binary), "--name", cfg["name"],
            "--interactor", str(ROOT / "tools/interactor"),
            "--tests", str(screen_input), "--out", str(run_dir),
            "--cpu-limit", "5", "--memory-limit-mb", "256",
        ]
        run = subprocess.run(run_command, cwd=ROOT, text=True, capture_output=True)
        (d / "screen.stdout.txt").write_text(run.stdout)
        (d / "screen.stderr.txt").write_text(run.stderr)
        summary_path = run_dir / "summary.json"
        if run.returncode or not summary_path.exists():
            raise SystemExit(f"Screen failed for {cfg['name']}; inspect {d}")
        summary = json.loads(summary_path.read_text())
        if summary["case_count"] != 3 or summary["ok_count"] != 3:
            raise SystemExit(f"Incomplete screen result for {cfg['name']}")
        rec = {
            "name": cfg["name"], "context": cfg["context"], "depth": cfg["depth"],
            "source": str(source.relative_to(ROOT)), "source_sha256": sha(source),
            "binary": str(binary.relative_to(ROOT)), "binary_sha256": sha(binary),
            "summary": str(summary_path.relative_to(ROOT)), "summary_sha256": sha(summary_path),
            "screen_score_sum": summary["weighted_score_sum"],
            "case_count": summary["case_count"], "ok_count": summary["ok_count"],
            "max_cpu_s": max(r["solver_cpu_total_s"] for r in summary["records"]),
            "max_cpu_case": max(summary["records"], key=lambda r: r["solver_cpu_total_s"])["case"],
            "max_rss_mib": max(r["solver_peak_rss_mb"] for r in summary["records"]),
            "max_rss_case": max(summary["records"], key=lambda r: r["solver_peak_rss_mb"])["case"],
        }
        results.append(rec)
        print(f"{cfg['name']}: screen={rec['screen_score_sum']:.12f}, "
              f"maxCPU={rec['max_cpu_s']:.6f}s, maxRSS={rec['max_rss_mib']:.3f}MiB", flush=True)

    baseline_score = results[0]["screen_score_sum"]
    (OUT / "screen-results.json").write_text(json.dumps({
        "base_source_sha256": BASE_SHA,
        "screen_cases": SCREEN_CASES,
        "screen_inputs": [
            {"case": str(i), "path": f"data/pipes/open/{i}.in", "sha256": sha(ROOT / "data/pipes/open" / f"{i}.in")}
            for i in SCREEN_CASES
        ],
        "variants_predeclared": VARIANTS,
        "baseline_screen_score": baseline_score,
        "full_open_condition": "Only variants strictly above baseline_screen_score qualify for official open15.",
        "results": results,
    }, indent=2) + "\n")
    (OUT / "screen-ranking.csv").write_text(
        "name,context,depth,screen_score_sum,delta_vs_baseline,max_cpu_s,max_cpu_case,max_rss_mib,max_rss_case,source_sha256,binary_sha256,summary_sha256\n" +
        "".join(
            f"{r['name']},{r['context']},{r['depth']},{r['screen_score_sum']:.15f},"
            f"{r['screen_score_sum']-baseline_score:+.15f},{r['max_cpu_s']:.9f},{r['max_cpu_case']},"
            f"{r['max_rss_mib']:.6f},{r['max_rss_case']},{r['source_sha256']},{r['binary_sha256']},{r['summary_sha256']}\n"
            for r in results
        )
    )
    print("baseline screen", f"{baseline_score:.12f}", "qualifying variants", sum(r["screen_score_sum"] > baseline_score for r in results[1:]))


if __name__ == "__main__":
    main()
