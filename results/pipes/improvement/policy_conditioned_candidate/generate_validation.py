#!/usr/bin/env python3
"""Generate an independent, previously unused synthetic validation matrix."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
BASE_SEED = 915_700_000
PROFILES = ("uniform", "short-heavy", "long-heavy")
POLICIES = ("random", "oldest", "newest")
SIZES = (16_384, 200_000)


def main() -> None:
    records = []
    offset = 0
    for operations in SIZES:
        for profile in PROFILES:
            for policy in POLICIES:
                seed = BASE_SEED + offset
                offset += 1
                name = f"{operations}_{profile}_{policy}"
                output = HERE / "inputs" / "validation" / f"{name}.in"
                command = [
                    sys.executable, str(GENERATOR), "--seed", str(seed),
                    "--operations", str(operations), "--length-profile", profile,
                    "--churn", "0.48", "--batch", "0",
                    "--deletion-policy", policy, "--weight", "1", "--out", str(output),
                ]
                subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
                data = output.read_bytes()
                records.append({
                    "case": name,
                    "file": str(output.relative_to(ROOT)),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "seed": seed,
                    "operations": operations,
                    "length_profile": profile,
                    "deletion_policy": policy,
                    "churn": 0.48,
                    "batch": 0,
                })
    manifest = {
        "purpose": "Independent local validation after candidate source freeze; no official cases or identifiers.",
        "generator": "tools/generate_pipes_synthetic.py",
        "generator_sha256": hashlib.sha256(GENERATOR.read_bytes()).hexdigest(),
        "seed_base": BASE_SEED,
        "sizes": list(SIZES),
        "profiles": list(PROFILES),
        "deletion_policies": list(POLICIES),
        "records": records,
    }
    out = HERE / "inputs" / "validation_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(records)} independent inputs; manifest {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
