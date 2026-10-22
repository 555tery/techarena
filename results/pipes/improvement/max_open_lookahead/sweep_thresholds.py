from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = OUT / "candidate.cpp"
THRESHOLDS = [1, 2, 4, 8, 16, 32, 64]
rows = []
for threshold in THRESHOLDS:
    source = OUT / f"batch_threshold_{threshold}.cpp"
    binary = OUT / "bin" / f"batch_threshold_{threshold}"
    report = OUT / "threshold_sweep" / str(threshold)
    content = BASE.read_text(encoding="utf-8")
    old = "predictiveRightPlacement = currentBatchPlacements >= 8"
    if content.count(old) != 1:
        raise RuntimeError(f"expected one threshold expression in {BASE}")
    source.write_text(content.replace(old, f"predictiveRightPlacement = currentBatchPlacements >= {threshold}"), encoding="utf-8")
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
        ["python3", str(ROOT / "tools/pipes_harness.py"), "--solver", str(binary), "--name", f"batch_threshold_{threshold}", "--interactor", str(ROOT / "tools/interactor"), "--tests", str(ROOT / "data/pipes/open/5.in"), "--out", str(report)],
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
        "threshold": threshold,
        "status": case["status"],
        "kpi": case["kpi"],
        "weighted_score": case["weighted_score"],
        "trench_m": case["trench_length_m"],
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "report": str(report),
    })
    print(f"threshold={threshold:>2} KPI={case['kpi']:.12f} H={case['trench_length_m']} status={case['status']}")
with (OUT / "threshold_sweep.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
(OUT / "threshold_sweep.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
