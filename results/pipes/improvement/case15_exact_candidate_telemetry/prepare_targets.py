#!/usr/bin/env python3
"""Build exact gap/placement targets up to each gap's first later expansion."""
from __future__ import annotations

import bisect
import csv
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
GEOMETRY = HERE / "geometry"
INPUT = ROOT / "data/pipes/open/15.in"
BASELINE_ANSWER = ROOT / "results/pipes/improvement/generator_audit/cost_runs/runs/15/judge_output.txt"
OUTPUT = HERE / "targets.tsv"


def main() -> None:
    words = INPUT.read_text().split()
    n = int(words[1])
    commands = list(map(int, words[2 : 2 + n]))
    if len(commands) != n:
        raise RuntimeError("case 15 input format changed")
    answer = list(map(int, BASELINE_ANSWER.read_text().split()))
    answer_at = 0
    expansion_ops = []
    for op, command in enumerate(commands, 1):
        if command > 0:
            digs = answer[answer_at]
            answer_at += 2
            if digs > 0:
                expansion_ops.append(op)
        else:
            answer_at += 1
    if answer_at != len(answer):
        raise RuntimeError("frozen answer does not match input operation count")

    placement_ops_by_length: dict[int, list[int]] = defaultdict(list)
    for op, command in enumerate(commands, 1):
        if command > 0:
            placement_ops_by_length[command].append(op)

    with (GEOMETRY / "gap_episodes.csv").open(newline="") as f:
        episodes = list(csv.DictReader(f))
    expansion_ops.sort()

    target_rows: list[tuple[int, int, int, int, int, int, int, int]] = []
    relevant_episode_count = 0
    for episode in episodes:
        birth = int(episode["birth_op"])
        end = int(episode["end_op"])
        length = int(episode["length"])
        expansion_index = bisect.bisect_right(expansion_ops, birth)
        if expansion_index == len(expansion_ops):
            continue
        first_expansion = expansion_ops[expansion_index]
        if first_expansion > end:
            continue
        relevant_episode_count += 1

        for request, ops in placement_ops_by_length.items():
            if request > length:
                continue
            lo = bisect.bisect_right(ops, birth)
            hi = bisect.bisect_left(ops, first_expansion)
            for op in ops[lo:hi]:
                target_rows.append((
                    op, int(episode["id"]), int(episode["start"]),
                    int(episode["end"]), length, birth, request, first_expansion,
                ))

    target_rows.sort()
    with OUTPUT.open("w") as f:
        for row in target_rows:
            f.write(" ".join(map(str, row)) + "\n")

    unique_ops = {row[0] for row in target_rows}
    print(
        f"Target lineage: {relevant_episode_count} intervals; "
        f"{len(target_rows)} interval-placement pairs; "
        f"{len(unique_ops)} unique placement operations."
    )


if __name__ == "__main__":
    main()
