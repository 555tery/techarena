#!/usr/bin/env python3
"""Summarize frozen champion/candidate stress runs and diagnostic triggers."""

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]

def read_cases(path):
    with path.open(newline="") as stream:
        return {row["case"]: row for row in csv.DictReader(stream)}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

inputs = json.loads((HERE / "inputs.json").read_text())
champion = read_cases(HERE / "champion" / "cases.csv")
candidate = read_cases(HERE / "candidate" / "cases.csv")
trace_dir = HERE / "trace" / "runs"
triggers = {}
for run in trace_dir.iterdir():
    stderr = run / "solver_stderr.txt"
    starts = []
    if stderr.exists():
        for line in stderr.read_text().splitlines():
            if line.startswith("COHORT_START"):
                fields = dict(item.split("=", 1) for item in line.split()[1:])
                starts.append(fields["len"])
    triggers[run.name] = starts

rows = []
for spec in inputs["cases"]:
    name = spec["name"]
    base, cand = champion[name], candidate[name]
    rows.append({
        "case": name,
        "operations": spec["operations"],
        "baseline_trench_m": base["trench_length_m"],
        "candidate_trench_m": cand["trench_length_m"],
        "delta_trench_m": int(cand["trench_length_m"]) - int(base["trench_length_m"]),
        "baseline_kpi": base["kpi"],
        "candidate_kpi": cand["kpi"],
        "delta_kpi": float(cand["kpi"]) - float(base["kpi"]),
        "cohort_trigger_lengths": ";".join(triggers.get(name, [])),
        "input_sha256": spec["sha256"],
    })

csv_path = HERE / "per_case_comparison.csv"
with csv_path.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

baseline_summary = json.loads((HERE / "champion" / "summary.json").read_text())
candidate_summary = json.loads((HERE / "candidate" / "summary.json").read_text())
trace_summary = json.loads((HERE / "trace" / "summary.json").read_text())
manifest = {
    "suite": inputs["suite"],
    "master_seed": inputs["master_seed"],
    "cases": inputs["cases"],
    "baseline_source_sha256": sha(ROOT / "results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1.cpp"),
    "baseline_binary_sha256": sha(ROOT / "results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1"),
    "candidate_source_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp"),
    "candidate_binary_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs"),
    "trace_binary_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs_stress_trace"),
    "generator_sha256": sha(HERE / "generate.py"),
    "comparison_csv_sha256": sha(csv_path),
    "baseline": {
        "sum_kpi": baseline_summary["weighted_score_sum"],
        "max_cpu_s": max(r["solver_cpu_total_s"] for r in baseline_summary["records"]),
        "max_rss_mib": max(r["solver_peak_rss_mb"] for r in baseline_summary["records"]),
    },
    "candidate": {
        "sum_kpi": candidate_summary["weighted_score_sum"],
        "delta_sum_kpi": candidate_summary["weighted_score_sum"] - baseline_summary["weighted_score_sum"],
        "max_cpu_s": max(r["solver_cpu_total_s"] for r in candidate_summary["records"]),
        "max_rss_mib": max(r["solver_peak_rss_mb"] for r in candidate_summary["records"]),
    },
    "trigger_lengths_by_case": triggers,
    "trace_max_cpu_s": max(r["solver_cpu_total_s"] for r in trace_summary["records"]),
    "trace_max_rss_mib": max(r["solver_peak_rss_mb"] for r in trace_summary["records"]),
    "interpretation": "Targeted synthetic stress check only; includes both gains and a phase-shift regression; not an estimate of hidden-test performance.",
}
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"wrote {csv_path} and {HERE / 'manifest.json'}")
