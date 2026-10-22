#!/usr/bin/env python3
"""Generate the preregistered train and validation streams."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OFFICIAL_GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
GENERATOR = HERE / "fast_generator.py"
PROFILES = ("uniform", "short-heavy", "long-heavy")
POLICIES = ("random", "oldest", "newest", "shortest", "longest")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(path: Path, seed: int, operations: int, profile: str,
             policy: str, churn: float, batch: int) -> None:
    subprocess.run([
        sys.executable, str(GENERATOR), "--seed", str(seed),
        "--operations", str(operations), "--length-profile", profile,
        "--churn", str(churn), "--batch", str(batch),
        "--deletion-policy", policy, "--weight", "1.0", "--out", str(path),
    ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    records: list[dict[str, object]] = []
    train_seed = 2_026_101_800
    for profile in PROFILES:
        for policy in POLICIES:
            for regime, churn, batch in (("steady", 0.42, 0), ("periodic-drain", 0.38, 500)):
                seed = train_seed + len(records)
                name = f"{seed}_{profile}_{policy}_{regime}.in"
                path = HERE / "inputs" / "train" / name
                generate(path, seed, 40_000, profile, policy, churn, batch)
                records.append({
                    "split": "train", "seed": seed, "operations": 40_000,
                    "profile": profile, "deletion_policy": policy, "regime": regime,
                    "churn": churn, "batch": batch,
                    "path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                })

    validation_seed = 2_026_101_900
    for operations in (16_384, 200_000):
        for profile in PROFILES:
            for policy in POLICIES:
                for regime, churn, batch in (("steady", 0.42, 0), ("periodic-drain", 0.38, 500)):
                    seed = validation_seed + len([r for r in records if r["split"] == "validation"])
                    name = f"{seed}_{operations}_{profile}_{policy}_{regime}.in"
                    path = HERE / "inputs" / "validation" / name
                    generate(path, seed, operations, profile, policy, churn, batch)
                    records.append({
                        "split": "validation", "seed": seed, "operations": operations,
                        "profile": profile, "deletion_policy": policy, "regime": regime,
                        "churn": churn, "batch": batch,
                        "path": str(path.relative_to(ROOT)), "sha256": sha256(path),
                    })

    manifest = {
        "preregistered": True,
        "official_generator_sha256": sha256(OFFICIAL_GENERATOR),
        "order_statistics_generator_sha256": sha256(GENERATOR),
        "records": records,
    }
    target = HERE / "inputs" / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"generated {sum(r['split'] == 'train' for r in records)} train and "
          f"{sum(r['split'] == 'validation' for r in records)} validation streams")


if __name__ == "__main__":
    main()
