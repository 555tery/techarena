#!/usr/bin/env python3
"""Describe the frozen strict comparison, including honest partial snapshots.

Never executes a solver or changes frozen artifacts. Raw KPI is reconstructed
from frozen final occupied volume / measured trench; official rounded scores
are not used. Invalid or resource-failing runs receive adjusted KPI zero.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message: str):
    if not condition:
        raise ValueError(message)


def finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def percentile(values, q):
    """Linear interpolation at (n-1)*q, including the singleton case."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def distribution(values):
    return {"n": len(values), "mean": math.fsum(values) / len(values) if values else None,
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None, "p05": percentile(values, .05),
            "max": max(values) if values else None}


def resources(values):
    return {"measured_n": len(values), "max": max(values) if values else None,
            "p95": percentile(values, .95), "sum": math.fsum(values)}


def response_hashes(path: Path, expected: str, status: str, canonical_official_output=False):
    raw = hashlib.sha256()
    normalized = hashlib.sha256()
    normalized_valid = True
    response_lines = 0
    opener = gzip.open if path.suffix == ".gz" else open
    if canonical_official_output:
        # These are not untrusted solver stdout bytes: the frozen official
        # checker writes parsed integers with single spaces and LF to tout.
        # Re-parsing hundreds of millions of already-canonical tokens adds no
        # validation. Verify the lossless archive hash and full line count.
        with opener(path, "rb") as stream:
            last = b""
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                raw.update(block)
                response_lines += block.count(b"\n")
                last = block[-1:]
        require(raw.hexdigest() == expected, f"response hash mismatch: {path}")
        require(status != "ok" or last in (b"", b"\n"), f"unfinished successful transcript: {path}")
        return raw.hexdigest(), response_lines
    with opener(path, "rb") as stream:
        for line in stream:
            raw.update(line)
            tokens = line.split()
            if not tokens:
                continue
            response_lines += 1
            try:
                # Preserve response line boundaries while normalizing numeric
                # spelling and whitespace. All legal replies contain integers.
                normalized.update(b" ".join(str(int(x)).encode("ascii") for x in tokens) + b"\n")
            except ValueError:
                normalized_valid = False
    require(raw.hexdigest() == expected, f"response hash mismatch: {path}")
    require(status != "ok" or normalized_valid, f"noninteger response in successful run: {path}")
    return normalized.hexdigest() if normalized_valid else None, response_lines


def verify_artifacts(directory: Path, frozen):
    verified = {"method_sources": 0, "method_binaries": 0, "inputs": 0,
                "support_files": 0, "native_binary": False}
    for method in frozen["methods"]:
        for field in ("source", "binary"):
            path = directory / method[field]
            require(sha_file(path) == method[field + "_sha256"], f"{field} hash mismatch: {path}")
            verified["method_sources" if field == "source" else "method_binaries"] += 1
    for case in frozen["cases"]:
        path = directory / case["input"]
        require(sha_file(path) == case["input_sha256"], f"input hash mismatch: {path}")
        require(case["meta"]["test_sha256"] == case["input_sha256"], f"frozen meta hash mismatch: {case['id']}")
        verified["inputs"] += 1
    for name, expected in frozen.get("support_sha256", {}).items():
        require(sha_file(ROOT / name) == expected, f"support hash mismatch: {name}")
        verified["support_files"] += 1
    if "native_binary" in frozen:
        require(sha_file(directory / frozen["native_binary"]) == frozen["native_binary_sha256"], "native binary hash mismatch")
        verified["native_binary"] = True
    return verified


