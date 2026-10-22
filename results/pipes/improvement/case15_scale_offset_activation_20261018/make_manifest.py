from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def records(run: str) -> list[dict[str, object]]:
    with (OUT / "runs" / run / "cases.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = []
    for row in rows:
        item: dict[str, object] = {
            "case": row["case"],
            "test_sha256": row["test_sha256"],
            "status": row["status"],
            "trench_m": int(row["trench_length_m"]),
            "kpi": float(row["kpi"]),
            "solver_cpu_s": float(row["solver_cpu_total_s"]),
            "solver_rss_mib": float(row["solver_peak_rss_mb"]),
            "answer_sha256": sha(ROOT / row["judge_output_file"]),
        }
        if row["candidate_stderr"].strip():
            item["solver_diagnostics"] = row["candidate_stderr"].strip()
        result.append(item)
    return result


def run_info(name: str) -> dict[str, object]:
    run = OUT / "runs" / name
    summary = json.loads((run / "summary.json").read_text())
    rows = records(name)
    return {
        "summary_path": str((run / "summary.json").relative_to(ROOT)),
        "summary_sha256": sha(run / "summary.json"),
        "cases_path": str((run / "cases.csv").relative_to(ROOT)),
        "cases_sha256": sha(run / "cases.csv"),
        "all_ok": summary["ok_count"] == summary["case_count"],
        "score_sum": summary["weighted_score_sum"],
        "max_solver_cpu_s": max(row["solver_cpu_s"] for row in rows),
        "max_solver_rss_mib": max(row["solver_rss_mib"] for row in rows),
        "records": rows,
    }


ab_source = OUT / "source/ab_candidate.cpp"
scale_source = OUT / "source/scale_gt4096.cpp"
ab_original = ROOT / "results/pipes/improvement/case5_additive_next_alignment_20261017/src/staircase_plus_additive_next_alignment.cpp"
scale_original = ROOT / "results/pipes/improvement/case15_expansion_edge_cf/source/lifo_young_offset_scale_gt4096.cpp"
ab_binary = OUT / "bin/ab_candidate"
scale_binary = OUT / "bin/scale_gt4096"
interactor = ROOT / "results/pipes/final/bin/interactor"
manifest = json.loads((OUT / "synthetic/manifest.json").read_text())
synthetic_hashes = {
    f"synthetic/{record['name']}.in": record["input_sha256"]
    for record in manifest
}
synthetic = [
    {
        **record,
        "path": str((OUT / f"synthetic/{record['name']}.in").relative_to(ROOT)),
    }
    for record in manifest
]
clang = subprocess.run(["clang++", "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]

data = {
    "experiment": "scale_gt4096 active-count and gate-activation qualification",
    "date_local": "2026-10-18",
    "scope": "Four fresh 105k-command synthetic streams; local harness only; no website or Docker.",
    "prior_open15_scores_not_rerun": {
        "AB": 30.04308919953782,
        "scale_gt4096": 30.044966195,
        "source_report": "results/pipes/improvement/case15_expansion_edge_cf/manifest.json",
    },
    "policy": {
        "scale_gt4096_source_sha256": sha(scale_source),
        "gate": "dig required; positive post-dig slack; activePipeCount > 4096; >=48 recent delete ranks with >=80% in newest 5%; >=90% recent lengths <=8m; old tail neighbor in newest 5% by active PID rank.",
        "activation_metric": "expansion_gate_passes from the candidate's MC_ROLLOUT_DIAGNOSTICS stderr; this counter increments only when the complete offset condition is true.",
    },
    "comparators": {
        "AB": {
            "source": str(ab_source.relative_to(ROOT)),
            "source_sha256": sha(ab_source),
            "source_matches_original": sha(ab_source) == sha(ab_original),
            "original_source_sha256": sha(ab_original),
            "binary": str(ab_binary.relative_to(ROOT)),
            "binary_sha256": sha(ab_binary),
        },
        "scale_gt4096": {
            "source": str(scale_source.relative_to(ROOT)),
            "source_sha256": sha(scale_source),
            "source_matches_original": sha(scale_source) == sha(scale_original),
            "original_source_sha256": sha(scale_original),
            "binary": str(scale_binary.relative_to(ROOT)),
            "binary_sha256": sha(scale_binary),
        },
    },
    "synthetics": synthetic,
    "runs": {
        "AB": run_info("AB"),
        "scale_gt4096": run_info("scale_gt4096"),
    },
    "reproduction": {
        "generator": {
            "path": str((OUT / "generate_synthetics.py").relative_to(ROOT)),
            "sha256": sha(OUT / "generate_synthetics.py"),
        },
        "manifest_path": str((OUT / "synthetic/manifest.json").relative_to(ROOT)),
        "manifest_sha256": sha(OUT / "synthetic/manifest.json"),
        "harness": "tools/pipes_harness.py",
        "harness_sha256": sha(ROOT / "tools/pipes_harness.py"),
        "interactor": str(interactor.relative_to(ROOT)),
        "interactor_sha256": sha(interactor),
        "compiler": clang,
        "build_flags": "-std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS",
        "cpu_limit_s": 5,
        "memory_limit_mib": 256,
        "platform": platform.platform(),
        "input_hashes": synthetic_hashes,
    },
    "frozen_and_canonical": {
        "frozen_final_sha256": sha(ROOT / "results/pipes/final/solution.cpp"),
        "canonical_source_sha256": sha(ROOT / "src/pipes.cpp"),
    },
}
(OUT / "manifest.json").write_text(json.dumps(data, indent=2) + "\n")
print(OUT / "manifest.json")
