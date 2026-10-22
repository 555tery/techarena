#!/usr/bin/env python3
"""Exact bounded allocator oracle for short, synthetic command traces.

The oracle enumerates every integer placement coordinate and every permitted
20 m trench extension up to a feasible incumbent. It proves an optimum only
when the entire search below that incumbent is exhausted. State/time caps yield
"unknown", never an optimality claim. This is an offline diagnostic only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CAMPAIGN = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parents[4]
USAGE_GUARD = ROOT / "shinka-pipes" / "search-v3-1"
sys.path.insert(0, str(USAGE_GUARD))
from usage_guard import gate  # noqa: E402

DIG = 20


@dataclass
class PhysicalRun:
    trench: int
    starts: list[int]
    response_lines: list[str]


def loads(commands: list[int]) -> tuple[int, int]:
    """Return final active length and volume lower bound in trench meters."""
    active: dict[int, int] = {}
    peak = 0
    pid = 0
    for command in commands:
        if command > 0:
            pid += 1
            active[pid] = command
        elif command < 0:
            key = -command
            if key not in active:
                raise ValueError(f"invalid synthetic trace: inactive PID {key}")
            del active[key]
        peak = max(peak, sum(active.values()))
    final = sum(active.values())
    return final, math.ceil(peak / DIG) * DIG


def greedy_feasible(commands: list[int]) -> PhysicalRun:
    """Small deterministic best-fit/low-edge reference; used only as an upper bound."""
    starts: list[int] = []
    lengths: list[int] = []
    trench = 0
    lines: list[str] = []
    for command in commands:
        if command > 0:
            length = command
            gaps: list[tuple[int, int, int]] = []
            cursor = 0
            spans = sorted((start, lengths[pid], pid) for pid, start in enumerate(starts)
                           if start >= 0)
            for start, pipe_length, pid in spans:
                if cursor < start:
                    gaps.append((start - cursor, cursor, pid))
                cursor = max(cursor, start + pipe_length)
            if cursor < trench:
                gaps.append((trench - cursor, cursor, -1))
            fitting = [g for g in gaps if g[0] >= length]
            if fitting:
                _, start, _ = min(fitting, key=lambda g: (g[0] - length, g[1]))
                digs = 0
            else:
                tail = max((start0 + lengths[pid] for pid, start0 in enumerate(starts)
                            if start0 >= 0), default=0)
                tail_free = trench - tail
                digs = max(0, math.ceil((length - tail_free) / DIG))
                start = tail
                trench += digs * DIG
            starts.append(start)
            lengths.append(length)
            lines.append(f"{digs} {start}")
        elif command < 0:
            pid = -command
            if pid > len(starts) or starts[pid - 1] < 0:
                raise ValueError(f"invalid synthetic trace: inactive PID {pid}")
            lines.append(str(starts[pid - 1]))
            starts[pid - 1] = -1
    return PhysicalRun(trench, starts, lines)


def replay_output(commands: list[int], output_text: str) -> PhysicalRun:
    """Validate placement/deletion responses and derive a feasible upper bound."""
    lines = [line.strip() for line in output_text.splitlines() if line.strip()]
    cursor = 0
    starts: list[int] = []
    lengths: list[int] = []
    trench = 0
    for command in commands:
        if cursor >= len(lines):
            raise ValueError("reference output ended before the trace")
        fields = lines[cursor].split()
        cursor += 1
        if command > 0:
            if len(fields) != 2:
                raise ValueError("placement response must contain dig-sections and start")
            digs, start = map(int, fields)
            if digs < 0 or start < 0:
                raise ValueError("negative dig count or coordinate")
            trench += digs * DIG
            if start + command > trench:
                raise ValueError("reference places outside the dug trench")
            for pid, other in enumerate(starts):
                if other >= 0 and start < other + lengths[pid] and other < start + command:
                    raise ValueError("reference placement overlaps an active pipe")
            starts.append(start)
            lengths.append(command)
        elif command < 0:
            if len(fields) != 1:
                raise ValueError("deletion response must contain one coordinate")
            pid = -command
            if pid > len(starts) or starts[pid - 1] < 0:
                raise ValueError(f"trace deletes inactive PID {pid}")
            if int(fields[0]) != starts[pid - 1]:
                raise ValueError(f"wrong deletion coordinate for PID {pid}")
            starts[pid - 1] = -1
        else:
            raise ValueError("sentinel 0 is not part of the trace; responses are per nonzero command")
    if cursor != len(lines):
        raise ValueError("reference output has extra response lines")
    return PhysicalRun(trench, starts, lines)


def render_witness(commands: list[int], path: list[tuple[int, int]] | None) -> list[str] | None:
    """Turn an oracle placement path (dig sections, start) into protocol replies."""
    if path is None:
        return None
    replies: list[str] = []
    starts: list[int] = []
    path_pos = 0
    for command in commands:
        if command > 0:
            digs, start = path[path_pos]
            path_pos += 1
            starts.append(start)
            replies.append(f"{digs} {start}")
        elif command < 0:
            pid = -command
            if pid > len(starts) or starts[pid - 1] < 0:
                raise ValueError(f"oracle witness deletes inactive PID {pid}")
            replies.append(str(starts[pid - 1]))
            starts[pid - 1] = -1
    if path_pos != len(path):
        raise ValueError("oracle witness has excess placements")
    return replies


def exact_optimum(commands: list[int], *, incumbent: int | None = None,
                  incumbent_responses: list[str] | None = None,
                  max_states: int = 200_000, timeout_s: float = 10.0,
                  quota_poll_s: float = 1.0) -> dict:
    """Enumerate all legal allocations below an incumbent; prove or return unknown."""
    _, volume_lb = loads(commands)
    greedy = greedy_feasible(commands)
    upper = min(incumbent, greedy.trench) if incumbent is not None else greedy.trench
    if incumbent is not None and incumbent < volume_lb:
        raise ValueError("incumbent is below the volume lower bound")
    if greedy.trench > upper:
        # An externally validated trajectory is the known feasible witness.
        known_upper = incumbent
    else:
        known_upper = greedy.trench

    lengths_by_pid: list[int] = []
    pid_at_command: list[int] = []
    for command in commands:
        pid_at_command.append(len(lengths_by_pid) if command > 0 else -1)
        if command > 0:
            lengths_by_pid.append(command)
    # Only starts are state-dependent; slots are fixed by PID order.
    initial = tuple([-1] * len(lengths_by_pid))
    seen: set[tuple[int, int, tuple[int, ...]]] = set()
    started = time.monotonic()
    nodes = 0
    edges = 0
    timed_out = False
    quota_last = started
    best = known_upper
    best_path: list[tuple[int, int]] | None = None
    path: list[tuple[int, int]] = []

    def poll_quota() -> None:
        nonlocal quota_last
        now = time.monotonic()
        if now - quota_last >= quota_poll_s:
            gate(CAMPAIGN, max_age_seconds=60)
            quota_last = now

    def dfs(index: int, trench: int, state: tuple[int, ...]) -> None:
        nonlocal nodes, edges, timed_out, best, best_path
        if timed_out or best == volume_lb:
            return
        if nodes >= max_states or time.monotonic() - started >= timeout_s:
            timed_out = True
            return
        poll_quota()
        key = (index, trench, state)
        if key in seen:
            return
        seen.add(key)
        nodes += 1
        if trench >= best:
            return
        if index == len(commands):
            best = trench
            best_path = list(path)
            return
        command = commands[index]
        if command < 0:
            pid = -command - 1
            if pid >= len(state) or state[pid] < 0:
                raise ValueError(f"trace deletes inactive PID {pid + 1}")
            updated = list(state)
            updated[pid] = -1
            dfs(index + 1, trench, tuple(updated))
            return

        length = command
        # Digging is monotone; any route better than the incumbent stays below it.
        for new_trench in range(trench, best, DIG):
            if new_trench < length:
                continue
            max_start = new_trench - length
            for start in range(max_start + 1):
                if any(other >= 0 and start < other + lengths_by_pid[pid] and
                       other < start + length for pid, other in enumerate(state)):
                    continue
                updated = list(state)
                updated[pid_at_command[index]] = start
                edges += 1
                path.append(((new_trench - trench) // DIG, start))
                dfs(index + 1, new_trench, tuple(updated))
                path.pop()
                if timed_out or best == volume_lb:
                    return

    # State vectors are fixed to the final PID count; each placement updates
    # only its predetermined PID slot, preserving exact deletion identity.
    try:
        dfs(0, 0, initial)
    except Exception:
        raise
    proven = not timed_out
    # If an externally supplied incumbent is better than the local greedy, it
    # is still a valid witness; exhaustive search below it proves that witness.
    result = best if best_path is not None else known_upper
    return {
        "status": "optimal" if proven else "unknown",
        "optimality_proven": proven,
        "best_feasible_trench_m": result,
        "volume_lower_bound_m": volume_lb,
        "gap_to_volume_bound_m": result - volume_lb,
        "visited_states": nodes,
        "legal_placement_edges": edges,
        "state_cap": max_states,
        "timeout_s": timeout_s,
        "elapsed_s": round(time.monotonic() - started, 6),
        "reason": (
            "volume lower bound attained by feasible witness" if best == volume_lb else
            "exhaustive below incumbent" if proven else "state_or_time_cap"
        ),
        "oracle_witness_path": best_path,
        "oracle_witness_responses": render_witness(commands, best_path),
        "known_feasible_witness_responses": (
            incumbent_responses if incumbent is not None and incumbent <= greedy.trench
            else greedy.response_lines
        ),
        "initial_greedy_trench_m": greedy.trench,
        "external_incumbent_m": incumbent,
    }


def generated_traces(seed: int = 20261018) -> list[dict]:
    """Fresh short patterns with varied exact sizes, deletion order and seams."""
    # All traces are authored here and are not derived from any contest input.
    families = [
        ("staggered-middle-release", [11, 9, 7, -2, 12, -1, 8, -3, 10]),
        ("paired-reuse-and-coalesce", [6, 13, 8, 7, -2, -3, 12, -1, 9]),
        ("young-tail-vs-old-interior", [8, 12, 5, 10, -1, 13, -3, 6, -2, 11]),
        ("unequal-survivor-lane", [14, 6, 9, 11, -2, 8, -1, 13, -3, 7]),
        ("alternating-size-replacement", [5, 15, 6, 12, -1, 9, -3, 14, -2, 8]),
        ("double-delete-seam", [9, 8, 12, 6, -2, -3, 15, -1, 7, -4]),
        ("fifo-wave", [7, 11, 13, 5, -1, 10, -2, 8, -3, 14]),
        ("lifo-wave", [7, 11, 13, 5, -4, 10, -3, 8, -2, 14]),
    ]
    result = []
    for name, ops in families:
        # Validate IDs and ensure a nonempty final live set; no Open15 data used.
        loads(ops)
        result.append({"name": name, "seed": seed, "commands": ops,
                       "provenance": "hand-authored synthetic mechanism probe"})
    return result


def generated_variations(seed: int = 20261018, pairs: int = 32) -> list[dict]:
    """Parameter variations with repeated observed prefix and paired suffixes.

    Each pair has the same core [a,b,c,d]. The pressure trace's warmup repeats
    that motif in the same order; the light trace's warmup uses the same length
    multiset with b/c swapped. This intentionally inserts a learnable prefix
    cue and tests whether it selects an offline-helpful action. It is a
    synthetic signal test, not evidence that contest streams have this law.
    """
    rng = random.Random(seed)
    traces: list[dict] = []
    seen_parameters: set[tuple[int, int, int, int, int, int]] = set()
    attempts = 0
    while len(seen_parameters) < pairs and attempts < pairs * 100:
        attempts += 1
        # The first four lengths exactly fill a fresh 20 m span.
        a = rng.randint(3, 10)
        b = rng.randint(2, 10)
        c = rng.randint(3, 10)
        d = DIG - a - b - c
        if d < 2 or d > 12:
            continue
        # e must miss the deleted-a gap. f must miss both the c-gap and the
        # baseline tail after e, while fitting after early one-section growth.
        e_low = max(a + 1, 2)
        e_high = min(14, 40 - (a + b + d) - (c + 1))
        if e_low > e_high:
            continue
        e = rng.randint(e_low, e_high)
        f_low = max(c + 1, 21 - e)
        f_high = min(20, 40 - (a + b + d + e))
        if f_low > f_high:
            continue
        f = rng.randint(f_low, f_high)
        params = (a, b, c, d, e, f)
        if params in seen_parameters:
            continue
        seen_parameters.add(params)
        pair = len(seen_parameters) - 1
        repeated_warmup = [a, b, c, d, -1, -2, -3, -4]
        scrambled_warmup = [a, c, b, d, -1, -2, -3, -4]
        repeated_prefix = [a, b, c, d]
        pressure_suffix = [-5, e, -7, f, -6, 1]
        light_suffix = [-5, 1, -7, 1, -6, 1]
        for kind, warmup, suffix in (
            ("pressure", repeated_warmup, pressure_suffix),
            ("light", scrambled_warmup, light_suffix),
        ):
            commands = warmup + repeated_prefix + suffix
            loads(commands)
            traces.append({
                "name": f"repeat-{pair:02d}-{kind}",
                "pair_id": f"repeat-{pair:02d}",
                "suffix_kind": kind,
                "seed": seed,
                "parameters": {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f},
                "commands": commands,
                "decision_command_index": len(warmup) + 3,
                "shared_prefix_through_decision": len(warmup) + 4,
                "prefix_signal": (
                    "exact ordered motif repeats in warmup" if kind == "pressure"
                    else "same warmup length multiset with b/c order swapped"
                ),
                "provenance": "seeded synthetic paired-prefix variation; no contest input copied",
            })
    if len(seen_parameters) != pairs:
        raise RuntimeError(f"generated only {len(seen_parameters)} distinct parameter tuples")
    return traces


def save_traces(out_dir: Path, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    payload = {
        "schema": "bounded-counterexample-traces-v1",
        "seed": seed,
        "source": "hand-authored short synthetic allocator traces; no contest inputs copied",
        "traces": generated_traces(seed),
    }
    encoded = (json.dumps(payload, indent=2) + "\n").encode()
    (out_dir / "traces.json").write_bytes(encoded)
    # Standard whitespace-token protocol input for the official native checker.
    for row in payload["traces"]:
        text = f"1.0\n{len(row['commands'])}\n" + "\n".join(
            map(str, row["commands"] + [0])) + "\n"
        (out_dir / f"{row['name']}.in").write_text(text, encoding="ascii")
    manifest = {"traces_sha256": hashlib.sha256(encoded).hexdigest(),
                "count": len(payload["traces"]), "seed": seed,
                "max_commands": max(map(lambda r: len(r["commands"]), payload["traces"]))}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def save_variations(out_dir: Path, seed: int, pairs: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = generated_variations(seed, pairs)
    payload = {
        "schema": "bounded-counterexample-paired-prefix-v1",
        "seed": seed,
        "pair_count": pairs,
        "case_count": len(rows),
        "source": "parameterized short synthetic traces; no contest inputs copied",
        "traces": rows,
    }
    encoded = (json.dumps(payload, indent=2) + "\n").encode()
    (out_dir / "traces.json").write_bytes(encoded)
    for row in rows:
        text = f"1.0\n{len(row['commands'])}\n" + "\n".join(
            map(str, row["commands"] + [0])) + "\n"
        (out_dir / f"{row['name']}.in").write_text(text, encoding="ascii")
    (out_dir / "manifest.json").write_text(json.dumps({
        "traces_sha256": hashlib.sha256(encoded).hexdigest(),
        "pair_count": pairs, "case_count": len(rows), "seed": seed,
        "max_commands": max(len(r["commands"]) for r in rows),
        "prefix_relation": "pressure has an ordered motif repetition; light has the same length multiset with b/c swapped",
    }, indent=2) + "\n")


def run_suite(traces_path: Path, output: Path, *, max_states: int,
              timeout_s: float, reference_dir: Path | None) -> dict:
    suite = json.loads(traces_path.read_text())
    rows = []
    for trace in suite["traces"]:
        commands = trace["commands"]
        reference = None
        reference_responses = None
        if reference_dir:
            reference_path = reference_dir / f"{trace['name']}.out"
            if not reference_path.exists():
                reference_path = reference_dir / trace["name"] / "judge_output.txt"
            if reference_path.exists():
                validated = replay_output(commands, reference_path.read_text())
                reference = validated.trench
                reference_responses = validated.response_lines
        result = exact_optimum(commands, incumbent=reference,
                               incumbent_responses=reference_responses,
                               max_states=max_states, timeout_s=timeout_s)
        result["gap_reference_to_best_m"] = (
            reference - result["best_feasible_trench_m"] if reference is not None else None
        )
        rows.append({**trace, "reference_trench_m": reference, **result})
    report = {
        "schema": "bounded-oracle-report-v1",
        "diagnostic_only": True,
        "future_information_used_by_oracle": True,
        "production_policy_changes": 0,
        "trace_suite_sha256": hashlib.sha256(traces_path.read_bytes()).hexdigest(),
        "rows": rows,
        "limitations": [
            "proves only the exact optimum for the listed finite trace and integer coordinates",
            "oracle has the full future command suffix and cannot be copied into online policy",
            "state/time capped rows are unknown, even when a lower gap looks small",
            "synthetic mechanisms do not establish contest-table or hidden-test improvement",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def self_check() -> dict:
    # A 20 m trench can hold both 9 m objects; after removing one, 11 m fits.
    # A 21 m simultaneous load makes the volume lower bound 40 m.
    cases = [
        [9, 9, -1, 11],
        [7, 8, 9, -2, 10, -1, 8],
        [6, 14, 8, -2, 13, -1, 7],
    ]
    answers = [exact_optimum(case, max_states=80_000, timeout_s=2.0) for case in cases]
    # Artificial low cap must never report proof unless search completed.
    capped = exact_optimum([15, 15, -1, 16], max_states=0, timeout_s=1.0)
    assert capped["status"] == "unknown" and not capped["optimality_proven"]
    assert all(row["status"] in ("optimal", "unknown") for row in answers)
    return {"cases": answers, "cap_case": capped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", type=Path)
    parser.add_argument("--generate-variations", type=Path)
    parser.add_argument("--pairs", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--suite", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--reference-dir", type=Path)
    parser.add_argument("--max-states", type=int, default=200_000)
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    gate(CAMPAIGN, max_age_seconds=60)
    if args.generate:
        save_traces(args.generate, args.seed)
        print(json.dumps({"generated": str(args.generate), "count": len(generated_traces(args.seed))}))
    if args.generate_variations:
        save_variations(args.generate_variations, args.seed, args.pairs)
        print(json.dumps({"generated": str(args.generate_variations),
                          "pairs": args.pairs, "count": args.pairs * 2}))
    if args.self_check:
        print(json.dumps(self_check(), indent=2))
    if args.suite:
        if not args.out:
            parser.error("--suite requires --out")
        print(json.dumps(run_suite(args.suite, args.out,
                                  max_states=args.max_states,
                                  timeout_s=args.timeout_s,
                                  reference_dir=args.reference_dir), indent=2))
    if not (args.generate or args.generate_variations or args.self_check or args.suite):
        parser.error("specify --generate, --generate-variations, --self-check, or --suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
