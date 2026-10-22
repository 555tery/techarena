#!/usr/bin/env python3
"""Generate preregistered Pipes synthetic train/validation streams."""

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICIES = ["parity_even", "parity_odd", "random", "oldest", "newest", "alternating"]
RUN_LENGTHS = [32, 46, 48, 64, 96, 128]
PROFILES = ["uniform", "short-heavy", "long-heavy", "bimodal"]
PHASE_PLACEMENTS = 3000
CHURN_LEVELS = [0.40, 0.60, 0.75]
TRAIN_SEED_START = 910001
VALIDATION_SEED_START = 920001


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_length(rng, profile):
    if profile == "uniform":
        return rng.randint(1, 40)
    if profile == "short-heavy":
        pick = rng.random()
        if pick < 0.65:
            return rng.randint(1, 5)
        if pick < 0.90:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "long-heavy":
        pick = rng.random()
        if pick < 0.10:
            return rng.randint(1, 5)
        if pick < 0.35:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "bimodal":
        return rng.randint(1, 8) if rng.random() < 0.5 else rng.randint(32, 40)
    raise ValueError(profile)


def is_arithmetic_triple(values, candidate):
    return len(values) >= 2 and candidate - values[-1] == values[-1] - values[-2]


def phase_sizes(rng, placement_count, run_length, profile, prior_distinct):
    result = []
    remaining = placement_count
    previous = list(prior_distinct)
    while remaining:
        for _ in range(1000):
            length = sample_length(rng, profile)
            if previous and length == previous[-1]:
                continue
            if is_arithmetic_triple(previous, length):
                continue
            break
        else:
            raise RuntimeError("could not sample a non-trend block length")
        count = min(run_length, remaining)
        result.extend([length] * count)
        previous.append(length)
        if len(previous) > 2:
            previous.pop(0)
        remaining -= count
    return result, previous


def phase_two_policy(primary, run_index):
    if primary == "parity_even":
        return "random"
    if primary == "parity_odd":
        return "oldest"
    if primary == "random":
        return "parity_even" if run_index % 2 == 0 else "oldest"
    if primary == "oldest":
        return "parity_odd" if run_index % 2 == 1 else "newest"
    if primary == "newest":
        return "parity_even" if run_index % 2 == 1 else "random"
    return "parity_odd" if run_index % 2 == 1 else "random"


def config_for(split, index):
    if split == "train":
        policy_index = index // 2
        run_index = (1, 4)[index % 2]
        primary = POLICIES[policy_index]
        primary_run = RUN_LENGTHS[run_index]
        seed = TRAIN_SEED_START + index
    else:
        policy_index = index // len(RUN_LENGTHS)
        run_index = index % len(RUN_LENGTHS)
        primary = POLICIES[policy_index]
        primary_run = RUN_LENGTHS[run_index]
        seed = VALIDATION_SEED_START + index
    phase2_run_index = (run_index + 2) % len(RUN_LENGTHS)
    profile_index = (index + (0 if split == "train" else 1)) % len(PROFILES)
    return {
        "split": split,
        "seed": seed,
        "primary_policy": primary,
        "phase2_policy": phase_two_policy(primary, run_index),
        "phase1_run_length": primary_run,
        "phase2_run_length": RUN_LENGTHS[phase2_run_index],
        "phase1_profile": PROFILES[profile_index],
        "phase2_profile": PROFILES[(profile_index + 1) % len(PROFILES)],
        "phase1_churn": CHURN_LEVELS[index % len(CHURN_LEVELS)],
        "phase2_churn": CHURN_LEVELS[(index + 1) % len(CHURN_LEVELS)],
        "phase_placements": PHASE_PLACEMENTS,
    }


def design():
    train = [config_for("train", index) for index in range(12)]
    validation = [config_for("validation", index) for index in range(36)]
    return {"train": train, "validation": validation}


