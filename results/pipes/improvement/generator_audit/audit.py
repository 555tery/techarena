#!/usr/bin/env python3
"""Strictly chronological audit of removal-rank and short-lifetime signals.

This is analysis only: it never edits or runs the allocator. Every forecast is
made from labels that have already become observable at the current operation.
"""

import hashlib
import json
import math
import random
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OPEN = ROOT / "data/pipes/open"
SYNTHETIC = ROOT / "results/pipes/improvement/flow_predictors/synthetic"
ALPHA = 1.0
HORIZON = 128


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path):
    tokens = path.read_text(encoding="ascii").split()
    weight = float(tokens[0])
    n = int(tokens[1])
    commands = list(map(int, tokens[2:]))
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != n:
        raise ValueError(f"{path}: declared {n}, found {len(commands)} commands")
    return weight, commands


class Fenwick:
    def __init__(self, n):
        self.tree = [0] * (n + 1)

    def add(self, i, d):
        while i < len(self.tree):
            self.tree[i] += d
            i += i & -i

    def prefix(self, i):
        s = 0
        while i:
            s += self.tree[i]
            i -= i & -i
        return s


def dist(counts, alpha=ALPHA):
    total = sum(counts)
    return [(x + alpha) / (total + alpha * len(counts)) for x in counts]


def multiclass(rows, model):
    if not rows:
        return {"n": 0}
    n = len(rows)
    brier = ll = hit = 0.0
    for row in rows:
        p, y = row[model], row["y"]
        brier += sum((p[j] - (j == y)) ** 2 for j in range(4))
        ll -= math.log(max(1e-15, p[y]))
        hit += int(max(range(4), key=lambda j: p[j]) == y)
    return {"n": n, "accuracy": hit / n, "brier": brier / n, "logloss": ll / n}


