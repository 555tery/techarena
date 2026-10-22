#!/usr/bin/env python3
"""Generate the precommitted, fresh synthetic qualification matrix."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
FAST_GENERATOR = HERE / "qualification_generator.py"
INPUTS = HERE / "inputs/qualification_confirmatory"
SEED_BASE = 1_470_000_000
OPERATIONS = (16_384, 200_000)
PROFILES = ("uniform", "short-heavy", "long-heavy")
POLICIES = ("random", "oldest", "newest", "shortest", "longest")
REGIMES = (
    ("steady", 0.48, 0),
    ("periodic-drain", 0.42, 500),
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    official = load_module("pipes_generator_official", GENERATOR)
    fast = load_module("pipes_generator_fast", FAST_GENERATOR)
    prior = json.loads((HERE / "inputs/manifest.json").read_text(encoding="utf-8"))
    used = {
        row["seed"]
        for key in ("train_records", "validation_records")
        for row in prior[key]
    }
    gate = HERE / "qualification-gate.md"
    if not gate.exists():
        raise RuntimeError("precommitted qualification gate is missing")

    verification_cases = []
    verify_seed = 1_469_999_000
    for profile in PROFILES:
        for policy in POLICIES:
            for regime, churn, batch in REGIMES:
                official_commands = official.generate(
                    verify_seed, 4_096, profile, churn, batch, policy
                )
                fast_commands = fast.generate(
                    verify_seed, 4_096, profile, churn, batch, policy
                )
                if official_commands != fast_commands:
                    raise RuntimeError(
                        f"generator mismatch: {profile}/{policy}/{regime} seed={verify_seed}"
                    )
                verification_cases.append({
                    "seed": verify_seed,
                    "operations": 4_096,
                    "profile": profile,
                    "deletion_policy": policy,
                    "regime": regime,
                    "commands_sha256": hashlib.sha256(
                        ("\n".join(map(str, fast_commands)) + "\n").encode("ascii")
                    ).hexdigest(),
                })
                verify_seed += 1

    records = []
    seed = SEED_BASE
    for operations in OPERATIONS:
        for profile in PROFILES:
            for policy in POLICIES:
                for regime, churn, batch in REGIMES:
                    if seed in used:
                        raise RuntimeError(f"seed reused: {seed}")
                    name = f"{operations}_{profile}_{policy}_{regime}"
                    path = INPUTS / f"{name}.in"
                    if path.exists():
                        raise RuntimeError(f"refusing to overwrite existing input: {path}")
                    commands = fast.generate(seed, operations, profile, churn, batch, policy)
                    lines = [f"1 {len(commands)}", *(str(c) for c in commands), "0"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("\n".join(lines) + "\n", encoding="ascii")
                    records.append({
                        "name": name,
                        "path": str(path.relative_to(ROOT)),
                        "seed": seed,
                        "operations": operations,
                        "profile": profile,
                        "deletion_policy": policy,
                        "regime": regime,
                        "churn": churn,
                        "batch": batch,
                        "weight": 1.0,
                        "sha256": sha256(path),
                    })
                    seed += 1

    manifest = {
        "purpose": "Fresh paired synthetic confirmation of a frozen learned-gap-value candidate; not used for training or tuning.",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "gate_path": str(gate.relative_to(ROOT)),
        "gate_sha256": sha256(gate),
        "generator_path": str(GENERATOR.relative_to(ROOT)),
        "generator_sha256": sha256(GENERATOR),
        "optimized_generator_path": str(FAST_GENERATOR.relative_to(ROOT)),
        "optimized_generator_sha256": sha256(FAST_GENERATOR),
        "generator_equivalence": {
            "method": "exact command-list equality against official generator",
            "case_count": len(verification_cases),
            "records": verification_cases,
        },
        "seed_range": [SEED_BASE, seed - 1],
        "record_count": len(records),
        "records": records,
    }
    out = INPUTS / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"records={len(records)} seeds={SEED_BASE}..{seed - 1}")
    print(f"manifest={out.relative_to(ROOT)} sha256={sha256(out)}")


if __name__ == "__main__":
    main()
