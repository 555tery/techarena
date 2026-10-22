"""Research integration fixtures: no model, compiler, interactor or raw inputs."""

import asyncio
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

import research as r
import research_runner as hooks
import shinka_evaluate as publisher
from selection import VERSION as SELECTION_VERSION


def cases(trenches=(100, 200, 100), families=("a", "a", "b")):
    return [{"id": str(i), "family": f, "bound": 100, "final": 100,
             "test_sha256": str(i), "trench": t, "kpi": 100 / t}
            for i, (t, f) in enumerate(zip(trenches, families))]


def fixture_program(identifier="parent", generation=0, code="parent", rows=None):
    rows = rows or cases()
    groups = {}
    for row in rows:
        groups.setdefault(row["family"], []).append(row["kpi"])
    score = sum(sum(v) / len(v) for v in groups.values()) / len(groups)
    return {"id": identifier, "generation": generation, "parent_id": None, "correct": True,
            "source_sha256": r.code_hash(code), "combined_score": score, "island_idx": 0,
            "metadata": {"patch_name": "fixture", "patch_description": "claim only"},
            "private_metrics": {"research_cases": rows, "research_manifest_sha256": "manifest"}}


def database(run, entries):
    with sqlite3.connect(run / "programs.sqlite") as db:
        db.execute("CREATE TABLE programs(id TEXT,generation INTEGER,parent_id TEXT,code TEXT,correct INTEGER,"
                   "combined_score REAL,metadata TEXT,private_metrics TEXT,island_idx INTEGER)")
        for p, code in entries:
            db.execute("INSERT INTO programs VALUES(?,?,?,?,?,?,?,?,?)",
                       (p["id"], p["generation"], p["parent_id"], code, p["correct"], p["combined_score"],
                        json.dumps(p["metadata"]), json.dumps(p["private_metrics"]), p.get("island_idx", 0)))


