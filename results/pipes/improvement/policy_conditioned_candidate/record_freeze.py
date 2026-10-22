#!/usr/bin/env python3
"""Record immutable source/binary/input identities before independent validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    final_source = ROOT / "results/pipes/final/solution.cpp"
    canonical_source = ROOT / "src/pipes.cpp"
    interactor_source = ROOT / "vendor/pipes_official/interactor.cpp"
    expected = {
        final_source: "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991",
        canonical_source: "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8",
        interactor_source: "85672e4c3ad9fdcb97d8b601758de1f1d1b5e86d6dd20252e0f72acdb9cb122a",
    }
    for path, sha in expected.items():
        actual = digest(path)
        if actual != sha:
            raise RuntimeError(f"protected source changed: {path}: {actual}")
    manifest = {
        "status": "source frozen before independent validation",
        "candidate_source": {
            "path": "results/pipes/improvement/policy_conditioned_candidate/src/policy_conditioned.cpp",
            "sha256": digest(HERE / "src/policy_conditioned.cpp"),
        },
        "baseline_source": {
            "path": "results/pipes/final/solution.cpp",
            "sha256": digest(final_source),
        },
        "canonical_source": {
            "path": "src/pipes.cpp",
            "sha256": digest(canonical_source),
        },
        "interactor_source": {
            "path": "vendor/pipes_official/interactor.cpp",
            "sha256": digest(interactor_source),
        },
        "validation_input_manifest": {
            "path": "results/pipes/improvement/policy_conditioned_candidate/inputs/validation_manifest.json",
            "sha256": digest(HERE / "inputs/validation_manifest.json"),
        },
        "binaries": {
            name: {
                "path": f"results/pipes/improvement/policy_conditioned_candidate/bin/{name}",
                "sha256": digest(HERE / "bin" / name),
            }
            for name in (
                "frozen_final_linux", "policy_conditioned_linux",
                "policy_conditioned_linux_diag", "interactor_linux",
            )
        },
        "build": {
            "image": "agentic-scientist/pipes-cpp:2b8aa392",
            "target": "Linux 6.10.14-linuxkit aarch64",
            "compiler": "g++ (Debian 14.2.0-19) 14.2.0",
            "candidate_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror",
            "baseline_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic",
            "interactor_flags": "-O2 -std=c++17 -pipe",
        },
        "policy": {
            "decision_rule": "Use P4 iff paired 16-scenario mean terminal trench delta versus baseline is strictly negative.",
            "history_only": True,
            "test_ids_or_future_commands_used": False,
            "cadence_commands": 60,
            "maximum_selector_decisions": 8,
            "selector_starts_only_after_frozen_MC_budget_spent": True,
            "no_threshold_calibration_on_validation_or_Open15": True,
        },
        "qualification": {
            "synthetic_preflight": "completed on a prior fresh seed; used only for smoke/telemetry, not calibration",
            "independent_validation": "pending",
            "Open15": "not run",
            "holdout_v2": "not run",
            "platform_or_leaderboard": "not accessed",
        },
    }
    output = HERE / "manifest.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing manifest: {output}")
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"frozen candidate sha256={manifest['candidate_source']['sha256']}")
    print(f"manifest={output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
