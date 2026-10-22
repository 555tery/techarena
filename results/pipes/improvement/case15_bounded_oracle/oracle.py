#!/usr/bin/env python3
"""Exact finite-suffix placement oracle for three fixed case-15 prefixes.

The state at each window boundary is reconstructed from the saved verified
champion transcript. Within a window, every integer start coordinate that fits
is enumerated. Base-pipe deletions follow the fixed input; newly placed pipes
are branch-specific. Digging is delayed to the minimum 20 m multiple needed
for the chosen pipe endpoint, which is without loss for a monotone trench.
"""

from __future__ import annotations

import bisect
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "data/pipes/open/15.in"
OUTPUT = ROOT / (
    "results/pipes/improvement/case9_causal_profiles/runs/"
    "champion-trace-open15-v2/runs/15/judge_output.txt"
)
OUTDIR = Path(__file__).resolve().parent
EXPECTED_INPUT_SHA = "0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353"
EXPECTED_OUTPUT_SHA = "0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e"

# Fixed before examining oracle outputs: first early expansion cluster, the
# next cluster containing three 33/33/35 m placements, and the first cluster
# after a longer interval of non-expanding commands.
WINDOWS = [
    ("A_first_cluster", 100003, 100008),
    ("B_33m_cluster", 100012, 100018),
    ("C_34_30_35_cluster", 100144, 100150),
]
MAX_STATES_PER_STAGE = 300_000
MAX_TRANSITIONS_PER_WINDOW = 3_000_000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def merge_gap(gaps: List[Tuple[int, int]], start: int, end: int) -> None:
    """Insert a newly free interval into sorted, disjoint gaps."""
    i = bisect.bisect_left(gaps, (start, -1))
    if i and gaps[i - 1][1] == start:
        i -= 1
        start = gaps[i][0]
        gaps.pop(i)
    if i < len(gaps) and gaps[i][0] == end:
        end = gaps[i][1]
        gaps.pop(i)
    if i < len(gaps) and gaps[i][0] < end:
        raise AssertionError("overlapping base gaps")
    if i and gaps[i - 1][1] > start:
        raise AssertionError("overlapping left base gap")
    gaps.insert(i, (start, end))


def initial_gaps(active: Dict[int, Tuple[int, int]], trench: int) -> List[Tuple[int, int]]:
    occ = sorted((s, s + length, pid) for pid, (s, length) in active.items())
    gaps: List[Tuple[int, int]] = []
    cursor = 0
    for s, e, _pid in occ:
        if s < cursor or e > trench:
            raise AssertionError("invalid reconstructed prefix geometry")
        if cursor < s:
            gaps.append((cursor, s))
        cursor = e
    if cursor < trench:
        gaps.append((cursor, trench))
    return gaps


def load_trace():
    in_sha = sha256(INPUT)
    out_sha = sha256(OUTPUT)
    if in_sha != EXPECTED_INPUT_SHA or out_sha != EXPECTED_OUTPUT_SHA:
        raise RuntimeError(f"unexpected trace hashes: input={in_sha} output={out_sha}")
    fields = INPUT.read_text().split()
    weight, n = float(fields[0]), int(fields[1])
    commands = list(map(int, fields[2:2 + n]))
    if len(commands) != n or list(map(int, fields[2 + n:])) != [0]:
        raise RuntimeError("case-15 input framing changed")
    answers = OUTPUT.read_text().splitlines()
    if len(answers) != n:
        raise RuntimeError("answer line count differs from command count")
    parsed = [tuple(map(int, line.split())) for line in answers]
    if any(len(a) != (2 if c > 0 else 1) for c, a in zip(commands, parsed)):
        raise RuntimeError("answer line arity mismatch")
    return weight, commands, parsed


