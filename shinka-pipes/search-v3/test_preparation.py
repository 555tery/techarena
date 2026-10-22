"""Synthetic records and structural inputs only: never execute a real candidate."""

from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fitness import aggregate_report
import evaluator
from generate import MAIN, STRESS, generate_case, make_specs, select_prefix
from support import ROOT
import headless_bridge


def fixture():
    cases, records = [], []
    for i, (family, final, trench) in enumerate((("a", 95, 200), ("b", 100, 100))):
        name, sha = f"fixture-{i}.in", str(i) * 64
        cases.append({"id": name[:-3], "file": name, "family": family, "sha256": sha, "operations": 10,
                      "stats": {"volume_lower_bound": 100, "final_live_volume": final}})
        records.append({"test_file": str(MAIN / name), "test_sha256": sha, "status": "ok",
                        "solver_cpu_total_s": .1, "solver_peak_rss_mb": 10., "trench_length_m": trench,
                        "kpi": final / trench, "minimum_trench_lower_bound_m": 100,
                        "final_occupied_length_m": final, "occupied_length_m": final,
                        "operation_count": 10, "judge_commands_seen_including_final_zero": 11,
                        "official_weight": 1., "weight": 1., "weighted_score": final / trench})
    manifest = {"version": "search-v3", "split": "search", "role": "fitness", "cases": cases,
                "case_count": 2, "families": ["a", "b"], "cases_per_family": 1, "weight_per_case": 1}
    return {"records": records}, manifest