def load_records(directory: Path, frozen, freeze_sha, verify_transcripts=False):
    path = directory / "records.jsonl"
    payload = path.read_bytes() if path.exists() else b""
    cases = {x["id"]: x for x in frozen["cases"]}
    methods = {x["id"]: x for x in frozen["methods"]}
    records = {}
    ignored_tail_bytes = 0
    response_files = 0
    lines = payload.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if index == len(lines) - 1 and not line.endswith(b"\n"):
            # An append can be observed between the payload and final LF even
            # when the JSON itself already parses. Only finished rows count.
            ignored_tail_bytes = len(line)
            break
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError(f"invalid JSON record at line {index + 1}") from None
        require(row["id"] in cases and row["method"] in methods, f"unknown record key at line {index + 1}")
        key = (row["id"], row["method"])
        require(key not in records, f"duplicate id+method: {key}")
        case, method = cases[key[0]], methods[key[1]]
        for field, expected in [("freeze_sha256", freeze_sha), ("source_sha256", method["source_sha256"]),
                                ("binary_sha256", method["binary_sha256"]), ("test_sha256", case["input_sha256"]),
                                ("selected", case["selected"]), ("public_number", case.get("public_number")),
                                ("source_group", case["source_group"])]:
            require(row.get(field) == expected, f"record {key}: {field} mismatch")
        for field in ("operation_count", "final_occupied_length_m", "minimum_trench_lower_bound_m"):
            require(row.get(field) == case["meta"][field], f"record {key}: frozen {field} mismatch")
        normalized, line_count = None, None
        if row.get("response_sha256") is not None and verify_transcripts:
            response_path = Path(row["judge_output_file"])
            if not response_path.is_absolute():
                response_path = directory / response_path
            normalized, line_count = response_hashes(response_path, row["response_sha256"], row["status"],
                canonical_official_output="native_binary" in frozen and "official_source_sha256" in frozen)
            response_files += 1
        require(row["status"] != "ok" or row.get("response_sha256") is not None,
                f"missing response hash on successful run: {key}")
        cpu, rss = row.get("solver_cpu_total_s"), row.get("solver_peak_rss_mb")
        for name, value in (("CPU", cpu), ("RSS", rss)):
            require(value is None or (finite_number(value) and value >= 0), f"invalid {name}: {key}")
        workers = row.get("workers")
        require(workers is None or (isinstance(workers, int) and not isinstance(workers, bool) and workers > 0),
                f"invalid concurrent worker count: {key}")
        valid = row["status"] == "ok"
        resource_pass = (cpu is not None and rss is not None and cpu < frozen["cpu_limit_s"] and rss < frozen["memory_limit_mib"])
        within_limits = valid and resource_pass
        require(row.get("within_limits") is within_limits, f"within_limits disagrees with measured status/resources: {key}")
        raw = None
        ratio = None
        if valid:
            trench = row.get("trench_length_m")
            occupied = case["meta"]["final_occupied_length_m"]
            lower_bound = case["meta"]["minimum_trench_lower_bound_m"]
            require(isinstance(trench, int) and trench > 0 and trench % 20 == 0,
                    f"invalid trench on successful run: {key}")
            require(row.get("occupied_length_m") == occupied and 0 <= occupied <= lower_bound <= trench,
                    f"successful F/LB/T inconsistent: {key}")
            raw = Fraction(occupied, trench)
            ratio = Fraction(lower_bound, trench)
            require(finite_number(row.get("kpi")) and math.isclose(row["kpi"], float(raw), rel_tol=1e-14, abs_tol=1e-14),
                    f"stored raw KPI disagrees with F/T: {key}")
            if verify_transcripts:
                require(line_count == case["meta"]["operation_count"], f"successful response line count mismatch: {key}")
        adjusted = raw if within_limits else Fraction(0)
        require(finite_number(row.get("contest_adjusted_kpi")) and
                math.isclose(row["contest_adjusted_kpi"], float(adjusted), rel_tol=1e-14, abs_tol=1e-14),
                f"stored adjusted KPI disagrees with exact reconstruction: {key}")
        records[key] = {"id": key[0], "method": key[1], "status": row["status"],
            "detail": row.get("detail", ""), "raw": raw, "adjusted": adjusted,
            "raw_bound_ratio": ratio,
            "adjusted_bound_ratio": ratio if within_limits else Fraction(0),
            "within_limits": within_limits, "valid": valid,
            "resource_failure": valid and not resource_pass,
            "cpu": cpu, "rss": rss, "workers": workers, "trench": row.get("trench_length_m"),
            "response_sha256": row.get("response_sha256"),
            "normalized_response_sha256": normalized, "started_unix": row.get("started_unix")}
    return records, {"records_snapshot_sha256": hashlib.sha256(payload).hexdigest(),
                     "records_snapshot_bytes": len(payload), "ignored_unfinished_tail_bytes": ignored_tail_bytes,
                     "verified_response_files": response_files,
                     "transcripts_read_and_rehashed": verify_transcripts,
                     "transcript_verification": "gzip decompression, SHA256 and LF count; native official checker emits canonical integer formatting" if verify_transcripts else "recorded hashes only"}


