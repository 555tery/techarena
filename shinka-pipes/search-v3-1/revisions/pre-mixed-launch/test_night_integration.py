"""Night adapter wiring and publisher budgets using fake clients/results only."""

import asyncio
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch

import research as r
import research_runner as hooks
import shinka_evaluate as publisher
from selection import VERSION as SELECTION_VERSION
from night_runtime import NightState


class NightIntegrationTests(unittest.TestCase):
    def test_supervised_runner_installs_night_before_selection_and_shares_meta_stop(self):
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
            (root / "night-policy.json").write_bytes((hooks.ROOT / "night-policy.json").read_bytes())
            policy = json.loads((root / "night-policy.json").read_text())
            r.atomic_json(root / "research-prior.json", {"prompt_lines": []})
            r.atomic_json(run / "run-manifest.json", {
                "suite": "search-v3.1", "status": "running", "research_protocol": r.VERSION,
                "selection_protocol": SELECTION_VERSION,
                "service_tier": "default", "billing": "subscription", "target_generations": 800,
                "source_sha256": hooks.digest(task / "initial.cpp"),
                "snapshot_sha256": hooks.digest(root / "snapshot.json"),
                "night_protocol": "overnight-v1", "launch_authorized": True,
                "night_policy_sha256": hooks.digest(root / "night-policy.json"),
                "model": policy["model"], "reasoning_effort": "xhigh"})
            runner = types.SimpleNamespace(max_proposal_jobs=2, max_evaluation_jobs=2, max_db_workers=1,
                evo_config=types.SimpleNamespace(max_patch_attempts=3, max_patch_resamples=1, max_novelty_attempts=1),
                should_stop=asyncio.Event(), completed_generations=1, _run_patch_async=AsyncMock())
            build = lambda **kwargs: runner
            cli = types.SimpleNamespace(_build_runner=build)
            installed = []
            def install_night(item, directory, configuration):
                installed.append("night")
                item._pipes_night_state = NightState(directory, configuration)
            def install_selection(item, directory):
                self.assertTrue(item._pipes_research_installed)
                installed.append("selection")
            def install_meta(item, should_start_meta):
                installed.append("meta")
                self.assertTrue(should_start_meta())
                item._pipes_night_state.request_stop("fixture_stop")
                self.assertFalse(should_start_meta())
            def main(argv):
                self.assertEqual(argv[argv.index("--num_generations") + 1], "800")
                cli._build_runner()
                self.assertEqual(os.environ["PIPES_SEARCH_V31_NIGHT"], "overnight-v1")
                return 0
            cli.main = main
            with patch.object(hooks, "ROOT", root), patch.object(hooks, "check_upstream"), \
                    patch("evaluator.verify_snapshot"), patch.object(hooks, "frozen_v2"), \
                    patch.object(hooks, "install_selection", side_effect=install_selection), \
                    patch("night_runtime.install_night_runtime", side_effect=install_night), \
                    patch("meta_runtime.install_meta", side_effect=install_meta), \
                    patch.dict(os.environ, {"PIPES_SEARCH_V31_SUPERVISOR": str(os.getpid()),
                                            "PIPES_SEARCH_V31_NIGHT": "previous"}):
                result, stopped = hooks.run_with_research(cli, task=task, run=run, generations=800)
                self.assertEqual(os.environ["PIPES_SEARCH_V31_NIGHT"], "previous")
            self.assertEqual(installed, ["night", "selection", "meta"])
            self.assertEqual(stopped["reason"], "fixture_stop")
            self.assertEqual(result, 0)
            self.assertIs(cli._build_runner, build)

    def test_evaluator_accepts_reserved_id_above_target_and_rejects_unreserved_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "night-policy.json").write_bytes((hooks.ROOT / "night-policy.json").read_bytes())
            policy = json.loads((root / "night-policy.json").read_text())
            run = root / "runs/future"
            manifest = {"target_generations": 800, "night_protocol": "overnight-v1"}
            gen = run / "gen_801"
            gen.mkdir(parents=True)
            program = gen / "main.cpp"
            program.write_text("fixture code")
            r.atomic_json(gen / "research-context.json", {
                "version": r.VERSION, "generation": 801, "source_sha256": hooks.digest(program)})
            state = NightState(run, policy)
            def engine(source, stage, workers):
                r.atomic_json(stage / "metrics.json", {"combined_score": 0})
                r.atomic_json(stage / "correct.json", {"correct": False})
            with patch.object(publisher, "ROOT", root), \
                    patch.object(publisher, "checked_run", return_value=(run, manifest)):
                with self.assertRaisesRegex(ValueError, "reserved proposal ID"):
                    publisher.evaluate_for_shinka(program, gen / "results", engine=engine)
                self.assertFalse((gen / "results").exists())
                state.reserve_proposals([801])
                publisher.evaluate_for_shinka(program, gen / "results", engine=engine)
            self.assertEqual(json.loads((gen / "results/native-evaluation.json").read_text())["status"], "complete")


if __name__ == "__main__":
    unittest.main()
