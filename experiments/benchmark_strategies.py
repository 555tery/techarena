#!/usr/bin/env python3
"""Run a reproducible policy matrix through the online simulator."""
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "experiments/pipes_sim"
OPEN = sorted((ROOT / "data/pipes/open").glob("*.in"), key=lambda p: int(p.stem))
SYNTH = sorted((ROOT / "experiments/generated").glob("*.in"))
OUT = ROOT / "results/strategy-matrix"
ROW = re.compile(r"^(.*?) weight=([0-9.]+) alive=(\d+) H=(\d+) lb=(\d+) gap=(\d+) KPI=([0-9.eE+-]+)")

POLICIES = [
    ("bestfit_tail_left", "bf", "low", "left", True, 0),
    ("bestfit_all_left", "bf", "low", "left", False, 0),
    ("firstfit_tail_left", "ff", "low", "left", True, 0),
    ("firstfit_all_left", "ff", "low", "left", False, 0),
    ("firstfit_tail_highaddr", "ff", "high", "left", True, 0),
    ("bestfit_tail_highaddr", "bf", "high", "left", True, 0),
    ("bestfit_tail_oldest", "bf-old", "low", "left", True, 0),
    ("bestfit_tail_newest", "bf-new", "low", "left", True, 0),
    ("worstfit_tail_left", "wf", "low", "left", True, 0),
    ("worstfit_all_left", "wf", "low", "left", False, 0),
    ("worstfit_tail_highaddr", "wf", "high", "left", True, 0),
    ("nextfit_tail_left", "next", "low", "left", True, 0),
    ("nextfit_all_left", "next", "low", "left", False, 0),
    ("bestfit_tail_right", "bf", "low", "right", True, 0),
    ("bestfit_all_right", "bf", "low", "right", False, 0),
    ("bestfit_tail_center", "bf", "low", "center", True, 0),
    ("firstfit_tail_right", "ff", "low", "right", True, 0),
    ("bestfit_tail_nearsize", "bf", "low", "near-size", True, 0),
    ("bestfit_tail_nearage", "bf", "low", "near-age", True, 0),
    ("bestfit_all_nearsize", "bf", "low", "near-size", False, 0),
    ("bestfit_all_nearage", "bf", "low", "near-age", False, 0),
]
for threshold in (40, 200, 1000, 5000, 20000, 50000):
    POLICIES.append((f"hybrid_ff{threshold}_bf", "hybrid", "low", "left", True, threshold))


def run(config, files):
    name, policy, tie, side, preserve, threshold = config
    argv = [str(SIM), policy, *map(str, files), f"--tie={tie}", f"--side={side}"]
    if preserve:
        argv.append("--tail=preserve")
    if threshold:
        argv.append(f"--threshold={threshold}")
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=True)
    rows = {}
    for line in proc.stdout.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        path, weight, alive, h, lb, gap, kpi = m.groups()
        rows[Path(path).name] = {
            "weight": float(weight), "alive": int(alive), "H": int(h),
            "lower_bound": int(lb), "gap": int(gap), "KPI": float(kpi),
        }
    if len(rows) != len(files):
        raise RuntimeError(f"{name}: parsed {len(rows)} of {len(files)} simulator rows\n{proc.stdout[-1000:]}\n{proc.stderr}")
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for config in POLICIES:
        open_rows = run(config, OPEN)
        synth_rows = run(config, SYNTH)
        name = config[0]
        open_weighted = sum(r["weight"] * r["KPI"] for r in open_rows.values())
        synth_mean = sum(r["KPI"] for r in synth_rows.values()) / len(synth_rows)
        synth_gap_ratio = sum(r["gap"] / max(1, r["H"]) for r in synth_rows.values()) / len(synth_rows)
        synth_worst = min(r["KPI"] for r in synth_rows.values())
        rec = {
            "strategy": name,
            "open_weighted_score": open_weighted,
            "open_weight_sum": sum(r["weight"] for r in open_rows.values()),
            "synthetic_mean_KPI": synth_mean,
            "synthetic_worst_KPI": synth_worst,
            "synthetic_mean_H_over_lower_bound": sum(r["H"] / max(1, r["lower_bound"]) for r in synth_rows.values()) / len(synth_rows),
            "synthetic_mean_gap_over_H": synth_gap_ratio,
            "open": open_rows,
            "synthetic": synth_rows,
        }
        records.append(rec)
        print(f"{name:27s} open={open_weighted:.9f}/32.1  synthetic_mean={synth_mean:.6f}"
              f" worst={synth_worst:.6f}  mean_H/lb={rec['synthetic_mean_H_over_lower_bound']:.4f}")
    records.sort(key=lambda r: r["open_weighted_score"], reverse=True)
    (OUT / "matrix.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["strategy", "open_weighted_score", "open_weight_sum", "synthetic_mean_KPI",
                  "synthetic_worst_KPI", "synthetic_mean_H_over_lower_bound", "synthetic_mean_gap_over_H"]
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in records: w.writerow({k:r[k] for k in fields})
    print(f"saved {OUT / 'summary.csv'} and {OUT / 'matrix.json'}")


if __name__ == "__main__":
    main()
