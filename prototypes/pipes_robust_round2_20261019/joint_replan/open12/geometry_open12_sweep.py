#!/usr/bin/env python3
"""Causal Best-Fit-pinned Open12 prefix sweep against frozen candidate-v3."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = REPO / "prototypes/pipes_v5_robust_20261019/candidate-v3/solution.cpp"
CONDITIONED_CPP = REPO / "prototypes/pipes_open15_overfit_20261019/continuation/conditioned.cpp"
PROBE = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"
INPUT = REPO / "data/pipes/open/12.in"
BOUND = 10260
PREFIXES_FIXED = [32, 128, 512, 1024]
sys.path.insert(0, str(REPO / "prototypes/pipes_open15_adversary_20261019"))
from construct import decode  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_commands(path: Path) -> list[int]:
    t = list(map(int, path.read_text().split()))
    return t[2:2 + t[1]]


def run_probe(commands: list[int]) -> list[str]:
    p = subprocess.run([str(PROBE), "bestfit", str(TAPE)],
                       input="\n".join(map(str, commands + [0])) + "\n",
                       text=True, capture_output=True, check=True, timeout=60)
    lines = p.stdout.splitlines()
    assert len(lines) == len(commands), (len(lines), len(commands))
    return lines


def bf_positions(commands: list[int], lines: list[str]) -> list[int]:
    return [int(line.split()[1]) for c, line in zip(commands, lines) if c > 0]


def bf_trace(commands: list[int], lines: list[str]) -> list[int]:
    t, trace = 0, []
    for c, line in zip(commands, lines):
        if c > 0:
            digs, _ = map(int, line.split())
            t += 20 * digs
        trace.append(t)
    return trace


def physical_check(commands: list[int], positions: list[int]) -> tuple[list[int], dict]:
    lengths = [c for c in commands if c > 0]
    assert len(lengths) == len(positions)
    max_endpoint = max((x + c for x, c in zip(positions, lengths)), default=0)
    occupied = bytearray(max_endpoint + 1)
    active: dict[int, tuple[int, int]] = {}
    trace, T, pid, cursor = [], 0, 0, 0
    peak_live = peak_live_at = live = 0
    for ti, c in enumerate(commands, 1):
        if c > 0:
            pid += 1
            x = positions[cursor]
            cursor += 1
            assert x >= 0 and x + c <= len(occupied), (ti, pid, x, c)
            assert not any(occupied[x:x+c]), ("overlap", ti, pid, x, c)
            occupied[x:x+c] = b"\1" * c
            active[pid] = (x, c)
            live += c
            if live > peak_live:
                peak_live, peak_live_at = live, ti
            T = max(T, 20 * ((x + c + 19) // 20))
        else:
            assert -c in active, ("invalid delete", ti, -c)
            x, n = active.pop(-c)
            assert all(occupied[x:x+n]), ("delete from unoccupied", ti, -c, x, n)
            occupied[x:x+n] = b"\0" * n
            live -= n
        trace.append(T)
    assert cursor == len(positions)
    return trace, {"valid": True, "allocations": cursor, "remaining_live_pipes": len(active),
                   "peak_live_volume": peak_live, "peak_live_at_command_1based": peak_live_at,
                   "peak_endpoint_m": max_endpoint, "final_T_m": T}


def common_prefix_audit(tables, candidate_positions: list[int], commands: list[int]) -> dict:
    rows = []
    for case, (other, other_pos) in enumerate(tables, 1):
        if case == 12:
            continue
        k = 0
        while k < min(len(commands), len(other)) and commands[k] == other[k]:
            k += 1
        nalloc = sum(c > 0 for c in commands[:k])
        old12 = [p for c, p in zip(tables[11][0], tables[11][1]) if c > 0]
        if nalloc:
            ok = candidate_positions[:nalloc] == old12[:nalloc]
        else:
            ok = True
        rows.append({"other_case": case, "shared_commands": k,
                     "shared_allocations": nalloc, "candidate_v3_prefix_positions_preserved": ok,
                     "first_divergence_open12": commands[k:k+1],
                     "first_divergence_other": other[k:k+1]})
    return {"all_15_cases_checked": True,
            "all_other_cases_compatible_through_their_exact_command_prefix": all(r["candidate_v3_prefix_positions_preserved"] for r in rows),
            "pairs": rows}


def main() -> None:
    tables = decode(SOURCE)
    commands = read_commands(INPUT)
    assert tables[11][0] == commands
    candidate_positions = [p for c, p in zip(*tables[11]) if c > 0]
    assert len(candidate_positions) == sum(c > 0 for c in commands)
    source_audit = json.loads((SOURCE.parent.parent / "candidate-v3-plan-audit.json").read_text())
    current_T = next(x["T"] for x in source_audit if x["case"] == 12)
    assert current_T == BOUND

    compile_result = subprocess.run(["/usr/bin/clang++", "-std=c++17", "-O3", str(CONDITIONED_CPP),
                                     "-o", str(OUT / "geometry_conditioned")],
                                    cwd=OUT, text=True, capture_output=True, timeout=60)
    (OUT / "geometry_compile.log").write_text(compile_result.stdout + compile_result.stderr)
    if compile_result.returncode:
        raise RuntimeError("conditioned builder compilation failed")
    binary = OUT / "geometry_conditioned"

    bf_lines = run_probe(commands)
    bf = bf_trace(commands, bf_lines)
    first_over = next((i for i, x in enumerate(bf) if x > BOUND), None)
    longest_safe = first_over if first_over is not None else len(commands)
    prefixes = sorted(set(p for p in PREFIXES_FIXED + [longest_safe] if 0 < p <= longest_safe))

    attempts = []
    for prefix in prefixes:
        pins = bf_positions(commands[:prefix], bf_lines[:prefix])
        assert len(pins) == sum(c > 0 for c in commands[:prefix])
        pfile = OUT / f"geometry_open12_prefix_{prefix}_pins.txt"
        pfile.write_text("\n".join(map(str, pins)) + "\n")
        modes = []
        for mode in range(4):
            plan = OUT / f"geometry_open12_prefix_{prefix}_mode{mode}_positions.txt"
            proc = subprocess.run([str(binary), str(INPUT), str(pfile), str(prefix), str(plan), str(mode)],
                                  cwd=OUT, text=True, capture_output=True, timeout=30)
            log = OUT / f"geometry_open12_prefix_{prefix}_mode{mode}.log"
            log.write_text(proc.stdout + proc.stderr)
            if proc.returncode != 0:
                modes.append({"mode": mode, "returncode": proc.returncode,
                              "builder_output": proc.stdout.strip(), "positions_path": None})
                continue
            positions = list(map(int, plan.read_text().split()))
            trace, physical = physical_check(commands, positions)
            ratios = [trace[i] / bf[i] for i in range(len(commands)) if bf[i] > 0]
            ratio = max(ratios, default=1.0)
            peak_i = next(i for i in range(len(commands)) if bf[i] > 0 and trace[i] / bf[i] == ratio)
            modes.append({"mode": mode, "returncode": 0, "builder_T_m": int(proc.stdout.split()[0]),
                          "physical_T_m": physical["final_T_m"], "exact_bound_T": physical["final_T_m"] == BOUND,
                          "physical_check": physical, "positions_file": plan.name,
                          "positions_sha256": sha(plan), "position_count": len(positions),
                          "pinned_positions_match": positions[:len(pins)] == pins,
                          "pinned_positions_sha256": sha(pfile),
                          "all_1501_command_max_ratio_target_over_BF": ratio,
                          "ratio_peak_command_1based": peak_i + 1,
                          "ratio_peak_target_T_m": trace[peak_i], "ratio_peak_BF_T_m": bf[peak_i]})
        attempts.append({"prefix_commands": prefix, "pinned_allocations": len(pins),
                         "pins_file": pfile.name, "pins_sha256": sha(pfile),
                         "pins_first_12": pins[:12], "bf_T_at_prefix": bf[prefix-1], "modes": modes})

    exact = [(a["prefix_commands"], m) for a in attempts for m in a["modes"] if m.get("exact_bound_T")]
    best_prefix = max((p for p, _ in exact), default=None)
    pool = [m for p, m in exact if p == best_prefix]
    best = min(pool, key=lambda m: (m["all_1501_command_max_ratio_target_over_BF"], m["mode"])) if pool else None
    common = common_prefix_audit(tables, candidate_positions, commands)
    if best:
        src = OUT / best["positions_file"]
        dst = OUT / "geometry_open12_best_positions.txt"
        dst.write_bytes(src.read_bytes())
        pos = list(map(int, dst.read_text().split()))
        (OUT / "geometry_open12_best_pid_positions.tsv").write_text(
            "pid\tstart_m\n" + "".join(f"{i+1}\t{x}\n" for i, x in enumerate(pos)))
        changes = [(i + 1, old, new) for i, (old, new) in enumerate(zip(candidate_positions, pos)) if old != new]
        best = {**best, "positions_file": dst.name, "positions_sha256": sha(dst),
                "pid_positions_file": "geometry_open12_best_pid_positions.tsv",
                "changed_allocations_vs_candidate_v3": len(changes),
                "max_abs_position_delta_m": max((abs(old - new) for _, old, new in changes), default=0),
                "first_20_changed_pid_positions": changes[:20]}
    cand_trace, cand_physical = physical_check(commands, candidate_positions)
    report = {"scope": "bounded causal Best-Fit prefix replan for Open12 only; no target or platform changes",
              "candidate_v3_source_sha256": sha(SOURCE), "open12_input_sha256": sha(INPUT),
              "conditioned_builder_source_sha256": sha(CONDITIONED_CPP), "target_final_T_m": BOUND,
              "current_candidate_v3": {"T_m": cand_physical["final_T_m"],
                                       "max_ratio_all_1501_commands": max((x/y for x,y in zip(cand_trace,bf) if y>0), default=1.0),
                                       "physical_check": cand_physical},
              "plain_bestfit_final_T_m": max(bf), "first_BF_command_where_T_exceeds_bound_1based": first_over + 1 if first_over is not None else None,
              "longest_BF_safe_prefix_commands": longest_safe, "tested_prefixes_commands": prefixes,
              "attempts": attempts, "max_prefix_with_exact_original_T_commands": best_prefix,
              "selected_exact_plan": best, "sharedprefix_with_current_v3_all15": common,
              "selection_rule": "Keep exact T=10260; choose the longest tested causal-BF-pinned command prefix, then minimize max T_target/T_plain_BF over all 1501 commands.",
              "physical_check_method": "Independent Python bytearray occupancy replay with overlap rejection and exact PID deletion checks."}
    (OUT / "geometry_open12_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"plain_BF_final_T": max(bf), "first_BF_over_bound": report["first_BF_command_where_T_exceeds_bound_1based"],
                      "prefixes": {str(a["prefix_commands"]): [(m["mode"], m.get("physical_T_m"), m.get("all_1501_command_max_ratio_target_over_BF")) for m in a["modes"]] for a in attempts},
                      "selected": best, "sharedprefix": {"all_compatible": common["all_other_cases_compatible_through_their_exact_command_prefix"],
                                                            "counts": [(x["other_case"], x["shared_commands"], x["shared_allocations"]) for x in common["pairs"]]}}, indent=2))


if __name__ == "__main__":
    main()
