"""Resume routing and generation recovery without models or real evaluations."""

import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

from shinka_evaluate import evaluate_for_shinka
from resume_search_v2 import install_recovered_job, PARENT_ID, V2, RUN_NAME


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native-shinka-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.support, self.run = self.root / "native", self.root / "run"
        self.support.mkdir()
        self.gen = self.run / "gen_4"
        self.gen.mkdir(parents=True)
        (self.gen / "main.cpp").write_text("saved candidate")
        (self.gen / "edit.diff").write_text("saved diff")
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps({"native_root": str(self.support), "run_dir": str(self.run),
                            "native_sha256": {}, "workers": 2, "suite": "search-v2",
                            "first_generation": 4, "recovered_generation": 4, "target_generations": 30}))

    def fake_engine(self, source, output, workers):
        self.assertEqual(source, self.gen / "main.cpp")
        self.assertEqual(workers, 2)
        self.assertFalse(output.is_relative_to(self.run))
        (output / "harness").mkdir(parents=True)
        (output / "harness/summary.json").write_text('{"records": []}')
        (output / "metrics.json").write_text('{"combined_score": 0.9}')
        (output / "correct.json").write_text('{"correct": true}')

    def test_publish_keeps_old_partial_results_and_prevents_overwrite(self):
        (self.gen / "results").mkdir()
        original = self.gen / "results/partial.txt"
        original.write_text("preserve")
        output = self.gen / "native-results"
        evaluate_for_shinka(self.gen / "main.cpp", output, self.plan, self.fake_engine)
        self.assertEqual(original.read_text(), "preserve")
        self.assertTrue((output / "harness/summary.json").exists())
        self.assertEqual(json.loads((output / "metrics.json").read_text())["native_workers"], 2)
        self.assertTrue(json.loads((output / "correct.json").read_text())["correct"])
        with self.assertRaises(ValueError):
            evaluate_for_shinka(self.gen / "main.cpp", output, self.plan, self.fake_engine)

    def test_reject_outside_budget_and_old_partial_output(self):
        with self.assertRaises(ValueError):
            evaluate_for_shinka(self.gen / "main.cpp", self.gen / "results", self.plan, self.fake_engine)
        gen30 = self.run / "gen_30"
        with self.assertRaises(ValueError):
            evaluate_for_shinka(gen30 / "main.cpp", gen30 / "results", self.plan, self.fake_engine)
        with self.assertRaises(ValueError):
            evaluate_for_shinka(self.gen / "main.cpp", self.root / "elsewhere/results", self.plan, self.fake_engine)

    def test_support_mutation_rejected_before_engine(self):
        source = self.support / "file.py"
        source.write_text("first")
        plan = json.loads(self.plan.read_text())
        plan["native_sha256"] = {"file.py": hashlib.sha256(source.read_bytes()).hexdigest()}
        self.plan.write_text(json.dumps(plan))
        source.write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed during run"):
            evaluate_for_shinka(self.gen / "main.cpp", self.gen / "native-results", self.plan, self.fake_engine)

    def test_recovered_generation_submitted_once_without_new_proposal(self):
        calls = []

        async def setup():
            calls.append("original_setup")

        async def submit(**kwargs):
            calls.append(kwargs)
            return "native-job", 0, 10.0, 10.0, 1

        runner = SimpleNamespace(_setup_async=setup, _submit_evaluation_job_with_slot=submit,
                                 completed_generations=4, next_generation_to_submit=4,
                                 total_api_cost=1.0, total_proposals_generated=0,
                                 assigned_generations=set(), running_jobs=[], submitted_jobs={},
                                 slot_available=asyncio.Event())
        attempt = {"llm_cost": 0.5, "patch_name": "saved", "patch_description": "saved hypothesis",
                   "num_applied": 1, "headless_prompt_path": "saved-prompt.md", "timestamp": "original"}
        install_recovered_job(runner, self.run, attempt, self.root)
        asyncio.run(runner._setup_async())
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["exec_fname"], str(self.gen / "main.cpp"))
        self.assertEqual(calls[1]["results_dir"], str(self.gen / "native-results"))
        self.assertEqual(runner.next_generation_to_submit, 5)
        self.assertEqual(runner.completed_generations, 4)
        self.assertEqual(len(runner.running_jobs), 1)
        self.assertEqual(runner.running_jobs[0].generation, 4)
        self.assertEqual(runner.running_jobs[0].parent_id, PARENT_ID)
        self.assertEqual(runner.total_api_cost, 1.5)

    def test_frozen_baseline_gate_keeps_baseline_and_active_evaluator_hashes_separate(self):
        sys.path.insert(0, str(V2.parent / "evaluator-fast"))
        from reference import load_frozen
        bridge = load_frozen("headless_bridge.py")
        original = V2 / "runs" / RUN_NAME
        with tempfile.TemporaryDirectory(prefix="native-gate-fixture-", dir=V2 / "runs") as temporary:
            run = Path(temporary)
            (run / "gen_0/results").mkdir(parents=True)
            for name in ("main.cpp", "results/metrics.json", "results/correct.json"):
                shutil.copyfile(original / "gen_0" / name, run / "gen_0" / name)
            manifest = json.loads((original / "run-manifest.json").read_text())
            manifest.update(status="running", evaluator_sha256=hashlib.sha256((V2 / "evaluator.py").read_bytes()).hexdigest(),
                            active_evaluator_sha256="separate-native-wrapper-identity")
            (run / "run-manifest.json").write_text(json.dumps(manifest))
            bridge.check_baseline(str(run))
            manifest["evaluator_sha256"] = manifest["active_evaluator_sha256"]
            (run / "run-manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, "baseline provenance"):
                bridge.check_baseline(str(run))


if __name__ == "__main__":
    unittest.main(verbosity=2)