def summarize(rows):
    rows = list(rows)
    adjusted = [float(r["adjusted"]) for r in rows]
    raw = [float(r["raw"]) for r in rows if r["raw"] is not None]
    bounds = [float(r["adjusted_bound_ratio"]) for r in rows]
    raw_bounds = [float(r["raw_bound_ratio"]) for r in rows if r["raw_bound_ratio"] is not None]
    worker_groups = {}
    for workers in sorted({str(r.get("workers")) if r.get("workers") is not None else "unknown" for r in rows}):
        group = [r for r in rows if (str(r.get("workers")) if r.get("workers") is not None else "unknown") == workers]
        worker_groups[workers] = {"completed_runs": len(group),
            "scope": "measured solver resources grouped by runner concurrent worker count; no CPU affinity implied",
            "cpu_process_user_plus_system_s": resources([r["cpu"] for r in group if r["cpu"] is not None]),
            "peak_rss_MiB": resources([r["rss"] for r in group if r["rss"] is not None]),
            "invalid_or_protocol_failures": sum(not r["valid"] for r in group),
            "resource_failures_among_valid_runs": sum(r["resource_failure"] for r in group)}
    return {"completed_runs": len(rows), "contest_adjusted_kpi": distribution(adjusted),
            "raw_kpi_valid_scored_runs_only": distribution(raw),
            "contest_adjusted_kpi_over_U_equals_LB_over_T": distribution(bounds),
            "raw_LB_over_T_valid_scored_runs_only": distribution(raw_bounds),
            "counts_adjusted_kpi_below": {str(t): sum(r["adjusted"] < Fraction(str(t)) for r in rows) for t in (.85, .5, .1)},
            "counts_raw_kpi_below_valid_scored_runs_only": {
                str(t): sum(r["raw"] is not None and r["raw"] < Fraction(str(t)) for r in rows) for t in (.85, .5, .1)},
            "invalid_or_protocol_failures": sum(not r["valid"] for r in rows),
            "resource_failures_among_valid_runs": sum(r["resource_failure"] for r in rows),
            "contest_failures_total": sum(not r["within_limits"] for r in rows),
            "status_counts": dict(collections.Counter(r["status"] for r in rows)),
            "missing_cpu_measurements": sum(r["cpu"] is None for r in rows),
            "missing_rss_measurements": sum(r["rss"] is None for r in rows),
            "cpu_process_user_plus_system_s": resources([r["cpu"] for r in rows if r["cpu"] is not None]),
            "peak_rss_MiB": resources([r["rss"] for r in rows if r["rss"] is not None]),
            "resources_by_workers": worker_groups}


def case_description(case):
    meta = case["meta"]
    return {"id": case["id"], "selected": case["selected"], "public_number": case.get("public_number"),
            "origin": case["origin"], "source_group": case["source_group"],
            "operations": meta["operation_count"], "F": meta["final_occupied_length_m"],
            "LB": meta["minimum_trench_lower_bound_m"],
            "U": meta["final_occupied_length_m"] / meta["minimum_trench_lower_bound_m"]
                 if meta["minimum_trench_lower_bound_m"] else 0.0}


def public_result(row):
    return {"status": row["status"], "detail": row["detail"],
            "raw_kpi": float(row["raw"]) if row["raw"] is not None else None,
            "contest_adjusted_kpi": float(row["adjusted"]),
            "raw_LB_over_T": float(row["raw_bound_ratio"]) if row["raw_bound_ratio"] is not None else None,
            "contest_adjusted_LB_over_T": float(row["adjusted_bound_ratio"]),
            "within_limits": row["within_limits"], "resource_failure": row["resource_failure"],
            "trench_length_m": row["trench"], "cpu_process_s": row["cpu"], "peak_rss_MiB": row["rss"],
            "workers": row.get("workers"),
            "response_sha256": row["response_sha256"],
            "normalized_response_sha256": row["normalized_response_sha256"]}


