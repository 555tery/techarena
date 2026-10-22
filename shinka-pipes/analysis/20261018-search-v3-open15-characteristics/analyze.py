"""Read-only workload characterization. Never imports evaluators or runs children."""

from collections import Counter
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
SHINKA = PROJECT / "shinka-pipes"
MAIN = SHINKA / "search-v3/task/data/search"
STRESS = SHINKA / "search-v3/stress/data"
OPEN = PROJECT / "data/pipes/open"
ALLOWED_INPUT_DIRS = {MAIN, STRESS, OPEN}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def distribution(values):
    values = [x for x in values if x is not None]
    if not values:
        return None
    return {"min": min(values), "p10": quantile(values, .10), "median": statistics.median(values),
            "p90": quantile(values, .90), "max": max(values), "mean": statistics.mean(values)}


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


def parse_input(data):
    tokens = data.split()
    if len(tokens) < 3:
        raise ValueError("missing input envelope")
    weight, n = float(tokens[0]), int(tokens[1])
    if not math.isfinite(weight) or weight <= 0 or not 1 <= n <= 200_000:
        raise ValueError("invalid weight or operation count")
    commands = list(map(int, tokens[2:]))
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != n:
        raise ValueError("declared operation count mismatch")
    return weight, commands


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


def load_case(path, group, family, expected_sha=None):
    path = path.resolve()
    if path.parent not in ALLOWED_INPUT_DIRS or path.suffix != ".in":
        raise ValueError("input outside explicit Open15/SEARCH-v3 whitelist")
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if expected_sha and sha != expected_sha:
        raise ValueError(f"input checksum changed: {path.name}")
    weight, commands = parse_input(data)
    result = characterize(commands, weight)
    result.update(id=path.stem, group=group, family=family,
                  file=str(path.relative_to(PROJECT)), sha256=sha)
    return result


def summarize(cases):
    result = {"cases": len(cases), "total_weight": sum(c["features"]["weight"] for c in cases),
              "total_operations": sum(c["features"]["operations"] for c in cases)}
    result["features"] = {key: distribution([c["features"][key] for c in cases]) for key in cases[0]["features"]}
    weight = result["total_weight"]
    result["weighted_mean"] = {key: sum(c["features"][key] * c["features"]["weight"] for c in cases
                                       if c["features"][key] is not None)
                              / sum(c["features"]["weight"] for c in cases if c["features"][key] is not None)
                              for key in cases[0]["features"] if any(c["features"][key] is not None for c in cases)}
    result["occupancy_bands"] = []
    for low, high in ((0., .3), (.3, .9), (.9, .95), (.95, 1.000001)):
        rows = [c for c in cases if low <= c["features"]["final_to_bound"] < high]
        result["occupancy_bands"].append({"low_inclusive": low, "high_exclusive": high,
                                          "count": len(rows), "weight_share": sum(c["features"]["weight"] for c in rows) / weight,
                                          "ids": [c["id"] for c in rows]})
    return result


def tv_distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / 2


def compare(open_cases, main, stress):
    summaries = {"main": summarize(main), "stress": summarize(stress)}
    result = []
    for case in open_cases:
        row = {"id": case["id"], "weight": case["features"]["weight"], "outside_main_ranges": [], "outside_main_and_stress_ranges": []}
        for key, value in case["features"].items():
            if value is None or key in {"weight", "insertions", "deletions", "final_volume", "volume_bound", "final_live_count"}:
                continue
            interval = summaries["main"]["features"][key]
            if interval and not interval["min"] - 1e-12 <= value <= interval["max"] + 1e-12:
                row["outside_main_ranges"].append(key)
                other = summaries["stress"]["features"][key]
                if not other or not other["min"] - 1e-12 <= value <= other["max"] + 1e-12:
                    row["outside_main_and_stress_ranges"].append(key)
        nearest = min(main, key=lambda c: tv_distance(case["size_histogram"], c["size_histogram"]))
        row["nearest_main_by_size_histogram"] = {"id": nearest["id"], "family": nearest["family"],
                                                 "total_variation": tv_distance(case["size_histogram"], nearest["size_histogram"])}
        result.append(row)
    return result


