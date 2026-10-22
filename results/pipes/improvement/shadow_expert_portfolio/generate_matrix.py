#!/usr/bin/env python3
"""Generate the pre-registered causal synthetic matrix; refuse collisions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
GENERATOR = ROOT.parents[0] / "run48_synthetic_independent" / "generate_streams.py"
FAMILIES = [
    ("uniform_random", [{"length_profile": "uniform", "churn": .42,
                          "deletion_policy": "random", "batch": 0,
                          "repeat_probability": .02}]),
    ("short_fifo", [{"length_profile": "short-heavy", "churn": .48,
                     "deletion_policy": "oldest", "batch": 400,
                     "repeat_probability": .10}]),
    ("long_newest", [{"length_profile": "long-heavy", "churn": .42,
                      "deletion_policy": "newest", "batch": 480,
                      "repeat_probability": .15}]),
    ("bimodal_sticky_oldest", [{"length_profile": "bimodal", "churn": .52,
                                "deletion_policy": "oldest", "batch": 320,
                                "repeat_probability": .75}]),
    ("short_to_long_delete_shift", [
        {"length_profile": "short-heavy", "churn": .36,
         "deletion_policy": "random", "batch": 320,
         "repeat_probability": .15},
        {"length_profile": "long-heavy", "churn": .50,
         "deletion_policy": "oldest", "batch": 520,
         "repeat_probability": .20},
    ]),
    ("long_to_short_delete_shift", [
        {"length_profile": "long-heavy", "churn": .50,
         "deletion_policy": "newest", "batch": 520,
         "repeat_probability": .20},
        {"length_profile": "short-heavy", "churn": .35,
         "deletion_policy": "longest", "batch": 320,
         "repeat_probability": .10},
    ]),
]
SIZES = [(0, 5_000), (1, 50_000), (2, 200_000)]
REPLICATES = range(2)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_scenario(fi: int, family: tuple[str, list[dict]],
                  size_index: int, operations: int, replicate: int) -> dict:
    name, template = family
    seed = 8_710_230_000 + fi * 1_000_000 + size_index * 1_000 + replicate
    phases = []
    if len(template) == 1:
        phase = dict(template[0], start=0, end=operations)
        phases.append(phase)
    else:
        midpoint = operations // 2
        phases = [dict(template[0], start=0, end=midpoint),
                  dict(template[1], start=midpoint, end=operations)]
    return {"name": f"{name}_n{operations}_r{replicate + 1}",
            "operations": operations, "seed": seed, "phases": phases}


def main() -> None:
    if list(INPUTS.glob("*.in")) or (ROOT / "input_manifest.json").exists():
        raise SystemExit("refusing to overwrite existing generated inputs/manifest")
    spec = importlib.util.spec_from_file_location("pipes_generator", GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load generator: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    scenarios = []
    for fi, family in enumerate(FAMILIES):
        for size_index, operations in SIZES:
            for replicate in REPLICATES:
                scenarios.append(make_scenario(fi, family, size_index,
                                               operations, replicate))
    seeds = [scenario["seed"] for scenario in scenarios]
    if len(seeds) != len(set(seeds)):
        raise SystemExit("duplicate seeds inside the registered matrix")

    prior_manifests = []
    seed_collisions = []
    scan_root = ROOT.parents[1]
    for path in scan_root.rglob("*.json"):
        if ROOT in path.parents:
            continue
        low_name = path.name.lower()
        if not any(marker in low_name for marker in
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
        raise SystemExit(f"seed collision(s) in prior manifests: {seed_collisions}")

    known_inputs: dict[str, str] = {}
    repo_root = ROOT.parents[3]
    for base in (repo_root / "data/pipes", repo_root / "results/pipes"):
        for path in base.rglob("*.in"):
            if ROOT in path.parents:
                continue
            try:
                known_inputs.setdefault(sha(path), str(path.relative_to(repo_root)))
            except OSError:
                continue

    INPUTS.mkdir(parents=True, exist_ok=True)
    records = {}
    for scenario in scenarios:
        commands, stats = module.generate(scenario)
        path = INPUTS / f"{scenario['name']}.in"
        path.write_text("\n".join([f"1.0 {len(commands)}",
                                   *map(str, commands), "0"]) + "\n",
                        encoding="ascii")
        digest = sha(path)
        if digest in known_inputs:
            raise SystemExit(f"input hash collision: {path} with {known_inputs[digest]}")
        records[scenario["name"]] = {
            "path": str(path.relative_to(ROOT)), "sha256": digest,
            "scenario": scenario, "stats": stats,
        }
    if len({row["sha256"] for row in records.values()}) != len(records):
        raise SystemExit("duplicate generated input hashes")

    manifest = {
        "purpose": "Pre-registered shadow-expert portfolio screen",
        "generator": str(GENERATOR.relative_to(repo_root)),
        "generator_sha256": sha(GENERATOR),
        "script_sha256": sha(Path(__file__)),
        "families": [name for name, _ in FAMILIES],
        "sizes": [n for _, n in SIZES], "replicates_per_cell": 2,
        "seed_formula": "8710230000 + family*1000000 + size_index*1000 + replicate",
        "seed_collisions": [], "prior_seed_manifests_scanned": len(prior_manifests),
        "prior_manifest_paths": prior_manifests,
        "prior_input_hashes_scanned": len(known_inputs), "input_hash_collisions": [],
        "streams": records,
    }
    (ROOT / "input_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    for name, row in records.items():
        print(f"{name}: ops={row['stats']['operations']} seed={row['scenario']['seed']} "
              f"sha256={row['sha256']}")
    print(f"generated {len(records)} unique streams; scanned "
          f"{len(prior_manifests)} prior manifests and {len(known_inputs)} saved inputs")


if __name__ == "__main__":
    main()
