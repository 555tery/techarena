"""Resume the repaired SEARCH-v1 run with its original total generation budget."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import types
from zoneinfo import ZoneInfo

from local_runtime import ROOT, TASK, subscription_environment
from manage import check_setup


def install_terminal_failure_accounting(runner) -> None:
    """Keep failed proposals inside the total budget using Shinka's native writer.

    The pinned runner records terminal proposal failures in attempt_log only.
    Its resume/completion counter counts Program rows. Persist the same failure
    once so skipped proposal IDs neither get replayed nor leave budget holes.
    """
    original = runner._record_terminal_failed_proposal

    async def record_and_persist(self, **kwargs):
        generation = kwargs["generation"]
        persisted = await self.async_db.get_persisted_generation_ids_async()
        if generation in persisted:
            return
        await original(**kwargs)  # Includes the original cost accounting once.
        failure = Path(self.results_dir) / f"gen_{generation}/failure.json"
        recorded = failure.with_name("failure-before-program-persistence.json")
        if failure.is_file() and not recorded.exists():
            shutil.copy2(failure, recorded)
        program = await self._persist_failed_generation(**kwargs)
        if program is None:
            raise RuntimeError(f"Failed to persist terminal generation {generation}; refusing a budget hole")

    runner._record_terminal_failed_proposal = types.MethodType(record_and_persist, runner)


def inspect_run() -> tuple[dict, Path, dict]:
    state = json.loads((ROOT / "pending-recovery.json").read_text())
    run = Path(state["run_dir"]).resolve()
    if not run.is_relative_to(ROOT / "runs"):
        raise ValueError("only the existing SEARCH-v1 run may be resumed")
    manifest = json.loads((run / "run-manifest.json").read_text())
    if manifest.get("target_generations") != 20:
        raise ValueError("original total budget must remain exactly 20")
    con = sqlite3.connect("file:" + str(run / "programs.sqlite") + "?mode=ro", uri=True)
    generations = [row[0] for row in con.execute("SELECT DISTINCT generation FROM programs ORDER BY generation")]
    rows = con.execute("SELECT count(*) FROM programs").fetchone()[0]
    con.close()
    if generations != list(range(12)) or rows != 13:
        raise ValueError("expected preserved generations 0..11 and one extra baseline island copy")
    repair = json.loads((Path(state["recovery_dir"]) / "publication.json").read_text())
    if repair.get("status") != "committed" or repair.get("total_generation_budget") != 20:
        raise ValueError("saved reevaluations and terminal budget slots are not committed")
    return state, run, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Continue the already-authorized original budget")
    args = parser.parse_args()
    state, run, manifest = inspect_run()
    env = subscription_environment()
    # The provider's command builder reads os.environ during preflight.
    os.environ.clear()
    os.environ.update(env)
    report = check_setup(env, search_only=True)
    # The fix changes source-format validation only. Re-audit saved gen0 reports
    # on the same fixed corpus instead of spending a new baseline evaluation.
    from synthetic_eval import SEARCH, aggregate_report
    baseline = json.loads((run / "gen_0/results/metrics.json").read_text())
    correct = json.loads((run / "gen_0/results/correct.json").read_text())
    suite = json.loads((SEARCH / "manifest.json").read_text())
    summary = json.loads((run / "gen_0/results/harness/summary.json").read_text())
    recomputed, baseline_ok = aggregate_report(summary, suite, SEARCH, 0)
    if (not baseline_ok or correct.get("correct") is not True
            or recomputed["combined_score"] != baseline["combined_score"]
            or baseline["program_sha256"] != hashlib.sha256((TASK / "initial.cpp").read_bytes()).hexdigest()):
        raise ValueError("preserved baseline does not match the current source/data/fitness")
    report.update(search_baseline_status="preserved_and_reaudited_same_source_data_fitness",
                  recorded_baseline={"fitness": baseline["combined_score"], "valid_cases": 32})
    report.update(mode="resume_existing_run", run_dir=str(run), total_generation_budget=20,
                  consumed_generation_slots=12, remaining_generation_slots=8, next_generation=12)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not args.run:
        return 0
    from shinka.cli import run as cli
    original_build = cli._build_runner

    def build_with_failure_accounting(**kwargs):
        runner = original_build(**kwargs)
        install_terminal_failure_accounting(runner)
        return runner

    cli._build_runner = build_with_failure_accounting
    now = datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat()
    previous_evaluator = manifest["evaluator_sha256"]
    manifest.update(status="running", pid=os.getpid(), resumed_at=now,
                    evaluator_sha256=hashlib.sha256((ROOT / "synthetic_eval.py").read_bytes()).hexdigest(),
                    previous_evaluator_sha256=previous_evaluator,
                    resume_policy="same database; fixed SEARCH-v1; total slots 0..19 including failed/interrupted proposals",
                    consumed_at_resume=12, remaining_at_resume=8)
    manifest.pop("finished_at", None)
    manifest.pop("exception_type", None)
    path = run / "run-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    active_path = ROOT / "active-run.json"
    active = json.loads(active_path.read_text())
    active.update(pid=os.getpid(), status="resumed_running", resumed_at=now,
                  target_generations=20, consumed_at_resume=12, remaining_at_resume=8,
                  last_observed_generation=12)
    active_path.write_text(json.dumps(active, indent=2) + "\n")
    try:
        result = cli.main(["--task-dir", str(TASK), "--config-fname", "shinka.yaml",
                           "--results_dir", str(run), "--num_generations", "20"])
        manifest.update(status="runner_returned", returncode=result)
        return result
    except BaseException as exc:
        manifest.update(status="failed", exception_type=type(exc).__name__)
        raise
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat()
        path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
