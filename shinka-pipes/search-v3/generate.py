"""Prepare fresh candidate-independent inputs, never solvers, compilers or LLMs."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

from support import ROOT, PARENT, digest, frozen_v2, verify_dependencies

V2 = frozen_v2("generate.py")
VERSION = "search-v3"
MAIN = ROOT / "task/data/search"
STRESS = ROOT / "stress/data"
MAIN_REPEATS, STRESS_REPEATS = 8, 2
MIN_FINAL_BOUND_RATIO = 0.95
MIN_PREFIX_FRACTION = 0.75
MIN_DELETE_FRACTION = 0.05
MAX_ATTEMPTS = 32
MAIN_DELETE_PROB = (0.10, 0.18, 0.26, 0.34, 0.40, 0.44, 0.47, 0.49)


def seed_for(role, family, variant, attempt=0):
    text = f"{VERSION}/{role}/{family}/{variant}/{attempt}"
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def make_specs(role):
    if role not in {"search", "stress"}:
        raise ValueError("only search and stress are supported")
    specs = []
    for original in V2.make_specs():
        if role == "stress" and original["variant"] not in {3, 7}:
            continue
        spec = {**original, "parameters": dict(original["parameters"])}
        variant = spec["variant"] if role == "search" else (0 if spec["variant"] == 3 else 1)
        spec.update(id=f"{'s3' if role == 'search' else 'x3'}_{len(specs)+1:03d}_{spec['family']}",
                    role=role, variant=original["variant"], stress_variant=variant if role == "stress" else None,
                    design_seed=seed_for(role, spec["family"], variant),
                    source_operations=spec["operations"])
        family_index = V2.SEARCH_FAMILIES.index(spec["family"])
        if spec["family"] != "large_live_set":
            # Enough cycles and deletions even for short horizons and big cohorts.
            spec["target_live"] = min(spec["target_live"], spec["operations"] // 12)
            spec["deletion_probability"] = MAIN_DELETE_PROB[(variant * 5 + family_index) % 8]
        if role == "stress":
            # Reserve room for the declared drain; it never adds a filling tail.
            spec["source_operations"] = max(2_000, spec["operations"] * 3 // 4)
            spec["operations"] = spec["source_operations"]
            spec["target_live"] = min(spec["target_live"], spec["operations"] // 12)
        specs.append(spec)
    return specs


def select_prefix(commands):
    """Latest natural endpoint in the last quarter, with high load and real churn."""
    live, next_pid, volume, peak, deletes, endpoint = {}, 1, 0, 0, 0, None
    start = math.ceil(len(commands) * MIN_PREFIX_FRACTION)
    for index, command in enumerate(commands, 1):
        if command > 0:
            live[next_pid] = command
            next_pid += 1
            volume += command
            peak = max(peak, volume)
        else:
            volume -= live.pop(-command)
            deletes += 1
        bound = 20 * ((peak + 19) // 20)
        if (index >= start and volume >= MIN_FINAL_BOUND_RATIO * bound
                and deletes >= max(64, math.ceil(index * MIN_DELETE_FRACTION))):
            endpoint = index
    return endpoint


def generate_source(spec):
    if spec["family"] != "distribution_switch":
        return V2.generate(spec)
    # The v2 warmup fills the unscaled target even during a low-target phase.
    # Avoid that startup-only peak here: start ordinary phased churn immediately.
    rng = random.Random(spec["seed"])
    stream = V2.Stream(spec["operations"], rng)
    p = spec["parameters"]
    while len(stream.commands) < stream.limit:
        step = len(stream.commands)
        phase = (step + p["phase_offset"]) // p["phase_length"]
        profile = ("short", "long", "bimodal", "uniform")[(phase + spec["variant"]) % 4]
        target = max(8, int(spec["target_live"] * (0.25, 1.8, 0.65, 1.25)[phase % 4]))
        if stream.live and (len(stream.live) > target or rng.random() < spec["deletion_probability"]):
            stream.delete(stream.choose("random"))
        else:
            stream.insert(V2.sample_length(rng, profile, step, spec))
    return stream.commands


def generate_case(spec):
    role = spec["role"]
    for attempt in range(MAX_ATTEMPTS if role == "search" else 1):
        actual = {**spec, "parameters": dict(spec["parameters"])}
        variant = spec["variant"] if role == "search" else spec["stress_variant"]
        actual["seed"] = seed_for(role, spec["family"], variant, attempt)
        rng = random.Random(actual["seed"] ^ 0x53A3)
        # Rotate phase origins independently of allocator behavior, including
        # long monotone additive/geometric cycles. Directions stay stratified.
        actual["parameters"]["phase_offset"] = rng.randrange(max(40, 4 * actual["parameters"]["phase_length"]))
        commands = generate_source(actual)
        if role == "search":
            endpoint = select_prefix(commands)
            if endpoint is None:
                continue
            commands = commands[:endpoint]
            termination = {"policy": "latest qualifying natural prefix in final quarter",
                           "generated_operations": spec["source_operations"],
                           "discarded_suffix_operations": spec["source_operations"] - endpoint,
                           "appended_operations": 0}
        else:
            live, next_pid = {}, 1
            for command in commands:
                if command > 0:
                    live[next_pid] = command
                    next_pid += 1
                else:
                    del live[-command]
            stats = V2.audit_commands(commands)
            fraction = (0.05, 0.25)[spec["stress_variant"]]
            target_volume = max(1, int(stats["volume_lower_bound"] * fraction))
            victims = list(live)
            rng.shuffle(victims)
            volume, drain = stats["final_live_volume"], 0
            for pid in victims:
                if volume <= target_volume or len(live) <= 1:
                    break
                volume -= live.pop(pid)
                commands.append(-pid)
                drain += 1
            termination = {"policy": "declared randomized drain, retain at least one live pipe",
                           "target_final_bound_ratio": fraction,
                           "generated_operations": spec["source_operations"],
                           "appended_deletions": drain, "appended_insertions": 0}
        stats = V2.audit_commands(commands)
        alpha = stats["final_live_volume"] / stats["volume_lower_bound"]
        if role == "search" and alpha < MIN_FINAL_BOUND_RATIO:
            raise ValueError("main stream below predeclared occupancy floor")
        if role == "stress" and alpha > 0.30:
            raise ValueError("stress stream failed low-final-load design")
        actual.update(operations=len(commands), generator_attempt=attempt,
                      termination=termination, final_to_bound=alpha,
                      final_to_peak=stats["final_live_volume"] / stats["peak_live_volume"])
        return commands, actual, stats
    raise ValueError(f"no qualifying natural endpoint after {MAX_ATTEMPTS} attempts: {spec['id']}")


def overview(cases):
    ratios = [c["final_to_bound"] for c in cases]
    return {"cases": len(cases), "families": len({c["family"] for c in cases}),
            "operations": sum(c["operations"] for c in cases),
            "operation_range": [min(c["operations"] for c in cases), max(c["operations"] for c in cases)],
            "final_to_bound": {"min": min(ratios), "median": statistics.median(ratios),
                               "mean": statistics.mean(ratios), "max": max(ratios)},
            "final_to_peak_min": min(c["final_to_peak"] for c in cases),
            "minimum_deletion_fraction": min(c["stats"]["deletions"] / c["operations"] for c in cases),
            "max_generator_attempt": max(c["generator_attempt"] for c in cases),
            "family_counts": dict(sorted(Counter(c["family"] for c in cases).items()))}


def prepare():
    for path in (MAIN, STRESS, ROOT / "protocol.json", ROOT / "preparation.json"):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite: {path}")
    verify_dependencies(include_active=True)
    old = [json.loads((PARENT / name).read_text()) for name in
           ("task-synthetic/data/search/manifest.json", "search-v2/task/data/search/manifest.json")]
    seen_hashes = {c["sha256"] for m in old for c in m["cases"]}
    seen_seeds = {c["seed"] for m in old for c in m["cases"]}
    parser, manifests, report = V2.parser_module(), {}, {}
    for role, destination in (("search", MAIN), ("stress", STRESS)):
        destination.mkdir(parents=True)
        cases = []
        for spec in make_specs(role):
            commands, actual, stats = generate_case(spec)
            file = destination / (actual["id"] + ".in")
            file.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
            sha = digest(file)
            if sha in seen_hashes or actual["seed"] in seen_seeds:
                raise ValueError("duplicate content or seed, including earlier SEARCH corpora")
            seen_hashes.add(sha)
            seen_seeds.add(actual["seed"])
            parsed = parser.parse_test(file)
            for key, value in (("operation_count", len(commands)), ("weight", 1.0), ("test_sha256", sha),
                               ("peak_live_pipe_length_m", stats["peak_live_volume"]),
                               ("final_occupied_length_m", stats["final_live_volume"]),
                               ("minimum_trench_lower_bound_m", stats["volume_lower_bound"])):
                if parsed[key] != value:
                    raise ValueError(f"independent parser disagrees: {file.name}: {key}")
            cases.append({**actual, "file": file.name, "sha256": sha, "stats": stats})
        manifest = {"version": VERSION, "split": role, "role": "fitness" if role == "search" else "diagnostic_only",
                    "case_count": len(cases), "families": list(V2.SEARCH_FAMILIES),
                    "cases_per_family": MAIN_REPEATS if role == "search" else STRESS_REPEATS,
                    "weight_per_case": 1, "generator_sha256": digest(Path(__file__)),
                    "primitive_generator_sha256": digest(PARENT / "generate_synthetic.py"),
                    "family_generator_sha256": digest(PARENT / "search-v2/generate.py"),
                    "python_version": sys.version.split()[0],
                    "fitness": "mean_over_families(mean_over_cases(F/T))" if role == "search" else None,
                    "candidate_results_used_to_select_inputs": False,
                    "independent_holdout": False, "held_out_mechanisms": [],
                    "design_basis": "predeclared input-only conditioning; earlier SEARCH outcomes are known",
                    "cases": cases}
        path = destination / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
        manifests[role] = digest(path)
        report[role] = {**overview(cases), "manifest_sha256": manifests[role]}
        print(f"prepared {role}: {len(cases)} streams", flush=True)
    protocol = {"version": VERSION, "status": "prepared_not_run", "manifest_sha256": manifests,
                "metric": "family-balanced arithmetic mean F/T", "family_weights": "1/16", "case_weights": "1/8 within family",
                "minimum_main_final_to_bound": MIN_FINAL_BOUND_RATIO,
                "minimum_prefix_fraction": MIN_PREFIX_FRACTION, "minimum_main_deletion_fraction": MIN_DELETE_FRACTION,
                "max_input_generation_attempts": MAX_ATTEMPTS, "cpu_limit_seconds": 5, "rss_limit_mib": 256,
                "native_workers": 2, "evaluation_route": "only task/data/search; no selectable split",
                "stress_in_fitness": False, "stress_in_selection": False, "stress_in_feedback": False,
                "stress_runs_automatically": False, "heldout_files_accessed": False,
                "baseline_source": None, "baseline_evaluated": False, "authorized_generations": None,
                "source_guard_sha256": digest(ROOT / "source-guard.json")}
    (ROOT / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    report.update(version=VERSION, solvers_executed=0, interactor_runs=0, compiler_runs=0, model_requests=0,
                  independent_parser_cases=160, previous_search_overlap=0, heldout_files_accessed=False,
                  generator_sha256=digest(Path(__file__)), protocol_sha256=digest(ROOT / "protocol.json"))
    (ROOT / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
