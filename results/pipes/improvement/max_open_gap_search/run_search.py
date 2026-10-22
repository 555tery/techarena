#!/usr/bin/env python3
"""Compile and compare gap-selection policies on all official open inputs."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
SOURCE = BASE / "src" / "gap_search.cpp"
BIN = BASE / "binaries"
REPORT = BASE / "reports"
HARNESS = ROOT / "tools" / "pipes_harness.py"
INTERACTOR = ROOT / "tools" / "interactor"
TESTS = ROOT / "data" / "pipes" / "open"

# Independently selected query policies followed by targeted recent-window sweeps.
CANDIDATES = [
    {"name": "best_fit", "policy": 0, "window": 128, "scale": 50},
    {"name": "first_fit_low", "policy": 1, "window": 128, "scale": 50},
    {"name": "worst_fit", "policy": 2, "window": 128, "scale": 50},
    {"name": "first_fit_high", "policy": 3, "window": 128, "scale": 50},
    {"name": "age_oldest_near", "policy": 4, "window": 128, "scale": 50},
    {"name": "age_newest_near", "policy": 5, "window": 128, "scale": 50},
    {"name": "recent_w16_s8", "policy": 7, "window": 16, "scale": 8},
    {"name": "recent_w32_s16", "policy": 7, "window": 32, "scale": 16},
    {"name": "recent_w64_s25", "policy": 7, "window": 64, "scale": 25},
    {"name": "recent_w64_s32", "policy": 7, "window": 64, "scale": 32},
    {"name": "recent_w64_s50", "policy": 7, "window": 64, "scale": 50},
    {"name": "recent_w64_s64", "policy": 7, "window": 64, "scale": 64},
    {"name": "recent_w64_s80", "policy": 7, "window": 64, "scale": 80},
    {"name": "recent_w96_s50", "policy": 7, "window": 96, "scale": 50},
    {"name": "recent_w128_s25", "policy": 7, "window": 128, "scale": 25},
    {"name": "recent_w128_s32", "policy": 7, "window": 128, "scale": 32},
    {"name": "recent_w128_s65", "policy": 7, "window": 128, "scale": 65},
    {"name": "recent_w128_s80", "policy": 7, "window": 128, "scale": 80},
    {"name": "recent_w256_s64", "policy": 7, "window": 256, "scale": 64},
    {"name": "recent_w256_s100", "policy": 7, "window": 256, "scale": 100},
    {"name": "recent_w512_s50", "policy": 7, "window": 512, "scale": 50},
    {"name": "recent_w512_s128", "policy": 7, "window": 512, "scale": 128},
]

BASELINES = {
    "policy4": ROOT / "results/pipes/improvement/strategies/binaries/policy4_baseline",
    "s50": ROOT / "results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20",
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compile_one(candidate):
    binary = BIN / candidate["name"]
    command = [
        "g++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-DPIPES_POLICY=%d" % candidate["policy"],
        "-DPIPES_WINDOW=%d" % candidate["window"],
        "-DPIPES_SCALE=%d" % candidate["scale"], str(SOURCE), "-o", str(binary),
    ]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    candidate["compile_command"] = " ".join(command)
    candidate["source_sha256"] = sha(SOURCE)
    candidate["binary"] = str(binary)
    candidate["binary_sha256"] = sha(binary)
    return binary


def harness(binary, name):
    out = REPORT / name
    if out.exists():
        # Re-running a named candidate intentionally replaces its old report.
        import shutil
        shutil.rmtree(out)
    command = [sys.executable, str(HARNESS), "--solver", str(binary), "--name", name,
               "--interactor", str(INTERACTOR), "--tests", str(TESTS), "--out", str(out)]
    start = time.monotonic()
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    result = {"returncode": proc.returncode, "stdout": proc.stdout[-2000:],
              "stderr": proc.stderr[-4000:], "elapsed_s": time.monotonic() - start,
              "output_dir": str(out)}
    if proc.returncode == 0:
        summary = json.loads((out / "summary.json").read_text())
        result["summary"] = summary
        result["score"] = summary["weighted_score_sum"]
        result["ok"] = summary["ok_count"]
    return result


def records(out):
    data = json.loads((Path(out) / "summary.json").read_text())
    return {str(row["case"]): row for row in data["records"]}


def save_scoreboard(done):
    base_rows = records(REPORT / "s50_baseline")
    names = list(done)
    rows = []
    for case in sorted(base_rows, key=lambda x: int(x)):
        ref = base_rows[case]
        row = {"case": case, "weight": ref["weight"], "s50_kpi": ref["kpi"],
               "s50_trench_m": ref["trench_length_m"]}
        for name in names:
            rec = records(REPORT / name)[case]
            row[name + "_kpi"] = rec["kpi"]
            row[name + "_weighted_delta_vs_s50"] = rec["weight"] * (rec["kpi"] - ref["kpi"])
        rows.append(row)
    path = REPORT / "per_case_scoreboard_vs_s50.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summaries = []
    for name in names:
        summary = json.loads((REPORT / name / "summary.json").read_text())
        s50score = json.loads((REPORT / "s50_baseline" / "summary.json").read_text())["weighted_score_sum"]
        summaries.append({"candidate": name, "weighted_score": summary["weighted_score_sum"],
                          "delta_vs_s50": summary["weighted_score_sum"] - s50score,
                          "valid": summary["ok_count"], "case_count": summary["case_count"],
                          "max_cpu_s": summary["rss_measurement"] if False else max(
                              (x.get("solver_cpu_total_s") or 0) for x in summary["records"]),
                          "max_rss_mb": max((x.get("solver_peak_rss_mb") or 0) for x in summary["records"])})
    summaries.sort(key=lambda x: x["weighted_score"], reverse=True)
    with (REPORT / "scoreboard.json").open("w", encoding="utf-8") as stream:
        json.dump(summaries, stream, indent=2)
    with (REPORT / "scoreboard.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)


def main():
    BIN.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    for key, binary in BASELINES.items():
        if not binary.exists():
            raise FileNotFoundError(binary)
        item = harness(binary, key + "_baseline")
        if item["returncode"] != 0:
            raise RuntimeError("baseline harness failed: " + json.dumps(item))
    done = []
    manifest = {"source": str(SOURCE), "source_sha256": sha(SOURCE),
                "interactor": str(INTERACTOR), "interactor_sha256": sha(INTERACTOR),
                "tests_dir": str(TESTS), "candidates": []}
    for candidate in CANDIDATES:
        binary = compile_one(candidate)
        result = harness(binary, candidate["name"])
        candidate["run"] = {k: v for k, v in result.items() if k != "summary"}
        if result.get("returncode") == 0:
            candidate["score"] = result["score"]
            candidate["valid"] = result["ok"]
            done.append(candidate["name"])
            save_scoreboard(done)
            print("%s: %.12f (%+0.12f vs s50) valid=%d/15" % (
                candidate["name"], candidate["score"],
                candidate["score"] - json.loads((REPORT / "s50_baseline" / "summary.json").read_text())["weighted_score_sum"],
                candidate["valid"]), flush=True)
        else:
            print("%s failed: rc=%s %s" % (candidate["name"], result["returncode"], result["stderr"]), flush=True)
        manifest["candidates"].append(candidate)
        (REPORT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
