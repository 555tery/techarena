#!/usr/bin/env python3
"""Fast simulator screening for the mixed endpoint policy; open winner is harness-verified separately."""
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
SIM = ROOT / "results/pipes/improvement/max_open_sequence/search_sim"
TESTS = sorted((ROOT / "data/pipes/open").glob("*.in"), key=lambda p: int(p.stem))
OUT = BASE / "reports" / "adaptive_grid"
ROW = re.compile(r"/open/(\d+)\.in weight=([0-9.]+).* H=(\d+).* KPI=([0-9.eE+-]+)")
WINDOWS = [1024, 2048, 4096]
SCALES = [50, 60, 70]
RIGHT_MAXES = [3, 4, 5]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for window in WINDOWS:
        for scale in SCALES:
            for right_max in RIGHT_MAXES:
                command = [str(SIM), "hist", *map(str, TESTS),
                           f"--history-window={window}", f"--unfit-scale={scale}",
                           "--side=small-right", f"--right-max={right_max}"]
                result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
                cases = {}
                for line in result.stdout.splitlines():
                    match = ROW.search(line)
                    if match:
                        case, weight, trench, kpi = match.groups()
                        cases[case] = {"weight": float(weight), "H": int(trench), "KPI": float(kpi)}
                if len(cases) != 15:
                    raise RuntimeError(f"could not parse all 15 cases: {command}\n{result.stdout[-2000:]}")
                score = sum(row["weight"] * row["KPI"] for row in cases.values())
                records.append({"window": window, "scale": scale, "right_max": right_max,
                                "weighted_score_sim": score, "cases": cases,
                                "command": " ".join(command)})
    records.sort(key=lambda row: row["weighted_score_sim"], reverse=True)
    for rank, row in enumerate(records, 1):
        row["rank"] = rank
    (OUT / "grid.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    fields = ["rank", "window", "scale", "right_max", "weighted_score_sim"]
    with (OUT / "grid.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row[key] for key in fields})
    manifest = {"simulator": str(SIM), "simulator_sha256": sha(SIM),
                "tests": [{"name": p.name, "sha256": sha(p)} for p in TESTS],
                "windows": WINDOWS, "scales": SCALES, "right_max_values": RIGHT_MAXES,
                "top_10": [{key: row[key] for key in fields} for row in records[:10]]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for row in records[:10]:
        print(f"{row['weighted_score_sim']:.12f} window={row['window']} scale={row['scale']} "
              f"right_max={row['right_max']}")


if __name__ == "__main__":
    main()
