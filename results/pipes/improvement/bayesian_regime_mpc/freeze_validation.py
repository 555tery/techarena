#!/usr/bin/env python3
"""Freeze source, fitted model, validation inputs and harness before screening."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if (ROOT / "runs/validation").exists():
        raise SystemExit("validation output exists; refusing to refreeze after results")
    manifest = json.loads((ROOT / "input_manifest.json").read_text(encoding="utf-8"))
    params = json.loads((ROOT / "model_params.json").read_text(encoding="utf-8"))
    candidate = ROOT / "source/bayesian_regime_mpc.cpp"
    frozen = ROOT / "source/frozen_final.cpp"
    if sha(frozen) != "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991":
        raise SystemExit("frozen source snapshot mismatch")
    validation = manifest["validation"]
    if len(validation) != 28:
        raise SystemExit("expected 28 independent validation inputs")
    for name, row in validation.items():
        path = ROOT / row["path"]
        if sha(path) != row["sha256"]:
            raise SystemExit(f"validation input SHA mismatch: {name}")

    clangxx = subprocess.run(["clang++", "--version"], check=True,
                             capture_output=True, text=True).stdout.splitlines()[0]
    interactor = REPO / "results/pipes/final/bin/interactor"
    harness = REPO / "tools/pipes_harness.py"
    compare = REPO / "tools/compare_pipes_binaries.py"
    result = {
        "status": "frozen-before-validation",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.platform(),
        "compiler": clangxx,
        "build_flags": ["-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra",
                        "-Wconversion", "-Wshadow", "-pedantic", "-Werror"],
        "frozen_source_sha256": sha(frozen),
        "candidate_source_sha256": sha(candidate),
        "fitted_model_parameters_sha256": sha(ROOT / "model_params.json"),
        "training_manifest_sha256": sha(ROOT / "input_manifest.json"),
        "preregistered_gate_sha256": sha(ROOT / "PREREGISTERED.md"),
        "generator_sha256": manifest["generator_sha256"],
        "training_stream_count": len(manifest["train"]),
        "validation_stream_count": len(validation),
        "validation_input_hashes": {
            name: row["sha256"] for name, row in sorted(validation.items())
        },
        "frozen_binary_sha256": sha(ROOT / "bin/frozen"),
        "candidate_binary_sha256": sha(ROOT / "bin/bayesian"),
        "interactor_sha256": sha(interactor),
        "harness_sha256": sha(harness),
        "comparison_driver_sha256": sha(compare),
        "train_smoke": {
            "command": "python3 tools/compare_pipes_binaries.py --solver frozen=results/pipes/improvement/bayesian_regime_mpc/bin/frozen --solver bayesian=results/pipes/improvement/bayesian_regime_mpc/bin/bayesian --tests results/pipes/improvement/bayesian_regime_mpc/inputs/train --out results/pipes/improvement/bayesian_regime_mpc/runs/train_smoke_final --interactor results/pipes/final/bin/interactor --baseline frozen",
            "valid_cases": 8,
            "candidate_cpu_max_s": 0.093135,
            "candidate_rss_max_mib": 3.296875,
        },
    }
    out = ROOT / "freeze_manifest.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"frozen candidate sha256={result['candidate_source_sha256']}")
    print(f"frozen validation inputs={result['validation_stream_count']}")
    print(f"manifest sha256={sha(out)}")


if __name__ == "__main__":
    main()
