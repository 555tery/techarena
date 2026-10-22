#!/usr/bin/env python3
"""Create preregistered train and fresh validation streams; refuse collisions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR = ROOT.parents[0] / "run48_synthetic_independent" / "generate_streams.py"
SIZES = (16_384, 200_000)

TRAIN = [
    ("uniform_random", [{"length_profile": "uniform", "churn": .42,
                         "deletion_policy": "random", "batch": 0,
                         "repeat_probability": .02}]),
    ("short_fifo", [{"length_profile": "short-heavy", "churn": .48,
                     "deletion_policy": "oldest", "batch": 0,
                     "repeat_probability": .10}]),
    ("long_newest", [{"length_profile": "long-heavy", "churn": .42,
                      "deletion_policy": "newest", "batch": 0,
                      "repeat_probability": .12}]),
    ("bimodal_shortest", [{"length_profile": "bimodal", "churn": .50,
                           "deletion_policy": "shortest", "batch": 0,
                           "repeat_probability": .65}]),
    ("short_to_long", [
        {"length_profile": "short-heavy", "churn": .35,
         "deletion_policy": "random", "batch": 0, "repeat_probability": .10},
        {"length_profile": "long-heavy", "churn": .50,
         "deletion_policy": "oldest", "batch": 0, "repeat_probability": .10},
    ]),
    ("long_to_short", [
        {"length_profile": "long-heavy", "churn": .45,
         "deletion_policy": "newest", "batch": 0, "repeat_probability": .10},
        {"length_profile": "short-heavy", "churn": .35,
         "deletion_policy": "longest", "batch": 0, "repeat_probability": .10},
    ]),
    ("uniform_fifo_to_newest", [
        {"length_profile": "uniform", "churn": .42,
         "deletion_policy": "oldest", "batch": 0, "repeat_probability": .02},
        {"length_profile": "uniform", "churn": .42,
         "deletion_policy": "newest", "batch": 0, "repeat_probability": .02},
    ]),
    ("short_random", [{"length_profile": "short-heavy", "churn": .40,
                       "deletion_policy": "random", "batch": 0,
                       "repeat_probability": .08}]),
]

VALIDATION = [
    ("uniform_random", [{"length_profile": "uniform", "churn": .42,
                         "deletion_policy": "random", "batch": 0,
                         "repeat_probability": .02}]),
    ("short_fifo", [{"length_profile": "short-heavy", "churn": .48,
                     "deletion_policy": "oldest", "batch": 0,
                     "repeat_probability": .10}]),
    ("long_newest", [{"length_profile": "long-heavy", "churn": .42,
                      "deletion_policy": "newest", "batch": 0,
                      "repeat_probability": .12}]),
    ("bimodal_shortest", [{"length_profile": "bimodal", "churn": .50,
                           "deletion_policy": "shortest", "batch": 0,
                           "repeat_probability": .65}]),
    ("short_to_long", [
        {"length_profile": "short-heavy", "churn": .35,
         "deletion_policy": "random", "batch": 0, "repeat_probability": .10},
        {"length_profile": "long-heavy", "churn": .50,
         "deletion_policy": "oldest", "batch": 0, "repeat_probability": .10},
    ]),
    ("long_to_short", [
        {"length_profile": "long-heavy", "churn": .45,
         "deletion_policy": "newest", "batch": 0, "repeat_probability": .10},
        {"length_profile": "short-heavy", "churn": .35,
         "deletion_policy": "longest", "batch": 0, "repeat_probability": .10},
    ]),
    ("uniform_fifo_to_newest", [
        {"length_profile": "uniform", "churn": .42,
         "deletion_policy": "oldest", "batch": 0, "repeat_probability": .02},
        {"length_profile": "uniform", "churn": .42,
         "deletion_policy": "newest", "batch": 0, "repeat_probability": .02},
    ]),
]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def phase_list(template: list[dict], operations: int) -> list[dict]:
    if len(template) == 1:
        return [dict(template[0], start=0, end=operations)]
    bounds = [round(i * operations / len(template))
              for i in range(len(template) + 1)]
    return [dict(phase, start=bounds[i], end=bounds[i + 1])
            for i, phase in enumerate(template)]


def make_case(split: str, index: int, name: str, template: list[dict],
              size_index: int, operations: int, replicate: int) -> dict:
    if split == "train":
        seed = 9_801_600_000 + index * 1_000 + replicate
    else:
        seed = 9_802_700_000 + index * 1_000_000 + size_index * 1_000 + replicate
    return {"name": f"{name}_n{operations}_r{replicate + 1}",
            "operations": operations, "seed": seed,
            "phases": phase_list(template, operations)}


def main() -> None:
    input_root = ROOT / "inputs"
    if input_root.exists() and any(input_root.rglob("*.in")):
        raise SystemExit(f"refusing to overwrite existing inputs in {input_root}")
    spec = importlib.util.spec_from_file_location("pipe_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load generator {GENERATOR}")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)

    cases = []
    for i, (name, phases) in enumerate(TRAIN):
        cases.append(("train", i, name, phases, 0, 16_384, 0))
    for i, (name, phases) in enumerate(VALIDATION):
        for size_index, operations in enumerate(SIZES):
            for replicate in range(2):
                cases.append(("validation", i, name, phases, size_index,
                              operations, replicate))

    seeds = []
    scenarios = []
    for split, i, name, phases, size_index, operations, replicate in cases:
        scenario = make_case(split, i, name, phases, size_index,
                             operations, replicate)
        seeds.append(scenario["seed"])
        scenarios.append((split, scenario))
    if len(seeds) != len(set(seeds)):
        raise SystemExit("duplicate seeds in this matrix")

    prior_manifests: list[str] = []
    seed_collisions = []
    for path in ROOT.parents[1].rglob("*.json"):
        if ROOT in path.parents:
            continue
        if not any(marker in path.name.lower() for marker in
                   ("manifest", "input", "qualification")):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        prior_manifests.append(str(path.relative_to(ROOT.parents[2])))
        for seed in seeds:
            if re.search(rf"(?<!\d){seed}(?!\d)", content):
                seed_collisions.append({"seed": seed, "path": str(path)})
    if seed_collisions:
        raise SystemExit(f"seed collision(s) in previous manifests: {seed_collisions}")

    prior_hashes = set()
    for base in (ROOT.parents[3] / "data/pipes", ROOT.parents[3] / "results/pipes"):
        for path in base.rglob("*.in"):
            if ROOT in path.parents:
                continue
            try:
                prior_hashes.add(sha_bytes(path.read_bytes()))
            except OSError:
                continue

    input_root.mkdir(parents=True, exist_ok=True)
    records = {"train": {}, "validation": {}}
    hash_collisions = []
    for split, scenario in scenarios:
        commands, stats = generator.generate(scenario)
        text = "\n".join([f"1.0 {len(commands)}", *map(str, commands), "0", ""])
        data = text.encode("ascii")
        digest = sha_bytes(data)
        if digest in prior_hashes:
            hash_collisions.append({"name": scenario["name"], "sha256": digest})
        out = input_root / split / f"{scenario['name']}.in"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        records[split][scenario["name"]] = {
            "path": str(out.relative_to(ROOT)), "sha256": digest,
            "scenario": scenario, "stream_stats": stats,
        }
        print(f"{split}/{scenario['name']}: seed={scenario['seed']} "
              f"ops={stats['operations']} sha256={digest}")
    if hash_collisions:
        raise SystemExit(f"input hash collision(s): {hash_collisions}")

    manifest = {
        "purpose": "BOCPD latent-regime MPC synthetic train and preregistered fresh validation",
        "generator": str(GENERATOR.relative_to(ROOT.parents[3])),
        "generator_sha256": sha_bytes(GENERATOR.read_bytes()),
        "script_sha256": sha_bytes(Path(__file__).read_bytes()),
        "families": [name for name, _ in VALIDATION],
        "sizes": list(SIZES), "replicates_per_validation_cell": 2,
        "seed_collisions": seed_collisions,
        "input_hash_collisions": hash_collisions,
        "prior_manifest_paths_scanned": len(prior_manifests),
        "prior_input_hashes_scanned": len(prior_hashes),
        "train": records["train"], "validation": records["validation"],
    }
    (ROOT / "input_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"generated {len(records['train'])} train and "
          f"{len(records['validation'])} validation streams")


if __name__ == "__main__":
    main()
