"""Prepare only SEARCH-v2 inputs. Never execute a candidate, interactor or LLM."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import heapq
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
sys.path.insert(0, str(PARENT))
from generate_synthetic import SEARCH_FAMILIES, Stream, audit_commands

VERSION = "search-v2"
DATA = ROOT / "task/data/search"
REPEATS = 8
OPERATIONS = (8_000, 16_000, 32_000, 50_000, 80_000, 110_000, 150_000, 200_000)
TARGETS = (24, 64, 192, 512, 1_536, 4_096, 8_192, 16_384)
DELETE_PROB = (0.10, 0.22, 0.34, 0.43, 0.49, 0.56, 0.68, 0.82)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_specs() -> list[dict]:
    specs = []
    for family_index, family in enumerate(SEARCH_FAMILIES):
        for variant in range(REPEATS):
            seed = int.from_bytes(hashlib.sha256(
                f"{VERSION}/search/{family}/{variant}".encode()).digest()[:8], "big")
            slot = (variant + family_index) % REPEATS
            params = {
                "short_max": (3, 5, 8, 4, 6, 2, 7, 5)[variant],
                "long_min": (24, 29, 33, 36, 27, 31, 35, 30)[variant],
                "hot_probability": (0.65, 0.75, 0.85, 0.95, 0.70, 0.80, 0.90, 0.97)[variant],
                "small_mixture": (0.20, 0.35, 0.50, 0.65, 0.80, 0.45, 0.60, 0.30)[variant],
                "phase_length": (127, 509, 1_021, 2_039, 4_093, 8_191, 997, 3_001)[variant],
                "phase_offset": (variant * 211) % 997,
                "run_length": (17, 43, 97, 211, 503, 887, 1_531, 4_093)[variant],
                "run_direction": 1 if variant % 2 == 0 else -1,
                "run_stride": (1, 1, 3, 1, 7, 3, 1, 9)[variant],
                "drift_radius": (1, 2, 3, 5, 8, 2, 4, 6)[variant],
                "drift_step": (1, 1, 2, 2, 3, 1, 3, 2)[variant],
                "drift_move_probability": (0.05, 0.15, 0.35, 0.65, 0.90, 0.25, 0.50, 0.80)[variant],
                "burst_scale": (0.35, 0.50, 0.75, 1.0, 1.5, 2.0, 0.65, 1.25)[variant],
                "drain_fraction": (0.35, 0.55, 0.75, 0.95, 0.45, 0.65, 0.85, 0.98)[variant],
                "stripe_period": (2, 3, 4, 5, 7, 3, 5, 9)[variant],
                "lifetime_relation": ("positive", "negative", "alternating", "positive",
                                      "negative", "alternating", "positive", "negative")[variant],
                "lifetime_scale": (0.25, 0.5, 1.0, 2.0, 0.75, 1.5, 3.0, 0.4)[variant],
                "base_profile": ("uniform", "bimodal", "boundary", "short",
                                 "long", "uniform", "boundary", "bimodal")[variant],
            }
            operations = OPERATIONS[slot]
            target = TARGETS[(variant * 3 + family_index) % REPEATS]
            deletion_probability = DELETE_PROB[(variant * 5 + family_index) % REPEATS]
            if family == "large_live_set":
                operations = (80_000, 100_000, 120_000, 140_000, 160_000, 180_000, 200_000, 200_000)[variant]
                target = (2_048, 4_096, 8_192, 12_000, 16_384, 24_000, 32_768, 45_000)[variant]
                deletion_probability = (0.02, 0.04, 0.07, 0.10, 0.14, 0.18, 0.23, 0.28)[variant]
            specs.append({"id": f"s2_{len(specs)+1:03d}_{family}", "family": family,
                          "variant": variant, "seed": seed, "operations": operations,
                          "target_live": target, "deletion_probability": deletion_probability,
                          "parameters": params})
    return specs


def sample_length(rng: random.Random, profile: str, step: int, spec: dict) -> int:
    p, variant = spec["parameters"], spec["variant"]
    if profile == "short":
        top = p["short_max"]
        return rng.randint(1, top) if rng.random() < p["hot_probability"] else rng.randint(top+1, 40)
    if profile == "long":
        low = p["long_min"]
        return rng.randint(low, 40) if rng.random() < p["hot_probability"] else rng.randint(1, low-1)
    if profile == "bimodal":
        return rng.randint(1, p["short_max"]) if rng.random() < p["small_mixture"] else rng.randint(p["long_min"], 40)
    if profile == "boundary":
        sets = ((19, 20, 21), (1, 19, 20, 39, 40), (2, 18, 22, 38),
                (1, 2, 20, 21, 40), (18, 19, 21, 22, 39, 40),
                (1, 20, 40), (2, 19, 21, 38, 40), (1, 18, 20, 22, 39))
        return rng.choice(sets[variant])
    if profile == "geometric":
        sizes = ((1, 2, 4, 8, 16, 32), (1, 2, 3, 5, 8, 13, 21, 34),
                 (2, 3, 5, 9, 17, 33), (1, 3, 7, 15, 31))[variant % 4]
        index = (step // p["run_length"] + p["phase_offset"]) * p["run_direction"]
        return sizes[index % len(sizes)]
    if profile == "additive":
        index = (step // p["run_length"]) * p["run_stride"] * p["run_direction"]
        return 1 + (index + p["phase_offset"]) % 40
    return rng.randint(1, 40)


def generate(spec: dict) -> list[int]:
    rng = random.Random(spec["seed"])
    stream = Stream(spec["operations"], rng)
    family, target, p = spec["family"], spec["target_live"], spec["parameters"]
    profile = {"short_heavy": "short", "long_heavy": "long", "bimodal": "bimodal",
               "section_boundaries": "boundary", "geometric_cohorts": "geometric",
               "additive_cohorts": "additive"}.get(family, p["base_profile"])
    if family in {"uniform_churn", "large_live_set"}:
        profile = "uniform"

    if family == "size_lifetimes":
        due: list[tuple[int, int]] = []
        clock = 0
        while len(stream.commands) < stream.limit:
            clock += 1
            if due and due[0][0] <= clock:
                _, pid = heapq.heappop(due)
                stream.delete(pid)
                continue
            length = sample_length(rng, p["base_profile"], clock, spec)
            pid = stream.insert(length)
            positive = p["lifetime_relation"] == "positive"
            if p["lifetime_relation"] == "alternating":
                positive = ((clock + p["phase_offset"]) // p["phase_length"]) % 2 == 1
            multiplier = length if positive else 41 - length
            mean = max(1.0, target * multiplier / 20 * p["lifetime_scale"])
            lifetime = min(max(2, 8 * target), max(1, int(rng.expovariate(1 / mean))))
            heapq.heappush(due, (clock + lifetime, pid))
    elif family in {"burst_drain", "striped_recycling"}:
        wave = 0
        while len(stream.commands) < stream.limit:
            cohort = []
            batch = max(4, int(target * p["burst_scale"] * rng.uniform(0.7, 1.3)))
            batch = min(batch, stream.limit-len(stream.commands))
            for index in range(batch):
                current_profile = ("short" if (index+wave) % 2 else "long") if family == "striped_recycling" else p["base_profile"]
                pid = stream.insert(sample_length(rng, current_profile, len(stream.commands), spec))
                if pid is not None:
                    cohort.append(pid)
            if family == "striped_recycling":
                period = p["stripe_period"]
                victims = cohort[wave % period::period]
            else:
                victims = list(stream.ids)
                rng.shuffle(victims)
                victims = victims[:max(1, int(len(victims) * p["drain_fraction"]))]
            for pid in victims:
                stream.delete(pid)
            wave += 1
    else:
        center = rng.randint(1, 40)
        warmup = min(target, max(1, stream.limit // 4))
        while len(stream.commands) < stream.limit:
            step = len(stream.commands)
            phase = (step + p["phase_offset"]) // p["phase_length"]
            policy = "fifo" if family == "fifo" else "lifo" if family == "lifo" else "random"
            current_profile, current_target = profile, target
            if family == "size_biased_deletion":
                policy = "shortest" if (phase+spec["variant"]) % 2 else "longest"
            if family == "distribution_switch":
                current_profile = ("short", "long", "bimodal", "uniform")[(phase+spec["variant"]) % 4]
                current_target = max(8, int(target * (0.25, 1.8, 0.65, 1.25)[phase % 4]))
            remove = (step >= warmup and bool(stream.live) and
                      (len(stream.live) > current_target or rng.random() < spec["deletion_probability"]))
            if remove:
                stream.delete(stream.choose(policy))
            else:
                if family == "drifting_sizes":
                    if rng.random() < p["drift_move_probability"]:
                        center = max(1, min(40, center + rng.choice((-p["drift_step"], p["drift_step"]))))
                    length = max(1, min(40, center + rng.randint(-p["drift_radius"], p["drift_radius"])))
                else:
                    length = sample_length(rng, current_profile, step, spec)
                stream.insert(length)
    if len(stream.commands) != spec["operations"] or not stream.live:
        raise ValueError("generator violated operation count or positive final volume")
    return stream.commands


def parser_module():
    path = PARENT / "task-synthetic/tools/pipes_harness.py"
    spec = importlib.util.spec_from_file_location("search_v2_input_parser", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(destination: Path = DATA) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing corpus: {destination}")
    # Only SEARCH-v1 metadata is read for overlap checks. No held-out paths.
    old = json.loads((PARENT / "task-synthetic/data/search/manifest.json").read_text())
    old_hashes = {c["sha256"] for c in old["cases"]}
    old_seeds = {c["seed"] for c in old["cases"]}
    destination.mkdir(parents=True)
    parser, cases, seen_hashes, seen_seeds = parser_module(), [], set(), set()
    for spec in make_specs():
        commands = generate(spec)
        stats = audit_commands(commands)
        file = destination / (spec["id"] + ".in")
        file.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
        sha = digest(file)
        if sha in seen_hashes | old_hashes or spec["seed"] in seen_seeds | old_seeds:
            raise ValueError("duplicate seed or content within v2 or against SEARCH-v1")
        seen_hashes.add(sha)
        seen_seeds.add(spec["seed"])
        parsed = parser.parse_test(file)
        for a, b in (("operation_count", "operation_count"),
                     ("peak_live_pipe_length_m", "peak_live_volume"),
                     ("final_occupied_length_m", "final_live_volume"),
                     ("minimum_trench_lower_bound_m", "volume_lower_bound")):
            if parsed[a] != stats[b]:
                raise ValueError(f"independent parser disagreement: {file.name} {a}")
        if parsed["weight"] != 1.0 or parsed["test_sha256"] != sha:
            raise ValueError("wrong stream envelope or content hash")
        cases.append({**spec, "file": file.name, "sha256": sha, "stats": stats})
    manifest = {"version": VERSION, "split": "search", "case_count": len(cases),
                "families": list(SEARCH_FAMILIES), "cases_per_family": REPEATS,
                "weight_per_case": 1, "generator_sha256": digest(Path(__file__)),
                "primitive_generator_sha256": digest(PARENT / "generate_synthetic.py"),
                "python_version": sys.version.split()[0], "held_out_mechanisms": [],
                "independent_holdout": False,
                "candidate_results_used_to_select_inputs": False,
                "design_basis": "predeclared stratified parameters; prior search outcomes already known",
                "fitness": "mean_over_families(mean_over_cases(rounded_peak_live_volume / trench_length))",
                "cases": cases}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    grouped = defaultdict(list)
    for case in cases:
        grouped[case["family"]].append(case)
    coverage = {}
    for family, values in grouped.items():
        coverage[family] = {"cases": len(values), "unique_seeds": len({c["seed"] for c in values}),
                            "operation_counts": sorted({c["operations"] for c in values}),
                            "target_live_values": sorted({c["target_live"] for c in values}),
                            "deletion_probabilities": sorted({c["deletion_probability"] for c in values}),
                            "observed_peak_live_range": [min(c["stats"]["peak_live_count"] for c in values),
                                                         max(c["stats"]["peak_live_count"] for c in values)],
                            "observed_final_volume_range": [min(c["stats"]["final_live_volume"] for c in values),
                                                             max(c["stats"]["final_live_volume"] for c in values)]}
    report = {"version": VERSION, "status": "inputs_prepared_and_independently_parsed",
              "case_count": len(cases), "families": len(grouped),
              "operations": sum(c["operations"] for c in cases),
              "input_bytes": sum((destination / c["file"]).stat().st_size for c in cases),
              "manifest_sha256": digest(destination / "manifest.json"),
              "structural_audit_passed": True, "existing_harness_parser_passed": True,
              "overlap_with_search_v1": {"seeds": 0, "content": 0},
              "validation_accessed": False, "open15_accessed": False,
              "held_out_overlap_check": "not performed; held-out data was not accessed",
              "solvers_executed": 0, "interactors_executed": 0, "model_requests": 0,
              "family_coverage": coverage}
    (ROOT / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    report = prepare()
    print(json.dumps({k: v for k, v in report.items() if k != "family_coverage"}, indent=2))
