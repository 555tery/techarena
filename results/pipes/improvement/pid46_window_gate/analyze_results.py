#!/usr/bin/env python3
"""Audit paired PID/46-window runs and preregistered gate exposure."""

import csv
import hashlib
import json
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOTSTRAP_RESAMPLES = 20000
BOOTSTRAP_SEED = 930017


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smooth_size_trend(history, current):
    if not history:
        return False
    current_run_already_in_history = history[-1] == current
    prior_run_lengths = []
    first_run = True
    last_run_length = -1
    for value in reversed(history):
        if first_run:
            first_run = False
            last_run_length = value
            if not current_run_already_in_history:
                prior_run_lengths.append(value)
            continue
        if value == last_run_length:
            continue
        last_run_length = value
        prior_run_lengths.append(value)
        if len(prior_run_lengths) == 2:
            break
    return len(prior_run_lengths) == 2 and (
        current - prior_run_lengths[0] == prior_run_lengths[0] - prior_run_lengths[1]
    )


def gate_exposure(path, phase_placements):
    lines = Path(path).read_text(encoding="ascii").splitlines()
    history = deque(maxlen=2048)
    recent_run = deque(maxlen=46)
    removal_parities = deque(maxlen=64)
    parity_counts = [0, 0]
    length_occurrences = [0] * 41
    disabled = False
    placements = 0
    run_left = 0
    gate_active_placements = 0
    run_left_and_gate = 0
    pid_parity_equals_size_cohort = 0
    gated_lane_differences = 0
    gated_lane_equal = 0
    first_trigger = None
    for raw in lines[1:]:
        command = int(raw)
        if command == 0:
            break
        if command > 0:
            if smooth_size_trend(history, command):
                disabled = True
            is_run_left = not disabled and len(history) >= 46 and \
                len(recent_run) == 46 and all(v == command for v in recent_run)
            removal_count = len(removal_parities)
            dominant = max(parity_counts)
            gate_active = removal_count >= 32 and dominant * 4 >= removal_count * 3
            pid_parity = (placements + 1) & 1
            size_cohort = length_occurrences[command] & 1
            if pid_parity == size_cohort:
                pid_parity_equals_size_cohort += 1
            if is_run_left:
                run_left += 1
            if gate_active:
                gate_active_placements += 1
            if is_run_left and gate_active:
                run_left_and_gate += 1
                if pid_parity == size_cohort:
                    gated_lane_differences += 1
                else:
                    gated_lane_equal += 1
                if first_trigger is None:
                    phase = 1 if placements < phase_placements else 2
                    first_trigger = {
                        "placement_number": placements + 1,
                        "phase": phase,
                        "removals_in_window": removal_count,
                        "dominant_parity_count": dominant,
                        "smooth_trend_latched": disabled,
                    }
            history.append(command)
            recent_run.append(command)
            length_occurrences[command] += 1
            placements += 1
        else:
            pid = -command
            if len(removal_parities) == 64:
                expired = removal_parities[0]
                parity_counts[expired] -= 1
            parity = pid & 1
            removal_parities.append(parity)
            parity_counts[parity] += 1
    return {
        "placements": placements,
        "run_left_active_placements": run_left,
        "gate_active_placements": gate_active_placements,
        "run_left_and_gate_placements": run_left_and_gate,
        "pid_parity_equals_size_cohort_placements": pid_parity_equals_size_cohort,
        "gated_pid_vs_size_cohort_lane_differences": gated_lane_differences,
        "gated_pid_vs_size_cohort_lane_equal_placements": gated_lane_equal,
        "smooth_trend_latched": disabled,
        "first_run_left_and_gate": first_trigger,
    }


