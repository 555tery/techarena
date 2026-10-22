#!/usr/bin/env python3
"""Create state-only, preregistered train/holdout coalescence cases."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "coalescence_cases"
OUT.mkdir(exist_ok=True)


def make(seed: int, split_index: int) -> dict:
    rng = random.Random(seed)
    # The mechanism is fixed before evaluation: two boundary anchors of equal
    # size, symmetric outside gaps, and a centered residue split that alone
    # leaves both future Q-sized corridors wide enough after co-deletion.
    ext = rng.randint(1, 3)
    anchor = rng.randint(4, 8)
    half_slack = rng.randint(3, 8)
    probe = rng.randint(ext + 1, 4)
    gap = probe + 2 * half_slack
    future = ext + anchor + half_slack
    total_without_fill = 2 * ext + 2 * anchor + gap
    trench = 40 if total_without_fill <= 36 else 60
    fill_total = trench - total_without_fill
    left_fill = rng.randint(1, fill_total - 1)
    right_fill = fill_total - left_fill
    return {
        "seed": seed,
        "split": "train" if split_index < 12 else "holdout",
        "trench": trench,
        "left_fill": left_fill,
        "left_ext": ext,
        "left_anchor": anchor,
        "target_gap": gap,
        "right_anchor": anchor,
        "right_ext": ext,
        "right_fill": right_fill,
        "probe_length": probe,
        "future_length": future,
    }


cases = [make(seed, index) for index, seed in enumerate(range(20261001, 20261025))]
# Split by a fixed, preregistered seed boundary, not by observed outcome.
train = [case for case in cases if case["split"] == "train"]
holdout = [case for case in cases if case["split"] == "holdout"]
for group_name, group in (("train", train), ("holdout", holdout)):
    lines = []
    for case in group:
        lines.append(" ".join(str(case[key]) for key in (
            "seed", "trench", "left_fill", "left_ext", "left_anchor",
            "target_gap", "right_anchor", "right_ext", "right_fill",
            "probe_length", "future_length")))
    (OUT / f"{group_name}.tsv").write_text("\n".join(lines) + "\n", encoding="ascii")
keys = ["seed", "split", "trench", "left_fill", "left_ext", "left_anchor",
        "target_gap", "right_anchor", "right_ext", "right_fill",
        "probe_length", "future_length"]
(OUT / "manifest.json").write_text(json.dumps({
    "generator": "make_coalescence_cases.py",
    "seed_range": [20261001, 20261024],
    "split_rule": "first 12 train, next 12 holdout before evaluation",
    "keys": keys,
    "cases": [[case[key] for key in keys] for case in cases],
    "tsv": {"train": "train.tsv", "holdout": "holdout.tsv"},
}, separators=(",", ":")) + "\n", encoding="utf-8")
print(f"train={len(train)} holdout={len(holdout)} out={OUT}")
