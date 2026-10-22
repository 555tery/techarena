#!/usr/bin/env python3
"""Bounded replan search for compact early Open15 placements.

Reads the frozen release-v5 plan and Open15 inputs, pins a short causal
Best-Fit prefix for four selected cases, and rebuilds only in this directory.
For shared public prefixes, case 8 seeds case 13 and case 11 seeds case 15.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OVERFIT = REPO / "prototypes/pipes_open15_overfit_20261019"
CONT = OVERFIT / "continuation"
SOURCE = CONT / "release-v5/solution.cpp"
AUDIT = CONT / "release-v5/plan-audit.json"
CONDITIONED_CPP = CONT / "conditioned.cpp"
PROBE = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"

sys.path.insert(0, str(REPO / "prototypes"))
from pipes_open15_adversary_20261019.construct import decode  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_case(case: int) -> tuple[float, list[int]]:
    tokens = (REPO / f"data/pipes/open/{case}.in").read_text().split()
    weight, n = float(tokens[0]), int(tokens[1])
    return weight, list(map(int, tokens[2:2 + n]))


def allocations(commands: list[int]) -> list[tuple[int, int, int]]:
    """Return (pid, birth-command-index, length) for every positive command."""
    out, pid = [], 0
    for t, c in enumerate(commands):
        if c > 0:
            pid += 1
            out.append((pid, t, c))
    return out


def cutoff_for_k(commands: list[int], k: int) -> int:
    seen = 0
    for t, c in enumerate(commands):
        if c > 0:
            seen += 1
            if seen == k:
                return t + 1
    raise ValueError((len(commands), k))


def causal_bf_pins(case: int, commands: list[int], k: int) -> tuple[int, list[int]]:
    prefix = cutoff_for_k(commands, k)
    proc = subprocess.run(
        [str(PROBE), "bestfit", str(TAPE)],
        input="\n".join(map(str, commands[:prefix] + [0])) + "\n",
        text=True, capture_output=True, check=True, timeout=30,
    )
    lines = proc.stdout.splitlines()
    assert len(lines) == prefix, (case, prefix, len(lines))
    pins = []
    for cmd, line in zip(commands[:prefix], lines):
        if cmd > 0:
            dig, x = map(int, line.split())
            assert dig >= 0 and x >= 0
            pins.append(x)
    assert len(pins) == k
    return prefix, pins


def build_conditioned(binary: Path, case: int, commands: list[int], prefix: int,
                      pins: list[int], destination: Path) -> list[dict]:
    expected_pins = sum(1 for _, t, _ in allocations(commands) if t < prefix)
    assert len(pins) == expected_pins, (case, prefix, len(pins), expected_pins)
    case_dir = destination
    case_dir.mkdir(parents=True, exist_ok=True)
    pin_file = case_dir / "pins.txt"
    pin_file.write_text("\n".join(map(str, pins)) + "\n")
    input_file = REPO / f"data/pipes/open/{case}.in"
    rows = []
    for mode in range(4):
        plan = case_dir / f"mode{mode}.txt"
        log = case_dir / f"mode{mode}.log"
        result = subprocess.run(
            [str(binary), str(input_file), str(pin_file), str(prefix), str(plan), str(mode)],
            cwd=case_dir, text=True, capture_output=True, timeout=45,
        )
        log.write_text(result.stdout + result.stderr)
        rows.append({"case": case, "mode": mode, "returncode": result.returncode,
                     "T": int(result.stdout.split()[0]) if result.returncode == 0 and result.stdout.split() else None,
                     "positions": str(plan) if result.returncode == 0 else None,
                     "log": str(log)})
    return rows


def read_positions(path: Path, commands: list[int]) -> list[int]:
    values = list(map(int, path.read_text().split()))
    assert len(values) == sum(c > 0 for c in commands), (path, len(values))
    return values


def prefix_positions(plan: Path, commands: list[int], prefix: int) -> list[int]:
    vals = read_positions(plan, commands)
    return vals[:sum(1 for _, t, _ in allocations(commands) if t < prefix)]


def best(rows: list[dict], lower_t: int) -> dict | None:
    feasible = [r for r in rows if r["returncode"] == 0]
    return min(feasible, key=lambda r: (r["T"] != lower_t, r["T"], r["mode"])) if feasible else None


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    lower = {c["case"]: c["lower_T"] for c in audit["cases"]}
    tables = decode(SOURCE)
    assert sha(SOURCE) == audit["source_sha256"]
    assert len(tables) == 15

    compiler = subprocess.run(
        ["/usr/bin/clang++", "-std=c++17", "-O3", str(CONDITIONED_CPP), "-o", str(OUT / "geometry_conditioned")],
        cwd=OUT, text=True, capture_output=True, timeout=90,
    )
    (OUT / "geometry_compile.log").write_text(compiler.stdout + compiler.stderr)
    if compiler.returncode:
        raise RuntimeError("conditioned builder compilation failed")
    binary = OUT / "geometry_conditioned"

    result: dict = {
        "scope": "local conditioned-plan feasibility search only",
        "source_sha256": sha(SOURCE),
        "builder_source": str(CONDITIONED_CPP.relative_to(REPO)),
        "builder_sha256": sha(CONDITIONED_CPP),
        "input_sha256": {},
        "targets": {str(k): lower[k] for k in (8, 10, 11, 14)},
        "attempts": [],
        "shared_prefixes": {},
    }
    data: dict[int, list[int]] = {}
    for case in range(1, 16):
        _, data[case] = read_case(case)
        result["input_sha256"][str(case)] = sha(REPO / f"data/pipes/open/{case}.in")

    # First produce compact initial allocations, then rebuild each selected tail.
    selected = [(8, 2), (10, 3), (11, 2), (14, 8)]
    chosen: dict[int, dict] = {}
    for case, k in selected:
        prefix, pins = causal_bf_pins(case, data[case], k)
        rows = build_conditioned(binary, case, data[case], prefix, pins, OUT / f"case{case}_shortpin")
        pick = best(rows, lower[case])
        result["attempts"].append({"case": case, "pins": k, "prefix_commands": prefix,
                                   "pin_positions": pins, "target_T": lower[case], "modes": rows,
                                   "selected": pick})
        if pick:
            chosen[case] = pick

    # Public-prefix compatibility requires one shared plan for each pair.
    # Reuse the first case's candidate placements across the entire shared prefix.
    for a, b, prefix, n_pids in [(8, 13, 388, 210), (11, 15, 4999, 4006)]:
        item = {"cases": [a, b], "prefix_commands": prefix, "prefix_pids": n_pids}
        if a not in chosen:
            item["status"] = "no_feasible_seed_plan"
            result["shared_prefixes"][f"{a}_{b}"] = item
            continue
        seed = Path(chosen[a]["positions"])
        shared_pins = prefix_positions(seed, data[a], prefix)
        assert len(shared_pins) == n_pids
        assert data[a][:prefix] == data[b][:prefix]
        # Confirm that the candidate is valid on the shared prefix before reusing it.
        seed_cmds = data[a][:prefix]
        pos_iter = iter(shared_pins)
        live: dict[int, tuple[int, int]] = {}
        pid = 0
        for c in seed_cmds:
            if c > 0:
                pid += 1
                x = next(pos_iter)
                assert all(x + c <= ox or ox + ol <= x for ox, ol in live.values()), (a, pid, x, c)
                live[pid] = (x, c)
            else:
                live.pop(-c)
        assert not list(pos_iter)
        rows = build_conditioned(binary, b, data[b], prefix, shared_pins,
                                OUT / f"case{b}_shared_from_{a}")
        pick = best(rows, lower[b])
        item.update({"seed_case": a, "seed_plan": str(seed), "pin_positions_sha256": hashlib.sha256(
            ("\n".join(map(str, shared_pins)) + "\n").encode()).hexdigest(),
                    "modes": rows, "selected": pick})
        if pick:
            chosen[b] = pick
        result["shared_prefixes"][f"{a}_{b}"] = item

    result["summary"] = {
        str(case): {"target_T": lower[case], "selected_T": chosen.get(case, {}).get("T"),
                    "mode": chosen.get(case, {}).get("mode"),
                    "plan": chosen.get(case, {}).get("positions")}
        for case in (8, 10, 11, 13, 14, 15)
    }
    result["all_selected_cases_at_original_T"] = all(
        chosen.get(case, {}).get("T") == lower[case] for case in (8, 10, 11, 14, 13, 15)
    )
    (OUT / "geometry_replan.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    print("all_selected_cases_at_original_T", result["all_selected_cases_at_original_T"])


if __name__ == "__main__":
    main()
