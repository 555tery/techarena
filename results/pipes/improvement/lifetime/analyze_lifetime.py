#!/usr/bin/env python3
"""Descriptive and prequential lifetime analysis for Pipes input streams.

All predictor values are computed at pipe placement from deletions observed
before that placement. The script reads complete files for retrospective
reporting; it is not part of any solver candidate.
"""

import csv
import json
import math
import statistics
from collections import Counter, defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OPEN = ROOT / "data/pipes/open"
OUT = Path(__file__).resolve().parent / "analysis"


def parse(path):
    tokens = path.read_text(encoding="ascii").split()
    weight, n = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    assert len(commands) == n
    return weight, commands


def percentile(values, p):
    if not values:
        return None
    xs = sorted(values)
    return xs[min(len(xs) - 1, int(math.ceil(p * len(xs)) - 1))]


class Fenwick:
    """Prefix counts over monotonically assigned pipe PIDs."""

    def __init__(self, size):
        self.tree = [0] * (size + 1)

    def add(self, index, delta):
        while index < len(self.tree):
            self.tree[index] += delta
            index += index & -index

    def prefix(self, index):
        total = 0
        while index:
            total += self.tree[index]
            index -= index & -index
        return total


def trend_cohort_gate(recent, current_length, removed):
    if len(recent) < 128:
        return None
    distinct = []
    previous = None
    for request_length in reversed(recent):
        if request_length == previous:
            continue
        distinct.append(request_length)
        previous = request_length
        if len(distinct) == 3:
            break
    if len(distinct) < 3 or distinct[0] - distinct[1] != distinct[1] - distinct[2]:
        return None
    total = removed[current_length][0] + removed[current_length][1]
    dominant = max(removed[current_length])
    if total >= 8 and dominant * 100 >= total * 85:
        return {
            "length": current_length,
            "recent_distinct_lengths": distinct,
            "cohort0_deletions": removed[current_length][0],
            "cohort1_deletions": removed[current_length][1],
            "dominant_share": dominant / total,
        }
    return None


