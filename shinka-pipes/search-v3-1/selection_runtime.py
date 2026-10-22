"""Instance-local parent selection; never changes installed Shinka or scores."""

import asyncio
import json
from pathlib import Path
import types

from research import atomic_json, code_hash, read_programs
from selection import VERSION, choose, load_policy, mean_key, profiles, registry, selection_text, summary
from support import ROOT, digest
import mixed_seed_runtime as mixed


def prepared_manifest(run):
    manifest_path = ROOT / "task/data/search/manifest.json"
    run_manifest = json.loads((Path(run) / "run-manifest.json").read_text())
    sha = digest(manifest_path)
    if run_manifest.get("search_manifest_sha256") != sha or run_manifest.get("selection_protocol") != VERSION:
        raise ValueError("selection requires the pinned main corpus and policy")
    return json.loads(manifest_path.read_text()), sha


def refresh(run, manifest, manifest_sha, policy, before_generation=None):
    pool, baseline = profiles(read_programs(run), manifest, manifest_sha, policy, before_generation)
    run_manifest = json.loads((Path(run) / "run-manifest.json").read_text())
    if baseline["source_sha256"] != run_manifest.get("source_sha256"):
        raise ValueError("selection baseline source differs from authorized seed")
    archive = registry(pool, baseline, manifest_sha, policy)
    archive["policy_sha256"] = digest(ROOT / "selection-policy.json")
    atomic_json(Path(run) / "selection-state.json", archive)
    return pool


