#!/usr/bin/env python3
"""Open10 BF-pinned prefix sweep with exact-T and cumulative early-ratio audit."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from geometry_replan import (
    OUT, PROBE, REPO, TAPE, build_conditioned, read_case, read_positions, sha,
)

PREFIXES = [8, 32, 128, 512, 2048, 5383]
CASE = 10
LOWER_T = 15380


def probe(commands: list[int]) -> list[str]:
    proc = subprocess.run(
        [str(PROBE), "bestfit", str(TAPE)],
        input="\n".join(map(str, commands + [0])) + "\n",
        text=True, capture_output=True, check=True, timeout=60,
    )
    lines = proc.stdout.splitlines()
    assert len(lines) == len(commands), (len(lines), len(commands))
    return lines


def simulate_positions(commands: list[int], positions: list[int]) -> tuple[list[int], int]:
    need = max((x + c for x, c in zip(positions, [c for c in commands if c > 0])), default=0)
    occupied = bytearray(need + 1)
    active: dict[int, tuple[int, int]] = {}
    pid = 0
    T = 0
    trace = []
    it = iter(positions)
    for t, command in enumerate(commands):
        if command > 0:
            pid += 1
            x = next(it)
            assert x >= 0 and x + command <= len(occupied)
            assert not any(occupied[x:x + command]), (t, pid, x, command)
            occupied[x:x + command] = b"\1" * command
            active[pid] = (x, command)
            T = max(T, 20 * ((x + command + 19) // 20))
        else:
            x, length = active.pop(-command)
            assert all(occupied[x:x + length])
            occupied[x:x + length] = b"\0" * length
        trace.append(T)
    assert not list(it)
    return trace, T


def bestfit_trace(commands: list[int], lines: list[str]) -> list[int]:
    T = 0
    trace = []
    for command, line in zip(commands, lines):
        if command > 0:
            digs, _x = map(int, line.split())
            T += 20 * digs
        trace.append(T)
    return trace


def main() -> None:
    _, commands = read_case(CASE)
    input_path = REPO / "data/pipes/open/10.in"
    bf_lines = probe(commands)
    bf_trace = bestfit_trace(commands, bf_lines)
    assert max(bf_trace) == 18460, max(bf_trace)

    results: list[dict] = []
    binary = OUT / "geometry_conditioned"
    assert binary.exists()
    for prefix in PREFIXES:
        count = sum(c > 0 for c in commands[:prefix])
        pins = [int(line.split()[1]) for c, line in zip(commands[:prefix], bf_lines[:prefix]) if c > 0]
        assert len(pins) == count
        case_dir = OUT / f"geometry_open10_prefix_{prefix}"
        modes = build_conditioned(binary, CASE, commands, prefix, pins, case_dir)
        rows = []
        for mode_row in modes:
            if mode_row["returncode"] != 0:
                rows.append({**mode_row, "valid_replay": False})
                continue
            plan = Path(mode_row["positions"])
            positions = read_positions(plan, commands)
            target_trace, observed_T = simulate_positions(commands, positions)
            assert observed_T == mode_row["T"]
            horizon = min(250, prefix + 10)
            ratios = [target_trace[j] / bf_trace[j] for j in range(horizon) if bf_trace[j] > 0]
            max_ratio = max(ratios, default=1.0)
            max_idx = next(j + 1 for j in range(horizon)
                           if bf_trace[j] > 0 and target_trace[j] / bf_trace[j] == max_ratio)
            rows.append({
                **mode_row,
                "positions_sha256": sha(plan),
                "position_count": len(positions),
                "valid_replay": True,
                "observed_T": observed_T,
                "exact_original_T": observed_T == LOWER_T,
                "early_horizon_operations": horizon,
                "early_max_cumulative_ratio": max_ratio,
                "ratio_peak_operation_1based": max_idx,
                "ratio_peak_target_T_m": target_trace[max_idx - 1],
                "ratio_peak_bestfit_T_m": bf_trace[max_idx - 1],
                "T_at_early_horizon_m": target_trace[horizon - 1],
            })
        results.append({
            "prefix_commands": prefix,
            "pinned_allocations": count,
            "pinned_positions_sha256": hashlib.sha256(("\n".join(map(str, pins)) + "\n").encode()).hexdigest(),
            "pinned_first_positions_m": pins[:min(12, len(pins))],
            "early_horizon_operations": min(250, prefix + 10),
            "modes": rows,
        })

    exact = [(r["prefix_commands"], m) for r in results for m in r["modes"]
             if m.get("exact_original_T")]
    max_exact_prefix = max((p for p, _ in exact), default=None)
    best_candidates = [m for p, m in exact if p == max_exact_prefix]
    best_candidate = min(best_candidates, key=lambda m: (m["early_max_cumulative_ratio"], m["mode"])) if best_candidates else None
    if best_candidate:
        source = Path(best_candidate["positions"])
        dest = OUT / "geometry_open10_prefix_best_positions.txt"
        dest.write_bytes(source.read_bytes())
        best_candidate = {**best_candidate, "positions": str(dest), "positions_sha256": sha(dest)}

    prior = OUT / "geometry_open10_positions.txt"
    prior_positions = read_positions(prior, commands)
    prior_trace, prior_T = simulate_positions(commands, prior_positions)
    prior_horizon = min(250, 8 + 10)
    prior_ratios = [prior_trace[j] / bf_trace[j] for j in range(prior_horizon) if bf_trace[j] > 0]

    report = {
        "scope": "bounded Open10 prefix-length sweep; no edits outside replan",
        "input_sha256": sha(input_path),
        "target_release_source_sha256": sha(OUT.parent.parent / "pipes_open15_overfit_20261019/continuation/release-v5/solution.cpp"),
        "original_volume_bound_T_m": LOWER_T,
        "plain_bestfit_final_T_m": max(bf_trace),
        "prefixes": results,
        "max_prefix_with_exact_original_T": max_exact_prefix,
        "best_exact_variant_at_max_prefix": best_candidate,
        "prior_p3_fix": {
            "positions_file": str(prior), "final_T_m": prior_T,
            "early_horizon_operations": prior_horizon,
            "early_max_cumulative_ratio": max(prior_ratios, default=1.0),
        },
        "selection_rule": "Among tested prefixes that retain T=15380, choose the longest prefix; among its modes minimize max(T_target/T_plain_BF) over operations 1..min(250,prefix+10).",
    }
    (OUT / "geometry_open10_prefix_sweep.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "max_prefix_with_exact_original_T": max_exact_prefix,
        "best_exact_variant_at_max_prefix": best_candidate,
        "plain_bestfit_final_T_m": max(bf_trace),
        "prior_p3_fix": report["prior_p3_fix"],
        "per_prefix": {str(r["prefix_commands"]): [(m["mode"], m.get("observed_T"), m.get("early_max_cumulative_ratio")) for m in r["modes"]] for r in results},
    }, indent=2))


if __name__ == "__main__":
    main()
