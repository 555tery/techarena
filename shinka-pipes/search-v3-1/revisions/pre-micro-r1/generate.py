"""Prepare SEARCH-v3.1 inputs only. No solver, compiler, checker or model calls."""

from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

from characteristics import characterize, Fenwick
from support import ROOT, PARENT, digest, frozen_v2, verify_dependencies

V2 = frozen_v2("generate.py")
VERSION = "search-v3.1"
MAIN, STRESS = ROOT / "task/data/search", ROOT / "stress/data"
LEGACY = tuple(V2.SEARCH_FAMILIES)
NEW = ("recent_window_growth", "soft_recency_growth", "background_ephemeral", "isolated_recent_churn",
       "tiny_growth", "tiny_churn", "hotset_growth", "hotset_switching", "serial_growth", "serial_churn",
       "long_prefill_random", "long_prefill_recent", "drain_recovery", "partial_drain",
       "short_rounding", "short_phase_churn")
FAMILIES = LEGACY + NEW
MAX_ATTEMPTS = 32
MAIN_REPEATS, STRESS_REPEATS = 4, 2


def seed_for(role, family, variant, attempt=0):
    return int.from_bytes(hashlib.sha256(f"{VERSION}/{role}/{family}/{variant}/{attempt}".encode()).digest()[:8], "big")


