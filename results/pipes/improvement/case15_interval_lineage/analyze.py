#!/usr/bin/env python3
"""Lineage and realized-demand analysis for the frozen Pipes case 15 replay."""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import resource
import sys
import time
from array import array
from collections import Counter, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPLAY = ROOT / "replay"
AUDIT = ROOT.parent / "generator_audit"
INPUT = AUDIT / "cost_inputs/15.in"
JUDGE = AUDIT / "cost_runs/runs/15/judge_output.txt"
COST_LOG = AUDIT / "cost_runs/runs/15/solver_stderr.txt"
EPISODES = REPLAY / "gap_episodes.csv"
CURRENT = REPLAY / "current_gaps.csv"
PLACEMENTS = REPLAY / "placements.csv"
FINAL_SOURCE = ROOT.parents[1] / "final/solution.cpp"
CANONICAL = ROOT.parents[3] / "src/pipes.cpp"
REPLAY_SOURCE = REPLAY / "interval_origin_replay.cpp"
REPLAY_BINARY = REPLAY / "interval_origin_replay"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def quantile(values, q):
    if not values:
        return None
    xs = sorted(values)
    at = (len(xs) - 1) * q
    lo, hi = math.floor(at), math.ceil(at)
    return xs[lo] + (xs[hi] - xs[lo]) * (at - lo)


def distribution(values):
    return {
        "n": len(values),
        "mean": sum(values) / len(values) if values else None,
        "median": quantile(values, 0.5),
        "p90": quantile(values, 0.9),
        "p99": quantile(values, 0.99),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "sum": sum(values),
    }


def read_input():
    with INPUT.open() as f:
        first = f.readline().split()
        if len(first) != 2:
            raise ValueError("expected weight and operation count")
        weight, n = float(first[0]), int(first[1])
        commands = [int(line) for line in f if line.strip()]
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()  # Harness input carries the protocol terminator after n operations.
    if len(commands) != n:
        raise ValueError(f"input has {len(commands)} commands after terminator handling, expected {n}")
    return weight, commands


def make_prefix(commands):
    """prefix[t][op] = positive commands of length <= t in operations 1..op."""
    n = len(commands)
    prefix = [array("I", [0]) * (n + 1) for _ in range(41)]
    running = [0] * 41
    for op, command in enumerate(commands, 1):
        if command > 0:
            if command > 40:
                raise ValueError(f"unsupported pipe length {command} at operation {op}")
            for threshold in range(command, 41):
                running[threshold] += 1
        for threshold in range(1, 41):
            prefix[threshold][op] = running[threshold]
    return prefix


def parse_cost_log():
    rows = {}
    for line in COST_LOG.read_text().splitlines():
        if not line.startswith("COST "):
            continue
        fields = line.split()
        if len(fields) != 14:
            raise ValueError(f"bad COST row: {line[:120]}")
        op, length, high, cohort, parity, base_start, base_len, base_score, chosen_start, chosen_len, hist, slack, misses = map(int, fields[1:])
        rows[op] = (length, base_score, hist, slack, misses)
    return rows


