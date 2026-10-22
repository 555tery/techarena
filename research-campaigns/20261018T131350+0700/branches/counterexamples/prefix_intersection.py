#!/usr/bin/env python3
"""Exhaustively test shared optimal-prefix states for a short synthetic pair.

This is a diagnostic only. It asks whether one legal allocator state after the
identical observed prefix can be continued to each suffix's already-proven
offline optimum. An empty intersection is a pair-specific online impossibility
certificate; a nonempty intersection disproves that claim for this pair.
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

from bounded_oracle import DIG, ROOT, replay_output

sys.path.insert(0, str(ROOT / "shinka-pipes" / "search-v3-1"))
from usage_guard import gate  # noqa: E402


def live_lengths(commands: list[int]) -> list[int]:
    return [c for c in commands if c > 0]


def pid_slots(commands: list[int]) -> list[int]:
    slots = []
    count = 0
    for command in commands:
        if command > 0:
            slots.append(count)
            count += 1
        else:
            slots.append(-1)
    return slots


def overlaps(start: int, length: int, state: tuple[int, ...], lengths: list[int]) -> bool:
    return any(other >= 0 and start < other + lengths[pid] and
               other < start + length for pid, other in enumerate(state))


def enumerate_prefix(commands: list[int], prefix_n: int, max_trench: int) -> set[tuple[int, tuple[int, ...]]]:
    lengths = live_lengths(commands)
    slots = pid_slots(commands)
    initial = tuple([-1] * len(lengths))
    states: set[tuple[int, tuple[int, ...]]] = set()
    seen: set[tuple[int, int, tuple[int, ...]]] = set()

    def visit(index: int, trench: int, state: tuple[int, ...]) -> None:
        if trench > max_trench:
            return
        key = (index, trench, state)
        if key in seen:
            return
        seen.add(key)
        if index == prefix_n:
            states.add((trench, state))
            return
        command = commands[index]
        if command < 0:
            pid = -command - 1
            if pid >= len(state) or state[pid] < 0:
                raise ValueError(f"invalid prefix deletion {command} at {index}")
            updated = list(state)
            updated[pid] = -1
            visit(index + 1, trench, tuple(updated))
            return
        pid = slots[index]
        for new_trench in range(trench, max_trench + 1, DIG):
            max_start = new_trench - command
            for start in range(max_start + 1):
                if overlaps(start, command, state, lengths):
                    continue
                updated = list(state)
                updated[pid] = start
                visit(index + 1, new_trench, tuple(updated))

    visit(0, 0, initial)
    return states


def can_finish(commands: list[int], prefix_n: int, prefix_state: tuple[int, tuple[int, ...]],
               target: int) -> bool:
    lengths = live_lengths(commands)
    slots = pid_slots(commands)
    initial_trench, initial_state = prefix_state
    if initial_trench > target:
        return False

    @lru_cache(maxsize=None)
    def visit(index: int, trench: int, state: tuple[int, ...]) -> bool:
        if trench > target:
            return False
        if index == len(commands):
            return True
        command = commands[index]
        if command < 0:
            pid = -command - 1
            if pid >= len(state) or state[pid] < 0:
                raise ValueError(f"invalid suffix deletion {command} at {index}")
            updated = list(state)
            updated[pid] = -1
            return visit(index + 1, trench, tuple(updated))
        pid = slots[index]
        for new_trench in range(trench, target + 1, DIG):
            max_start = new_trench - command
            for start in range(max_start + 1):
                if overlaps(start, command, state, lengths):
                    continue
                updated = list(state)
                updated[pid] = start
                if visit(index + 1, new_trench, tuple(updated)):
                    return True
        return False

    return visit(prefix_n, initial_trench, initial_state)


def suffix_witness(commands: list[int], prefix_n: int,
                   prefix_state: tuple[int, tuple[int, ...]], target: int) -> list[str] | None:
    """Return one exact response suffix if the given prefix state can hit target."""
    lengths = live_lengths(commands)
    slots = pid_slots(commands)
    initial_trench, initial_state = prefix_state

    @lru_cache(maxsize=None)
    def visit(index: int, trench: int, state: tuple[int, ...]) -> tuple[str, ...] | None:
        if trench > target:
            return None
        if index == len(commands):
            return ()
        command = commands[index]
        if command < 0:
            pid = -command - 1
            if pid >= len(state) or state[pid] < 0:
                raise ValueError(f"invalid suffix deletion {command} at {index}")
            updated = list(state)
            deleted_start = updated[pid]
            updated[pid] = -1
            rest = visit(index + 1, trench, tuple(updated))
            return None if rest is None else (str(deleted_start), *rest)
        pid = slots[index]
        for new_trench in range(trench, target + 1, DIG):
            max_start = new_trench - command
            for start in range(max_start + 1):
                if overlaps(start, command, state, lengths):
                    continue
                updated = list(state)
                updated[pid] = start
                rest = visit(index + 1, new_trench, tuple(updated))
                if rest is not None:
                    return (f"{(new_trench - trench) // DIG} {start}", *rest)
        return None

    result = visit(prefix_n, initial_trench, initial_state)
    return None if result is None else list(result)


def analyze(pair_path: Path, report_path: Path, pair_id: str,
            baseline_eval_dir: Path | None = None) -> dict:
    suite = json.loads(pair_path.read_text())
    report = json.loads(report_path.read_text())
    result_rows = {r["name"]: r for r in report["rows"]}
    selected = [r for r in suite["traces"] if r.get("pair_id") == pair_id]
    if len(selected) != 2:
        raise ValueError(f"expected exactly two cases for {pair_id}, got {len(selected)}")
    for row in selected:
        exact = result_rows[row["name"]]
        if exact["status"] != "optimal" or not exact["optimality_proven"]:
            raise ValueError(f"{row['name']} has no proven exact optimum")
    common_n = selected[0]["shared_prefix_through_decision"]
    if any(row["shared_prefix_through_decision"] != common_n or
           row["commands"][:common_n] != selected[0]["commands"][:common_n]
           for row in selected):
        raise ValueError("pair does not have the declared identical observed prefix")
    prefix = selected[0]["commands"][:common_n]
    if not all(row["commands"][:common_n] == prefix for row in selected):
        raise AssertionError("prefix check failed")
    targets = {row["name"]: result_rows[row["name"]]["best_feasible_trench_m"]
               for row in selected}
    cap = min(targets.values())
    states = enumerate_prefix(selected[0]["commands"], common_n, cap)
    reachability: dict[str, set[tuple[int, tuple[int, ...]]]] = {}
    for row in selected:
        reachability[row["name"]] = {
            state for state in states
            if can_finish(row["commands"], common_n, state, targets[row["name"]])
        }
    common = set.intersection(*reachability.values()) if reachability else set()
    baseline_states = {}
    if baseline_eval_dir is not None:
        for row in selected:
            output_path = baseline_eval_dir / "harness" / "runs" / row["name"] / "judge_output.txt"
            if not output_path.exists():
                raise FileNotFoundError(output_path)
            prefix_run = replay_output(prefix, "\n".join(output_path.read_text().splitlines()[:common_n]))
            full_pid_count = len(live_lengths(row["commands"]))
            starts = prefix_run.starts + [-1] * (full_pid_count - len(prefix_run.starts))
            state = (prefix_run.trench, tuple(starts))
            baseline_states[row["name"]] = {
                "trench_m": state[0],
                "active_pid_starts": [x if x >= 0 else None for x in state[1]],
                "state_is_legal_within_prefix_cap": state in states,
                "can_reach_each_proven_optimum_from_this_state": {
                    target_row["name"]: can_finish(
                        target_row["commands"], common_n, state,
                        targets[target_row["name"]]
                    ) for target_row in selected
                },
                "one_exact_suffix_witness_per_proven_optimum": {
                    target_row["name"]: suffix_witness(
                        target_row["commands"], common_n, state,
                        targets[target_row["name"]]
                    ) for target_row in selected
                },
            }
    return {
        "pair_id": pair_id,
        "diagnostic_only": True,
        "prefix_commands": prefix,
        "prefix_command_count": common_n,
        "proven_global_offline_optima_m": targets,
        "prefix_state_cap_m": cap,
        "legal_prefix_states_enumerated": len(states),
        "prefix_states_reaching_each_suffix_optimum": {
            name: len(rows) for name, rows in reachability.items()
        },
        "states_reaching_both_optima": len(common),
        "baseline_prefix_states_by_suffix": baseline_states,
        "pair_specific_conclusion": (
            "No single deterministic online state after this identical prefix can attain both proven suffix optima."
            if not common else
            "At least one common prefix state attains both optima; this pair does not establish an online impossibility."
        ),
        "scope_limit": (
            "This conclusion concerns only the listed finite synthetic pair and its shared command prefix; "
            "it says nothing about the probability of either suffix or generalization to contest inputs."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-suite", type=Path, required=True)
    parser.add_argument("--oracle-report", type=Path, required=True)
    parser.add_argument("--pair-id", required=True)
    parser.add_argument("--baseline-eval-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    gate(ROOT / "research-campaigns" / "20261018T131350+0700", max_age_seconds=60)
    result = analyze(args.pair_suite, args.oracle_report, args.pair_id,
                     args.baseline_eval_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
