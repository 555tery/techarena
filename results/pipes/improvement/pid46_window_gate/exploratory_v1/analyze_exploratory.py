#!/usr/bin/env python3
"""Replay pre-registered gate/lane exposure and paired synthetic outcomes."""
import csv
import hashlib
import json
import random
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOOTSTRAP_N = 20000


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def smooth_size_trend(history, current):
    if not history:
        return False
    current_already = history[-1] == current
    prior = []
    first = True
    last = -1
    for value in reversed(history):
        if first:
            first = False
            last = value
            if not current_already:
                prior.append(value)
            continue
        if value == last:
            continue
        last = value
        prior.append(value)
        if len(prior) == 2:
            break
    return len(prior) == 2 and current - prior[0] == prior[0] - prior[1]


def exposure(path):
    tokens = Path(path).read_text(encoding="ascii").split()
    commands = [int(x) for x in tokens[2:]]
    if commands and commands[-1] == 0:
        commands.pop()
    history = deque(maxlen=2048)
    removals = deque(maxlen=64)
    removal_counts = [0, 0]
    occurrences = [0] * 41
    active = set()
    placements = 0
    disabled = False
    runleft_active = gate_active = divergence = equal = 0
    first = None
    for command in commands:
        if command == 0:
            break
        if command > 0:
            if smooth_size_trend(history, command):
                disabled = True
            runleft = (not disabled and len(history) >= 46 and len(history) >= 46 and
                       all(v == command for v in list(history)[-46:]))
            count = len(removals)
            dominant = max(removal_counts)
            gate = count >= 32 and dominant * 4 >= count * 3
            pid = placements + 1
            cohort = occurrences[command] & 1
            if runleft:
                runleft_active += 1
            if gate:
                gate_active += 1
            if runleft and gate:
                # Candidate maps even PID to high, odd PID to low; c4 maps cohort 1 to high.
                candidate_high = (pid % 2 == 0)
                baseline_high = (cohort != 0)
                if candidate_high != baseline_high:
                    divergence += 1
                else:
                    equal += 1
                if first is None:
                    first = {"placement": pid, "removals_in_window": count,
                             "dominant_count": dominant, "dominant_parity": removal_counts.index(dominant),
                             "candidate_high": candidate_high, "baseline_high": baseline_high}
            active.add(pid)
            occurrences[command] += 1
            history.append(command)
            placements += 1
        else:
            pid = -command
            if pid not in active:
                raise ValueError(f"invalid removal pid {pid} in {path}")
            active.remove(pid)
            parity = pid & 1
            if len(removals) == 64:
                expired = removals[0]
                removal_counts[expired] -= 1
            removals.append(parity)
            removal_counts[parity] += 1
    if placements < 1 or not active:
        raise ValueError(f"stream has no final active pipe: {path}")
    return {"placements": placements, "runleft_active_placements": runleft_active,
            "gate_active_placements": gate_active, "runleft_and_gate_placements": divergence + equal,
            "lane_divergences": divergence, "lane_equal": equal,
            "smooth_trend_latched": disabled, "first_gate_runleft": first,
            "active_at_end": len(active)}


def pct(values, q):
    vals = sorted(values)
    x = (len(vals) - 1) * q
    lo = int(x)
    hi = min(lo + 1, len(vals) - 1)
    frac = x - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def bootstrap(values, seed):
    rng = random.Random(seed)
    n = len(values)
    means = [sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOTSTRAP_N)]
    return {"n": n, "mean": sum(values) / n,
            "ci95_percentile": [pct(means, .025), pct(means, .975)],
            "positive": sum(x > 0 for x in values), "negative": sum(x < 0 for x in values),
            "zero": sum(x == 0 for x in values)}


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return {r["case"]: r for r in csv.DictReader(f)}


