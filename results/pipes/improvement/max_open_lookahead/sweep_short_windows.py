from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = OUT / "candidate_v6_w1024_short_predictor.cpp"
WINDOWS = [8, 16, 32, 48, 64, 96, 128, 192, 256, 512, 1024]
rows = []
for window in WINDOWS:
    source = OUT / f"candidate_v6_short_{window}.cpp"
    binary = OUT / "bin" / f"candidate_v6_short_{window}"
    report = OUT / "short_window_sweep" / str(window)
    content = BASE.read_text(encoding="utf-8")
    old = "shortRecentLengths.size() > 128"
    if content.count(old) != 1:
        raise RuntimeError(f"expected one short-window expression in {BASE}")
    source.write_text(content.replace(old, f"shortRecentLengths.size() > {window}"), encoding="utf-8")
    build = subprocess.run(
        ["g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion", "-Wshadow", "-pedantic", "-Werror", str(source), "-o", str(binary)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if build.returncode:
        raise RuntimeError(build.stderr)
    run = subprocess.run(
        ["python3", str(ROOT / "tools/pipes_harness.py"), "--solver", str(binary), "--name", f"window1024_predictive_short_{window}", "--interactor", str(ROOT / "tools/interactor"), "--tests", str(ROOT / "data/pipes/open/5.in"), "--out", str(report)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if run.returncode:
        raise RuntimeError(run.stdout + "\n" + run.stderr)
    result = json.loads((report / "summary.json").read_text(encoding="utf-8"))
    case = result["records"][0]
    rows.append({
        "predictive_window": window,
        "status": case["status"],
        "kpi": case["kpi"],
        "weighted_score": case["weighted_score"],
        "trench_m": case["trench_length_m"],
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "report": str(report),
    })
    print(f"window={window:>4} KPI={case['kpi']:.12f} H={case['trench_length_m']} status={case['status']}")
with (OUT / "short_window_sweep.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
(OUT / "short_window_sweep.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
