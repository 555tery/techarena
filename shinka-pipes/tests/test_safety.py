"""Offline checks of auth and launch boundaries; no candidate/model execution."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from local_runtime import subscription_environment


class SafetyChecks(unittest.TestCase):
    def test_copied_evaluator_imports_outside_task_directory(self):
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "evaluate.py"
            shutil.copyfile(ROOT / "task-synthetic/evaluate.py", copied)
            env = subscription_environment()
            result = subprocess.run([
                sys.executable, "-I", "-c",
                'import runpy,sys; runpy.run_path(sys.argv[1],run_name="import_only")', str(copied),
            ], cwd=temporary, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_model_call_requires_successful_initial_search_baseline(self):
        import json
        from headless_bridge import check_initial_baseline
        snapshot = json.loads((ROOT / "task-synthetic/snapshot.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError):
                check_initial_baseline(temporary)
            results = Path(temporary) / "gen_0/results"
            results.mkdir(parents=True)
            (results / "correct.json").write_text('{"correct": true}')
            (results / "metrics.json").write_text(json.dumps({
                "suite": "search", "public": {"valid_cases": 32},
                "manifest_sha256": snapshot["snapshot_sha256"]["data/search/manifest.json"],
            }))
            check_initial_baseline(temporary)
            (results / "correct.json").write_text('{"correct": false}')
            with self.assertRaises(RuntimeError):
                check_initial_baseline(temporary)

    def test_subscription_mode_overrides_environment_and_removes_api_keys(self):
        with patch.dict(os.environ, {
            "CODEX_HOME": str(ROOT / ".missing-config-for-unit-check"),
            "OPENAI_API_KEY": "inert-test-value", "CODEX_API_KEY": "inert-test-value",
            "HEADLESS_BILLING": "api", "OPENAI_BASE_URL": "https://invalid.example",
        }):
            env = subscription_environment()
        self.assertEqual(env["HEADLESS_BILLING"], "subscription")
        self.assertEqual(env["PYTHON_DOTENV_DISABLED"], "1")
        self.assertFalse({"OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"} & env.keys())

    def test_launch_requires_explicit_positive_budget(self):
        for args in (["--run"], ["--generations", "1"], ["--run", "--generations", "0"]):
            result = subprocess.run([str(ROOT / "run.sh"), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)

    def test_explicit_chat_model_overrides_native_cli_default(self):
        from manage import load_config
        from shinka.llm.providers.headless import _build_headless_command, parse_headless_model

        with tempfile.TemporaryDirectory() as config_dir:
            (Path(config_dir) / "config.toml").write_text('model = "gpt-6-luna"\n')
            with patch.dict(os.environ, {"CODEX_HOME": config_dir, "CODEX_MODEL": "gpt-6-luna"}):
                env = subscription_environment()
        self.assertNotIn("CODEX_MODEL", env)
        config, _ = load_config()
        model = parse_headless_model(config["evo"]["llm_models"][0])
        command = _build_headless_command(model=model, prompt_path=ROOT / ".configuration-probe",
                                          work_dir=str(ROOT))
        self.assertEqual(command[command.index("--model") + 1], "gpt-6.1-sol")
        self.assertEqual(command[command.index("--reasoning-effort") + 1], "xhigh")

    def test_bridge_rejects_paid_billing_and_docker_before_any_agent_call(self):
        base = [str(ROOT / "headless.sh"), "codex", "--prompt-file", "/nonexistent",
                "--work-dir", str(ROOT), "--allow", "read-only"]
        for extra in (["--billing", "api"], ["--docker"]):
            result = subprocess.run([*base, *extra], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)

    def test_headless_subscription_route_rejects_paid_fallback(self):
        script = """
import assert from 'node:assert/strict';
import {prepareBillingAttempt} from './runtime/node_modules/@roberttlange/headless/dist/billing.js';
assert.throws(() => prepareBillingAttempt('codex', {}, {}, 'subscription', 'openai-api'),
              /subscription billing cannot switch/);
const result = prepareBillingAttempt('codex', {}, {
  ...process.env, OPENAI_API_KEY: 'inert-test-value', CODEX_API_KEY: 'inert-test-value',
  OPENAI_BASE_URL: 'https://invalid.example'
}, 'subscription');
assert.equal(result.route, 'subscription');
for (const key of ['OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL']) {
  assert.equal(result.env[key], undefined);
}
"""
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
