"""Instance-local parent selection; never changes installed Shinka or scores."""

import json
from pathlib import Path
import types

from research import atomic_json, code_hash, read_programs
from selection import VERSION, choose, load_policy, profiles, registry, selection_text
from support import ROOT, digest


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


def install_database_sampling(database, run, manifest, manifest_sha, policy, num_islands, budget):
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
        pool = refresh(run, manifest, manifest_sha, policy, target_generation)
        count = num_islands() if callable(num_islands) else num_islands
        initialized = len({p["island_idx"] for p in pool if p["island_idx"] is not None}) >= count
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
    if (runner.max_proposal_jobs not in (1, 2) or runner.max_evaluation_jobs not in (1, 2) or runner.max_db_workers != 1
            or runner.db_config.num_islands != 2 or not runner.db_config.enforce_island_separation
            or runner.db_config.archive_selection_strategy != "fitness"
            or runner.db_config.parent_selection_strategy != "weighted"):
        raise ValueError("selection adapter requires at most two workers, two initial islands and score selection")
    original_setup = runner._setup_async

    async def setup(self):
        await original_setup()
        num_islands = self.db_config.num_islands
        if night:
            from islands_runtime import install_island_runtime, current_island_count
            install_island_runtime(self.async_db, **{key: night_policy[key] for key in (
                "initial_islands", "max_islands", "stagnation_evaluations", "migration_evaluations",
                "migration_rate", "island_elitism", "spawn_strategy")})
            num_islands = lambda: current_island_count(self.async_db)
        install_database_sampling(self.async_db, run, manifest, sha, policy, num_islands, budget)
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
