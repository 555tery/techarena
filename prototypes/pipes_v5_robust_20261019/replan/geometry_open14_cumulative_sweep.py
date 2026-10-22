#!/usr/bin/env python3
"""Bounded Open14 BF-pinned prefix sweep with full-stream risk metric."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from geometry_replan import OUT, PROBE, REPO, TAPE, build_conditioned, read_case, read_positions, sha

CASE = 14
BOUND = 37720
FIXED_PREFIXES = [512, 2048, 8192]


def probe(commands: list[int]) -> list[str]:
    p = subprocess.run(
        [str(PROBE), "bestfit", str(TAPE)],
        input="\n".join(map(str, commands + [0])) + "\n",
        text=True, capture_output=True, check=True, timeout=60,
    )
    rows = p.stdout.splitlines()
    assert len(rows) == len(commands), (len(rows), len(commands))
    return rows


def bf_trace(commands: list[int], rows: list[str]) -> list[int]:
    T, trace = 0, []
    for c, row in zip(commands, rows):
        if c > 0:
            dig, _x = map(int, row.split())
            T += 20 * dig
        trace.append(T)
    return trace


def target_trace(commands: list[int], positions: list[int]) -> tuple[list[int], int, int]:
    lengths = [c for c in commands if c > 0]
    assert len(lengths) == len(positions)
    max_endpoint = max((x + c for x, c in zip(positions, lengths)), default=0)
    occupied = bytearray(max_endpoint + 1)
    active: dict[int, tuple[int, int]] = {}
    T = pid = 0
    trace = []
    it = iter(positions)
    for t, c in enumerate(commands):
        if c > 0:
            pid += 1
            x = next(it)
            assert not any(occupied[x:x + c]), (t, pid, x, c)
            occupied[x:x + c] = b"\1" * c
            active[pid] = (x, c)
            T = max(T, 20 * ((x + c + 19) // 20))
        else:
            x, length = active.pop(-c)
            assert all(occupied[x:x + length])
            occupied[x:x + length] = b"\0" * length
        trace.append(T)
    assert not list(it)
    return trace, T, max_endpoint


def risk(commands: list[int], target: list[int], bf: list[int]) -> dict:
    ratios = [target[i] / bf[i] for i in range(len(commands)) if bf[i] > 0]
    value = max(ratios, default=1.0)
    peak = next(i for i in range(len(commands)) if bf[i] > 0 and target[i] / bf[i] == value)
    return {"max_ratio_all_commands": value,
            "peak_operation_1based": peak + 1,
            "peak_command": commands[peak],
            "peak_target_T_m": target[peak],
            "peak_bestfit_T_m": bf[peak],
            "operations_checked": len(commands)}


def main() -> None:
    _, commands = read_case(CASE)
    input_path = REPO / "data/pipes/open/14.in"
    rows = probe(commands)
    plain = bf_trace(commands, rows)
    max_plain = max(plain)
    first_over = next((i for i, T in enumerate(plain) if T > BOUND), None)
    longest_safe_prefix = first_over if first_over is not None else len(commands)
    prefixes = sorted(set(p for p in FIXED_PREFIXES + [longest_safe_prefix]
                          if 0 < p <= longest_safe_prefix))
    binary = OUT / "geometry_conditioned"
    assert binary.exists()

    results = []
    for prefix in prefixes:
        pins = [int(line.split()[1]) for c, line in zip(commands[:prefix], rows[:prefix]) if c > 0]
        case_dir = OUT / f"geometry_open14_cumulative_prefix_{prefix}"
        mode_rows = build_conditioned(binary, CASE, commands, prefix, pins, case_dir)
        audited = []
        for row in mode_rows:
            if row["returncode"] != 0:
                audited.append({**row, "valid_replay": False})
                continue
            plan = Path(row["positions"])
            positions = read_positions(plan, commands)
            tr, final_T, endpoint = target_trace(commands, positions)
            assert final_T == row["T"]
            audited.append({
                **row,
                "positions_sha256": sha(plan),
                "position_count": len(positions),
                "valid_replay": True,
                "observed_T": final_T,
                "exact_original_T": final_T == BOUND,
                "max_endpoint_m": endpoint,
                "full_risk": risk(commands, tr, plain),
            })
        results.append({
            "prefix_commands": prefix,
            "pinned_allocations": len(pins),
            "pins_sha256": hashlib.sha256(("\n".join(map(str, pins)) + "\n").encode()).hexdigest(),
            "first_pinned_positions_m": pins[:12],
            "modes": audited,
        })

    # Full-stream audit of the earlier p8-only replan for a direct comparison.
    prior = OUT / "geometry_open14_positions.txt"
    prior_positions = read_positions(prior, commands)
    prior_trace, prior_T, prior_endpoint = target_trace(commands, prior_positions)
    prior_risk = risk(commands, prior_trace, plain)

    exact = [(r["prefix_commands"], m) for r in results for m in r["modes"]
             if m.get("exact_original_T")]
    best = min(exact, key=lambda pair: (pair[1]["full_risk"]["max_ratio_all_commands"], -pair[0], pair[1]["mode"])) if exact else None
    chosen = None
    if best:
        prefix, row = best
        src = Path(row["positions"])
        dest = OUT / "geometry_open14_cumulative_best_positions.txt"
        shutil.copyfile(src, dest)
        chosen = {"prefix_commands": prefix, "mode": row["mode"], "T_m": row["observed_T"],
                  "positions_file": str(dest), "positions_sha256": sha(dest),
                  "position_count": row["position_count"], "max_endpoint_m": row["max_endpoint_m"],
                  "full_risk": row["full_risk"]}

    report = {
        "scope": "bounded Open14 conditioned-prefix sweep; files confined to replan/",
        "input_sha256": sha(input_path),
        "target_release_source_sha256": sha(OUT.parent.parent / "pipes_open15_overfit_20261019/continuation/release-v5/solution.cpp"),
        "input_commands": len(commands),
        "target_volume_bound_T_m": BOUND,
        "plain_bestfit_final_T_m": max_plain,
        "first_plain_BF_operation_over_target_bound": first_over + 1 if first_over is not None else None,
        "longest_prefix_before_plain_BF_crosses_bound": longest_safe_prefix,
        "tested_prefixes": results,
        "prior_p8_fix": {"positions_file": str(prior), "T_m": prior_T,
                         "max_endpoint_m": prior_endpoint, "full_risk": prior_risk},
        "best_exact_candidate": chosen,
        "improves_prior_full_risk": bool(chosen and chosen["full_risk"]["max_ratio_all_commands"] < prior_risk["max_ratio_all_commands"]),
        "selection_rule": "Among exact-T candidates, minimize max(T_target/T_plain_BF) over every original command; ties prefer longer pin prefix, then lower mode.",
    }
    (OUT / "geometry_open14_cumulative_sweep.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"plain_bestfit_final_T_m": max_plain,
                      "first_plain_BF_operation_over_target_bound": report["first_plain_BF_operation_over_target_bound"],
                      "longest_prefix_before_plain_BF_crosses_bound": longest_safe_prefix,
                      "prior_p8_fix": prior_risk,
                      "best_exact_candidate": chosen,
                      "improves_prior_full_risk": report["improves_prior_full_risk"],
                      "per_prefix": {str(r["prefix_commands"]): [(m["mode"], m.get("observed_T"), m.get("full_risk", {}).get("max_ratio_all_commands")) for m in r["modes"]] for r in results}}, indent=2))


if __name__ == "__main__":
    main()
