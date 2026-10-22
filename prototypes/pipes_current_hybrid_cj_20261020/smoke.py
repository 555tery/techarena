#!/usr/bin/env python3
"""Old public inputs only; validate the port before freezing the full run."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "shinka-pipes/evaluator-native"))
import native_harness as nh

spec = importlib.util.spec_from_file_location("base", ROOT / "tools/pipes_harness.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
os.environ["cjProcessorNum"] = "1"
native = ROOT / "prototypes/pipes_all2537_comparison_20261020/native-build/native_runner"
rows = []
for number in [1, 2, 3, 8, 11, 15]:
    paired = []
    for method, binary in [("cpp", HERE / "cpp/solution"), ("cj", HERE / "bin/hybrid-cj")]:
        row = nh.run_case(base, [str(binary)], native, ROOT / f"data/pipes/open/{number}.in",
                          HERE / f"smoke/open{number}/{method}", 5, 240)
        response = Path(row["judge_output_file"]).read_bytes()
        row.update(method=method, public_number=number,
                   response_sha256=hashlib.sha256(response).hexdigest())
        assert row["status"] == "ok", row
        rows.append(row)
        paired.append(row)
    assert paired[0]["response_sha256"] == paired[1]["response_sha256"], number
    print(json.dumps({"open": number, "equal_responses": True,
                      "kpi": paired[1]["kpi"], "cj_cpu_s": paired[1]["solver_cpu_total_s"],
                      "cj_rss_mib": paired[1]["solver_peak_rss_mb"],
                      "diagnostic": paired[1]["candidate_stderr"]}), flush=True)
(HERE / "smoke.json").write_text(json.dumps(rows, indent=2) + "\n")
