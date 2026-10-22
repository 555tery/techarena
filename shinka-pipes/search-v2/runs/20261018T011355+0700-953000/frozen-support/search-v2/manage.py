"""Check prepared SEARCH-v2 without experiments; --run requires a future explicit budget."""

from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
TASK = ROOT / "task"
sys.path.insert(0, str(PARENT))
from local_runtime import check_prerequisites, subscription_environment
from patch_repair import policy as patch_repair_policy, run_with_patch_repair


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
        cls(**config[ns])
    evo = config["evo"]
    if (evo["llm_models"] != ["headless/codex@gpt-6-astra?effort=xhigh"]
            or evo.get("embedding_model") is not None or evo.get("meta_rec_interval") is not None
            or evo.get("novelty_llm_models") is not None or evo.get("evolve_prompts")
            or evo.get("enable_wandb_logging") or evo.get("job_type") != "local"):
        raise ValueError("unexpected model, additional model calls or nonlocal backend")
    if any(runner.get(k) != 1 for k in ("max_evaluation_jobs", "max_proposal_jobs", "max_db_workers")):
        raise ValueError("SEARCH-v2 requires one worker per stage")
    repair = patch_repair_policy()
    if any(evo.get(k) != repair[k] for k in
           ("max_patch_attempts", "max_patch_resamples", "max_novelty_attempts")):
        raise ValueError("SEARCH-v2 requires three bounded patch attempts on the same parent")
    return config, runner


def check() -> dict:
    from evaluator import load_search
    manifest = load_search()
    snapshot = json.loads((ROOT / "snapshot.json").read_text())
    for base, key in ((ROOT, "files"), (PARENT, "shared_files")):
        for name, expected in snapshot[key].items():
            if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"prepared source or support changed: {name}")
    config, runner = load_config()
    direct = json.loads(importlib.metadata.distribution("shinka-evolve").read_text("direct_url.json"))
    if direct["vcs_info"]["commit_id"] != "8adc053a2ce4511ad2ac310e004c530a73fb974a":
        raise ValueError("installed Shinka differs from pinned version")
    return {"status": "prepared_only_no_experiments", "task": str(TASK),
            "cases": manifest["case_count"], "families": len(manifest["families"]),
            "model": config["evo"]["llm_models"][0],
            "reasoning_effort": "xhigh", "service_tier": "fast", "workers": runner,
            "patch_repair": patch_repair_policy(),
            "baseline_evaluated_on_v2": False, "candidate_evaluations": 0, "model_requests": 0,
            "validation_accessed": False, "open15_accessed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--generations", type=int)
    args = parser.parse_args()
    if args.generations is not None and (not args.run or args.generations <= 0):
        parser.error("--generations requires --run and a positive explicit budget")
    if args.run and args.generations is None:
        parser.error("--run requires a future authorized --generations budget")
    report = check()
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if not args.run:
        return 0
    env = subscription_environment()
    env["SHINKA_HEADLESS_COMMAND"] = str(ROOT / "headless.sh")
    env["PIPES_SEARCH_V2_ROOT"] = str(ROOT)
    check_prerequisites(env)
    os.environ.clear()
    os.environ.update(env)
    now = datetime.now(ZoneInfo("Asia/Novosibirsk"))
    run = ROOT / "runs" / (now.strftime("%Y%m%dT%H%M%S%z") + f"-{time.time_ns()%1000000:06d}")
    run.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "running", "started_at": now.isoformat(), "pid": os.getpid(),
                "target_generations": args.generations, "includes_initial_generation_zero": True,
                "billing": "subscription", "model": report["model"],
                "reasoning_effort": report["reasoning_effort"],
                "service_tier": report["service_tier"], "suite": "search-v2",
                "patch_repair": report["patch_repair"],
                "search_manifest_sha256": hashlib.sha256((TASK / "data/search/manifest.json").read_bytes()).hexdigest(),
                "snapshot_sha256": hashlib.sha256((ROOT / "snapshot.json").read_bytes()).hexdigest(),
                "source_sha256": hashlib.sha256((TASK / "initial.cpp").read_bytes()).hexdigest(),
                "evaluator_sha256": hashlib.sha256((ROOT / "evaluator.py").read_bytes()).hexdigest(),
                "validation_accessed": False, "open15_accessed": False}
    path = run / "run-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    from shinka.cli import run as cli
    try:
        result, repair_stop = run_with_patch_repair(
            cli, task=TASK, run=run, generations=args.generations)
        if repair_stop:
            manifest.update(status="needs_patch_repair", returncode=2,
                            stopped_generation=repair_stop["generation"])
            (run / "patch-repair-exhausted.json").write_text(
                json.dumps(repair_stop, ensure_ascii=False, indent=2) + "\n")
            print("Patch repair exhausted; stopped before the next generation. "
                  "See patch-repair-exhausted.json; no automatic restart.", file=sys.stderr)
            return 2
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