def pair_summary(first, second, ids, records, cases):
    matched = sorted(case_id for case_id in ids if (case_id, first) in records and (case_id, second) in records)
    deltas = [(case_id, records[case_id, first]["adjusted"] - records[case_id, second]["adjusted"]) for case_id in matched]
    jointly_valid = [case_id for case_id in matched if records[case_id, first]["valid"] and records[case_id, second]["valid"]]
    raw_deltas = [(case_id, records[case_id, first]["raw"] - records[case_id, second]["raw"]) for case_id in jointly_valid]
    def extreme(item, metric="adjusted"):
        case_id, delta = item
        return {**case_description(cases[case_id]), "delta": float(delta),
                "first_kpi": float(records[case_id, first][metric]),
                "second_kpi": float(records[case_id, second][metric]),
                "first_workers": records[case_id, first].get("workers"),
                "second_workers": records[case_id, second].get("workers")}
    raw_summary = {
        "scope": "pairwise matched completed selected streams with both status=ok; resource-failing scored runs remain included to describe placements",
        "jointly_valid_count": len(jointly_valid), "jointly_valid_selected_ids": jointly_valid,
        "excluded_pairs_with_any_invalid_or_protocol_failure": len(matched) - len(jointly_valid),
        "included_pairs_with_any_resource_failure": sum(records[x, first]["resource_failure"] or records[x, second]["resource_failure"] for x in jointly_valid),
        "wins": sum(delta > 0 for _, delta in raw_deltas),
        "ties": sum(delta == 0 for _, delta in raw_deltas),
        "losses": sum(delta < 0 for _, delta in raw_deltas),
        "delta_mean_raw_kpi": math.fsum(float(delta) for _, delta in raw_deltas) / len(raw_deltas) if raw_deltas else None,
        "minimum_delta": extreme(min(raw_deltas, key=lambda x: (x[1], x[0])), "raw") if raw_deltas else None,
        "maximum_delta": extreme(max(raw_deltas, key=lambda x: (x[1], x[0])), "raw") if raw_deltas else None,
        "worker_pair_counts_first_second": dict(collections.Counter(
            f"{records[x, first].get('workers')}/{records[x, second].get('workers')}" for x in jointly_valid))}
    return {"first": first, "second": second, "scope": "pairwise matched completed selected streams",
            "matched_count": len(matched), "matched_selected_ids": matched,
            "wins": sum(delta > 0 for _, delta in deltas), "ties": sum(delta == 0 for _, delta in deltas),
            "losses": sum(delta < 0 for _, delta in deltas),
            "delta_mean_adjusted_kpi": math.fsum(float(delta) for _, delta in deltas) / len(deltas) if deltas else None,
            "minimum_delta": extreme(min(deltas, key=lambda x: (x[1], x[0]))) if deltas else None,
            "maximum_delta": extreme(max(deltas, key=lambda x: (x[1], x[0]))) if deltas else None,
            "raw_jointly_valid": raw_summary}


