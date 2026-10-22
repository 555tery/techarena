"""Fabricated complete results only; no candidate, model or held-out inputs."""

import copy
import json
import math
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

import selection as s
import selection_runtime as runtime
from research import atomic_json, code_hash, read_programs
import research_runner as hooks
from test_research import database


def suite(families=5, repeats=4):
    cases = [{"id": f"case-{i:03d}", "family": f"family-{i // repeats}", "sha256": str(i),
              "stats": {"volume_lower_bound": 100, "final_live_volume": 100}}
             for i in range(families * repeats)]
    return {"case_count": len(cases), "families": sorted({c["family"] for c in cases}),
            "cases_per_family": repeats, "cases": cases}


def program(name, generation, trenches=None, island=0, manifest=None, code=None):
    manifest = manifest or suite()
    trenches = trenches or [200] * manifest["case_count"]
    rows = [{"id": c["id"], "family": c["family"], "test_sha256": c["sha256"],
             "trench": t, "bound": 100, "final": 100, "kpi": 100/t,
             "solver_cpu_s": .1, "solver_rss_mib": 10.} for c, t in zip(manifest["cases"], trenches)]
    return {"id": name, "generation": generation, "parent_id": None, "correct": True,
            "source_sha256": code_hash(code or name), "combined_score": sum(r["kpi"] for r in rows)/len(rows),
            "island_idx": island, "metadata": {}, "private_metrics": {
                "research_manifest_sha256": "manifest", "research_cases": rows}}


