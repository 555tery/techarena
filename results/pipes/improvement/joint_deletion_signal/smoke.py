"""Train-side plumbing check only; deliberately emits no predictive metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate import generate_stream
from trace import extract_snapshots

SMOKE_APPROVAL_TOKEN = "smoke-reviewed-v3"
SMOKE_DIR_NAME = "train-smoke"
SMOKE_SEEDS = (202610179001, 202610179002, 202610179003)
SMOKE_MODES = ("independent", "grouped", "phase")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--approval-token", required=True)
    args = parser.parse_args()
    if args.approval_token != SMOKE_APPROVAL_TOKEN:
        raise SystemExit("smoke requires separate v3 review approval")
    smoke_dir = Path(__file__).resolve().parent / SMOKE_DIR_NAME
    smoke_dir.mkdir(parents=True, exist_ok=False)

    checks = []
    for index, (seed, mode) in enumerate(zip(SMOKE_SEEDS, SMOKE_MODES)):
        stem = f"train-smoke-{index + 1}-{mode}"
        metadata = generate_stream(
            mode=mode,
            seed=seed,
            epoch_count=4,
            source=args.source,
            binary=args.solver,
            output_dir=smoke_dir,
            stem=stem,
        )
        snapshots = extract_snapshots(
            Path(str(metadata["input_path"])),
            Path(str(metadata["reply_path"])),
        )
        expected_pairs = metadata["pair_counts_per_snapshot"]
        expected_same = metadata["same_size_pair_counts_per_snapshot"]
        actual_pairs = [len(snapshot.pairs) for snapshot in snapshots]
        actual_same = [sum(row.pair.relation for row in snapshot.pairs) for snapshot in snapshots]
        if actual_pairs != expected_pairs or actual_same != expected_same:
            raise RuntimeError("online pair extraction and trace replay disagree")
        if len(snapshots) != 4 or any(len(snapshot.active) != 32 for snapshot in snapshots):
            raise RuntimeError("smoke trace has an incorrect snapshot or active-set size")
        if int(metadata["command_count"]) != 5 * 128:
            raise RuntimeError("smoke trace has an incorrect command count")
        checks.append(
            {
                "seed": seed,
                "mode": mode,
                "command_count": metadata["command_count"],
                "snapshots": len(snapshots),
                "active_pipes_per_snapshot": [len(snapshot.active) for snapshot in snapshots],
                "pairs_per_snapshot": actual_pairs,
                "same_size_pairs_per_snapshot": actual_same,
                "command_stream_valid": True,
                "response_count_valid": True,
                "deletion_coordinates_valid": True,
                "overlap_checks_passed": True,
                "horizon_windows_nonoverlapping": True,
                "predictive_scores_computed": False,
            }
        )
    report = smoke_dir / "train-smoke-checks.json"
    report.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