def inspect_exposure():
    manifest = json.loads((ROOT / "validation/stream_manifest.json").read_text())
    per = []
    for cfg in manifest:
        exp = exposure(ROOT / cfg["path"])
        per.append({"case": cfg["case"], "seed": cfg["seed"],
                    "primary_policy": cfg["primary_policy"], "phase2_policy": cfg["phase2_policy"],
                    "prefix_parity": cfg["prefix_parity"], "phase1_run_length": cfg["phase1_run_length"],
                    "phase2_run_length": cfg["phase2_run_length"], **exp})
    summary = {"stream_count": len(per), "total_divergences": sum(x["lane_divergences"] for x in per),
               "streams_with_divergence": sum(x["lane_divergences"] > 0 for x in per),
               "parity_primary_divergences": sum(x["lane_divergences"] for x in per if x["primary_policy"].startswith("parity_")),
               "control_primary_divergences": sum(x["lane_divergences"] for x in per if not x["primary_policy"].startswith("parity_")),
               "total_runleft_and_gate": sum(x["runleft_and_gate_placements"] for x in per),
               "smooth_trend_latched_streams": sum(x["smooth_trend_latched"] for x in per),
               "pre_run_exposure_gate_pass": (sum(x["lane_divergences"] for x in per) >= 500 and
                                               sum(x["lane_divergences"] > 0 for x in per) >= 8)}
    (ROOT / "exposure_per_stream.json").write_text(json.dumps(per, indent=2) + "\n")
    (ROOT / "exposure_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return per, summary


def paired_analysis():
    prereg = json.loads((ROOT / "PRE_REGISTRATION.json").read_text())
    manifest = json.loads((ROOT / "validation/stream_manifest.json").read_text())
    base = rows(ROOT / "baseline-run/cases.csv")
    cand = rows(ROOT / "candidate-run/cases.csv")
    exp_by_case = {x["case"]: x for x in json.loads((ROOT / "exposure_per_stream.json").read_text())}
    pairs = []
    all_ok = True
    for cfg in manifest:
        key = cfg["case"]
        b, c = base[key], cand[key]
        same_input = b["test_sha256"] == c["test_sha256"]
        ok = b["status"] == "ok" and c["status"] == "ok" and same_input
        all_ok = all_ok and ok
        parity_primary = cfg["primary_policy"].startswith("parity_")
        pairs.append({"case": key, "seed": cfg["seed"], "primary_policy": cfg["primary_policy"],
                      "phase2_policy": cfg["phase2_policy"], "prefix_parity": cfg["prefix_parity"],
                      "phase1_run_length": cfg["phase1_run_length"], "phase2_run_length": cfg["phase2_run_length"],
                      "same_input": same_input, "baseline_status": b["status"], "candidate_status": c["status"],
                      "baseline_kpi": float(b["kpi"]), "candidate_kpi": float(c["kpi"]),
                      "delta_kpi": float(c["kpi"]) - float(b["kpi"]),
                      "baseline_trench_m": int(b["trench_length_m"]), "candidate_trench_m": int(c["trench_length_m"]),
                      "delta_trench_m": int(c["trench_length_m"]) - int(b["trench_length_m"]),
                      "baseline_cpu_s": float(b["solver_cpu_total_s"]), "candidate_cpu_s": float(c["solver_cpu_total_s"]),
                      "baseline_rss_mib": float(b["solver_peak_rss_mb"]), "candidate_rss_mib": float(c["solver_peak_rss_mb"]),
                      "lane_divergences": exp_by_case[key]["lane_divergences"],
                      "parity_primary": parity_primary})
    seed = prereg["design"]["analysis_seed"]
    overall = bootstrap([r["delta_kpi"] for r in pairs], seed)
    parity = bootstrap([r["delta_kpi"] for r in pairs if r["parity_primary"]], seed)
    controls = bootstrap([r["delta_kpi"] for r in pairs if not r["parity_primary"]], seed)
    exposure_summary = json.loads((ROOT / "exposure_summary.json").read_text())
    gate = {
        "all_official_transcripts_ok_and_paired": all_ok,
        "exposure_floor_pass": exposure_summary["pre_run_exposure_gate_pass"],
        "overall_mean_at_least_0_0001": overall["mean"] >= .0001,
        "overall_ci95_lower_above_zero": overall["ci95_percentile"][0] > 0,
        "parity_primary_mean_positive": parity["mean"] > 0,
        "parity_primary_ci95_lower_above_zero": parity["ci95_percentile"][0] > 0,
        "control_primary_mean_nonnegative": controls["mean"] >= 0,
        "resources_within_limits": all(r["candidate_cpu_s"] < 5 and r["candidate_rss_mib"] < 256 for r in pairs),
    }
    gate["pass"] = all(gate.values())
    summary = {"all_official_transcripts_ok_and_paired": all_ok,
               "identical_inputs": sum(r["same_input"] for r in pairs),
               "identical_candidate_baseline_trench_streams": sum(r["delta_trench_m"] == 0 for r in pairs),
               "streams_candidate_lower_trench": sum(r["delta_trench_m"] < 0 for r in pairs),
               "streams_candidate_higher_trench": sum(r["delta_trench_m"] > 0 for r in pairs),
               "baseline_weighted_score_sum": sum(r["baseline_kpi"] for r in pairs),
               "candidate_weighted_score_sum": sum(r["candidate_kpi"] for r in pairs),
               "overall_paired_bootstrap": overall, "parity_primary_bootstrap": parity,
               "control_primary_bootstrap": controls,
               "candidate_max_cpu_s": max(r["candidate_cpu_s"] for r in pairs),
               "candidate_max_rss_mib": max(r["candidate_rss_mib"] for r in pairs),
               "decision_checks": gate}
    with (ROOT / "paired_validation.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0]))
        w.writeheader(); w.writerows(pairs)
    (ROOT / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["exposure", "paired"])
    args = parser.parse_args()
    if args.action == "exposure":
        _, result = inspect_exposure()
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(paired_analysis(), indent=2))
