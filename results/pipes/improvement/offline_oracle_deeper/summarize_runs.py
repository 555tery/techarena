#!/usr/bin/env python3
"""Validate and tabulate the saved offline-oracle window runs."""

import csv
import hashlib
import json
from pathlib import Path


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[3]
EXPECTED_BASELINE = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
EXPECTED_CANONICAL = "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8"
EXPECTED_RUNNER = "9e6c9f360381b6fc6f868d9fbaf687dc5d5a352def45579f95c5b2ae00ba904a"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    selection = json.loads((WORK / "selection_manifest.json").read_text())
    divergences = json.loads((WORK / "witness_divergences.json").read_text())
    divergence_by_name = {x["run"]: x for x in divergences["runs"]}
    run_rows = []
    all_valid = True
    for result_path in sorted((WORK / "runs").glob("*.json")):
        result = json.loads(result_path.read_text())
        resource_path = WORK / "resources" / f"{result_path.stem}.json"
        resource = json.loads(resource_path.read_text())
        checks = {
            "success": resource["return_code"] == 0,
            "frozen_baseline_sha": resource["baseline_source_sha256"] == EXPECTED_BASELINE,
            "runner_sha": resource["runner_binary_sha256"] == EXPECTED_RUNNER,
            "control_replay": result["baseline_control_replay_trench_m"] == result["baseline_final_trench_m"],
            "runner_resource_names_match": resource["name"] == result_path.stem,
        }
        all_valid = all_valid and all(checks.values())
        divergence = divergence_by_name[result_path.stem]
        run_rows.append({
            "run": result_path.stem,
            "window": result_path.stem.rsplit("_w", 1)[0],
            "beam_width": result["beam_width"],
            "action_cap": result["action_cap"],
            "window_start_op_1based": result["window_start_op_1based"],
            "window_count": result["window_count"],
            "baseline_final_trench_m": result["baseline_final_trench_m"],
            "witness_final_trench_m": result["best_full_suffix_witness_trench_m"],
            "witness_saving_m": result["full_suffix_witness_saving_m"],
            "best_path_divergent_placements": divergence["divergent_placement_decisions"],
            "expanded_states_generated": result["expanded_states_generated"],
            "cpu_seconds": resource["child_cpu_seconds"],
            "wall_seconds": resource["wall_seconds"],
            "peak_rss_mib": resource["peak_rss_mib"],
            "memory_limit_enforced": resource["memory_limit_enforced"],
            **{f"check_{key}": value for key, value in checks.items()},
        })

    fields = list(run_rows[0])
    with (WORK / "run_resource_summary.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(run_rows)

    configs = [(4, 6), (16, 6), (64, 6), (4, 12), (16, 12), (64, 12)]
    window_rows = []
    for window in selection["windows"]:
        row = {
            "window": window["id"],
            "input": window["input"],
            "start_op_1based": window["start_op_1based"],
            "command_count": window["command_count"],
            "baseline_final_trench_m": None,
        }
        names = []
        for width, cap in configs:
            name = f"{window['id']}_w{width}_a{cap}"
            p = WORK / "runs" / f"{name}.json"
            if p.exists():
                result = json.loads(p.read_text())
                row["baseline_final_trench_m"] = result["baseline_final_trench_m"]
                row[f"saving_w{width}_a{cap}_m"] = result["full_suffix_witness_saving_m"]
                names.append(name)
            else:
                row[f"saving_w{width}_a{cap}_m"] = "not run"
        subset = [x for x in run_rows if x["run"].startswith(window["id"] + "_")]
        row["max_cpu_seconds"] = max(x["cpu_seconds"] for x in subset)
        row["max_wall_seconds"] = max(x["wall_seconds"] for x in subset)
        row["max_peak_rss_mib"] = max(x["peak_rss_mib"] for x in subset)
        row["run_count"] = len(subset)
        window_rows.append(row)

    window_fields = list(window_rows[0])
    with (WORK / "window_summary.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=window_fields)
        writer.writeheader()
        writer.writerows(window_rows)

    frozen_sha = sha(ROOT / "results/pipes/final/solution.cpp")
    canonical_sha = sha(ROOT / "src/pipes.cpp")
    runner_sha = sha(ROOT / "results/pipes/improvement/offline_longbeam/longbeam")
    validation = {
        "run_count": len(run_rows),
        "all_runs_valid": all_valid,
        "frozen_baseline_source_sha256": frozen_sha,
        "frozen_baseline_source_matches_expected": frozen_sha == EXPECTED_BASELINE,
        "canonical_source_sha256": canonical_sha,
        "canonical_source_matches_expected": canonical_sha == EXPECTED_CANONICAL,
        "runner_binary_sha256": runner_sha,
        "runner_binary_matches_expected": runner_sha == EXPECTED_RUNNER,
        "baseline_control_exact_final_match_count": sum(x["check_control_replay"] for x in run_rows),
        "successful_return_codes_count": sum(x["check_success"] for x in run_rows),
        "open15_width64_action12_was_run": (WORK / "runs/open15_w64_a12.json").exists(),
        "open15_width64_action12_status": "Completed as a one-off high-budget diagnostic after the earlier skip; no hindsight saving found.",
        "memory_enforced": False,
        "interpretation": "Offline oracle only; positive savings are feasible hindsight witnesses, not online score gains or optimality certificates.",
    }
    (WORK / "execution_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))
    if not all_valid or frozen_sha != EXPECTED_BASELINE or canonical_sha != EXPECTED_CANONICAL or runner_sha != EXPECTED_RUNNER:
        raise SystemExit("validation failure")


if __name__ == "__main__":
    main()
