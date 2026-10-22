"""Run a single-CPU, 180-second offline survivor-order reverse search."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from condition_rotations import INPUT11, OUT, read_input, read_positions, replay, sha
from runtime import ROOT, REPO, e

SOURCE_CPP = ROOT / "case13" / "search.cpp"
SOURCE_PLAN = REPO / "prototypes/pipes_open15_overfit_20261019/future/2/11.txt"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = SOURCE_CPP.read_text()
    if raw.count("best.h>3220") != 2 or raw.count("best.h<=3220") != 2:
        raise ValueError("case13 search target expressions changed; refusing unsafe substitution")
    raw = raw.replace("best.h>3220", "best.h>20760").replace("best.h<=3220", "best.h<=20760")
    cpp = OUT / "raw_search.cpp"
    cpp.write_text(raw)
    binary = OUT / "raw_search"
    compile_log = "raw-search-compile.log"
    rc = e.invoke(["/usr/bin/clang++", "-std=c++17", "-O3", str(cpp), "-o", str(binary)], OUT, compile_log, 120)
    if rc != 0:
        raise RuntimeError(f"raw search compile failed: {rc}")

    candidate = OUT / "raw-search-best.txt"
    shutil.copyfile(SOURCE_PLAN, candidate)
    baseline = replay(INPUT11, read_positions(SOURCE_PLAN, len(read_input(INPUT11)[3])-1))
    started = time.time()
    timed_out = False
    returncode = None
    try:
        returncode = e.invoke([str(binary), str(INPUT11), str(candidate)], OUT, "raw-search.log", 180)
    except TimeoutError:
        timed_out = True

    _, n, commands, lengths, birth, death, _, _ = read_input(INPUT11)
    positions = read_positions(candidate, len(lengths)-1)
    best = replay(INPUT11, positions)
    cut = positions[1]
    if lengths[1] != 3 or birth[1] != 0 or death[1] != n:
        raise ValueError("PID1 ceased to be the immortal length-3 pipe")
    crossed = [pid for pid in range(2, len(lengths))
               if positions[pid] < cut < positions[pid]+lengths[pid]]
    if crossed:
        raise ValueError(f"raw plan has {len(crossed)} pipes crossing PID1 cut")
    rotated = [0]
    for pid in range(1, len(lengths)):
        x = positions[pid]
        rotated.append(x-cut if x >= cut else x+best["extent"]-cut)
    rotated_path = OUT / "raw-search-rotated.txt"
    rotated_path.write_text("".join(f"{rotated[pid]}\n" for pid in range(1, len(rotated))))
    rotated_report = replay(INPUT11, rotated)
    if rotated[1] != 0 or rotated_report["extent"] > best["extent"]:
        raise ValueError("PID1 cut rotation failed to preserve the extent bound")
    log_path = OUT / "raw-search.log"
    log = log_path.read_text() if log_path.exists() else ""
    report = {
        "task": "case11 reverse random-order offline search, then rotate at immortal PID1",
        "offline_future_deletions_used": True,
        "source_cpp_sha256": sha(SOURCE_CPP),
        "adapted_cpp_sha256": sha(cpp),
        "source_plan_sha256": sha(SOURCE_PLAN),
        "source_plan_replay": baseline,
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "timeout_seconds": 180,
        "timed_out": timed_out,
        "returncode": returncode,
        "best_raw_plan": best,
        "best_raw_plan_sha256": sha(candidate),
        "pid1": {"length": lengths[1], "birth_command": birth[1],
                 "death_command": death[1], "final_time": n,
                 "immortal": death[1] == n, "cut": cut,
                 "other_pipes_crossing_cut": len(crossed)},
        "rotated_plan": rotated_report,
        "rotated_plan_sha256": sha(rotated_path),
        "target_20760_reached": rotated_report["trench_score"] <= 20760,
        "search_log_tail": log[-6000:],
    }
    e.save(OUT / "raw-search-report.json", report)
    print(json.dumps({"T_raw": best["trench_score"],
                      "T_rotated": rotated_report["trench_score"],
                      "extent_raw": best["extent"], "pid1_before": cut,
                      "target_20760_reached": report["target_20760_reached"],
                      "timed_out": timed_out, "returncode": returncode,
                      "report": str(OUT / "raw-search-report.json")}, indent=2))


if __name__ == "__main__":
    main()
