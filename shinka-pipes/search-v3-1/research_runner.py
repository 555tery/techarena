"""Run-local Shinka hooks. Import and --check never start a search."""

from contextlib import contextmanager
from contextvars import ContextVar
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import types

from support import ROOT, PARENT, digest, frozen_v2
from research import (VERSION, atomic_json, code_hash, exact_duplicate, memory,
                      prompt_memory, proposal_context, read_programs)
from selection import VERSION as SELECTION_VERSION, load_policy
from selection_runtime import install_selection, prepared_manifest, refresh
from parallel_runtime import install_crossover_feedback, reserve_source
import mixed_seed_runtime as mixed

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
            or manifest.get("selection_protocol") != SELECTION_VERSION
            or manifest.get("service_tier") != "default"
            or manifest.get("billing") != "subscription"
            or type(budget) is not int or budget < 2
            or generations is not None and generations != budget):
        raise ValueError("requires a separately authorized run, original budget and research policy")
    if manifest.get("night_protocol") is not None:
        policy = json.loads((ROOT / "night-policy.json").read_text())
        if (manifest["night_protocol"] != policy["version"] or budget != policy["target_generations"]
                or manifest.get("night_policy_sha256") != digest(ROOT / "night-policy.json")
                or manifest.get("launch_authorized") is not True
                or manifest.get("model") != policy["model"] or manifest.get("reasoning_effort") != "xhigh"):
            raise ValueError("night run does not match the prepared policy/model/budget")
        plan = mixed.load_plan(ROOT)
        if (manifest.get("seed_protocol") != mixed.VERSION
                or manifest.get("seed_plan_sha256") != plan["plan_sha256"]
                or manifest.get("initial_islands") != plan["initial_islands"]
                or manifest.get("max_islands") != plan["max_islands"]):
            raise ValueError("night run does not match the pinned mixed-seed plan")
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
        duplicate = reserve_source(state, code)
        if duplicate is None:
            return result
        event = {"generation": state["generation"], "source_sha256": code_hash(code),
                 "duplicate_of": duplicate, "evaluated": False}
        state["duplicates"].append(event)
        atomic_json(patch_dir / "exact-duplicates.json", state["duplicates"])
        error = (f"Exact source duplicate of {duplicate}. "
                 "No evaluator was run. Return a complete proposal for the SAME parent with a "
                 "substantive behavioral difference; explain why it is not the same tested policy. "
                 "This retry uses the existing three-attempt limit, not another generation.")
        return code, 0, output, error, patch_text, patch_path

    module.apply_patch_async = guarded_apply
    try:
        yield
    finally:
        module.apply_patch_async = original_apply