def rows_by_case(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return {row["case"]: row for row in csv.DictReader(stream)}


def percentile(values, pct):
    values = sorted(values)
    position = (len(values) - 1) * pct
    low = int(position)
    high = min(low + 1, len(values) - 1)
    fraction = position - low
    return values[low] * (1.0 - fraction) + values[high] * fraction


def bootstrap_mean_ci(values):
    rng = random.Random(BOOTSTRAP_SEED)
    size = len(values)
    means = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        means.append(sum(values[rng.randrange(size)] for _ in range(size)) / size)
    return {
        "n_streams": size,
        "mean": sum(values) / size,
        "ci95_percentile": [percentile(means, 0.025), percentile(means, 0.975)],
        "positive_streams": sum(value > 0 for value in values),
        "negative_streams": sum(value < 0 for value in values),
        "zero_streams": sum(value == 0 for value in values),
    }


def analyze_split(split):
    baseline_csv = ROOT / (split + "-baseline-run") / "cases.csv"
    candidate_csv = ROOT / (split + "-candidate-run") / "cases.csv"
    baseline = rows_by_case(baseline_csv)
    candidate = rows_by_case(candidate_csv)
    configs = json.loads((ROOT / split / "stream_manifest.json").read_text(encoding="utf-8"))
    config_by_name = {Path(item["path"]).name: item for item in configs}
    paired = []
    all_ok = True
    identical_transcripts = 0
    for case, base in baseline.items():
        cand = candidate[case]
        if base["status"] != "ok" or cand["status"] != "ok":
            all_ok = False
        same_input = base["test_sha256"] == cand["test_sha256"]
        if not same_input:
            all_ok = False
        base_transcript_sha = sha256(base["judge_output_file"])
        candidate_transcript_sha = sha256(cand["judge_output_file"])
        same_transcript = base_transcript_sha == candidate_transcript_sha
        if same_transcript:
            identical_transcripts += 1
        config = config_by_name[Path(base["test_file"]).name]
        parity_exposed = any(
            policy in ("parity_even", "parity_odd")
            for policy in (config["primary_policy"], config["phase2_policy"])
        )
        exposure = gate_exposure(base["test_file"], config["phase_placements"])
        paired.append({
            "case": case,
            "seed": config["seed"],
            "primary_policy": config["primary_policy"],
            "phase2_policy": config["phase2_policy"],
            "phase1_run_length": config["phase1_run_length"],
            "phase2_run_length": config["phase2_run_length"],
            "phase1_profile": config["phase1_profile"],
            "phase2_profile": config["phase2_profile"],
            "phase1_churn": config["phase1_churn"],
            "phase2_churn": config["phase2_churn"],
            "parity_exposed": parity_exposed,
            "input_sha256": base["test_sha256"],
            "same_input": same_input,
            "baseline_status": base["status"],
            "candidate_status": cand["status"],
            "baseline_kpi": float(base["kpi"]),
            "candidate_kpi": float(cand["kpi"]),
            "delta_kpi": float(cand["kpi"]) - float(base["kpi"]),
            "baseline_trench_m": int(base["trench_length_m"]),
            "candidate_trench_m": int(cand["trench_length_m"]),
            "delta_trench_m": int(cand["trench_length_m"]) - int(base["trench_length_m"]),
            "baseline_cpu_s": float(base["solver_cpu_total_s"]),
            "candidate_cpu_s": float(cand["solver_cpu_total_s"]),
            "baseline_rss_mib": float(base["solver_peak_rss_mb"]),
            "candidate_rss_mib": float(cand["solver_peak_rss_mb"]),
            "same_transcript": same_transcript,
            "baseline_transcript_sha256": base_transcript_sha,
            "candidate_transcript_sha256": candidate_transcript_sha,
            **exposure,
        })
    return paired, all_ok, identical_transcripts


def summarize(paired, all_ok, identical_transcripts, split):
    overall = bootstrap_mean_ci([row["delta_kpi"] for row in paired])
    exposed = [row["delta_kpi"] for row in paired if row["parity_exposed"]]
    controls = [row["delta_kpi"] for row in paired if not row["parity_exposed"]]
    resource_rows = [row for row in paired]
    decision = None
    if split == "validation":
        decision = {
            "all_transcripts_ok_and_inputs_paired": all_ok,
            "overall_mean_at_least_0_0001": overall["mean"] >= 0.0001,
            "overall_ci95_lower_above_zero": overall["ci95_percentile"][0] > 0,
            "parity_exposed_mean_positive": bootstrap_mean_ci(exposed)["mean"] > 0,
            "parity_exposed_ci95_lower_above_zero": bootstrap_mean_ci(exposed)["ci95_percentile"][0] > 0,
            "pure_nonparity_control_mean_nonnegative": bootstrap_mean_ci(controls)["mean"] >= 0,
            "resources_within_limits": all(
                row["candidate_cpu_s"] < 5.0 and row["candidate_rss_mib"] < 256.0
                for row in resource_rows
            ),
        }
        decision["pass"] = all(decision.values())
    return {
        "split": split,
        "stream_count": len(paired),
        "all_transcripts_ok_and_inputs_paired": all_ok,
        "identical_transcripts": identical_transcripts,
        "whole_stream_bootstrap_overall": overall,
        "whole_stream_bootstrap_parity_exposed": bootstrap_mean_ci(exposed),
        "whole_stream_bootstrap_pure_nonparity_controls": bootstrap_mean_ci(controls),
        "total_baseline_weighted_score": sum(row["baseline_kpi"] for row in paired),
        "total_candidate_weighted_score": sum(row["candidate_kpi"] for row in paired),
        "total_score_delta": sum(row["delta_kpi"] for row in paired),
        "streams_with_lower_candidate_trench": sum(row["delta_trench_m"] < 0 for row in paired),
        "streams_with_higher_candidate_trench": sum(row["delta_trench_m"] > 0 for row in paired),
        "streams_with_same_trench": sum(row["delta_trench_m"] == 0 for row in paired),
        "candidate_max_cpu_s": max(row["candidate_cpu_s"] for row in paired),
        "candidate_max_rss_mib": max(row["candidate_rss_mib"] for row in paired),
        "run_left_active_placements": sum(row["run_left_active_placements"] for row in paired),
        "run_left_and_gate_placements": sum(row["run_left_and_gate_placements"] for row in paired),
        "gate_active_placements": sum(row["gate_active_placements"] for row in paired),
        "pid_parity_equals_size_cohort_placements": sum(
            row["pid_parity_equals_size_cohort_placements"] for row in paired
        ),
        "gated_pid_vs_size_cohort_lane_differences": sum(
            row["gated_pid_vs_size_cohort_lane_differences"] for row in paired
        ),
        "gated_pid_vs_size_cohort_lane_equal_placements": sum(
            row["gated_pid_vs_size_cohort_lane_equal_placements"] for row in paired
        ),
        "decision_checks": decision,
    }


def main():
    paired_all = {}
    summaries = {}
    for split in ("train", "validation"):
        paired, all_ok, identical = analyze_split(split)
        paired_all[split] = paired
        summaries[split] = summarize(paired, all_ok, identical, split)
        with (ROOT / ("paired_" + split + ".csv")).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(paired[0].keys()))
            writer.writeheader()
            writer.writerows(paired)
    output = {
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "summaries": summaries,
        "validation_gate_pass": summaries["validation"]["decision_checks"]["pass"],
    }
    (ROOT / "analysis.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
