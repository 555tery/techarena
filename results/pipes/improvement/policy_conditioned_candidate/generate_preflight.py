#!/usr/bin/env python3
"""Create fresh synthetic streams for the policy-conditioned candidate gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
BASE_SEED = 912_300_000
PROFILES = ("uniform", "short-heavy", "long-heavy")
POLICIES = ("random", "oldest", "newest")


def main() -> None:
    records = []
    cases = []
    seed_offset = 0
    for operations in (4096, 16384):
        for profile in PROFILES:
            for policy in POLICIES:
                seed = BASE_SEED + seed_offset
                seed_offset += 1
                name = f"{operations}_{profile}_{policy}"
                output = HERE / "inputs" / "preflight" / f"{name}.in"
                output.parent.mkdir(parents=True, exist_ok=True)
                command = [
                    sys.executable, str(GENERATOR), "--seed", str(seed),
                    "--operations", str(operations), "--length-profile", profile,
                    "--churn", "0.48", "--batch", "0",
                    "--deletion-policy", policy, "--weight", "1", "--out", str(output),
                ]
                subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                records.append({
                    "case": name,
                    "file": str(output.relative_to(ROOT)),
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "seed": seed,
                    "operations": operations,
                    "length_profile": profile,
                    "deletion_policy": policy,
                    "churn": 0.48,
                    "batch": 0,
                })

    stress = (
        ("uniform_random", "uniform", "random"),
        ("short_heavy_oldest", "short-heavy", "oldest"),
        ("long_heavy_newest", "long-heavy", "newest"),
    )
    for name, profile, policy in stress:
        seed = BASE_SEED + seed_offset
        seed_offset += 1
        output = HERE / "inputs" / "preflight" / f"200000_{name}.in"
        command = [
            sys.executable, str(GENERATOR), "--seed", str(seed),
            "--operations", "200000", "--length-profile", profile,
            "--churn", "0.48", "--batch", "0",
            "--deletion-policy", policy, "--weight", "1", "--out", str(output),
        ]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        records.append({
            "case": name,
            "file": str(output.relative_to(ROOT)),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "seed": seed,
            "operations": 200000,
            "length_profile": profile,
            "deletion_policy": policy,
            "churn": 0.48,
            "batch": 0,
        })

    manifest = {
        "purpose": "Fresh local synthetic preflight; no official inputs or test identifiers.",
        "generator": "tools/generate_pipes_synthetic.py",
        "generator_sha256": hashlib.sha256(GENERATOR.read_bytes()).hexdigest(),
        "seed_base": BASE_SEED,
        "short_and_medium_streams": 18,
        "maximum_command_stress_streams": 3,
        "profiles": list(PROFILES),
        "deletion_policies": list(POLICIES),
        "records": records,
    }
    (HERE / "inputs" / "preflight_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
