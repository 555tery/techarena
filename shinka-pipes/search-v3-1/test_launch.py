import json
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch

import launch
import psutil


class LaunchTests(unittest.TestCase):
    def test_real_cli_parses_frozen_yaml_without_starting_runner(self):
        import shinka.cli.run as cli
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task"
            task.mkdir()
            for name in ("shinka.yaml", "evaluate.py"):
                shutil.copy2(launch.ROOT / "task" / name, task / name)
            shutil.copy2(launch.ROOT / "seeds/strong_v2_gen17.cpp", task / "initial.cpp")
            runner = types.SimpleNamespace(run=lambda: None)
            with patch.object(cli, "_build_runner", return_value=runner) as build:
                result = cli.main(["--task-dir", str(task),
                    "--config-fname", "shinka.yaml",
                    "--results_dir", str(Path(tmp) / "run"), "--num_generations", "800"])
            self.assertEqual(result, 0)
            config = build.call_args.kwargs
            self.assertEqual(config["evo_config"].meta_llm_models,
                ["headless/codex@gpt-6.1-sol?effort=xhigh"])
            self.assertEqual(config["db_config"].num_islands, 8)
            self.assertEqual(config["args"].max_evaluation_jobs, 2)
            self.assertEqual(config["args"].max_proposal_jobs, 2)

    def test_old_supervisor_gone_but_cleanup_unconfirmed_blocks_new_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            run = root / "runs/old"
            run.mkdir(parents=True)
            (root / "night-policy.json").write_text(json.dumps({"launch_authorized": True, "target_generations": 800}))
            (root / "active-run.json").write_text(json.dumps({"run_dir": str(run), "supervisor_pid": 12345,
                                                             "supervisor_created_at": 1}))
            (run / "night-supervisor.json").write_text(json.dumps({"cleanup_confirmed": False}))
            with patch.object(launch, "ROOT", root), patch("evaluator.verify_snapshot"), \
                    patch("research_runner.check_upstream"), patch.object(psutil, "Process", side_effect=psutil.NoSuchProcess(12345)), \
                    patch.object(launch.subprocess, "Popen") as popen, self.assertRaisesRegex(RuntimeError, "unconfirmed"):
                launch.start()
            popen.assert_not_called()
            self.assertEqual(list((root / "runs").iterdir()), [run])

    def test_quota_preflight_failure_is_recorded_without_spawning(self):
        original = launch.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "task").mkdir()
            (root / "seeds").mkdir()
            for name in ("night-policy.json", "seed-plan.json", "protocol.json", "snapshot.json", "evaluator.py"):
                shutil.copy2(original / name, root / name)
            for name in ("shinka.yaml", "evaluate.py", "AGENTS.md"):
                shutil.copy2(original / "task" / name, root / "task" / name)
            shutil.copy2(original / "seeds/strong_v2_gen17.cpp", root / "seeds/strong_v2_gen17.cpp")
            with patch.object(launch, "ROOT", root), patch("evaluator.verify_snapshot"), \
                    patch("research_runner.check_upstream"), patch("night_manager.prepared_run"), \
                    patch.dict("sys.modules", {"local_runtime": types.SimpleNamespace(subscription_environment=lambda: {}, check_prerequisites=lambda env: {})}), \
                    patch("usage_guard.gate", side_effect=RuntimeError("quota unavailable")), \
                    patch.object(launch.subprocess, "Popen") as popen, self.assertRaisesRegex(RuntimeError, "quota unavailable"):
                launch.start()
            popen.assert_not_called()
            manifests = list((root / "runs").glob("*/run-manifest.json"))
            self.assertEqual(len(manifests), 1)
            self.assertEqual(json.loads(manifests[0].read_text())["status"], "preflight_failed")
            self.assertFalse((root / "active-run.json").exists())


if __name__ == "__main__":
    unittest.main()