def block_ci(rows, value_fn, block_width=128, reps=2000, seed=20261017):
    blocks = defaultdict(list)
    for row in rows:
        blocks[(row["op"] - 1) // block_width].append(row)
    groups = list(blocks.values())
    if len(groups) < 8:
        return {"nonempty_blocks": len(groups), "ci95": None}
    stats = [(sum(value_fn(r) for r in group), len(group)) for group in groups]
    rng = random.Random(seed + len(rows))
    values = []
    for _ in range(reps):
        chosen = [rng.choice(stats) for _ in range(len(stats))]
        values.append(sum(s for s, _ in chosen) / sum(n for _, n in chosen))
    values.sort()
    return {"nonempty_blocks": len(groups),
            "ci95": [values[int(.025 * (reps - 1))], values[int(.975 * (reps - 1))]]}


def rank_audit(commands):
    n = len(commands)
    max_pid = sum(x > 0 for x in commands)
    fw = Fenwick(max_pid + 2)
    live = 0
    rank_rows = []
    pid_lengths = [0] * (max_pid + 1)
    next_pid = 0
    train_cut = int(.40 * n)
    test_cut = int(.60 * n)
    all_counts = [0] * 4
    trans = [[0] * 4 for _ in range(4)]
    recent_bands = deque(maxlen=64)
    recent_ranks = deque(maxlen=64)
    previous = None
    phase_changes = 0
    test_phase_changes = 0
    last_mode = None
    test_rows = []

    for op, x in enumerate(commands, 1):
        if x > 0:
            next_pid += 1
            pid_lengths[next_pid] = x
            fw.add(next_pid, 1)
            live += 1
            continue

        pid = -x
        if not (1 <= pid <= next_pid) or fw.prefix(pid) - fw.prefix(pid - 1) != 1:
            raise ValueError(f"invalid delete at op={op}, pid={pid}")
        newer = live - fw.prefix(pid)
        denominator = max(1, live - 1)
        permille = newer * 1000 // denominator if live > 1 else 0
        y = min(3, permille * 4 // 1001)

        if op > test_cut:
            global_p = dist(all_counts)
            if previous is None:
                markov_p = global_p
            else:
                markov_p = dist(trans[previous])
            recent_p = dist([recent_bands.count(j) for j in range(4)])
            row = {"op": op, "y": y, "stationary": global_p,
                   "markov1": markov_p, "recent64": recent_p}
            test_rows.append(row)

        # Existing causal detector in survival_hazard: same 64-event mean,
        # rank-from-newest permille convention, and 16-observation minimum.
        if len(recent_ranks) >= 16:
            mean_recent = sum(recent_ranks) / len(recent_ranks)
            mode = "lifo" if mean_recent <= 250 else "fifo" if mean_recent >= 750 else "mixed"
            if last_mode is not None and mode != last_mode:
                phase_changes += 1
                if op > test_cut:
                    test_phase_changes += 1
            last_mode = mode

        if previous is not None:
            trans[previous][y] += 1
        all_counts[y] += 1
        previous = y
        recent_bands.append(y)
        recent_ranks.append(permille)
        fw.add(pid, -1)
        live -= 1

    cuts = [test_cut + (n - test_cut) * q // 4 for q in range(5)]
    phases = []
    for q in range(4):
        events = [r for r in test_rows if cuts[q] < r["op"] <= cuts[q + 1]]
        bins = [sum(r["y"] == j for r in events) for j in range(4)]
        phases.append({"phase": q + 1, "op_range_inclusive": [cuts[q] + 1, cuts[q + 1]],
                       "n": len(events), "rank_band_counts": bins,
                       "mean_rank_band": sum(i * c for i, c in enumerate(bins)) / max(1, len(events)),
                       "markov1_accuracy": multiclass(events, "markov1").get("accuracy")})

    metrics = {m: multiclass(test_rows, m) for m in ("stationary", "markov1", "recent64")}
    improve_rows = []
    for r in test_rows:
        y = r["y"]
        p0, pm = r["stationary"], r["markov1"]
        ll_gain = math.log(max(1e-15, pm[y])) - math.log(max(1e-15, p0[y]))
        b0 = sum((p0[j] - (j == y)) ** 2 for j in range(4))
        bm = sum((pm[j] - (j == y)) ** 2 for j in range(4))
        improve_rows.append({"op": r["op"], "ll_gain": ll_gain, "brier_gain": b0 - bm})

    test_mean_band = metrics["stationary"].get("n", 0)
    test_bins = [sum(r["y"] == j for r in test_rows) for j in range(4)]
    return {
        "n_deletions": sum(all_counts),
        "train_end_op_exclusive": train_cut,
        "validation_ops": [train_cut + 1, test_cut],
        "test_ops": [test_cut + 1, n],
        "test_n_deletions": len(test_rows),
        "test_rank_band_counts": test_bins,
        "test_rank_sequence_models": metrics,
        "markov1_minus_stationary": {
            "mean_logloss_improvement": sum(r["ll_gain"] for r in improve_rows) / max(1, len(improve_rows)),
            "logloss_improvement_ci95_by_128op_blocks": block_ci(improve_rows, lambda r: r["ll_gain"], seed=9001),
            "mean_brier_improvement": sum(r["brier_gain"] for r in improve_rows) / max(1, len(improve_rows)),
            "brier_improvement_ci95_by_128op_blocks": block_ci(improve_rows, lambda r: r["brier_gain"], seed=9101),
        },
        "heldout_time_quartiles": phases,
        "survival_hazard_trailing64_mode_changes_all_time": phase_changes,
        "survival_hazard_trailing64_mode_changes_in_test": test_phase_changes,
    }


def binary_metrics(rows, model):
    if not rows:
        return {"n": 0}
    n = len(rows)
    brier = ll = acc = 0.0
    cal = [[] for _ in range(10)]
    for r in rows:
        p, y = r[model], r["y"]
        p = min(1 - 1e-12, max(1e-12, p))
        brier += (p - y) ** 2
        ll -= y * math.log(p) + (1 - y) * math.log(1 - p)
        acc += int((p >= .5) == bool(y))
        cal[min(9, int(p * 10))].append((p, y))
    ece = sum(len(g) / n * abs(sum(p for p, _ in g) / len(g) - sum(y for _, y in g) / len(g))
              for g in cal if g)
    return {"n": n, "prevalence": sum(r["y"] for r in rows) / n,
            "brier": brier / n, "logloss": ll / n, "accuracy_at_0_5": acc / n, "ece10": ece}


def lifetime_audit(commands):
    n = len(commands)
    test_start = int(.60 * n)
    max_pid = sum(x > 0 for x in commands)
    birth = [0] * (max_pid + 1)
    lengths = [0] * (max_pid + 1)
    resolved = [False] * (max_pid + 1)
    alive = [False] * (max_pid + 1)
    forecasts = [None] * (max_pid + 1)
    pending = deque()
    global_count = global_pos = 0
    by_length = defaultdict(lambda: [0, 0])
    recent = deque(maxlen=128)
    scored = {m: [] for m in ("global", "exact_length", "recent128")}
    test_placements = 0
    next_pid = 0

    def global_probability():
        return (global_pos + 1) / (global_count + 2)

    def predict(length):
        pg = global_probability()
        lp, ln = by_length[length]
        pe = (lp + 1) / (ln + 2) if ln >= 5 else pg
        rp = (sum(recent) + 1) / (len(recent) + 2)
        return {"global": pg, "exact_length": pe, "recent128": rp}

    def resolve(pid, y, current_op):
        nonlocal global_count, global_pos
        if resolved[pid]:
            return
        resolved[pid] = True
        pred = forecasts[pid]
        if pred is not None and birth[pid] > test_start and birth[pid] + HORIZON <= n:
            phase = min(3, (birth[pid] - test_start) * 4 // max(1, n - test_start))
            for model in scored:
                scored[model].append({"op": birth[pid], "resolve_op": current_op,
                                      "phase": phase + 1, "y": y, model: pred[model]})
        global_count += 1
        global_pos += y
        by_length[lengths[pid]][0] += y
        by_length[lengths[pid]][1] += 1
        recent.append(y)

    for op, x in enumerate(commands, 1):
        due_positive = []
        if x > 0:
            next_pid += 1
            birth[next_pid] = op
            lengths[next_pid] = x
            alive[next_pid] = True
            forecasts[next_pid] = predict(x)
            if op > test_start and op + HORIZON <= n:
                test_placements += 1
            pending.append(next_pid)
        else:
            pid = -x
            if not (1 <= pid <= next_pid) or not alive[pid]:
                raise ValueError(f"invalid lifetime deletion at op={op}, pid={pid}")
            alive[pid] = False
            if not resolved[pid] and op - birth[pid] <= HORIZON:
                due_positive.append(pid)

        # Positive observation at this operation overrides a deadline on the
        # same operation. Then all fully observed negative horizons are resolved.
        batch = [(birth[pid], pid, 1) for pid in due_positive]
        while pending and birth[pending[0]] + HORIZON <= op:
            pid = pending.popleft()
            if not resolved[pid] and pid not in due_positive:
                batch.append((birth[pid], pid, 0))
        for _, pid, y in sorted(batch):
            resolve(pid, y, op)

    all_rows = [r for m in scored for r in scored[m]]
    by_phase = {}
    for phase in range(1, 5):
        by_phase[str(phase)] = {m: binary_metrics([r for r in rows if r["phase"] == phase], m)
                                for m, rows in scored.items()}
    improvement = {}
    global_rows = scored["global"]
    for model in ("exact_length", "recent128"):
        paired = []
        for base, cand in zip(global_rows, scored[model]):
            if base["op"] != cand["op"] or base["y"] != cand["y"]:
                raise AssertionError("model row alignment broken")
            p0, p1, y = base["global"], cand[model], base["y"]
            b0, b1 = (p0 - y) ** 2, (p1 - y) ** 2
            paired.append({"op": base["op"], "brier_gain": b0 - b1,
                           "ll_gain": (y * math.log(p1) + (1-y) * math.log(1-p1)) -
                                      (y * math.log(p0) + (1-y) * math.log(1-p0))})
        improvement[model] = {
            "mean_brier_improvement_vs_global": sum(r["brier_gain"] for r in paired) / max(1, len(paired)),
            "brier_improvement_ci95_by_128op_blocks": block_ci(paired, lambda r: r["brier_gain"], seed=1101),
            "mean_logloss_improvement_vs_global": sum(r["ll_gain"] for r in paired) / max(1, len(paired)),
            "logloss_improvement_ci95_by_128op_blocks": block_ci(paired, lambda r: r["ll_gain"], seed=1201),
        }
    return {
        "horizon_operations": HORIZON,
        "split": {"train_first40pct": [1, int(.40*n)], "validation_next20pct": [int(.40*n)+1, test_start],
                  "heldout_test_final40pct": [test_start+1, n]},
        "heldout_test_eligible_placements": test_placements,
        "heldout_test_scored_after_full_horizon": len(scored["global"]),
        "models": {m: binary_metrics(rows, m) for m, rows in scored.items()},
        "test_phase_metrics_by_birth_time": by_phase,
        "improvement_vs_global": improvement,
        "note": "All forecast states update only when a deletion is observed or a full 128-operation horizon has elapsed. Test labels from a test placement affect only later predictions after their resolution; final censored horizons are excluded.",
    }


def case_audit(path):
    _, commands = parse(path)
    return {"operations": len(commands), "rank_sequence": rank_audit(commands),
            "short_lifetime": lifetime_audit(commands)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    official = {}
    for p in sorted(OPEN.glob("*.in"), key=lambda q: int(q.stem)):
        official[p.stem] = {"input_sha256": sha(p), **case_audit(p)}
    synthetic = {}
    for p in sorted(SYNTHETIC.glob("*.in")):
        synthetic[p.stem] = {"input_sha256": sha(p), **case_audit(p)}
    upstream = {
        "flow_predictors_report_sha256": sha(ROOT / "results/pipes/improvement/flow_predictors/REPORT.md"),
        "flow_predictors_metrics_sha256": sha(ROOT / "results/pipes/improvement/flow_predictors/metrics.json"),
        "lifetime_report_sha256": sha(ROOT / "results/pipes/improvement/lifetime/REPORT.md"),
        "survival_hazard_report_sha256": sha(ROOT / "results/pipes/improvement/survival_hazard/REPORT.md"),
        "final_source_sha256": sha(ROOT / "results/pipes/final/solution.cpp"),
    }
    result = {
        "protocol": {
            "official_temporal_split": "train rows first 40% of operation time; validation next 20%; held-out test final 40%. Rank models are fixed, with no validation tuning; all models update prequentially only after observing each deletion. Lifetime target is removal within the next 128 command operations, with delayed labels and fully observed horizons only.",
            "rank": "rank-from-newest permille is reproduced as floor(newer_active*(1000)/(active_count-1)); 0 is newest/LIFO and 1000 oldest/FIFO, matching final solution.cpp. Four bins use floor(permille*4/1001). Models: cumulative stationary Dirichlet(1), first-order Markov with Dirichlet(1), and trailing 64 observed deletion ranks. Test only begins after the 60% op cut.",
            "lifetime": "At placement compare global Beta(1,1), exact length Beta(1,1) when at least 5 prior resolved labels else global, and recent 128 resolved labels Beta(1,1). A positive is known on deletion if age<=128; a negative is known only once the horizon passes. No unresolved/censored labels are scored.",
            "phase": "Held-out final 40% divided into four equal operation-time quarters. Phase results use fixed model definitions and causal prequential state updates.",
            "uncertainty": "Paired bootstrap resamples nonempty, nonoverlapping 128-operation blocks within each case, 2,000 replicates, deterministic seeds. Intervals are conditional on the public trace and do not imply hidden-test uncertainty.",
            "synthetic": "Existing fixed LIFO/FIFO/periodic-size+deletion/regime-shift/random-churn files are re-scored for rank and lifetime diagnostics; they are mechanism checks, not independent official evidence.",
        },
        "upstream_sha256": upstream,
        "official_cases": official,
        "existing_synthetic": synthetic,
    }
    out = OUT / "audit.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(out), "official_cases": len(official),
                      "synthetic_cases": len(synthetic), "final_source_sha256": upstream["final_source_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
