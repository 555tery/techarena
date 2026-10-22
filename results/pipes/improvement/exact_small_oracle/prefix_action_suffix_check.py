#!/usr/bin/env python3
"""Exhaustively compare second-pipe starts for the fixed +6,+7 prefix only."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path


WORK = Path(__file__).resolve().parent
STEP = 20
PREFIX_TOTAL_LENGTH = 6 + 7
STARTS = tuple(range(6, 14))


def ceil20(value: int) -> int:
    return ((value + STEP - 1) // STEP) * STEP


def suffixes_without_new_pipe() -> list[tuple[int, ...]]:
    result: set[tuple[int, ...]] = {()}
    for mask in range(4):
        deletes = tuple(-pid for bit, pid in ((1, 1), (2, 2)) if mask & bit)
        result.update(set(itertools.permutations(deletes)))
    return sorted(result)


def suffixes_with_one_new_pipe(length: int) -> list[tuple[int, ...]]:
    result: set[tuple[int, ...]] = set()
    for mask in range(4):
        earlier_deletes = tuple(-pid for bit, pid in ((1, 1), (2, 2)) if mask & bit)
        for remove_new in (False, True):
            events = (length,) + earlier_deletes + ((-3,) if remove_new else ())
            for order in set(itertools.permutations(events)):
                if -3 in order and order.index(-3) < order.index(length):
                    continue
                result.add(order)
    return sorted(result)


def legal_suffixes() -> list[tuple[int, ...]]:
    result = suffixes_without_new_pipe()
    # The prefix has already placed lengths 6 and 7; the class total is at most 40.
    for length in range(1, 40 - PREFIX_TOTAL_LENGTH + 1):
        result.extend(suffixes_with_one_new_pipe(length))
    return result


def exact_final_for_fixed_prefix(second_start: int, suffix: tuple[int, ...]) -> int:
    """Naively enumerate every legal coordinate for the sole suffix placement."""
    assert second_start in STARTS
    future_total = sum(value for value in suffix if value > 0)
    # The prefix coordinates are fixed and already reach T=20. Appending all
    # future placements at the current trench end is a feasible completion,
    # even when this fixed prefix cannot attain the global sum-length bound.
    coordinate_bound = ceil20(20 + future_total)
    # Prefix is fixed: PID1 [0,6), PID2 [second_start, second_start+7), T=20.
    initial_active = {1: (0, 6), 2: (second_start, 7)}
    initial = (20, initial_active, 2)

    def visit(index: int, trench: int, active: dict[int, tuple[int, int]], pid: int) -> int:
        if index == len(suffix):
            return trench
        command = suffix[index]
        if command < 0:
            target = -command
            assert target in active
            rest = dict(active)
            del rest[target]
            return visit(index + 1, trench, rest, pid)

        length = command
        new_pid = pid + 1
        best = coordinate_bound + STEP
        for start in range(coordinate_bound - length + 1):
            end = start + length
            if any(start < other_start + other_length and other_start < end
                   for other_start, other_length in active.values()):
                continue
            next_trench = ceil20(max(trench, end))
            extended = dict(active)
            extended[new_pid] = (start, length)
            best = min(best, visit(index + 1, next_trench, extended, new_pid))
        assert best <= coordinate_bound
        return best

    return visit(0, *initial)


def main() -> int:
    cases = legal_suffixes()
    if len(cases) != len(set(cases)):
        raise AssertionError("suffix generator emitted duplicates")

    rows = []
    per_start = {start: Counter() for start in STARTS}
    for suffix in cases:
        outcomes = {
            start: exact_final_for_fixed_prefix(start, suffix)
            for start in STARTS
        }
        for start, trench in outcomes.items():
            per_start[start][trench] += 1
        rows.append({"suffix": list(suffix), "final_trench_by_second_start_m": {
            str(start): outcomes[start] for start in STARTS
        }})

    start6_vs_start13 = {"x13_better": 0, "equal": 0, "x13_worse": 0, "examples": {}}
    x13_dominates = True
    pairwise = {str(start): {"x13_better": 0, "equal": 0, "x13_worse": 0}
                for start in STARTS if start != 13}
    for row in rows:
        outcomes = {int(start): trench for start, trench
                    in row["final_trench_by_second_start_m"].items()}
        a, b = outcomes[6], outcomes[13]
        if b < a:
            key = "x13_better"
        elif b == a:
            key = "equal"
        else:
            key = "x13_worse"
            x13_dominates = False
        start6_vs_start13[key] += 1
        start6_vs_start13["examples"].setdefault(key, row["suffix"])
        for start_text in pairwise:
            start = int(start_text)
            x, y = outcomes[start], outcomes[13]
            pairwise[start_text]["x13_better" if y < x else "equal" if y == x else "x13_worse"] += 1
            if y > x:
                x13_dominates = False

    requested = {
        "plus_7_no_delete": (7,),
        "delete_pid1_then_plus_8": (-1, 8),
        "delete_pid1_then_plus_13": (-1, 13),
        "delete_pid2_then_plus_14": (-2, 14),
    }
    requested_outcomes = {}
    row_by_suffix = {tuple(row["suffix"]): row for row in rows}
    for label, suffix in requested.items():
        requested_outcomes[label] = row_by_suffix[suffix]["final_trench_by_second_start_m"]

    result = {
        "scope": "fixed prefix +6,+7; PID1 is fixed at [0,6); only the second placement coordinate varies",
        "prefix_state": {
            "trench_m": 20,
            "pid1": {"start_m": 0, "length_m": 6},
            "pid2_length_m": 7,
            "candidate_pid2_starts_m": list(STARTS),
            "request_history_before_pid2": [6],
        },
        "continuation_class": {
            "at_most_one_remaining_positive_placement": True,
            "remaining_positive_lengths_checked_m": list(range(1, 28)),
            "valid_deletions_of_existing_pids": [1, 2],
            "optional_delete_of_new_pid": True,
            "max_total_placement_length_m": 40,
            "suffix_orderings_checked": len(cases),
            "exact_coordinate_evaluations": len(cases) * len(STARTS),
            "suffixes": rows,
        },
        "final_trench_counts_by_second_start_m": {
            str(start): {str(trench): count for trench, count in sorted(counts.items())}
            for start, counts in per_start.items()
        },
        "start13_vs_start6": start6_vs_start13,
        "start13_vs_intermediate_starts": pairwise,
        "start13_weakly_dominates_all_gap_starts_for_this_class": x13_dominates,
        "requested_suffix_examples": requested_outcomes,
        "interpretation": "A weakly dominating right-edge choice is an online-feasible action for this one observed state and this bounded continuation class; it is not a general Pipes policy claim.",
    }
    out = WORK / "prefix_action_suffix_result.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("continuation_class", "requested_suffix_examples")}, indent=2))
    print(json.dumps({"requested_suffix_examples": requested_outcomes}, indent=2))
    print(f"saved {out.relative_to(WORK.parents[3])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