def settings(run, seed):
    atomic_json(run / "run-manifest.json", {"source_sha256": seed["source_sha256"], "target_generations": 20,
                "selection_protocol": s.VERSION, "search_manifest_sha256": "manifest"})


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.policy = s.load_policy()
        self.manifest = suite()

    def test_tail_measures_positive_losses_and_includes_zeros(self):
        baseline = program("baseline", 0)
        mixed = program("mixed", 1, [400] + [100] * 19)
        before = copy.deepcopy([baseline, mixed])
        pool, base = s.profiles([baseline, mixed], self.manifest, "manifest", self.policy)
        reg = pool[1]["regression"]
        self.assertEqual(reg["tail_count"], 2)
        self.assertAlmostEqual(reg["tail_loss"], .125)  # .25 loss + one zero, divided by 2.
        self.assertAlmostEqual(reg["max_case_loss"], .25)
        self.assertEqual(reg["regressed_cases"], 1)
        self.assertGreater(pool[1]["mean"], base["mean"])
        self.assertEqual([baseline, mixed], before)
        manifest = suite(38)
        rows, _ = s.profiles([program("b", 0, manifest=manifest)], manifest, "manifest", self.policy)
        self.assertEqual(rows[0]["regression"]["tail_count"], 16)

    def test_robust_slot_uses_near_leader_band_and_fixed_baseline(self):
        entries = [program("baseline", 0),
                   program("volatile", 1, [100]*9 + [200]*10 + [240]),
                   program("steady", 2, [100]*8 + [120] + [200]*11)]
        pool, base = s.profiles(entries, self.manifest, "manifest", self.policy, 3)
        chosen, decision = s.choose(pool, "volatile", 3, self.policy)
        self.assertEqual(chosen["id"], "steady")
        self.assertEqual(decision["mode"], "robust")
        self.assertEqual(chosen["regression"]["tail_loss"], 0)
        self.assertLess(decision["island_mean_leader"]["mean"] - chosen["mean"], .005)
        self.assertEqual(s.registry(pool, base, "manifest", self.policy)["mean_leader"]["id"], "volatile")
        # A safe but far weaker baseline cannot displace the leader.
        chosen, _ = s.choose(pool[:2], "volatile", 3, self.policy)
        self.assertEqual(chosen["id"], "volatile")

    def test_family_specialist_survives_lower_mean_and_source_copies(self):
        entries = [program("baseline", 0), program("leader", 1, [160]*20),
                   program("specialist", 2, [100]*4+[200]*16)]
        pool, base = s.profiles(entries, self.manifest, "manifest", self.policy)
        chosen, info = s.choose(pool, "leader", 5, self.policy)
        self.assertEqual(chosen["id"], "specialist")
        self.assertLess(chosen["mean"], pool[1]["mean"])
        self.assertEqual(info["specialist_families"], ["family-0"])
        archive = s.registry(pool, base, "manifest", self.policy)
        self.assertEqual(archive["family_champions"]["family-0"]["id"], "specialist")
        clone = {**entries[2], "id": "clone"}
        cloned, _ = s.profiles(entries + [clone], self.manifest, "manifest", self.policy)
        self.assertEqual(len(s.deduplicated(cloned)), 3)
        self.assertEqual(s.choose(cloned, "leader", 5, self.policy)[0]["source_sha256"], chosen["source_sha256"])

    def test_cycle_bootstrap_island_and_future_exclusion(self):
        entries = [program("baseline", 0), program("leader", 1, [160]*20),
                   program("foreign", 2, [100]*20, island=1), program("future", 6, [100]*20)]
        pool, _ = s.profiles(entries, self.manifest, "manifest", self.policy, 5)
        self.assertNotIn("future", {p["id"] for p in pool})
        for generation in (1, 2, 4, 6, 7, 9):
            self.assertEqual(s.choose(pool, "baseline", generation, self.policy)[0]["id"], "baseline")
        chosen, info = s.choose(pool, "leader", 5, self.policy)
        self.assertEqual(chosen["island_idx"], 0)
        self.assertEqual(info["mode"], "score_fallback_no_distinct_specialist")
        chosen, info = s.choose(pool, "baseline", 3, self.policy, initialized=False)
        self.assertEqual((chosen["id"], info["mode"]), ("baseline", "bootstrap"))

    def test_incomplete_foreign_nonfinite_and_inconsistent_evidence_rejected(self):
        seed = program("baseline", 0)
        for kind in ("missing", "duplicate", "hash", "manifest", "score", "cpu", "rss", "nan", "float_trench"):
            p = program("bad", 1)
            rows = p["private_metrics"]["research_cases"]
            if kind == "missing": rows.pop()
            elif kind == "duplicate": rows[-1] = copy.deepcopy(rows[0])
            elif kind == "hash": rows[0]["test_sha256"] = "foreign"
            elif kind == "manifest": p["private_metrics"]["research_manifest_sha256"] = "foreign"
            elif kind == "score": p["combined_score"] += .1
            elif kind == "cpu": rows[0]["solver_cpu_s"] = 5
            elif kind == "rss": rows[0]["solver_rss_mib"] = 256
            elif kind == "nan": rows[0]["kpi"] = math.nan
            elif kind == "float_trench": rows[0]["trench"] = 200.
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                s.profiles([seed, p], self.manifest, "manifest", self.policy)
        bad_copy = program("clone", 0, [100]*20, code="baseline")
        with self.assertRaises(ValueError):
            s.profiles([seed, bad_copy], self.manifest, "manifest", self.policy)
        with self.assertRaises(ValueError):
            s.profiles([program("different_seed", 0), seed], self.manifest, "manifest", self.policy)

    def test_wrong_candidates_are_never_selected_and_missing_baseline_fails(self):
        wrong = program("wrong", 1, [100]*20)
        wrong["correct"] = False
        pool, _ = s.profiles([program("baseline", 0), wrong], self.manifest, "manifest", self.policy)
        self.assertEqual(len(pool), 1)
        with self.assertRaises(ValueError):
            s.profiles([wrong], self.manifest, "manifest", self.policy)

    def test_publisher_diagnostics_keep_primary_metrics_identical(self):
        p = program("new", 1, [400]+[100]*19)
        metrics = {"combined_score": p["combined_score"], "private": copy.deepcopy(p["private_metrics"]),
                   "public": {"valid_cases": 20}, "text_feedback": "native", "manifest_sha256": "manifest"}
        before = copy.deepcopy(metrics)
        runtime.enrich_selection(metrics, 1, p["source_sha256"], [program("baseline", 0)],
                                 self.manifest, "manifest", self.policy)
        self.assertEqual(metrics["combined_score"], before["combined_score"])
        self.assertEqual(metrics["public"], before["public"])
        self.assertEqual(metrics["private"]["research_cases"], before["private"]["research_cases"])
        self.assertAlmostEqual(metrics["selection_diagnostics"]["tail_loss"], .125)

    def test_registry_rebuild_after_loss_or_resume_is_identical_without_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            entries = [program("baseline", 0), program("leader", 1, [160]*20),
                       program("specialist", 2, [100]*4+[200]*16)]
            database(run, [(p, p["id"]) for p in entries])
            settings(run, entries[0])
            original = (run / "programs.sqlite").read_bytes()
            with patch.object(subprocess, "run", side_effect=AssertionError("process forbidden")), \
                    patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")):
                runtime.refresh(run, self.manifest, "manifest", self.policy)
                first = (run / "selection-state.json").read_bytes()
                (run / "selection-state.json").unlink()  # Disposable fixture cache only.
                runtime.refresh(run, self.manifest, "manifest", self.policy)
            self.assertEqual(first, (run / "selection-state.json").read_bytes())
            self.assertEqual(original, (run / "programs.sqlite").read_bytes())


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_database_specialist_outside_archive_and_parent_lineage(self):
        # REAL installed database and async methods; every score is fabricated.
        from shinka.database.dbase import DatabaseConfig, Program, ProgramDatabase
        from shinka.database.async_dbase import AsyncProgramDatabase
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            manifest, policy = suite(), s.load_policy()
            entries = [program("baseline", 0), program("leader", 1, [160]*20),
                       program("specialist", 2, [100]*4+[200]*16)]
            settings(run, entries[0])
            config = DatabaseConfig(db_path=str(run / "programs.sqlite"), num_islands=1, archive_size=1)
            db = ProgramDatabase(config, embedding_model=None)
            adb = AsyncProgramDatabase(db, max_workers=1)
            try:
                for p in entries:
                    db.add(Program(id=p["id"], code=p["id"], generation=p["generation"],
                        combined_score=p["combined_score"], correct=True, complexity=1,
                        private_metrics=p["private_metrics"], parent_id="baseline" if p["generation"] else None))
                self.assertEqual(db.get_best_program().id, "leader")
                self.assertIsNone(db.cursor.execute("SELECT program_id FROM archive WHERE program_id='specialist'").fetchone())
                chosen = await adb.get_async("specialist")
                leader = await adb.get_async("leader")
                baseline = await adb.get_async("baseline")
                # Keep the original upstream draw under control, while using its
                # actual DB/get_async/Program interface and persisted evidence.
                adb.sample_with_fix_mode_async = AsyncMock(return_value=(leader, [chosen], [baseline, chosen], False))
                runtime.install_database_sampling(adb, run, manifest, "manifest", policy, 1, 20)
                parent, archive, top, fix = await adb.sample_with_fix_mode_async(target_generation=5)
                self.assertEqual(parent.id, "specialist")
                self.assertFalse(fix)
                self.assertEqual(archive, [])
                self.assertEqual([p.id for p in top], ["baseline"])
                decision = json.loads((run / "gen_5/selection-context.json").read_text())
                self.assertEqual(decision["selected_parent"]["id"], parent.id)
                self.assertEqual(db.get_best_program().id, "leader")
                self.assertEqual(db.get("specialist").combined_score, entries[2]["combined_score"])
                # Route the selected Program through the actual research hook:
                # proposal provenance and parent seen by the patch method agree.
                seen = []
                async def patch_method(parent, archive, top, generation, **kwargs):
                    seen.append(parent.id)
                    (run / f"gen_{generation}/main.cpp").write_text("new synthetic source")
                    return "diff", {"patch_name": "fixture", "patch_description": "no solver execution"}, True
                runner = types.SimpleNamespace(max_proposal_jobs=1, max_evaluation_jobs=1, max_db_workers=1,
                    _run_patch_async=patch_method, _pipes_selection_installed=True,
                    evo_config=types.SimpleNamespace(max_patch_attempts=3, max_patch_resamples=1, max_novelty_attempts=1))
                hooks.install_research(runner, run, {"prompt_lines": []})
                await runner._run_patch_async(parent, archive, top, 5)
                context = json.loads((run / "gen_5/research-context.json").read_text())
                self.assertEqual(seen, ["specialist"])
                self.assertEqual(context["parent"]["id"], "specialist")
                self.assertEqual(context["selection"]["selected_parent"]["id"], "specialist")
                self.assertIn("mode=specialist", (run / "gen_5/research-prompt.txt").read_text())
                with self.assertRaises(ValueError):
                    await runner._run_patch_async(leader, archive, top, 5)
            finally:
                adb.executor.shutdown(wait=True)
                db.close()

    async def test_fix_mode_is_untouched_and_bad_budget_does_not_sample(self):
        parent, archive, top = object(), [object()], []
        original = AsyncMock(return_value=(parent, archive, top, True))
        db = types.SimpleNamespace(sample_with_fix_mode_async=original)
        runtime.install_database_sampling(db, Path("/unused"), suite(), "manifest", s.load_policy(), 2, 10)
        result = await db.sample_with_fix_mode_async(target_generation=3)
        self.assertIs(result[0], parent)
        self.assertIs(result[1], archive)
        self.assertTrue(result[3])
        for generation in (None, True, 0, 10):
            with self.assertRaises(ValueError):
                await db.sample_with_fix_mode_async(target_generation=generation)
        self.assertEqual(original.await_count, 1)

    async def test_setup_installs_after_async_database_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            seed = program("baseline", 0)
            database(run, [(seed, "baseline")])
            settings(run, seed)
            db = types.SimpleNamespace(sample_with_fix_mode_async=AsyncMock())
            runner = types.SimpleNamespace(max_proposal_jobs=1, max_evaluation_jobs=1, max_db_workers=1,
                async_db=None, db_config=types.SimpleNamespace(num_islands=2, enforce_island_separation=True,
                    archive_selection_strategy="fitness", parent_selection_strategy="weighted"))
            async def original_setup():
                runner.async_db = db
            runner._setup_async = original_setup
            with patch.object(runtime, "prepared_manifest", return_value=(suite(), "manifest")):
                runtime.install_selection(runner, run)
                self.assertIsNone(runner.async_db)
                await runner._setup_async()
            self.assertTrue(db._pipes_selection_installed)
            self.assertTrue((run / "selection-state.json").exists())


if __name__ == "__main__":
    unittest.main()
