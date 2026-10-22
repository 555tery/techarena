"""Inspect one authorized run, or request an immediate supervised stop."""
import argparse
import json
from pathlib import Path
import sqlite3
import time

from research import atomic_json
from support import ROOT


def evaluated_summary(run):
    path = Path(run) / "programs.sqlite"
    if not path.exists():
        return {"completed": 0, "correct": 0, "best": None}
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        rows = connection.execute("SELECT id,generation,correct,combined_score,island_idx,metadata FROM programs").fetchall()
    evaluated = {}
    for row in rows:
        meta = json.loads(row[5] or "{}")
        if meta.get("_is_island_copy") or meta.get("_spawned_island"):
            continue
        evaluated[row[1]] = row
    correct = [row for row in evaluated.values() if row[2]]
    best = max(correct, key=lambda row: row[3], default=None)
    return {"completed": len(evaluated), "correct": len(correct),
            "best": None if best is None else dict(id=best[0], generation=best[1], score=best[3], island=best[4])}


def status(run):
    import psutil
    run = Path(run).resolve()
    if run.parent != ROOT / "runs":
        raise ValueError("only this SEARCH-v3.1 runs namespace is accepted")
    manifest = json.loads((run / "run-manifest.json").read_text())
    result = {"run": str(run), "status": manifest["status"], "target": manifest["target_generations"],
              **evaluated_summary(run)}
    result["remaining"] = max(0, result["target"] - result["completed"])
    for filename, key in (("night-supervisor.json", "supervisor"), ("night-runtime-state.json", "runtime"),
                          ("quota-usage.json", "usage"), ("night-stop-request.json", "stop_request"),
                          ("mixed-seed-state.json", "mixed_seeds")):
        path = run / filename
        if path.exists():
            result[key] = json.loads(path.read_text())
    supervisor = result.get("supervisor", {})
    try:
        proc = psutil.Process(supervisor["worker_pid"])
        result["worker_alive"] = proc.create_time() == supervisor["worker_created_at"] and proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except (KeyError, psutil.NoSuchProcess):
        result["worker_alive"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--stop-reason")
    args = parser.parse_args()
    result = status(args.run)
    if args.stop_reason:
        atomic_json(args.run / "night-stop-request.json", {
            "reason": args.stop_reason, "immediate": True, "requested_at": time.time()})
        result["stop_requested"] = args.stop_reason
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
