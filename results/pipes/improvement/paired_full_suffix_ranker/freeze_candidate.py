#!/usr/bin/env python3
"""Record immutable hashes for the one final ranker candidate."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    source = HERE / "src/ranker_candidate.cpp"
    model = HERE / "src/ranker_model.hpp"
    binary = HERE / "bin/candidate_final"
    inputs = HERE / "inputs/manifest.json"
    training = HERE / "runs/training-manifest.json"
    missing = [str(p) for p in (source, model, binary, inputs, training) if not p.exists()]
    if missing:
        raise RuntimeError("candidate is not ready to freeze: " + ", ".join(missing))
    lock = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "candidate_source_sha256": sha256(source),
        "candidate_model_sha256": sha256(model),
        "candidate_binary_sha256": sha256(binary),
        "input_manifest_sha256": sha256(inputs),
        "training_manifest_sha256": sha256(training),
        "candidate_build": "clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic",
        "frozen": True,
    }
    path = HERE / "runs/candidate-lock.json"
    if path.exists():
        raise RuntimeError("candidate already frozen; do not overwrite the lock")
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
