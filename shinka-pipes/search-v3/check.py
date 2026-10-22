#!/usr/bin/env python3
"""Structural corpus/snapshot checks only. No compiler, candidate, checker or model."""

from collections import Counter
import json

from evaluator import load_search, verify_snapshot
from generate import V2, overview
from support import ROOT, digest, verify_dependencies


def check_preparation(reparse=True):
    count = verify_snapshot()
    main = load_search()
    protocol = json.loads((ROOT / "protocol.json").read_text())
    path = ROOT / "stress/data"
    if digest(path / "manifest.json") != protocol["manifest_sha256"]["stress"]:
        raise ValueError("stress manifest changed")
    stress = json.loads((path / "manifest.json").read_text())
    if (stress["version"] != "search-v3" or stress["split"] != "stress"
            or stress["role"] != "diagnostic_only" or stress["fitness"] is not None
            or stress["case_count"] != 32 or len(stress["cases"]) != 32
            or stress["cases_per_family"] != 2
            or Counter(c["family"] for c in stress["cases"]) != {f: 2 for f in main["families"]}
            or {c["file"] for c in stress["cases"]} != {p.name for p in path.glob("*.in")}):
        raise ValueError("wrong stress coverage or role")
    parser = V2.parser_module() if reparse else None
    seen_hashes, seen_seeds, cases_checked = set(), set(), 0
    for suite, directory in ((main, ROOT / "task/data/search"), (stress, path)):
        for case in suite["cases"]:
            file = directory / case["file"]
            if (file.name != case["file"] or file.suffix != ".in"
                    or digest(file) != case["sha256"]
                    or case["seed"] in seen_seeds or case["sha256"] in seen_hashes):
                raise ValueError("input hash, filename or distinctness failure")
            seen_hashes.add(case["sha256"])
            seen_seeds.add(case["seed"])
            stats = case["stats"]
            alpha = stats["final_live_volume"] / stats["volume_lower_bound"]
            if (case["final_to_bound"] != alpha or not 1 <= case["operations"] <= 200_000
                    or stats["operation_count"] != case["operations"]):
                raise ValueError("input statistics changed")
            if suite["split"] == "search":
                if (alpha < .95 or case["termination"]["appended_operations"] != 0
                        or case["operations"] < .75 * case["source_operations"]
                        or stats["deletions"] < max(64, .05 * case["operations"])):
                    raise ValueError("main occupancy, churn or natural-endpoint rule failed")
            elif alpha > .30 or case["termination"]["appended_insertions"] != 0:
                raise ValueError("stress drain rule failed")
            if parser:
                parsed = parser.parse_test(file)
                expected = {"operation_count": case["operations"], "weight": 1., "test_sha256": case["sha256"],
                            "peak_live_pipe_length_m": stats["peak_live_volume"],
                            "final_occupied_length_m": stats["final_live_volume"],
                            "minimum_trench_lower_bound_m": stats["volume_lower_bound"]}
                if any(parsed[k] != v for k, v in expected.items()):
                    raise ValueError("independent parser disagrees")
            cases_checked += 1
    return {"version": "search-v3", "status": "prepared_not_run", "support_files": count,
            "cases_checked": cases_checked, "independent_parser_cases": cases_checked if reparse else 0,
            "search": overview(main["cases"]), "stress": overview(stress["cases"]),
            "preserved_dependencies": len(verify_dependencies(include_active=True)),
            "solvers_executed": 0, "interactor_runs": 0, "compiler_runs": 0, "model_requests": 0,
            "stress_in_fitness": False, "heldout_files_accessed": False}


if __name__ == "__main__":
    print(json.dumps(check_preparation(), indent=2))
