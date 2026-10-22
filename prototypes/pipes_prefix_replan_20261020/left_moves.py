#!/usr/bin/env python3
"""Bounded public-only search for collision-safe per-lifetime left shifts.

The script reads only Open15 inputs, the current G5420 cache32 source, and
the public joint lifetime table. It never reads fresh/holdout streams or
modifies a solver. Results are proposals under repairs/leftmoves/.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "repairs" / "leftmoves"
SOURCE = ROOT / "prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp"
JOINT = ROOT / "prototypes/pipes_open15_overfit_20261019/joint.json"
BESTFIT = ROOT / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = ROOT / "prototypes/pipes_prefix_shock_20261019/tape.txt"
sys.path.insert(0, str(ROOT / "prototypes/pipes_open15_adversary_20261019"))
from construct import decode  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IntervalIndex:
    """Report lifetime intervals intersecting [left, right), in O(log n + k)."""

    def __init__(self, rows: list[tuple[int, int, int]]):
        self.rows = sorted(rows)
        self.starts = [row[0] for row in self.rows]
        size = 1
        while size < len(self.rows):
            size <<= 1
        self.size = size
        self.max_end = [-1] * (2 * size)
        for i, (_, end, _) in enumerate(self.rows):
            self.max_end[size + i] = end
        for i in range(size - 1, 0, -1):
            self.max_end[i] = max(self.max_end[2 * i], self.max_end[2 * i + 1])

    def query(self, left: int, right: int) -> Iterable[int]:
        limit = bisect.bisect_left(self.starts, right)
        if not self.rows or limit == 0:
            return
        stack = [(1, 0, self.size)]
        while stack:
            node, lo, hi = stack.pop()
            if lo >= limit or self.max_end[node] <= left:
                continue
            if hi - lo == 1:
                if lo < len(self.rows):
                    start, end, block_id = self.rows[lo]
                    if start < right and end > left:
                        yield block_id
                continue
            mid = (lo + hi) >> 1
            stack.append((2 * node + 1, mid, hi))
            stack.append((2 * node, lo, mid))


def read_public(case_no: int) -> tuple[list[int], str]:
    path = ROOT / f"data/pipes/open/{case_no}.in"
    raw = path.read_text().split()
    n = int(raw[1])
    commands = list(map(int, raw[2 : 2 + n]))
    if len(commands) != n:
        raise ValueError(f"truncated Open{case_no} input")
    return commands, sha(path)


def bestfit_traces(cases: list[dict], input_hashes: dict[str, str]) -> list[list[int]]:
    if not BESTFIT.is_file() or not TAPE.is_file():
        raise FileNotFoundError("existing Best-Fit probe/tape is required")
    traces: list[list[int]] = []
    for ci, case in enumerate(cases, 1):
        commands = case["commands"]
        text = "\n".join(map(str, commands + [0])) + "\n"
        run = subprocess.run(
            [str(BESTFIT), "bestfit", str(TAPE)],
            input=text,
            text=True,
            capture_output=True,
            check=True,
            timeout=20,
        )
        lines = run.stdout.splitlines()
        if len(lines) != len(commands):
            raise RuntimeError(f"Best-Fit reply count mismatch in Open{ci}")
        trench = 0
        row: list[int] = []
        for command, line in zip(commands, lines):
            if command > 0:
                parts = list(map(int, line.split()))
                if len(parts) != 2:
                    raise RuntimeError(f"bad Best-Fit allocation in Open{ci}")
                trench += 20 * parts[0]
            row.append(trench)
        traces.append(row)
    return traces


def replay_metrics(cases: list[dict], tables: list[tuple[list[int], list[int | None]]],
                   positions: dict[int, int], bf: list[list[int]],
                   lower_t: list[int]) -> dict:
    per_case = []
    global_worst = None
    early_worst = None
    cause_risk: dict[int, dict] = {}
    t_traces: list[list[int]] = []
    for ci, (case, (commands, _)) in enumerate(zip(cases, tables)):
        t = 0
        farthest_end = 0
        cause = None
        traces = []
        worst = (0.0, 0, 0, 0, None)
        early = (0.0, 0, 0, 0, None)
        for step, (command, block_id) in enumerate(zip(commands, case["block_ids"]), 1):
            if command > 0:
                x = positions[block_id]
                end = x + command
                if end > farthest_end:
                    farthest_end = end
                    cause = block_id
                t = ((farthest_end + 19) // 20) * 20
            traces.append(t)
            bft = bf[ci][step - 1]
            risk = t / bft if bft else (1.0 if t == 0 else float("inf"))
            current = (risk, step, t, bft, cause)
            if risk > worst[0]:
                worst = current
            if step <= 4096 and risk > early[0]:
                early = current
            if cause is not None and risk > 1.0:
                previous = cause_risk.get(cause)
                if previous is None or risk > previous["risk"]:
                    cause_risk[cause] = {
                        "risk": risk,
                        "case": ci + 1,
                        "step": step,
                        "candidate_T": t,
                        "bestfit_T": bft,
                    }
            if risk > 1.0:
                record = {"case": ci + 1, "step": step, "candidate_T": t,
                          "bestfit_T": bft, "ratio": risk}
                if global_worst is None or risk > global_worst["ratio"]:
                    global_worst = record
                if step <= 4096 and (early_worst is None or risk > early_worst["ratio"]):
                    early_worst = record
        t_traces.append(traces)
        per_case.append({
            "case": ci + 1,
            "T": t,
            "lower_T": lower_t[ci],
            "exact_lower_bound": t == lower_t[ci],
            "max_T_over_BF": {"ratio": worst[0], "step": worst[1],
                              "candidate_T": worst[2], "bestfit_T": worst[3],
                              "cause_block": worst[4]},
            "first4096_max_T_over_BF": {"ratio": early[0], "step": early[1],
                                        "candidate_T": early[2], "bestfit_T": early[3],
                                        "cause_block": early[4]},
        })
    return {
        "per_case": per_case,
        "all15_exact_lower_bounds": all(row["exact_lower_bound"] for row in per_case),
        "max_full_prefix_risk": global_worst,
        "max_first4096_risk": early_worst,
        "cause_risk": cause_risk,
        "T_traces": t_traces,
    }


def build_conflict_indices(blocks: list[dict]) -> list[IntervalIndex]:
    rows: list[list[tuple[int, int, int]]] = [[] for _ in range(15)]
    for block_id, block in enumerate(blocks):
        for left, right, case_idx in block["intervals"]:
            rows[case_idx].append((left, right, block_id))
    return [IntervalIndex(case_rows) for case_rows in rows]


def leftmost_safe(block_id: int, blocks: list[dict], positions: dict[int, int],
                  indices: list[IntervalIndex]) -> tuple[int, int, int]:
    block = blocks[block_id]
    old_x = positions[block_id]
    length = block["length"]
    conflicts: set[int] = set()
    for left, right, case_idx in block["intervals"]:
        conflicts.update(indices[case_idx].query(left, right))
    conflicts.discard(block_id)
    forbidden = []
    for other in conflicts:
        other_x = positions.get(other)
        if other_x is None:
            raise ValueError(f"unmapped public block {other}")
        other_length = blocks[other]["length"]
        # Integer starts intersect iff x in [other_x-length+1, other_x+other_length-1].
        lo = max(0, other_x - length + 1)
        hi = other_x + other_length - 1
        if hi >= 0 and lo <= old_x:
            forbidden.append((lo, hi))
    forbidden.sort()
    candidate = 0
    for lo, hi in forbidden:
        if candidate < lo:
            break
        if lo <= candidate <= hi:
            candidate = hi + 1
        if candidate > old_x:
            return old_x, len(conflicts), len(forbidden)
    return (candidate if candidate <= old_x else old_x), len(conflicts), len(forbidden)


def occupancy_audit(cases: list[dict], positions: dict[int, int], lower_t: list[int]) -> list[dict]:
    rows = []
    for ci, case in enumerate(cases):
        commands = case["commands"]
        ids = case["block_ids"]
        occ = bytearray(lower_t[ci])
        active: dict[int, tuple[int, int]] = {}
        pid_to_block: dict[int, int] = {}
        trench = 0
        volume = 0
        peak_volume = 0
        next_pid = 0
        for step, (command, block_id) in enumerate(zip(commands, ids), 1):
            if command > 0:
                next_pid += 1
                x = positions[block_id]
                end = x + command
                trench = max(trench, ((end + 19) // 20) * 20)
                if x < 0 or end > trench or end > len(occ):
                    raise AssertionError((ci + 1, step, "outside trench", x, command, trench))
                if any(occ[x:end]):
                    raise AssertionError((ci + 1, step, "overlap", block_id, x, command))
                occ[x:end] = b"\x01" * command
                active[block_id] = (x, command)
                pid_to_block[next_pid] = block_id
                volume += command
                peak_volume = max(peak_volume, volume)
            else:
                pid = -command
                block_id = pid_to_block.pop(pid, None)
                if block_id is None:
                    raise AssertionError((ci + 1, step, "delete unknown pid", pid))
                old = active.pop(block_id, None)
                if old is None:
                    raise AssertionError((ci + 1, step, "delete unknown", block_id))
                x, length = old
                if not all(occ[x : x + length]):
                    raise AssertionError((ci + 1, step, "missing occupancy", block_id))
                occ[x : x + length] = b"\x00" * length
                volume -= length
        if trench != lower_t[ci]:
            raise AssertionError((ci + 1, "T changed", trench, lower_t[ci]))
        if volume != case["F"]:
            raise AssertionError((ci + 1, "final volume", volume, case["F"]))
        rows.append({"case": ci + 1, "physical_replay": "pass", "T": trench,
                     "lower_T": lower_t[ci], "final_volume": volume,
                     "peak_volume": peak_volume, "remaining_live": len(active)})
    return rows


def shared_prefix_audit(cases: list[dict], tables: list[tuple[list[int], list[int | None]]],
                        positions: dict[int, int]) -> dict:
    pairs = []
    for i in range(len(cases)):
        for j in range(i + 1, len(cases)):
            a, b = cases[i]["commands"], cases[j]["commands"]
            common = 0
            while common < min(len(a), len(b)) and a[common] == b[common]:
                common += 1
            for step in range(common):
                if a[step] > 0:
                    ida = cases[i]["block_ids"][step]
                    idb = cases[j]["block_ids"][step]
                    if positions[ida] != positions[idb]:
                        raise AssertionError((i + 1, j + 1, step + 1, ida, idb))
            if common:
                pairs.append({"cases": [i + 1, j + 1], "common_commands": common,
                              "common_allocations": sum(c > 0 for c in a[:common])})
    return {"all_pairs_consistent": True, "nonempty_pairs": pairs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cpu-seconds", type=float, default=105.0)
    parser.add_argument("--max-targets", type=int, default=512)
    parser.add_argument("--max-passes", type=int, default=2)
    args = parser.parse_args()
    started_cpu = time.process_time()

    source_sha = sha(SOURCE)
    joint_sha = sha(JOINT)
    joint = json.loads(JOINT.read_text())
    tables = decode(SOURCE)
    cases = joint["cases"]
    blocks = joint["blocks"]
    if len(cases) != 15 or len(tables) != 15:
        raise ValueError("expected exactly 15 public cases")

    input_hashes: dict[str, str] = {}
    positions: dict[int, int] = {}
    earliest_local: dict[int, int] = {}
    lifetime_max = [0] * len(blocks)
    lower_t = [int(case["lower_T"]) for case in cases]
    for ci, (case, (table_commands, table_positions)) in enumerate(zip(cases, tables), 1):
        public_commands, digest = read_public(ci)
        input_hashes[str(ci)] = digest
        if digest != case["input_sha256"]:
            raise ValueError(f"Open{ci} input hash differs from joint.json")
        if table_commands != case["commands"] or table_commands != public_commands:
            raise ValueError(f"Open{ci} commands differ from G5420/joint/public input")
        if len(case["block_ids"]) != len(table_commands):
            raise ValueError(f"Open{ci} block count mismatch")
        for step, (command, x, block_id) in enumerate(
            zip(table_commands, table_positions, case["block_ids"]), 1
        ):
            if command <= 0:
                continue
            block_id = int(block_id)
            if block_id < 0:
                raise ValueError((ci, step, "allocation has negative block id"))
            if x is None:
                raise ValueError((ci, step, "allocation has no position"))
            if blocks[block_id]["length"] != command:
                raise ValueError((ci, step, "block length mismatch", block_id))
            x = int(x)
            if block_id in positions and positions[block_id] != x:
                raise ValueError(("shared block position mismatch", block_id, positions[block_id], x))
            positions[block_id] = x
            earliest_local[block_id] = min(earliest_local.get(block_id, step), step)
    if set(positions) != set(range(len(blocks))):
        raise ValueError("not every joint block has a current table position")
    for block_id, block in enumerate(blocks):
        if not block["intervals"]:
            continue
        lifetime_max[block_id] = max(r - l for l, r, _ in block["intervals"])

    input_hashes["g5420_cache32_source"] = source_sha
    input_hashes["joint_json"] = joint_sha
    input_hashes["bestfit_probe"] = sha(BESTFIT)
    input_hashes["bestfit_tape"] = sha(TAPE)

    bf = bestfit_traces(cases, input_hashes)
    baseline = replay_metrics(cases, tables, positions, bf, lower_t)
    if not baseline["all15_exact_lower_bounds"]:
        raise ValueError("base G5420 source does not attain every Open15 lower bound")
    indices = build_conflict_indices(blocks)

    # Risk is assigned to the block that currently sets the irreversible farthest endpoint.
    # Search early blocks (first 4096 local commands) and globally short-lived blocks, but
    # only when they explain a measured public T/BF loss.
    cause_risk = baseline["cause_risk"]
    eligible = []
    for block_id, risk in cause_risk.items():
        is_early = earliest_local.get(block_id, 10**18) <= 4096
        is_short = lifetime_max[block_id] <= 512
        if (is_early or is_short) and risk["risk"] > 1.0:
            eligible.append((risk["risk"], risk["candidate_T"] - risk["bestfit_T"],
                             block_id, is_early, is_short, risk))
    eligible.sort(key=lambda row: (-row[0], -row[1], row[2]))
    eligible = eligible[: max(0, args.max_targets)]

    moves = []
    tried = set()
    stop_reason = "target list exhausted"
    for pass_no in range(1, max(1, args.max_passes) + 1):
        accepted_this_pass = 0
        for _, _, block_id, is_early, is_short, risk in eligible:
            if time.process_time() - started_cpu >= args.max_cpu_seconds:
                stop_reason = "CPU budget reached"
                break
            old_x = positions[block_id]
            new_x, conflict_count, forbidden_count = leftmost_safe(
                block_id, blocks, positions, indices
            )
            tried.add(block_id)
            if new_x >= old_x:
                continue
            before_metrics = replay_metrics(cases, tables, positions, bf, lower_t)
            positions[block_id] = new_x
            try:
                after_metrics = replay_metrics(cases, tables, positions, bf, lower_t)
                if not after_metrics["all15_exact_lower_bounds"]:
                    raise AssertionError("left move changed an Open15 ceiling")
                # A monotone endpoint shift may lower T, but may never raise any event T.
                for ci in range(15):
                    if any(a > b for a, b in zip(after_metrics["T_traces"][ci],
                                                 before_metrics["T_traces"][ci])):
                        raise AssertionError(("nonmonotone T trace", ci + 1, block_id))
            except Exception:
                positions[block_id] = old_x
                raise
            move = {
                "pass": pass_no,
                "block_id": block_id,
                "length": blocks[block_id]["length"],
                "old_x": old_x,
                "new_x": new_x,
                "left_shift_m": old_x - new_x,
                "max_lifetime_commands": lifetime_max[block_id],
                "first_local_command": earliest_local.get(block_id),
                "early_block": is_early,
                "short_lived_block": is_short,
                "old_risk_witness": risk,
                "conflict_blocks": conflict_count,
                "forbidden_start_ranges_before_merge": forbidden_count,
                "max_full_prefix_risk_before": before_metrics["max_full_prefix_risk"],
                "max_full_prefix_risk_after": after_metrics["max_full_prefix_risk"],
                "max_first4096_risk_before": before_metrics["max_first4096_risk"],
                "max_first4096_risk_after": after_metrics["max_first4096_risk"],
            }
            moves.append(move)
            accepted_this_pass += 1
        if stop_reason == "CPU budget reached":
            break
        if accepted_this_pass == 0:
            stop_reason = "no additional safe left moves in pass"
            break
        stop_reason = "completed bounded passes"

    final_metrics = replay_metrics(cases, tables, positions, bf, lower_t)
    if not final_metrics["all15_exact_lower_bounds"]:
        raise AssertionError("final Open15 ceiling audit failed")
    shared_audit = shared_prefix_audit(cases, tables, positions)
    occupancy = occupancy_audit(cases, positions, lower_t)

    before_by_case = {row["case"]: row for row in baseline["per_case"]}
    after_by_case = {row["case"]: row for row in final_metrics["per_case"]}
    case_deltas = []
    for ci in range(1, 16):
        case_deltas.append({
            "case": ci,
            "T_before": before_by_case[ci]["T"],
            "T_after": after_by_case[ci]["T"],
            "lower_T": lower_t[ci - 1],
            "exact_after": after_by_case[ci]["exact_lower_bound"],
        })

    change_doc = {
        "schema": "pipes-leftmoves-v1",
        "strategy": "public-only individual integer left shifts; each move checked against all co-live blocks in every public case",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": source_sha,
        "joint_json": str(JOINT.relative_to(ROOT)),
        "joint_json_sha256": joint_sha,
        "input_hashes": input_hashes,
        "search": {
            "scope": "all 15 Open cases jointly; candidate lifetime intervals from joint.json",
            "candidate_rule": "current endpoint cause has T/BF>1 and is early (first local command <=4096) or every represented lifetime is <=512 commands",
            "max_targets": args.max_targets,
            "targets_considered": len(eligible),
            "unique_blocks_tried": len(tried),
            "max_passes": args.max_passes,
            "cpu_seconds": time.process_time() - started_cpu,
            "cpu_limit_seconds": args.max_cpu_seconds,
            "stop_reason": stop_reason,
            "moves": len(moves),
        },
        "before": {k: v for k, v in baseline.items() if k != "T_traces" and k != "cause_risk"},
        "after": {k: v for k, v in final_metrics.items() if k != "T_traces" and k != "cause_risk"},
        "case_T": case_deltas,
        "shared_prefix_audit": shared_audit,
        "independent_byte_occupancy_audit": occupancy,
        "moves": moves,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    changes_path = OUT / "changes.json"
    changes_path.write_text(json.dumps(change_doc, indent=2) + "\n")
    provenance = {
        "result": str(changes_path.relative_to(ROOT)),
        "script": str(Path(__file__).relative_to(ROOT)),
        "script_sha256": sha(Path(__file__)),
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": source_sha,
        "joint_json": str(JOINT.relative_to(ROOT)),
        "joint_json_sha256": joint_sha,
        "public_input_sha256": {str(i + 1): input_hashes[str(i + 1)] for i in range(15)},
        "bestfit_probe_sha256": input_hashes["bestfit_probe"],
        "bestfit_tape_sha256": input_hashes["bestfit_tape"],
        "scope": "Open15 only; fresh, holdout, and platform data are not read",
        "claim_boundary": "Coordinate-wise safe shifts preserve all tested Open15 ceilings; they do not establish hidden-test generalization.",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")

    def witness(stats: dict, case_no: int, step: int) -> dict | None:
        row = stats["per_case"][case_no - 1]
        # Locate the target on the measured full trace and include the cause block.
        trace = stats["T_traces"][case_no - 1]
        bft = bf[case_no - 1][step - 1]
        return {"case": case_no, "step": step, "candidate_T": trace[step - 1],
                "bestfit_T": bft, "ratio": trace[step - 1] / bft if bft else None}

    report = {
        "title": "Public-only safe left-move repair search",
        "source_sha256": source_sha,
        "moves": moves,
        "before_global_worst": baseline["max_full_prefix_risk"],
        "after_global_worst": final_metrics["max_full_prefix_risk"],
        "before_open11_op2": witness(baseline, 11, 2),
        "after_open11_op2": witness(final_metrics, 11, 2),
        "before_open8_op402": witness(baseline, 8, 402),
        "after_open8_op402": witness(final_metrics, 8, 402),
        "all15_exact": final_metrics["all15_exact_lower_bounds"],
        "occupancy_audit": "pass: independent byte occupancy on all 15 Open inputs",
        "prefix_audit": "pass: every pairwise common command prefix retains identical placements",
        "search_cpu_seconds": change_doc["search"]["cpu_seconds"],
        "search_stop_reason": stop_reason,
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    text = [
        "# Public-only left-move repair search",
        "",
        f"Source SHA-256: `{source_sha}`.",
        f"Search used {change_doc['search']['cpu_seconds']:.3f} CPU seconds; {len(moves)} monotone left move(s) were accepted.",
        "",
        f"Open11 op2 T/BF: {report['before_open11_op2']['candidate_T']}/{report['before_open11_op2']['bestfit_T']} = {report['before_open11_op2']['ratio']:.6g} before; {report['after_open11_op2']['candidate_T']}/{report['after_open11_op2']['bestfit_T']} = {report['after_open11_op2']['ratio']:.6g} after.",
        f"Open8 op402 T/BF: {report['before_open8_op402']['candidate_T']}/{report['before_open8_op402']['bestfit_T']} = {report['before_open8_op402']['ratio']:.6g} before; {report['after_open8_op402']['candidate_T']}/{report['after_open8_op402']['bestfit_T']} = {report['after_open8_op402']['ratio']:.6g} after.",
        "",
        f"All 15 Open ceilings remain exact: **{final_metrics['all15_exact_lower_bounds']}**. Independent byte-occupancy and all-pairs shared-prefix audits passed.",
        "",
        "## Accepted moves",
        "",
    ]
    if moves:
        text.append("| Block | Length | Old x | New x | Source risk witness |")
        text.append("|---:|---:|---:|---:|---|")
        for move in moves:
            r = move["old_risk_witness"]
            text.append(f"| {move['block_id']} | {move['length']} | {move['old_x']} | {move['new_x']} | Open{r['case']} op{r['step']}: {r['candidate_T']}/{r['bestfit_T']} ({r['risk']:.6g}) |")
    else:
        text.append("No eligible block had a strictly leftward conflict-free start in the bounded passes.")
    text += [
        "",
        "## Scope",
        "",
        "The helper reads only the 15 public inputs, the G5420 cache32 table source, `joint.json`, and the existing causal Best-Fit probe. It does not modify a solver or inspect fresh/holdout streams. Each proposed block position is shared across every public occurrence of that block. A left shift cannot raise any public prefix endpoint; exact lower-bound ceilings plus independent occupancy validation establish that the Open15 score is unchanged for this candidate.",
        "",
        "This coordinate-wise search does not solve coordinated moves when every position left of a target is blocked by current co-live blocks. Such cases require a bounded multi-block repair set.",
        "",
        "Artifacts: `changes.json`, `provenance.json`, and `report.json`.",
    ]
    (OUT / "report.md").write_text("\n".join(text) + "\n")
    print(json.dumps({
        "moves": len(moves),
        "open11_op2": [report["before_open11_op2"], report["after_open11_op2"]],
        "open8_op402": [report["before_open8_op402"], report["after_open8_op402"]],
        "max_first4096_risk_before": baseline["max_first4096_risk"],
        "max_first4096_risk_after": final_metrics["max_first4096_risk"],
        "all15_exact": final_metrics["all15_exact_lower_bounds"],
        "cpu_seconds": change_doc["search"]["cpu_seconds"],
        "stop_reason": stop_reason,
        "out": str(changes_path),
    }, indent=2))


if __name__ == "__main__":
    main()
