#!/usr/bin/env python3
"""Independent event-sweep verifier and report writer for case 11."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_case(path: Path):
    raw = list(map(int, path.read_text().split()))
    width, n = raw[:2]
    commands = raw[2 : 2 + n]
    if len(commands) != n:
        raise ValueError(f"{path}: expected {n} commands, got {len(commands)}")
    extra = raw[2 + n :]
    if extra not in ([], [0]):
        raise ValueError(f"{path}: unexpected trailing values {extra[:8]}")
    return width, n, commands, extra


def verify(input_path: Path, positions_path: Path):
    width, n, commands, extra = read_case(input_path)
    positions = list(map(int, positions_path.read_text().split()))
    lengths = [0]
    for c in commands:
        if c > 0:
            lengths.append(c)
    pipe_count = len(lengths) - 1
    if len(positions) != pipe_count:
        raise ValueError(f"position count {len(positions)} != pipe count {pipe_count}")
    if any(x < 0 for x in positions):
        raise ValueError("negative placement coordinate")

    # Active intervals are kept sorted by their spatial start. Since the live
    # set is known to be disjoint before each insertion, checking the adjacent
    # intervals suffices to detect every possible new overlap.
    occupied = []
    active_by_id = {}
    pid = 0
    live_volume = 0
    peak_volume = 0
    peak_at = []
    insertions = deletions = zero_commands = 0
    max_live_count = 0
    for t, c in enumerate(commands):
        if c < 0:
            q = -c
            if q not in active_by_id:
                raise ValueError(f"command {t}: deletion of inactive PID {q}")
            start, length = active_by_id.pop(q)
            idx = bisect.bisect_left(occupied, (start, q))
            if idx >= len(occupied) or occupied[idx] != (start, q):
                raise ValueError(f"command {t}: active index mismatch for PID {q}")
            occupied.pop(idx)
            live_volume -= length
            deletions += 1
        elif c > 0:
            pid += 1
            start = positions[pid - 1]
            end = start + c
            idx = bisect.bisect_left(occupied, (start, pid))
            if idx and occupied[idx - 1][0] + lengths[occupied[idx - 1][1]] > start:
                left_pid = occupied[idx - 1][1]
                raise ValueError(f"command {t}: PID {pid} overlaps active PID {left_pid}")
            if idx < len(occupied) and occupied[idx][0] < end:
                right_pid = occupied[idx][1]
                raise ValueError(f"command {t}: PID {pid} overlaps active PID {right_pid}")
            occupied.insert(idx, (start, pid))
            active_by_id[pid] = (start, c)
            live_volume += c
            insertions += 1
        else:
            zero_commands += 1
        if live_volume > peak_volume:
            peak_volume = live_volume
            peak_at = [t]
        elif live_volume == peak_volume:
            peak_at.append(t)
        max_live_count = max(max_live_count, len(active_by_id))
    if pid != pipe_count:
        raise ValueError(f"parsed {pid} insertions, expected {pipe_count}")
    extent = max((positions[i - 1] + lengths[i] for i in range(1, pipe_count + 1)), default=0)
    return {
        "input_path": str(input_path),
        "input_sha256": sha256(input_path),
        "positions_path": str(positions_path),
        "positions_sha256": sha256(positions_path),
        "width": width,
        "commands": n,
        "trailing_values": extra,
        "pipes": pipe_count,
        "insertions": insertions,
        "deletions": deletions,
        "zero_commands": zero_commands,
        "survivors": len(active_by_id),
        "max_live_count": max_live_count,
        "volume_lower_bound": peak_volume,
        "volume_peak_commands": peak_at,
        "extent": extent,
        "trench_score": 20 * ((extent + 19) // 20),
        "overlap_pairs_detected": 0,
        "deletion_errors": 0,
        "pid1": positions[0],
        "valid": True,
    }, positions, lengths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--positions", type=Path, required=True)
    ap.add_argument("--prefix-input", type=Path, required=True)
    ap.add_argument("--prefix-output", type=Path, required=True)
    ap.add_argument("--source-plan", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    report, positions, lengths = verify(args.input, args.positions)
    _, n15, cmds15, _ = read_case(args.prefix_input)
    _, n11, cmds11, _ = read_case(args.input)
    lcp = 0
    for a, b in zip(cmds11, cmds15):
        if a != b:
            break
        lcp += 1
    prefix_pipes = sum(c > 0 for c in cmds11[:lcp])
    prefix_values = positions[:prefix_pipes]
    args.prefix_output.write_text("".join(f"{x}\n" for x in prefix_values))

    report.update({
        "task": "Open15 test 11 offline placement plan",
        "method": "mode 1 reverse future-aware plan: final survivors in PID order, temporary pipes assigned while traversing the full command stream backward with best-fit gaps",
        "uses_future_deletions": True,
        "online_policy": False,
        "source_plan": str(args.source_plan),
        "source_plan_sha256": sha256(args.source_plan),
        "target_score": 20760,
        "target_reached": report["trench_score"] <= 20760,
        "volume_bound_score": 20 * ((report["volume_lower_bound"] + 19) // 20),
        "common_prefix": {
            "other_input": str(args.prefix_input),
            "other_input_sha256": sha256(args.prefix_input),
            "commands": lcp,
            "pipe_insertions": prefix_pipes,
            "first_mismatch_11": cmds11[lcp] if lcp < n11 else None,
            "first_mismatch_15": cmds15[lcp] if lcp < n15 else None,
            "pid_ordered_coordinates_path": str(args.prefix_output),
            "pid_ordered_coordinates_sha256": sha256(args.prefix_output),
            "coordinates_by_pid": prefix_values,
        },
        "search_notes": [
            "Five supplied future plans independently swept; mode 2 was best at 20820 but PID1 was not zero.",
            "Reverse greedy restarts capped at 20760 did not find a plan.",
            "A cut-at-peak greedy search at command 9818 did not find a plan in 10000 restarts.",
            "Bounded MILP repair of the upper 150 pipes reached the 90 second limit without a feasible incumbent; this is not an infeasibility proof.",
            "Fixed spatial-order repairs with 150 and 300 movable pipes were infeasible under that restricted ordering."
        ],
    })
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in (
        "valid", "pipes", "insertions", "deletions", "extent", "trench_score",
        "volume_lower_bound", "pid1", "target_reached", "overlap_pairs_detected",
    )}, indent=2))
    print(f"common_prefix_commands={lcp} pipe_insertions={prefix_pipes}")


if __name__ == "__main__":
    main()
