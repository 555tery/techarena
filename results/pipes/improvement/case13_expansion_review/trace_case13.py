#!/usr/bin/env python3
"""Reconstruct Pipe placements, live volume, and all trench expansions for case 13."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()

    input_lines = args.input.read_text().splitlines()
    output_lines = args.output.read_text().splitlines()
    _, command_count = map(int, input_lines[0].split())
    commands = list(map(int, input_lines[1:]))
    responses = [list(map(int, row.split())) for row in output_lines]
    if not commands or commands[-1] != 0:
        raise SystemExit("missing final zero sentinel")
    commands.pop()
    if len(commands) != command_count or len(responses) != command_count:
        raise SystemExit(f"count mismatch: commands={len(commands)} responses={len(responses)}")

    active: dict[int, tuple[int, int]] = {}
    pid = 0
    live = 0
    peak_live = 0
    trench = 0
    expansions: list[dict[str, int]] = []

    for ordinal, (command, response) in enumerate(zip(commands, responses), start=1):
        if command > 0:
            if len(response) != 2:
                raise SystemExit(f"placement response arity at command {ordinal}")
            digs, start = response
            if digs < 0:
                raise SystemExit(f"invalid dig-section count at command {ordinal}: {digs}")
            before_trench = trench
            before_live = live
            trench += digs * 20
            pid += 1
            end = start + command
            if start < 0 or end > trench:
                raise SystemExit(f"placement outside trench at command {ordinal}")
            for other_pid, (other_start, other_length) in active.items():
                if max(start, other_start) < min(end, other_start + other_length):
                    raise SystemExit(f"overlap at command {ordinal} with pid {other_pid}")
            active[pid] = (start, command)
            live += command
            peak_live = max(peak_live, live)
            if digs:
                expansions.append({
                    "ordinal": ordinal, "pid": pid, "pipe_length": command,
                    "dig_sections": digs, "trench_before": before_trench,
                    "trench_after": trench, "live_before": before_live,
                    "live_after": live, "peak_live_after": peak_live,
                    "lb_before": ((before_live + 19) // 20) * 20,
                    "lb_after": ((live + 19) // 20) * 20,
                    "start": start,
                })
        elif command < 0:
            if len(response) != 1:
                raise SystemExit(f"removal response arity at command {ordinal}")
            removed = -command
            expected = active.pop(removed, None)
            if expected is None:
                raise SystemExit(f"remove inactive pid {removed} at command {ordinal}")
            if response[0] != expected[0]:
                raise SystemExit(f"wrong removal coordinate at command {ordinal}")
            live -= expected[1]
        else:
            raise SystemExit(f"unexpected final sentinel at command {ordinal}")

    with args.csv.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(expansions[0]))
        writer.writeheader()
        writer.writerows(expansions)
    print(f"commands={command_count} placements={pid} expansions={len(expansions)}")
    print(f"peak_live={peak_live} lower_bound={((peak_live + 19) // 20) * 20} final_trench={trench}")
    print("last expansions:")
    for event in expansions[-12:]:
        print(" ".join(f"{key}={value}" for key, value in event.items()))


if __name__ == "__main__":
    main()