def analyze(directory: Path, verify_transcripts=False):
    freeze_path = directory / "freeze.json"
    frozen = json.loads(freeze_path.read_text())
    freeze_sha = sha_file(freeze_path)
    require(len({m["id"] for m in frozen["methods"]}) == len(frozen["methods"]), "duplicate method IDs in freeze")
    require(len({c["id"] for c in frozen["cases"]}) == len(frozen["cases"]), "duplicate case IDs in freeze")
    cases = {c["id"]: c for c in frozen["cases"]}
    methods = [m["id"] for m in frozen["methods"]]
    selected = sorted(c["id"] for c in frozen["cases"] if c["selected"])
    require(len(selected) == frozen["selected_count"], "selected_count mismatch")
    verification = verify_artifacts(directory, frozen)
    records, snapshot = load_records(directory, frozen, freeze_sha, verify_transcripts)
    matched = [case_id for case_id in selected if all((case_id, method) in records for method in methods)]
    selected_complete = len(matched) == len(selected)
    complete = len(records) == len(cases) * len(methods) and not snapshot["ignored_unfinished_tail_bytes"]
    panel = {m: summarize(records[case_id, m] for case_id in matched) for m in methods}
    representative_policies = [m for m in methods if m != "online_cj"]
    witness_ids, no_witness_ids, best_values = [], [], []
    best_counts = {m: {"best_or_tied": 0, "unique_best": 0} for m in representative_policies}
    for case_id in matched:
        has_witness = any(records[case_id, m]["raw"] is not None and records[case_id, m]["raw"] >= Fraction(17, 20)
                          for m in methods)
        (witness_ids if has_witness else no_witness_ids).append(case_id)
        valid_values = {m: records[case_id, m]["raw"] for m in representative_policies
                        if records[case_id, m]["raw"] is not None}
        if not valid_values:
            continue
        best = max(valid_values.values())
        best_values.append(float(best))
        winners = [m for m, value in valid_values.items() if value == best]
        for m in winners:
            best_counts[m]["best_or_tied"] += 1
            best_counts[m]["unique_best"] += len(winners) == 1
    portfolio = {"scope": "panel-matched completed selected streams; geometric raw KPI, resource penalties separate",
                 "representative_policies": representative_policies,
                 "cangjie_excluded_as_duplicate_policy": True,
                 "matched_count": len(matched),
                 "mean_best_observed_KPI": math.fsum(best_values) / len(best_values) if best_values else None,
                 "not_an_implementable_online_selector_or_true_optimum": True,
                 "best_counts": best_counts,
                 "KPI_at_least_085_with_observed_legal_placement": len(witness_ids),
                 "witness_ids": witness_ids,
                 "no_observed_085_witness_count": len(no_witness_ids),
                 "no_observed_085_witness_ids": no_witness_ids,
                 "no_witness_does_not_prove_optimum_below_085": True}
    observed = {}
    for method in methods:
        ids = [case_id for case_id in selected if (case_id, method) in records]
        observed[method] = {"scope": "method-specific completed selected subset; unequal subsets must not be ranked directly",
                            "selected_ids": ids, **summarize(records[case_id, method] for case_id in ids)}
    groups = {}
    for group in sorted({c["source_group"] for c in frozen["cases"] if c["selected"]}):
        ids = [case_id for case_id in matched if cases[case_id]["source_group"] == group]
        groups[group] = {"scope": "descriptive source group within panel-matched completed selected streams; not independent generating families",
                         "selected_total": sum(c["selected"] and c["source_group"] == group for c in frozen["cases"]),
                         "matched_completed_count": len(ids),
                         "methods": {m: summarize(records[case_id, m] for case_id in ids) for m in methods}}
    coverage_groups = {}
    coverage_path = directory / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text())
        require(coverage["artifacts_sha256"]["prototypes/pipes_all2537_comparison_20261020/freeze.json"] == freeze_sha,
                "coverage refers to a different freeze")
        previous = set(coverage["id_sets"]["old339_selected"])
        additional = set(coverage["id_sets"]["other_selected"])
        require(not previous.intersection(additional) and previous.union(additional) == set(selected),
                "previous/additional coverage does not partition selected corpus")
        for label in ("old339_selected", "other_selected", "public11"):
            all_ids = set(coverage["id_sets"][label])
            ids = sorted(all_ids.intersection(matched))
            coverage_groups[label] = {"selected_total": len(all_ids), "matched_completed_count": len(ids),
                "complete": len(ids) == len(all_ids),
                "scope": "previous port-validation membership by exact canonical input hash; additional inputs are archived, not an independent holdout",
                "methods": {m: summarize(records[case_id, m] for case_id in ids) for m in methods}}
    pairs = [pair_summary(a, b, selected, records, cases) for i, a in enumerate(methods) for b in methods[i + 1:]]
    parity = {"scope": "matched completed current C++ / Cangjie runs, selected and extra Open15 separately",
              "normalization": "per response line: integer tokens with canonical decimal spelling, single spaces, LF; empty lines ignored",
              "transcripts_rehashed": verify_transcripts,
              "progress_mode": "Without --verify-transcripts, equal recorded raw hashes imply equal normalized responses; differing raw hashes await normalization."}
    for label, ids in [("selected", selected), ("all_frozen_including_extra_open15", sorted(cases))]:
        paired = [case_id for case_id in ids if (case_id, "online_cpp") in records and (case_id, "online_cj") in records]
        verified_ids, equal_raw_ids, mismatches, unavailable = [], [], [], []
        for case_id in paired:
            a, b = records[case_id, "online_cpp"], records[case_id, "online_cj"]
            if (not verify_transcripts and a["response_sha256"] is not None and
                    a["response_sha256"] == b["response_sha256"]):
                equal_raw_ids.append(case_id)
            elif a["normalized_response_sha256"] is None or b["normalized_response_sha256"] is None:
                unavailable.append(case_id)
            elif a["normalized_response_sha256"] == b["normalized_response_sha256"]:
                verified_ids.append(case_id)
            else:
                mismatches.append({**case_description(cases[case_id]),
                    "cpp_status": a["status"], "cj_status": b["status"],
                    "cpp_hash": a["normalized_response_sha256"], "cj_hash": b["normalized_response_sha256"]})
        parity[label] = {"matched_completed_count": len(paired), "identical_normalized_responses": len(verified_ids),
                         "normalized_equality_inferred_from_equal_recorded_raw_hashes": len(equal_raw_ids),
                         "mismatches": mismatches, "hash_unavailable_ids": unavailable,
                         "raw_response_hash_equal_count": sum(records[x, "online_cpp"]["response_sha256"] is not None and
                             records[x, "online_cpp"]["response_sha256"] == records[x, "online_cj"]["response_sha256"] for x in paired)}
    open_cases = {c["public_number"]: c for c in frozen["cases"] if c.get("public_number") is not None}
    require(len(open_cases) == sum(c.get("public_number") is not None for c in frozen["cases"]), "duplicate public test numbers")
    open15 = {}
    for method in methods:
        available = [number for number, c in open_cases.items() if (c["id"], method) in records]
        has_all = set(open_cases) == set(range(1, 16)) and len(available) == 15
        entry = {"complete": has_all, "completed_public_numbers": sorted(available),
                 "weight_source": "frozen case.meta.weight; official rounded row weights and scores ignored"}
        if has_all:
            rows = [records[open_cases[i]["id"], method] for i in range(1, 16)]
            weights = [open_cases[i]["meta"]["weight"] for i in range(1, 16)]
            entry.update(weight_sum=math.fsum(weights),
                contest_adjusted_weighted_score=math.fsum(w * float(r["adjusted"]) for w, r in zip(weights, rows)),
                raw_weighted_score=math.fsum(w * float(r["raw"]) for w, r in zip(weights, rows)) if all(r["raw"] is not None for r in rows) else None,
                contest_failures=sum(not r["within_limits"] for r in rows))
        open15[method] = entry
    worst = {}
    for method in ("online_cpp", "replay_search"):
        ids = [case_id for case_id in selected if (case_id, method) in records]
        if method not in methods:
            continue
        def descriptions(key):
            return [{**case_description(cases[case_id]), **public_result(records[case_id, method])}
                    for case_id in sorted(ids, key=lambda x: (records[x, method][key], x))[:20]]
        worst[method] = {"scope": "method-specific completed selected subset",
                         "lowest_contest_adjusted_kpi": descriptions("adjusted"),
                         "lowest_contest_adjusted_LB_over_T": descriptions("adjusted_bound_ratio")}
    regressions = {}
    for baseline in ("primal_recent", "trial22", "hybrid"):
        ids = [case_id for case_id in selected if (case_id, "online_cpp") in records and (case_id, baseline) in records]
        delta = lambda x: records[x, "online_cpp"]["adjusted"] - records[x, baseline]["adjusted"]
        ids = sorted((x for x in ids if delta(x) < 0), key=lambda x: (delta(x), x))[:20]
        regressions[baseline] = {"scope": "pairwise matched completed selected streams; adjusted KPI losses only",
            "top20": [{**case_description(cases[x]), "delta": float(delta(x)),
                       "online_cpp": public_result(records[x, "online_cpp"]),
                       "baseline": public_result(records[x, baseline])} for x in ids]}
    result = {"schema_version": 1, "created_unix": time.time(), "freeze_sha256": freeze_sha,
        "complete": complete, "selected_complete": selected_complete,
        "expected_selected_streams": len(selected), "expected_all_streams": len(cases),
        "expected_runs": len(cases) * len(methods), "completed_runs": len(records),
        "matched_completed_selected_count": len(matched), "matched_completed_selected_ids": matched,
        "selected_summary_scope": "all frozen selected streams" if selected_complete else
            "PARTIAL: panel-matched completed selected streams only; not a 2537-stream estimate",
        "selected_panel_matched_summaries": panel, "best_observed_portfolio": portfolio,
        "all_selected_summaries": panel if selected_complete else None,
        "method_specific_selected_observed_summaries": observed,
        "all_completed_including_extra_open15_summaries": {m: summarize(r for r in records.values() if r["method"] == m) for m in methods},
        "pairwise": pairs, "response_parity_cpp_vs_cj": parity,
        "source_group_descriptives": groups, "previous_validation_coverage_groups": coverage_groups, "full_open15": open15,
        "worst20": worst, "largest_regressions_current_cpp": regressions,
        "per_case_results": [{**case_description(c), "methods": {m: public_result(records[c["id"], m])
                              for m in methods if (c["id"], m) in records}}
                             for c in frozen["cases"] if any((c["id"], m) in records for m in methods)],
        "hash_verification": {**verification, **snapshot},
        "definitions": {"KPI": "F/T reconstructed from frozen final occupied volume and measured trench; no official rounded score",
            "U": "F/LB, volume-only upper bound; not certified achievable optimum",
            "normalized": "KPI/U=LB/T, evaluated directly as LB/T",
            "contest_adjusted": "raw F/T only for status=ok and CPU<limit and RSS<limit; zero otherwise",
            "raw": "status=ok scored runs only; invalid outcomes remain null, not invented scores",
            "pairwise": "first minus second, exact rational F/T comparisons; arithmetic means use math.fsum of rational-to-float values",
            "raw_pairwise": "jointly status=ok selected intersections only; invalid pairs excluded, scored resource failures included; exact rational W/T/L",
            "percentiles": "linear interpolation at (n-1)*q", "resources": "solver process user+system CPU and measured peak RSS; sums include available measurements from failures",
            "workers": "concurrent runner workers recorded on each run; resource summaries also separated by this count, unknown stays explicit",
            "source_groups": "descriptive storage provenance groups; no independence or family-macro interpretation"},
        "limitations": ["Saved observed corpus; not an independent holdout or a hidden-score prediction.",
            "Partial method-specific summaries use unequal completed subsets; use panel-matched summaries for comparisons.",
            "Pairwise summaries use their own matched completed selected intersections, which can differ across pairs.",
            "Timer-dependent replay/search decisions and CPU measurements are host/load sensitive.",
            "Raw placement comparisons retain resource-failing scored runs; they do not establish contest admissibility. Worker-count strata may cover different inputs.",
            "No native Windows/G5420 validation is inferred from these host results."]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE)
    parser.add_argument("--out", type=Path, help="Default: DIRECTORY/analysis.json")
    parser.add_argument("--verify-transcripts", action="store_true",
                        help="Read/decompress every recorded response, verify raw hashes, compute normalized parity (final audit).")
    args = parser.parse_args()
    directory = args.directory.resolve()
    result = analyze(directory, args.verify_transcripts)
    output = args.out or directory / "analysis.json"
    # This file is a replaceable analysis snapshot, never the immutable records.
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temporary.replace(output)
    print(json.dumps({"complete": result["complete"], "completed_runs": result["completed_runs"],
                      "matched_completed_selected_count": result["matched_completed_selected_count"],
                      "output": str(output)}))


if __name__ == "__main__":
    main()
