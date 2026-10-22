"""Pure workload features; no paths, files, processes, models or allocator."""

from collections import Counter
import math
import statistics

def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def correlation(n, sx, sy, sxx, syy, sxy):
    if n < 2:
        return None
    vx, vy = n * sxx - sx * sx, n * syy - sy * sy
    return (n * sxy - sx * sy) / math.sqrt(vx * vy) if vx > 0 and vy > 0 else None


class Fenwick:
    def __init__(self, n):
        self.n, self.tree = n, [0] * (n + 1)

    def add(self, index, delta):
        while index <= self.n:
            self.tree[index] += delta
            index += index & -index

    def prefix(self, index):
        total = 0
        while index:
            total += self.tree[index]
            index -= index & -index
        return total


def characterize(commands, weight=1.):
    n = len(commands)
    if not 1 <= n <= 200_000:
        raise ValueError("operation count out of bounds")
    lengths, born, alive = [0] * (n + 1), [0] * (n + 1), [False] * (n + 1)
    active = Fenwick(n)
    inserted, deleted = Counter(), Counter()
    placement_sizes, completed_ages, ranks = [], [], []
    volumes, live_counts = [0], [0]
    volume = live = pid = peak = peak_live = 0
    first_peak = last_peak = max_drawdown = 0
    closed_sx = closed_sy = closed_sxx = closed_syy = closed_sxy = 0
    oldest = newest = eligible = 0
    op_runs, current_run, current_kind = {1: [], -1: []}, 0, None
    initial_insert_run = 0
    windows = [{"insertions": 0, "deletions": 0, "insert_volume": 0} for _ in range(20)]
    for step, command in enumerate(commands, 1):
        kind = 1 if command > 0 else -1
        if kind != current_kind:
            if current_kind is not None:
                op_runs[current_kind].append(current_run)
            current_kind, current_run = kind, 0
        current_run += 1
        window = windows[min(19, (step - 1) * 20 // n)]
        if command > 0:
            if command > 40:
                raise ValueError("pipe length outside [1,40]")
            pid += 1
            lengths[pid], born[pid], alive[pid] = command, step, True
            active.add(pid, 1)
            volume += command
            live += 1
            inserted[command] += 1
            placement_sizes.append(command)
            if initial_insert_run == step - 1:
                initial_insert_run += 1
            window["insertions"] += 1
            window["insert_volume"] += command
        elif command < 0 and -command <= pid and alive[-command]:
            victim = -command
            age, length = step - born[victim], lengths[victim]
            rank = active.prefix(victim - 1)
            if live > 1:
                ranks.append(rank / (live - 1))
                oldest += rank == 0
                newest += rank == live - 1
                eligible += 1
            active.add(victim, -1)
            alive[victim] = False
            volume -= length
            live -= 1
            deleted[length] += 1
            completed_ages.append(age)
            closed_sx += length
            closed_sy += age
            closed_sxx += length * length
            closed_syy += age * age
            closed_sxy += length * age
            window["deletions"] += 1
        else:
            raise ValueError("invalid deletion or embedded zero")
        if volume > peak:
            peak, first_peak, last_peak = volume, step, step
        elif volume == peak:
            last_peak = step
        peak_live = max(peak_live, live)
        max_drawdown = max(max_drawdown, peak - volume)
        volumes.append(volume)
        live_counts.append(live)
    op_runs[current_kind].append(current_run)
    if volume <= 0:
        raise ValueError("nonpositive final volume")
    bound = 20 * ((peak + 19) // 20)
    additions, deletions = sum(inserted.values()), sum(deleted.values())
    size_hist = [inserted[x] / additions for x in range(1, 41)]
    size_entropy = -sum(p * math.log2(p) for p in size_hist if p)
    surviving = [i for i in range(1, pid + 1) if alive[i]]
    early_volume = sum(lengths[i] for i in surviving if born[i] <= n * .1)
    old_volume = sum(lengths[i] for i in surviving if n - born[i] >= n * .5)
    survivor_ages = [n - born[i] for i in surviving]
    adjacent = list(zip(placement_sizes, placement_sizes[1:]))
    same_size_runs, run = [], 1
    for a, b in adjacent:
        if a == b:
            run += 1
        else:
            same_size_runs.append(run)
            run = 1
    same_size_runs.append(run)
    lag1 = correlation(len(adjacent), sum(a for a, _ in adjacent), sum(b for _, b in adjacent),
                       sum(a*a for a, _ in adjacent), sum(b*b for _, b in adjacent), sum(a*b for a, b in adjacent))
    normalized_ages = [age / n for age in completed_ages]
    checkpoints = [round(n * k / 100) for k in range(101)]
    bins = []
    for item in windows:
        total = item["insertions"] + item["deletions"]
        bins.append({"delete_fraction": item["deletions"] / total if total else None,
                     "mean_insert_length": item["insert_volume"] / item["insertions"] if item["insertions"] else None})
    features = {
        "operations": n, "weight": weight, "insertions": additions, "deletions": deletions,
        "delete_fraction": deletions / n, "peak_live_count": peak_live, "final_live_count": live,
        "peak_volume": peak, "final_volume": volume, "volume_bound": bound,
        "final_to_bound": volume / bound, "final_to_peak": volume / peak,
        "rounding_slack_over_bound": (bound - peak) / bound,
        "mean_load_over_peak": sum(volumes[1:]) / (n * peak),
        "time_above_90pct_peak": sum(v >= .9 * peak for v in volumes[1:]) / n,
        "time_below_25pct_peak": sum(v <= .25 * peak for v in volumes[1:]) / n,
        "first_peak_position": first_peak / n, "last_peak_position": last_peak / n,
        "max_drawdown_over_peak": max_drawdown / peak,
        "initial_insert_run": initial_insert_run, "initial_insert_run_over_n": initial_insert_run / n,
        "inserted_volume_over_peak": sum(x * count for x, count in inserted.items()) / peak,
        "mean_insert_length": statistics.mean(placement_sizes), "distinct_lengths": len(inserted),
        "size_entropy_bits": size_entropy, "share_length_1": inserted[1] / additions,
        "share_length_le2": sum(inserted[x] for x in (1, 2)) / additions,
        "share_length_le4": sum(inserted[x] for x in range(1, 5)) / additions,
        "share_length_ge33": sum(inserted[x] for x in range(33, 41)) / additions,
        "adjacent_equal_size_fraction": sum(a == b for a, b in adjacent) / len(adjacent) if adjacent else None,
        "max_same_size_allocation_run": max(same_size_runs), "size_lag1_correlation": lag1,
        "fifo_deletion_fraction": oldest / eligible if eligible else None,
        "lifo_deletion_fraction": newest / eligible if eligible else None,
        "deletion_age_rank_mean": statistics.mean(ranks) if ranks else None,
        "deletion_age_rank_p10": quantile(ranks, .1), "deletion_age_rank_p90": quantile(ranks, .9),
        "completed_lifetime_median_over_n": quantile(normalized_ages, .5),
        "completed_lifetime_p90_over_n": quantile(normalized_ages, .9),
        "completed_lifetime_length_correlation": correlation(deletions, closed_sx, closed_sy, closed_sxx, closed_syy, closed_sxy),
        "right_censored_pipe_fraction": len(surviving) / additions,
        "survivor_age_median_over_n": quantile(survivor_ages, .5) / n,
        "early_survivor_volume_over_final": early_volume / volume,
        "early_survivor_volume_over_peak": early_volume / peak,
        "old_survivor_volume_over_final": old_volume / volume,
        "insert_run_max": max(op_runs[1], default=0), "delete_run_max": max(op_runs[-1], default=0),
        "insert_run_p90": quantile(op_runs[1], .9), "delete_run_p90": quantile(op_runs[-1], .9),
    }
    return {"features": features, "size_histogram": size_hist,
            "inserted_length_counts": dict(sorted(inserted.items())), "deleted_length_counts": dict(sorted(deleted.items())),
            "load_curve": [volumes[t] / peak for t in checkpoints],
            "live_count_curve": [live_counts[t] / peak_live for t in checkpoints], "windows": bins}
