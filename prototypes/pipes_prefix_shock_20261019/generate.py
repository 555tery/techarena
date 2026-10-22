#!/usr/bin/env python3
"""Fixed public-prefix counterexamples, with no solver search or platform use."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_after(commands):
    live = {}
    pid = 0
    for command in commands:
        if command > 0:
            pid += 1
            live[pid] = command
        else:
            del live[-command]
    return live


def main():
    source = REPO / "data/pipes/open/15.in"
    tokens = source.read_text().split()
    original = list(map(int, tokens[2:2 + int(tokens[1])]))
    old = REPO / "prototypes/pipes_open15_overfit_20261019"
    joint = json.loads((old / "joint.json").read_text())
    case = next(c for c in joint["cases"] if c["case"] == 15)
    assert case["commands"] == original
    positions = list(map(int, (old / "best-positions.txt").read_text().split()))
    short_n, long_n = 8192, 100000
    assert original[short_n] == -6567

    # Independent byte occupancy replay of the frozen plan's exact prefix.
    cells = bytearray()
    alive = {}
    next_pid = 0
    tape = []
    for command, block in zip(original[:long_n + 1], case["block_ids"]):
        if command > 0:
            pos = positions[block]
            end = pos + command
            trench = ((end + 19) // 20) * 20
            if trench > len(cells):
                cells.extend(b"\0" * (trench - len(cells)))
            assert not any(cells[pos:end])
            cells[pos:end] = b"\1" * command
            next_pid += 1
            alive[next_pid] = (pos, command)
        else:
            pos, length = alive.pop(-command)
            assert all(cells[pos:pos + length])
            cells[pos:pos + length] = b"\0" * length
        tape.append((command, pos))

    (HERE / "tape.txt").write_text(
        str(len(tape)) + "\n" + "".join(f"{c} {p}\n" for c, p in tape)
    )
    short_live = live_after(original[:short_n])
    assert 1 in short_live and 6567 in short_live
    replacement_pid = 1
    shock = original[:short_n] + [-replacement_pid]
    shock += [-pid for pid in sorted(short_live) if pid != replacement_pid]
    shock += [40] * 4000
    long_live = live_after(original[:long_n])
    drain = original[:long_n] + [-pid for pid in sorted(long_live)] + [1]
    tests = {
        "prefix-shock": (shock, short_n,
            "Different live PID at first divergent deletion; clear all pipes, then 4000 pipes of length 40."),
        "prefix-drain": (drain, long_n,
            "Delete every active PID, then insert one 1 m pipe; universally tiny raw KPI."),
        "prefix-control": (original[:short_n + 1], short_n + 1,
            "Unmodified public prefix; positive control for the stored placement tape."),
    }
    (HERE / "inputs").mkdir(exist_ok=True)
    rows = []
    for name, (commands, common, mechanism) in tests.items():
        path = HERE / "inputs" / (name + ".in")
        path.write_text(f"1\n{len(commands)}\n" + "\n".join(map(str, commands)) + "\n")
        meta = parse_test(path)
        actual_common = 0
        for expected, actual in zip(original, commands):
            if expected != actual:
                break
            actual_common += 1
        assert actual_common == common
        assert len(commands) <= 200000
        assert meta["final_occupied_length_m"] > 0
        rows.append({
            "name": name, "file": str(path.relative_to(REPO)),
            "shared_command_prefix_count": common,
            "first_divergent_operation_1based": common + 1 if common < len(commands) else None,
            "original_next_command": original[common] if common < len(original) else None,
            "new_next_command": commands[common] if common < len(commands) else None,
            "mechanism": mechanism, **meta,
        })
    manifest = {
        "purpose": "Authorized fixed test construction and local diagnostics only; no optimization campaign resumed.",
        "platform_actions": 0, "public_input": str(source.relative_to(REPO)),
        "public_input_sha256": sha(source),
        "frozen_plan": str((old / "best-positions.txt").relative_to(REPO)),
        "frozen_plan_sha256": sha(old / "best-positions.txt"),
        "joint_plan_sha256": sha(old / "joint.json"),
        "tape_sha256": sha(HERE / "tape.txt"),
        "tape_prefix_independent_byte_replay": "passed",
        "no_generalization_claim": True,
        "universal_overfit_discriminator_claim": False,
        "cases": rows,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
