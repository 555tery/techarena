#!/usr/bin/env python3
"""Preregister and generate post-hoc exploratory synthetic PID46 streams."""
import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICIES = ["parity_even", "parity_odd", "random", "oldest", "newest", "alternating"]
RUN_LENGTHS = [95, 96, 191, 192]
PROFILES = ["uniform", "short-heavy", "long-heavy", "bimodal"]
SEED_START = 940001
ANALYSIS_SEED = 940999


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sample_length(rng, profile):
    if profile == "uniform":
        return rng.randint(1, 40)
    if profile == "short-heavy":
        x = rng.random()
        return rng.randint(1, 5) if x < .65 else (rng.randint(6, 20) if x < .90 else rng.randint(21, 40))
    if profile == "long-heavy":
        x = rng.random()
        return rng.randint(1, 5) if x < .10 else (rng.randint(6, 20) if x < .35 else rng.randint(21, 40))
    if profile == "bimodal":
        return rng.randint(1, 8) if rng.random() < .5 else rng.randint(32, 40)
    raise ValueError(profile)


def pick_length(rng, profile, excluded):
    for _ in range(10000):
        value = sample_length(rng, profile)
        if value not in excluded:
            return value
    raise RuntimeError("could not choose a non-excluded length")


def is_arithmetic_triple(a, b, c):
    return c - b == b - a


def profile_target(rng, profile, excluded):
    # Limit target sizes away from 1/40 only for no special reason? Keep all 1..40 eligible.
    return pick_length(rng, profile, excluded)


def secondary_policy(primary, index):
    mapping = {
        "parity_even": "random",
        "parity_odd": "oldest",
        "random": "parity_even",
        "oldest": "parity_odd",
        "newest": "alternating",
        "alternating": "newest",
    }
    return mapping[primary]