def _lineage_programs(programs, lineage_id):
    local = []
    for program in programs:
        metadata = program.get("metadata", {})
        if not isinstance(metadata, dict):
            try:
                metadata = json.loads(metadata or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
        if (program.get("island_idx") == lineage_id
                and not metadata.get("_is_island_copy")
                and not metadata.get("_spawned_island")):
            local.append(program)
    return local


def _lineage_leader(context, programs, lineage_id):
    local = [p for p in _lineage_programs(programs, lineage_id)
             if p.get("correct") and p.get("generation", 0) < context["generation"]]
    leader = max(local, key=lambda p: (p["combined_score"], -p["generation"], p["id"]), default=None)
    context["leader"] = None if leader is None else {
        key: leader[key] for key in ("id", "generation", "source_sha256")
    }
    context["leader_selection"] = f"best completed correct program in isolated lineage {lineage_id}"


def _seed_meta_queue(summarizer, programs, lineage_count=8):
    """Bound the first post-isolation meta batch to one best queued item per lineage."""
    queued = {p.id: p for p in summarizer.evaluated_since_last_meta}
    best_by_island = {}
    for program in programs:
        metadata = program.get("metadata", {})
        if not isinstance(metadata, dict):
            try:
                metadata = json.loads(metadata or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
        island = program.get("island_idx")
        if (not program.get("correct") or type(island) is not int
                or not 0 <= island < lineage_count
                or metadata.get("_is_island_copy") or metadata.get("_spawned_island")
                or program["id"] not in queued):
            continue
        previous = best_by_island.get(island)
        if previous is None or (program["combined_score"], -program["generation"], program["id"]) > (
                previous["combined_score"], -previous["generation"], previous["id"]):
            best_by_island[island] = program
    if not best_by_island:
        return 0
    chosen_ids = {p["id"] for p in best_by_island.values()}
    summarizer.evaluated_since_last_meta = [
        p for p in summarizer.evaluated_since_last_meta if p.id in chosen_ids]
    return len(chosen_ids)


async def _mixed_seed_proposal(self, *, run, generation, assignment, plan,
                              model_sample_probs=None, model_posterior=None):
    """Create one pinned-source or task-only root through Shinka's LLM client."""
    lineage_id = assignment["lineage_id"]
    seed = mixed.seed_for_lineage(plan, lineage_id)
    task_scaffold = (Path(run) / "task" / "initial.cpp").read_text(encoding="utf-8")
    gen_dir = Path(run) / f"gen_{generation}"
    source_path = gen_dir / "main.cpp"
    attempts = 1 if seed["kind"] in {"strong", "simple"} else 3
    total_cost = 0.0
    response = None
    error = None
    source = None

    if seed["kind"] in {"strong", "simple"}:
        source = mixed.seed_code(plan, lineage_id, task_scaffold)
    else:
        prompt = seed["prompt"]
        system_msg = (
            "Implement the requested allocator independently from the task and interface only. "
            "Do not use prior allocator code, research history, other candidate branches, or tools. "
            "Return a complete C++20 source in one fenced cpp block. The runtime preserves the "
            "protected source prefix and suffix and uses only your EVOLVE-BLOCK implementation."
        )
        for attempt in range(1, attempts + 1):
            message = prompt + (
                f"\n\nIndependent implementation trial {lineage_id - 3}. "
                "Return the complete source with exactly one EVOLVE-BLOCK. "
                "Do not add commentary outside the fenced cpp block."
            )
            if error:
                message += "\nThe previous response was unusable: " + error + ". Return a corrected complete source."
            llm_kwargs = self.llm.get_kwargs(model_sample_probs=model_sample_probs)
            model_name = llm_kwargs.get("model_name", "unknown")
            if self.llm_selection is not None:
                self.llm_selection.update_submitted(model_name)
            response_cost = 0.0
            try:
                response = await self.llm.query(
                    msg=message,
                    system_msg=system_msg,
                    msg_history=[],
                    llm_kwargs=llm_kwargs,
                    model_sample_probs=model_sample_probs,
                    model_posterior=model_posterior,
                )
                if response is None or not response.content:
                    raise ValueError("independent seed response was empty")
                response_cost = float(getattr(response, "cost", 0.0) or 0.0)
                total_cost += response_cost
                source = mixed.independent_candidate(response.content, seed["scaffold"], task_scaffold)
                duplicate = reserve_source(_proposal.get(), source)
                if duplicate:
                    source = None
                    error = "the returned source duplicates an evaluated or in-flight source"
                    continue
                break
            except Exception as exc:
                source = None
                error = str(exc)[:1000]
            finally:
                if self.llm_selection is not None:
                    self.llm_selection.update_cost(arm=model_name, cost=response_cost)

    if source is None:
        return None, {"api_costs": total_cost, "patch_type": "mixed_seed",
                      "patch_name": seed["name"], "patch_description": "Task-only independent seed",
                      "error_attempt": error or "independent source was unavailable",
                      "last_error_msg": error or "independent source was unavailable",
                      "patch_attempt": attempts, "mixed_seed": assignment}, False

    # Fixed seeds are reconstructed from their pinned mutable block using the
    # current task's exact protected prefix and suffix.
    duplicate = reserve_source(_proposal.get(), source)
    if duplicate:
        return None, {"api_costs": total_cost, "patch_type": "mixed_seed",
                      "patch_name": seed["name"], "patch_description": "Pinned mixed seed",
                      "error_attempt": duplicate, "last_error_msg": duplicate,
                      "patch_attempt": 1, "mixed_seed": assignment}, False
    source_path.write_text(source, encoding="utf-8")
    content_hash = code_hash(source)
    patch_text = f"MIXED-SEED {lineage_id}: {seed['name']} ({assignment['kind']})"
    metadata = {
        "api_costs": total_cost,
        "patch_type": "mixed_seed",
        "patch_name": seed["name"],
        "patch_description": ("Independent task-only implementation" if seed["kind"] == "independent"
                              else "Pinned strong/simple seed"),
        "num_applied": 1,
        "error_attempt": None,
        "novelty_attempt": 1,
        "resample_attempt": 1,
        "patch_attempt": attempt if seed["kind"] == "independent" else 1,
        "mixed_seed": {**assignment, "source_sha256": content_hash},
        "seed_asset_sha256": seed.get("source_sha256") or seed.get("prompt_sha256"),
    }
    if response is not None:
        metadata["model_name"] = getattr(response, "model_name", None)
        metadata["llm_result"] = response.to_dict() if hasattr(response, "to_dict") else None
    return patch_text, metadata, True


def install_research(runner, run, prior):
    """Install only on the future runner instance; no installed-package edits."""
    if getattr(runner, "_pipes_research_installed", False):
        return
    if (runner.max_proposal_jobs not in (1, 2) or runner.max_evaluation_jobs not in (1, 2) or runner.max_db_workers != 1
            or runner.evo_config.max_patch_attempts != 3
            or runner.evo_config.max_patch_resamples != 1 or runner.evo_config.max_novelty_attempts != 1):
        raise ValueError("research adapter requires at most two workers and three repair attempts")
    original_patch = runner._run_patch_async
    reservations = {}
    install_crossover_feedback(runner)

    async def propose(self, parent_program, archive_programs, top_k_programs, generation,
                      meta_recs=None, **kwargs):
        programs = read_programs(run)
        context = proposal_context(programs, parent_program.id, generation)
        if context["parent"]["source_sha256"] != code_hash(parent_program.code):
            raise ValueError("sampled parent source differs from the saved research evidence")
        directory = Path(run) / f"gen_{generation}"
        selection_path = directory / "selection-context.json"
        decision = None
        assignment = None
        if getattr(self, "_pipes_selection_installed", False):
            decision = json.loads(selection_path.read_text())
            if (decision["generation"] != generation or decision["selected_parent"]["id"] != parent_program.id
                    or decision["selected_parent"]["source_sha256"] != code_hash(parent_program.code)):
                raise ValueError("proposal differs from recorded parent selection")
            assignment = decision.get("mixed_seed")
            context["selection"] = decision

        isolated = isinstance(assignment, dict) and assignment.get("phase") in {"seed", "warmup"}
        lineage_id = assignment.get("lineage_id") if isolated else None
        lineage = _lineage_programs(programs, lineage_id) if isolated else programs
        # Keep a complete, durable run ledger for reporting, but only feed the
        # current branch's evidence into a warmup proposal. Independent roots
        # bypass this hook's prompt and receive the task-only prompt directly.
        ledger = memory(lineage)
        atomic_json(Path(run) / "research-memory.json", memory(programs))
        if isolated:
            _lineage_leader(context, programs, lineage_id)
            extra = ("MIXED-START ISOLATION: use only this lineage's completed candidates and feedback. "
                     "Do not infer from other lineages or historical memory.\n")
            if assignment["phase"] == "warmup":
                extra += prompt_memory(ledger, {"prompt_lines": []}, parent_program.generation)
        else:
            extra = prompt_memory(ledger, prior, parent_program.generation)
        if decision is not None:
            selected = decision["selected_parent"]
            if isolated:
                extra += (f"\nLINEAGE PARENT: mode={decision['mode']}; lineage={lineage_id}; "
                          f"local mean leader={decision['island_mean_leader']['mean']:.9f}; "
                          f"fixed-baseline tail loss={selected['regression']['tail_loss']:.9f}; "
                          f"maximum case loss={selected['regression']['max_case_loss']:.9f}.")
            else:
                extra += (f"\nPARENT SELECTION: mode={decision['mode']}; specialist families={decision['specialist_families']}; "
                          f"fixed-baseline tail loss={selected['regression']['tail_loss']:.9f}; "
                          f"maximum case loss={selected['regression']['max_case_loss']:.9f}. "
                          "Retain useful mechanisms while improving mean F/T and addressing the listed regressions.")
        (directory / "research-prompt.txt").write_text(extra + "\n")
        token = _proposal.set({"programs": programs, "generation": generation,
                               "directory": directory.resolve(), "duplicates": [],
                               "run": run, "reservations": reservations})
        try:
            if assignment and assignment.get("phase") == "seed":
                result = await _mixed_seed_proposal(
                    self, run=run, generation=generation, assignment=assignment,
                    plan=self._pipes_mixed_seed_plan,
                    model_sample_probs=kwargs.get("model_sample_probs"),
                    model_posterior=kwargs.get("model_posterior"),
                )
            else:
                result = await original_patch(
                    parent_program, archive_programs, top_k_programs, generation,
                    meta_recs=extra if isolated else "\n\n".join(
                        x for x in (meta_recs, extra) if x), **kwargs)
            if result and result[2]:
                context.update(source_sha256=digest(directory / "main.cpp"),
                               name=result[1].get("patch_name"),
                               claimed_mechanism=result[1].get("patch_description"))
                if assignment:
                    context["mixed_seed"] = {**assignment,
                                             "source_sha256": context["source_sha256"]}
                atomic_json(directory / "research-context.json", context)
                result[1]["research_protocol"] = VERSION
                result[1]["research_duplicate_retries"] = len(_proposal.get()["duplicates"])
            else:
                for sha, owner in list(reservations.items()):
                    if owner == generation:
                        del reservations[sha]
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
    mixed_plan = None
    if manifest.get("seed_protocol") == mixed.VERSION:
        mixed_plan = mixed.load_plan(ROOT)
        if (digest(task / "initial.cpp") != mixed_plan["seeds"][0]["source_sha256"]
                or manifest.get("seed_plan_sha256") != mixed_plan["plan_sha256"]):
            raise ValueError("run baseline is not the pinned lineage-zero strong seed")
    if manifest.get("snapshot_sha256") != digest(ROOT / "snapshot.json"):
        raise ValueError("run manifest does not pin the prepared research support")
    from shinka.core import async_runner
    repair = frozen_v2("patch_repair.py")
    prior = json.loads((ROOT / "research-prior.json").read_text())
    original_build = cli._build_runner
    runners = []
    env = {"PIPES_SEARCH_V31_ROOT": str(ROOT), "PIPES_SEARCH_V31_RESEARCH": VERSION,
           "PIPES_SEARCH_V31_SELECTION": SELECTION_VERSION,
           "SHINKA_HEADLESS_COMMAND": str(ROOT / "headless.sh")}
    previous = {k: os.environ.get(k) for k in env}
    night = manifest.get("night_protocol") == "overnight-v1"
    night_policy = json.loads((ROOT / "night-policy.json").read_text()) if night else None
    if night:
        if not os.environ.get("PIPES_SEARCH_V31_SUPERVISOR"):
            raise ValueError("use the supervisor for process ownership, cleanup and configured deadlines")
        env["PIPES_SEARCH_V31_NIGHT"] = "overnight-v1"
        previous["PIPES_SEARCH_V31_NIGHT"] = os.environ.get("PIPES_SEARCH_V31_NIGHT")

    def build(**kwargs):
        runner = original_build(**kwargs)
        workers = (runner.max_proposal_jobs, runner.max_evaluation_jobs, runner.max_db_workers)
        if night and workers != (2, 2, 1):
            raise ValueError("overnight preparation requires proposal/evaluation/database workers 2/2/1")
        if not night and workers != (1, 1, 1):
            raise ValueError("parallel work requires the overnight budget and process supervisor")
        if night:
            from night_runtime import install_night_runtime
            install_night_runtime(runner, run, night_policy)
        else:
            repair.install_stop_on_failed_proposal(runner)
        install_research(runner, run, prior)
        runner._pipes_mixed_seed_plan = mixed_plan
        install_selection(runner, run)
        if night:
            from meta_runtime import install_meta

            if mixed_plan is None:
                install_meta(runner, should_start_meta=lambda: (
                    not runner.should_stop.is_set()
                    and runner._pipes_night_state.admission_reason() is None))
            else:
                meta_seeded = False

                def should_start_meta():
                    nonlocal meta_seeded
                    if (runner.should_stop.is_set()
                            or runner._pipes_night_state.admission_reason() is not None):
                        return False
                    programs = read_programs(run)
                    if not mixed.mark_isolation_released(run, programs, 4):
                        return False
                    if not meta_seeded:
                        summarizer = getattr(runner.meta_summarizer, "sync_summarizer", None)
                        if summarizer is None:
                            raise ValueError("native meta summarizer lost its synchronous queue")
                        if not _seed_meta_queue(summarizer, programs):
                            return False
                        meta_seeded = True
                    return True

                install_meta(runner, should_start_meta=should_start_meta)
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
        if night and runners:
            state = runners[0]._pipes_night_state.snapshot()
            stopped = {"reason": state["stop_reason"], "state": state,
                       "completed_generations": runners[0].completed_generations}
        if (run / "programs.sqlite").exists():
            atomic_json(run / "research-memory.json", memory(read_programs(run)))
            manifest, sha = prepared_manifest(run)
            refresh(run, manifest, sha, load_policy())
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
