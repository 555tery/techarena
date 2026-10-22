#!/usr/bin/env python3
"""Create disjoint synthetic training and validation streams."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
PROFILES = ("uniform", "short-heavy", "long-heavy")
POLICIES = ("random", "oldest", "newest")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(split: str, seed_base: int, sizes: tuple[int, ...], repeats: int) -> list[dict]:
    records = []
    offset = 0
    for operations in sizes:
        for repeat in range(repeats):
            for profile in PROFILES:
                for policy in POLICIES:
                    seed = seed_base + offset
                    offset += 1
                    name = f"{operations}_{profile}_{policy}_{repeat}"
                    output = HERE / "inputs" / split / f"{name}.in"
                    command = [
                        sys.executable, str(GENERATOR), "--seed", str(seed),
                        "--operations", str(operations), "--length-profile", profile,
                        "--churn", "0.48", "--batch", "0",
                        "--deletion-policy", policy, "--weight", "1", "--out", str(output),
                    ]
                    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                    records.append({
                        "name": name,
                        "path": str(output.relative_to(ROOT)),
                        "seed": seed,
                        "operations": operations,
                        "profile": profile,
                        "deletion_policy": policy,
                        "repeat": repeat,
                        "churn": 0.48,
                        "batch": 0,
                        "sha256": digest(output),
                    })
    return records


def main() -> None:
    generator_hash = digest(GENERATOR)
    train = generate("train", 1_450_000_000, (16_384,), 2)
    validation = generate("validation", 1_460_000_000, (16_384, 200_000), 1)
    manifest = {
        "purpose": "Offline learned action-value training and independent synthetic validation.",
        "generator": str(GENERATOR.relative_to(ROOT)),
        "generator_sha256": generator_hash,
        "train_seed_range": [min(r["seed"] for r in train), max(r["seed"] for r in train)],
        "validation_seed_range": [min(r["seed"] for r in validation), max(r["seed"] for r in validation)],
        "train_records": train,
        "validation_records": validation,
        "training_uses_future_only_for_labels": True,
        "runtime_policy_uses_test_id_or_future": False,
    }
    (HERE / "inputs" / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"generated train={len(train)} validation={len(validation)} streams")


if __name__ == "__main__":
    main()
