#!/usr/bin/env python3
"""Create ten independent transfer-check streams after selecting tree #33."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[0].parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
OUT = HERE / "validation"
CASES = [
    (20262001, "uniform", 0.34, 500, "random"),
    (20262002, "short-heavy", 0.48, 0, "random"),
    (20262003, "long-heavy", 0.44, 700, "random"),
    (20262004, "uniform", 0.52, 900, "newest"),
    (20262005, "uniform", 0.52, 900, "oldest"),
    (20262006, "short-heavy", 0.38, 650, "longest"),
    (20262007, "long-heavy", 0.38, 650, "shortest"),
    (20262008, "short-heavy", 0.56, 0, "oldest"),
    (20262009, "long-heavy", 0.56, 0, "newest"),
    (20262010, "uniform", 0.30, 0, "shortest"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for seed, profile, churn, batch, deletion in CASES:
        name = f"seed-{seed}"
        path = OUT / f"{name}.in"
        cmd = [
            sys.executable, str(GENERATOR), "--seed", str(seed),
            "--operations", "25000", "--length-profile", profile,
            "--churn", str(churn), "--batch", str(batch),
            "--deletion-policy", deletion, "--out", str(path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        manifest.append({
            "name": name,
            "seed": seed,
            "operations": 25000,
            "length_profile": profile,
            "churn": churn,
            "batch": batch,
            "deletion_policy": deletion,
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    (OUT / "validation_manifest.json").write_text(json.dumps({
        "purpose": "independent synthetic transfer validation; not used in tree search",
        "cases": manifest,
    }, indent=2) + "\n")
    print(f"generated {len(manifest)} validation streams")


if __name__ == "__main__":
    main()
