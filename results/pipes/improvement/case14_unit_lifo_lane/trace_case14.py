#!/usr/bin/env python3
"""Reconstruct case14 free intervals at the final 50 baseline expansions."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path


def main() -> None:
    input_path = Path("data/pipes/open/14.in")
    output_path = Path(
        "results/pipes/improvement/archive_mix_screen/gated_causal/"
        "pid46-open15/runs/14/judge_output.txt"
    )
    input_lines = input_path.read_text().splitlines()
    output_lines = output_path.read_text().splitlines()
    _, command_count = map(int, input_lines[0].split())
    commands = list(map(int, input_lines[1:]))
    responses = [list(map(int, line.split())) for line in output_lines]
    if not commands or commands[-1] != 0:
        raise SystemExit("missing final zero sentinel")
    commands.pop()
    if len(commands) != command_count or len(responses) != command_count:
        raise SystemExit("command / response count mismatch")

    expansion_ops = {
        op for op, (command, response) in enumerate(zip(commands, responses), 1)
        if command > 0 and response[0] > 0
    }
    selected_ops = set(sorted(expansion_ops)[-50:])
    active: dict[int, tuple[int, int]] = {}
    live = trench = pid = alive = 0
    bit = [0] * (command_count + 2)
    recent_ranks: deque[int] = deque(maxlen=64)
    recent_placements: deque[int] = deque(maxlen=46)
    removals = 0
    first_single_unit_lifo_placement: int | None = None
    trace: list[dict[str, int]] = []

    def add(index: int, delta: int) -> None:
        while index < len(bit):
            bit[index] += delta
            index += index & -index

    def prefix(index: int) -> int:
        result = 0
        while index > 0:
            result += bit[index]
            index -= index & -index
        return result

    for op, (command, response) in enumerate(zip(commands, responses), 1):
        if command > 0:
            same_unit_run = command == 1 and len(recent_placements) == 46 and all(
                length == 1 for length in recent_placements
            )
            lifo_signal = len(recent_ranks) >= 32 and sum(
                rank <= 200 for rank in recent_ranks
            ) * 10 >= len(recent_ranks) * 9
            if same_unit_run and lifo_signal and first_single_unit_lifo_placement is None:
                first_single_unit_lifo_placement = op

            digs, start = response
            old_trench = trench
            if digs and op in selected_ops:
                gaps: list[tuple[int, int]] = []
                cursor = 0
                for gap_start, length in sorted(active.values()):
                    if gap_start > cursor:
                        gaps.append((cursor, gap_start - cursor))
                    cursor = gap_start + length
                if cursor < old_trench:
                    gaps.append((cursor, old_trench - cursor))
                tail = next(
                    ((gap_start, length) for gap_start, length in reversed(gaps)
                     if gap_start + length == old_trench),
                    None,
                )
                new_trench = old_trench + 20 * digs
                combined_tail_start = tail[0] if tail else old_trench
                internal = [length for start_gap, length in gaps
                            if start_gap + length < old_trench]
                trace.append({
                    "op": op,
                    "pipe_length": command,
                    "pid": pid + 1,
                    "dig_m": 20 * digs,
                    "trench_before_m": old_trench,
                    "trench_after_m": new_trench,
                    "live_before_m": live,
                    "live_after_m": live + command,
                    "lower_bound_after_m": ((live + command + 19) // 20) * 20,
                    "largest_internal_gap_before_m": max(internal, default=0),
                    "tail_gap_before_m": tail[1] if tail else 0,
                    "free_gap_count_before": len(gaps),
                    "combined_tail_after_dig_m": new_trench - combined_tail_start,
                    "chosen_start_m": start,
                    "recent_removal_count": len(recent_ranks),
                    "recent_lifo_rank_le_200": sum(rank <= 200 for rank in recent_ranks),
                })
            trench += 20 * digs
            pid += 1
            active[pid] = (start, command)
            live += command
            alive += 1
            add(pid, 1)
            recent_placements.append(command)
        elif command < 0:
            removed = -command
            start, length = active.pop(removed)
            newer = alive - prefix(removed)
            denominator = max(1, alive - 1)
            recent_ranks.append(newer * 1000 // denominator)
            removals += 1
            alive -= 1
            add(removed, -1)
            live -= length
        else:
            raise SystemExit(f"unexpected sentinel before end at operation {op}")

    artifact = {
        "case": 14,
        "command_count": command_count,
        "placements": pid,
        "removals": removals,
        "expansion_events": len(expansion_ops),
        "final_live_length_m": live,
        "final_trench_length_m": trench,
        "first_single_unit_lifo_placement_op": first_single_unit_lifo_placement,
        "last_50_expansions": trace,
    }
    out = Path("results/pipes/improvement/case14_unit_lifo_lane/trace_last50_baseline.json")
    out.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({k: v for k, v in artifact.items() if k != "last_50_expansions"}, indent=2))
    for event in trace[-10:]:
        print(event)


if __name__ == "__main__":
    main()