def make_specs(role):
    if role not in {"search", "stress"}:
        raise ValueError("only search and diagnostic stress may be generated")
    old = {(s["family"], s["variant"]): s for s in V2.make_specs()}
    specs = []
    for family_index, family in enumerate(FAMILIES):
        for variant in range(MAIN_REPEATS if role == "search" else STRESS_REPEATS):
            rng = random.Random(seed_for(role, family, variant) ^ 0x31D3516)
            regime = "high" if variant < 3 else "moderate"
            if family == "partial_drain":
                regime = "moderate"
            if family in {"short_rounding", "short_phase_churn"}:
                regime = "rounding"
            if role == "stress":
                regime = "stress"
            spec = {"id": f"{'s31' if role == 'search' else 'x31'}_{len(specs)+1:03d}_{family}",
                    "family": family, "variant": variant, "role": role, "regime": regime,
                    "design_seed": seed_for(role, family, variant),
                    "mechanism_block": "broad_prior" if family in LEGACY else "expanded_mechanisms"}
            if family in LEGACY:
                legacy_variant = (2 * variant + family_index) % 8
                source = old[family, legacy_variant]
                spec.update(legacy_variant=legacy_variant, operation_budget=source["operations"],
                            legacy_parameters=copy.deepcopy(source))
            else:
                index = family_index - len(LEGACY)
                budget = (640, 4_096, 32_768, 131_072)[(variant + index) % 4]
                if family == "short_rounding":
                    budget = rng.randrange(8 * 4**variant, 32 * 4**variant)
                elif family == "short_phase_churn":
                    budget = rng.randrange(32 * 4**variant, 128 * 4**variant)
                target = min(max(4, budget // 8), 2 ** rng.randrange(3, 15))
                profile = ("uniform", "short", "serial", "drifting")[(variant + index) % 4]
                if family.startswith("tiny_"):
                    profile = "tiny"
                elif family.startswith("hotset_"):
                    profile = "sparse"
                elif family.startswith("serial_"):
                    profile = "serial"
                elif family == "short_rounding":
                    profile = ("tiny", "boundary", "sparse", "uniform")[variant]
                params = {"profile": profile, "target_live": target,
                          "delete_probability": (0.08, 0.21, 0.35, 0.46)[(variant + index) % 4],
                          "recent_fraction": (0.01, 0.04, 0.16, 0.50)[variant],
                          "recency_power": (2, 4, 8, 16)[variant], "exclude_newest": variant % 2 == 1,
                          "background_probability": (0.15, 0.30, 0.45, 0.60)[variant],
                          "tiny_probability": rng.uniform(.82, .99), "one_probability": rng.uniform(.55, .97),
                          "hot_class_probability": rng.uniform(.45, .95), "class_count": rng.randrange(2, 8),
                          "run_length": 2 ** rng.randrange(2, 13), "phase_count": rng.randrange(3, 10),
                          "prefill_fraction": (0.35, 0.50, 0.65, 0.80)[variant],
                          "recovery_drain_fraction": rng.uniform(.30, .70),
                          "policy": ("random", "recent", "soft", "recent")[(variant + index) % 4]}
                if family == "recent_window_growth": params["policy"] = "recent"
                if family in {"soft_recency_growth", "background_ephemeral", "isolated_recent_churn"}: params["policy"] = "soft"
                if family == "long_prefill_random": params["policy"] = "random"
                if family == "long_prefill_recent": params["policy"] = "recent"
                if family == "tiny_growth": params["delete_probability"] = rng.uniform(.01, .08)
                if family in {"tiny_churn", "serial_churn", "hotset_switching"}: params["delete_probability"] = rng.uniform(.42, .49)
                spec.update(operation_budget=budget, parameters=params)
            if role == "stress":
                spec["operation_budget"] = max(512, min(131_072, spec["operation_budget"]))
            specs.append(spec)
    return specs


def select_prefix(commands, min_fraction=.75):
    live, pid, volume, peak, deletes, endpoint = {}, 0, 0, 0, 0, None
    for index, command in enumerate(commands, 1):
        if command > 0:
            pid += 1
            live[pid] = command
            volume += command
            peak = max(peak, volume)
        else:
            volume -= live.pop(-command)
            deletes += 1
        bound = 20 * ((peak + 19) // 20)
        if index >= math.ceil(len(commands) * min_fraction) and volume >= .95 * bound and deletes >= 1:
            endpoint = index
    return endpoint


def legacy_source(spec, seed, count):
    source = copy.deepcopy(spec["legacy_parameters"])
    source.update(seed=seed, operations=count)
    rng = random.Random(seed ^ 0xB31)
    source["parameters"]["phase_offset"] = rng.randrange(max(40, 4 * source["parameters"]["phase_length"]))
    if source["family"] != "large_live_set":
        source["target_live"] = min(source["target_live"], max(8, count // 12))
        source["deletion_probability"] = (.10, .18, .26, .34, .40, .44, .47, .49)[source["variant"]]
    if source["family"] != "distribution_switch":
        return V2.generate(source)
    # Ordinary phased churn, without the v2 oversized startup target.
    rng = random.Random(seed)
    stream, p = V2.Stream(count, rng), source["parameters"]
    while len(stream.commands) < count:
        step = len(stream.commands)
        phase = (step + p["phase_offset"]) // p["phase_length"]
        profile = ("short", "long", "bimodal", "uniform")[(phase + source["variant"]) % 4]
        target = max(8, int(source["target_live"] * (.25, 1.8, .65, 1.25)[phase % 4]))
        if stream.live and (len(stream.live) > target or rng.random() < source["deletion_probability"]):
            stream.delete(stream.choose("random"))
        else:
            stream.insert(V2.sample_length(rng, profile, step, source))
    return stream.commands


def kth_active(tree, order):
    """One-based live rank -> PID, without scanning a growing live set."""
    index, bit = 0, 1 << (tree.n.bit_length() - 1)
    while bit:
        candidate = index + bit
        if candidate <= tree.n and tree.tree[candidate] < order:
            order -= tree.tree[candidate]
            index = candidate
        bit >>= 1
    return index + 1


def expanded_source(spec, seed, count):
    rng, p, family = random.Random(seed), spec["parameters"], spec["family"]
    stream, tree, transient = V2.Stream(count, rng), Fenwick(count), set()
    eligible = 0
    classes = rng.sample(range(1, 41), p["class_count"])
    hot = rng.randrange(len(classes))
    weights = [rng.gammavariate(.6, 1) for _ in classes]
    center, remaining, current_size, last_phase = rng.randrange(1, 41), 0, 1, -1
    prefill = int(count * p["prefill_fraction"]) if family.startswith("long_prefill_") else 0
    target = max(prefill + 1, p["target_live"])
    stationary = family in {"tiny_churn", "serial_churn", "hotset_switching", "long_prefill_random", "short_phase_churn"}
    isolated = family in {"isolated_recent_churn", "tiny_growth", "short_phase_churn"}
    background = p["background_probability"] if family in {"background_ephemeral", "isolated_recent_churn"} else 0.
    recovery_done = False

    def choose(policy):
        if policy == "recent":
            window = max(2, math.ceil(eligible * p["recent_fraction"]))
            offset = rng.randrange(min(window, eligible))
        elif policy == "soft":
            offset = min(eligible - 1, int((rng.random() ** p["recency_power"]) * eligible))
        else:
            offset = rng.randrange(eligible)
        if policy != "random" and p["exclude_newest"] and eligible > 1:
            offset = max(1, offset)
        return kth_active(tree, eligible - offset)

    def remove(pid):
        nonlocal eligible
        stream.delete(pid)
        transient.remove(pid)
        tree.add(pid, -1)
        eligible -= 1

    while len(stream.commands) < count:
        step = len(stream.commands)
        phase = step * p["phase_count"] // count
        if family == "hotset_switching" and phase != last_phase:
            classes = rng.sample(range(1, 41), p["class_count"])
            hot = rng.randrange(len(classes))
            weights = [rng.gammavariate(.6, 1) for _ in classes]
        last_phase = phase
        if family == "drain_recovery" and step >= count // 2 and not recovery_done:
            target_volume = stream.volume * p["recovery_drain_fraction"]
            while len(stream.commands) < count and len(stream.live) > 1 and eligible and stream.volume > target_volume:
                remove(choose("random"))
            recovery_done = True
            continue
        deletion = (step >= prefill and eligible > 0 and len(stream.live) > 1
                    and ((stationary and len(stream.live) > target) or rng.random() < p["delete_probability"]))
        if isolated and stream.commands and stream.commands[-1] < 0:
            deletion = False
        if family.startswith("short_") and step == count // 2 and not any(x < 0 for x in stream.commands):
            deletion = eligible > 0 and len(stream.live) > 1
        if deletion:
            remove(choose(p["policy"]))
            continue
        profile = p["profile"]
        if profile == "tiny":
            size = (1 if rng.random() < p["one_probability"] else 2) if rng.random() < p["tiny_probability"] else rng.randrange(3, 41)
        elif profile == "sparse":
            size = classes[hot] if rng.random() < p["hot_class_probability"] else rng.choices(classes, weights=weights)[0]
        elif profile == "serial":
            if remaining <= 0:
                current_size, remaining = rng.randrange(1, 41), p["run_length"]
            size, remaining = current_size, remaining - 1
        elif profile == "drifting":
            center = max(1, min(40, center + rng.choice((-1, 0, 0, 1))))
            size = max(1, min(40, center + rng.choice((-1, 0, 1))))
        elif profile == "short":
            size = rng.randrange(1, 9) if rng.random() < .85 else rng.randrange(9, 41)
        elif profile == "boundary":
            size = rng.choice((1, 2, 19, 20, 21, 39, 40))
        else:
            size = rng.randrange(1, 41)
        pid = stream.insert(size)
        if rng.random() >= background:
            transient.add(pid)
            tree.add(pid, 1)
            eligible += 1
    return stream.commands


def drain(commands, seed, regime, variant):
    rng, live, pid, volume, peak = random.Random(seed ^ 0xD3A1), {}, 0, 0, 0
    for c in commands:
        if c > 0:
            pid += 1
            live[pid] = c
            volume += c
            peak = max(peak, volume)
        else:
            volume -= live.pop(-c)
    bound = 20 * ((peak + 19) // 20)
    requested = (.05, .25)[variant % 2] if regime == "stress" else rng.uniform(.64, .90)
    lower = 1 if regime == "stress" else math.ceil(.60 * bound)
    victims = list(live)
    rng.shuffle(victims)
    extra = []
    for victim in victims:
        if volume <= requested * bound or len(live) <= 1:
            break
        if volume - live[victim] >= lower:
            volume -= live.pop(victim)
            extra.append(-victim)
    return commands + extra, {"policy": "predeclared randomized terminal drain", "requested_final_to_bound": requested,
                              "appended_deletions": len(extra), "appended_insertions": 0}


def generate_case(spec):
    for attempt in range(MAX_ATTEMPTS):
        seed = seed_for(spec["role"], spec["family"], spec["variant"], attempt)
        terminal = spec["regime"] in {"moderate", "stress"}
        source_count = spec["operation_budget"] // 2 if terminal else spec["operation_budget"]
        source = legacy_source(spec, seed, source_count) if spec["family"] in LEGACY else expanded_source(spec, seed, source_count)
        if spec["regime"] in {"high", "moderate"}:
            end = select_prefix(source)
            if end is None:
                continue
        else:
            end = len(source)
        commands = source[:end]
        termination = {"policy": "natural prefix in final quarter" if end != len(source) else "declared source horizon",
                       "source_operations": source_count, "discarded_suffix_operations": len(source) - end,
                       "appended_insertions": 0, "appended_deletions": 0}
        if terminal:
            commands, tail = drain(commands, seed, spec["regime"], spec["variant"])
            termination.update(tail)
        stats = V2.audit_commands(commands)
        alpha = stats["final_live_volume"] / stats["volume_lower_bound"]
        if (spec["regime"] == "high" and alpha < .95
                or spec["regime"] == "moderate" and not .60 <= alpha < .95
                or spec["regime"] == "stress" and alpha > .30):
            continue
        if len(commands) > spec["operation_budget"]:
            raise ValueError("drain exceeded predeclared operation budget")
        features = characterize(commands)["features"]
        actual = {**spec, "seed": seed, "generator_attempt": attempt, "operations": len(commands),
                  "termination": termination, "final_to_bound": alpha, "features": features}
        return commands, actual, stats
    raise ValueError(f"input-only conditioning exhausted: {spec['id']}")


def overview(cases):
    f = [c["features"] for c in cases]
    return {"cases": len(cases), "families": len({c["family"] for c in cases}),
            "operations": sum(c["operations"] for c in cases),
            "operation_range": [min(c["operations"] for c in cases), max(c["operations"] for c in cases)],
            "family_counts": dict(sorted(Counter(c["family"] for c in cases).items())),
            "design_regime_counts": dict(Counter(c["regime"] for c in cases)),
            "mechanism_block_counts": dict(Counter(c["mechanism_block"] for c in cases)),
            "actual_high_final_cases": sum(x["final_to_bound"] >= .95 for x in f),
            "actual_intermediate_final_cases": sum(.30 <= x["final_to_bound"] < .95 for x in f),
            "short_under_2000": sum(x["operations"] < 2000 for x in f),
            "tiny_dominant_cases": sum(x["share_length_le2"] >= .8 for x in f),
            "rare_deletion_cases": sum(x["delete_fraction"] < .05 for x in f),
            "isolated_deletion_cases": sum(x["delete_run_max"] == 1 for x in f),
            "soft_recency_cases": sum(x["deletion_age_rank_mean"] is not None and x["deletion_age_rank_mean"] >= .9 and x["lifo_deletion_fraction"] < .3 for x in f),
            "soft_recency_positive_serial_cases": sum(x["deletion_age_rank_mean"] is not None and x["deletion_age_rank_mean"] >= .9 and x["lifo_deletion_fraction"] < .3 and x["size_lag1_correlation"] is not None and x["size_lag1_correlation"] > .1 for x in f),
            "long_initial_fill_cases": sum(x["initial_insert_run_over_n"] >= .35 for x in f),
            "mean_time_above_90pct_peak": statistics.mean(x["time_above_90pct_peak"] for x in f),
            "max_peak_live_count": max(x["peak_live_count"] for x in f),
            "max_generator_attempt": max(c["generator_attempt"] for c in cases)}


def prepare():
    for path in (MAIN, STRESS, ROOT / "protocol.json", ROOT / "preparation.json"):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite prepared artifacts: {path}")
    verify_dependencies(include_active=True)
    previous = [json.loads((PARENT / name).read_text()) for name in (
        "task-synthetic/data/search/manifest.json", "search-v2/task/data/search/manifest.json",
        "search-v3/task/data/search/manifest.json", "search-v3/stress/data/manifest.json")]
    seen_hashes = {c["sha256"] for m in previous for c in m["cases"]}
    seen_seeds = {c["seed"] for m in previous for c in m["cases"]}
    parser, manifests, report = V2.parser_module(), {}, {}
    stage = ROOT / "preparation-staging" / digest(Path(__file__))[:16]
    stage.mkdir(parents=True, exist_ok=False)
    for role, destination in (("search", stage / "search"), ("stress", stage / "stress")):
        destination.mkdir(parents=True)
        cases = []
        for spec in make_specs(role):
            commands, actual, stats = generate_case(spec)
            path = destination / (spec["id"] + ".in")
            path.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
            sha = digest(path)
            if sha in seen_hashes or actual["seed"] in seen_seeds:
                raise ValueError("duplicate input/seed, including previous SEARCH versions")
            seen_hashes.add(sha)
            seen_seeds.add(actual["seed"])
            parsed = parser.parse_test(path)
            expected = {"operation_count": len(commands), "weight": 1., "test_sha256": sha,
                        "peak_live_pipe_length_m": stats["peak_live_volume"], "final_occupied_length_m": stats["final_live_volume"],
                        "minimum_trench_lower_bound_m": stats["volume_lower_bound"]}
            if any(parsed[k] != v for k, v in expected.items()):
                raise ValueError(f"independent parser disagreement: {path.name}")
            cases.append({**actual, "file": path.name, "sha256": sha, "stats": stats})
        manifest = {"version": VERSION, "split": role, "role": "fitness" if role == "search" else "diagnostic_only",
                    "case_count": len(cases), "families": list(FAMILIES), "cases_per_family": MAIN_REPEATS if role == "search" else STRESS_REPEATS,
                    "weight_per_case": 1, "generator_sha256": digest(Path(__file__)), "characteristics_sha256": digest(ROOT / "characteristics.py"),
                    "python_version": sys.version.split()[0], "fitness": "mean_over_families(mean_over_cases(F/T))" if role == "search" else None,
                    "independent_holdout": False, "candidate_results_used_to_select_inputs": False,
                    "open15_raw_inputs_read_during_generation": False, "open15_histograms_weights_or_sequences_copied": False,
                    "design_basis": "broad prior plus generic mechanisms suggested by earlier input audit; NOT an independent distributional validation",
                    "cases": cases}
        path = destination / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
        manifests[role] = digest(path)
        report[role] = {**overview(cases), "manifest_sha256": manifests[role]}
        print(f"prepared {role}: {len(cases)} streams", flush=True)
    for role, destination in (("search", MAIN), ("stress", STRESS)):
        destination.parent.mkdir(parents=True, exist_ok=True)
        (stage / role).rename(destination)
    protocol = {"version": VERSION, "status": "prepared_not_run", "manifest_sha256": manifests,
                "metric": "family-balanced arithmetic mean F/T", "family_weights": "1/32", "case_weights": "1/4 within family",
                "case_count": 128, "family_count": 32, "cases_per_family": 4,
                "design_policy": "50% broad prior, 50% expanded mechanisms; no empirical Open15 frequency matching",
                "planned_main_regimes": dict(Counter(s["regime"] for s in make_specs("search"))),
                "high_final_floor": .95, "moderate_final_band": [.60, .95], "stress_final_ceiling": .30,
                "max_input_generation_attempts": MAX_ATTEMPTS, "cpu_limit_seconds": 5, "rss_limit_mib": 256,
                "native_workers": 2, "evaluation_route": "only task/data/search; no selectable split",
                "stress_in_fitness": False, "stress_in_selection": False, "stress_in_feedback": False,
                "stress_runs_automatically": False, "validation_files_accessed": False, "open15_files_read": False,
                "baseline_source": None, "baseline_evaluated": False, "authorized_generations": None,
                "source_guard_sha256": digest(ROOT / "source-guard.json")}
    (ROOT / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    report.update(version=VERSION, status="prepared_not_run", solvers_executed=0, interactor_runs=0, compiler_runs=0, model_requests=0,
                  independent_parser_cases=192, previous_search_overlap=0, validation_files_accessed=False, open15_files_read=False,
                  generator_sha256=digest(Path(__file__)), protocol_sha256=digest(ROOT / "protocol.json"))
    (ROOT / "preparation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
