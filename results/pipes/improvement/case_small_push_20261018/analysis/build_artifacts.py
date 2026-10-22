#!/usr/bin/env python3
"""Build the compact comparison table and provenance manifest."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
EXP = ROOT / "results/pipes/improvement/case_small_push_20261018"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        return {r["case"]: r for r in csv.DictReader(f)}


comparison = []


def add_pair(label: str, baseline_csv: Path, candidate_csv: Path,
             selected: list[str] | None = None) -> None:
    base = rows(baseline_csv)
    cand = rows(candidate_csv)
    keys = selected if selected is not None else sorted(base)
    for case in keys:
        b, c = base[case], cand[case]
        comparison.append({
            "comparison": label,
            "case": case,
            "baseline_trench_m": b["trench_length_m"],
            "candidate_trench_m": c["trench_length_m"],
            "delta_trench_m": str(int(c["trench_length_m"]) - int(b["trench_length_m"])),
            "baseline_weighted_score": b["weighted_score"],
            "candidate_weighted_score": c["weighted_score"],
            "delta_weighted_score": f"{float(c['weighted_score'])-float(b['weighted_score']):.12f}",
            "baseline_status": b["status"],
            "candidate_status": c["status"],
        })


add_pair("neighbor_tie_target", EXP / "runs/base_case12/cases.csv",
         EXP / "runs/candidate_case12/cases.csv")
add_pair("neighbor_tie_target", EXP / "runs/base_case14/cases.csv",
         EXP / "runs/candidate_case14/cases.csv")
add_pair("small_expansion_offset_case12", EXP / "runs/base_case12/cases.csv",
         EXP / "runs/expansion_candidate_case12/cases.csv")
add_pair("unit_profile_suppression_case14", EXP / "runs/base_case14/cases.csv",
         EXP / "runs/unit_suppression_case14/cases.csv")
add_pair("neighbor_tie_synthetic16", EXP / "runs/synthetic_base/cases.csv",
         EXP / "runs/synthetic_candidate/cases.csv")
add_pair("unit_profile_suppression_synthetic8", EXP / "runs/unit_v2_base/cases.csv",
         EXP / "runs/unit_v2_candidate/cases.csv")
add_pair("unit_profile_suppression_open15", ROOT / "results/pipes/improvement/case15_expansion_edge_cf/runs/scale_gt4096_open15/cases.csv",
         EXP / "runs/unit_suppress_open15/cases.csv")

with (EXP / "comparison.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(comparison[0]))
    writer.writeheader()
    writer.writerows(comparison)

candidate_open = json.loads((EXP / "runs/unit_suppress_open15/summary.json").read_text())
base_open = json.loads((ROOT / "results/pipes/improvement/case15_expansion_edge_cf/runs/scale_gt4096_open15/summary.json").read_text())
candidate_open_cases = rows(EXP / "runs/unit_suppress_open15/cases.csv")
base_open_cases = rows(ROOT / "results/pipes/improvement/case15_expansion_edge_cf/runs/scale_gt4096_open15/cases.csv")

source_names = [
    "source/base_ab.cpp",
    "source/current_champion.cpp",
    "source/lifo_neighbor_tie.cpp",
    "source/small_mixed_lifo_expansion_offset.cpp",
    "source/unit_profile_suppress_scale_offset.cpp",
]
binary_names = [
    "bin/base_ab",
    "bin/current_champion",
    "bin/lifo_neighbor_tie",
    "bin/small_mixed_lifo_expansion_offset",
    "bin/unit_profile_suppress_scale_offset",
]
synthetic_inputs = sorted((EXP / "synthetic").rglob("*.in"))
open_inputs = sorted((ROOT / "data/pipes/open").glob("*.in"))

run_roots = [
    EXP / "runs/base_case12", EXP / "runs/candidate_case12",
    EXP / "runs/base_case14", EXP / "runs/candidate_case14",
    EXP / "runs/expansion_candidate_case12", EXP / "runs/unit_suppression_case14",
    EXP / "runs/synthetic_base", EXP / "runs/synthetic_candidate",
    EXP / "runs/unit_v2_base", EXP / "runs/unit_v2_candidate",
    EXP / "runs/unit_suppress_open15",
]
run_artifacts = {}
for run in run_roots:
    rel = run.relative_to(ROOT).as_posix()
    files = [run / "cases.csv", run / "summary.json"]
    files.extend(sorted(run.glob("runs/*/judge_output.txt")))
    run_artifacts[rel] = {p.relative_to(ROOT).as_posix(): sha(p) for p in files if p.exists()}

manifest = {
    "experiment": "case 12/14 LIFO neighbor ties and unit-profile expansion gate",
    "date": "2026-10-17",
    "baseline": {
        "current_local_champion_score": base_open["weighted_score_sum"],
        "current_local_champion_source_sha256": sha(ROOT / "results/pipes/improvement/case15_expansion_edge_cf/source/lifo_young_offset_scale_gt4096.cpp"),
        "current_local_champion_binary_sha256": sha(ROOT / "results/pipes/improvement/case15_expansion_edge_cf/bin/lifo_young_offset_scale_gt4096"),
        "a_plus_b_score": 30.04308919953782,
        "a_plus_b_source_sha256": sha(ROOT / "results/pipes/improvement/case5_additive_next_alignment_20261017/src/staircase_plus_additive_next_alignment.cpp"),
    },
    "candidate": {
        "source": "results/pipes/improvement/case_small_push_20261018/source/unit_profile_suppress_scale_offset.cpp",
        "source_sha256": sha(EXP / "source/unit_profile_suppress_scale_offset.cpp"),
        "binary": "results/pipes/improvement/case_small_push_20261018/bin/unit_profile_suppress_scale_offset",
        "binary_sha256": sha(EXP / "bin/unit_profile_suppress_scale_offset"),
        "build": "clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS source/unit_profile_suppress_scale_offset.cpp -o bin/unit_profile_suppress_scale_offset",
        "policy": "Suppress the incumbent expansion offset when at least 85% of the latest up-to-2048 placement lengths are exactly 1m; all other incumbent offset conditions remain unchanged.",
        "open15": {
            "weighted_score_sum": candidate_open["weighted_score_sum"],
            "cases_ok": candidate_open["ok_count"],
            "delta_vs_current_champion": candidate_open["weighted_score_sum"] - base_open["weighted_score_sum"],
            "changed_cases": [
                {"case": k, "base_trench_m": base_open_cases[k]["trench_length_m"],
                 "candidate_trench_m": candidate_open_cases[k]["trench_length_m"],
                 "delta_score": float(candidate_open_cases[k]["weighted_score"]) - float(base_open_cases[k]["weighted_score"])}
                for k in sorted(base_open_cases, key=int)
                if base_open_cases[k]["trench_length_m"] != candidate_open_cases[k]["trench_length_m"]
            ],
            "max_solver_cpu_s": max(float(r["solver_cpu_total_s"]) for r in candidate_open_cases.values()),
            "max_solver_rss_mib": max(float(r["solver_peak_rss_mb"]) for r in candidate_open_cases.values()),
        },
    },
    "tested_variants": {
        "lifo_neighbor_tie": {"decision": "no-go", "case12_delta_trench_m": 20, "case14_delta_trench_m": 0,
                              "fresh_synthetic_count": 16, "open15_run": False},
        "small_mixed_lifo_expansion_offset": {"decision": "no-go", "case12_delta_trench_m": 240,
                                                "fresh_synthetic_count": 0, "open15_run": False},
        "unit_profile_suppress_scale_offset": {"decision": "local_gain", "case14_delta_trench_m": -20,
                                               "fresh_synthetic_count": 8, "open15_run": True},
    },
    "synthetic_manifests": {
        "neighbor_tie": "results/pipes/improvement/case_small_push_20261018/synthetic/manifest.json",
        "unit_profile_suppression": "results/pipes/improvement/case_small_push_20261018/synthetic/unit_profile_v2/manifest.json",
    },
    "hashes": {
        "sources": {p: sha(EXP / p) for p in source_names},
        "binaries": {p: sha(EXP / p) for p in binary_names},
        "open_inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in open_inputs},
        "synthetic_inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in synthetic_inputs},
        "tools": {
            "tools/interactor": sha(ROOT / "tools/interactor"),
            "tools/pipes_harness.py": sha(ROOT / "tools/pipes_harness.py"),
        },
        "run_artifacts": run_artifacts,
        "report_sha256": sha(EXP / "REPORT.md"),
        "comparison_csv_sha256": sha(EXP / "comparison.csv"),
        "synthetic_manifests": {
            "synthetic/manifest.json": sha(EXP / "synthetic/manifest.json"),
            "synthetic/unit_profile_v2/manifest.json": sha(EXP / "synthetic/unit_profile_v2/manifest.json"),
        },
    },
    "limits": {"cpu_s": 5, "memory_mib": 256},
    "canonical_source_sha256_after": sha(ROOT / "src/pipes.cpp"),
    "frozen_source_sha256_after": sha(ROOT / "results/pipes/final/solution.cpp"),
    "canonical_and_frozen_modified": False,
    "website_used": False,
    "docker_used": False,
    "commands": [
        "python3 tools/pipes_harness.py --solver bin/current_champion --interactor tools/interactor --tests data/pipes/open/12.in --out runs/base_case12 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/lifo_neighbor_tie --interactor tools/interactor --tests data/pipes/open/12.in --out runs/candidate_case12 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/current_champion --interactor tools/interactor --tests data/pipes/open/14.in --out runs/base_case14 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/lifo_neighbor_tie --interactor tools/interactor --tests data/pipes/open/14.in --out runs/candidate_case14 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/small_mixed_lifo_expansion_offset --interactor tools/interactor --tests data/pipes/open/12.in --out runs/expansion_candidate_case12 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/unit_profile_suppress_scale_offset --interactor tools/interactor --tests data/pipes/open/14.in --out runs/unit_suppression_case14 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/current_champion --interactor tools/interactor --tests synthetic --out runs/synthetic_base --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/lifo_neighbor_tie --interactor tools/interactor --tests synthetic --out runs/synthetic_candidate --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/current_champion --interactor tools/interactor --tests synthetic --out runs/unit_v2_base --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/unit_profile_suppress_scale_offset --interactor tools/interactor --tests synthetic/unit_profile_v2 --out runs/unit_v2_candidate --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver bin/unit_profile_suppress_scale_offset --interactor tools/interactor --tests data/pipes/open --out runs/unit_suppress_open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
    ],
}
(EXP / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"comparison_rows": len(comparison),
                  "candidate_open15": manifest["candidate"]["open15"],
                  "report_sha256": manifest["hashes"]["report_sha256"],
                  "manifest": str(EXP / "manifest.json")}, indent=2))
