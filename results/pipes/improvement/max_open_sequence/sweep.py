#!/usr/bin/env python3
"""Grid search for generic history-score parameters on all official open tests."""
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SIM = ROOT / "results/pipes/improvement/max_open_sequence/search_sim"
TESTS = sorted((ROOT / "data/pipes/open").glob("*.in"), key=lambda p: int(p.stem))
OUT = Path(__file__).resolve().parent
ROW = re.compile(r"/open/(\d+)\.in weight=([0-9.]+).* H=(\d+).* KPI=([0-9.eE+-]+)")
WINDOWS = [8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 512, 1024]
SCALES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100, 150, 200, 300]
SIDES = ["left", "right"]

records = []
for window in WINDOWS:
    for scale in SCALES:
        for side in SIDES:
            command = [str(SIM), "hist", *map(str, TESTS),
                       f"--history-window={window}", f"--unfit-scale={scale}",
                       f"--side={side}"]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
            cases = {}
            for line in result.stdout.splitlines():
                match = ROW.search(line)
                if match:
                    case, weight, trench, kpi = match.groups()
                    cases[case] = {"weight": float(weight), "H": int(trench), "KPI": float(kpi)}
            if len(cases) != 15:
                raise RuntimeError(f"could not parse all cases for {command}: {result.stdout[-2000:]}")
            score = sum(row["weight"] * row["KPI"] for row in cases.values())
            records.append({"window": window, "scale": scale, "side": side,
                            "weighted_score": score, "cases": cases})
records.sort(key=lambda row: row["weighted_score"], reverse=True)
(OUT / "grid.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
with (OUT / "grid.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=["rank", "window", "scale", "side", "weighted_score"])
    writer.writeheader()
    for rank, row in enumerate(records, 1):
        writer.writerow({"rank": rank, **{key: row[key] for key in ("window", "scale", "side", "weighted_score")}})
for row in records[:20]:
    print(f"{row['weighted_score']:.12f}  window={row['window']:4} scale={row['scale']:3} side={row['side']}")
print(f"saved {OUT / 'grid.csv'} and {OUT / 'grid.json'}")
