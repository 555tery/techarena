"""Search-v2 preparation checks only: no solver, interactor, model or held-out IO."""

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import generate


def load_local(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeneratorTests(unittest.TestCase):
    def test_128_stratified_specs_with_disjoint_search_v1_seeds(self):
        specs = generate.make_specs()
        self.assertEqual(len(specs), 128)
        self.assertEqual(Counter(s["family"] for s in specs),
                         {family: 8 for family in generate.SEARCH_FAMILIES})
        self.assertEqual(len({s["seed"] for s in specs}), 128)
        self.assertEqual(len({s["id"] for s in specs}), 128)
        old = json.loads((ROOT.parent / "task-synthetic/data/search/manifest.json").read_text())
        self.assertFalse({s["seed"] for s in specs} & {s["seed"] for s in old["cases"]})
        for family in generate.SEARCH_FAMILIES:
            cases = [s for s in specs if s["family"] == family]
            self.assertGreaterEqual(len({s["operations"] for s in cases}), 7)
            self.assertEqual(len({s["target_live"] for s in cases}), 8)
            self.assertEqual(len({s["deletion_probability"] for s in cases}), 8)

    def test_all_parameter_variants_are_deterministic_and_legal(self):
        for spec in generate.make_specs():
            small = {**spec, "operations": 1_000, "target_live": 24}
            with self.subTest(family=spec["family"], variant=spec["variant"]):
                first = generate.generate(small)
                self.assertEqual(first, generate.generate(small))
                stats = generate.audit_commands(first)
                self.assertEqual(stats["operation_count"], 1_000)
                self.assertGreater(stats["deletions"], 0)
                self.assertGreater(stats["final_live_volume"], 0)

    def test_fifo_and_lifo_remove_the_requested_live_endpoint(self):
        for family in ("fifo", "lifo"):
            spec = next(s for s in generate.make_specs() if s["family"] == family)
            commands = generate.generate({**spec, "operations": 3_000, "target_live": 24})
            live, pid = set(), 0
            for command in commands:
                if command > 0:
                    pid += 1
                    live.add(pid)
                else:
                    expected = min(live) if family == "fifo" else max(live)
                    self.assertEqual(-command, expected)
                    live.remove(-command)

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="search-v2-input-test-") as tmp:
            with self.assertRaises(FileExistsError):
                generate.prepare(Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_full_prepared_corpus_passes_independent_parser_and_hashes(self):
        path = generate.DATA
        if not path.exists():
            self.skipTest("full corpus not prepared yet")
        manifest = json.loads((path / "manifest.json").read_text())
        parser = generate.parser_module()
        self.assertEqual(len(list(path.glob("*.in"))), 128)
        self.assertEqual(manifest["generator_sha256"], generate.digest(ROOT / "generate.py"))
        hashes = set()
        for case in manifest["cases"]:
            with self.subTest(case=case["id"]):
                file = path / case["file"]
                digest = generate.digest(file)
                self.assertEqual(digest, case["sha256"])
                self.assertNotIn(digest, hashes)
                hashes.add(digest)
                parsed = parser.parse_test(file)
                self.assertEqual(parsed["operation_count"], case["operations"])
                self.assertEqual(parsed["peak_live_pipe_length_m"], case["stats"]["peak_live_volume"])
                self.assertEqual(parsed["final_occupied_length_m"], case["stats"]["final_live_volume"])


class RoutingTests(unittest.TestCase):
    def test_native_availability_probe_requires_no_baseline_or_model_call(self):
        bridge = load_local("prepared_v2_availability_bridge", "headless_bridge.py")
        environment = {"HEADLESS_BILLING": "subscription", "PATH": "/stub"}
        with patch.object(sys, "argv", ["headless_bridge.py", "--check"]), \
                patch.object(bridge, "subscription_environment", return_value=environment), \
                patch.object(bridge, "check_prerequisites") as prerequisites, \
                patch.object(bridge, "check_baseline") as baseline, \
                patch.object(bridge.os, "execve") as execute, redirect_stdout(io.StringIO()):
            self.assertEqual(bridge.main(), 0)
        prerequisites.assert_called_once_with(environment)
        baseline.assert_not_called()
        execute.assert_not_called()

    def test_future_bridge_pins_astra_xhigh_fast_without_model_call(self):
        bridge = load_local("prepared_v2_astra_bridge", "headless_bridge.py")
        arguments = ["headless_bridge.py", "codex", "--prompt-file", "/not-read.txt",
                     "--work-dir", "/not-read-run", "--allow", "read-only", "--usage",
                     "--model", "gpt-6-astra", "--reasoning-effort", "xhigh"]
        environment = {"HEADLESS_BILLING": "subscription", "PATH": "/stub"}
        with patch.object(sys, "argv", arguments), \
                patch.object(bridge, "check_baseline") as baseline, \
                patch.object(bridge, "subscription_environment", return_value=environment), \
                patch.object(bridge, "check_prerequisites"), \
                patch.object(bridge.shutil, "which", return_value="/stub/node"), \
                patch.object(bridge.os, "execve") as execute:
            self.assertEqual(bridge.main(), 0)
        baseline.assert_called_once_with("/not-read-run")
        command = execute.call_args.args[1]
        self.assertEqual(command[command.index("--model") + 1], "gpt-6-astra")
        self.assertEqual(command[command.index("--reasoning-effort") + 1], "xhigh")
        self.assertIn("--fast", command)
        self.assertEqual(command[-2:], ["--billing", "subscription"])
        for invalid in (arguments + ["--no-fast"],
                        [value.replace("gpt-6-astra", "gpt-6.1-sol") for value in arguments]):
            with patch.object(sys, "argv", invalid), \
                    patch.object(bridge, "check_baseline") as baseline, \
                    patch.object(bridge.os, "execve") as execute, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    bridge.main()
                baseline.assert_not_called()
                execute.assert_not_called()

    def test_diff_final_newline_loss_is_allowed_but_protected_code_changes_are_rejected(self):
        evaluator = load_local("prepared_v2_eof_check", "evaluator.py")
        from shinka.edit.apply_diff import apply_diff_patch
        original = ("#include <iostream>\n// EVOLVE-BLOCK-START\nint x = 1;\n"
                    "// EVOLVE-BLOCK-END\nint main() { return x; }\n")
        diff = "<<<<<<< SEARCH\nint x = 1;\n=======\nint x = 2;\n>>>>>>> REPLACE\n"
        updated, count, _, error, _, _ = apply_diff_patch(diff, original_str=original, language="cpp", verbose=False)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertFalse(updated.endswith("\n"))
        with tempfile.TemporaryDirectory(prefix="search-v2-eof-test-") as tmp:
            task = Path(tmp)
            (task / "initial.cpp").write_text(original)
            candidate = task / "candidate.cpp"
            with patch.object(evaluator, "TASK", task):
                candidate.write_text(updated)
                evaluator.check_candidate(candidate)
                candidate.write_text(updated+"\n")
                evaluator.check_candidate(candidate)
                for bad in (updated.replace("return x;", "return 0;"),
                            updated.replace("#include <iostream>", "#include <fstream>"),
                            updated.replace("// EVOLVE-BLOCK-END", "// wrong marker")):
                    candidate.write_text(bad)
                    with self.assertRaises(ValueError):
                        evaluator.check_candidate(candidate)

    def test_default_check_never_enters_experiment_branch(self):
        manager = load_local("prepared_v2_manager", "manage.py")
        with patch.object(sys, "argv", ["manage.py"]), patch.object(manager, "check", return_value={}), \
                patch.object(manager, "check_prerequisites") as prereq, \
                patch.object(manager, "subscription_environment") as environment, redirect_stdout(io.StringIO()):
            self.assertEqual(manager.main(), 0)
        prereq.assert_not_called()
        environment.assert_not_called()

    def test_run_requires_explicit_positive_budget(self):
        manager = load_local("prepared_v2_manager_guard", "manage.py")
        for args in (["--run"], ["--generations", "20"], ["--run", "--generations", "0"]):
            with self.subTest(args=args), patch.object(sys, "argv", ["manage.py", *args]), \
                    patch.object(manager, "check") as check, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    manager.main()
                check.assert_not_called()

    def test_copied_entrypoint_uses_explicit_v2_root_and_never_runs_on_import(self):
        with tempfile.TemporaryDirectory(prefix="search-v2-entrypoint-test-") as tmp:
            copied = Path(tmp) / "evaluate.py"
            copied.write_text((ROOT / "task/evaluate.py").read_text())
            spec = importlib.util.spec_from_file_location("copied_v2_entry", copied)
            module = importlib.util.module_from_spec(spec)
            with patch.dict("os.environ", {"PIPES_SEARCH_V2_ROOT": str(ROOT)}):
                spec.loader.exec_module(module)
            self.assertEqual(module.support, ROOT)
            with patch.object(module, "evaluate") as evaluate, \
                    patch.object(sys, "argv", ["evaluate.py", "--program_path", "/not-run.cpp", "--results_dir", "/not-created"]):
                self.assertEqual(module.main(), 0)
                evaluate.assert_called_once_with(Path("/not-run.cpp"), Path("/not-created"))

    def test_model_gate_accepts_only_complete_v2_baseline(self):
        bridge = load_local("prepared_v2_bridge", "headless_bridge.py")
        with tempfile.TemporaryDirectory(prefix="search-v2-gate-test-") as tmp:
            root = Path(tmp)
            run = root / "runs/test"
            results = run / "gen_0/results"
            results.mkdir(parents=True)
            (root / "protocol.json").write_text(json.dumps({"manifest_sha256": "v2"}))
            (results / "correct.json").write_text(json.dumps({"correct": True}))
            (root / "task").mkdir()
            for file in (root / "task/initial.cpp", run / "gen_0/main.cpp"):
                file.write_text("baseline")
            (root / "evaluator.py").write_text("evaluator")
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            source_hash, evaluator_hash = sha(root / "task/initial.cpp"), sha(root / "evaluator.py")
            (root / "snapshot.json").write_text(json.dumps({"files": {"task/initial.cpp": source_hash, "evaluator.py": evaluator_hash}}))
            snapshot_hash = sha(root / "snapshot.json")
            provenance = {"status": "running", "suite": "search-v2", "billing": "subscription",
                          "search_manifest_sha256": "v2", "snapshot_sha256": snapshot_hash,
                          "source_sha256": source_hash, "evaluator_sha256": evaluator_hash}
            (run / "run-manifest.json").write_text(json.dumps(provenance))
            metric = {"suite": "search", "corpus_version": "search-v2", "public": {"valid_cases": 128},
                      "manifest_sha256": "v2", "program_sha256": source_hash,
                      "evaluator_sha256": evaluator_hash, "snapshot_sha256": snapshot_hash}
            with patch.object(bridge, "ROOT", root):
                (results / "metrics.json").write_text(json.dumps(metric))
                bridge.check_baseline(str(run))
                for key, value in (("corpus_version", "synthetic-v1"), ("manifest_sha256", "wrong"),
                                   ("public", {"valid_cases": 32}), ("suite", "other")):
                    (results / "metrics.json").write_text(json.dumps({**metric, key: value}))
                    with self.assertRaises(RuntimeError):
                        bridge.check_baseline(str(run))
                (results / "metrics.json").write_text(json.dumps(metric))
                for key in ("program_sha256", "evaluator_sha256", "snapshot_sha256"):
                    (results / "metrics.json").write_text(json.dumps({**metric, key: "stale"}))
                    with self.assertRaises(RuntimeError):
                        bridge.check_baseline(str(run))
                (results / "metrics.json").write_text(json.dumps(metric))
                (run / "run-manifest.json").write_text(json.dumps({**provenance, "source_sha256": "wrong"}))
                with self.assertRaises(RuntimeError):
                    bridge.check_baseline(str(run))
                with self.assertRaises(RuntimeError):
                    bridge.check_baseline(str(root / "unrelated"))

    def test_check_reads_no_held_out_files_and_no_subprocesses(self):
        manager = load_local("prepared_v2_manager_io", "manage.py")
        original_text, original_bytes = Path.read_text, Path.read_bytes
        def allowed(path):
            name = str(path).lower()
            if any(part in name for part in ("validation-v1", "/data/open/", "open15")):
                raise AssertionError("held-out file access: " + str(path))
        def read_text(path, *args, **kwargs):
            allowed(path)
            return original_text(path, *args, **kwargs)
        def read_bytes(path, *args, **kwargs):
            allowed(path)
            return original_bytes(path, *args, **kwargs)
        with patch.object(Path, "read_text", read_text), patch.object(Path, "read_bytes", read_bytes), \
                patch("subprocess.run", side_effect=AssertionError("subprocess execution")), \
                patch("subprocess.Popen", side_effect=AssertionError("subprocess execution")):
            report = manager.check()
        self.assertEqual(report["cases"], 128)
        self.assertEqual(report["candidate_evaluations"], 0)

    def test_fitness_keeps_equal_family_weight_and_rejects_missing_cases(self):
        evaluator = load_local("prepared_v2_evaluator", "evaluator.py")
        manifest = {"split": "search", "version": "search-v2", "families": ["A", "B"], "cases": []}
        records = []
        for name, family, trench in (("a1", "A", 100), ("a2", "A", 200), ("b1", "B", 400)):
            manifest["cases"].append({"file": name+".in", "id": name, "family": family, "sha256": name,
                                      "stats": {"volume_lower_bound": 100, "final_live_volume": 40}})
            records.append({"test_file": str(evaluator.SEARCH / (name+".in")), "test_sha256": name,
                            "status": "ok", "solver_cpu_total_s": 0.1, "solver_peak_rss_mb": 10,
                            "trench_length_m": trench, "minimum_trench_lower_bound_m": 100,
                            "final_occupied_length_m": 40, "kpi": 40/trench})
        metrics, correct = evaluator.aggregate_report({"records": records}, manifest, evaluator.SEARCH, 0)
        self.assertTrue(correct)
        self.assertAlmostEqual(metrics["combined_score"], (0.75+0.25)/2)
        with self.assertRaises(ValueError):
            evaluator.aggregate_report({"records": records[:-1]}, manifest, evaluator.SEARCH, 0)


if __name__ == "__main__":
    unittest.main()