class FitnessTests(unittest.TestCase):
    def test_hand_computed_raw_kpi_and_diagnostics(self):
        summary, manifest = fixture()
        metrics, correct = aggregate_report(summary, manifest, MAIN, 0)
        self.assertTrue(correct)
        self.assertAlmostEqual(metrics["combined_score"], (.475 + 1.) / 2)
        self.assertNotEqual(metrics["combined_score"], .75)  # B/T would give .75.
        self.assertEqual(metrics["public"]["mean_overrun"], .5)
        self.assertEqual(metrics["family_scores"], {"a": .475, "b": 1.})
        self.assertEqual(metrics["diagnostics"]["worst_16"][0]["id"], "fixture-0")

    def test_parallel_order_and_cpu_do_not_change_fitness(self):
        summary, manifest = fixture()
        first = aggregate_report(summary, manifest, MAIN, 0)[0]
        summary["records"].reverse()
        summary["records"][0]["solver_cpu_total_s"] = 4.9
        other = aggregate_report(summary, manifest, MAIN, 0)[0]
        self.assertEqual(first["combined_score"], other["combined_score"])
        self.assertNotEqual(first["solver_cpu_total_s"], other["solver_cpu_total_s"])

    def test_stress_cannot_become_fitness(self):
        summary, manifest = fixture()
        for field, value in (("split", "stress"), ("role", "diagnostic_only"), ("version", "search-v2")):
            changed = copy.deepcopy(manifest)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                aggregate_report(summary, changed, MAIN, 0)

    def test_invalid_records_never_receive_fitness(self):
        mutations = [("status", "invalid"), ("solver_cpu_total_s", 5.), ("solver_cpu_total_s", -1.),
                     ("solver_peak_rss_mb", 256.), ("solver_peak_rss_mb", float("nan")),
                     ("kpi", float("nan")), ("kpi", .9), ("weighted_score", float("inf")),
                     ("trench_length_m", 101), ("trench_length_m", 80), ("occupied_length_m", 94),
                     ("final_occupied_length_m", 94), ("minimum_trench_lower_bound_m", 80),
                     ("test_sha256", "wrong"), ("operation_count", 9),
                     ("judge_commands_seen_including_final_zero", 10), ("official_weight", 2.),
                     ("solver_cpu_limit_exceeded", True), ("solver_memory_limit_exceeded", True)]
        for key, value in mutations:
            summary, manifest = fixture()
            summary["records"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                aggregate_report(summary, manifest, MAIN, 0)

    def test_coverage_returncode_and_paths(self):
        for mutation in ("missing", "duplicate", "outside", "returncode"):
            summary, manifest = fixture()
            if mutation == "missing":
                summary["records"].pop()
            elif mutation == "duplicate":
                summary["records"][1] = summary["records"][0]
            elif mutation == "outside":
                summary["records"][0]["test_file"] = str(STRESS / "fixture-0.in")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                aggregate_report(summary, manifest, MAIN, 1 if mutation == "returncode" else 0)


class PreparationTests(unittest.TestCase):
    def test_stratification_and_disjoint_seed_namespaces(self):
        main, stress = make_specs("search"), make_specs("stress")
        self.assertEqual(len(main), 128)
        self.assertEqual(len(stress), 32)
        self.assertEqual(len({s["design_seed"] for s in main + stress}), 160)
        for family in {s["family"] for s in main}:
            rows = [s for s in main if s["family"] == family]
            self.assertEqual({s["variant"] for s in rows}, set(range(8)))
        with self.assertRaises(ValueError):
            make_specs("validation")

    def test_prefix_does_not_accept_a_drain_or_unworked_fill(self):
        self.assertIsNone(select_prefix([20] * 200))  # No churn.
        self.assertIsNone(select_prefix([20] * 100 + [-i for i in range(1, 100)]))
        commands = [20, 20]
        for pid in range(3, 103):
            commands.extend([20, -(pid - 2)])
        endpoint = select_prefix(commands)
        self.assertIsNotNone(endpoint)
        self.assertEqual(commands[endpoint - 1], 20)

    def test_prepared_inputs_reparse_without_processes_or_heldouts(self):
        original_text, original_bytes = Path.read_text, Path.read_bytes

        def check_path(path):
            text = str(path).lower()
            if "validation-v1" in text or "/data/open/" in text or "open15" in text:
                raise AssertionError(f"forbidden held-out read: {path}")

        def read_text(path, *args, **kwargs):
            check_path(path)
            return original_text(path, *args, **kwargs)

        def read_bytes(path, *args, **kwargs):
            check_path(path)
            return original_bytes(path, *args, **kwargs)

        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, "read_text", read_text))
            stack.enter_context(patch.object(Path, "read_bytes", read_bytes))
            stack.enter_context(patch.object(subprocess, "run", side_effect=AssertionError("process forbidden")))
            stack.enter_context(patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")))
            from check import check_preparation
            result = check_preparation()
        self.assertEqual(result["cases_checked"], 160)
        self.assertEqual(result["solvers_executed"], 0)

    def test_evaluation_route_does_not_even_read_stress(self):
        original_text, original_bytes = Path.read_text, Path.read_bytes

        def guard(method):
            def read(path, *args, **kwargs):
                if "/stress/" in str(path):
                    raise AssertionError("stress reached the fitness route")
                return method(path, *args, **kwargs)
            return read

        with patch.object(Path, "read_text", guard(original_text)), patch.object(Path, "read_bytes", guard(original_bytes)):
            self.assertEqual(evaluator.load_search()["case_count"], 128)

    def test_regenerate_one_full_input_per_family_and_stress(self):
        # Reproduce hashes at real horizons, without executing any allocator.
        main = json.loads((MAIN / "manifest.json").read_text())
        stress = json.loads((STRESS / "manifest.json").read_text())
        indexed = {c["id"]: c for suite in (main, stress) for c in suite["cases"]}
        selected = [s for s in make_specs("search") if s["variant"] == 0] + make_specs("stress")[:2]
        for spec in selected:
            commands, actual, stats = generate_case(spec)
            encoded = ("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n").encode("ascii")
            saved = indexed[spec["id"]]
            with self.subTest(case=spec["id"]):
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), saved["sha256"])
                self.assertEqual(stats, saved["stats"])
                self.assertEqual(actual["termination"], saved["termination"])


