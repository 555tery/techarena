"""Run-local Shinka hooks. Import and --check never start a search."""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import sys
import types

from support import ROOT, PARENT, digest, frozen_v2
from research import (VERSION, atomic_json, code_hash, exact_duplicate, memory,
                      prompt_memory, proposal_context, read_programs)

_proposal = ContextVar("pipes_v31_proposal", default=None)


def check_upstream():
    import importlib.util
    spec = importlib.util.find_spec("shinka")
    package = Path(spec.origin).parent
    policy = json.loads((ROOT / "research-policy.json").read_text())
    for name, sha in policy["upstream_files_sha256"].items():
        if digest(package / name) != sha:
            raise ValueError("Shinka research hook contract changed: " + name)
    return policy


def checked_run(run, generations=None):
    run = Path(run).resolve()
    if run.parent != ROOT / "runs" or run.is_symlink():
        raise ValueError("research hooks accept only this SEARCH-v3.1 run namespace")
    manifest = json.loads((run / "run-manifest.json").read_text())
    budget = manifest.get("target_generations")
    if (manifest.get("suite") != "search-v3.1" or manifest.get("status") != "running"
            or manifest.get("research_protocol") != VERSION
            or manifest.get("service_tier") != "default"
            or manifest.get("billing") != "subscription"
            or type(budget) is not int or budget < 2
            or generations is not None and generations != budget):
        raise ValueError("requires a separately authorized run, original budget and research policy")
    return run, manifest


@contextmanager
def patch_application_guard(module):
    """Use the upstream three-attempt repair loop for exact duplicates too."""
    original_apply = module.apply_patch_async

    async def guarded_apply(*args, **kwargs):
        result = await original_apply(*args, **kwargs)
        state = _proposal.get()
        if state is None:
            return result
        code, applied, output, error, patch_text, patch_path = result
        if error is not None or applied <= 0:
            return result
        patch_dir = Path(kwargs["patch_dir"]).resolve()
        if patch_dir != state["directory"]:
            raise ValueError("patch application escaped its research generation")
        duplicate = exact_duplicate(code, state["programs"])
        if duplicate is None:
            return result
        event = {"generation": state["generation"], "source_sha256": code_hash(code),
                 "duplicate_of": duplicate["generation"], "evaluated": False}
        state["duplicates"].append(event)
        atomic_json(patch_dir / "exact-duplicates.json", state["duplicates"])
        error = (f"Exact source duplicate of evaluated SEARCH-v3.1 generation {duplicate['generation']}. "
                 "No evaluator was run. Return a complete proposal for the SAME parent with a "
                 "substantive behavioral difference; explain why it is not the same tested policy. "
                 "This retry uses the existing three-attempt limit, not another generation.")
        return code, 0, output, error, patch_text, patch_path

    module.apply_patch_async = guarded_apply
    try:
        yield
    finally:
        module.apply_patch_async = original_apply


def install_research(runner, run, prior):
    """Install only on the future runner instance; no installed-package edits."""
    if getattr(runner, "_pipes_research_installed", False):
        return
    if (runner.max_proposal_jobs != 1 or runner.max_evaluation_jobs != 1 or runner.max_db_workers != 1
            or runner.evo_config.max_patch_attempts != 3
            or runner.evo_config.max_patch_resamples != 1 or runner.evo_config.max_novelty_attempts != 1):
        raise ValueError("research adapter requires the prepared serial pipeline and three repair attempts")
    original_patch = runner._run_patch_async

    async def propose(self, parent_program, archive_programs, top_k_programs, generation,
                      meta_recs=None, **kwargs):
        programs = read_programs(run)
        context = proposal_context(programs, parent_program.id, generation)
        if context["parent"]["source_sha256"] != code_hash(parent_program.code):
            raise ValueError("sampled parent source differs from the saved research evidence")
        ledger = memory(programs)
        atomic_json(Path(run) / "research-memory.json", ledger)
        extra = prompt_memory(ledger, prior, parent_program.generation)
        directory = Path(run) / f"gen_{generation}"
        (directory / "research-prompt.txt").write_text(extra + "\n")
        token = _proposal.set({"programs": programs, "generation": generation,
                               "directory": directory.resolve(), "duplicates": []})
        try:
            result = await original_patch(parent_program, archive_programs, top_k_programs, generation,
                                          meta_recs="\n\n".join(x for x in (meta_recs, extra) if x), **kwargs)
            if result and result[2]:
                context.update(source_sha256=digest(directory / "main.cpp"),
                               name=result[1].get("patch_name"),
                               claimed_mechanism=result[1].get("patch_description"))
                atomic_json(directory / "research-context.json", context)
                result[1]["research_protocol"] = VERSION
                result[1]["research_duplicate_retries"] = len(_proposal.get()["duplicates"])
            return result
        finally:
            _proposal.reset(token)

    runner._run_patch_async = types.MethodType(propose, runner)
    runner._pipes_research_installed = True


def run_with_research(cli, *, task, run, generations):
    """Future launch manager entry: it must supply a selected seed and run manifest.

    Does not invent a budget, create a run, choose a seed or resume any old run.
    The evaluation publisher handles native staging and paired feedback.
    """
    from evaluator import verify_snapshot
    verify_snapshot()
    check_upstream()
    run, manifest = checked_run(run, generations)
    task = Path(task).resolve()
    if not task.is_relative_to(run) or task == run:
        raise ValueError("future task snapshot must be inside its own run")
    for name in ("shinka.yaml", "evaluate.py", "AGENTS.md"):
        if digest(task / name) != digest(ROOT / "task" / name):
            raise ValueError("future task differs from prepared research configuration: " + name)
    if digest(task / "initial.cpp") != manifest.get("source_sha256"):
        raise ValueError("future selected seed does not match run manifest")
    if manifest.get("snapshot_sha256") != digest(ROOT / "snapshot.json"):
        raise ValueError("run manifest does not pin the prepared research support")
    from shinka.core import async_runner
    repair = frozen_v2("patch_repair.py")
    prior = json.loads((ROOT / "research-prior.json").read_text())
    original_build = cli._build_runner
    runners = []
    env = {"PIPES_SEARCH_V31_ROOT": str(ROOT), "PIPES_SEARCH_V31_RESEARCH": VERSION,
           "SHINKA_HEADLESS_COMMAND": str(ROOT / "headless.sh")}
    previous = {k: os.environ.get(k) for k in env}

    def build(**kwargs):
        runner = original_build(**kwargs)
        repair.install_stop_on_failed_proposal(runner)
        install_research(runner, run, prior)
        runners.append(runner)
        return runner

    cli._build_runner = build
    os.environ.update(env)
    try:
        with patch_application_guard(async_runner):
            result = cli.main(["--task-dir", str(task), "--config-fname", "shinka.yaml",
                               "--results_dir", str(run), "--num_generations", str(generations)])
        stopped = next((r._search_v2_repair_stop for r in runners
                        if getattr(r, "_search_v2_repair_stop", None)), None)
        if (run / "programs.sqlite").exists():
            atomic_json(run / "research-memory.json", memory(read_programs(run)))
        return result, stopped
    finally:
        cli._build_runner = original_build
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    if sys.argv[1:] != ["--check"]:
        raise SystemExit("Preparation only: use --check. Starting a run requires a separate launch request.")
    from evaluator import verify_snapshot
    verify_snapshot()
    check_upstream()
    print("Research hooks verified; model calls=0; candidate evaluations=0.")
