#!/usr/bin/env python3
"""Read-only ordinal-rank summary for the public case-15 input."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "data/pipes/open/15.in"
OUT = Path(__file__).resolve().parent / "rank-segments.json"


def main() -> None:
    tokens = INPUT.read_text().split()
    weight, count = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError("unexpected input shape")

    size = count + 2
    bit = [0] * size
    latest_pid = 0
    active_count = 0
    birth_op = [0] * size
    pipe_length = [0] * size
    recent_ranks: list[tuple[float, int, int, int]] = []
    windows: list[dict] = []
    current: dict | None = None

    def add(index: int, delta: int) -> None:
        while index < size:
            bit[index] += delta
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        while index > 0:
            total += bit[index]
            index -= index & -index
        return total

    def new_window(start: int) -> dict:
        return {
            "start_op": start,
            "end_op": min(count, start + 9999),
            "deletions": 0,
            "deleted_length_le7": 0,
            "deleted_length_ge8": 0,
            "relative_rank_sum": 0.0,
            "relative_rank_le05": 0,
            "relative_rank_gt75": 0,
            "relative_rank_gt95": 0,
            "deleted_birth_pid_sum": 0,
            "deleted_birth_age_ops_sum": 0,
            "birth_cohort_counts_20k": [0] * 7,
        }

    def rank_summary(items: list[tuple[float, int, int, int]]) -> dict:
        if not items:
            return {"count": 0}
        n = len(items)
        return {
            "count": n,
            "mean_relative_rank_from_newest": sum(x[0] for x in items) / n,
            "fraction_newest_5pct": sum(x[0] <= .05 for x in items) / n,
            "fraction_oldest_25pct": sum(x[0] > .75 for x in items) / n,
            "fraction_oldest_5pct": sum(x[0] > .95 for x in items) / n,
        }

    for op, command in enumerate(commands[:-1], start=1):
        slot = (op - 1) // 10_000
        if current is None or slot != (current["start_op"] - 1) // 10_000:
            if current is not None:
                windows.append(current)
            current = new_window((slot * 10_000) + 1)
        if command > 0:
            latest_pid += 1
            active_count += 1
            birth_op[latest_pid] = op
            pipe_length[latest_pid] = command
            add(latest_pid, 1)
        elif command < 0:
            pid = -command
            if pid <= 0 or pid > latest_pid or prefix(pid) == prefix(pid - 1):
                raise RuntimeError(f"invalid deletion at op {op}")
            rank = active_count - prefix(pid) + 1
            relative_rank = (rank - 1) / max(1, active_count)
            length = pipe_length[pid]
            age = op - birth_op[pid]
            item = (relative_rank, pid, length, age)
            recent_ranks.append(item)
            if len(recent_ranks) > 64:
                recent_ranks.pop(0)
            c = current
            c["deletions"] += 1
            c["deleted_length_le7"] += length <= 7
            c["deleted_length_ge8"] += length >= 8
            c["relative_rank_sum"] += relative_rank
            c["relative_rank_le05"] += relative_rank <= .05
            c["relative_rank_gt75"] += relative_rank > .75
            c["relative_rank_gt95"] += relative_rank > .95
            c["deleted_birth_pid_sum"] += pid
            c["deleted_birth_age_ops_sum"] += age
            c["birth_cohort_counts_20k"][min(6, (pid - 1) // 20_000)] += 1
            add(pid, -1)
            active_count -= 1
        if op % 10_000 == 0:
            current["active_at_window_end"] = active_count
            current["latest_pid_at_window_end"] = latest_pid
            current["last_64_deletions_rank"] = rank_summary(recent_ranks)
            if current["deletions"]:
                n = current["deletions"]
                current["mean_relative_rank_from_newest"] = current["relative_rank_sum"] / n
                current["fraction_newest_5pct"] = current["relative_rank_le05"] / n
                current["fraction_oldest_25pct"] = current["relative_rank_gt75"] / n
                current["fraction_oldest_5pct"] = current["relative_rank_gt95"] / n
                current["mean_deleted_birth_pid"] = current["deleted_birth_pid_sum"] / n
                current["mean_deleted_birth_age_ops"] = current["deleted_birth_age_ops_sum"] / n
    if current is not None:
        windows.append(current)

    result = {
        "input": str(INPUT),
        "weight": weight,
        "operations": count,
        "placement_count": latest_pid,
        "window_size_ops": 10_000,
        "rank_definition": "rank among currently active PIDs, newest=0.0 and oldest approaching 1.0",
        "birth_cohort_definition": "fixed PID intervals of 20,000, diagnostics only",
        "windows": windows,
        "scope": "read-only public Open15 case-15 input trace; values must not become solver fingerprints",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
