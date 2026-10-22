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


def summary(run: str) -> dict[str, object]:
    path = OUT / "runs" / run / "summary.json"
    return json.loads(path.read_text())


def per_case(run: str) -> list[dict[str, object]]:
    with (OUT / "runs" / run / "cases.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    return [
        {
            "case": row["case"],
            "status": row["status"],
            "trench_m": int(row["trench_length_m"]),
            "kpi": float(row["kpi"]),
            "solver_cpu_s": float(row["solver_cpu_total_s"]),
            "solver_rss_mib": float(row["solver_peak_rss_mb"]),
            "candidate_stderr": row["candidate_stderr"].strip(),
            "answer_sha256": sha(ROOT / row["judge_output_file"]),
        }
        for row in rows
    ]


source = OUT / "source/coalescence_option_value.cpp"
binary = OUT / "bin/coalescence_option_value"
baseline_source = ROOT / "results/pipes/improvement/case15_expansion_edge_cf/source/lifo_young_offset_scale_gt4096.cpp"
baseline_binary = OUT / "bin/baseline_scale_offset"
case15_input = OUT / "tests/case15/15.in"
synthetics = sorted((OUT / "synthetic").glob("fresh_*.in"))

baseline_case15 = summary("baseline_case15")
candidate_case15 = summary("candidate_case15")
baseline_synthetic = summary("baseline_synthetic8")
candidate_synthetic = summary("candidate_synthetic8")

clang = subprocess.run(["clang++", "--version"], check=True, capture_output=True, text=True).stdout.splitlines()[0]
manifest = {
    "experiment": "case15 causal local coalescence option-value screen",
    "date_local": "2026-10-18",
    "scope": "Local case15 and eight fixed-seed synthetic streams; no full Open15, platform, or Docker.",
    "baseline_comparator": {
        "open15_score_from_parent_manifest": 30.044966195,
        "source": str(baseline_source.relative_to(ROOT)),
        "source_sha256": sha(baseline_source),
        "binary": str(baseline_binary.relative_to(ROOT)),
        "binary_sha256": sha(baseline_binary),
        "case15_run": str((OUT / "runs/baseline_case15").relative_to(ROOT)),
        "case15_trench_m": baseline_case15["records"][0]["trench_length_m"],
        "synthetic8_run": str((OUT / "runs/baseline_synthetic8").relative_to(ROOT)),
        "synthetic8_score_sum": baseline_synthetic["weighted_score_sum"],
    },
    "candidate": {
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha(source),
        "binary": str(binary.relative_to(ROOT)),
        "binary_sha256": sha(binary),
        "policy": "At most two best-fit candidates may be skipped when a newest-5%-boundary pipe has a causal near-LIFO coalescence option whose observed demand value exceeds the extra base gap cost.",
        "case15_run": str((OUT / "runs/candidate_case15").relative_to(ROOT)),
        "case15_trench_m": candidate_case15["records"][0]["trench_length_m"],
        "case15_cpu_s": candidate_case15["records"][0]["solver_cpu_total_s"],
        "case15_rss_mib": candidate_case15["records"][0]["solver_peak_rss_mb"],
        "case15_records": per_case("candidate_case15"),
        "synthetic8_run": str((OUT / "runs/candidate_synthetic8").relative_to(ROOT)),
        "synthetic8_score_sum": candidate_synthetic["weighted_score_sum"],
        "synthetic8_records": per_case("candidate_synthetic8"),
    },
    "inputs": {
        "case15": {
            "path": str(case15_input.relative_to(ROOT)),
            "sha256": sha(case15_input),
            "operations": 200000,
        },
        "synthetics": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
            for path in synthetics
        ],
        "generator": {
            "path": str((OUT / "generate_synthetics.py").relative_to(ROOT)),
            "sha256": sha(OUT / "generate_synthetics.py"),
            "seed_base": 2026101800,
            "initial_active": 700,
            "events_per_stream": 40000,
        },
    },
    "reproduction": {
        "prepare_script": {
            "path": str((OUT / "prepare_candidate.py").relative_to(ROOT)),
            "sha256": sha(OUT / "prepare_candidate.py"),
        },
        "harness": "tools/pipes_harness.py",
        "harness_sha256": sha(ROOT / "tools/pipes_harness.py"),
        "interactor": "results/pipes/final/bin/interactor",
        "interactor_sha256": sha(ROOT / "results/pipes/final/bin/interactor"),
        "compiler": clang,
        "build_flags": "-std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS",
        "cpu_limit_s": 5,
        "memory_limit_mib": 256,
        "platform": platform.platform(),
    },
    "frozen_and_canonical": {
        "frozen_final_sha256": sha(ROOT / "results/pipes/final/solution.cpp"),
        "canonical_source_sha256": sha(ROOT / "src/pipes.cpp"),
    },
    "runs": {
        name: {
            "summary_sha256": sha(OUT / "runs" / name / "summary.json"),
            "cases_sha256": sha(OUT / "runs" / name / "cases.csv"),
            "all_ok": all(row["status"] == "ok" for row in per_case(name)),
        }
        for name in (
            "baseline_case15", "candidate_case15",
            "baseline_synthetic8", "candidate_synthetic8",
        )
    },
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(OUT / "manifest.json")