class AdapterTests(unittest.TestCase):
    def test_future_adapter_with_fake_subprocesses_uses_only_main(self):
        summary, manifest = fixture()
        with tempfile.TemporaryDirectory(prefix="v3-adapter-unit-") as temporary:
            root = Path(temporary).resolve()
            program, runner = root / "fake-source.txt", root / "fake-native.txt"
            program.write_text("unit fixture, never compiled")
            runner.write_text("unit fixture, never executed")
            (root / "snapshot.json").write_text("{}")
            (root / "evaluator.py").write_text("unit fixture evaluator identity")
            out = root / "evaluations/case"
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                if "--tests" in command:
                    self.assertEqual(command[command.index("--tests") + 1], str(MAIN))
                    for flag, value in (("--workers", "2"), ("--cpu-limit", "5"), ("--memory-limit-mb", "256")):
                        self.assertEqual(command[command.index(flag) + 1], value)
                    (out / "harness").mkdir(parents=True)
                    (out / "harness/summary.json").write_text(json.dumps(summary))
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            checker = SimpleNamespace(check_candidate=lambda path: None)
            with patch.object(evaluator, "ROOT", root), patch.object(evaluator, "load_search", return_value=manifest), \
                    patch.object(evaluator, "frozen_v2", return_value=checker), \
                    patch.object(evaluator, "native_cache", return_value=(runner, "fake-cache-key")), \
                    patch.object(evaluator.shutil, "which", return_value="/fake/g++"), \
                    patch.object(subprocess, "run", side_effect=fake_run):
                self.assertTrue(evaluator.evaluate(program, out))
                self.assertEqual(len(calls), 2)
                metrics = json.loads((out / "metrics.json").read_text())
                self.assertAlmostEqual(metrics["combined_score"], .7375)
                self.assertFalse(metrics["stress_evaluated"])
                with self.assertRaises(ValueError):
                    evaluator.evaluate(program, out)  # Never overwrite a result.
                self.assertEqual(len(calls), 2)

    def test_model_gate_requires_new_budget_and_matching_v3_baseline(self):
        from support import digest
        with tempfile.TemporaryDirectory(prefix="v3-gate-unit-") as temporary:
            root = Path(temporary).resolve()
            run = root / "runs/unit-fixture"
            results = run / "gen_0/results"
            results.mkdir(parents=True)
            (run / "gen_0/main.cpp").write_text("unit fixture, never compiled")
            (root / "evaluator.py").write_text("unit evaluator")
            (root / "snapshot.json").write_text("{}")
            (root / "protocol.json").write_text(json.dumps({"manifest_sha256": {"search": "main-sha"}}))
            (results / "correct.json").write_text('{"correct": true}')
            ids = {"manifest_sha256": "main-sha", "program_sha256": digest(run / "gen_0/main.cpp"),
                   "snapshot_sha256": digest(root / "snapshot.json"), "evaluator_sha256": digest(root / "evaluator.py")}
            metrics = {**ids, "suite": "search", "corpus_version": "search-v3", "public": {"valid_cases": 128},
                       "native_workers": 2, "stress_evaluated": False}
            run_manifest = {"status": "running", "suite": "search-v3", "billing": "subscription", "target_generations": 2,
                            "search_manifest_sha256": "main-sha", "source_sha256": ids["program_sha256"],
                            "snapshot_sha256": ids["snapshot_sha256"], "evaluator_sha256": ids["evaluator_sha256"]}
            (run / "run-manifest.json").write_text(json.dumps(run_manifest))
            (results / "metrics.json").write_text(json.dumps(metrics))
            with patch.object(headless_bridge, "ROOT", root):
                headless_bridge.check_baseline(run)
                with self.assertRaises(RuntimeError):
                    headless_bridge.check_baseline(root.parent / "search-v2/runs/something")
                for key, value in (("corpus_version", "search-v2"), ("stress_evaluated", True),
                                   ("manifest_sha256", "wrong"), ("program_sha256", "wrong")):
                    changed = {**metrics, key: value}
                    (results / "metrics.json").write_text(json.dumps(changed))
                    with self.subTest(key=key), self.assertRaises(RuntimeError):
                        headless_bridge.check_baseline(run)
                (results / "metrics.json").write_text(json.dumps(metrics))
                for budget in (None, 0, True):
                    (run / "run-manifest.json").write_text(json.dumps({**run_manifest, "target_generations": budget}))
                    with self.subTest(budget=budget), self.assertRaises(RuntimeError):
                        headless_bridge.check_baseline(run)


if __name__ == "__main__":
    unittest.main()