def _copy_ids(programs):
    result = set()
    for program in programs:
        metadata = program.get("metadata", {})
        if not isinstance(metadata, dict):
            try:
                metadata = json.loads(metadata or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
        if metadata.get("_is_island_copy") or metadata.get("_spawned_island"):
            result.add(program["id"])
    return result


def install_database_sampling(database, run, manifest, manifest_sha, policy, num_islands, budget,
                              *, mixed_plan=None, runner=None):
    if getattr(database, "_pipes_selection_installed", False):
        return
    original = database.sample_with_fix_mode_async

    async def sample(self, target_generation=None, novelty_attempt=None, max_novelty_attempts=None,
                     resample_attempt=None, max_resample_attempts=None):
        if type(target_generation) is not int or not 1 <= target_generation < budget:
            raise ValueError("parent selection is outside the authorized generation budget")
        parent, archive, top, needs_fix = await original(
            target_generation=target_generation, novelty_attempt=novelty_attempt,
            max_novelty_attempts=max_novelty_attempts, resample_attempt=resample_attempt,
            max_resample_attempts=max_resample_attempts)
        if needs_fix:
            return parent, archive, top, needs_fix
        assignment = None
        if mixed_plan is not None:
            while True:
                if (runner is not None and
                        (runner.should_stop.is_set()
                         or runner._pipes_night_state.admission_reason() is not None)):
                    raise asyncio.CancelledError("mixed bootstrap stopped by the run supervisor")
                assignment = mixed.reserve_assignment(
                    run, read_programs(run), target_generation, mixed_plan)
                if not (assignment and assignment.get("wait")):
                    break
                await asyncio.sleep(0.5)
            if assignment is None:
                mixed.mark_isolation_released(run, read_programs(run),
                                              mixed_plan["isolation_correct_per_lineage"])
        pool = refresh(run, manifest, manifest_sha, policy, target_generation)
        count = num_islands() if callable(num_islands) else num_islands
        initialized = len({p["island_idx"] for p in pool if p["island_idx"] is not None}) >= count
        if assignment is not None:
            lineage_id = assignment["lineage_id"]
            lineage_pool = [p for p in pool if p["island_idx"] == lineage_id]
            copy_ids = _copy_ids(read_programs(run))
            if assignment["phase"] == "seed":
                local_seed_parents = [p for p in lineage_pool if p["generation"] == 0]
                if not local_seed_parents:
                    raise ValueError(f"mixed seed lineage {lineage_id} has no generation-zero island copy")
                chosen = min(local_seed_parents, key=lambda p: (p["generation"], p["id"]))
                decision = {"version": VERSION, "generation": target_generation,
                            "requested_mode": "mixed-seed", "mode": "mixed-seed-root",
                            "island_idx": lineage_id, "upstream_parent": summary(chosen),
                            "selected_parent": summary(chosen), "island_mean_leader": summary(chosen),
                            "specialist_families": [], "primary_metric_changed": False}
                archive, top = [], []
            else:
                real_ids = {p["id"] for p in lineage_pool if p["id"] not in copy_ids}
                lineage_pool = [p for p in lineage_pool if p["id"] in real_ids]
                if not lineage_pool:
                    raise ValueError(f"mixed warmup lineage {lineage_id} has no evaluated root")
                local_leader = min(lineage_pool, key=mean_key)
                chosen, decision = choose(lineage_pool, local_leader["id"], target_generation,
                                          policy, initialized=True)
                decision["mode"] = "lineage-local-" + decision["mode"]
                decision["mixed_seed"] = assignment
                eligible_rows = [p for p in sorted(lineage_pool, key=mean_key)
                                 if p["id"] != chosen["id"]]
                archive_limit = int(getattr(self.config, "num_archive_inspirations", len(archive)))
                top_limit = int(getattr(self.config, "num_top_k_inspirations", len(top)))
                inspiration_ids = [p["id"] for p in eligible_rows[:archive_limit + top_limit]]
                inspiration_programs = []
                for program_id in inspiration_ids:
                    item = await self.get_async(program_id)
                    if item is not None:
                        inspiration_programs.append(item)
                archive = inspiration_programs[:archive_limit]
                top = inspiration_programs[archive_limit:archive_limit + top_limit]
                decision.update(island_idx=lineage_id, upstream_parent=summary(local_leader),
                                selected_parent=summary(chosen), island_mean_leader=summary(local_leader),
                                specialist_families=[])
            decision["mixed_seed"] = assignment
        else:
            chosen, decision = choose(pool, parent.id, target_generation, policy, initialized)
        selected = parent if chosen["id"] == parent.id else await self.get_async(chosen["id"])
        if (selected is None or not selected.correct or selected.island_idx != chosen["island_idx"]
                or selected.generation != chosen["generation"] or selected.combined_score != chosen["mean"]
                or code_hash(selected.code) != chosen["source_sha256"]):
            raise ValueError("selected parent changed since the complete evidence snapshot")
        # Upstream selected inspirations for the old parent. Remove the new
        # parent, same-code copies, foreign islands and duplicates across lists.
        seen = {chosen["source_sha256"]}
        eligible = {p["id"]: p for p in pool}

        def filtered(items):
            result = []
            for p in items:
                row = eligible.get(p.id)
                sha = code_hash(p.code)
                if row and row["island_idx"] == chosen["island_idx"] and sha == row["source_sha256"] and sha not in seen:
                    result.append(p)
                    seen.add(sha)
            return result

        if assignment is None:
            archive, top = filtered(archive), filtered(top)
        decision.update(manifest_sha256=manifest_sha, policy_sha256=digest(ROOT / "selection-policy.json"),
                        archive_inspiration_ids=[p.id for p in archive], top_k_inspiration_ids=[p.id for p in top])
        path = Path(run) / f"gen_{target_generation}" / "selection-context.json"
        atomic_json(path, decision)
        return selected, archive, top, False

    database.sample_with_fix_mode_async = types.MethodType(sample, database)
    database._pipes_selection_installed = True


def install_selection(runner, run):
    if getattr(runner, "_pipes_selection_installed", False):
        return
    policy = load_policy()
    manifest, sha = prepared_manifest(run)
    run_manifest = json.loads((Path(run) / "run-manifest.json").read_text())
    budget = run_manifest["target_generations"]
    night = run_manifest.get("night_protocol") == "overnight-v1"
    night_policy = json.loads((ROOT / "night-policy.json").read_text()) if night else None
    if night:
        # IDs include failed proposals; their distinct budget is not fitness work.
        budget += night_policy["max_failed_proposals"]
    mixed_plan = getattr(runner, "_pipes_mixed_seed_plan", None)
    initial_islands = mixed_plan["initial_islands"] if mixed_plan else 2
    if (runner.max_proposal_jobs not in (1, 2) or runner.max_evaluation_jobs not in (1, 2) or runner.max_db_workers != 1
            or runner.db_config.num_islands != initial_islands or not runner.db_config.enforce_island_separation
            or runner.db_config.archive_selection_strategy != "fitness"
            or runner.db_config.parent_selection_strategy != "weighted"):
        raise ValueError("selection adapter requires at most two workers, the prepared island count and score selection")
    original_setup = runner._setup_async

    async def setup(self):
        await original_setup()
        num_islands = self.db_config.num_islands
        if night:
            from islands_runtime import install_island_runtime, current_island_count
            isolation_ready = None
            if mixed_plan is not None:
                def isolation_ready(db):
                    db.cursor.execute("SELECT generation, correct, island_idx, metadata FROM programs")
                    rows = []
                    for row in db.cursor.fetchall():
                        metadata = row["metadata"]
                        try:
                            metadata = json.loads(metadata or "{}")
                        except (TypeError, json.JSONDecodeError):
                            metadata = {}
                        rows.append({"generation": int(row["generation"]),
                                     "correct": bool(row["correct"]),
                                     "island_idx": row["island_idx"],
                                     "metadata": metadata})
                    return mixed.mark_isolation_released(
                        run, rows, mixed_plan["isolation_correct_per_lineage"])

            install_island_runtime(self.async_db, **{key: night_policy[key] for key in (
                "initial_islands", "max_islands", "stagnation_evaluations", "migration_evaluations",
                "migration_rate", "island_elitism", "spawn_strategy")},
                isolation_ready=isolation_ready)
            num_islands = lambda: current_island_count(self.async_db)
        install_database_sampling(self.async_db, run, manifest, sha, policy, num_islands, budget,
                                  mixed_plan=mixed_plan, runner=self)
        refresh(run, manifest, sha, policy)

    runner._setup_async = types.MethodType(setup, runner)
    runner._pipes_selection_installed = True


def enrich_selection(metrics, generation, source_sha, programs, manifest, manifest_sha, policy):
    # The native evaluator already accepted every input and resource limit.
    candidate = {"id": "candidate", "generation": generation, "correct": True,
                 "source_sha256": source_sha, "island_idx": None,
                 "combined_score": metrics["combined_score"], "private_metrics": metrics["private"]}
    pool, _ = profiles(programs + [candidate], manifest, manifest_sha, policy)
    profile = next(p for p in pool if p["id"] == "candidate")
    metrics["selection_diagnostics"] = profile["regression"]
    metrics["private"]["selection_diagnostics"] = profile["regression"]
    metrics["text_feedback"] += "\n\nREGRESSIONS AGAINST FIXED BASELINE\n" + selection_text(profile)
    return metrics
