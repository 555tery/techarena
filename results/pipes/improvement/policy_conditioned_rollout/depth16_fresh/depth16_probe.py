#!/usr/bin/env python3
"""Post-hoc fixed depth-16 policy-conditioned rollout extension."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
LEGACY_PROBE = ROOT / "results/pipes/improvement/joint_gap_portfolio_probe/probe.py"
SPEC = importlib.util.spec_from_file_location("joint_gap_probe", LEGACY_PROBE)
assert SPEC is not None and SPEC.loader is not None
joint = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = joint
SPEC.loader.exec_module(joint)

TRAINING_SPLIT = "train"
VALIDATION_SPLIT = "validation"
SNAPSHOT_CADENCE = 60
MIN_COMMAND_INDEX = 180
SCENARIO_DEPTH = 16
SCENARIO_TRIALS = 16
BOOTSTRAP_SAMPLES = 20_000
BOOTSTRAP_SEED = 20261022

# The imported history-only sampler reads these module constants at call time.
joint.SCENARIO_DEPTH = SCENARIO_DEPTH
joint.SCENARIO_TRIALS = SCENARIO_TRIALS


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_commands(path: Path) -> list[int]:
    tokens = path.read_text(encoding="utf-8").split()
    if len(tokens) < 3:
        raise RuntimeError(f"bad input header: {path}")
    count = int(tokens[1])
    commands = [int(value) for value in tokens[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError(f"bad command count/terminator: {path}")
    return commands


def read_solver_output(binary: Path, commands: list[int]) -> list[list[int]]:
    proc = subprocess.run(
        [str(binary)], input="\n".join(map(str, commands)) + "\n",
        text=True, capture_output=True, check=True,
    )
    lines = [line.strip() for line in proc.stdout.splitlines()]
    expected = sum(command != 0 for command in commands)
    if len(lines) != expected:
        raise RuntimeError(f"{binary.name}: expected {expected} replies, got {len(lines)}")
    return [[int(token) for token in line.split()] for line in lines]


def p4_place(sim, length: int, *, record_observation: bool = True) -> tuple[int, int]:
    """Policy 4: shortest fitting interval, then lowest address; always left edge."""
    fits = [
        (end - start, start)
        for start, (end, _cohort) in sim.gaps.items()
        if end - start >= length
    ]
    digs = 0
    if fits:
        _gap_length, start = min(fits)
        start, _ = sim._place_at(start, length, False)
    else:
        tail = sim.tail_start()
        tail_start = sim.trench if tail is None else tail
        tail_length = sim.trench - tail_start
        digs = max(0, (length - tail_length + joint.DIG - 1) // joint.DIG)
        if tail is not None:
            del sim.gaps[tail]
        sim.trench += digs * joint.DIG
        start = tail_start
        remainder = start + length
        if remainder < sim.trench:
            sim._add_gap(remainder, sim.trench, -1)
    size_cohort = sim.length_occurrences[length] % 2
    sim._append_pipe(length, start, size_cohort)
    if record_observation:
        sim.observations.append((1, length))
    return digs, start


def p4_action(sim, length: int):
    fits = [
        (end - start, start)
        for start, (end, _cohort) in sim.gaps.items()
        if end - start >= length
    ]
    if not fits:
        return None
    _gap_length, start = min(fits)
    return joint.Action(start=start, high_side=False, label="P4")


def baseline_action(sim, length: int):
    high_side = sim.high_side(length)
    start = sim.best_gap(length, high_side, sim.length_occurrences[length] % 2)
    if start is None:
        return None
    return joint.Action(start=start, high_side=high_side, label="frozen-noMC")


def apply_policy_event(sim, event: tuple[int, int], policy: str) -> None:
    kind, value = event
    if kind > 0:
        if policy == "P4":
            p4_place(sim, value)
        else:
            sim.place(value)
    elif kind < 0:
        sim.remove_rank(value)


def rollout_value(sim, length: int, action, scenarios, policy: str) -> float:
    base_trench = sim.trench
    rolled = sim.clone()
    rolled.place_candidate(length, action)
    for scenario in scenarios:
        branch = rolled.clone()
        for event in scenario:
            apply_policy_event(branch, event, policy)
        # Preserve paired candidate/scenario averaging, without any tail proxy.
        yield float(branch.trench - base_trench)


def mean_rollout_value(sim, length: int, action, scenarios, policy: str) -> float:
    values = list(rollout_value(sim, length, action, scenarios, policy))
    return sum(values) / len(values) if values else math.inf


def exact_suffix(sim, length: int, action, commands: list[int], begin: int, policy: str) -> int:
    state = sim.clone()
    initial = state.trench
    state.place_candidate(length, action)
    for command in commands[begin:]:
        if command == 0:
            break
        if command > 0:
            if policy == "P4":
                p4_place(state, command)
            else:
                state.place(command)
        else:
            state.remove_pid(-command)
    return state.trench - initial


def pair_accuracy(predicted: list[float], actual: list[int]) -> float | None:
    if len(actual) != 2 or actual[0] == actual[1]:
        return None
    if predicted[0] == predicted[1]:
        return 0.5
    return float((predicted[0] < predicted[1]) == (actual[0] < actual[1]))


def top1_regret(predicted: list[float], actual: list[int]) -> int | None:
    if len(actual) != 2:
        raise ValueError("expected two policy candidates")
    chosen = 0 if predicted[0] <= predicted[1] else 1
    return actual[chosen] - min(actual)


def run_baseline_transcript(commands: list[int], outputs: list[list[int]], collect: bool):
    sim = joint.Sim()
    rows = []
    out_index = 0
    checks = 0
    for command_index, command in enumerate(commands):
        if command == 0:
            break
        actual_reply = outputs[out_index]
        out_index += 1
        if command > 0:
            b_action = baseline_action(sim, command)
            p_action = p4_action(sim, command)
            eligible = (
                collect
                and command_index >= MIN_COMMAND_INDEX
                and command_index % SNAPSHOT_CADENCE == 0
                and b_action is not None
                and p_action is not None
                and (b_action.start, b_action.high_side) != (p_action.start, p_action.high_side)
                and len(sim.observations) >= 16
                and command_index + 1 < len(commands)
            )
            if eligible:
                scenarios = joint.sample_scenarios(sim, command_index + 1, command)
                if scenarios:
                    # Both candidate actions use the same scenario samples.
                    base_scores = [
                        mean_rollout_value(sim, command, b_action, scenarios, "baseline"),
                        mean_rollout_value(sim, command, p_action, scenarios, "baseline"),
                    ]
                    conditioned_scores = [
                        base_scores[0],
                        mean_rollout_value(sim, command, p_action, scenarios, "P4"),
                    ]
                    baseline_targets = [
                        exact_suffix(sim, command, b_action, commands, command_index + 1, "baseline"),
                        exact_suffix(sim, command, p_action, commands, command_index + 1, "baseline"),
                    ]
                    conditioned_targets = [
                        baseline_targets[0],
                        exact_suffix(sim, command, p_action, commands, command_index + 1, "P4"),
                    ]
                    baseline_choice = "baseline" if base_scores[0] <= base_scores[1] else "P4"
                    conditioned_choice = "baseline" if conditioned_scores[0] <= conditioned_scores[1] else "P4"
                    target_choice = (
                        "baseline" if conditioned_targets[0] < conditioned_targets[1]
                        else "P4" if conditioned_targets[1] < conditioned_targets[0]
                        else "tie"
                    )
                    rows.append({
                        "command_index": command_index,
                        "request_length": command,
                        "active_pipes": len(sim.active),
                        "free_gaps": len(sim.gaps),
                        "baseline_action_start": b_action.start,
                        "baseline_action_high_side": int(b_action.high_side),
                        "p4_action_start": p_action.start,
                        "p4_action_high_side": int(p_action.high_side),
                        "baseline_rollout_score_baseline_action_m": base_scores[0],
                        "baseline_rollout_score_p4_action_m": base_scores[1],
                        "conditioned_rollout_score_baseline_action_m": conditioned_scores[0],
                        "conditioned_rollout_score_p4_action_m": conditioned_scores[1],
                        "baseline_target_baseline_action_m": baseline_targets[0],
                        "baseline_target_p4_action_m": baseline_targets[1],
                        "conditioned_target_baseline_action_m": conditioned_targets[0],
                        "conditioned_target_p4_action_m": conditioned_targets[1],
                        "mixed_target_spread_m": abs(conditioned_targets[0] - conditioned_targets[1]),
                        "baseline_prediction_pair_accuracy_on_mixed_target": pair_accuracy(
                            base_scores, conditioned_targets),
                        "conditioned_prediction_pair_accuracy_on_mixed_target": pair_accuracy(
                            conditioned_scores, conditioned_targets),
                        "baseline_prediction_regret_on_mixed_target_m": top1_regret(
                            base_scores, conditioned_targets),
                        "conditioned_prediction_regret_on_mixed_target_m": top1_regret(
                            conditioned_scores, conditioned_targets),
                        "baseline_prediction_pair_accuracy_on_baseline_target": pair_accuracy(
                            base_scores, baseline_targets),
                        "baseline_prediction_regret_on_baseline_target_m": top1_regret(
                            base_scores, baseline_targets),
                        "baseline_predictor_selected_action": baseline_choice,
                        "conditioned_predictor_selected_action": conditioned_choice,
                        "mixed_target_best_action": target_choice,
                        "recommendation_flip": int(baseline_choice != conditioned_choice),
                    })
            digs, start = sim.place(command)
            expected = [digs, start]
            if actual_reply != expected:
                raise RuntimeError(
                    f"frozen noMC transcript mismatch at {command_index}: "
                    f"expected {expected}, got {actual_reply}"
                )
        else:
            start = sim.remove_pid(-command)
            if actual_reply != [start]:
                raise RuntimeError(
                    f"frozen noMC deletion mismatch at {command_index}: "
                    f"expected {[start]}, got {actual_reply}"
                )
        checks += 1
    return rows, {"commands_checked": checks, "transcript_matches": True}


def verify_p4_transcript(commands: list[int], outputs: list[list[int]]) -> dict:
    sim = joint.Sim()
    out_index = 0
    checks = 0
    for command_index, command in enumerate(commands):
        if command == 0:
            break
        actual_reply = outputs[out_index]
        out_index += 1
        if command > 0:
            digs, start = p4_place(sim, command)
            expected = [digs, start]
        else:
            expected = [sim.remove_pid(-command)]
        if actual_reply != expected:
            raise RuntimeError(
                f"P4 transcript mismatch at {command_index}: expected {expected}, got {actual_reply}"
            )
        checks += 1
    return {"commands_checked": checks, "transcript_matches": True}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def paired_bootstrap(rows: list[dict], metric_base: str, metric_conditioned: str) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row[metric_base] is not None and row[metric_conditioned] is not None:
            grouped[row["stream"]].append(row)
    per_stream = {
        stream: {
            "baseline_mean": sum(float(r[metric_base]) for r in sr) / len(sr),
            "conditioned_mean": sum(float(r[metric_conditioned]) for r in sr) / len(sr),
        }
        for stream, sr in sorted(grouped.items())
    }
    names = sorted(per_stream)
    if len(names) < 2:
        return {"informative_streams": len(names), "per_stream": per_stream, "mean_delta": None,
                "percentile_95_ci": None, "improved_streams": 0, "worsened_streams": 0, "tied_streams": 0}
    deltas = [per_stream[name]["conditioned_mean"] - per_stream[name]["baseline_mean"] for name in names]
    rng = random.Random(BOOTSTRAP_SEED)
    draws = [
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(BOOTSTRAP_SAMPLES)
    ]
    return {
        "unit": "whole stream, equal stream weight",
        "informative_streams": len(names),
        "mean_delta": sum(deltas) / len(deltas),
        "percentile_95_ci": [percentile(draws, 0.025), percentile(draws, 0.975)],
        "positive_delta_streams": sum(d > 0 for d in deltas),
        "negative_delta_streams": sum(d < 0 for d in deltas),
        "tied_streams": sum(d == 0 for d in deltas),
        "per_stream": per_stream,
    }


def summarize_rows(rows: list[dict], split: str) -> dict:
    informative = [r for r in rows if r["mixed_target_spread_m"] > 0]
    acc = paired_bootstrap(
        informative,
        "baseline_prediction_pair_accuracy_on_mixed_target",
        "conditioned_prediction_pair_accuracy_on_mixed_target",
    )
    regret = paired_bootstrap(
        informative,
        "baseline_prediction_regret_on_mixed_target_m",
        "conditioned_prediction_regret_on_mixed_target_m",
    )
    base_sanity_acc = [r["baseline_prediction_pair_accuracy_on_baseline_target"]
                       for r in rows if r["baseline_prediction_pair_accuracy_on_baseline_target"] is not None]
    base_sanity_regret = [r["baseline_prediction_regret_on_baseline_target_m"]
                          for r in rows if r["baseline_prediction_regret_on_baseline_target_m"] is not None]
    profile_groups: dict[str, list[dict]] = defaultdict(list)
    for row in informative:
        profile_groups[row["profile"]].append(row)
    profiles = {}
    for profile, profile_rows in sorted(profile_groups.items()):
        profile_acc = paired_bootstrap(
            profile_rows,
            "baseline_prediction_pair_accuracy_on_mixed_target",
            "conditioned_prediction_pair_accuracy_on_mixed_target",
        )
        profile_regret = paired_bootstrap(
            profile_rows,
            "baseline_prediction_regret_on_mixed_target_m",
            "conditioned_prediction_regret_on_mixed_target_m",
        )
        profiles[profile] = {
            "states": len(profile_rows),
            "pair_accuracy_delta": profile_acc["mean_delta"],
            "pair_accuracy_ci": profile_acc["percentile_95_ci"],
            "regret_delta_m": profile_regret["mean_delta"],
            "regret_ci_m": profile_regret["percentile_95_ci"],
            "informative_streams": profile_acc["informative_streams"],
        }
    leave_one_profile_out = {}
    for omitted_profile in ("long-heavy", "short-heavy", "uniform"):
        retained = [row for row in informative if row["profile"] != omitted_profile]
        retained_acc = paired_bootstrap(
            retained,
            "baseline_prediction_pair_accuracy_on_mixed_target",
            "conditioned_prediction_pair_accuracy_on_mixed_target",
        )
        retained_regret = paired_bootstrap(
            retained,
            "baseline_prediction_regret_on_mixed_target_m",
            "conditioned_prediction_regret_on_mixed_target_m",
        )
        leave_one_profile_out[omitted_profile] = {
            "retained_states": len(retained),
            "retained_streams": retained_acc["informative_streams"],
            "pair_accuracy_delta": retained_acc["mean_delta"],
            "pair_accuracy_ci": retained_acc["percentile_95_ci"],
            "regret_delta_m": retained_regret["mean_delta"],
            "regret_ci_m": retained_regret["percentile_95_ci"],
        }
    flips = sum(int(row["recommendation_flip"]) for row in rows)
    informative_flips = sum(
        int(row["recommendation_flip"]) for row in informative
    )
    def action_counts(field: str, records: list[dict]) -> dict[str, int]:
        return {key: sum(row[field] == key for row in records) for key in ("baseline", "P4", "tie")}

    return {
        "split": split,
        "states": len(rows),
        "informative_states_mixed_target": len(informative),
        "streams": len({r["stream"] for r in rows}),
        "baseline_continuation_sanity": {
            "pair_accuracy_mean": sum(base_sanity_acc) / len(base_sanity_acc) if base_sanity_acc else None,
            "top1_regret_mean_m": sum(base_sanity_regret) / len(base_sanity_regret) if base_sanity_regret else None,
            "informative_states": len(base_sanity_acc),
        },
        "selected_action_counts": {
            "candidate_states": len(rows),
            "baseline_continuation_predictor": action_counts("baseline_predictor_selected_action", rows),
            "conditioned_predictor": action_counts("conditioned_predictor_selected_action", rows),
            "mixed_policy_target_best": action_counts("mixed_target_best_action", rows),
            "recommendation_flips": flips,
            "recommendation_flip_frequency": flips / len(rows) if rows else None,
            "informative_states": len(informative),
            "informative_recommendation_flips": informative_flips,
            "informative_recommendation_flip_frequency": informative_flips / len(informative) if informative else None,
        },
        "mixed_policy_target": {
            "baseline_continuation_predictor_vs_conditioned_predictor_pair_accuracy": acc,
            "baseline_continuation_predictor_vs_conditioned_predictor_top1_regret_m": regret,
            "profile_breakdown": profiles,
            "leave_one_profile_out": leave_one_profile_out,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--p4", type=Path, required=True)
    parser.add_argument("--split", choices=(TRAINING_SPLIT, VALIDATION_SPLIT, "all"), default="all")
    args = parser.parse_args()
    input_root = HERE / "inputs"
    splits = (TRAINING_SPLIT, VALIDATION_SPLIT) if args.split == "all" else (args.split,)
    all_rows = []
    transcript_checks = []
    t0 = time.perf_counter()
    for split in splits:
        for path in sorted((input_root / split).glob("*.in")):
            commands = parse_commands(path)
            frozen_output = read_solver_output(args.baseline.resolve(), commands)
            p4_output = read_solver_output(args.p4.resolve(), commands)
            rows, frozen_check = run_baseline_transcript(commands, frozen_output, collect=True)
            p4_check = verify_p4_transcript(commands, p4_output)
            meta = next(
                entry for entry in json.loads((HERE / "input_manifest.json").read_text())["records"]
                if Path(entry["file"]).name == path.name and entry["split"] == split
            )
            for row in rows:
                row.update({
                    "split": split,
                    "stream": path.stem,
                    "profile": meta["length_profile"],
                    "deletion_policy": meta["deletion_policy"],
                    "seed": meta["seed"],
                })
            all_rows.extend(rows)
            transcript_checks.append({
                "split": split,
                "stream": path.stem,
                "input_sha256": sha256(path),
                "frozen_noMC": frozen_check,
                "P4": p4_check,
                "candidate_states": len(rows),
            })
    elapsed = time.perf_counter() - t0
    csv_path = HERE / "ranking_states.csv"
    if all_rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
    summary = {
        "experiment": "post-hoc policy-conditioned depth-16 rollout vs all-baseline continuation",
        "frozen_baseline": "results/pipes/final/solution.cpp compiled with MC_ROLLOUT_DISABLED",
        "alternative_policy": "results/pipes/improvement/strategies/policy4_baseline.cpp",
        "estimand": {
            "candidate_actions": "the distinct first action selected by frozen-noMC and P4 on the same frozen-noMC state",
            "baseline_continuation_predictor": "both first actions followed by frozen-noMC for sixteen sampled events",
            "conditioned_predictor": "frozen action followed by frozen-noMC; P4 action followed by P4 for sixteen sampled events",
            "mixed_policy_target": "exact known suffix after frozen action under frozen-noMC; exact suffix after P4 action under P4",
            "sanity_target": "both first actions followed by frozen-noMC over the exact known suffix",
            "causality": "rollout scenarios are sampled only from observed history; future input is used only for evaluator targets",
        },
        "fixed_parameters": {
            "operations_per_stream": 1800,
            "train_streams": 9,
            "validation_streams": 18,
            "snapshot_cadence_commands": SNAPSHOT_CADENCE,
            "minimum_command_index": MIN_COMMAND_INDEX,
            "scenario_depth": SCENARIO_DEPTH,
            "scenario_trials": SCENARIO_TRIALS,
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "tuning_on_validation": False,
        },
        "transcript_checks": transcript_checks,
        "splits": {
            split: summarize_rows([r for r in all_rows if r["split"] == split], split)
            for split in splits
        },
        "measurement": {"wall_seconds": elapsed, "python": sys.version.split()[0],
                        "platform": platform.platform()},
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        split: {
            "states": result["states"],
            "informative": result["informative_states_mixed_target"],
            "pair_delta": result["mixed_policy_target"][
                "baseline_continuation_predictor_vs_conditioned_predictor_pair_accuracy"]["mean_delta"],
            "regret_delta_m": result["mixed_policy_target"][
                "baseline_continuation_predictor_vs_conditioned_predictor_top1_regret_m"]["mean_delta"],
        }
        for split, result in summary["splits"].items()
    }, indent=2))
    print(f"wall_seconds={elapsed:.3f} rows={len(all_rows)}")


if __name__ == "__main__":
    main()
