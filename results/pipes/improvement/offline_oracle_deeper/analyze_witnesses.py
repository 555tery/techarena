#!/usr/bin/env python3
"""Summarize bounded offline witnesses and baseline state at first divergence."""

import hashlib
import json
from collections import Counter
from pathlib import Path


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[3]
RUNS = WORK / "runs"


def load_input(path):
    tokens = Path(path).read_text().split()
    n = int(tokens[1])
    return list(map(int, tokens[2 : 2 + n]))


def load_baseline(ops, trace_path):
    tokens = list(map(int, Path(trace_path).read_text().split()))
    cursor = 0
    baseline = []
    for op in ops:
        if op > 0:
            baseline.append((tokens[cursor], tokens[cursor + 1]))
            cursor += 2
        else:
            baseline.append((0, tokens[cursor]))
            cursor += 1
    if cursor != len(tokens):
        raise ValueError(f"trace token mismatch: {cursor} != {len(tokens)}")
    return baseline


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reconstruct(ops, baseline, stop_op):
    """Rebuild exact baseline state immediately before 1-based stop_op."""
    trench = 0
    pipes = {}
    recent = []
    pid = 0
    for i, op in enumerate(ops[: stop_op - 1], 1):
        digs, start = baseline[i - 1]
        if op > 0:
            trench += 20 * digs
            pid += 1
            pipes[pid] = {
                "start": start,
                "end": start + op,
                "length": op,
                "created_op": i,
                "active": True,
            }
            recent.append(op)
            if len(recent) > 2048:
                recent.pop(0)
        else:
            target = -op
            if target in pipes:
                pipes[target]["active"] = False

    live = [p for p in pipes.values() if p["active"]]
    live.sort(key=lambda p: p["start"])
    gaps = []
    cursor = 0
    for p in live:
        if p["start"] < cursor:
            raise ValueError(f"overlapping pipe at op {stop_op}")
        if p["start"] > cursor:
            gaps.append((cursor, p["start"]))
        cursor = p["end"]
    if cursor < trench:
        gaps.append((cursor, trench))

    def neighbors_for(start, length):
        end = start + length
        left = None
        right = None
        for p in live:
            if p["end"] <= start and (left is None or p["end"] > left["end"]):
                left = p
            if p["start"] >= end and (right is None or p["start"] < right["start"]):
                right = p
        def brief(p):
            if p is None:
                return None
            return {
                "length": p["length"],
                "age_commands": stop_op - p["created_op"],
            }
        return {"left": brief(left), "right": brief(right)}

    def containing_gap(start, length):
        end = start + length
        for a, b in gaps:
            if a <= start and end <= b:
                return {"start": a, "end": b, "length": b - a}
        # A candidate beyond the old trench can consume its expandable tail.
        if start <= trench <= end or start >= trench:
            tail = gaps[-1] if gaps and gaps[-1][1] == trench else (trench, trench)
            return {"start": tail[0], "end": tail[1], "length": tail[1] - tail[0], "extends_tail": True}
        return None

    return {
        "trench_length_m": trench,
        "active_pipes": len(live),
        "free_gap_count": len(gaps),
        "total_free_m": sum(b - a for a, b in gaps),
        "largest_gap_m": max((b - a for a, b in gaps), default=0),
        "tail_gap_m": (gaps[-1][1] - gaps[-1][0]) if gaps and gaps[-1][1] == trench else 0,
        "recent_length_tail_12": recent[-12:],
        "recent_length_count_for_request": None,
        "gap_count_fitting_request": None,
        "min_fitting_gap_slack_m": None,
        "max_fitting_gap_slack_m": None,
        "gap_histogram": dict(sorted(Counter(b - a for a, b in gaps).items())),
        "_gaps": gaps,
        "_pipes": live,
        "_recent": recent,
        "_containing_gap": containing_gap,
        "_neighbors_for": neighbors_for,
    }


def enrich_state(state, length):
    fitting = [b - a for a, b in state["_gaps"] if b - a >= length]
    recent = state["_recent"]
    state["recent_length_count_for_request"] = sum(x == length for x in recent)
    state["gap_count_fitting_request"] = len(fitting)
    state["min_fitting_gap_slack_m"] = min((g - length for g in fitting), default=None)
    state["max_fitting_gap_slack_m"] = max((g - length for g in fitting), default=None)
    for key in ("_gaps", "_pipes", "_recent", "_containing_gap", "_neighbors_for"):
        del state[key]


