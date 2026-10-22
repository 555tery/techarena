#!/usr/bin/env python3
"""Record candidate freeze and fresh validation input identities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protected = {
        "results/pipes/final/solution.cpp": "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991",
        "src/pipes.cpp": "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8",
        "vendor/pipes_official/interactor.cpp": "85672e4c3ad9fdcb97d8b601758de1f1d1b5e86d6dd20252e0f72acdb9cb122a",
    }
    for name, expected in protected.items():
        actual = digest(ROOT / name)
        if actual != expected:
            raise RuntimeError(f"protected file hash changed: {name}: {actual}")
    input_manifest = HERE / "inputs/validation_manifest.json"
    manifest = {
        "status": "candidate source frozen before new independent validation",
        "candidate_source": {
            "path": "results/pipes/improvement/policy_conditioned_unique8/src/policy_conditioned.cpp",
            "sha256": digest(HERE / "src/policy_conditioned.cpp"),
        },
        "baseline_source": {
            "path": "results/pipes/final/solution.cpp",
            "sha256": digest(ROOT / "results/pipes/final/solution.cpp"),
        },
        "canonical_source": {
            "path": "src/pipes.cpp",
            "sha256": digest(ROOT / "src/pipes.cpp"),
        },
        "interactor_source": {
            "path": "vendor/pipes_official/interactor.cpp",
            "sha256": digest(ROOT / "vendor/pipes_official/interactor.cpp"),
        },
        "input_manifest": {
            "path": "results/pipes/improvement/policy_conditioned_unique8/inputs/validation_manifest.json",
            "sha256": digest(input_manifest),
        },
        "binaries": {
            name: {
                "path": f"results/pipes/improvement/policy_conditioned_unique8/bin/{name}",
                "sha256": digest(HERE / "bin" / name),
            }
            for name in (
                "frozen_final_linux", "policy_conditioned_linux",
                "policy_conditioned_linux_diag", "interactor_linux",
            )
        },
        "policy_change": {
            "only_algorithmic_change": "Require at least 8 distinct exact event sequences among the 16 history-only scenarios before evaluating or selecting P4.",
            "scenario_identity": "Exact equality over all 16 (kind,value) observations; duplicates remain in the paired 16-sample score after the unique-count gate passes.",
            "no_other_thresholds_changed": True,
            "no_previous_validation_streams_used": True,
        },
        "predeclared_gate": {
            "overall_delta_kpi_paired_stream_bootstrap_95_ci_strictly_positive": True,
            "overall_delta_trench_paired_stream_bootstrap_95_ci_strictly_negative": True,
            "short_heavy_200000_no_systematic_regression": "mean delta KPI >= 0 and fewer than 2 of 3 streams have worse KPI",
            "maximum_cpu_s": 4.50,
            "maximum_rss_mib": 230.0,
            "all_18_paired_transcripts_accepted": True,
            "bootstrap_replicates": 50000,
            "bootstrap_stream_weighting": "equal weight per independent stream",
        },
        "build": {
            "image": "agentic-scientist/pipes-cpp:2b8aa392",
            "target": "Linux aarch64",
            "compiler": "GCC 14.2.0",
            "candidate_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror",
            "baseline_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic",
            "interactor_flags": "-O2 -std=c++17 -pipe",
            "harness_parallel_pairs": 1,
        },
        "qualification": {
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
    print(f"fresh input manifest sha256={manifest['input_manifest']['sha256']}")


if __name__ == "__main__":
    main()