def main():
    target = OUT / "report.json"
    if target.exists():
        raise FileExistsError("refusing to overwrite the completed audit")
    before = json.loads((OUT / "preservation-before.json").read_text())
    open_protocol = json.loads((SHINKA / "corpus-protocol.json").read_text())
    cases, manifests = [], {}
    for group, directory in (("main", MAIN), ("stress", STRESS)):
        manifest = json.loads((directory / "manifest.json").read_text())
        manifests[group] = digest(directory / "manifest.json")
        for spec in manifest["cases"]:
            item = load_case(directory / spec["file"], group, spec["family"], spec["sha256"])
            f = item["features"]
            for a, b in (("operations", "operation_count"), ("peak_live_count", "peak_live_count"),
                         ("peak_volume", "peak_live_volume"), ("final_volume", "final_live_volume"),
                         ("volume_bound", "volume_lower_bound"), ("insertions", "insertions"), ("deletions", "deletions")):
                if f[a] != spec["stats"][b]:
                    raise ValueError(f"independent manifest-stat disagreement: {spec['file']}: {a}")
            cases.append(item)
        print(f"characterized {group}: {manifest['case_count']} inputs", flush=True)
    for i in range(1, 16):
        path = OPEN / f"{i}.in"
        expected = open_protocol["open15_sha256"][str(path.relative_to(PROJECT))]
        cases.append(load_case(path, "open15", "official_open", expected))
    grouped = {g: [c for c in cases if c["group"] == g] for g in ("main", "stress", "open15")}
    if len({c["sha256"] for c in cases}) != len(cases):
        raise ValueError("duplicate input content across audited suites")
    differences = {name: {"before": sha, "after": digest(PROJECT / name)} for name, sha in before["files"].items()
                   if digest(PROJECT / name) != sha}
    if differences:
        raise ValueError(f"preservation guard changed: {list(differences)}")
    report = {
        "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "scope": "read-only input characterization: SEARCH-v3 main128/stress32 and canonical Open15",
        "candidate_runs": 0, "interactor_runs": 0, "compiler_runs": 0, "model_calls": 0,
        "validation_inputs_accessed": False, "current_run_modified": False,
        "preserved_source_files": len(before["files"]), "preservation_differences": differences,
        "manifests_sha256": manifests, "analyzer_sha256": digest(Path(__file__)),
        "definitions": {
            "final_to_bound": "F / (20*ceil(P/20)); P is historical peak live volume",
            "deletion_age_rank": "0=oldest live PID; 1=newest; fractions exclude deletions with one live pipe",
            "completed_lifetime": "deletion operation index minus insertion operation index, divided by trace operations",
            "censoring": "survivors are right-censored; completed-lifetime metrics describe deleted pipes only",
            "early_survivors": "pipes allocated in first 10% of operation indices and still alive at the end",
            "age_size_correlation": "Pearson on completed lifetimes only, not an unbiased full-lifetime estimate",
            "size_histogram_tv": "0.5*sum(abs(p_size-q_size)); only marginal-size similarity, not trace equivalence",
            "range_coverage": "one-dimensional empirical min/max; membership does not establish joint or mechanism coverage",
            "summaries": "per-trace statistics; Open15 also has official-weight means; no hypothesis-test p values",
            "windows": "20 operation-time bins; curves sampled at 101 positions in normalized operation time"
        },
        "summaries": {g: summarize(rows) for g, rows in grouped.items()},
        "open15_vs_main": compare(grouped["open15"], grouped["main"], grouped["stress"]), "cases": cases,
    }
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    with (OUT / "per-case.csv").open("w", newline="") as stream:
        fields = ["id", "group", "family", "file", "sha256", *cases[0]["features"]]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow({**{k: case[k] for k in fields[:5]}, **case["features"]})
    print(json.dumps({"cases": {g: len(rows) for g, rows in grouped.items()}, "source_files_preserved": len(before["files"]),
                      "output": str(target), "candidate_runs": 0, "validation_inputs_accessed": False}))


if __name__ == "__main__":
    main()
