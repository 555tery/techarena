#!/usr/bin/env python3
"""Generate fresh whole-stream train/validation data for policy rollout probe."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"


def main() -> None:
    records = []
    profiles = ("uniform", "short-heavy", "long-heavy")
    policies = ("random", "oldest", "newest")
    for split, reps in (("train", 1), ("validation", 2)):
        split_offset = 0 if split == "train" else 1000
        for profile_i, profile in enumerate(profiles):
            for policy_i, policy in enumerate(policies):
                for replicate in range(reps):
                    seed = 516_000_000 + split_offset + profile_i * 10_000 + policy_i * 100 + replicate
                    output = HERE / "inputs" / split / f"{profile}_{policy}_{replicate}.in"
                    output.parent.mkdir(parents=True, exist_ok=True)
                    command = [
                        sys.executable, str(GENERATOR), "--seed", str(seed),
                        "--operations", "1800", "--length-profile", profile,
                        "--churn", "0.48", "--batch", "0",
                        "--deletion-policy", policy, "--weight", "1", "--out", str(output),
                    ]
                    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                    digest = hashlib.sha256(output.read_bytes()).hexdigest()
                    records.append({
                        "split": split,
                        "file": str(output.relative_to(ROOT)),
                        "sha256": digest,
                        "seed": seed,
                        "operations": 1800,
                        "length_profile": profile,
                        "deletion_policy": policy,
                        "churn": 0.48,
                    })
    manifest = {
        "purpose": "Fresh synthetic whole streams; train and validation are disjoint by seed.",
        "generator": "tools/generate_pipes_synthetic.py",
        "train_streams": 9,
        "validation_streams": 18,
        "profiles": ["uniform", "short-heavy", "long-heavy"],
        "deletion_policies": ["random", "oldest", "newest"],
        "records": records,
    }
    (HERE / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
