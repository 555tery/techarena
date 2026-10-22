#!/usr/bin/env python3
"""Check one hand-constructed short regret example; no input sweep is run."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from exact_oracle import solve


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[3]
FROZEN = ROOT / "results/pipes/final/solution.cpp"
FROZEN_BIN = WORK / "frozen_final"
EXPECTED_FROZEN_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
COMMANDS = (6, 7, -1, 8)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def simulate_replies(commands: tuple[int, ...], replies: list[int]) -> dict[str, object]:
    cursor = 0
    trench = 0
    active: dict[int, tuple[int, int]] = {}
    pid = 0
    actions = []
    for command_index, command in enumerate(commands, 1):
        if command > 0:
            digs, start = replies[cursor : cursor + 2]
            cursor += 2
            assert digs >= 0 and start >= 0
            trench += 20 * digs
            end = start + command
            assert end <= trench
            for other_pid, (other_start, other_length) in active.items():
                assert start + command <= other_start or other_start + other_length <= start
            pid += 1
            active[pid] = (start, command)
            actions.append({"command_index_1based": command_index, "pid": pid,
                            "length_m": command, "digs_sections": digs,
                            "start_m": start, "trench_after_m": trench})
        else:
            printed_start = replies[cursor]
            cursor += 1
            target = -command
            assert target in active
            expected_start, _ = active.pop(target)
            assert printed_start == expected_start
    assert cursor == len(replies)
    return {"final_trench_m": trench, "terminal_active": active, "actions": actions}


def validate_witness(commands: tuple[int, ...], oracle_result: dict[str, object]) -> None:
    actions = oracle_result["witness"]
    by_command = {action["command_index_1based"]: action for action in actions}
    trench = 0
    active: dict[int, tuple[int, int]] = {}
    pid = 0
    for command_index, command in enumerate(commands, 1):
        if command > 0:
            action = by_command[command_index]
            pid += 1
            assert action["pid"] == pid
            start = action["start_m"]
            digs = action["digs_sections"]
            assert trench + 20 * digs == action["trench_after_m"]
            trench += 20 * digs
            end = start + command
            assert end <= trench
            for other_start, other_length in active.values():
                assert end <= other_start or other_start + other_length <= start
            active[pid] = (start, command)
        else:
            del active[-command]
    assert trench == oracle_result["minimum_final_trench_m"]


def main() -> int:
    if sha256(FROZEN) != EXPECTED_FROZEN_SHA:
        raise SystemExit("frozen source SHA mismatch")
    if not FROZEN_BIN.exists():
        raise SystemExit(f"compile frozen solver first: {FROZEN_BIN}")

    oracle = solve(COMMANDS)
    validate_witness(COMMANDS, oracle)
    proc = subprocess.run(
        [str(FROZEN_BIN)],
        input="\n".join(map(str, COMMANDS + (0,))) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    replies = [int(token) for token in proc.stdout.split()]
    frozen = simulate_replies(COMMANDS, replies)
    lower_bound = 20
    result = {
        "scope": "one manually constructed stream; not a mass search",
        "commands": list(COMMANDS),
        "frozen_source_sha256": sha256(FROZEN),
        "frozen_binary_sha256": sha256(FROZEN_BIN),
        "frozen_reply_tokens": replies,
        "frozen_simulation": frozen,
        "exact_oracle": oracle,
        "peak_live_length_lower_bound_m": lower_bound,
        "frozen_regret_m": frozen["final_trench_m"] - oracle["minimum_final_trench_m"],
    }
    if oracle["minimum_final_trench_m"] != lower_bound:
        raise AssertionError("the proposed exact witness did not reach the volume lower bound")
    if frozen["final_trench_m"] <= oracle["minimum_final_trench_m"]:
        raise AssertionError("the proposed stream is not a frozen-final counterexample")
    output = WORK / "prototype_candidate_result.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"saved {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
