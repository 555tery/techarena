#!/usr/bin/env python3
"""Resume the paused SEARCH-v2 run at its original 30-generation budget."""

import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import types
from zoneinfo import ZoneInfo

NATIVE = Path(__file__).resolve().parent
V2 = NATIVE.parent / "search-v2"
sys.path[:0] = [str(V2), str(V2.parent)]
from manage import check
from local_runtime import check_prerequisites, subscription_environment
from patch_repair import install_stop_on_failed_proposal

MODEL = "headless/codex@gpt-6-astra?effort=xhigh"
RUN_NAME = "20261018T011836+0700-084000"
PARENT_ID = "6c05edea-7a74-4bf0-b078-00ccfc663419"
ARCHIVE_ID = "cc5a13ee-f7e4-4135-9c4f-045fe52a9be0"
TOP_ID = "b08e03fa-07a1-474e-b6ed-78533c717981"


def now():
    return datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def inspect_run():
    active = json.loads((V2 / "active-run.json").read_text())
    run = V2 / "runs" / RUN_NAME
    if Path(active["run_dir"]) != run:
        raise ValueError("active SEARCH-v2 run changed")
    manifest = json.loads((run / "run-manifest.json").read_text())
    if (manifest["status"] != "paused_by_user" or manifest["target_generations"] != 30
            or manifest["model"] != MODEL or manifest["service_tier"] != "fast"
            or manifest["suite"] != "search-v2"):
        raise ValueError("expected the paused Astra xhigh Fast run with original budget 30")
    if subprocess.run(["ps", "-p", str(active["pid"]), "-o", "stat="], capture_output=True).returncode == 0:
        raise ValueError("previous manager PID is still alive; inspect before resuming")
    with sqlite3.connect(f"file:{run}/programs.sqlite?mode=ro", uri=True) as con:
        generations = [r[0] for r in con.execute("SELECT DISTINCT generation FROM programs ORDER BY generation")]
        rows = con.execute("SELECT count(*) FROM programs").fetchone()[0]
        parents = dict(con.execute("SELECT id,code FROM programs WHERE id IN (?,?,?)", (PARENT_ID, ARCHIVE_ID, TOP_ID)))
    if generations != [0, 1, 2, 3] or rows != 5 or len(parents) != 3:
        raise ValueError("expected preserved generations 0..3 plus one baseline island copy")
    gen = run / "gen_4"
    if parents[PARENT_ID] != (gen / "original.cpp").read_text():
        raise ValueError("saved generation4 parent code no longer matches its selected parent")
    attempt = json.loads((gen / "attempts/novelty_1/resample_1/patch_1/metadata.json").read_text())
    if (attempt["generation"] != 4 or not attempt["success"] or attempt["llm_model"] != MODEL
            or attempt["patch_attempt"] != 1 or (gen / "native-results").exists()):
        raise ValueError("unexpected saved generation4 patch or existing native results")
    return active, run, manifest, attempt


