#!/usr/bin/env python3
"""Fresh paired timing on eight predetermined SEARCH cases, not a fitness gate."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
FAST = ROOT.parent / "evaluator-fast"
sys.path.insert(0, str(FAST))
sys.path.insert(0, str(ROOT))
from reference import BASE, digest, check_reference
from fast_harness import build_harness as selector
from native_harness import build_harness as native


def main():
    full = json.loads((OUT / "summary.json").read_text())
    assert full["correct"] and full["reference_unchanged"]
    meta = json.loads((OUT / "native/metrics.json").read_text())
    preparation = json.loads((OUT / "preflight.json").read_text())["native_preparation"]
    runner = Path(preparation["binary"])
    assert digest(runner) == meta["native_binary_sha256"]
    assert meta["native_binary_cache_key"] == preparation["cache_key"]
    before = check_reference()
    manifest = json.loads((BASE / "task/data/search/manifest.json").read_text())
    # Every second family; median operation-count variant within each family.
    # Selection uses workload metadata only, never scores or measured times.
    selected = []
    for family in sorted(manifest["families"])[::2]:
        cases = sorted((c for c in manifest["cases"] if c["family"] == family),
                       key=lambda c: (c["stats"]["operation_count"], c["file"]))
        selected.append(cases[4])
    records = {"selector": [], "native": []}
    with tempfile.TemporaryDirectory(prefix="pipes-native-paired-") as temporary:
        directory = Path(temporary)
        solver, official = directory / "solver", directory / "official"
        for command in (
            [shutil.which("g++"), "-O2", "-std=c++20", "-pipe", str(OUT / "baseline.cpp"), "-o", str(solver)],
            [shutil.which("g++"), "-O2", "-std=c++17", "-pipe", "-I", str(BASE / "task/vendor"),
             str(BASE / "task/vendor/interactor.cpp"), "-o", str(official)],
        ):
            subprocess.run(command, capture_output=True, text=True, timeout=120, check=True)
        for index, case in enumerate(selected):
            traces = set()
            pair = []
            for name in (("selector", "native") if index % 2 == 0 else ("native", "selector")):
                harness, checker = (selector(), official) if name == "selector" else (native(), runner)
                record = harness.run_case([str(solver)], checker, BASE / "task/data/search" / case["file"],
                                          directory / f"{index}-{name}", 5, 180)
                assert record["status"] == "ok", record
                assert record["solver_cpu_total_s"] < 5 and record["solver_peak_rss_mb"] < 256
                traces.add(digest(Path(record["judge_output_file"])))
                values = {key: record[key] for key in ("wall_orchestration_s", "trench_length_m", "kpi",
                                                       "solver_cpu_total_s", "solver_peak_rss_mb")}
                values.update(case=case["id"], family=case["family"])
                records[name].append(values)
                pair.append(values)
                print(name, case["file"], f"{record['wall_orchestration_s']:.3f}s", flush=True)
            assert len(traces) == 1 and pair[0]["trench_length_m"] == pair[1]["trench_length_m"]
    times = {name: sum(row["wall_orchestration_s"] for row in rows) for name, rows in records.items()}
    assert before == check_reference()
    report = {"scope": "eight paired SEARCH cases, both implementations measured afresh, fixed saved baseline",
              "selection": "sorted families[::2], sorted variants by operation_count/file at index4",
              "selected_cases": [case["id"] for case in selected],
              "operations": sum(case["stats"]["operation_count"] for case in selected),
              "records": records, "wall_sums_s": times, "speedup_over_selector": times["selector"] / times["native"],
              "all_transcripts_identical": True, "implementation_unchanged": full["implementation_unchanged"],
              "fitness_not_computed_from_subset": True}
    with (OUT / "paired-speed.json").open("x") as stream:json.dump(report, stream, indent=2)
    print(json.dumps({"wall_sums_s": times, "speedup": report["speedup_over_selector"]}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
