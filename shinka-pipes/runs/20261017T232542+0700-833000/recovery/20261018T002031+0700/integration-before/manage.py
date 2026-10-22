"""Check setup without model/evaluator calls, or explicitly launch a bounded run."""

from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

from local_runtime import HEADLESS, ROOT, TASK, check_prerequisites, subscription_environment


def load_config():
    from shinka.cli.run_config import load_optional_yaml_config
    from shinka.core import EvolutionConfig
    from shinka.database import DatabaseConfig
    from shinka.launch import LocalJobConfig

    classes = {"evo": EvolutionConfig, "db": DatabaseConfig, "job": LocalJobConfig}
    config, runner = load_optional_yaml_config(
        task_dir=TASK, config_fname="shinka.yaml",
        allowed_field_types={ns: {f.name: f.type for f in fields(cls)} for ns, cls in classes.items()},
    )
    for ns, cls in classes.items():
        cls(**config[ns])  # Validate dataclass arguments without creating a runner.
    evo = config["evo"]
    if evo.get("llm_models") != ["headless/codex@gpt-6.1-sol?effort=xhigh"]:
        raise RuntimeError("Expected pinned Codex model gpt-6.1-sol with xhigh reasoning.")
    if (evo.get("embedding_model") is not None or evo.get("meta_rec_interval") is not None
            or evo.get("novelty_llm_models") is not None or evo.get("evolve_prompts")
            or evo.get("enable_wandb_logging") or evo.get("job_type") != "local"):
        raise RuntimeError("Unexpected extra model, telemetry, or nonlocal backend configuration.")
    if any(runner.get(k) != 1 for k in ("max_evaluation_jobs", "max_proposal_jobs", "max_db_workers")):
        raise RuntimeError("This setup expects one worker per stage.")
    return config, runner