def install_recovered_job(runner, run, attempt, recovery_dir):
    """Submit the saved proposal through Shinka's normal evaluation/persistence."""
    original_setup = runner._setup_async

    async def setup(self):
        await original_setup()
        if self.completed_generations != 4 or self.next_generation_to_submit != 4:
            raise ValueError("resume counters changed before recovery")
        from shinka.core.async_runner import AsyncRunningJob
        source = run / "gen_4/main.cpp"
        results = run / "gen_4/native-results"
        submitted = await self._submit_evaluation_job_with_slot(
            exec_fname=str(source), results_dir=str(results), sampling_worker_id=None)
        job_id, worker_id, submitted_at, started_at, running = submitted
        metadata = {"api_costs": attempt["llm_cost"], "patch_type": "full",
                    "patch_name": attempt["patch_name"], "patch_description": attempt["patch_description"],
                    "num_applied": attempt["num_applied"], "error_attempt": None,
                    "novelty_attempt": 1, "resample_attempt": 1, "patch_attempt": 1,
                    "model_name": MODEL, "headless_prompt_path": attempt["headless_prompt_path"],
                    "recovered_saved_proposal": True, "recovery_dir": str(recovery_dir),
                    "original_proposal_created_at": attempt["timestamp"],
                    "original_evaluation_interrupted_by_user": True}
        # The resumed timeline begins now; the original sampling timestamp is
        # retained separately so the paused interval is not charged as work.
        job = AsyncRunningJob(
            job_id=job_id, exec_fname=str(source), results_dir=str(results),
            start_time=submitted_at, proposal_started_at=submitted_at,
            evaluation_submitted_at=submitted_at, evaluation_started_at=started_at,
            generation=4, evaluation_worker_id=worker_id,
            running_eval_jobs_at_submit=running, parent_id=PARENT_ID,
            archive_insp_ids=[ARCHIVE_ID], top_k_insp_ids=[TOP_ID],
            code_diff=(run / "gen_4/edit.diff").read_text(), meta_patch_data=metadata,
            code_embedding=[], proposal_task_id="recovered-generation-4")
        self.total_api_cost += attempt["llm_cost"]
        self.total_proposals_generated += 1
        self.assigned_generations.add(4)
        self.next_generation_to_submit = 5
        self.running_jobs.append(job)
        self.submitted_jobs[str(job_id)] = job
        self.slot_available.set()
        save(recovery_dir / "recovered-job.json", {"generation": 4, "job_id": str(job_id),
             "source_sha256": digest(source), "parent_id": PARENT_ID, "results_dir": str(results),
             "submitted_at": now(), "new_model_calls_for_generation4": 0,
             "next_generation": 5, "completed_generations": self.completed_generations})
        logging.getLogger(__name__).info("Resubmitted saved gen4 to native evaluator, workers=2; next proposal=5, total target=30")

    runner._setup_async = types.MethodType(setup, runner)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--recovery-dir", required=True)
    args = parser.parse_args()
    active, run, manifest, attempt = inspect_run()
    env = subscription_environment()
    env.update(SHINKA_HEADLESS_COMMAND=str(V2 / "headless.sh"), PIPES_SEARCH_V2_ROOT=str(V2),
               PIPES_NATIVE_EVALUATOR_ROOT=str(NATIVE))
    auth = check_prerequisites(env)
    os.environ.clear()
    os.environ.update(env)
    prepared = check()
    sys.path.insert(0, str(NATIVE))
    from cache import native_binary
    binary, key = native_binary()
    report = {"status": "resume_preflight_passed", "run_dir": str(run), "total_generation_budget": 30,
              "completed_generations": [0, 1, 2, 3], "recover_saved_generation": 4,
              "remaining_generation_slots": 26, "model": MODEL, "service_tier": "fast",
              "patch_repair": prepared["patch_repair"], "auth": auth, "native_workers": 2,
              "native_binary": str(binary), "native_binary_cache_key": key,
              "validation_accessed": False, "open15_accessed": False}
    print(json.dumps(report, indent=2), flush=True)
    if not args.run:
        return 0
    recovery = Path(args.recovery_dir).resolve()
    recovery.mkdir(parents=True, exist_ok=True)
    lock = (NATIVE / (RUN_NAME + ".resume.lock")).open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (recovery / "plan.json").exists():
        raise ValueError("recovery directory has already been used")
    with sqlite3.connect(f"file:{run}/programs.sqlite?mode=ro", uri=True) as source:
        with sqlite3.connect(recovery / "programs-before.sqlite") as target:
            source.backup(target)
    for source, name in ((run / "run-manifest.json", "run-manifest-before.json"),
                         (V2 / "active-run.json", "active-run-before.json"),
                         (run / "evaluate.py", "evaluate-before.py")):
        shutil.copy2(source, recovery / name)
    sources = [*NATIVE.glob("*.py"), NATIVE / "native_runner.cpp"]
    plan = {"run_dir": str(run), "native_root": str(NATIVE), "suite": "search-v2",
            "workers": 2, "target_generations": 30, "first_generation": 4, "recovered_generation": 4,
            "native_sha256": {p.name: digest(p) for p in sources}, "created_at": now(),
            "old_partial_results_preserved": str(run / "gen_4/results"),
            "gen4_source_sha256": digest(run / "gen_4/main.cpp")}
    save(recovery / "plan.json", plan)
    save(recovery / "preflight.json", report)
    os.environ["PIPES_NATIVE_SHINKA_PLAN"] = str(recovery / "plan.json")
    from shinka.cli import run as cli
    original_build = cli._build_runner
    runners = []

    def build(**kwargs):
        kwargs["evaluate_str"] = (NATIVE / "shinka_evaluate.py").read_text()
        runner = original_build(**kwargs)
        install_stop_on_failed_proposal(runner)
        install_recovered_job(runner, run, attempt, recovery)
        runners.append(runner)
        return runner

    cli._build_runner = build
    manifest.update(status="running", execution_state="running_native_evaluator", pid=os.getpid(),
                    resumed_at=now(), evaluator_engine="native-direct-v1", native_workers=2,
                    native_resume_dir=str(recovery), remaining_at_resume=26,
                    resumed_from_generation=4, automatic_resume=False,
                    active_evaluator_sha256=digest(NATIVE / "shinka_evaluate.py"),
                    baseline_evaluator_sha256=manifest["evaluator_sha256"])
    manifest.pop("exception_type", None)
    manifest.pop("finished_at", None)
    save(run / "run-manifest.json", manifest)
    active.update(pid=os.getpid(), status="resumed_running", resumed_at=manifest["resumed_at"],
                  status_source=str(run / "run-manifest.json"), native_workers=2,
                  evaluator_engine="native-direct-v1", native_resume_dir=str(recovery))
    save(V2 / "active-run.json", active)
    try:
        result = cli.main(["--task-dir", str(V2 / "task"), "--config-fname", "shinka.yaml",
                           "--results_dir", str(run), "--num_generations", "30"])
        stopped = next((r._search_v2_repair_stop for r in runners if getattr(r, "_search_v2_repair_stop", None)), None)
        if stopped:
            save(run / "patch-repair-exhausted.json", stopped)
            manifest.update(status="needs_patch_repair", stopped_generation=stopped["generation"], returncode=2)
            return 2
        with sqlite3.connect(f"file:{run}/programs.sqlite?mode=ro", uri=True) as con:
            ids = [row[0] for row in con.execute("SELECT DISTINCT generation FROM programs ORDER BY generation")]
        manifest.update(status="completed" if ids == list(range(30)) else "runner_returned_incomplete", returncode=result)
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
