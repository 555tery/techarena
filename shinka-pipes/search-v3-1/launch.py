"""Create and start only the explicitly authorized, frozen mixed SEARCH-v3.1 run."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from support import ROOT, PARENT, digest
from research import atomic_json


def start():
    from evaluator import verify_snapshot
    from research_runner import check_upstream
    verify_snapshot()
    check_upstream()
    policy = json.loads((ROOT / "night-policy.json").read_text())
    if policy.get("launch_authorized") is not True or policy["target_generations"] != 800:
        raise RuntimeError("this launcher requires the user-authorized 800-evaluation policy")
    import psutil
    active_path = ROOT / "active-run.json"
    if active_path.exists():
        old = json.loads(active_path.read_text())
        try:
            old_proc = psutil.Process(old["supervisor_pid"])
            if old_proc.create_time() == old["supervisor_created_at"] and old_proc.is_running():
                raise RuntimeError("the active run still has a supervisor; do not duplicate it")
        except (KeyError, psutil.NoSuchProcess):
            pass
        previous_run = Path(old["run_dir"]).resolve()
        if previous_run.parent != ROOT / "runs":
            raise RuntimeError("active-run pointer escaped the run namespace")
        previous_state = previous_run / "night-supervisor.json"
        if not previous_state.exists():
            raise RuntimeError("previous run has no confirmed supervisor cleanup; reconcile first")
        previous = json.loads(previous_state.read_text())
        if previous.get("cleanup_confirmed") is not True:
            raise RuntimeError("previous run cleanup is unconfirmed; reconcile before another launch")
        for pid, created in previous.get("processes", {}).items():
            try:
                owned = psutil.Process(int(pid))
                if owned.create_time() == created and owned.is_running() and owned.status() != psutil.STATUS_ZOMBIE:
                    raise RuntimeError("previous run still owns a live process; reconcile before another launch")
            except psutil.NoSuchProcess:
                pass
    sys.path.insert(0, str(PARENT))
    from local_runtime import subscription_environment, check_prerequisites
    env = subscription_environment()
    check_prerequisites(env)
    seeds = json.loads((ROOT / "seed-plan.json").read_text())
    seed = seeds["seeds"][0]
    source = ROOT / seed["source_path"]
    if digest(source) != seed["source_sha256"]:
        raise ValueError("selected baseline source changed")
    run = ROOT / "runs" / (datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "-mixed")
    (run / "task").mkdir(parents=True)
    for name in ("shinka.yaml", "evaluate.py", "AGENTS.md"):
        shutil.copy2(ROOT / "task" / name, run / "task" / name)
    shutil.copy2(source, run / "task/initial.cpp")
    protocol = json.loads((ROOT / "protocol.json").read_text())
    manifest = dict(suite="search-v3.1", status="running", run_dir=str(run),
        launch_authorized=True, authorization="User: запускай; сначала подключить смешанный старт; hourly checks and stop below 65% remaining",
        target_generations=800, includes_baseline=True, created_at=time.time(),
        model=policy["model"], reasoning_effort="xhigh", service_tier="default", billing="subscription",
        research_protocol="research-memory-v1", selection_protocol="family-specialists-v1",
        night_protocol="overnight-v1", night_policy_sha256=digest(ROOT / "night-policy.json"),
        seed_protocol="mixed-seeds-v1", seed_plan_sha256=digest(ROOT / "seed-plan.json"),
        source_path=str(source), source_sha256=digest(source),
        snapshot_sha256=digest(ROOT / "snapshot.json"), evaluator_sha256=digest(ROOT / "evaluator.py"),
        search_manifest_sha256=protocol["manifest_sha256"]["search"],
        stress_evaluated=False, validation_access=False, open15_access=False,
        initial_islands=8, max_islands=10, usage_guard=policy["usage_guard"])
    atomic_json(run / "run-manifest.json", manifest)
    from night_manager import prepared_run
    try:
        prepared_run(run)
        from usage_guard import gate
        gate(run, min_remaining_percent=65, max_age_seconds=0)
    except Exception as exc:
        manifest.update(status="preflight_failed", finished_at=time.time(), failure=str(exc))
        atomic_json(run / "run-manifest.json", manifest)
        raise
    with (run / "supervisor.log").open("a") as log:
        proc = subprocess.Popen([sys.executable, "-B", str(ROOT / "night_manager.py"),
                                 "--execute-authorized-run", str(run)], cwd=ROOT, env=env,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
    active = {**manifest, "supervisor_pid": proc.pid,
              "supervisor_created_at": psutil.Process(proc.pid).create_time()}
    # A process-local assertion ends automatically with the supervisor.
    caffeinate = shutil.which("caffeinate")
    if caffeinate:
        awake = subprocess.Popen([caffeinate, "-i", "-w", str(proc.pid)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        active["caffeinate_pid"] = awake.pid
    atomic_json(active_path, active)
    print(json.dumps(active, indent=2))
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-authorized", action="store_true", required=True)
    parser.parse_args()
    start()