def analyze_result(result_path):
    result = json.loads(result_path.read_text())
    ops = load_input(result["input"])
    baseline = load_baseline(ops, result["trace"])
    start = result["window_start_op_1based"]
    stop = start + result["window_count"]
    winner = {a["op"]: (a["digs"], a["start"]) for a in result["winner_path"]}
    placement_ops = [i for i in range(start, stop) if ops[i - 1] > 0]
    diff_ops = [i for i in placement_ops if winner.get(i) != baseline[i - 1]]
    first_op = diff_ops[0] if diff_ops else None
    first = None
    if first_op is not None:
        length = ops[first_op - 1]
        state = reconstruct(ops, baseline, first_op)
        base_action = baseline[first_op - 1]
        oracle_action = winner[first_op]
        baseline_gap = state["_containing_gap"](base_action[1], length)
        oracle_gap = state["_containing_gap"](oracle_action[1], length)
        baseline_neighbors = state["_neighbors_for"](base_action[1], length)
        oracle_neighbors = state["_neighbors_for"](oracle_action[1], length)
        enrich_state(state, length)
        first = {
            "op_1based": first_op,
            "request_length_m": length,
            "baseline_action": {"digs_sections": base_action[0], "start": base_action[1]},
            "oracle_action": {"digs_sections": oracle_action[0], "start": oracle_action[1]},
            "baseline_gap": baseline_gap,
            "oracle_gap": oracle_gap,
            "baseline_location_neighbors": baseline_neighbors,
            "oracle_location_neighbors": oracle_neighbors,
            "common_prechoice_state": state,
            "next_16_command_types_and_lengths": [
                ("place", x) if x > 0 else ("delete", -x)
                for x in ops[first_op : min(stop, first_op + 16) - 1]
            ],
        }
    return {
        "run": result_path.stem,
        "input_sha256": sha256(result["input"]),
        "trace_sha256": sha256(result["trace"]),
        "window_start_op_1based": start,
        "window_count": result["window_count"],
        "beam_width": result["beam_width"],
        "action_cap": result["action_cap"],
        "baseline_final_trench_m": result["baseline_final_trench_m"],
        "witness_final_trench_m": result["best_full_suffix_witness_trench_m"],
        "witness_saving_m": result["full_suffix_witness_saving_m"],
        "best_is_baseline_control": result["best_is_baseline_control"],
        "expanded_states_generated": result["expanded_states_generated"],
        "placement_decisions_in_window": len(placement_ops),
        "divergent_placement_decisions": len(diff_ops),
        "first_divergence": first,
    }


def main():
    analyzed = [analyze_result(p) for p in sorted(RUNS.glob("*.json"))]
    # Bring in the already archived long-window witnesses without rerunning them.
    old = [
        ROOT / "results/pipes/improvement/offline_longbeam/case5_start1505_n2048.json",
        ROOT / "results/pipes/improvement/offline_longbeam/case5_start3573_n2048.json",
        ROOT / "results/pipes/improvement/offline_longbeam/case9_start1501_n2048.json",
        ROOT / "results/pipes/improvement/offline_longbeam/case9_start6001_n2048.json",
        ROOT / "results/pipes/improvement/offline_longbeam_longanchors/case5_start1505_n4096_w3_a4.json",
        ROOT / "results/pipes/improvement/offline_longbeam_longanchors/case9_start3001_n4096_w3_a4.json",
    ]
    for p in old:
        if p.exists():
            analyzed.append(analyze_result(p))
    output = WORK / "witness_divergences.json"
    output.write_text(json.dumps({"analysis_scope": "first-divergence state is reconstructed from exact baseline transcript; future commands are reported only for diagnostic context", "runs": analyzed}, indent=2) + "\n")
    print(f"wrote {output.relative_to(ROOT)} with {len(analyzed)} runs")
    for row in analyzed:
        fd = row["first_divergence"]
        if fd is None:
            detail = "same path"
        else:
            detail = f"op={fd['op_1based']} len={fd['request_length_m']} active={fd['common_prechoice_state']['active_pipes']} gaps={fd['common_prechoice_state']['free_gap_count']} fit={fd['common_prechoice_state']['gap_count_fitting_request']} base={fd['baseline_action']} oracle={fd['oracle_action']}"
        print(f"{row['run']}: save={row['witness_saving_m']} m, diverged={row['divergent_placement_decisions']}, {detail}")


if __name__ == "__main__":
    main()
