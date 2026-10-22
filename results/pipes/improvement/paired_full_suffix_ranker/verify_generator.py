#!/usr/bin/env python3
"""Check exact command-list equality with the repository generator."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(commands: list[int]) -> str:
    payload = ",".join(map(str, commands)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    official = import_file("official_generator", ROOT / "tools/generate_pipes_synthetic.py")
    fast = import_file("fast_generator", HERE / "fast_generator.py")
    profiles = ("uniform", "short-heavy", "long-heavy")
    policies = ("random", "oldest", "newest", "shortest", "longest")
    regimes = (("steady", 0.42, 0), ("periodic-drain", 0.38, 500))
    checks = []
    for index, (profile, policy, (regime, churn, batch)) in enumerate(
        (p, d, r) for p in profiles for d in policies for r in regimes
    ):
        seed = 2_026_101_700 + index
        expected = official.generate(seed, 5_000, profile, churn, batch, policy)
        actual = fast.generate(seed, 5_000, profile, churn, batch, policy)
        if expected != actual:
            first = next((i for i, (a, b) in enumerate(zip(expected, actual)) if a != b), None)
            raise RuntimeError(f"generator mismatch seed={seed}, first_index={first}")
        checks.append({
            "seed": seed, "operations": 5_000, "profile": profile,
            "deletion_policy": policy, "regime": regime,
            "command_sha256": digest(actual),
        })
    manifest = {
        "checks": len(checks),
        "official_generator_sha256": hashlib.sha256(
            (ROOT / "tools/generate_pipes_synthetic.py").read_bytes()).hexdigest(),
        "fast_generator_sha256": hashlib.sha256((HERE / "fast_generator.py").read_bytes()).hexdigest(),
        "all_command_lists_exactly_equal": True,
        "records": checks,
    }
    path = HERE / "inputs/generator-equivalence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"exact command-list equality: {len(checks)}/{len(checks)}")


if __name__ == "__main__":
    main()
