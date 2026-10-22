#!/usr/bin/env python3
"""Continue the existing SEARCH-v2 budget in a clean directory, preserving history."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import types

from resume_search_v2 import NATIVE, V2, MODEL, RUN_NAME, now, digest, save, check
from local_runtime import subscription_environment, check_prerequisites
from patch_repair import install_stop_on_failed_proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--recovery-dir", required=True)
    args = parser.parse_args()
    source = V2 / "runs" / RUN_NAME
    run, recovery = Path(args.run_dir).resolve(), Path(args.recovery_dir).resolve()
    if run.parent != V2 / "runs" or run.exists() or recovery.exists():
        raise ValueError("continuation requires fresh directories inside SEARCH-v2 runs")
    original = json.loads((source / "run-manifest.json").read_text())
    if original["status"] != "needs_patch_repair" or original["stopped_generation"] != 5:
        raise ValueError("expected the stopped baseline-provenance connection failure")
    if subprocess.run(["ps", "-p", str(original["pid"]), "-o", "stat="], capture_output=True).returncode == 0:
        raise ValueError("source run manager is still alive")
    with sqlite3.connect(f"file:{source}/programs.sqlite?mode=ro", uri=True) as db:
        ids = [r[0] for r in db.execute("SELECT DISTINCT generation FROM programs ORDER BY generation")]
        count = db.execute("SELECT count(*) FROM programs").fetchone()[0]
    if ids != list(range(5)) or count != 6 or original["target_generations"] != 30:
        raise ValueError("expected exactly preserved generations0..4 and original budget30")
    env = subscription_environment()
    env.update(SHINKA_HEADLESS_COMMAND=str(V2 / "headless.sh"), PIPES_SEARCH_V2_ROOT=str(V2),
               PIPES_NATIVE_EVALUATOR_ROOT=str(NATIVE))
    auth = check_prerequisites(env)
    os.environ.clear()
    os.environ.update(env)
    prepared = check()
    lock = (NATIVE / (RUN_NAME + ".resume.lock")).open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    run.mkdir()
    recovery.mkdir(parents=True)
    with sqlite3.connect(f"file:{source}/programs.sqlite?mode=ro", uri=True) as db:
        with sqlite3.connect(run / "programs.sqlite") as target:
            db.backup(target)
    for generation in range(5):
        (run / f"gen_{generation}").symlink_to(source / f"gen_{generation}", target_is_directory=True)
    sources = [*NATIVE.glob("*.py"), NATIVE / "native_runner.cpp"]
    hashes = {p.name: digest(p) for p in sources}
    (recovery / "source-snapshot").mkdir()
    for p in sources:
        shutil.copyfile(p, recovery / "source-snapshot" / p.name)
    shutil.copyfile(source / "run-manifest.json", recovery / "source-run-manifest.json")
    shutil.copyfile(V2 / "active-run.json", recovery / "active-run-before.json")
    plan = {"run_dir": str(run), "native_root": str(NATIVE), "suite": "search-v2", "workers": 2,
            "target_generations": 30, "first_generation": 5, "recovered_generation": -1,
            "native_sha256": hashes, "created_at": now(), "continuation_of": str(source),
            "preserved_generations": list(range(5)), "remaining_generation_slots": 25,
            "failed_generation5_artifacts_preserved": str(source / "gen_5")}
    save(recovery / "plan.json", plan)
    os.environ["PIPES_NATIVE_SHINKA_PLAN"] = str(recovery / "plan.json")
    # This legacy field is the provenance of the already-evaluated baseline.
    # Keep it fixed; the active native wrapper has its own separate identity.
    manifest = {**original, "status": "running", "pid": os.getpid(), "resumed_at": now(),
                "execution_state": "running_native_evaluator", "continuation_of": str(source),
                "native_resume_dir": str(recovery), "native_workers": 2,
                "evaluator_engine": "native-direct-v1", "remaining_at_resume": 25,
                "resumed_from_generation": 5, "evaluator_sha256": digest(V2 / "evaluator.py"),
                "baseline_evaluator_sha256": digest(V2 / "evaluator.py"),
                "active_evaluator_sha256": digest(NATIVE / "shinka_evaluate.py"), "automatic_resume": False}
    for field in ("finished_at", "exception_type", "stopped_generation", "returncode", "unfinished_generation"):
        manifest.pop(field, None)
    save(run / "run-manifest.json", manifest)
    sys.path.insert(0, str(NATIVE.parent / "evaluator-fast"))
    from reference import load_frozen
    bridge = load_frozen("headless_bridge.py")
    bridge.check_baseline(str(run))
    report = {"baseline_gate_passed": True, "model_calls_during_preflight": 0,
              "source_run": str(source), "run_dir": str(run), "preserved_generations": list(range(5)),
              "program_rows_copied": count, "target_generations": 30, "next_generation": 5,
              "remaining_generation_slots": 25, "model": MODEL, "service_tier": "fast",
              "native_workers": 2, "patch_repair": prepared["patch_repair"], "auth": auth,
              "validation_accessed": False, "open15_accessed": False}
    save(recovery / "preflight.json", report)
    print(json.dumps(report, indent=2), flush=True)
    active = json.loads((V2 / "active-run.json").read_text())
    from urllib.parse import quote
    active.update(run_dir=str(run), pid=os.getpid(), status="resumed_running", resumed_at=now(),
                  status_source=str(run / "run-manifest.json"), native_workers=2,
                  evaluator_engine="native-direct-v1", native_resume_dir=str(recovery), observed_at=now(),
                  continuation_of=str(source), remaining_at_resume=25,
                  webui_url="http://127.0.0.1:8889/viz_tree.html?db_path=" + quote(str(run / "programs.sqlite"), safe=""))
    save(V2 / "active-run.json", active)
    from shinka.cli import run as cli
    original_build = cli._build_runner
    runners = []

    def build(**kwargs):
        kwargs["evaluate_str"] = (NATIVE / "shinka_evaluate.py").read_text()
        runner = original_build(**kwargs)
        install_stop_on_failed_proposal(runner)
        original_setup = runner._setup_async

        async def setup(self):
            await original_setup()
            if self.completed_generations != 5 or self.next_generation_to_submit != 5:
                raise ValueError("continuation counters do not preserve the original budget")
            save(recovery / "startup.json", {"completed_generations": 5, "next_generation": 5,
                                             "target_generations": self.evo_config.num_generations, "at": now()})

        runner._setup_async = types.MethodType(setup, runner)
        runners.append(runner)
        return runner

    cli._build_runner = build
    try:
        result = cli.main(["--task-dir", str(V2 / "task"), "--config-fname", "shinka.yaml",
                           "--results_dir", str(run), "--num_generations", "30"])
        stopped = next((r._search_v2_repair_stop for r in runners if getattr(r, "_search_v2_repair_stop", None)), None)
        if stopped:
            save(run / "patch-repair-exhausted.json", stopped)
            manifest.update(status="needs_patch_repair", stopped_generation=stopped["generation"], returncode=2)
            return 2
        with sqlite3.connect(f"file:{run}/programs.sqlite?mode=ro", uri=True) as db:
            generations = [r[0] for r in db.execute("SELECT DISTINCT generation FROM programs ORDER BY generation")]
        manifest.update(status="completed" if generations == list(range(30)) else "runner_returned_incomplete", returncode=result)
        return result
    except BaseException as exc:
        manifest.update(status="failed", exception_type=type(exc).__name__)
        raise
    finally:
        cli._build_runner = original_build
        manifest.update(finished_at=now(), execution_state="stopped")
        save(run / "run-manifest.json", manifest)
        active.update(status=manifest["status"], observed_at=now())
        save(V2 / "active-run.json", active)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
