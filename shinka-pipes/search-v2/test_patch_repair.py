"""Native patch-feedback flow with scripted responses, no models or evaluations."""

import asyncio
import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from patch_repair import install_stop_on_failed_proposal, run_with_patch_repair
from shinka.core.async_runner import ShinkaEvolveRunner
from shinka.core.config import EvolutionConfig
from shinka.database import Program
from shinka.llm.providers.headless import _query_result, _render_prompt

SOURCE = ("#include <iostream>\n// EVOLVE-BLOCK-START\n"
          "int left = 1;\n\nint right = 2;\n"
          "// EVOLVE-BLOCK-END\nint main() { return 0; }\n")


def response(search, replacement):
    return ("<NAME>toy_change</NAME><DESCRIPTION>text-only fixture</DESCRIPTION>\n"
            "<DIFF>\n<<<<<<< SEARCH\n" + search + "\n=======\n" + replacement
            + "\n>>>>>>> REPLACE\n</DIFF>")


BAD = response("int left = 1;\nint right = 2;", "int left = 9;\nint right = 2;")
GOOD = response("int left = 1;\n\nint right = 2;", "int left = 9;\n\nint right = 2;")


class ScriptedLLM:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def get_kwargs(self, **kwargs):
        return {"model_name": "headless/codex@gpt-6-astra?effort=xhigh"}

    async def query(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        return _query_result(
            content=next(self.replies), usage={"cost": 0.01},
            model="headless/codex@gpt-6-astra?effort=xhigh",
            msg=kwargs["msg"], system_msg=kwargs["system_msg"],
            msg_history=kwargs["msg_history"], kwargs={}, model_posteriors=None,
        )


def toy_runner(directory, replies):
    parent = Program(id="toy-parent", code=SOURCE, language="cpp", generation=0)
    runner = types.SimpleNamespace(
        evo_config=EvolutionConfig(language="cpp", max_patch_attempts=3,
                                   max_patch_resamples=1, max_novelty_attempts=1),
        db_config=types.SimpleNamespace(parent_selection_strategy=""),
        results_dir=str(directory), lang_ext="cpp", verbose=False,
        prompt_sampler=types.SimpleNamespace(
            task_sys_msg="toy instructions",
            sample=Mock(return_value=("toy instructions", "Edit this parent:\n" + SOURCE, "diff"))),
        llm=ScriptedLLM(replies), llm_selection=None, novelty_judge=None,
        async_db=types.SimpleNamespace(sample_with_fix_mode_async=AsyncMock(
            return_value=(parent, [], [], False))),
        _get_current_system_prompt=lambda: (None, None),
        _print_metadata_table=Mock(),
        _get_code_embedding_async=AsyncMock(return_value=(None, 0.0)),
        _submit_evaluation_job_with_slot=AsyncMock(
            return_value=("mock-evaluation", 0, 1.0, 1.0, 0)),
        _record_terminal_failed_proposal=AsyncMock(),
        _persist_failed_generation=AsyncMock(),
        _update_avg_proposal_cost=Mock(),
        running_jobs=[], submitted_jobs={}, total_api_cost=0.0,
        completed_generations=1, next_generation_to_submit=8,
        should_stop=asyncio.Event(), slot_available=asyncio.Event(),
        finalization_complete=asyncio.Event(),
    )
    runner._run_patch_async = types.MethodType(ShinkaEvolveRunner._run_patch_async, runner)
    runner._save_patch_attempt_async = types.MethodType(
        ShinkaEvolveRunner._save_patch_attempt_async, runner)
    install_stop_on_failed_proposal(runner)
    return runner


async def propose(runner):
    return await ShinkaEvolveRunner._generate_evolved_proposal(
        runner, generation=7, task_id="toy-proposal",
        exec_fname=str(Path(runner.results_dir) / "gen_7/main.cpp"),
        results_dir=str(Path(runner.results_dir) / "gen_7/results"),
        meta_recs=None, meta_summary=None, meta_scratch=None,
        proposal_started_at=1.0, sampling_worker_id=0, active_proposals_at_start=1,
    )


class PatchRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_apply_error_is_repaired_in_same_generation_before_one_submission(self):
        with tempfile.TemporaryDirectory(prefix="shinka-text-repair-") as temporary:
            runner = toy_runner(Path(temporary), [BAD, GOOD])
            with patch.object(subprocess, "Popen", side_effect=AssertionError("No subprocess")), \
                    patch.object(asyncio, "create_subprocess_exec", side_effect=AssertionError("No compiler")):
                job = await propose(runner)
            self.assertEqual(job.generation, 7)
            self.assertEqual(len(runner.llm.calls), 2)
            feedback = runner.llm.calls[1]
            self.assertIn("SEARCH text not found", feedback["msg"])
            rendered = _render_prompt(msg=feedback["msg"], system_msg=feedback["system_msg"],
                                      msg_history=feedback["msg_history"])
            self.assertIn(SOURCE, rendered.replace("\\n", "\n"))
            self.assertIn("int left = 9", rendered)
            self.assertEqual(runner.async_db.sample_with_fix_mode_async.await_count, 1)
            runner._submit_evaluation_job_with_slot.assert_awaited_once()
            runner._persist_failed_generation.assert_not_awaited()
            self.assertFalse(runner.should_stop.is_set())
            self.assertEqual(runner.completed_generations, 1)
            self.assertEqual(runner.next_generation_to_submit, 8)
            self.assertEqual({p.name for p in Path(temporary).glob("gen_*")}, {"gen_7"})
            attempts = Path(temporary) / "gen_7/attempts/novelty_1/resample_1"
            self.assertFalse(json.loads((attempts / "patch_1/metadata.json").read_text())["success"])
            self.assertTrue(json.loads((attempts / "patch_2/metadata.json").read_text())["success"])
            self.assertIn("int left = 9;", (Path(temporary) / "gen_7/main.cpp").read_text())
            self.assertEqual(job.meta_patch_data["patch_attempt"], 2)
            self.assertAlmostEqual(job.meta_patch_data["api_costs"], 0.02)

    async def test_second_correction_can_succeed_on_third_attempt(self):
        with tempfile.TemporaryDirectory(prefix="shinka-text-repair-") as temporary:
            runner = toy_runner(Path(temporary), [BAD, BAD, GOOD])
            job = await propose(runner)
            self.assertEqual(job.meta_patch_data["patch_attempt"], 3)
            self.assertEqual(len(runner.llm.calls), 3)
            self.assertEqual(len(runner.llm.calls[2]["msg_history"]), 4)
            runner._submit_evaluation_job_with_slot.assert_awaited_once()
            self.assertFalse(runner.should_stop.is_set())

    async def test_exhaustion_stops_without_submission_or_consuming_program_slot(self):
        with tempfile.TemporaryDirectory(prefix="shinka-text-repair-") as temporary:
            runner = toy_runner(Path(temporary), [BAD, BAD, BAD, GOOD])
            job = await propose(runner)
            self.assertIsNone(job)
            self.assertEqual(len(runner.llm.calls), 3)
            runner._submit_evaluation_job_with_slot.assert_not_awaited()
            runner._persist_failed_generation.assert_not_awaited()
            self.assertEqual(runner.completed_generations, 1)
            self.assertEqual(runner.next_generation_to_submit, 8)
            self.assertEqual(runner._search_v2_repair_stop["generation"], 7)
            self.assertEqual(runner._search_v2_repair_stop["patch_attempts"], 3)
            self.assertTrue(runner.should_stop.is_set())
            self.assertTrue(runner.finalization_complete.is_set())
            runner._start_proposals = AsyncMock()
            await ShinkaEvolveRunner._proposal_coordinator_task(runner)
            runner._start_proposals.assert_not_awaited()
            self.assertAlmostEqual(runner._search_v2_repair_stop["proposal_cost_estimate"], 0.03)
            self.assertFalse((Path(temporary) / "gen_7/main.cpp").exists())


class InvocationTests(unittest.TestCase):
    def test_manager_reports_exhaustion_as_early_stop_without_real_launch(self):
        spec = importlib.util.spec_from_file_location("repair_manager_test", ROOT / "manage.py")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        with tempfile.TemporaryDirectory(prefix="shinka-repair-manager-") as temporary:
            base = Path(temporary)
            task = base / "task"
            (task / "data/search").mkdir(parents=True)
            for path in (task / "data/search/manifest.json", task / "initial.cpp",
                         base / "evaluator.py", base / "snapshot.json"):
                path.write_text("toy")
            report = {"model": "headless/codex@gpt-6-astra?effort=xhigh",
                      "reasoning_effort": "xhigh", "service_tier": "fast", "patch_repair": {},
                      "seed_origin": {"generation": 2, "sha256": "toy-source"}}
            stopped = {"generation": 7, "patch_attempts": 3, "failed_program_persisted": False}
            with patch.object(manager, "ROOT", base), patch.object(manager, "TASK", task), \
                    patch.object(manager, "check", return_value=report), \
                    patch.object(manager, "subscription_environment", return_value={}), \
                    patch.object(manager, "check_prerequisites"), \
                    patch.object(manager, "run_with_patch_repair", return_value=(0, stopped)), \
                    patch.object(sys, "argv", ["manage.py", "--run", "--generations", "9"]), \
                    patch.dict("os.environ", {}, clear=False), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(manager.main(), 2)
            folders = list((base / "runs").iterdir())
            self.assertEqual(len(folders), 1)
            manifest = json.loads((folders[0] / "run-manifest.json").read_text())
            self.assertEqual(manifest["status"], "needs_patch_repair")
            self.assertEqual(manifest["stopped_generation"], 7)
            self.assertEqual(manifest["target_generations"], 9)
            self.assertEqual(manifest["seed_origin"], report["seed_origin"])
            self.assertEqual(json.loads((folders[0] / "patch-repair-exhausted.json").read_text()), stopped)

    def test_wrapper_is_installed_only_for_this_invocation_and_builder_is_restored(self):
        recorder = AsyncMock()
        runner = types.SimpleNamespace(_record_terminal_failed_proposal=recorder)
        original = Mock(return_value=runner)
        cli = types.SimpleNamespace(_build_runner=original)

        def main(arguments):
            built = cli._build_runner()
            self.assertTrue(built._search_v2_repair_installed)
            built._search_v2_repair_stop = {"generation": 7}
            return 0

        cli.main = main
        result, stopped = run_with_patch_repair(cli, task="/toy-task", run="/toy-run", generations=9)
        self.assertEqual(result, 0)
        self.assertEqual(stopped["generation"], 7)
        self.assertIs(cli._build_runner, original)
        cli.main = Mock(side_effect=RuntimeError("toy failure"))
        with self.assertRaises(RuntimeError):
            run_with_patch_repair(cli, task="/toy-task", run="/toy-run", generations=9)
        self.assertIs(cli._build_runner, original)
