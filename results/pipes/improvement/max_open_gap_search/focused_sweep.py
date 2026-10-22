#!/usr/bin/env python3
"""Small official-interactor sweep around W=1024, scale=50, right-end placement."""
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
SRC = BASE / "src/gap_search.cpp"
BIN = BASE / "binaries"
REPORT = BASE / "reports"
HARNESS = ROOT / "tools/pipes_harness.py"
INTERACTOR = ROOT / "tools/interactor"
TESTS = ROOT / "data/pipes/open"
S50_REPORT = REPORT / "s50_baseline/summary.json"
FOCUS = [(512, 50), (768, 50), (1024, 32), (1024, 40), (1024, 50),
         (1024, 60), (1024, 70), (1024, 100), (1536, 50), (2048, 50)]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def read_records(path):
    data = json.loads(Path(path).read_text())
    return {str(row["case"]): row for row in data["records"]}


def run_one(window, scale):
    name = f"right_w{window}_s{scale}"
    binary = BIN / name
    compile_command = ["g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
                       "-Wshadow", "-Werror", "-pedantic", "-DPIPES_POLICY=7",
                       f"-DPIPES_WINDOW={window}", f"-DPIPES_SCALE={scale}",
                       "-DPIPES_PLACE_RIGHT=1", "-DPIPES_TIE_HIGH_ADDRESS=0",
                       str(SRC), "-o", str(binary)]
    subprocess.run(compile_command, cwd=ROOT, check=True)
    out = REPORT / name
    command = [sys.executable, str(HARNESS), "--solver", str(binary), "--name", name,
               "--interactor", str(INTERACTOR), "--tests", str(TESTS), "--out", str(out)]
    start = time.monotonic()
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    result = {"name": name, "window": window, "scale": scale,
              "compile_command": " ".join(compile_command), "binary": str(binary),
              "binary_sha256": sha(binary), "compile_source_sha256": sha(SRC),
              "run_elapsed_s": time.monotonic() - start,
              "harness_returncode": proc.returncode,
              "harness_stdout": proc.stdout[-3000:], "harness_stderr": proc.stderr[-3000:]}
    if proc.returncode == 0:
        result["summary"] = json.loads((out / "summary.json").read_text())
        result["weighted_score"] = result["summary"]["weighted_score_sum"]
        result["valid"] = result["summary"]["ok_count"]
    return result


def main():
    BIN.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    s50 = json.loads(S50_REPORT.read_text())
    s50_score = s50["weighted_score_sum"]
    base = read_records(S50_REPORT)
    results = []
    for window, scale in FOCUS:
        entry = run_one(window, scale)
        results.append(entry)
        if entry["harness_returncode"] == 0:
            print(f"{entry['name']}: {entry['weighted_score']:.12f} "
                  f"({entry['weighted_score'] - s50_score:+.12f} vs S50), "
                  f"valid={entry['valid']}/15", flush=True)
        else:
            print(f"{entry['name']}: harness failure {entry['harness_returncode']}", flush=True)
        manifest = {"source": str(SRC), "source_sha256": sha(SRC),
                    "interactor": str(INTERACTOR), "interactor_sha256": sha(INTERACTOR),
                    "tests_dir": str(TESTS), "candidate_runs": results}
        (REPORT / "focused_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    done = [x for x in results if x["harness_returncode"] == 0]
    rows = []
    for case in sorted(base, key=int):
        ref = base[case]
        row = {"case": case, "weight": ref["weight"], "s50_kpi": ref["kpi"],
               "s50_trench_m": ref["trench_length_m"]}
        for item in done:
            cand = read_records(REPORT / item["name"] / "summary.json")[case]
            row[item["name"] + "_kpi"] = cand["kpi"]
            row[item["name"] + "_weighted_delta_vs_s50"] = cand["weight"] * (cand["kpi"] - ref["kpi"])
            row[item["name"] + "_trench_m"] = cand["trench_length_m"]
        rows.append(row)
    with (REPORT / "focused_per_case_vs_s50.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    ranking = []
    for item in done:
        summ = item["summary"]
        ranking.append({"candidate": item["name"], "weighted_score": summ["weighted_score_sum"],
                        "delta_vs_s50": summ["weighted_score_sum"] - s50_score,
                        "valid": summ["ok_count"], "case_count": summ["case_count"],
                        "max_solver_cpu_s": max((r.get("solver_cpu_total_s") or 0) for r in summ["records"]),
                        "max_solver_rss_mib": max((r.get("solver_peak_rss_mb") or 0) for r in summ["records"])})
    ranking.sort(key=lambda x: x["weighted_score"], reverse=True)
    (REPORT / "focused_scoreboard.json").write_text(json.dumps(ranking, indent=2), encoding="utf-8")
    with (REPORT / "focused_scoreboard.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ranking[0]))
        writer.writeheader()
        writer.writerows(ranking)


if __name__ == "__main__":
    main()
