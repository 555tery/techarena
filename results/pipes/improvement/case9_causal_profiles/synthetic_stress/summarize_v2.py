#!/usr/bin/env python3
"""Summarize the fresh-seed v2 stress run for geometric size prediction."""

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cases(path):
    with path.open(newline="") as stream:
        return {r["case"]: r for r in csv.DictReader(stream)}

inputs = json.loads((HERE / "inputs_v2.json").read_text())
base = cases(HERE / "champion_v2" / "cases.csv")
candidate = cases(HERE / "candidate_v2" / "cases.csv")
trace_root = HERE / "trace_v2" / "runs"
triggers = {}
for run in trace_root.iterdir():
    starts = []
    for line in (run / "solver_stderr.txt").read_text().splitlines():
        if line.startswith("COHORT_START"):
            starts.append(dict(x.split("=", 1) for x in line.split()[1:])["len"])
    triggers[run.name] = starts

rows = []
for spec in inputs["cases"]:
    name = spec["name"]
    a, b = base[name], candidate[name]
    rows.append({
        "case": name,
        "operations": spec["operations"],
        "baseline_trench_m": a["trench_length_m"],
        "candidate_trench_m": b["trench_length_m"],
        "delta_trench_m": int(b["trench_length_m"]) - int(a["trench_length_m"]),
        "baseline_kpi": a["kpi"],
        "candidate_kpi": b["kpi"],
        "delta_kpi": float(b["kpi"]) - float(a["kpi"]),
        "cohort_trigger_lengths": ";".join(triggers.get(name, [])),
        "input_sha256": spec["sha256"],
    })

csv_path = HERE / "per_case_comparison_v2.csv"
with csv_path.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

base_summary = json.loads((HERE / "champion_v2" / "summary.json").read_text())
candidate_summary = json.loads((HERE / "candidate_v2" / "summary.json").read_text())
trace_summary = json.loads((HERE / "trace_v2" / "summary.json").read_text())
manifest = {
    "suite": inputs["suite"],
    "master_seed": inputs["master_seed"],
    "inputs": inputs["cases"],
    "baseline_source_sha256": sha(ROOT / "results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1.cpp"),
    "candidate_source_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/source/cohort_slabs_geometric_capacity.cpp"),
    "candidate_binary_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/bin/cohort_slabs_geometric_capacity"),
    "trace_binary_sha256": sha(ROOT / "results/pipes/improvement/case9_causal_profiles/bin/cohort_slabs_geometric_capacity_trace"),
    "generator_sha256": sha(HERE / "generate_v2.py"),
    "comparison_csv_sha256": sha(csv_path),
    "baseline_sum_kpi": base_summary["weighted_score_sum"],
    "candidate_sum_kpi": candidate_summary["weighted_score_sum"],
    "delta_sum_kpi": candidate_summary["weighted_score_sum"] - base_summary["weighted_score_sum"],
    "max_candidate_cpu_s": max(r["solver_cpu_total_s"] for r in candidate_summary["records"]),
    "max_candidate_rss_mib": max(r["solver_peak_rss_mb"] for r in candidate_summary["records"]),
    "trigger_lengths_by_case": triggers,
    "trace_max_cpu_s": max(r["solver_cpu_total_s"] for r in trace_summary["records"]),
    "trace_max_rss_mib": max(r["solver_peak_rss_mb"] for r in trace_summary["records"]),
    "interpretation": "Fresh targeted stress suite, no threshold tuning; not an estimate of hidden-test score.",
}
(HERE / "manifest_v2.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"wrote {csv_path} and {HERE / 'manifest_v2.json'}")