def configs():
    out = []
    index = 0
    for policy in POLICIES:
        for run_index, run_length in enumerate(RUN_LENGTHS):
            for prefix_parity, prefix_count in enumerate((100, 101)):
                seed = SEED_START + index
                profile = PROFILES[index % len(PROFILES)]
                churn = (0.45, 0.55, 0.65)[index % 3]
                spacer_count = (5, 6, 7, 8)[(index // 2) % 4]
                out.append({
                    "case": f"validation_{index + 1:02d}_{seed}",
                    "seed": seed,
                    "primary_policy": policy,
                    "phase2_policy": secondary_policy(policy, index),
                    "prefix_placements": prefix_count,
                    "prefix_parity": "odd" if prefix_count % 2 else "even",
                    "phase1_run_length": run_length,
                    "phase2_run_length": RUN_LENGTHS[(run_index + 1) % len(RUN_LENGTHS)],
                    "phase1_profile": profile,
                    "phase2_profile": PROFILES[(index + 1) % len(PROFILES)],
                    "churn_probability": churn,
                    "spacer_placements": spacer_count,
                    "tail_placements": 20,
                })
                index += 1
    return out


def make_preregistration():
    baseline = ROOT / "baseline.cpp"
    candidate = ROOT / "candidate.cpp"
    generator = Path(__file__).resolve()
    return {
        "experiment": "pid46_window_gate_exploratory_v1",
        "status": "posthoc_exploratory_preregistered_before_new_stream_generation",
        "preregistered_at_local_time": "2026-10-17T08:00:00+07:00",
        "candidate_rule_unchanged": {
            "baseline_source_sha256": "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991",
            "candidate_source_sha256": "91aba259929fc45ce0f520b5a8ff22dea7cce203ea6d9c28aae687babf71ecc4",
            "run_threshold": 46,
            "removal_window": 64,
            "minimum_removals": 32,
            "dominant_pid_parity_fraction": "at least 3/4 by integer arithmetic",
            "mapping": "even next PID to high edge; odd next PID to low edge",
            "fallback": "frozen c4 size-cohort edge; all other rules remain frozen",
        },
        "design": {
            "generation": "Deterministic Python random.Random per stream seed; no Open/holdout inputs; no test-number features.",
            "streams": configs(),
            "components": [
                "Mixed-size 100/101-placement prefix with short blocks, excluding both long-run lengths from its sizes.",
                "Long same-size phase with one of four run lengths 95/96/191/192, varying odd/even length.",
                "Deletion policy and size distribution change, followed by a second distinct long same-size phase.",
                "Deletion modes include parity-even, parity-odd, random, oldest, newest and alternating.",
                "Final 20 placements have no removals so every stream has positive final occupancy.",
            ],
            "pre-run_exposure_gate": {
                "minimum_total_runLeft_and_gate_lane_divergence_opportunities": 500,
                "minimum_streams_with_at_least_one_divergence": 8,
                "failure_interpretation": "uninformative/null contrast; do not score or run Open/holdout",
            },
            "primary_analysis": {
                "unit": "whole stream paired baseline versus candidate on byte-identical input",
                "metric": "official per-stream KPI; trench delta in meters also reported",
                "bootstrap": "20000 whole-stream paired percentile bootstrap resamples, fixed seed 940999",
                "validation_success_gate": [
                    "all official-interactor transcripts pass and inputs are byte-identical",
                    "mean paired KPI delta >= +0.0001 and 95% bootstrap CI lower endpoint > 0",
                    "parity-biased-primary subset has positive mean and 95% CI lower endpoint > 0",
                    "non-parity-primary controls have mean delta >= 0",
                    "all candidate CPU < 5 seconds and RSS < 256 MiB per stream",
                    "pre-run exposure gate passes",
                ],
                "post_gate": "Do not run Open15 or holdout in this exploratory turn; report to coordinator for decision.",
            },
            "analysis_seed": ANALYSIS_SEED,
            "stream_seed_start": SEED_START,
        },
        "baseline_source_sha256": sha256(baseline),
        "candidate_source_sha256": sha256(candidate),
        "generator_sha256": sha256(generator),
        "baseline_binary_sha256": sha256(ROOT / "baseline"),
        "candidate_binary_sha256": sha256(ROOT / "candidate"),
    }


def write_preregistration(path):
    path.write_text(json.dumps(make_preregistration(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote preregistration", path)


def add_removal(rng, commands, active, policy, alternating):
    if not active:
        return alternating
    if policy == "random":
        pid = rng.choice(active)
    elif policy == "oldest":
        pid = min(active)
    elif policy == "newest":
        pid = max(active)
    elif policy == "parity_even":
        candidates = [pid for pid in active if pid % 2 == 0]
        if not candidates:
            return alternating
        pid = rng.choice(candidates)
    elif policy == "parity_odd":
        candidates = [pid for pid in active if pid % 2 == 1]
        if not candidates:
            return alternating
        pid = rng.choice(candidates)
    elif policy == "alternating":
        candidates = [pid for pid in active if pid % 2 == alternating]
        if not candidates:
            candidates = [pid for pid in active if pid % 2 != alternating]
        pid = rng.choice(candidates)
        alternating = 1 - alternating
    else:
        raise ValueError(policy)
    active.remove(pid)
    commands.append(-pid)
    return alternating


def append_placement(commands, active, next_pid, length, rng, policy, churn, alternating, allow_delete=True):
    pid = next_pid
    next_pid += 1
    commands.append(length)
    active.append(pid)
    if allow_delete and rng.random() < churn:
        alternating = add_removal(rng, commands, active, policy, alternating)
    return next_pid, alternating


def append_mixed_prefix(config, rng, commands, active, next_pid, alternating):
    count = config["prefix_placements"]
    profile = config["phase1_profile"]
    excluded = {config["phase1_target_length"], config["phase2_target_length"]}
    sizes = []
    remaining = count
    while remaining:
        size = None
        for _ in range(10000):
            candidate = pick_length(rng, profile, excluded)
            if sizes and candidate == sizes[-1]:
                continue
            distinct = []
            for v in reversed(sizes):
                if not distinct or v != distinct[-1]:
                    distinct.append(v)
                if len(distinct) == 2:
                    break
            if len(distinct) == 2 and is_arithmetic_triple(distinct[1], distinct[0], candidate):
                continue
            size = candidate
            break
        if size is None:
            raise RuntimeError("could not construct prefix sizes without smooth triples")
        block = min(remaining, rng.randint(6, 15))
        sizes.extend([size] * block)
        remaining -= block
    for length in sizes:
        next_pid, alternating = append_placement(
            commands, active, next_pid, length, rng, config["primary_policy"],
            config["churn_probability"], alternating)
    return next_pid, alternating, sizes


def generate_one(config):
    rng = random.Random(config["seed"])
    excluded = set()
    t1 = profile_target(rng, config["phase1_profile"], excluded)
    excluded.add(t1)
    t2 = profile_target(rng, config["phase2_profile"], excluded)
    config = dict(config, phase1_target_length=t1, phase2_target_length=t2)
    commands, active, next_pid = [], [], 1
    alternating = config["seed"] & 1
    next_pid, alternating, prefix_sizes = append_mixed_prefix(
        config, rng, commands, active, next_pid, alternating)
    for _ in range(config["phase1_run_length"]):
        next_pid, alternating = append_placement(
            commands, active, next_pid, t1, rng, config["primary_policy"],
            config["churn_probability"], alternating)
    spacer_sizes = []
    prev_distinct = []
    for v in reversed(prefix_sizes):
        if not prev_distinct or v != prev_distinct[-1]:
            prev_distinct.append(v)
        if len(prev_distinct) == 2:
            break
    prev_distinct.reverse()
    for _ in range(config["spacer_placements"]):
        for _try in range(10000):
            length = pick_length(rng, config["phase2_profile"], {t1, t2})
            if spacer_sizes and length == spacer_sizes[-1]:
                continue
            recent = prev_distinct + spacer_sizes
            distinct = []
            for v in reversed(recent):
                if not distinct or v != distinct[-1]:
                    distinct.append(v)
                if len(distinct) == 2:
                    break
            if len(distinct) == 2 and is_arithmetic_triple(distinct[1], distinct[0], length):
                continue
            break
        else:
            raise RuntimeError("could not select spacer size")
        spacer_sizes.append(length)
        next_pid, alternating = append_placement(
            commands, active, next_pid, length, rng, config["phase2_policy"],
            config["churn_probability"], alternating)
    for _ in range(config["phase2_run_length"]):
        next_pid, alternating = append_placement(
            commands, active, next_pid, t2, rng, config["phase2_policy"],
            config["churn_probability"], alternating)
    tail_sizes = []
    for _ in range(config["tail_placements"]):
        length = pick_length(rng, config["phase2_profile"], {t1, t2})
        tail_sizes.append(length)
        next_pid, alternating = append_placement(
            commands, active, next_pid, length, rng, config["phase2_policy"],
            config["churn_probability"], alternating, allow_delete=False)
    commands.append(0)
    return commands, dict(config, prefix_size_blocks=prefix_sizes, spacer_sizes=spacer_sizes,
                          tail_sizes=tail_sizes)


def generate_all():
    prereg_path = ROOT / "PRE_REGISTRATION.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg["generator_sha256"] != sha256(__file__):
        raise SystemExit("generator hash differs from preregistration")
    if prereg["baseline_source_sha256"] != sha256(ROOT / "baseline.cpp"):
        raise SystemExit("baseline hash differs from preregistration")
    if prereg["candidate_source_sha256"] != sha256(ROOT / "candidate.cpp"):
        raise SystemExit("candidate hash differs from preregistration")
    if prereg["baseline_binary_sha256"] != sha256(ROOT / "baseline") or prereg["candidate_binary_sha256"] != sha256(ROOT / "candidate"):
        raise SystemExit("binary hash differs from preregistration")
    outdir = ROOT / "validation"
    outdir.mkdir(exist_ok=True)
    entries = []
    for original in prereg["design"]["streams"]:
        commands, config = generate_one(original)
        path = outdir / (original["case"] + ".in")
        path.write_text("1.0 %d\n" % (len(commands) - 1) + "\n".join(map(str, commands)) + "\n", encoding="ascii")
        entries.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path), **config,
                        "command_count": len(commands) - 1,
                        "placement_count": sum(x > 0 for x in commands),
                        "removal_count": sum(x < 0 for x in commands)})
    (outdir / "stream_manifest.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("generated", len(entries), "synthetic validation streams")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preregister", "generate"])
    parser.add_argument("--preregistration", type=Path, default=ROOT / "PRE_REGISTRATION.json")
    args = parser.parse_args()
    if args.action == "preregister":
        write_preregistration(args.preregistration)
    else:
        generate_all()
