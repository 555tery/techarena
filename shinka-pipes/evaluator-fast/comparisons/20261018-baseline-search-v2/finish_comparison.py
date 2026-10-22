#!/usr/bin/env python3
"""Complete the comparison with one quiet reference run after the user pause."""

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
SUPPORT = OUT.parents[1]
sys.path.insert(0, str(SUPPORT))
from compare_baseline import run_one, write_json
from compare_reports import compare
from reference import BASE, check_reference, digest


def recompute(directory, manifest):
    summary = json.loads((directory / "harness/summary.json").read_text())
    metrics = json.loads((directory / "metrics.json").read_text())
    expected = {case["file"]: case for case in manifest["cases"]}
    grouped = {family: [] for family in manifest["families"]}
    for record in summary["records"]:
        case = expected[Path(record["test_file"]).name]
        bound, trench = case["stats"]["volume_lower_bound"], record["trench_length_m"]
        assert record["minimum_trench_lower_bound_m"] == bound
        assert record["final_occupied_length_m"] == case["stats"]["final_live_volume"]
        assert trench >= bound > 0 and trench % 20 == 0
        assert record["kpi"] == case["stats"]["final_live_volume"] / trench
        grouped[case["family"]].append(bound / trench)
    assert len(summary["records"]) == 128 and all(len(values) == 8 for values in grouped.values())
    families = {family: sum(values) / len(values) for family, values in sorted(grouped.items())}
    fitness = sum(families.values()) / len(families)
    assert families == metrics["family_scores"]
    assert fitness == metrics["combined_score"]
    return {"family_scores": families, "combined_score": fitness, "cases": 128}


def main():
    print("Waiting for the first reference/accelerated pair to complete.", flush=True)
    while True:
        status = json.loads((OUT / "status.json").read_text())
        if status["phase"] in ("failed", "mismatch"):
            raise RuntimeError(f"first pair failed: {status}")
        if status["phase"] == "complete":
            break
        time.sleep(2)
    initial = json.loads((OUT / "comparison.json").read_text())
    assert initial["ok"] and not initial["mismatches"]
    preflight = json.loads((OUT / "preflight.json").read_text())
    active = json.loads((BASE / "active-run.json").read_text())
    run = Path(active["run_dir"])
    run_manifest = run / "run-manifest.json"
    manifest_before = run_manifest.read_bytes()
    assert json.loads(manifest_before)["status"] == "paused_by_user"
    assert subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode != 0
    reference_before = check_reference()
    assert reference_before == preflight["reference"]
    assert digest(OUT / "baseline.cpp") == preflight["baseline_sha256"]
    write_json(OUT / "quiet-reference-reason.json", {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "reason": "User paused main Shinka during first reference run; repeat reference once so both full runs have main Shinka stopped.",
        "excluded_from_final_speedup": "reference", "final_pair_order": ["accelerated", "reference-paused"],
        "planned_total_full_baseline_evaluations": 3, "evolution_generations": 0, "model_calls": 0,
        "pause_record": str(OUT / "background-shinka-pause.json"),
    }, exclusive=True)
    quiet_timing = run_one("reference-paused", BASE / "task/evaluate.py", OUT / "baseline.cpp",
                           OUT / "reference-paused", OUT)
    manifest = json.loads((OUT / "search-manifest.json").read_text())
    report = compare(OUT / "reference-paused", OUT / "accelerated", manifest, BASE / "task/data/search")
    fast_timing = json.loads((OUT / "accelerated-timing.json").read_text())
    report["timings"] = {"reference_paused": quiet_timing, "accelerated": fast_timing}
    report["end_to_end_speedup"] = quiet_timing["end_to_end_wall_s"] / fast_timing["end_to_end_wall_s"]
    report["end_to_end_time_reduction_fraction"] = 1 - fast_timing["end_to_end_wall_s"] / quiet_timing["end_to_end_wall_s"]
    report["independent_recomputation"] = {label: recompute(OUT / label, manifest)
                                            for label in ("reference", "accelerated", "reference-paused")}
    report["matches_historical_baseline_score"] = all(
        row["combined_score"] == preflight["saved_baseline_score"]
        for row in report["independent_recomputation"].values())
    report["main_shinka_stopped_for_both_final_runs"] = (
        run_manifest.read_bytes() == manifest_before
        and subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode != 0)
    report["reference_files_unchanged"] = check_reference() == reference_before
    report["input_baseline_unchanged"] = digest(OUT / "baseline.cpp") == preflight["baseline_sha256"]
    report["all_initial_runtime_files_unchanged"] = all(digest(Path(path)) == sha
                                                       for path, sha in preflight["implementation_sha256"].items())
    report["source_files_sha256"] = {
        "comparison_tool": digest(SUPPORT / "compare_reports/__init__.py"),
        "finalization_tool": digest(Path(__file__).resolve()),
    }
    report["timing_scope"] = "one full accelerated/reference pair, both with main Shinka stopped; ordinary host load and order effects remain uncontrolled"
    report["excluded_reference_timing"] = json.loads((OUT / "reference-timing.json").read_text())
    write_json(OUT / "controlled-comparison.json", report, exclusive=True)
    old_records = {record["case"]: record for record in json.loads((OUT / "reference-paused/harness/summary.json").read_text())["records"]}
    fast_records = {record["case"]: record for record in json.loads((OUT / "accelerated/harness/summary.json").read_text())["records"]}
    fields = ["case", "family", "bound_m", "trench_m", "score_bound_over_trench", "old_wall_s", "fast_wall_s",
              "wall_speedup", "old_solver_cpu_s", "fast_solver_cpu_s", "old_solver_rss_mib", "fast_solver_rss_mib", "transcript_identical"]
    with (OUT / "per-case-comparison.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case in manifest["cases"]:
            key = Path(case["file"]).stem
            old, fast = old_records[key], fast_records[key]
            writer.writerow({
                "case": key, "family": case["family"], "bound_m": old["minimum_trench_lower_bound_m"],
                "trench_m": old["trench_length_m"], "score_bound_over_trench": old["lower_bound_to_actual_trench_ratio"],
                "old_wall_s": old["wall_orchestration_s"], "fast_wall_s": fast["wall_orchestration_s"],
                "wall_speedup": old["wall_orchestration_s"] / fast["wall_orchestration_s"],
                "old_solver_cpu_s": old["solver_cpu_total_s"], "fast_solver_cpu_s": fast["solver_cpu_total_s"],
                "old_solver_rss_mib": old["solver_peak_rss_mb"], "fast_solver_rss_mib": fast["solver_peak_rss_mb"],
                "transcript_identical": report["artifacts"]["per_case"][key]["judge_output_sha256"]["equal"],
            })
    success = (report["ok"] and not report["mismatches"] and report["matches_historical_baseline_score"]
               and report["main_shinka_stopped_for_both_final_runs"] and report["reference_files_unchanged"]
               and report["input_baseline_unchanged"] and report["all_initial_runtime_files_unchanged"])
    write_json(OUT / "status.json", {"phase": "verified-complete" if success else "controlled-mismatch",
                                     "completed_at": datetime.now(timezone.utc).isoformat(),
                                     "report": str(OUT / "controlled-comparison.json")})
    print(json.dumps({"success": success, "end_to_end_speedup": report["end_to_end_speedup"],
                      "counts": report["counts"], "resources": {k: report["resources"][k] for k in ("old", "fast")}}, indent=2), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