class ResearchTests(unittest.TestCase):
    def test_mutable_old_status_is_not_a_dependency_but_sources_remain_pinned(self):
        import support
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "old").mkdir()
            (root / "old/active-run.json").write_text("completed")
            source = root / "old/source.py"
            source.write_text("unchanged")
            r.atomic_json(root / "source-guard.json", {"files": {
                "old/active-run.json": r.code_hash("running"), "old/source.py": support.digest(source)}})
            with patch.object(support, "ROOT", root), patch.object(support, "PARENT", root):
                self.assertEqual(len(support.verify_dependencies(include_stress=True)), 1)
                with self.assertRaises(ValueError):
                    support.verify_dependencies(include_active=True)
                source.write_text("changed source")
                with self.assertRaises(ValueError):
                    support.verify_dependencies(include_stress=True)

    def test_future_runner_installs_hooks_and_restores_process_state(self):
        from shinka.core import async_runner
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run, task = root / "runs/future", root / "runs/future/task"
            task.mkdir(parents=True)
            (root / "task").mkdir()
            for name in ("shinka.yaml", "evaluate.py", "AGENTS.md"):
                (root / "task" / name).write_text("fixture")
                (task / name).write_text("fixture")
            (task / "initial.cpp").write_text("selected seed")
            (root / "snapshot.json").write_text("{}")
            r.atomic_json(root / "research-prior.json", {"prompt_lines": []})
            r.atomic_json(run / "run-manifest.json", {
                "suite": "search-v3.1", "status": "running", "research_protocol": r.VERSION,
                "selection_protocol": SELECTION_VERSION,
                "service_tier": "default", "billing": "subscription", "target_generations": 3,
                "source_sha256": hooks.digest(task / "initial.cpp"),
                "snapshot_sha256": hooks.digest(root / "snapshot.json")})
            runner = types.SimpleNamespace(max_proposal_jobs=1, max_evaluation_jobs=1, max_db_workers=1,
                evo_config=types.SimpleNamespace(max_patch_attempts=3, max_patch_resamples=1, max_novelty_attempts=1),
                _run_patch_async=AsyncMock())
            build = lambda **kwargs: runner
            cli = types.SimpleNamespace(_build_runner=build)
            old_apply = async_runner.apply_patch_async
            repaired = []

            def fake_main(argv):
                self.assertEqual(argv[argv.index("--num_generations") + 1], "3")
                made = cli._build_runner()
                self.assertTrue(made._pipes_research_installed)
                self.assertEqual(os.environ["PIPES_SEARCH_V31_RESEARCH"], r.VERSION)
                self.assertIsNot(async_runner.apply_patch_async, old_apply)
                return 0

            cli.main = fake_main
            with patch.object(hooks, "ROOT", root), patch.object(hooks, "check_upstream"), \
                    patch.object(hooks, "install_selection") as selection_install, \
                    patch("evaluator.verify_snapshot"), \
                    patch.object(hooks, "frozen_v2", return_value=types.SimpleNamespace(
                        install_stop_on_failed_proposal=lambda item: repaired.append(item))), \
                    patch.dict(os.environ, {"PIPES_SEARCH_V31_RESEARCH": "previous"}):
                result, stopped = hooks.run_with_research(cli, task=task, run=run, generations=3)
                self.assertEqual(os.environ["PIPES_SEARCH_V31_RESEARCH"], "previous")
            self.assertEqual(result, 0)
            self.assertIsNone(stopped)
            selection_install.assert_called_once_with(runner, run)
            self.assertEqual(repaired, [runner])
            self.assertIs(cli._build_runner, build)
            self.assertIs(async_runner.apply_patch_async, old_apply)

    def test_pair_is_family_balanced_and_reports_opposing_changes(self):
        result = r.paired(cases((200, 200, 100)), cases((100, 200, 200)))
        self.assertAlmostEqual(result["delta_score"], .125)  # a=-.25, b=+.5.
        self.assertEqual((result["improved"], result["regressed"], result["tied"]), (1, 1, 1))
        self.assertEqual(result["largest_regressions"][0]["id"], "0")

    def test_wrong_inputs_and_partial_evidence_cannot_be_compared(self):
        for field, value in (("test_sha256", "other"), ("family", "other"), ("final", 90)):
            changed = cases()
            changed[0][field] = value
            if field == "final":
                changed[0]["kpi"] = .9
            with self.subTest(field=field), self.assertRaises(ValueError):
                r.paired(changed, cases())
        for changed in (cases()[:-1], cases() + [cases()[0]]):
            with self.assertRaises(ValueError):
                r.paired(changed, cases())

    def test_exact_source_only_and_island_copies(self):
        p = fixture_program()
        copy_p = {**p, "id": "island-copy"}
        self.assertIsNotNone(r.exact_duplicate("parent", [p]))
        self.assertIsNone(r.exact_duplicate("parent ", [p]))
        self.assertIsNone(r.exact_duplicate("parent", [{**p, "correct": False}]))
        self.assertEqual(len(r.memory([p, copy_p])["cards"]), 1)
        self.assertEqual(len(r.memory([p, {**copy_p, "generation": 1}])["cards"]), 2)

    def test_pair_diagnostics_never_change_fitness(self):
        parent = fixture_program()
        context = r.proposal_context([parent], "parent", 1)
        metrics = {"combined_score": .75, "manifest_sha256": "manifest", "text_feedback": "original",
                   "private": {"research_cases": cases((200, 200, 100))}, "public": {"valid_cases": 3}}
        before = copy.deepcopy(metrics)
        r.enrich_metrics(metrics, context, [parent], "manifest")
        self.assertEqual(metrics["combined_score"], before["combined_score"])
        self.assertEqual(metrics["public"], before["public"])
        self.assertAlmostEqual(metrics["research_comparisons"]["parent"]["delta_score"], -.125)
        self.assertIn("parent gen0", metrics["text_feedback"])
        parent["private_metrics"]["research_manifest_sha256"] = "old-corpus"
        with self.assertRaises(ValueError):
            r.enrich_metrics(before, context, [parent], "manifest")

    def test_memory_bounded_and_keeps_prior_separate(self):
        programs = []
        for g in range(100):
            p = fixture_program(str(g), g, str(g))
            p["metadata"]["patch_description"] = "long claim " * 1000
            programs.append(p)
        text = r.prompt_memory(r.memory(programs), {"prompt_lines": ["Previous corpus; do not transfer scores."]}, 0)
        self.assertLess(len(text), r.PROMPT_LIMIT + 120)
        self.assertIn("HISTORICAL SEARCH-v2", text)
        self.assertIn("gen0", text)

    def test_read_only_snapshot_and_deterministic_resume_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary).resolve()
            p = fixture_program()
            database(run, [(p, "parent"), ({**p, "id": "island-copy"}, "parent")])
            before = (run / "programs.sqlite").read_bytes()
            first = r.memory(r.read_programs(run))
            second = r.memory(r.read_programs(run))
            self.assertEqual(first, second)
            self.assertEqual(len(first["cards"]), 1)
            self.assertEqual(before, (run / "programs.sqlite").read_bytes())

    def test_generation_scope_and_explicit_future_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run = root / "runs/future"
            run.mkdir(parents=True)
            m = {"suite": "search-v3.1", "status": "running", "research_protocol": r.VERSION,
                 "selection_protocol": SELECTION_VERSION,
                 "service_tier": "default", "billing": "subscription", "target_generations": 5}
            (run / "run-manifest.json").write_text(json.dumps(m))
            with patch.object(hooks, "ROOT", root):
                self.assertEqual(hooks.checked_run(run, 5)[0], run)
                for budget in (None, True, 0):
                    (run / "run-manifest.json").write_text(json.dumps({**m, "target_generations": budget}))
                    with self.assertRaises(ValueError):
                        hooks.checked_run(run)
                (run / "run-manifest.json").write_text(json.dumps(m))
                with self.assertRaises(ValueError):
                    hooks.checked_run(run, 6)
                with self.assertRaises(ValueError):
                    hooks.checked_run(root / "outside")


class UpstreamRetryTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, replies):
        # Invoke the REAL installed upstream patch/retry method with synthetic
        # responses and patch application. Nothing executes the generated code.
        from shinka.core import async_runner
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary).resolve()
            gen = run / "gen_1"
            gen.mkdir()
            p = fixture_program()
            database(run, [(p, "parent")])
            queries, memories = [], []

            async def query(**kwargs):
                queries.append(kwargs)
                content = replies[len(queries) - 1]
                return types.SimpleNamespace(content=content, cost=0.0,
                                             new_msg_history=[{"role": "assistant", "content": content}],
                                             to_dict=lambda: {"content": content})

            async def apply(**kwargs):
                code = kwargs["patch_str"]
                target = Path(kwargs["patch_dir"]) / "main.cpp"
                target.write_text(code)
                return code, 1, str(target), None, "fixture diff", None

            def sample(**kwargs):
                memories.append(kwargs["meta_recommendations"])
                return "fixture system", "fixture prompt", "full"

            runner = types.SimpleNamespace(
                results_dir=str(run), lang_ext="cpp", verbose=False, llm_selection=None,
                max_proposal_jobs=1, max_evaluation_jobs=1, max_db_workers=1,
                evo_config=types.SimpleNamespace(language="cpp", max_patch_attempts=3,
                                                max_patch_resamples=1, max_novelty_attempts=1),
                prompt_sampler=types.SimpleNamespace(task_sys_msg="fixture", sample=sample),
                _get_current_system_prompt=lambda: ("fixture system", None),
                llm=types.SimpleNamespace(query=query, get_kwargs=lambda **kw: {}),
                _save_patch_attempt_async=AsyncMock(), _print_metadata_table=lambda *a: None)
            runner._run_patch_async = types.MethodType(async_runner.ShinkaEvolveRunner._run_patch_async, runner)
            hooks.install_research(runner, run, {"prompt_lines": ["Old corpus only."]})
            with patch.object(async_runner, "apply_patch_async", apply):
                with hooks.patch_application_guard(async_runner):
                    result = await runner._run_patch_async(
                        types.SimpleNamespace(id="parent", generation=0, code="parent"), [], [], 1)
                self.assertIs(async_runner.apply_patch_async, apply)
            self.assertEqual(len(queries), len(replies))
            self.assertIn("RESEARCH MEMORY", memories[0])
            self.assertIn("Exact source duplicate", queries[1]["msg"])
            self.assertEqual(len(r.read_programs(run)), 1)
            self.assertFalse((gen / "results").exists())
            if result[2]:
                context = json.loads((gen / "research-context.json").read_text())
                self.assertEqual(context["generation"], 1)
                self.assertEqual(context["parent"]["id"], "parent")
                self.assertEqual(result[1]["patch_attempt"], 2)
                self.assertEqual(result[1]["research_duplicate_retries"], 1)
            else:
                self.assertFalse((gen / "research-context.json").exists())
                self.assertEqual(result[1]["patch_attempt"], 3)
            return result

    async def test_duplicate_repaired_in_same_generation_and_parent(self):
        result = await self.exercise(["parent", "different program"])
        self.assertTrue(result[2])

    async def test_three_duplicates_exhaust_existing_budget(self):
        result = await self.exercise(["parent", "parent", "parent"])
        self.assertFalse(result[2])

    async def test_patch_hook_is_inert_outside_research_context(self):
        original = AsyncMock(return_value=("parent", 1, "file", None, "diff", None))
        module = types.SimpleNamespace(apply_patch_async=original)
        with hooks.patch_application_guard(module):
            result = await module.apply_patch_async(patch_dir="/unrelated")
        self.assertEqual(result[1], 1)
        self.assertIs(module.apply_patch_async, original)