def make_preregistration():
    baseline = ROOT / "baseline.cpp"
    candidate = ROOT / "candidate.cpp"
    generator = Path(__file__).resolve()
    return {
        "experiment": "pid46_window_gate",
        "status": "preregistered_before_stream_generation",
        "candidate_rule": {
            "base": "Frozen c4 source, SHA-256 c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991",
            "run_threshold": 46,
            "gate": "During runLeftActive, use PID lanes iff the last min(64, removals_seen) valid removals contain at least 32 removals and one 1-based PID parity has at least 75 percent of that window.",
            "window": 64,
            "minimum_removals": 32,
            "dominance_fraction": "3/4, checked by integer arithmetic",
            "pid_lane_mapping": "Even placement PID goes to the high edge; odd placement PID goes to the low edge, matching the prior PID/46 preprobe.",
            "fallback": "Use frozen c4 sizeCohort lane while runLeftActive and gate is false; retain all other frozen c4 behavior.",
            "causality": "Only prior valid removal PID parities and the current placement history are consulted; no stream index or future command is read.",
            "rollout": "Mirror the same gate and simulated PID-parity window in the frozen Monte Carlo rollout state.",
        },
        "candidate_sha256": sha256(candidate),
        "baseline_sha256": sha256(baseline),
        "generator_sha256": sha256(generator),
        "design": {
            "synthetic_generator": "This local deterministic generator; Python random.Random(seed).",
            "phase_placements": PHASE_PLACEMENTS,
            "phase_change": "Each stream has two contiguous phases; policy, length profile, same-size run length, and churn change at the boundary.",
            "run_lengths": RUN_LENGTHS,
            "length_profiles": PROFILES,
            "deletion_policies": POLICIES,
            "churn_levels": CHURN_LEVELS,
            "train_stream_count": 12,
            "validation_stream_count": 36,
            "configurations": design(),
            "same_size_blocks": "Each phase is composed of exact same-size runs; adjacent block sizes differ, and three consecutive block sizes are rejected when arithmetic to avoid the frozen smooth-trend latch.",
            "deletion_timing": "After each placement, delete at the phase churn probability unless it is the final placement; the final command is always a placement.",
            "parity_deletion": "Choose uniformly from active PIDs of the selected parity; if none are active, choose uniformly from all active PIDs.",
            "alternating_deletion": "Alternate desired PID parity on each deletion; if absent, choose from active PIDs of the other parity.",
            "other_deletions": "random uniformly chooses active PID; oldest/newest choose minimum/maximum active PID.",
            "input_weight": 1.0,
            "validation_is_not_used_for_selection": True,
        },
        "analysis_plan": {
            "paired_unit": "one whole stream; baseline and candidate run on byte-identical inputs",
            "primary_metric": "per-stream KPI = final occupied length / trench length; report trench deltas too",
            "bootstrap": "20,000 whole-stream paired bootstrap resamples, percentile 95% CI, fixed analysis seed 930017",
            "validation_success_gate": [
                "All baseline and candidate transcripts pass the official local interactor.",
                "Validation overall mean paired KPI delta is at least +0.0001 and its percentile 95% CI lower endpoint is above zero.",
                "The parity-exposed validation subset (a stream with parity_even or parity_odd in either phase) has positive mean paired KPI delta and 95% CI lower endpoint above zero.",
                "The pure non-parity control subset has mean paired KPI delta at least zero.",
                "All CPU and RSS observations stay below 5 seconds and 256 MiB per stream.",
            ],
            "post_gate": "Run local Open15 and holdout-v2 only if every validation success condition passes; otherwise stop NO-GO.",
            "analysis_seed": 930017,
        },
    }


def delete_pid(rng, active, policy, alternating_parity):
    if policy == "random":
        return rng.choice(active), alternating_parity
    if policy == "oldest":
        return min(active), alternating_parity
    if policy == "newest":
        return max(active), alternating_parity
    if policy == "parity_even":
        wanted = 0
        candidates = [pid for pid in active if (pid & 1) == wanted]
        return rng.choice(candidates or active), alternating_parity
    if policy == "parity_odd":
        wanted = 1
        candidates = [pid for pid in active if (pid & 1) == wanted]
        return rng.choice(candidates or active), alternating_parity
    if policy == "alternating":
        wanted = alternating_parity
        candidates = [pid for pid in active if (pid & 1) == wanted]
        if not candidates:
            candidates = [pid for pid in active if (pid & 1) != wanted]
        return rng.choice(candidates or active), 1 - wanted
    raise ValueError(policy)


def generate_stream(config):
    rng = random.Random(config["seed"])
    commands = []
    active = []
    next_pid = 1
    previous_sizes = []
    alternating_parity = config["seed"] & 1
    phases = [
        (config["phase1_policy"] if "phase1_policy" in config else config["primary_policy"],
         config["phase1_profile"], config["phase1_run_length"], config["phase1_churn"]),
        (config["phase2_policy"], config["phase2_profile"], config["phase2_run_length"], config["phase2_churn"]),
    ]
    total_placements = config["phase_placements"] * len(phases)
    placements_done = 0
    for policy, profile, run_length, churn in phases:
        sizes, previous_sizes = phase_sizes(
            rng, config["phase_placements"], run_length, profile, previous_sizes
        )
        for length in sizes:
            pid = next_pid
            next_pid += 1
            active.append(pid)
            commands.append(length)
            placements_done += 1
            if placements_done < total_placements and rng.random() < churn:
                removed, alternating_parity = delete_pid(
                    rng, active, policy, alternating_parity
                )
                active.remove(removed)
                commands.append(-removed)
    commands.append(0)
    return commands


def write_preregistration(path):
    payload = make_preregistration()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote preregistration", path)


def generate_split(split, prereg_path):
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg["generator_sha256"] != sha256(__file__):
        raise SystemExit("generator hash differs from preregistration")
    if prereg["candidate_sha256"] != sha256(ROOT / "candidate.cpp"):
        raise SystemExit("candidate source hash differs from preregistration")
    configs = prereg["design"]["configurations"][split]
    out_dir = ROOT / split
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_manifest = []
    for config in configs:
        commands = generate_stream(config)
        path = out_dir / ("%s_%02d_%d.in" % (split, config["seed"] - (TRAIN_SEED_START if split == "train" else VALIDATION_SEED_START) + 1, config["seed"]))
        content = "1.0 %d\n" % (len(commands) - 1)
        content += "\n".join(str(value) for value in commands) + "\n"
        path.write_text(content, encoding="ascii")
        stream_manifest.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path), **config})
    (out_dir / "stream_manifest.json").write_text(
        json.dumps(stream_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("generated", len(stream_manifest), split, "streams under", out_dir)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-preregistration", action="store_true")
    group.add_argument("--generate", choices=("train", "validation"))
    parser.add_argument("--preregistration", default=str(ROOT / "PRE_REGISTRATION.json"))
    args = parser.parse_args()
    prereg_path = Path(args.preregistration)
    if args.write_preregistration:
        write_preregistration(prereg_path)
    else:
        generate_split(args.generate, prereg_path)


if __name__ == "__main__":
    main()