def main():
    started = time.perf_counter()
    weight, commands = read_input()
    n = len(commands)
    placements = sum(c > 0 for c in commands)
    prefix = make_prefix(commands)
    placement_ops_by_length = [[] for _ in range(41)]
    for op, command in enumerate(commands, 1):
        if command > 0:
            placement_ops_by_length[command].append(op)

    current = read_csv(CURRENT)
    costs = parse_cost_log()

    def window_counts(lo_exclusive, hi_inclusive, threshold):
        if hi_inclusive <= lo_exclusive or threshold <= 0:
            return 0
        t = min(40, threshold)
        return int(prefix[t][hi_inclusive] - prefix[t][lo_exclusive])

    def future_metrics(row, is_current=False):
        born = int(row["birth_op"])
        end = n if is_current else int(row["end_op"])
        cause = "eof_censored" if is_current else row["close_cause"]
        # A gap is measured after its birth operation. Include a placement that
        # actually consumes/splits it; other closing events are not pipe demand.
        hi = end if cause in ("placement_consumed_or_split", "tail_extended_by_dig", "eof_censored") else end - 1
        hi = min(hi, n)
        fit = window_counts(born, hi, int(row["length"]))
        all_demand = window_counts(born, hi, 40)
        prior_hi = end if cause == "tail_extended_by_dig" else end - 1
        prior_fit = window_counts(born, prior_hi, int(row["length"]))
        first_fit_op = None
        for request_length in range(1, min(40, int(row["length"])) + 1):
            events = placement_ops_by_length[request_length]
            event_index = bisect.bisect_right(events, born)
            if event_index < len(events) and events[event_index] <= hi:
                if first_fit_op is None or events[event_index] < first_fit_op:
                    first_fit_op = events[event_index]
        return {
            "fit_requests": fit,
            "demand_requests": all_demand,
            "prior_fit_requests": prior_fit,
            "first_fit_delay_ops": first_fit_op - born if first_fit_op is not None else None,
            "fit_fraction": fit / all_demand if all_demand else None,
            "prior_fit_unselected": prior_fit > 0,
        }

    def mask_name(mask):
        return {1: "placement_only_ancestry", 2: "deletion_only_ancestry", 3: "mixed_ancestry"}.get(mask, f"mask_{mask}")

    def new_lineage_accumulator():
        return {
            "episodes": 0, "causes": Counter(), "lengths": array("I"), "lifetimes": array("I"),
            "censored": 0, "observed": 0, "any_fit": 0, "prior_fit": 0,
            "fit_requests": 0, "demand_requests": 0, "fit_fraction_sum": 0.0,
            "fit_fraction_n": 0, "first_fit_delays": array("I"),
        }

    lineage_acc = {mask: new_lineage_accumulator() for mask in (1, 2, 3)}
    reason_vs_lineage = Counter()
    with EPISODES.open(newline="") as f:
        for row in csv.DictReader(f):
            mask = int(row["lineage_mask"])
            if mask not in lineage_acc:
                raise ValueError(f"unexpected lineage mask {mask}")
            acc = lineage_acc[mask]
            metrics = future_metrics(row)
            acc["episodes"] += 1
            acc["causes"][row["close_cause"]] += 1
            acc["lengths"].append(int(row["length"]))
            acc["lifetimes"].append(int(row["lifetime_ops"]))
            acc["censored"] += int(row["right_censored"])
            acc["observed"] += metrics["demand_requests"] > 0
            acc["any_fit"] += metrics["fit_requests"] > 0
            acc["prior_fit"] += metrics["prior_fit_unselected"]
            acc["fit_requests"] += metrics["fit_requests"]
            acc["demand_requests"] += metrics["demand_requests"]
            if metrics["fit_fraction"] is not None:
                acc["fit_fraction_sum"] += metrics["fit_fraction"]
                acc["fit_fraction_n"] += 1
            if metrics["first_fit_delay_ops"] is not None:
                acc["first_fit_delays"].append(metrics["first_fit_delay_ops"])
            reason_vs_lineage[f"{row['reason']} / mask {mask}"] += 1

    lineage_summary = {}
    for mask, acc in lineage_acc.items():
        live = [r for r in current if int(r["lineage_mask"]) == mask]
        live_metrics = [future_metrics(r, is_current=True) for r in live]
        lineage_summary[mask_name(mask)] = {
            "episodes": acc["episodes"],
            "close_causes": dict(sorted(acc["causes"].items())),
            "episode_length_m": distribution(acc["lengths"]),
            "episode_lifetime_ops": distribution(acc["lifetimes"]),
            "right_censored_share": acc["censored"] / acc["episodes"] if acc["episodes"] else None,
            "episodes_with_observed_future_demand": acc["observed"],
            "episodes_with_any_fitting_future_request": acc["any_fit"],
            "episodes_with_prior_fit_but_not_selected_before_close": acc["prior_fit"],
            "prior_fit_but_not_selected_share": acc["prior_fit"] / acc["episodes"] if acc["episodes"] else None,
            "fitting_requests_while_alive": acc["fit_requests"],
            "observed_demand_requests_while_alive": acc["demand_requests"],
            "mean_episode_fit_fraction": acc["fit_fraction_sum"] / acc["fit_fraction_n"] if acc["fit_fraction_n"] else None,
            "episode_delay_to_first_fitting_request_ops": distribution(acc["first_fit_delays"]),
            "current_gap_count": len(live),
            "current_free_length_m": sum(int(r["length"]) for r in live),
            "current_gap_length_m": distribution([int(r["length"]) for r in live]),
            "current_gap_age_at_eof_ops": distribution([int(r["age_at_eof_ops"]) for r in live]),
            "current_gap_delay_to_first_fitting_request_ops": distribution([m["first_fit_delay_ops"] for m in live_metrics if m["first_fit_delay_ops"] is not None]),
            "current_fitting_placement_op_pairs_per_gap": distribution([m["fit_requests"] for m in live_metrics]),
            "current_gaps_with_no_post_birth_fitting_request": sum(m["fit_requests"] == 0 for m in live_metrics),
            "current_gaps_with_any_post_birth_fitting_request": sum(m["fit_requests"] > 0 for m in live_metrics),
            "current_gaps_with_prior_fitting_request_before_final_operation": sum(m["prior_fit_requests"] > 0 for m in live_metrics),
            "current_gaps_whose_first_fit_is_final_operation": sum(m["first_fit_delay_ops"] == int(r["age_at_eof_ops"]) for r, m in zip(live, live_metrics)),
            "current_fit_requests_since_birth": sum(m["fit_requests"] for m in live_metrics),
            "current_prior_fit_requests_before_final_operation": sum(m["prior_fit_requests"] for m in live_metrics),
            "current_demand_requests_since_birth": sum(m["demand_requests"] for m in live_metrics),
        }

    free_total = sum(int(r["length"]) for r in current)
    current_length_bands = {}
    bands = [(1, 1, "1m"), (2, 4, "2-4m"), (5, 7, "5-7m"), (8, 16, "8-16m"), (17, 40, "17-40m"), (41, 10**12, ">40m")]
    recent_lengths = [c for c in commands if c > 0][-2048:]
    recent_hist = Counter(recent_lengths)
    whole_hist = Counter(c for c in commands if c > 0)
    for lo, hi, label in bands:
        rs = [r for r in current if lo <= int(r["length"]) <= hi]
        current_length_bands[label] = {
            "intervals": len(rs),
            "free_length_m": sum(int(r["length"]) for r in rs),
            "share_of_current_free_length": sum(int(r["length"]) for r in rs) / free_total if free_total else None,
            "intervals_fitting_any_whole_trace_request": sum(any(k <= int(r["length"]) for k in whole_hist) for r in rs),
            "intervals_fitting_any_recent_2048_request": sum(any(k <= int(r["length"]) for k in recent_hist) for r in rs),
        }

    # For each placement, count how many already-born final survivor gaps could
    # physically fit its length. These intervals persist through EOF, so any
    # such placement necessarily went to another gap/expansion. A command can
    # fit several final intervals; report both unique commands and pair counts.
    final_gaps_by_mask = {
        mask: sorted((r for r in current if int(r["lineage_mask"]) == mask), key=lambda r: int(r["birth_op"]))
        for mask in (1, 2, 3)
    }
    survivor_fit_queries = {mask: {"cursor": 0, "active_by_length": [0] * 41,
                                   "unique_placement_ops_with_fit": 0, "gap_placement_op_pairs": 0}
                            for mask in (1, 2, 3)}
    for op, command in enumerate(commands, 1):
        for mask in (1, 2, 3):
            q = survivor_fit_queries[mask]
            gaps = final_gaps_by_mask[mask]
            while q["cursor"] < len(gaps) and int(gaps[q["cursor"]]["birth_op"]) < op:
                length = min(40, int(gaps[q["cursor"]]["length"]))
                q["active_by_length"][length] += 1
                q["cursor"] += 1
            if command > 0:
                fitting = sum(q["active_by_length"][length] for length in range(command, 41))
                q["gap_placement_op_pairs"] += fitting
                q["unique_placement_ops_with_fit"] += fitting > 0
    for mask in (1, 2, 3):
        if survivor_fit_queries[mask]["gap_placement_op_pairs"] != lineage_summary[mask_name(mask)]["current_fit_requests_since_birth"]:
            raise ValueError(f"survivor fit pair audit mismatch for lineage mask {mask}")
        lineage_summary[mask_name(mask)]["unique_placement_ops_with_at_least_one_fitting_final_gap"] = survivor_fit_queries[mask]["unique_placement_ops_with_fit"]

    # Also count distinct placement operations across all lineage categories;
    # per-category unique counts can overlap and must not be added together.
    all_final_gaps = sorted(current, key=lambda r: int(r["birth_op"]))
    all_gap_cursor = 0
    all_active_by_length = [0] * 41
    all_survivor_fit_pairs = 0
    all_survivor_fit_pairs_before_final_op = 0
    all_unique_survivor_fit_ops = 0
    all_unique_survivor_fit_ops_before_final_op = 0
    for op, command in enumerate(commands, 1):
        while all_gap_cursor < len(all_final_gaps) and int(all_final_gaps[all_gap_cursor]["birth_op"]) < op:
            length = min(40, int(all_final_gaps[all_gap_cursor]["length"]))
            all_active_by_length[length] += 1
            all_gap_cursor += 1
        if command > 0:
            fitting = sum(all_active_by_length[length] for length in range(command, 41))
            all_survivor_fit_pairs += fitting
            all_unique_survivor_fit_ops += fitting > 0
            if op < n:
                all_survivor_fit_pairs_before_final_op += fitting
                all_unique_survivor_fit_ops_before_final_op += fitting > 0

    # Verify interval replay output against the trace-derived exact counts.
    recent_history_mismatch = 0
    cost_miss_mismatch = 0
    under_min_count = under_min_history_sum = under_min_misses_sum = 0
    under_min_score_sum = under_min_slack_sum = 0
    under_min_misses_equal_history = 0
    cost_audited_count = positive_slack_count = zero_slack_count = 0
    sliding_freq = [0] * 41
    sliding = deque()
    minq2 = deque()
    residual_bands = Counter()
    residual_by_parent_lineage = {1: Counter(), 2: Counter(), 3: Counter()}
    placement_row_count = 0
    with PLACEMENTS.open(newline="") as f:
        placement_iter = iter(csv.DictReader(f))
        for op, command in enumerate(commands, 1):
            if command <= 0:
                continue
            try:
                row = next(placement_iter)
            except StopIteration:
                raise ValueError("placements.csv ended before the input trace")
            placement_row_count += 1
            if int(row["op"]) != op:
                raise ValueError(f"placement row/input op mismatch at {op}")
            hist_size = len(sliding)
            hist_min = minq2[0][1] if minq2 else None
            if int(row["history_size"]) != hist_size:
                recent_history_mismatch += 1
            slack = int(row["slack"])
            miss_expected = sum(sliding_freq[s] for s in range(max(slack + 1, 1), 41)) if 0 < slack <= 40 else 0
            if int(row["misses"]) != miss_expected:
                cost_miss_mismatch += 1
            lineage = int(row["lineage_mask"])
            band = ("exact_fit_0m" if slack == 0 else "1m" if slack == 1 else
                    "2-4m" if slack <= 4 else "5-7m" if slack <= 7 else
                    "8-16m" if slack <= 16 else "17-40m" if slack <= 40 else ">40m")
            residual_bands[band] += 1
            residual_by_parent_lineage.setdefault(lineage, Counter())[band] += 1
            if op in costs:
                c_length, c_score, c_history, c_slack, c_misses = costs[op]
                if c_length != command or c_history != hist_size or c_slack != slack or c_misses != miss_expected:
                    raise ValueError(f"cost log mismatch at operation {op}")
                if int(row["total_cost"]) != slack * hist_size + 60 * miss_expected:
                    raise ValueError(f"score recomputation mismatch at operation {op}")
                cost_audited_count += 1
                positive_slack_count += slack > 0
                zero_slack_count += slack == 0
                under_min = slack > 0 and hist_min is not None and slack < hist_min and slack <= 40
                if under_min:
                    under_min_count += 1
                    under_min_history_sum += hist_size
                    under_min_misses_sum += miss_expected
                    under_min_score_sum += int(row["total_cost"])
                    under_min_slack_sum += slack
                    under_min_misses_equal_history += miss_expected == hist_size
            sliding.append((op, command))
            sliding_freq[command] += 1
            while minq2 and minq2[-1][1] > command:
                minq2.pop()
            minq2.append((op, command))
            if len(sliding) > 2048:
                old_op, old_len = sliding.popleft()
                sliding_freq[old_len] -= 1
                if minq2 and minq2[0][0] == old_op:
                    minq2.popleft()
        if next(placement_iter, None) is not None:
            raise ValueError("placements.csv has extra rows")
    if placement_row_count != placements:
        raise ValueError(f"placement rows {placement_row_count} != input placements {placements}")

    if recent_history_mismatch or cost_miss_mismatch or cost_audited_count != len(costs):
        raise ValueError(f"history/cost checks failed: {recent_history_mismatch=}, {cost_miss_mismatch=}, {cost_audited_count=}, cost_log_rows={len(costs)}")

    cost_summary = {
        "cost_audited_placements": cost_audited_count,
        "under_recent_min_positive_slack_count": under_min_count,
        "under_recent_min_positive_slack_share": under_min_count / cost_audited_count if cost_audited_count else None,
        "under_recent_min_avg_history": under_min_history_sum / under_min_count if under_min_count else None,
        "under_recent_min_avg_misses": under_min_misses_sum / under_min_count if under_min_count else None,
        "under_recent_min_avg_slack": under_min_slack_sum / under_min_count if under_min_count else None,
        "under_recent_min_misses_equal_history_count": under_min_misses_equal_history,
        "under_recent_min_avg_score": under_min_score_sum / under_min_count if under_min_count else None,
        "all_cost_rows_positive_slack": positive_slack_count,
        "all_cost_rows_exact_fit_slack_zero": zero_slack_count,
        "miss_penalty_scale": 60,
        "mechanism": "score = slack * recent_history_size + 60 * count(recent requests with length > slack), for 1 <= slack <= 40; exact-fit slack 0 has no miss term",
        "checks": {
            "history_size_mismatches": recent_history_mismatch,
            "miss_count_mismatches": cost_miss_mismatch,
            "cost_log_rows": len(costs),
        },
    }

    summary = {
        "case": 15,
        "input_weight": weight,
        "operations": n,
        "placements": placements,
        "lineage_semantics": {
            "mask_1": "placement-derived ancestry only",
            "mask_2": "deletion-derived ancestry only",
            "mask_3": "both placement- and deletion-derived ancestry",
            "note": "Grouping uses lineage_mask, not the CSV reason field, which records the latest interval-creation event and can relabel a mixed descendant as placement_residual.",
        },
        "episode_reason_vs_true_lineage_counts": dict(sorted(reason_vs_lineage.items())),
        "episode_groups_by_lineage_mask": lineage_summary,
        "current_gap_count": len(current),
        "current_free_length_m": free_total,
        "current_survivor_fit_op_pairs_since_birth": all_survivor_fit_pairs,
        "current_survivor_fit_op_pairs_before_final_operation": all_survivor_fit_pairs_before_final_op,
        "current_survivor_fit_op_pairs_on_final_operation": all_survivor_fit_pairs - all_survivor_fit_pairs_before_final_op,
        "unique_placement_ops_with_at_least_one_fitting_survivor_gap": all_unique_survivor_fit_ops,
        "unique_placement_ops_with_at_least_one_fitting_survivor_gap_before_final_operation": all_unique_survivor_fit_ops_before_final_op,
        "final_operation_command": commands[-1] if commands else None,
        "current_gap_length_bands": current_length_bands,
        "post_placement_residuals_by_consumed_parent_lineage": {
            "all_placements": {k: residual_bands[k] for k in
                               ("exact_fit_0m", "1m", "2-4m", "5-7m", "8-16m", "17-40m", ">40m")},
            **{mask_name(mask): {k: residual_by_parent_lineage[mask][k] for k in
                                ("exact_fit_0m", "1m", "2-4m", "5-7m", "8-16m", "17-40m", ">40m")}
               for mask in (1, 2, 3)},
        },
        "whole_trace_demand_histogram": {str(k): whole_hist[k] for k in sorted(whole_hist)},
        "last_2048_placement_demand_histogram": {str(k): recent_hist[k] for k in sorted(recent_hist)},
        "cost_function": cost_summary,
        "resource_and_reproducibility": {
            "analysis_wall_seconds": time.perf_counter() - started,
            "analysis_peak_rss_mib": (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
                                       if sys.platform == "darwin"
                                       else resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "hashes": {
                "baseline_final_solution.cpp": sha(FINAL_SOURCE),
                "canonical_src_pipes.cpp": sha(CANONICAL),
                "case15_input": sha(INPUT),
                "judge_output": sha(JUDGE),
                "solver_cost_audit_log": sha(COST_LOG),
                "interval_replay_source": sha(REPLAY_SOURCE),
                "interval_replay_binary": sha(REPLAY_BINARY),
                "episodes_csv": sha(EPISODES),
                "current_gaps_csv": sha(CURRENT),
                "placements_csv": sha(PLACEMENTS),
                "analyzer": sha(Path(__file__)),
            },
            "baseline_unchanged_expected_sha256": "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991",
            "canonical_unchanged_expected_sha256": "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8",
        },
    }
    if summary["resource_and_reproducibility"]["hashes"]["baseline_final_solution.cpp"] != summary["resource_and_reproducibility"]["baseline_unchanged_expected_sha256"]:
        raise ValueError("frozen final source hash changed")
    if summary["resource_and_reproducibility"]["hashes"]["canonical_src_pipes.cpp"] != summary["resource_and_reproducibility"]["canonical_unchanged_expected_sha256"]:
        raise ValueError("canonical source hash changed")

    out_path = ROOT / "analysis.json"
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
