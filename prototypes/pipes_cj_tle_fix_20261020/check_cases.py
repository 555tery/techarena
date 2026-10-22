#!/usr/bin/env python3
"""Serial official-interactor tests, full process CPU, frozen response parity."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE.parent / "pipes_current_hybrid_cj_20261020"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "shinka-pipes/evaluator-native"))
import native_harness as nh
spec = importlib.util.spec_from_file_location("base", ROOT / "tools/pipes_harness.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--cases", type=int, nargs="+", default=list(range(1, 16)))
    args = parser.parse_args()
    os.environ["cjProcessorNum"] = "1"
    frozen = {
        r["public_number"]: r
        for r in map(json.loads, (BASE / "records.jsonl").read_text().splitlines())
        if r["method"] == "hybrid_cj" and r["public_number"] is not None
    }
    native = ROOT / "prototypes/pipes_all2537_comparison_20261020/native-build/native_runner"
    results = []
    for n in args.cases:
        dest = HERE / "checks" / args.name / f"open{n}"
        assert not dest.exists(), dest
        row = nh.run_case(base, [str(args.binary.resolve())], native, ROOT / f"data/pipes/open/{n}.in", dest, 5, 240)
        response = Path(row["judge_output_file"]).read_bytes()
        row.update(public_number=n, response_sha256=hashlib.sha256(response).hexdigest(),
                   response_equal=response == gzip.open(frozen[n]["judge_output_file"], "rb").read())
        row["within_limits"] = (row["status"] == "ok" and row["solver_cpu_total_s"] is not None and
                                row["solver_cpu_total_s"] < 5 and row["solver_peak_rss_mb"] is not None and
                                row["solver_peak_rss_mb"] < 256)
        results.append(row)
        (HERE / "checks" / args.name / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps({k: row[k] for k in ("public_number", "status", "response_equal", "solver_cpu_total_s", "solver_peak_rss_mb", "candidate_stderr")}), flush=True)
        if row["status"] != "ok" or not row["response_equal"]:
            raise SystemExit("correctness or parity failure")
    if not all(r["within_limits"] for r in results):
        raise SystemExit("resource failure")

if __name__ == "__main__":
    main()
