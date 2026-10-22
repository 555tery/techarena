#!/usr/bin/env python3
"""Summarize exact expansion-candidate and free-interval lifecycle telemetry."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INPUT = ROOT / "data/pipes/open/15.in"
FINAL = ROOT / "results/pipes/final/solution.cpp"
OLD_REPLAY = ROOT / "results/pipes/improvement/case15_survivor_rank/survivor_rank_replay.cpp"
BASELINE_ANSWER = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/judge_output.txt"
COST_LOG = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/solver_stderr.txt"
UPSTREAM_INSTRUMENT = ROOT / "results/pipes/improvement/case15_survivor_rank/instrument.py"
UPSTREAM_GEOMETRY_REPLAY = ROOT / "results/pipes/improvement/case15_interval_lineage/replay/interval_origin_replay.cpp"
RUNS = HERE / "runs"
GEOMETRY = HERE / "geometry"
EXPECTED_FINAL_SHA256 = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
EXPECTED_INPUT_SHA256 = "0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353"
EXPECTED_ANSWER_SHA256 = "0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def size_band(n: int) -> str:
    if n <= 1:
        return "1m"
    if n <= 4:
        return "2-4m"
    if n <= 7:
        return "5-7m"
    if n <= 16:
        return "8-16m"
    if n <= 40:
        return "17-40m"
    return ">40m"


def birth_class(command: int, reason: str, lifetime: int) -> str:
    if command > 0:
        if reason == "placement_residual":
            return "placement_residual" if lifetime > 0 else "same_op_growth_span"
        if reason == "mixed_merged":
            return "placement_tail_extension"
        return "other_placement_gap"
    if reason == "deletion_hole":
        return "deletion_hole"
    if reason == "mixed_merged":
        return "deletion_merge_result"
    return "other_deletion_gap"


def main() -> None:
    words = INPUT.read_text().split()
    weight, n = float(words[0]), int(words[1])
    commands = list(map(int, words[2 : 2 + n]))
    if len(words) != n + 3 or int(words[-1]) != 0:
        raise RuntimeError("case 15 input format changed")
    if sha(INPUT) != EXPECTED_INPUT_SHA256 or sha(FINAL) != EXPECTED_FINAL_SHA256:
        raise RuntimeError("input or frozen-final source hash differs from this qualification")

    answer_tokens = list(map(int, (RUNS / "judge_output.txt").read_text().split()))
    answer_at = 0
    dig_at_op: dict[int, tuple[int, int]] = {}
    trench = 0
    for op, command in enumerate(commands, 1):
        if command > 0:
            digs, start = answer_tokens[answer_at : answer_at + 2]
            answer_at += 2
            if digs < 0 or start < 0:
                raise RuntimeError(f"invalid placement answer at op {op}")
            if digs:
                dig_at_op[op] = (digs, start)
                trench += 20 * digs
        else:
            answer_at += 1
    if answer_at != len(answer_tokens):
        raise RuntimeError("unexpected extra answer tokens")
    if (sha(RUNS / "judge_output.txt") != sha(BASELINE_ANSWER) or
            sha(RUNS / "judge_output.txt") != EXPECTED_ANSWER_SHA256):
        raise RuntimeError("replay output hash does not match frozen-final output")

    extensions = rows(RUNS / "extensions.csv")
    candidates = rows(RUNS / "extension_candidates.csv")
    if len(extensions) != len(dig_at_op):
        raise RuntimeError("extension telemetry count differs from answer stream")
    if len(candidates) != 0:
        raise RuntimeError("unexpected physical-fit candidate rows; inspect before summarizing")

    growth = {int(r["op"]): r for r in rows(
        ROOT / "results/pipes/improvement/all_tests_diagnosis/growth_events.csv")
        if r["case"] == "15"}
    if set(growth) != set(dig_at_op):
        raise RuntimeError("existing growth-event trace and exact replay disagree on extension ops")
    ext_by_op = {}
    for event in extensions:
        op = int(event["op"])
        ext_by_op[op] = event
        digs, start = dig_at_op[op]
        old = int(event["old_trench"])
        new = int(event["new_trench"])
        if int(event["request"]) != commands[op - 1]:
            raise RuntimeError(f"request mismatch at op {op}")
        if int(event["digs"]) != digs or int(event["selected_start"]) != start:
            raise RuntimeError(f"placement output mismatch at op {op}")
        if new != old + 20 * digs:
            raise RuntimeError(f"trench update mismatch at op {op}")
        prior = growth[op]
        checks = {
            "trench_before_m": old,
            "trench_after_m": new,
            "free_volume_before_m": int(event["free_volume_before_m"]),
            "largest_free_gap_before_m": int(event["largest_gap_before_m"]),
        }
        for key, value in checks.items():
            if int(prior[key]) != value:
                raise RuntimeError(f"growth trace mismatch {key} at op {op}")
        if (prior["free_volume_sufficed"] == "True") != (event["free_volume_sufficed"] == "1"):
            raise RuntimeError(f"free-volume classification mismatch at op {op}")
        if int(event["physical_fit_count"]) != 0:
            raise RuntimeError(f"physically fitting gap found at extension op {op}")

    episodes = rows(GEOMETRY / "gap_episodes.csv")
    placements = rows(GEOMETRY / "placements.csv")
    by_interval: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    fates = []
    for episode in episodes:
        born = int(episode["birth_op"])
        category = birth_class(commands[born - 1], episode["reason"], int(episode["lifetime_ops"]))
        record = {
            "id": episode["id"], "start": episode["start"], "end": episode["end"],
            "length": episode["length"], "birth_op": episode["birth_op"],
            "birth_command": commands[born - 1], "birth_class": category,
            "lineage_mask": episode["lineage_mask"], "end_op": episode["end_op"],
            "lifetime_ops": episode["lifetime_ops"], "reason": episode["reason"],
            "close_cause": episode["close_cause"], "right_censored": episode["right_censored"],
        }
        fates.append(record)
        by_interval[(int(episode["start"]), int(episode["end"]))].append(episode)

    fate_path = HERE / "interval_fates.csv"
    with fate_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fates[0]))
        writer.writeheader()
        writer.writerows(fates)

    candidate_fates = []
    for candidate in candidates:
        op = int(candidate["op"])
        key = (int(candidate["gap_start"]), int(candidate["gap_end"]))
        matches = [e for e in by_interval[key]
                   if int(e["birth_op"]) <= op < int(e["end_op"])]
        if len(matches) != 1:
            raise RuntimeError(f"cannot identify unique interval episode for candidate at op {op}")
        e = matches[0]
        candidate_fates.append({
            **candidate, "gap_id": e["id"], "birth_op": e["birth_op"],
            "lineage_mask": e["lineage_mask"], "end_op": e["end_op"],
            "lifetime_ops": e["lifetime_ops"], "close_cause": e["close_cause"],
        })
    fate_candidate_path = HERE / "candidate_fates.csv"
    candidate_fields = list(candidates[0]) + ["gap_id", "birth_op", "lineage_mask", "end_op", "lifetime_ops", "close_cause"] if candidates else [
        "op", "request", "gap_start", "gap_end", "gap_length", "gap_cohort", "physical_rank",
        "hypothetical_score", "slack", "history_size", "misses", "pool", "cohort_eligible",
        "pool_representative_start", "is_pool_representative", "score_status", "score_rank",
        "excluded_reason", "gap_id", "birth_op", "lineage_mask", "end_op", "lifetime_ops", "close_cause",
    ]
    with fate_candidate_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=candidate_fields)
        writer.writeheader()
        writer.writerows(candidate_fates)

    small_residuals = [r for r in fates if r["birth_class"] == "placement_residual" and int(r["length"]) <= 7]
    placement_slack_1_7 = sum(1 <= int(r["slack"]) <= 7 for r in placements)
    if len(small_residuals) != placement_slack_1_7:
        raise RuntimeError("small placement-residual episodes do not reconcile with placement slack")
    deletion_gaps = [r for r in fates if r["birth_class"] in ("deletion_hole", "deletion_merge_result")]

    def grouped(rows_, key):
        out = defaultdict(Counter)
        for r in rows_:
            out[r[key]][r["close_cause"]] += 1
        return {k: dict(v) for k, v in sorted(out.items())}

    tail_reused = Counter(r["tail_reused"] for r in extensions)
    dig_sections = Counter(int(r["digs"]) for r in extensions)
    free_volume_sufficed = sum(r["free_volume_sufficed"] == "1" for r in extensions)
    parity_modes = Counter(r["parity_mode"] for r in extensions)
    no_fit_decisions = Counter(r["decision"] for r in extensions)
    small_by_fate = Counter(r["close_cause"] for r in small_residuals)
    deletion_by_fate = Counter(r["close_cause"] for r in deletion_gaps)
    deletion_small_by_fate = Counter(
        r["close_cause"] for r in deletion_gaps if int(r["length"]) <= 7)
    summary = {
        "case": 15,
        "weight": weight,
        "input_sha256": sha(INPUT),
        "frozen_final_sha256": sha(FINAL),
        "frozen_answer_sha256": sha(BASELINE_ANSWER),
        "replay_answer_sha256": sha(RUNS / "judge_output.txt"),
        "cost_log_sha256": sha(COST_LOG),
        "copied_replay_source_sha256": sha(OLD_REPLAY),
        "upstream_instrument_script_sha256": sha(UPSTREAM_INSTRUMENT),
        "diagnostic_replay_source_sha256": sha(HERE / "solver_replay.cpp"),
        "geometry_replay_source_sha256": sha(HERE / "interval_origin_replay.cpp"),
        "upstream_geometry_replay_source_sha256": sha(UPSTREAM_GEOMETRY_REPLAY),
        "extension_count": len(extensions),
        "extension_ops_first_last": [int(extensions[0]["op"]), int(extensions[-1]["op"])],
        "total_dig_sections": sum(int(r["digs"]) for r in extensions),
        "final_trench_m": int(extensions[-1]["new_trench"]),
        "extension_events_with_enough_aggregate_free_volume": free_volume_sufficed,
        "extension_events_with_any_contiguous_physical_fit": sum(int(r["physical_fit_count"]) > 0 for r in extensions),
        "physical_fit_candidates_total": sum(int(r["physical_fit_count"]) for r in extensions),
        "parity_mode_at_extensions": dict(parity_modes),
        "candidate_filters_at_extensions": {
            "cohort_preferred": sum(int(r["preferred_fit_count"]) for r in extensions),
            "cohort_shared": sum(int(r["shared_fit_count"]) for r in extensions),
            "cohort_foreign": sum(int(r["foreign_fit_count"]) for r in extensions),
            "representatives": sum(int(r["representative_count"]) for r in extensions),
            "scored": sum(int(r["scored_count"]) for r in extensions),
            "after_slack_scan_cutoff": sum(int(r["after_cap_count"]) for r in extensions),
            "candidate_rows": len(candidates),
        },
        "extension_decisions": dict(no_fit_decisions),
        "tail_reused_at_extensions": dict(tail_reused),
        "dig_sections_distribution": dict(dig_sections),
        "interval_episode_count": len(episodes),
        "interval_episode_close_causes": dict(Counter(r["close_cause"] for r in fates)),
        "small_placement_residuals_1_7m": {
            "count": len(small_residuals), "matches_selected_slack_count": placement_slack_1_7,
            "close_causes": dict(small_by_fate),
        },
        "deletion_born_gaps": {
            "count": len(deletion_gaps), "close_causes": dict(deletion_by_fate),
            "small_1_7m_count": sum(int(r["length"]) <= 7 for r in deletion_gaps),
            "small_1_7m_close_causes": dict(deletion_small_by_fate),
        },
        "per_origin_lifecycle": {
            category: dict(Counter(r["close_cause"] for r in fates if r["birth_class"] == category))
            for category in sorted({r["birth_class"] for r in fates})
        },
        "small_residuals_by_size_and_fate": {
            band: dict(Counter(r["close_cause"] for r in small_residuals if size_band(int(r["length"])) == band))
            for band in sorted({size_band(int(r["length"])) for r in small_residuals})
        },
        "existing_geometry_replay_match": {
            name: sha(GEOMETRY / name) == sha(ROOT / "results/pipes/improvement/case15_interval_lineage/replay" / name)
            for name in ("placements.csv", "gap_episodes.csv", "current_gaps.csv")
        },
        "artifact_sha256": {
            "extensions.csv": sha(RUNS / "extensions.csv"),
            "extension_candidates.csv": sha(RUNS / "extension_candidates.csv"),
            "solver_stderr.txt": sha(RUNS / "solver_stderr.txt"),
            "placements.csv": sha(GEOMETRY / "placements.csv"),
            "gap_episodes.csv": sha(GEOMETRY / "gap_episodes.csv"),
            "current_gaps.csv": sha(GEOMETRY / "current_gaps.csv"),
            "interval_fates.csv": sha(HERE / "interval_fates.csv"),
            "candidate_fates.csv": sha(HERE / "candidate_fates.csv"),
        },
    }
    if not all(summary["existing_geometry_replay_match"].values()):
        raise RuntimeError("geometry replay artifacts differ from prior exact replay")
    (HERE / "analysis.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
