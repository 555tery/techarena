#!/usr/bin/env python3
"""Generate independent short Pipes streams for the joint-gap probe."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "inputs"
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    profiles = ("uniform", "short-heavy", "long-heavy")
    policies = ("random", "oldest", "newest")
    for profile_i, profile in enumerate(profiles):
        for policy_i, policy in enumerate(policies):
            for replicate in range(2):
                seed = 874_310_001 + profile_i * 10_000 + policy_i * 100 + replicate
                output = OUT / f"{profile}_{policy}_{replicate}.in"
                command = [
                    sys.executable, str(GENERATOR), "--seed", str(seed),
                    "--operations", "1800", "--length-profile", profile,
                    "--churn", "0.48", "--batch", "0",
                    "--deletion-policy", policy, "--weight", "1",
                    "--out", str(output),
                ]
                subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                digest = hashlib.sha256(output.read_bytes()).hexdigest()
                records.append({
                    "file": str(output.relative_to(ROOT)),
                    "sha256": digest,
                    "seed": seed,
                    "operations": 1800,
                    "length_profile": profile,
                    "deletion_policy": policy,
                    "churn": 0.48,
                })
    manifest = {
        "purpose": "New independent short streams; not official tests or holdout-v2.",
        "generator": "tools/generate_pipes_synthetic.py",
        "records": records,
    }
    (OUT.parent / "input_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
