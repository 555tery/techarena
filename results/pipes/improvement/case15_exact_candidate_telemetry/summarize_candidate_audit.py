#!/usr/bin/env python3
"""Validate and summarize the first-successor candidate/lineage audit."""
from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict, deque
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNS = HERE / "runs"
GEOMETRY = HERE / "geometry"
INPUT = ROOT / "data/pipes/open/15.in"
FINAL = ROOT / "results/pipes/final/solution.cpp"
BASELINE = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/judge_output.txt"
EXPECTED_ANSWER = "0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e"
EXPECTED_FINAL = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def read_gzip_csv(path: Path):
    with gzip.open(path, "rt", newline="") as stream:
        yield from csv.DictReader(stream)


def main() -> None:
    words = INPUT.read_text().split()
    n = int(words[1])
    commands = list(map(int, words[2 : 2 + n]))
    if len(commands) != n or int(words[-1]) != 0:
        raise RuntimeError("input format changed")
    if sha(FINAL) != EXPECTED_FINAL or sha(BASELINE) != EXPECTED_ANSWER:
        raise RuntimeError("frozen source/output hashes changed")
    if sha(RUNS / "judge_output.txt") != EXPECTED_ANSWER:
        raise RuntimeError("diagnostic output differs from frozen baseline")

    expansions = sorted(int(r["op"]) for r in read_csv(RUNS / "extensions.csv"))
    placements = {int(r["op"]): r for r in read_csv(GEOMETRY / "placements.csv")}
    episodes = {int(r["id"]): r for r in read_csv(GEOMETRY / "gap_episodes.csv")}
    episode_first_expansion: dict[int, int] = {}
    for episode_id, episode in episodes.items():
        birth, end = int(episode["birth_op"]), int(episode["end_op"])
        index = bisect.bisect_right(expansions, birth)
        if index < len(expansions) and expansions[index] <= end:
            episode_first_expansion[episode_id] = expansions[index]

    expected_targets = []
    for line in (HERE / "targets.tsv").read_text().splitlines():
        fields = tuple(map(int, line.split()))
        if len(fields) != 8:
            raise RuntimeError("target file does not have eight fields")
        expected_targets.append(fields)
    target_keys = {
        (op, expansion, request, gap_id, start, end, gap_length, birth)
        for op, gap_id, start, end, gap_length, birth, request, expansion in expected_targets
    }
    target_ops: dict[int, list[tuple[int, int]]] = defaultdict(list)
    target_expansion_ops = set()
    for op, gap_id, start, end, gap_length, birth, request, expansion in expected_targets:
        if commands[op - 1] != request or not (birth < op < expansion):
            raise RuntimeError(f"invalid target op/birth/request relation: {op}, {gap_id}")
        episode = episodes[gap_id]
        if (int(episode["start"]), int(episode["end"]), int(episode["length"]),
                int(episode["birth_op"])) != (start, end, gap_length, birth):
            raise RuntimeError(f"target coordinates do not match episode {gap_id}")
        if episode_first_expansion.get(gap_id) != expansion:
            raise RuntimeError(f"wrong first-successor expansion for episode {gap_id}")
        target_ops[op].append((gap_id, expansion))
        target_expansion_ops.add(expansion)

    target_rows = list(read_gzip_csv(RUNS / "candidate_targets.csv.gz"))
    if len(target_rows) != len(expected_targets):
        raise RuntimeError("target-pair count differs from generated target set")
    observed_keys = set()
    status_counts = Counter()
    rank_rows = []
    for row in target_rows:
        op = int(row["op"])
        key = (op, int(row["first_expansion_op"]), int(row["request"]),
               int(row["gap_id"]), int(row["gap_start"]), int(row["gap_end"]),
               int(row["gap_length"]), int(row["birth_op"]))
        if key not in target_keys or key in observed_keys:
            raise RuntimeError(f"candidate target is unexpected or duplicated: {key}")
        observed_keys.add(key)
        if row["current_gap"] != "1" or int(row["physical_rank"]) <= 0:
            raise RuntimeError(f"target gap is not present in physical universe at op {op}")
        if int(row["gap_length"]) < int(row["request"]):
            raise RuntimeError(f"target interval cannot physically fit request at op {op}")
        status_counts[row["score_status"]] += 1
        rank_rows.append((int(row["physical_rank"]), int(row["scored_rank"])))
    if observed_keys != target_keys:
        raise RuntimeError("not all target pairs were captured")

    op_rows = read_csv(RUNS / "candidate_ops.csv")
    if {int(r["op"]) for r in op_rows} != set(target_ops):
        raise RuntimeError("candidate-op summaries do not match target-op set")
    if len(op_rows) != len(target_ops):
        raise RuntimeError("duplicate candidate-op summary")
    expansion_set = set(expansions)
    winner_reasons = Counter()
    pool_counts = Counter()
    parity_modes = Counter()
    mc_override_ops = 0
    mc_used_ops = 0
    physical_fit_sum = 0
    suppression_sum = 0
    after_cap_sum = 0
    scored_sum = 0
    baseline_rows_checked = 0
    for row in op_rows:
        op = int(row["op"])
        if int(row["target_count"]) != len(target_ops[op]):
            raise RuntimeError(f"target count mismatch for op {op}")
        if int(row["request"]) != commands[op - 1]:
            raise RuntimeError(f"request mismatch for op {op}")
        if int(row["baseline_start"]) != int(placements[op]["bestfit_gap_start"]):
            raise RuntimeError(f"baseline winner mismatch for op {op}")
        if int(row["baseline_score"]) != int(placements[op]["bestfit_score"]):
            raise RuntimeError(f"baseline score mismatch for op {op}")
        if int(row["baseline_start"]) >= 0 and int(row["selected_start"]) >= 0 and \
                int(row["selected_start"]) != int(placements[op]["selected_gap_start"]):
            raise RuntimeError(f"selected gap mismatch for op {op}")
        baseline_rows_checked += 1
        winner_reasons[row["winner_reason"]] += 1
        pool_counts[row["pool"]] += 1
        parity_modes[row["parity_mode"]] += 1
        physical_fit_sum += int(row["physical_fit_count"])
        suppression_sum += int(row["representative_suppressed_count"])
        after_cap_sum += int(row["after_cap_count"])
        scored_sum += int(row["scored_count"])
        if int(row["rollouts_this_op"]) > 0:
            mc_used_ops += 1
        if row["winner_reason"] == "monte_carlo_override":
            mc_override_ops += 1

    # Recompute the live cost formula independently from the exact command prefix.
    histories: dict[int, tuple[int, list[int]]] = {}
    history = deque()
    frequencies = [0] * 41
    for op, command in enumerate(commands, 1):
        if op in target_ops:
            histories[op] = (len(history), frequencies.copy())
        if command > 0:
            history.append(command)
            frequencies[command] += 1
            if len(history) > 2048:
                frequencies[history.popleft()] -= 1

    def expected_cost(op: int, slack: int) -> int:
        h, freq = histories[op]
        penalty = 60 * sum(freq[slack + 1 : 41]) if 0 < slack <= 40 else 0
        return slack * h + penalty

    for row in target_rows:
        op = int(row["op"])
        slack = int(row["gap_length"]) - int(row["request"])
        if int(row["score"]) != expected_cost(op, slack):
            raise RuntimeError(f"target cost mismatch at op {op}, gap {row['gap_id']}")
    score_row_count = 0
    score_rows_by_op: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in read_gzip_csv(RUNS / "candidate_scores.csv.gz"):
        op = int(row["op"])
        if int(row["score"]) != expected_cost(op, int(row["slack"])):
            raise RuntimeError(f"candidate score mismatch at op {op}, start {row['start']}")
        score_rows_by_op[op].append(row)
        score_row_count += 1

    for row in op_rows:
        op = int(row["op"])
        scored = [r for r in score_rows_by_op[op] if int(r["scorer_rank"]) > 0]
        if len(scored) != int(row["scored_count"]):
            raise RuntimeError(f"scored candidate count mismatch at op {op}")
        by_rank = sorted(scored, key=lambda r: int(r["scorer_rank"]))
        for i, candidate in enumerate(by_rank, 1):
            if int(candidate["scorer_rank"]) != i:
                raise RuntimeError(f"non-contiguous scorer rank at op {op}")
        is_expansion = op in expansion_set
        if is_expansion and int(row["physical_fit_count"]) > 0:
            # This can happen only when cohort selection rejected all fits.
            if row["pool"] != "none":
                raise RuntimeError(f"expansion with fit candidates not cohort-filtered at op {op}")

    # Independently reconstruct physical candidates from gap episodes. A gap
    # is present immediately before op iff birth_op < op <= end_op.
    targets_by_op: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in target_rows:
        targets_by_op[int(row["op"])].append(row)
    op_rows_by_id = {int(row["op"]): row for row in op_rows}
    births = sorted((int(row["birth_op"]), episode_id)
                    for episode_id, row in episodes.items())
    closes = sorted((int(row["end_op"]), episode_id)
                    for episode_id, row in episodes.items())
    birth_at = close_at = 0
    active_episodes: dict[int, dict[str, str]] = {}
    physical_rank_checks = 0
    rank_one_shadowed = 0
    shadowed_that_beat_baseline = 0
    reconstructed_physical_fit_total = 0
    for op in range(1, n + 1):
        while birth_at < len(births) and births[birth_at][0] < op:
            _, episode_id = births[birth_at]
            active_episodes[episode_id] = episodes[episode_id]
            birth_at += 1
        while close_at < len(closes) and closes[close_at][0] < op:
            _, episode_id = closes[close_at]
            active_episodes.pop(episode_id, None)
            close_at += 1
        if op not in targets_by_op:
            continue
        request = commands[op - 1]
        operation_targets = targets_by_op[op]
        high_side = operation_targets[0]["high_side"] == "1"
        if any((row["high_side"] == "1") != high_side for row in operation_targets):
            raise RuntimeError(f"inconsistent edge choice for target op {op}")
        physical = []
        for episode_id, episode in active_episodes.items():
            gap_length = int(episode["length"])
            if gap_length >= request:
                start = int(episode["start"])
                physical.append((expected_cost(op, gap_length - request), start, episode_id))
        physical.sort(key=lambda item: (item[0], -item[1] if high_side else item[1]))
        reconstructed_physical_fit_total += len(physical)
        physical_rank_by_episode = {
            episode_id: rank for rank, (_, _, episode_id) in enumerate(physical, 1)
        }
        if len(physical) != int(op_rows_by_id[op]["physical_fit_count"]):
            raise RuntimeError(f"physical-fit count mismatch at op {op}")
        for row in operation_targets:
            rank = physical_rank_by_episode.get(int(row["gap_id"]))
            if rank != int(row["physical_rank"]):
                raise RuntimeError(f"physical rank mismatch at op {op}, gap {row['gap_id']}")
            physical_rank_checks += 1
            if row["score_status"] == "same_size_shadowed":
                if rank == 1:
                    rank_one_shadowed += 1
                target_score = int(row["score"])
                baseline_score = int(row["baseline_score"])
                target_start = int(row["gap_start"])
                baseline_start = int(row["baseline_start"])
                better_tie = (high_side and target_start > baseline_start) or \
                    (not high_side and target_start < baseline_start)
                if target_score < baseline_score or \
                        (target_score == baseline_score and better_tie):
                    shadowed_that_beat_baseline += 1

    # Count only intervals active before each expansion, not gaps created by
    # that expansion's own placement.
    expansion_births = births
    expansion_closes = closes
    active_at_expansions: set[int] = set()
    eb = ec = active_episode_expansion_pairs = 0
    episodes_seen_at_expansion: set[int] = set()
    for op in expansions:
        while eb < len(expansion_births) and expansion_births[eb][0] < op:
            active_at_expansions.add(expansion_births[eb][1])
            eb += 1
        while ec < len(expansion_closes) and expansion_closes[ec][0] < op:
            active_at_expansions.discard(expansion_closes[ec][1])
            ec += 1
        active_episode_expansion_pairs += len(active_at_expansions)
        episodes_seen_at_expansion.update(active_at_expansions)

    physical_ranks = [x[0] for x in rank_rows]
    scored_ranks = [x[1] for x in rank_rows if x[1] > 0]
    target_ops_overlapping_expansions = sum(op in expansion_set for op in target_ops)
    target_rows_overlapping_expansions = sum(
        int(row["op"]) in expansion_set for row in target_rows
    )
    associated_intervals = len(episode_first_expansion)
    current_analysis = json.loads((HERE / "analysis.json").read_text())

    def quantiles(values: list[int]) -> dict[str, float | int | None]:
        if not values:
            return {"min": None, "median": None, "p90": None, "max": None}
        values.sort()
        return {
            "min": values[0],
            "median": values[(len(values) - 1) // 2],
            "p90": values[int(0.9 * (len(values) - 1))],
            "max": values[-1],
        }

    summary = {
        "case": 15,
        "scope": "each gap episode's first strictly later expansion; eligible prior placements only",
        "input_sha256": sha(INPUT),
        "frozen_final_sha256": sha(FINAL),
        "baseline_answer_sha256": sha(BASELINE),
        "replay_answer_sha256": sha(RUNS / "judge_output.txt"),
        "episode_count": len(episodes),
        "expansion_count": len(expansions),
        "active_episode_expansion_pairs_all_states": active_episode_expansion_pairs,
        "unique_episodes_active_at_some_expansion": len(episodes_seen_at_expansion),
        "episodes_with_strictly_later_expansion": associated_intervals,
        "episodes_with_at_least_one_fitting_prior_placement": len({
            int(row["gap_id"]) for row in target_rows
        }),
        "candidate_gap_placement_pairs": len(target_rows),
        "unique_placement_operations": len(op_rows),
        "target_operations_that_are_also_expansions": target_ops_overlapping_expansions,
        "target_pairs_at_operations_that_are_also_expansions": target_rows_overlapping_expansions,
        "target_first_expansion_ops_covered": len(target_expansion_ops),
        "status_counts": dict(status_counts),
        "rank_one_shadowed_target_pairs": rank_one_shadowed,
        "shadowed_target_pairs_that_would_outrank_baseline_by_cost_and_tie_break":
            shadowed_that_beat_baseline,
        "physical_rank_quantiles": quantiles(physical_ranks),
        "scored_rank_quantiles_for_evaluated_targets": quantiles(scored_ranks),
        "candidate_universe_totals_over_target_operations": {
            "physical_fits": physical_fit_sum,
            "same_length_representatives_suppressed": suppression_sum,
            "representatives_after_slack_cutoff": after_cap_sum,
            "actually_scored_representatives": scored_sum,
            "scorer_plus_rollout_pool_rows": score_row_count,
        },
        "pool_counts": dict(pool_counts),
        "parity_mode_counts": dict(parity_modes),
        "winner_reasons": dict(winner_reasons),
        "monte_carlo": {
            "operations_with_rollouts": mc_used_ops,
            "operations_overridden_from_baseline": mc_override_ops,
        },
        "baseline_winner_reconciliations": baseline_rows_checked,
        "independent_geometry_rank_checks": physical_rank_checks,
        "reconstructed_physical_fit_candidates_total": reconstructed_physical_fit_total,
        "cost_recomputations_checked": len(target_rows) + score_row_count,
        "expansion_telemetry_crosscheck": {
            "expansions_with_any_contiguous_physical_fit": current_analysis[
                "extension_events_with_any_contiguous_physical_fit"],
            "expansions_with_enough_aggregate_free_volume": current_analysis[
                "extension_events_with_enough_aggregate_free_volume"],
            "final_trench_m": current_analysis["final_trench_m"],
        },
        "geometry_lineage_caveat": (
            "episode IDs are first-close interval lifetimes; after deletion merges, the replay "
            "records a new episode and a lineage bitmask but no parent IDs or ancestry graph"
        ),
        "selection_bias_caveat": (
            "targets are selected by survival to an expansion in the frozen baseline trace; "
            "this explains that trace's candidate decisions, not counterfactual improvement"
        ),
        "source_hashes": {
            "solver_replay_cpp": sha(HERE / "solver_replay.cpp"),
            "prepare_targets_py": sha(HERE / "prepare_targets.py"),
            "summarizer_py": sha(HERE / "summarize_candidate_audit.py"),
        },
        "artifact_hashes": {
            name: sha(RUNS / name) for name in (
                "candidate_ops.csv", "candidate_targets.csv.gz", "candidate_scores.csv.gz",
                "extensions.csv", "extension_candidates.csv", "judge_output.txt",
            )
        },
    }
    (HERE / "candidate_audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
