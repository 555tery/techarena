#!/usr/bin/env python3
"""Descriptive replay/search regimes on the frozen, observed comparison corpus.

This is not a causal ablation. No solver is executed and no table-free score
is estimated. Raw F/T comparisons include scored runs exceeding resource limits.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRST = "replay_search"
SECOND = "online_cpp"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counter_line(stderr, tag):
    matches = re.findall(r"^" + re.escape(tag) + r"\s+(.*)$", stderr, re.MULTILINE)
    if not matches:
        return None
    require(len(matches) == 1, f"duplicate diagnostic counter line: {tag}")
    values = {}
    for key, value in re.findall(r"([A-Za-z_][A-Za-z_0-9]*)=([-+]?[0-9]+(?:\.[0-9]+)?)", matches[0]):
        require(key not in values, f"duplicate diagnostic counter: {tag}.{key}")
        values[key] = float(value) if "." in value else int(value)
    return values


def counters(row, case):
    stderr = row.get("candidate_stderr", "")
    replay = counter_line(stderr, "OPEN15_FULL_OVERFIT")
    search = counter_line(stderr, "ROBUST_SEARCH")
    validation = counter_line(stderr, "CAUSAL_VALIDATION")
    if replay is None or search is None:
        return None
    for fields, names in [(replay, ("replay", "fallback")), (search, ("decisions", "changes"))]:
        for name in names:
            require(isinstance(fields.get(name), int) and fields[name] >= 0,
                    f"invalid required counter {name}: {case['id']}")
    require(search["changes"] <= search["decisions"], f"changes>decisions: {case['id']}")
    if row["status"] == "ok":
        require(replay["replay"] + replay["fallback"] == case["meta"]["placement_count"],
                f"replay+fallback != placements: {case['id']}")
        require(replay.get("T") == row["trench_length_m"], f"diagnostic T mismatch: {case['id']}")
    if validation is not None and "committed" in validation:
        require(validation["committed"] == search["changes"], f"committed != search changes: {case['id']}")
    return {"replay": replay, "search": search, "causal_validation": validation}


def raw_result(row, case, frozen):
    if row["status"] != "ok":
        return None
    final = case["meta"]["final_occupied_length_m"]
    lower_bound = case["meta"]["minimum_trench_lower_bound_m"]
    trench = row.get("trench_length_m")
    require(isinstance(trench, int) and trench > 0 and trench % 20 == 0 and 0 <= final <= lower_bound <= trench,
            f"invalid F/LB/T for {case['id']}:{row['method']}")
    require(row.get("occupied_length_m") == final, f"occupied volume mismatch: {case['id']}:{row['method']}")
    raw = Fraction(final, trench)
    require(math.isclose(row["kpi"], float(raw), rel_tol=1e-14, abs_tol=1e-14), "stored KPI differs from F/T")
    cpu, rss = row.get("solver_cpu_total_s"), row.get("solver_peak_rss_mb")
    resource_pass = (isinstance(cpu, (int, float)) and math.isfinite(cpu) and 0 <= cpu < frozen["cpu_limit_s"] and
                     isinstance(rss, (int, float)) and math.isfinite(rss) and 0 <= rss < frozen["memory_limit_mib"])
    return {"raw": raw, "T": trench, "resource_pass": resource_pass,
            "CPU_s": cpu, "RSS_MiB": rss, "workers": row.get("workers")}


def describe(item):
    c = item["case"]
    return {"id": c["id"], "origin": c["origin"], "source_group": c["source_group"],
            "public_number": c.get("public_number"), "operations": c["meta"]["operation_count"],
            "F": c["meta"]["final_occupied_length_m"],
            "replay_search_raw_kpi": float(item["first"]["raw"]),
            "online_cpp_raw_kpi": float(item["second"]["raw"]), "delta": float(item["delta"]),
            "replay_search_T": item["first"]["T"], "online_cpp_T": item["second"]["T"],
            "replay_search_workers": item["first"]["workers"], "online_cpp_workers": item["second"]["workers"],
            "replay_search_resource_pass": item["first"]["resource_pass"],
            "online_cpp_resource_pass": item["second"]["resource_pass"], "counters": item["counters"]}


def summarize(items):
    items = list(items)
    n = len(items)
    deltas = [item["delta"] for item in items]
    ordered = sorted(items, key=lambda x: (x["delta"], x["case"]["id"]))
    losses = [item for item in ordered if item["delta"] < 0]
    gains = sorted((item for item in ordered if item["delta"] > 0), key=lambda x: (-x["delta"], x["case"]["id"]))
    return {"jointly_valid_count": n,
        "paired_mean_replay_search_raw_kpi": math.fsum(float(x["first"]["raw"]) for x in items) / n if n else None,
        "paired_mean_online_cpp_raw_kpi": math.fsum(float(x["second"]["raw"]) for x in items) / n if n else None,
        "paired_mean_delta_raw_kpi": math.fsum(float(x) for x in deltas) / n if n else None,
        "wins": sum(x > 0 for x in deltas), "ties": sum(x == 0 for x in deltas), "losses": sum(x < 0 for x in deltas),
        "minimum_delta": float(min(deltas)) if deltas else None,
        "maximum_delta": float(max(deltas)) if deltas else None,
        "minimum_loss": float(min(x for x in deltas if x < 0)) if losses else None,
        "best_gain": float(max(x for x in deltas if x > 0)) if gains else None,
        "worst_loss_examples_up_to3": [describe(x) for x in losses[:3]],
        "best_gain_examples_up_to3": [describe(x) for x in gains[:3]],
        "deterministic_examples_up_to3": [describe(x) for x in sorted(items, key=lambda x: x["case"]["id"])[:3]],
        "scored_resource_failure_pair_count": sum(not x["first"]["resource_pass"] or not x["second"]["resource_pass"] for x in items),
        "worker_pair_counts_replay_then_online": dict(collections.Counter(
            f"{x['first']['workers']}/{x['second']['workers']}" for x in items)),
        "replayed_placements_total": sum(x["counters"]["replay"]["replay"] for x in items),
        "fallback_placements_total": sum(x["counters"]["replay"]["fallback"] for x in items),
        "search_decisions_total": sum(x["counters"]["search"]["decisions"] for x in items),
        "search_changes_total": sum(x["counters"]["search"]["changes"] for x in items),
        "selected_ids": [x["case"]["id"] for x in sorted(items, key=lambda x: x["case"]["id"])]}


def analyze(directory):
    freeze_path = directory / "freeze.json"
    frozen = json.loads(freeze_path.read_text())
    freeze_sha = digest(freeze_path)
    cases = {c["id"]: c for c in frozen["cases"]}
    methods = {m["id"]: m for m in frozen["methods"]}
    require(len(cases) == len(frozen["cases"]) and len(methods) == len(frozen["methods"]), "duplicate frozen IDs")
    require(FIRST in methods and SECOND in methods, "required methods absent")
    for method in (FIRST, SECOND):
        m = methods[method]
        require(digest(directory / m["source"]) == m["source_sha256"], f"source hash mismatch: {method}")
        require(digest(directory / m["binary"]) == m["binary_sha256"], f"binary hash mismatch: {method}")
    payload = (directory / "records.jsonl").read_bytes() if (directory / "records.jsonl").exists() else b""
    records = {}
    ignored_tail_bytes = 0
    for line in payload.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            ignored_tail_bytes = len(line)
            break
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["id"], row["method"])
        require(key not in records, f"duplicate record: {key}")
        require(key[0] in cases and key[1] in methods, f"unknown record: {key}")
        c, m = cases[key[0]], methods[key[1]]
        for field, expected in [("freeze_sha256", freeze_sha), ("source_sha256", m["source_sha256"]),
                                ("binary_sha256", m["binary_sha256"]), ("test_sha256", c["input_sha256"]),
                                ("selected", c["selected"])]:
            require(row.get(field) == expected, f"record {field} mismatch: {key}")
        records[key] = row
    selected = sorted(c["id"] for c in cases.values() if c["selected"])
    require(len(selected) == frozen["selected_count"], "frozen selected count mismatch")
    matched = [x for x in selected if (x, FIRST) in records and (x, SECOND) in records]
    invalid, missing_counters, parsed, items = [], [], [], []
    for case_id in matched:
        c = cases[case_id]
        first_row, second_row = records[case_id, FIRST], records[case_id, SECOND]
        count = counters(first_row, c)
        if count is None:
            missing_counters.append(case_id)
        else:
            parsed.append(case_id)
        first, second = raw_result(first_row, c, frozen), raw_result(second_row, c, frozen)
        if first is None or second is None:
            invalid.append({"id": case_id, "replay_search_status": first_row["status"], "online_cpp_status": second_row["status"]})
            continue
        if count is None:
            continue
        items.append({"case": c, "first": first, "second": second, "counters": count,
                      "delta": first["raw"] - second["raw"]})
    groups = {
        "replay_placements_eq0": [x for x in items if x["counters"]["replay"]["replay"] == 0],
        "replay_placements_gt0": [x for x in items if x["counters"]["replay"]["replay"] > 0],
        "search_changes_eq0": [x for x in items if x["counters"]["search"]["changes"] == 0],
        "search_changes_gt0": [x for x in items if x["counters"]["search"]["changes"] > 0]}
    for replay_positive in (False, True):
        for changes_positive in (False, True):
            name = f"replay_{'gt0' if replay_positive else 'eq0'}__search_changes_{'gt0' if changes_positive else 'eq0'}"
            groups[name] = [x for x in items if (x["counters"]["replay"]["replay"] > 0) == replay_positive and
                            (x["counters"]["search"]["changes"] > 0) == changes_positive]
    expected = len(cases) * len(methods)
    complete = len(records) == expected and not ignored_tail_bytes
    pair_complete = len(matched) == len(selected)
    return {"schema_version": 1, "created_unix": time.time(), "complete": complete,
        "selected_pair_complete": pair_complete, "partial": not complete,
        "scope": "all frozen selected matched completed streams" if pair_complete else
            "PARTIAL: matched completed selected streams only; not the full 2537-stream result",
        "freeze_sha256": freeze_sha, "records_snapshot_sha256": hashlib.sha256(payload).hexdigest(),
        "ignored_unfinished_tail_bytes": ignored_tail_bytes,
        "expected_selected_streams": len(selected), "completed_runs_all_methods": len(records), "expected_runs_all_methods": expected,
        "matched_completed_selected_count": len(matched), "jointly_valid_with_required_counters_count": len(items),
        "parsed_required_counters_matched_count": len(parsed), "missing_required_counter_ids": missing_counters,
        "excluded_invalid_status_pairs": invalid,
        "comparison": {"first": FIRST, "second": SECOND, "delta": "replay_search raw F/T minus online_cpp raw F/T",
            "score_scope": "jointly status=ok only; invalid pairs excluded; scored resource-limit failures retained and counted",
            "arithmetic": "exact Fraction F/T comparisons for W/T/L; math.fsum for means from unrounded F/T"},
        "all_analyzable_matched_selected": summarize(items),
        "regimes": {name: summarize(values) for name, values in groups.items()},
        "counter_meanings_verified_from_source": {
            "source": methods[FIRST]["source"], "source_sha256": methods[FIRST]["source_sha256"],
            "replay": "Number of placement commands actually answered using matching public-table addresses; excludes matching deletion commands.",
            "fallback": "Number of placement commands after replay ends; can include BF, robust Planner and the separately gated fallback_online episode.",
            "search_decisions": "ROBUST Planner candidate-simulation batches reaching its decisions counter; includes incomplete batches flagged aborted. This is not a count of changed placements.",
            "search_changes": "ROBUST Planner placements actually returned at an address different from its BF baseline after the delayed confidence gate.",
            "changes_zero": "No committed ROBUST Planner address changes; does not rule out tabular placements or fallback_online-episode address changes.",
            "replay_zero_changes_zero": "No executed tabular placements and no ROBUST Planner address changes. In this source the physical fallback follows BF; search may still consume CPU.",
            "replay_zero": "No successful table-address placements on this observed trajectory. Table decoding/lookup and their CPU cost still occur; this is not a build with tables removed."},
        "interpretation_limits": [
            "These regime groups are descriptive and post-outcome-conditioned, not a causal ablation. Input composition and solver decisions jointly determine group membership.",
            "The full solver has a different fallback and handoff from current online_cpp; a win cannot be assigned solely to search or solely to removal of replay.",
            "replay=0 observations can motivate a future predeclared table-free fallback experiment. They do not establish its full-corpus counterfactual score.",
            "search_changes>0 proves committed deviations from BF occurred, not that those deviations caused a final gain.",
            "search_changes=0 with replay>0 does not isolate BF because public placements and an online episode may already have altered geometry.",
            "Timer-dependent search, table parsing overhead and worker load can change the trajectory of a separately built or rerun solver.",
            "Missing diagnostics and invalid status pairs are explicitly excluded from raw regime summaries; resource-failing scored runs remain visible.",
            "The saved corpus is observed data, not an independent holdout, a hidden-test distribution, or proof of a general improvement."],
        "transcript_audit": "Not performed here; counters are read from stored candidate_stderr, with frozen record/source/binary provenance checked. No gzip transcripts read."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    result = analyze(directory)
    target = args.out or directory / "regime_analysis.json"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temporary.replace(target)
    print(json.dumps({"complete": result["complete"], "matched_selected": result["matched_completed_selected_count"],
                      "analyzable": result["jointly_valid_with_required_counters_count"], "output": str(target)}))


if __name__ == "__main__":
    main()
