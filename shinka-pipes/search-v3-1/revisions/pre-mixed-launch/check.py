#!/usr/bin/env python3
"""Verify only prepared input structure and metadata. Never execute a candidate."""

from collections import Counter
import json

from evaluator import load_search, verify_snapshot
from generate import FAMILIES, BASE_FAMILIES, LEGACY, V2, overview
from micro import verify_layout_witness
from support import ROOT, digest, verify_dependencies


def check_preparation(reparse=True):
    main = load_search()
    protocol = json.loads((ROOT / "protocol.json").read_text())
    directory = ROOT / "stress/data"
    if digest(directory / "manifest.json") != protocol["manifest_sha256"]["stress"]:
        raise ValueError("stress manifest changed")
    stress = json.loads((directory / "manifest.json").read_text())
    if (stress["version"] != "search-v3.1" or stress["split"] != "stress"
            or stress["role"] != "diagnostic_only" or stress["fitness"] is not None
            or stress["case_count"] != 64 or len(stress["cases"]) != 64
            or stress["cases_per_family"] != 2 or stress["families"] != list(BASE_FAMILIES)
            or Counter(c["family"] for c in stress["cases"]) != {f: 2 for f in BASE_FAMILIES}
            or {c["file"] for c in stress["cases"]} != {p.name for p in directory.glob("*.in")}):
        raise ValueError("wrong diagnostic coverage or role")
    if (main["families"] != list(FAMILIES)
            or Counter(c["regime"] for c in main["cases"]) != {"high": 87, "moderate": 33, "rounding": 8, "micro": 24}
            or Counter(c["mechanism_block"] for c in main["cases"]) != {"broad_prior": 64, "expanded_mechanisms": 64, "micro": 24}):
        raise ValueError("predeclared diversity allocation changed")
    parser = V2.parser_module() if reparse else None
    hashes, seeds, checked = set(), set(), 0
    for suite, directory in ((main, ROOT / "task/data/search"), (stress, ROOT / "stress/data")):
        for case in suite["cases"]:
            path = directory / case["file"]
            if (path.name != case["file"] or path.suffix != ".in" or digest(path) != case["sha256"]
                    or case["sha256"] in hashes or case["seed"] in seeds):
                raise ValueError("input hash, filename or distinctness failed")
            hashes.add(case["sha256"])
            seeds.add(case["seed"])
            stats = case["stats"]
            alpha = stats["final_live_volume"] / stats["volume_lower_bound"]
            if (case["final_to_bound"] != alpha or not 1 <= case["operations"] <= case["operation_budget"] <= 200_000
                    or stats["operation_count"] != case["operations"]
                    or case["termination"]["appended_insertions"] != 0
                    or suite["split"] == "stress" and alpha > .30):
                raise ValueError("statistics, budget or termination policy changed")
            if parser:
                parsed = parser.parse_test(path)
                expected = {"operation_count": case["operations"], "weight": 1., "test_sha256": case["sha256"],
                            "peak_live_pipe_length_m": stats["peak_live_volume"],
                            "final_occupied_length_m": stats["final_live_volume"],
                            "minimum_trench_lower_bound_m": stats["volume_lower_bound"]}
                if any(parsed[k] != v for k, v in expected.items()):
                    raise ValueError("independent parser disagrees")
                if case["regime"] == "micro":
                    tokens = path.read_text(encoding="ascii").split()
                    commands = list(map(int, tokens[2:2 + case["operations"]]))
                    verify_layout_witness(commands, case)
            checked += 1
    return {"version": "search-v3.1", "status": "prepared_not_run", "cases_checked": checked,
            "independent_parser_cases": checked if reparse else 0, "support_files": verify_snapshot(),
            "search": overview(main["cases"]), "stress": overview(stress["cases"]),
            "preserved_dependencies": len(verify_dependencies(include_stress=True)),
            "historical_active_pointer": "excluded: a prior run can update its own status",
            "solvers_executed": 0, "compiler_runs": 0, "interactor_runs": 0, "model_requests": 0,
            "validation_files_accessed": False, "open15_files_read": False}


if __name__ == "__main__":
    print(json.dumps(check_preparation(), indent=2))
