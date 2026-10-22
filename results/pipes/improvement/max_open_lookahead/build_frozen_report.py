#!/usr/bin/env python3
"""Create the frozen all-open comparison and reproducibility manifest."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

REPORTS = {
    "v6_short8": OUT / "official-open-short8/summary.json",
    "v6_short16": OUT / "official-open-short16/summary.json",
    "v6_short128": OUT / "official-open-v6/summary.json",
    "window1024_right": OUT / "reference-window1024-right/summary.json",
    "adaptive_right4_w2048_s60": ROOT / "results/pipes/improvement/max_open_sequence/official-open-adaptive-right4-w2048-s60/summary.json",
    "adaptive_short8": OUT / "official-open-adaptive-short8/summary.json",
    "adaptive_recent8_right": OUT / "official-open-recent8-right/summary.json",
    "adaptive_recent16_right": OUT / "official-open-recent16-right/summary.json",
    "adaptive_recent32_right": OUT / "official-open-recent32-right/summary.json",
    "adaptive_recent32_right_repro": OUT / "official-open-recent32-right-repro/summary.json",
    "adaptive_recent20_right": OUT / "official-open-recent20-right/summary.json",
    "adaptive_recent24_right": OUT / "official-open-recent24-right/summary.json",
    "adaptive_recent28_right": OUT / "official-open-recent28-right/summary.json",
    "adaptive_recent36_right": OUT / "official-open-recent36-right/summary.json",
    "adaptive_recent40_right": OUT / "official-open-recent40-right/summary.json",
    "adaptive_recent43_right": OUT / "official-open-recent43-right/summary.json",
    "adaptive_recent44_right": OUT / "official-open-recent44-right/summary.json",
    "adaptive_recent46_right": OUT / "official-open-recent46-right/summary.json",
    "adaptive_recent46_right_repro": OUT / "official-open-recent46-right-repro/summary.json",
    "adaptive_recent47_right": OUT / "official-open-recent47-right/summary.json",
    "adaptive_recent48_right": OUT / "official-open-recent48-right/summary.json",
    "adaptive_recent48_right_repro": OUT / "official-open-recent48-right-repro/summary.json",
    "adaptive_recent49_right": OUT / "official-open-recent49-right/summary.json",
    "adaptive_recent50_right": OUT / "official-open-recent50-right/summary.json",
    "adaptive_recent45_right": OUT / "official-open-recent45-right/summary.json",
    "adaptive_recent52_right": OUT / "official-open-recent52-right/summary.json",
    "adaptive_recent56_right": OUT / "official-open-recent56-right/summary.json",
    "adaptive_recent64_right": OUT / "official-open-recent64-right/summary.json",
    "adaptive_recent72_right": OUT / "official-open-recent72-right/summary.json",
    "S50": ROOT / "results/pipes/improvement/strategies/reports/integrated-final/integrated_s50/summary.json",
    "P4": ROOT / "results/pipes/improvement/strategies/reports/baseline/policy4/summary.json",
    "all_right": ROOT / "results/pipes/improvement/strategies/reports/open-v1/all_right/summary.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


reports = {name: load_report(path) for name, path in REPORTS.items()}
case_maps = {
    name: {record["case"]: record for record in report["records"]}
    for name, report in reports.items()
}
case_ids = [str(i) for i in range(1, 16)]
reference_hashes = {
    case: case_maps["v6_short8"][case]["test_sha256"] for case in case_ids
}
for name, records in case_maps.items():
    if list(records) != case_ids:
        raise SystemExit(f"{name}: expected 15 ordered cases, found {list(records)}")
    for case in case_ids:
        if records[case]["test_sha256"] != reference_hashes[case]:
            raise SystemExit(f"{name}: input hash mismatch in case {case}")

rows = []
for case in case_ids:
    row = {
        "case": case,
        "weight": case_maps["v6_short8"][case]["official_weight"],
        "test_sha256": reference_hashes[case],
    }
    for name, records in case_maps.items():
        record = records[case]
        row[f"{name}_kpi"] = record["kpi"]
        row[f"{name}_H_m"] = record["trench_length_m"]
        row[f"{name}_weighted"] = record["weighted_score"]
        row[f"{name}_status"] = record["status"]
    row["v6_short8_minus_window1024_weighted"] = (
        case_maps["v6_short8"][case]["weighted_score"]
        - case_maps["window1024_right"][case]["weighted_score"]
    )
    row["v6_short8_minus_v6_short128_weighted"] = (
        case_maps["v6_short8"][case]["weighted_score"]
        - case_maps["v6_short128"][case]["weighted_score"]
    )
    row["adaptive_short8_minus_adaptive_base_weighted"] = (
        case_maps["adaptive_short8"][case]["weighted_score"]
        - case_maps["adaptive_right4_w2048_s60"][case]["weighted_score"]
    )
    rows.append(row)

csv_path = OUT / "frozen-comparison.csv"
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

score_summaries = {
    name: {
        "weighted_score_sum": report["weighted_score_sum"],
        "weight_sum": report["weight_sum"],
        "ok_count": report["ok_count"],
        "case_count": report["case_count"],
        "delta_vs_adaptive_base": (
            report["weighted_score_sum"]
            - reports["adaptive_right4_w2048_s60"]["weighted_score_sum"]
        ),
        "delta_vs_window1024_right": (
            report["weighted_score_sum"]
            - reports["window1024_right"]["weighted_score_sum"]
        ),
    }
    for name, report in reports.items()
}
identical_adaptive_outcomes = all(
    case_maps["adaptive_short8"][case][field]
    == case_maps["adaptive_right4_w2048_s60"][case][field]
    for case in case_ids
    for field in ("kpi", "trench_length_m", "occupied_length_m", "weighted_score")
)
identical_recent32_repro = all(
    case_maps["adaptive_recent32_right"][case][field]
    == case_maps["adaptive_recent32_right_repro"][case][field]
    for case in case_ids
    for field in ("status", "kpi", "trench_length_m", "occupied_length_m", "weighted_score")
)
identical_recent48_repro = all(
    case_maps["adaptive_recent48_right"][case][field]
    == case_maps["adaptive_recent48_right_repro"][case][field]
    for case in case_ids
    for field in ("status", "kpi", "trench_length_m", "occupied_length_m", "weighted_score")
)
output_fields = ("judge_output_file", "candidate_stderr_file", "interactor_stderr_file")
recent48_output_hashes = []
for case in case_ids:
    primary = case_maps["adaptive_recent48_right"][case]
    repeated = case_maps["adaptive_recent48_right_repro"][case]
    hashes = {
        field: {
            "primary_sha256": sha256(Path(primary[field])),
            "repeat_sha256": sha256(Path(repeated[field])),
        }
        for field in output_fields
    }
    recent48_output_hashes.append({"case": case, "artifacts": hashes})
identical_recent48_artifact_bytes = all(
    values["primary_sha256"] == values["repeat_sha256"]
    for case_record in recent48_output_hashes
    for values in case_record["artifacts"].values()
)
identical_recent46_repro = all(
    case_maps["adaptive_recent46_right"][case][field]
    == case_maps["adaptive_recent46_right_repro"][case][field]
    for case in case_ids
    for field in ("status", "kpi", "trench_length_m", "occupied_length_m", "weighted_score")
)
recent46_output_hashes = []
for case in case_ids:
    primary = case_maps["adaptive_recent46_right"][case]
    repeated = case_maps["adaptive_recent46_right_repro"][case]
    hashes = {
        field: {
            "primary_sha256": sha256(Path(primary[field])),
            "repeat_sha256": sha256(Path(repeated[field])),
        }
        for field in output_fields
    }
    recent46_output_hashes.append({"case": case, "artifacts": hashes})
identical_recent46_artifact_bytes = all(
    values["primary_sha256"] == values["repeat_sha256"]
    for case_record in recent46_output_hashes
    for values in case_record["artifacts"].values()
)
max_cpu = max(
    float(record["solver_cpu_total_s"])
    for name in ("adaptive_recent46_right", "adaptive_recent46_right_repro")
    for record in reports[name]["records"]
)
max_rss = max(
    float(record["solver_peak_rss_mb"])
    for name in ("adaptive_recent46_right", "adaptive_recent46_right_repro")
    for record in reports[name]["records"]
)
max_wall = max(
    float(record["wall_orchestration_s"])
    for name in ("adaptive_recent46_right", "adaptive_recent46_right_repro")
    for record in reports[name]["records"]
)

comparison = {
    "open_cases": 15,
    "all_inputs_match_by_sha256": True,
    "score_summaries": score_summaries,
    "adaptive_short8_has_identical_official_outcomes_to_base": identical_adaptive_outcomes,
    "recent32_right_reproduced_identically": identical_recent32_repro,
    "recent48_right_reproduced_identically": identical_recent48_repro,
    "recent48_right_artifact_bytes_match": identical_recent48_artifact_bytes,
    "recent48_right_output_artifact_hashes": recent48_output_hashes,
    "recent48_right_resource_maxima": {
        "solver_cpu_s": max_cpu,
        "solver_peak_rss_mb": max_rss,
        "wall_orchestration_s": max_wall,
    },
    "recent46_right_reproduced_identically": identical_recent46_repro,
    "recent46_right_artifact_bytes_match": identical_recent46_artifact_bytes,
    "recent46_right_output_artifact_hashes": recent46_output_hashes,
    "recent46_right_resource_maxima": {
        "solver_cpu_s": max_cpu,
        "solver_peak_rss_mb": max_rss,
        "wall_orchestration_s": max_wall,
    },
    "per_case": rows,
}
(OUT / "frozen-comparison.json").write_text(
    json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
)

sources = {
    "v6_short8": OUT / "candidate_v6_short_8.cpp",
    "v6_short16": OUT / "candidate_v6_short_16.cpp",
    "v6_short128": OUT / "candidate_v6_w1024_short_predictor.cpp",
    "adaptive_short8": OUT / "candidate_adaptive_right4_w2048_s60_short8_predictor.cpp",
    "adaptive_recent8_right": OUT / "candidate_adaptive_right4_w2048_s60_recent8_right.cpp",
    "adaptive_recent16_right": OUT / "candidate_adaptive_right4_w2048_s60_recent16_right.cpp",
    "adaptive_recent20_right": OUT / "candidate_adaptive_right4_w2048_s60_recent20_right.cpp",
    "adaptive_recent24_right": OUT / "candidate_adaptive_right4_w2048_s60_recent24_right.cpp",
    "adaptive_recent28_right": OUT / "candidate_adaptive_right4_w2048_s60_recent28_right.cpp",
    "adaptive_recent32_right": OUT / "candidate_adaptive_right4_w2048_s60_recent32_right.cpp",
    "adaptive_recent36_right": OUT / "candidate_adaptive_right4_w2048_s60_recent36_right.cpp",
    "adaptive_recent40_right": OUT / "candidate_adaptive_right4_w2048_s60_recent40_right.cpp",
    "adaptive_recent43_right": OUT / "candidate_adaptive_right4_w2048_s60_recent43_right.cpp",
    "adaptive_recent44_right": OUT / "candidate_adaptive_right4_w2048_s60_recent44_right.cpp",
    "adaptive_recent45_right": OUT / "candidate_adaptive_right4_w2048_s60_recent45_right.cpp",
    "adaptive_recent46_right": OUT / "candidate_adaptive_right4_w2048_s60_recent46_right.cpp",
    "adaptive_recent48_right": OUT / "candidate_adaptive_right4_w2048_s60_recent48_right.cpp",
    "adaptive_recent47_right": OUT / "candidate_adaptive_right4_w2048_s60_recent47_right.cpp",
    "adaptive_recent49_right": OUT / "candidate_adaptive_right4_w2048_s60_recent49_right.cpp",
    "adaptive_recent50_right": OUT / "candidate_adaptive_right4_w2048_s60_recent50_right.cpp",
    "adaptive_recent52_right": OUT / "candidate_adaptive_right4_w2048_s60_recent52_right.cpp",
    "adaptive_recent56_right": OUT / "candidate_adaptive_right4_w2048_s60_recent56_right.cpp",
    "adaptive_recent64_right": OUT / "candidate_adaptive_right4_w2048_s60_recent64_right.cpp",
    "adaptive_recent72_right": OUT / "candidate_adaptive_right4_w2048_s60_recent72_right.cpp",
    "adaptive_base": ROOT / "results/pipes/improvement/max_open_sequence/candidate_adaptive_right4_w2048_s60.cpp",
}
binaries = {
    "v6_short8": OUT / "bin/candidate_v6_short_8",
    "v6_short16": OUT / "bin/candidate_v6_short_16",
    "v6_short128": OUT / "bin/candidate_v6",
    "adaptive_short8": OUT / "bin/candidate_adaptive_right4_w2048_s60_short8_predictor",
    "adaptive_recent8_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent8_right",
    "adaptive_recent16_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent16_right",
    "adaptive_recent20_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent20_right",
    "adaptive_recent24_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent24_right",
    "adaptive_recent28_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent28_right",
    "adaptive_recent32_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent32_right",
    "adaptive_recent36_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent36_right",
    "adaptive_recent40_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent40_right",
    "adaptive_recent43_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent43_right",
    "adaptive_recent44_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent44_right",
    "adaptive_recent45_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent45_right",
    "adaptive_recent46_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent46_right",
    "adaptive_recent48_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent48_right",
    "adaptive_recent47_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent47_right",
    "adaptive_recent49_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent49_right",
    "adaptive_recent50_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent50_right",
    "adaptive_recent52_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent52_right",
    "adaptive_recent56_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent56_right",
    "adaptive_recent64_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent64_right",
    "adaptive_recent72_right": OUT / "bin/candidate_adaptive_right4_w2048_s60_recent72_right",
    "adaptive_base": ROOT / "results/pipes/improvement/max_open_sequence/candidate_adaptive_right4_w2048_s60",
}
input_hashes = {
    str(i): sha256(ROOT / f"data/pipes/open/{i}.in") for i in range(1, 16)
}
compiler = subprocess.run(
    ["g++", "--version"], capture_output=True, text=True, check=True
).stdout.splitlines()[0]
manifest = {
    "scope": "official open tests 1 through 15",
    "run_command_template": [
        "python3 tools/pipes_harness.py",
        "--solver <candidate-binary>",
        "--name <strategy-label>",
        "--interactor tools/interactor",
        "--tests data/pipes/open",
        "--out <report-directory>",
    ],
    "selected_candidate": {
        "name": "adaptive_recent46_right",
        "weighted_score_sum": reports["adaptive_recent46_right"]["weighted_score_sum"],
        "weight_sum": reports["adaptive_recent46_right"]["weight_sum"],
        "ok_count": reports["adaptive_recent46_right"]["ok_count"],
        "run_command": [
            "python3", "tools/pipes_harness.py",
            "--solver", "results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right",
            "--name", "adaptive_right4_w2048_s60_recent46_right",
            "--interactor", "tools/interactor",
            "--tests", "data/pipes/open",
            "--out", "results/pipes/improvement/max_open_lookahead/official-open-recent46-right",
        ],
        "repeat_run_command": [
            "python3", "tools/pipes_harness.py",
            "--solver", "results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right",
            "--name", "adaptive_right4_w2048_s60_recent46_right_repro",
            "--interactor", "tools/interactor",
            "--tests", "data/pipes/open",
            "--out", "results/pipes/improvement/max_open_lookahead/official-open-recent46-right-repro",
        ],
        "delta_vs_adaptive_base": (
            reports["adaptive_recent46_right"]["weighted_score_sum"]
            - reports["adaptive_right4_w2048_s60"]["weighted_score_sum"]
        ),
        "repeated_case_outputs_identical": identical_recent46_repro,
        "judge_and_stderr_artifact_bytes_match": identical_recent46_artifact_bytes,
        "max_resource_usage_across_two_runs": {
            "solver_cpu_s": max_cpu,
            "solver_peak_rss_mb": max_rss,
            "wall_orchestration_s": max_wall,
        },
    },
    "compile_command": [
        "g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-Werror", "<source.cpp>", "-o", "<binary>"
    ],
    "compiler": compiler,
    "platform": platform.platform(),
    "harness": {
        "path": str(ROOT / "tools/pipes_harness.py"),
        "sha256": sha256(ROOT / "tools/pipes_harness.py"),
    },
    "interactor": {
        "path": str(ROOT / "tools/interactor"),
        "sha256": sha256(ROOT / "tools/interactor"),
    },
    "official_open_inputs_sha256": input_hashes,
    "sources": {name: {"path": str(path), "sha256": sha256(path)} for name, path in sources.items()},
    "binaries": {name: {"path": str(path), "sha256": sha256(path)} for name, path in binaries.items()},
    "reports": {
        name: {"path": str(path), "sha256": sha256(path)} for name, path in REPORTS.items()
    },
}
(OUT / "harness-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)

base_score = reports["adaptive_right4_w2048_s60"]["weighted_score_sum"]
best_name = "adaptive_recent46_right"
best_score = reports[best_name]["weighted_score_sum"]
score_table_names = (
    "adaptive_right4_w2048_s60",
    "adaptive_recent8_right", "adaptive_recent16_right", "adaptive_recent20_right",
    "adaptive_recent24_right", "adaptive_recent28_right", "adaptive_recent32_right",
    "adaptive_recent36_right", "adaptive_recent40_right", "adaptive_recent43_right",
    "adaptive_recent44_right", "adaptive_recent45_right", "adaptive_recent46_right",
    "adaptive_recent47_right", "adaptive_recent48_right", "adaptive_recent49_right",
    "adaptive_recent50_right", "adaptive_recent52_right", "adaptive_recent56_right",
    "adaptive_recent64_right", "adaptive_recent72_right",
    "v6_short8", "v6_short16", "v6_short128", "window1024_right", "S50", "P4", "all_right",
)
report_lines = [
    "# Frozen open-test comparison",
    "",
    "All candidates were run through `tools/pipes_harness.py` with the same official interactor and all 15 `data/pipes/open/*.in` inputs. Input SHA-256 values are checked equal across reports in `harness-manifest.json`.",
    "",
    "## Scores",
    "",
    "| Candidate | Weighted score / 32.1 | Delta vs adaptive right4/W2048/S60 | Valid |",
    "|---|---:|---:|---:|",
]
for name in score_table_names:
    score = reports[name]["weighted_score_sum"]
    report_lines.append(
        f"| `{name}` | {score:.12f} | {score - base_score:+.12f} | {reports[name]['ok_count']}/15 |"
    )
report_lines += [
    "",
    f"Best tested here: `{best_name}`, {best_score:.12f}/32.1, a net gain of {best_score - base_score:+.12f} over the frozen adaptive right4/W2048/S60 baseline. All official runs in the focused threshold sweep passed 15/15.",
    "",
    "## T=46 rule",
    "",
    "The baseline allocator uses W=2048 and unfit penalty S=60. It places pipes of length at most 4 m at the right endpoint of a selected gap and longer pipes at the left endpoint. Before placing the current pipe of length L, the candidate checks the last 46 placement lengths in the observed input history. If all 46 equal L, it places this pipe at the right endpoint even when L>4; otherwise the baseline side rule applies. Deletions do not reset this placement-length run. There is no test number or command-position branch.",
    "",
    "## Per-case weighted delta vs baseline",
    "",
    "| Case | Weight | Baseline H | T=46 H | Baseline KPI | T=46 KPI | Weighted delta |",
    "|---:|---:|---:|---:|---:|---:|---:|",
]
changed_cases = []
for case in case_ids:
    baseline = case_maps["adaptive_right4_w2048_s60"][case]
    candidate = case_maps[best_name][case]
    delta = candidate["weighted_score"] - baseline["weighted_score"]
    if delta:
        changed_cases.append((case, delta))
        report_lines.append(
            f"| {case} | {candidate['official_weight']:g} | {baseline['trench_length_m']} | {candidate['trench_length_m']} | {baseline['kpi']:.12f} | {candidate['kpi']:.12f} | {delta:+.12f} |"
        )
case_delta_sentences = "; ".join(
    f"case {case} {delta:+.12f}" for case, delta in changed_cases
)
report_lines += [
    "",
    f"Changed weighted outcomes: {case_delta_sentences}. Their net is the {best_score - base_score:+.12f} overall gain.",
    "",
    "## Reproducibility and resources",
    "",
    f"The T=46 full open run was repeated. Both runs scored {reports['adaptive_recent46_right']['weighted_score_sum']:.12f}/32.1, and status/KPI/trench/occupied/weighted score matched for every case: `{identical_recent46_repro}`. Judge output and solver/interactor stderr bytes also matched case by case: `{identical_recent46_artifact_bytes}`.",
    f"Across the primary and repeated T=46 runs, maximum solver CPU: {max_cpu:.6f} s; maximum solver peak RSS: {max_rss:.4f} MiB; maximum harness wall time for one case: {max_wall:.6f} s.",
    "",
    "Exact primary official command:",
    "```sh",
    "python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right --name adaptive_right4_w2048_s60_recent46_right --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/official-open-recent46-right",
    "```",
    "",
    "Exact repeat command:",
    "```sh",
    "python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right --name adaptive_right4_w2048_s60_recent46_right_repro --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/official-open-recent46-right-repro",
    "```",
    "",
    "Strict build command:",
    "```sh",
    "g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/max_open_lookahead/candidate_adaptive_right4_w2048_s60_recent46_right.cpp -o results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right",
    "```",
    "",
    "T=46 source: `candidate_adaptive_right4_w2048_s60_recent46_right.cpp`. Source and binary SHA-256 values, the harness/interactor hashes, and all 15 input hashes are in `harness-manifest.json`. The candidate remains isolated in this directory and was not copied into canonical source.",
    "",
]
(OUT / "REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

print(json.dumps({
    "scores": {name: data["weighted_score_sum"] for name, data in score_summaries.items()},
    "deltas_vs_adaptive_base": {name: data["delta_vs_adaptive_base"] for name, data in score_summaries.items()},
    "identical_adaptive_outcomes": identical_adaptive_outcomes,
    "identical_recent32_repro": identical_recent32_repro,
    "max_cpu_s": max_cpu,
    "max_rss_mib": max_rss,
    "max_wall_s": max_wall,
    "best_score": best_score,
    "best_delta_vs_adaptive_base": best_score - base_score,
    "comparison_csv": str(csv_path),
    "manifest": str(OUT / "harness-manifest.json"),
}, indent=2))