def one_case(path):
    weight, commands = parse(path)
    pipes = [None]
    live_count = 0
    active_by_pid = Fenwick(200002)
    by_length = defaultdict(lambda: [[], []])  # placement cohort -> observed lifetimes
    placed_by_length_cohort = [[0, 0] for _ in range(41)]
    by_sizebin = defaultdict(list)
    pid_parity_lifetimes = [[], []]
    pid_parity_placements = [0, 0]
    removed_ages = []
    normalized_ranks = []
    active_at_delete = []
    online_hist = defaultdict(lambda: [0.0, 0])  # sum, count; avoids future data and O(n^2) medians
    prediction_errors = defaultdict(list)
    horizon = 128
    short_history = defaultdict(lambda: [0, 0])  # positive outcomes, resolved outcomes
    short_errors = defaultdict(list)  # prequential probability, outcome
    pending_horizon = deque()
    recent = deque(maxlen=2048)
    occurrences = Counter()
    removed_cohort = [[0, 0] for _ in range(41)]
    trend_gate_at = None
    trend_gate_detail = None
    placement_count = 0
    delete_count = 0
    max_live_count = 0
    short_lives_128 = 0

    def size_bin(length):
        if length <= 4:
            return "1-4"
        if length <= 12:
            return "5-12"
        if length <= 24:
            return "13-24"
        return "25-40"

    def horizon_feature_keys(pid, length, cohort):
        return {
            "global": ("short_global",),
            "length": ("short_length", length),
            "length_parity": ("short_length_parity", length, cohort),
            "cohort_parity": ("short_cohort_parity", cohort),
            "pid_parity": ("short_pid_parity", pid % 2),
            "size_bin": ("short_size_bin", size_bin(length)),
        }

    def resolve_short_lifetime(pid, label):
        pipe = pipes[pid]
        if pipe["horizon_resolved"]:
            return
        for model, key in pipe["horizon_keys"].items():
            short_errors[model].append((pipe["short_forecasts"][model], label))
            short_history[key][0] += label
            short_history[key][1] += 1
        pipe["horizon_resolved"] = True

    def resolve_deadlines(cutoff):
        while pending_horizon and pipes[pending_horizon[0]]["place_op"] + horizon <= cutoff:
            pid = pending_horizon.popleft()
            if not pipes[pid]["horizon_resolved"]:
                # Still active after the full horizon means a negative outcome.
                resolve_short_lifetime(pid, 0)

    for op, command in enumerate(commands, 1):
        if command > 0:
            resolve_deadlines(op)
            length = command
            cohort = occurrences[length] % 2
            occurrences[length] += 1
            pid = len(pipes)
            pid_parity_placements[pid % 2] += 1
            placed_by_length_cohort[length][cohort] += 1
            # Prequential forecasts: only lifetimes completed before this placement.
            global_sum, global_count = online_hist[("global",)]
            global_fallback = global_sum / global_count if global_count else 1.0
            keys = {
                "global": ("global",),
                "length": ("length", length),
                "length_parity": ("length_parity", length, cohort),
                "cohort_parity": ("cohort_parity", cohort),
                "pid_parity": ("pid_parity", pid % 2),
                "size_bin": ("size_bin", size_bin(length)),
            }
            forecasts = {}
            for name, key in keys.items():
                total, count = online_hist[key]
                # Require modest prior support; otherwise use only past global evidence.
                forecasts[name] = total / count if count >= 5 else global_fallback
            short_keys = horizon_feature_keys(pid, length, cohort)
            global_pos, global_count = short_history[short_keys["global"]]
            global_probability = (global_pos + 1) / (global_count + 2)
            short_forecasts = {}
            for name, key in short_keys.items():
                positive_count, count = short_history[key]
                short_forecasts[name] = ((positive_count + 1) / (count + 2)
                                         if count >= 5 else global_probability)
            pipes.append({
                "pid": pid, "length": length, "cohort": cohort,
                "place_op": op, "removed_op": None, "active_rank": None,
                "forecasts": forecasts,
                "horizon_keys": short_keys,
                "short_forecasts": short_forecasts,
                "horizon_resolved": False,
            })
            pending_horizon.append(pid)
            active_by_pid.add(pid, 1)
            live_count += 1
            placement_count += 1
            max_live_count = max(max_live_count, live_count)
            recent.append(length)
        else:
            pid = -command
            pipe = pipes[pid]
            assert pipe is not None and pipe["removed_op"] is None
            # PID order equals creation order; prefix counts give rank among live PIDs.
            rank = active_by_pid.prefix(pid - 1)
            denom = max(1, live_count - 1)
            rank_frac = rank / denom
            pipe["removed_op"] = op
            pipe["active_rank"] = rank_frac
            age = op - pipe["place_op"]
            pipe["lifetime"] = age
            if age <= horizon:
                # Positive labels are observable immediately at the delete event.
                resolve_short_lifetime(pid, 1)
            removed_ages.append(age)
            pid_parity_lifetimes[pid % 2].append(age)
            normalized_ranks.append(rank_frac)
            active_at_delete.append(live_count)
            if age <= 128:
                short_lives_128 += 1
            length = pipe["length"]
            cohort = pipe["cohort"]
            by_length[length][cohort].append(age)
            by_sizebin[size_bin(length)].append(age)
            for name, key in {
                "global": ("global",),
                "length": ("length", length),
                "length_parity": ("length_parity", length, cohort),
                "cohort_parity": ("cohort_parity", cohort),
                "pid_parity": ("pid_parity", pid % 2),
                "size_bin": ("size_bin", size_bin(length)),
            }.items():
                prediction_errors[name].append(abs(math.log1p(age) - math.log1p(pipe["forecasts"][name])))
                online_hist[key][0] += age
                online_hist[key][1] += 1
            removed_cohort[length][cohort] += 1
            delete_count += 1
            active_by_pid.add(pid, -1)
            live_count -= 1
            if trend_gate_at is None:
                gate_detail = trend_cohort_gate(recent, length, removed_cohort)
                if gate_detail is not None:
                    trend_gate_at = op
                    trend_gate_detail = gate_detail
            resolve_deadlines(op)

    placed = [p for p in pipes[1:]]
    final_active = [p for p in placed if p["removed_op"] is None]
    removed_total = len(removed_ages)
    removed_by_cohort = [sum(removed_cohort[l][c] for l in range(1, 41)) for c in (0, 1)]
    pid_even_removed, pid_odd_removed = (len(pid_parity_lifetimes[0]), len(pid_parity_lifetimes[1]))
    newest_fraction = sum(x >= 0.9 for x in normalized_ranks) / max(1, len(normalized_ranks))
    oldest_fraction = sum(x <= 0.1 for x in normalized_ranks) / max(1, len(normalized_ranks))
    global_lifetime_median = statistics.median(removed_ages) if removed_ages else None
    global_lifetime_p90 = percentile(removed_ages, 0.90)
    case_rec = {
        "case": path.stem,
        "weight": weight,
        "operations": len(commands),
        "placements": placement_count,
        "deletions": delete_count,
        "final_live_pipes_censored": len(final_active),
        "deleted_fraction": delete_count / placement_count if placement_count else None,
        "peak_active_pipe_count": max_live_count,
        "median_lifetime_commands": global_lifetime_median,
        "p90_lifetime_commands": global_lifetime_p90,
        "lifetime_le_128_fraction": short_lives_128 / max(1, removed_total),
        "mean_deletion_rank_oldest0_newest1": statistics.mean(normalized_ranks) if normalized_ranks else None,
        "deleted_oldest_decile_fraction": oldest_fraction,
        "deleted_newest_decile_fraction": newest_fraction,
        "median_active_pipe_count_at_delete": statistics.median(active_at_delete) if active_at_delete else None,
        "parity_cohort0_deletions": removed_by_cohort[0],
        "parity_cohort1_deletions": removed_by_cohort[1],
        "parity_larger_share": max(removed_by_cohort) / max(1, sum(removed_by_cohort)),
        "pid_even_placements": pid_parity_placements[0],
        "pid_odd_placements": pid_parity_placements[1],
        "pid_even_deletions": pid_even_removed,
        "pid_odd_deletions": pid_odd_removed,
        "pid_parity_larger_deletion_share": max(pid_even_removed, pid_odd_removed) / max(1, pid_even_removed + pid_odd_removed),
        "median_lifetime_pid_even": statistics.median(pid_parity_lifetimes[0]) if pid_parity_lifetimes[0] else None,
        "median_lifetime_pid_odd": statistics.median(pid_parity_lifetimes[1]) if pid_parity_lifetimes[1] else None,
        "cohort_trend_gate_first_op": trend_gate_at,
        "cohort_trend_gate_detail": trend_gate_detail,
    }

    rows = []
    for length in range(1, 41):
        a, b = by_length[length]
        total = len(a) + len(b)
        if total == 0:
            continue
        rows.append({
            "case": path.stem,
            "length": length,
            "placed_cohort0": placed_by_length_cohort[length][0],
            "placed_cohort1": placed_by_length_cohort[length][1],
            "removed_cohort0": len(a),
            "removed_cohort1": len(b),
            "censored_cohort0": placed_by_length_cohort[length][0] - len(a),
            "censored_cohort1": placed_by_length_cohort[length][1] - len(b),
            "removed_total": total,
            "cohort0_median_lifetime": statistics.median(a) if a else "",
            "cohort1_median_lifetime": statistics.median(b) if b else "",
            "cohort0_p90_lifetime": percentile(a, 0.90) if a else "",
            "cohort1_p90_lifetime": percentile(b, 0.90) if b else "",
            "dominant_cohort_share": max(len(a), len(b)) / total,
            "lifetime_ratio_c1_over_c0": (statistics.median(b) / statistics.median(a)) if a and b and statistics.median(a) else "",
        })
    short_metrics = {}
    for model, values in short_errors.items():
        if not values:
            continue
        short_metrics[model] = {
            "scored_pipes": len(values),
            "positive_fraction": statistics.mean(y for _, y in values),
            "brier_score": statistics.mean((p - y) ** 2 for p, y in values),
            "log_loss": statistics.mean(
                -math.log(max(1e-12, min(1 - 1e-12, p if y else 1 - p)))
                for p, y in values
            ),
            "accuracy_at_0_5": statistics.mean((p >= 0.5) == bool(y) for p, y in values),
        }
    return case_rec, rows, prediction_errors, by_sizebin, short_metrics


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    case_rows, length_rows, per_case_prediction_rows, per_case_short_rows = [], [], [], []
    errors = defaultdict(list)
    sizebin_ages = defaultdict(list)
    short_metrics_by_model = defaultdict(list)
    for path in sorted(OPEN.glob("*.in"), key=lambda p: int(p.stem)):
        case, lengths, case_errors, bins, short_metrics = one_case(path)
        case_rows.append(case)
        length_rows.extend(lengths)
        for model, values in case_errors.items():
            errors[model].extend(values)
            per_case_prediction_rows.append({
                "case": path.stem,
                "model": model,
                "scored_deleted_pipes": len(values),
                "mean_absolute_log_lifetime_error": statistics.mean(values) if values else None,
                "median_absolute_log_lifetime_error": statistics.median(values) if values else None,
            })
        for name, values in bins.items():
            sizebin_ages[name].extend(values)
        for model, metric in short_metrics.items():
            per_case_short_rows.append({"case": path.stem, "model": model, **metric})
            short_metrics_by_model[model].append(metric)
    prediction_rows = []
    for model, values in sorted(errors.items()):
        prediction_rows.append({
            "model": model,
            "scored_deleted_pipes": len(values),
            "mean_absolute_log_lifetime_error": statistics.mean(values) if values else None,
            "median_absolute_log_lifetime_error": statistics.median(values) if values else None,
        })
    bin_rows = []
    for name in ("1-4", "5-12", "13-24", "25-40"):
        values = sizebin_ages[name]
        bin_rows.append({
            "length_bin": name,
            "deleted_pipes": len(values),
            "median_lifetime_commands": statistics.median(values) if values else None,
            "p90_lifetime_commands": percentile(values, 0.90),
            "fraction_lifetime_le_128": sum(x <= 128 for x in values) / max(1, len(values)),
        })
    short_summary_rows = []
    for model, metrics in sorted(short_metrics_by_model.items()):
        n = sum(row["scored_pipes"] for row in metrics)
        short_summary_rows.append({
            "model": model,
            "scored_pipes": n,
            "positive_fraction": sum(row["positive_fraction"] * row["scored_pipes"] for row in metrics) / n,
            "brier_score": sum(row["brier_score"] * row["scored_pipes"] for row in metrics) / n,
            "log_loss": sum(row["log_loss"] * row["scored_pipes"] for row in metrics) / n,
            "accuracy_at_0_5": sum(row["accuracy_at_0_5"] * row["scored_pipes"] for row in metrics) / n,
        })
    write_csv(OUT / "per_case.csv", case_rows)
    write_csv(OUT / "per_length_and_parity.csv", length_rows)
    write_csv(OUT / "prequential_prediction_errors.csv", prediction_rows)
    write_csv(OUT / "prequential_prediction_errors_by_case.csv", per_case_prediction_rows)
    write_csv(OUT / "short_lifetime_prediction_by_case.csv", per_case_short_rows)
    write_csv(OUT / "short_lifetime_prediction_summary.csv", short_summary_rows)
    write_csv(OUT / "lifetime_by_length_bin.csv", bin_rows)
    summary = {
        "scope": "official open traces 1..15, descriptive only",
        "predictor_protocol": "at each placement, forecast using only previously completed lifetimes; update history only on later deletion; censored pipes excluded from prediction error",
        "gate_protocol": "faithful replay of cohort-trend source's online parity and trend gate; operation position is recorded only as a retrospective diagnostic",
        "cases": case_rows,
        "prediction_errors": prediction_rows,
        "short_lifetime_prediction": {
            "target": "deleted within 128 commands of placement",
            "protocol": "prequential Beta(1,1) estimates from resolved outcomes only; a removal is positive immediately; surviving the full horizon is negative; final partial horizons are censored; exact-length or parity groups require five prior labels, otherwise use the prior global estimate",
            "models": short_summary_rows,
            "per_case": per_case_short_rows,
        },
        "lifetime_by_length_bin": bin_rows,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": len(case_rows),
        "placements": sum(x["placements"] for x in case_rows),
        "deletions": sum(x["deletions"] for x in case_rows),
        "censored": sum(x["final_live_pipes_censored"] for x in case_rows),
        "prediction_errors": prediction_rows,
        "short_lifetime_prediction": short_summary_rows,
        "lifetime_by_length_bin": bin_rows,
        "cohort_gate_cases": [x["case"] for x in case_rows if x["cohort_trend_gate_first_op"] is not None],
    }, indent=2))


if __name__ == "__main__":
    main()