def expansion_summary(commands, answers):
    active: Dict[int, Tuple[int, int]] = {}
    trench = 0
    active_length = 0
    pid = 0
    expansions = []
    for op, (command, answer) in enumerate(zip(commands, answers), 1):
        if command > 0:
            digs, start = answer
            if digs:
                expansions.append({"op": op, "length": command,
                                   "added_m": 20 * digs,
                                   "free_volume_before": trench - active_length,
                                   "aggregate_volume_sufficient": trench - active_length >= command})
            trench += 20 * digs
            pid += 1
            active[pid] = (start, command)
            active_length += command
        else:
            _start, length = active.pop(-command)
            active_length -= length
    phase = [e for e in expansions if 100001 <= e["op"] <= 110000]
    return {
        "all_case15_expansions": len(expansions),
        "phase_op_range": [100001, 110000],
        "phase_expansions": len(phase),
        "phase_added_m": sum(e["added_m"] for e in phase),
        "phase_aggregate_volume_sufficient": sum(e["aggregate_volume_sufficient"] for e in phase),
        "phase_aggregate_volume_short": sum(not e["aggregate_volume_sufficient"] for e in phase),
    }


def reconstruct(start_after: int, commands, answers):
    """Replay one exact prefix, returning its active PID geometry and trench."""
    active: Dict[int, Tuple[int, int]] = {}
    occupied: List[Tuple[int, int, int]] = []
    trench = 0
    pid = 0
    for op in range(1, start_after + 1):
        c = commands[op - 1]
        out = answers[op - 1]
        if c > 0:
            digs, start = out
            new_trench = trench + 20 * digs
            if digs < 0 or start < 0 or start + c > new_trench:
                raise AssertionError(f"invalid baseline placement at op {op}")
            i = bisect.bisect_left(occupied, (start, -1, -1))
            if i and occupied[i - 1][1] > start:
                raise AssertionError(f"baseline overlap at op {op}")
            if i < len(occupied) and occupied[i][0] < start + c:
                raise AssertionError(f"baseline overlap at op {op}")
            pid += 1
            occupied.insert(i, (start, start + c, pid))
            active[pid] = (start, c)
            trench = new_trench
        else:
            k = -c
            if k not in active:
                raise AssertionError(f"baseline deletes inactive PID {k} at op {op}")
            start, length = active.pop(k)
            if out[0] != start:
                raise AssertionError(f"baseline deletion coordinate mismatch at op {op}")
            i = bisect.bisect_left(occupied, (start, -1, -1))
            if occupied[i] != (start, start + length, k):
                raise AssertionError(f"baseline active geometry mismatch at op {op}")
            occupied.pop(i)
    return pid, trench, active


def effective_free_gaps(base_gaps: List[Tuple[int, int]], trench0: int,
                        trench: int, added: Tuple[Tuple[int, int, int], ...]):
    """Subtract active branch-added pipes from fixed-prefix free gaps."""
    gaps = list(base_gaps)
    if trench > trench0:
        if gaps and gaps[-1][1] == trench0:
            gaps[-1] = (gaps[-1][0], trench)
        else:
            gaps.append((trench0, trench))
    occupied = sorted((s, s + length) for _pid, s, length in added)
    free: List[Tuple[int, int]] = []
    j = 0
    for a, b in gaps:
        cursor = a
        while j < len(occupied) and occupied[j][1] <= a:
            j += 1
        k = j
        while k < len(occupied) and occupied[k][0] < b:
            s, e = occupied[k]
            if s < cursor:
                raise AssertionError("branch pipe overlaps a base obstacle or another pipe")
            if cursor < s:
                free.append((cursor, s))
            cursor = max(cursor, e)
            k += 1
        if cursor < b:
            free.append((cursor, b))
    return free


def action_class(gap: Tuple[int, int], start: int, length: int, trench: int,
                 trench0: int) -> str:
    a, b = gap
    if start == a:
        side = "left-edge"
    elif start + length == b:
        side = "right-edge"
    else:
        side = "interior"
    if a < trench0 < b:
        origin = "old-tail+new-tail"
    elif a >= trench0:
        origin = "new-tail"
    else:
        origin = "preexisting-gap"
    return f"{origin}:{side}"


def make_base_schedule(start_after: int, end_op: int, commands, initial_active,
                       trench0: int):
    """Precompute deterministic base-pipe free gaps immediately before ops."""
    gaps = initial_gaps(initial_active, trench0)
    base_active = dict(initial_active)
    before: Dict[int, List[Tuple[int, int]]] = {}
    for op in range(start_after + 1, end_op + 1):
        before[op] = list(gaps)
        c = commands[op - 1]
        if c < 0 and -c in base_active:
            pid = -c
            start, length = base_active.pop(pid)
            merge_gap(gaps, start, start + length)
    return before