class PublisherTests(unittest.TestCase):
    def test_staging_pair_publication_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run = root / "runs/future"
            gen = run / "gen_1"
            gen.mkdir(parents=True)
            program = gen / "main.cpp"
            program.write_text("different")
            parent = fixture_program()
            database(run, [(parent, "parent")])
            context = r.proposal_context([parent], "parent", 1)
            context["source_sha256"] = r.code_hash("different")
            r.atomic_json(gen / "research-context.json", context)
            r.atomic_json(run / "run-manifest.json", {
                "suite": "search-v3.1", "status": "running", "research_protocol": r.VERSION,
                "selection_protocol": SELECTION_VERSION,
                "service_tier": "default", "billing": "subscription", "target_generations": 2,
                "search_manifest_sha256": "manifest"})
            calls = []

            def engine(source, stage, workers):
                calls.append(stage)
                self.assertEqual(workers, 2)
                self.assertTrue(stage.is_relative_to(root / "evaluations"))
                r.atomic_json(stage / "metrics.json", {"combined_score": .75, "manifest_sha256": "manifest",
                                                       "private": {"research_cases": cases((200, 200, 100))},
                                                       "text_feedback": "original feedback"})
                r.atomic_json(stage / "correct.json", {"correct": True})

            with patch.object(publisher, "ROOT", root), patch.object(hooks, "ROOT", root), \
                    patch.object(publisher, "prepared_manifest", return_value=({}, "manifest")), \
                    patch.object(publisher, "enrich_selection"):
                publisher.evaluate_for_shinka(program, gen / "results", engine=engine)
                with self.assertRaises(ValueError):
                    publisher.evaluate_for_shinka(program, gen / "results", engine=engine)
            self.assertEqual(len(calls), 1)
            metrics = json.loads((gen / "results/metrics.json").read_text())
            self.assertEqual(metrics["combined_score"], .75)
            self.assertIn("PAIRED SEARCH EVIDENCE", metrics["text_feedback"])
            self.assertEqual(metrics["research_comparisons"]["parent"]["generation"], 0)


if __name__ == "__main__":
    unittest.main()
