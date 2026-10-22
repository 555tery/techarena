#!/usr/bin/env python3
"""Build an audit table from already saved TECH ARENA Pipes results; runs no tests."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "results/pipes/improvement/macro_policy_search"
BASE_MANIFEST = json.loads((ROOT / "results/pipes/final/manifest.json").read_text())
BASE = BASE_MANIFEST["open15"]
BASE_CASES = {str(x["case"]): x for x in BASE["per_case"]}
EXPECTED_INPUTS = {case: row["input_sha256"] for case, row in BASE_CASES.items()}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_csv(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

catalog = []
valid_full = []
excluded = []
for path in sorted((ROOT / "results/pipes").rglob("summary.json")):
    try:
        summary = json.loads(path.read_text())
    except Exception:
        continue
    records = summary.get("records", [])
    if not (summary.get("is_official_open_test_set") and summary.get("case_count") == 15 and len(records) == 15):
        continue
    hashes = {str(r.get("case")): r.get("test_sha256") for r in records}
    input_match = hashes == EXPECTED_INPUTS
    all_ok = summary.get("ok_count") == 15 and all(r.get("status") == "ok" for r in records)
    rel = path.relative_to(ROOT).as_posix()
    cases_csv = path.with_name("cases.csv")
    entry = {
        "candidate_id": path.parent.relative_to(ROOT).as_posix().replace("/", "__"),
        "summary_path": rel,
        "summary_sha256": sha(path),
        "cases_csv_path": cases_csv.relative_to(ROOT).as_posix() if cases_csv.exists() else "",
        "cases_csv_sha256": sha(cases_csv) if cases_csv.exists() else "",
        "strategy": summary.get("strategy", ""),
        "weighted_score_sum": summary.get("weighted_score_sum"),
        "weight_sum": summary.get("weight_sum"),
        "case_count": summary.get("case_count"),
        "ok_count": summary.get("ok_count"),
        "same_current_input_hashes": input_match,
        "all_15_protocol_ok": all_ok,
        "max_solver_cpu_s": max((r.get("solver_cpu_total_s", 0) or 0) for r in records),
        "max_solver_peak_rss_mib": max((r.get("solver_peak_rss_mb", 0) or 0) for r in records),
        "solver_argv": json.dumps(summary.get("solver_argv", []), ensure_ascii=False),
    }
    catalog.append(entry)
    if input_match and all_ok:
        valid_full.append((path, summary, entry))
    else:
        excluded.append(entry)

catalog_fields = list(catalog[0]) if catalog else []
write_csv(OUT / "full15_candidate_catalog.csv", catalog, catalog_fields)

full_rows = []
by_case = {str(c): [] for c in range(1, 16)}
for path, summary, meta in valid_full:
    for record in summary["records"]:
        c = str(record["case"])
        baseline = BASE_CASES[c]
        row = {
            "candidate_id": meta["candidate_id"],
            "summary_path": meta["summary_path"],
            "summary_sha256": meta["summary_sha256"],
            "strategy": meta["strategy"],
            "candidate_total_score": summary["weighted_score_sum"],
            "case": c,
            "official_weight": record.get("official_weight"),
            "test_sha256": record.get("test_sha256"),
            "status": record.get("status"),
            "candidate_trench_m": record.get("trench_length_m"),
            "candidate_weighted_score": record.get("weighted_score"),
            "baseline_trench_m": baseline["trench_length_m"],
            "baseline_weighted_score": baseline["weighted_score"],
            "delta_trench_vs_current_final_m": (baseline["trench_length_m"] - record["trench_length_m"]),
            "delta_weighted_score_vs_current_final": (record["weighted_score"] - baseline["weighted_score"]),
            "solver_cpu_s": record.get("solver_cpu_total_s"),
            "solver_peak_rss_mib": record.get("solver_peak_rss_mb"),
        }
        full_rows.append(row)
        by_case[c].append(row)
full_fields = list(full_rows[0]) if full_rows else []
write_csv(OUT / "full15_per_case_results.csv", full_rows, full_fields)

best_rows = []
for c in map(str, range(1, 16)):
    best = max(by_case[c], key=lambda r: (r["candidate_weighted_score"], -r["candidate_trench_m"]))
    base = BASE_CASES[c]
    best_rows.append({
        "case": c,
        "official_weight": base["official_weight"],
        "baseline_trench_m": base["trench_length_m"],
        "baseline_weighted_score": base["weighted_score"],
        "oracle_best_trench_m": best["candidate_trench_m"],
        "oracle_best_weighted_score": best["candidate_weighted_score"],
        "delta_trench_m": best["delta_trench_vs_current_final_m"],
        "delta_weighted_score": best["delta_weighted_score_vs_current_final"],
        "winning_candidate_id": best["candidate_id"],
        "winning_strategy": best["strategy"],
        "winning_summary_path": best["summary_path"],
        "winning_summary_sha256": best["summary_sha256"],
    })
write_csv(OUT / "full15_hindsight_envelope.csv", best_rows, list(best_rows[0]))

macro = json.loads((OUT / "runs/blocks/macro_screen_summary.json").read_text())
macro_rows = []
for r in macro["results"]:
    row = {
        "variant_id": r["run_id"],
        "scope": "partial_screen_only",
        "case_screened": r["case"],
        "block_start_op_diagnostic_only": r["block_start_op"],
        "block_end_op_diagnostic_only": r["block_end_op"],
        "block_length": r["block_length"],
        "selection_stratum": r["selection_stratum"],
        "policy": r["policy"],
        "candidate_trench_m_after_full_test_suffix": r["candidate_trench_m"],
        "candidate_weighted_score_for_screened_case": r["candidate_weighted_score"],
        "delta_trench_vs_baseline_m": r["delta_trench_m"],
        "delta_weighted_score_vs_baseline": r["delta_weighted_score"],
        "cpu_s": r["candidate_cpu_s"],
        "rss_mib": r["candidate_rss_mib"],
        "input_sha256": r["input_sha256"],
        "judge_trace_sha256": r["output_sha256"],
    }
    for c in range(1, 16):
        row[f"case_{c}_weighted_score"] = r["candidate_weighted_score"] if c == r["case"] else ""
        row[f"case_{c}_trench_m"] = r["candidate_trench_m"] if c == r["case"] else ""
    macro_rows.append(row)
write_csv(OUT / "macro_partial_screen_only.csv", macro_rows, list(macro_rows[0]))

macro_best = []
for c in (5, 9, 15):
    rows = [r for r in macro["results"] if r["case"] == c]
    best = max(rows, key=lambda r: r["delta_weighted_score"])
    macro_best.append({
        "case": c,
        "coverage": "partial_block_screen_only",
        "baseline_trench_m": best["baseline_trench_m"],
        "best_screen_trench_m": best["candidate_trench_m"],
        "delta_trench_m": best["delta_trench_m"],
        "best_screen_weighted_score": best["candidate_weighted_score"],
        "delta_weighted_score": best["delta_weighted_score"],
        "variant_id": best["run_id"],
        "policy": best["policy"],
        "block_length": best["block_length"],
        "diagnostic_block_start_op": best["block_start_op"],
        "status": best["status"],
    })
write_csv(OUT / "macro_screen_best_by_test.csv", macro_best, list(macro_best[0]))

block_groups = {}
for r in macro["results"]:
    key = (r["case"], r["block_start_op"], r["block_length"], r["selection_stratum"])
    block_groups.setdefault(key, []).append(r)
macro_block_best = []
for (case, start, length, stratum), rows in sorted(block_groups.items()):
    best = max(rows, key=lambda r: r["delta_weighted_score"])
    row = {
        "case": case,
        "diagnostic_block_start_op": start,
        "block_length": length,
        "selection_stratum": stratum,
        "best_policy_in_this_block_hindsight": best["policy"],
        "best_delta_trench_m": best["delta_trench_m"],
        "best_delta_weighted_score": best["delta_weighted_score"],
        "best_variant_id": best["run_id"],
        "best_variant_status": best["status"],
    }
    for policy in ("first_fit", "tail_first", "tail_only", "no_cohort"):
        r = next(r for r in rows if r["policy"] == policy)
        row[f"{policy}_delta_trench_m"] = r["delta_trench_m"]
        row[f"{policy}_delta_weighted_score"] = r["delta_weighted_score"]
    macro_block_best.append(row)
write_csv(OUT / "macro_best_policy_by_block.csv", macro_block_best, list(macro_block_best[0]))

full_envelope_score = sum(float(r["oracle_best_weighted_score"]) for r in best_rows)
full_delta = full_envelope_score - float(BASE["weighted_score_sum"])
macro_delta = sum(float(r["delta_weighted_score"]) for r in macro_best)
manifest = {
    "description": "Derived retrospective comparison only; no test execution. Hindsight per-case maxima are not one deployable candidate.",
    "current_final": {
        "score": BASE["weighted_score_sum"],
        "weight_sum": BASE["weight_sum"],
        "source_sha256": sha(ROOT / "results/pipes/final/solution.cpp"),
        "canonical_source_sha256": sha(ROOT / "src/pipes.cpp"),
    },
    "full_open15_inventory": {
        "official_full15_summary_artifacts_found": len(catalog),
        "same_exact_15_input_hashes": sum(1 for r in catalog if r["same_current_input_hashes"]),
        "same_inputs_and_all_15_protocol_ok": len(valid_full),
        "excluded_input_mismatch_or_protocol_failure": len(excluded),
        "case_result_rows_in_envelope_input": len(full_rows),
        "scope": "Only saved summary.json artifacts marked official_open_test_set with 15 records; input SHA-256 for every case must match current final manifest. No new runs were made.",
    },
    "full_open15_hindsight_envelope": {
        "score_sum_of_independent_per_case_maxima": full_envelope_score,
        "delta_vs_current_final": full_delta,
        "important_limitation": "Unattainable hindsight oracle: each case may select a different policy/run from 275 full-Open15 experiments. It is not a scored solution and has severe multiple-selection bias; no single causal online classifier was tested.",
        "per_case_csv": "results/pipes/improvement/macro_policy_search/full15_hindsight_envelope.csv",
        "all_candidate_case_rows_csv": "results/pipes/improvement/macro_policy_search/full15_per_case_results.csv",
        "candidate_catalog_csv": "results/pipes/improvement/macro_policy_search/full15_candidate_catalog.csv",
    },
    "macro_policy_screen": {
        "variants_completed": macro["variants"],
        "protocol_ok": macro["protocol_ok"],
        "coverage": [5, 9, 15],
        "unique_diagnostic_blocks": 30,
        "policies_per_block": 4,
        "best_per_case_screen_delta_sum": macro_delta,
        "scope": "Partial block screens only. Each record has one tested case; all other case columns are blank. This is not an official Open15 candidate.",
        "rows_csv": "results/pipes/improvement/macro_policy_search/macro_partial_screen_only.csv",
        "best_by_screened_case_csv": "results/pipes/improvement/macro_policy_search/macro_screen_best_by_test.csv",
        "best_by_diagnostic_block_csv": "results/pipes/improvement/macro_policy_search/macro_best_policy_by_block.csv",
    },
    "generated_files": {},
}
for filename in ("full15_candidate_catalog.csv", "full15_per_case_results.csv", "full15_hindsight_envelope.csv", "macro_partial_screen_only.csv", "macro_screen_best_by_test.csv", "macro_best_policy_by_block.csv"):
    p = OUT / filename
    manifest["generated_files"][filename] = {"sha256": sha(p), "rows": sum(1 for _ in p.open()) - 1}
(OUT / "envelope_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({
    "full15_inventory": manifest["full_open15_inventory"],
    "hindsight_envelope": manifest["full_open15_hindsight_envelope"],
    "macro_screen_best_per_case_delta_sum": macro_delta,
    "generated_files": manifest["generated_files"],
}, indent=2, ensure_ascii=False))