def solve_window(name, start_after, end_op, commands, answers):
    prefix_pid, trench0, active0 = reconstruct(start_after, commands, answers)
    base_before = make_base_schedule(start_after, end_op, commands, active0, trench0)
    initial_pids = set(active0)
    baseline_pid = prefix_pid
    baseline_trench = trench0
    baseline_actions = []
    placement_pid_at_op = {}
    for op in range(start_after + 1, end_op + 1):
        c = commands[op - 1]
        if c > 0:
            baseline_pid += 1
            placement_pid_at_op[op] = baseline_pid
            digs, start = answers[op - 1]
            baseline_trench += 20 * digs
            baseline_actions.append({"op": op, "pid": baseline_pid, "length": c,
                                     "digs": digs, "start": start,
                                     "trench_after": baseline_trench})
    trench_cap = baseline_trench

    # Independently check that the saved baseline suffix is legal from this
    # fixed state before comparing its terminal trench to the oracle.
    verify_added: Dict[int, Tuple[int, int]] = {}
    verify_trench = trench0
    for op in range(start_after + 1, end_op + 1):
        c = commands[op - 1]
        if c > 0:
            digs, start = answers[op - 1]
            next_trench = verify_trench + 20 * digs
            overlay = tuple(sorted((pid, s, length)
                                   for pid, (s, length) in verify_added.items()))
            legal = any(a <= start and start + c <= b
                        for a, b in effective_free_gaps(base_before[op], trench0,
                                                        next_trench, overlay))
            if not legal:
                raise AssertionError(f"saved baseline placement illegal at op {op}")
            verify_added[placement_pid_at_op[op]] = (start, c)
            verify_trench = next_trench
        else:
            delete_pid = -c
            if delete_pid not in initial_pids:
                if delete_pid not in verify_added:
                    raise AssertionError(f"saved baseline deletes absent PID {delete_pid} at op {op}")
                del verify_added[delete_pid]
    if verify_trench != baseline_trench:
        raise AssertionError("baseline suffix trench replay mismatch")

    # Each key is (monotone trench length, active branch-added (pid,start,len)).
    # The value retains one witness path and the exact set of possible first actions.
    states = {(trench0, ()): {"path": (), "first": frozenset()}}
    stage_stats = []
    total_transitions = 0
    aborted = None
    for op in range(start_after + 1, end_op + 1):
        c = commands[op - 1]
        next_states = {}
        transitions = 0
        if c < 0:
            delete_pid = -c
            for (trench, added), node in states.items():
                if delete_pid in initial_pids:
                    new_added = added
                else:
                    mutable = list(added)
                    idx = next((i for i, x in enumerate(mutable) if x[0] == delete_pid), None)
                    if idx is None:
                        raise AssertionError(f"branch PID {delete_pid} absent at delete op {op}")
                    mutable.pop(idx)
                    new_added = tuple(mutable)
                key = (trench, new_added)
                if key not in next_states:
                    next_states[key] = node
                else:
                    old = next_states[key]
                    merged_first = old["first"] | node["first"]
                    if node["path"] < old["path"]:
                        old["path"] = node["path"]
                    old["first"] = merged_first
                transitions += 1
        else:
            new_pid = placement_pid_at_op[op]
            fixed_gaps = base_before[op]
            for (trench, added), node in states.items():
                # Enumerate all starts reachable by the known baseline terminal
                # trench. This includes starting inside future new tail; the
                # minimal required 20 m extension is charged for each action.
                # States past the baseline terminal trench cannot improve the
                # bounded objective and are safely dominated.
                for free_gap in effective_free_gaps(fixed_gaps, trench0, trench_cap, added):
                    a, b = free_gap
                    last_start = b - c
                    if last_start < a:
                        continue
                    for start in range(a, last_start + 1):
                        new_trench = max(trench, ((start + c + 19) // 20) * 20)
                        if new_trench > trench_cap:
                            continue
                        if start + c > new_trench:
                            raise AssertionError("minimal extension failed")
                        containing = (a, min(b, new_trench))
                        if not (containing[0] <= start and start + c <= containing[1]):
                            raise AssertionError("enumerated action is not legal after minimal dig")
                        act = (op, new_pid, c, (new_trench - trench) // 20,
                               start, containing,
                               action_class(containing, start, c, new_trench, trench0))
                        new_added = tuple(sorted(added + ((new_pid, start, c),)))
                        key = (new_trench, new_added)
                        path = node["path"] + (act,)
                        first = node["first"] if node["first"] else frozenset({act})
                        if key in next_states:
                            old = next_states[key]
                            old["first"] = old["first"] | first
                            if path < old["path"]:
                                old["path"] = path
                        else:
                            next_states[key] = {"path": path, "first": first}
                        transitions += 1
                        if transitions > MAX_TRANSITIONS_PER_WINDOW:
                            aborted = f"transition cap {MAX_TRANSITIONS_PER_WINDOW} at op {op}"
                            break
                    if aborted:
                        break
                if aborted:
                    break
        total_transitions += transitions
        stage_stats.append({"op": op, "command": c, "states_in": len(states),
                            "transitions": transitions, "states_out": len(next_states)})
        if aborted:
            break
        if len(next_states) > MAX_STATES_PER_STAGE:
            aborted = f"state cap {MAX_STATES_PER_STAGE} at op {op}"
            break
        states = next_states

    if aborted:
        return {
            "name": name, "start_after": start_after, "end_op": end_op,
            "complete": False, "abort_reason": aborted, "stage_stats": stage_stats,
            "total_transitions": total_transitions,
            "baseline_final_trench": baseline_trench,
            "baseline_actions": baseline_actions,
        }

    optimum = min(t for t, _added in states)
    optimum_states = [(key, node) for key, node in states.items() if key[0] == optimum]
    first_actions = set()
    paths = []
    for _key, node in optimum_states:
        first_actions.update(node["first"])
        paths.append(node["path"])
    best_path = min(paths) if paths else ()
    return {
        "name": name, "start_after": start_after, "end_op": end_op,
        "complete": True, "initial_trench": trench0,
        "initial_active_pipes": len(active0), "initial_gap_count": len(initial_gaps(active0, trench0)),
        "baseline_suffix_geometry_valid": True,
        "baseline_final_trench": baseline_trench, "oracle_final_trench": optimum,
        "hindsight_saving_m": baseline_trench - optimum,
        "baseline_actions": baseline_actions,
        "oracle_witness": [
            {"op": a[0], "pid": a[1], "length": a[2], "digs": a[3],
             "start": a[4], "containing_free_gap_before_place": list(a[5]),
             "class": a[6]}
            for a in best_path
        ],
        "optimal_first_actions": [
            {"op": a[0], "pid": a[1], "length": a[2], "digs": a[3],
             "start": a[4], "containing_free_gap_before_place": list(a[5]),
             "class": a[6]}
            for a in sorted(first_actions)
        ],
        "optimal_terminal_state_count": len(optimum_states),
        "stage_stats": stage_stats,
        "total_transitions": total_transitions,
        "terminal_state_count": len(states),
    }


def main():
    weight, commands, answers = load_trace()
    result = {
        "title": "case15 exact bounded offline placement oracle",
        "scope": "three prespecified finite suffixes; hindsight only; not solver policy",
        "case_weight": weight,
        "trace_expansion_summary": expansion_summary(commands, answers),
        "input_sha256": sha256(INPUT),
        "champion_source_sha256": sha256(ROOT / "results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp"),
        "champion_binary_sha256": sha256(ROOT / "results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs"),
        "champion_output_sha256": sha256(OUTPUT),
        "action_set": "all integer start coordinates fitting any free interval; current trench may be minimally extended in 20 m sections to fit endpoint",
        "windows": [],
    }
    for window in WINDOWS:
        result["windows"].append(solve_window(*window, commands, answers))
    out = OUTDIR / "oracle_results.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "input_sha256": result["input_sha256"],
        "champion_source_sha256": result["champion_source_sha256"],
        "champion_output_sha256": result["champion_output_sha256"],
        "windows": [
            {"name": w["name"], "complete": w["complete"],
             "baseline_final_trench": w.get("baseline_final_trench"),
             "oracle_final_trench": w.get("oracle_final_trench"),
             "hindsight_saving_m": w.get("hindsight_saving_m"),
             "terminal_state_count": w.get("terminal_state_count"),
             "abort_reason": w.get("abort_reason"),
             "total_transitions": w.get("total_transitions")}
            for w in result["windows"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