def check_setup(env: dict[str, str], *, search_only: bool = False) -> dict:
    runtime = check_prerequisites(env)
    config, runner = load_config()
    if search_only:
        from synthetic_eval import SEARCH, load_suite
        search = load_suite(SEARCH, "search")
        corpus = {"search_cases": search["case_count"], "search_families": len(search["families"]),
                  "validation_checks": "skipped", "open15_checks": "skipped"}
    else:
        from synthetic_eval import check_prepared_suites
        corpus = check_prepared_suites()
    snapshot = json.loads((TASK / "snapshot.json").read_text())
    for name, expected in snapshot["snapshot_sha256"].items():
        actual = hashlib.sha256((TASK / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Snapshot changed: {name}")
    for name, expected in snapshot["support_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Integration support changed: {name}")
    direct = json.loads(importlib.metadata.distribution("shinka-evolve").read_text("direct_url.json"))
    if direct["vcs_info"]["commit_id"] != "8adc053a2ce4511ad2ac310e004c530a73fb974a":
        raise RuntimeError("Installed Shinka commit differs from the pinned version.")
    lock = json.loads((ROOT / "runtime/package-lock.json").read_text())
    resolved = lock["packages"]["node_modules/@roberttlange/headless"]["resolved"]
    if not resolved.endswith("#93cd9b06b85f848af1308c41e018991b33907c5e"):
        raise RuntimeError("Headless package differs from the pinned version.")
    if "HEADLESS_BILLING" not in (HEADLESS.parent / "billing.js").read_text():
        raise RuntimeError("Installed Headless lacks subscription billing support.")
    from shinka.llm.providers.headless import _build_headless_command, parse_headless_model
    model = parse_headless_model(config["evo"]["llm_models"][0])
    command = _build_headless_command(model=model,
                                     prompt_path=ROOT / ".configuration-probe", work_dir=str(ROOT))
    if command[0] != str(ROOT / "headless.sh") or command[command.index("--allow") + 1] != "read-only":
        raise RuntimeError("Unexpected Shinka-to-Headless command routing.")
    # Headless documents --print-command as a preview: no agent/model execution.
    preview = subprocess.run(
        ["node", str(HEADLESS), "codex", "--prompt", "Configuration preview only",
         "--model", model.agent_model, "--reasoning-effort", model.effort,
         "--allow", "read-only", "--billing", "subscription", "--print-command"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=30, check=False,
    )
    if (preview.returncode or "read-only" not in preview.stdout or "codex" not in preview.stdout
            or model.agent_model not in preview.stdout or model.effort not in preview.stdout):
        raise RuntimeError("Headless command preview failed; no model was called.")
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("No C++ compiler is available.")
    baseline = None
    reference = ROOT / "baseline-search.json"
    if reference.is_file():
        recorded = json.loads(reference.read_text())
        if (recorded["source_sha256"] == snapshot["snapshot_sha256"]["initial.cpp"]
                and recorded["search_manifest_sha256"] == snapshot["snapshot_sha256"]["data/search/manifest.json"]
                and recorded["evaluator_sha256"] == snapshot["support_sha256"]["synthetic_eval.py"]):
            baseline = recorded
    return {
        "status": "setup_checked_without_experiments", "runtime": runtime,
        "model": model.agent_model, "reasoning_effort": model.effort,
        "shinka_commit": direct["vcs_info"]["commit_id"],
        "headless_commit": resolved.rsplit("#", 1)[-1],
        "compiler": compiler, "snapshot_files_checked": len(snapshot["snapshot_sha256"]),
        "active_task": str(TASK), "fitness": "family-balanced synthetic B/T",
        "corpus": corpus, "search_baseline_status": "measured" if baseline else "not_evaluated_for_current_inputs",
        "recorded_baseline": baseline,
        "baseline_re_evaluated": False, "model_requests": 0, "candidate_evaluations": 0,
        "docker_used": False, "workers": runner,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check installation only (default).")
    mode.add_argument("--dry-run", action="store_true", help="Same safe setup check; no evolution.")
    mode.add_argument("--run", action="store_true", help="Start real evolution; requires --generations.")
    parser.add_argument("--generations", type=int)
    args = parser.parse_args()
    if args.generations is not None and (not args.run or args.generations <= 0):
        parser.error("--generations must be positive and used with --run")
    if args.run and args.generations is None:
        parser.error("Real evolution requires an explicit --generations budget")
    env = subscription_environment()
    os.environ.clear()
    os.environ.update(env)
    report = check_setup(env, search_only=args.run)
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    if not args.run:
        return 0
    started = datetime.now(ZoneInfo("Asia/Novosibirsk"))
    run_dir = ROOT / "runs" / (started.strftime("%Y%m%dT%H%M%S%z") + f"-{time.time_ns() % 1000000:06d}")
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads((TASK / "snapshot.json").read_text())
    manifest = {
        "status": "initializing", "started_at": started.isoformat(), "pid": os.getpid(),
        "target_generations": args.generations, "includes_initial_generation_zero": True,
        "model": report["model"], "reasoning_effort": report["reasoning_effort"],
        "billing": "subscription", "fitness": report["fitness"],
        "search_manifest_sha256": snapshot["snapshot_sha256"]["data/search/manifest.json"],
        "source_sha256": snapshot["snapshot_sha256"]["initial.cpp"],
        "evaluator_sha256": snapshot["support_sha256"]["synthetic_eval.py"],
        "config_sha256": snapshot["snapshot_sha256"]["shinka.yaml"],
        "validation_accessed": False, "open15_accessed": False,
        "shinka_commit": report["shinka_commit"], "headless_commit": report["headless_commit"],
    }
    def save_manifest():
        (run_dir / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    save_manifest()
    print(f"RUN_DIR={run_dir}", flush=True)
    from shinka.cli.run import main as shinka_main
    manifest["status"] = "running"
    save_manifest()
    try:
        result = shinka_main([
            "--task-dir", str(TASK), "--config-fname", "shinka.yaml",
            "--results_dir", str(run_dir), "--num_generations", str(args.generations),
        ])
        manifest.update(status="runner_returned", returncode=result)
        return result
    except BaseException as exc:
        manifest.update(status="failed", exception_type=type(exc).__name__)
        raise
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat()
        save_manifest()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        raise SystemExit(1)
