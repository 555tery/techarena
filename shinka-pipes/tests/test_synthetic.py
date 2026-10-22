"""Input/fitness/protocol tests only. No solver, interactor or model execution."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generate_synthetic import SEARCH_FAMILIES, RESERVED_FAMILIES, audit_commands, generate, make_specs
from synthetic_eval import SEARCH, VALIDATION, aggregate_report, check_prepared_suites, load_suite


class CorpusChecks(unittest.TestCase):
    def test_every_prepared_input_with_existing_harness_parser(self):
        spec = importlib.util.spec_from_file_location("input_parser_only", ROOT / "task-synthetic/tools/pipes_harness.py")
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)
        for split, path in (("search", SEARCH), ("validation", VALIDATION)):
            manifest = load_suite(path, split)
            for case in manifest["cases"]:
                stats = harness.parse_test(path / case["file"])
                with self.subTest(case=case["id"]):
                    self.assertEqual(stats["operation_count"], case["operations"])
                    self.assertEqual(stats["peak_live_pipe_length_m"], case["stats"]["peak_live_volume"])
                    self.assertEqual(stats["final_occupied_length_m"], case["stats"]["final_live_volume"])
                    self.assertEqual(stats["minimum_trench_lower_bound_m"], case["stats"]["volume_lower_bound"])
                    self.assertEqual(stats["weight"], 1.0)

    def test_disjoint_splits_and_untouched_open15(self):
        report = check_prepared_suites()
        self.assertEqual((report["search_cases"], report["validation_cases"]), (32, 24))
        self.assertEqual((report["search_families"], report["validation_families"]), (16, 20))
        self.assertTrue(report["open15_preserved"])
        self.assertEqual(len(report["validation_reserved_families"]), 4)

    def test_all_mechanisms_are_deterministic_and_structurally_valid(self):
        specs = make_specs("search") + make_specs("validation")
        seen = set()
        for spec in specs:
            if spec["family"] in seen:
                continue
            seen.add(spec["family"])
            small = {**spec, "operations": 2500, "target_live": 16}
            first = generate(small)
            self.assertEqual(first, generate(small))
            stats = audit_commands(first)
            self.assertEqual(stats["operation_count"], 2500)
            self.assertGreater(stats["deletions"], 0)
        self.assertEqual(seen, set(SEARCH_FAMILIES + RESERVED_FAMILIES))

    def test_independent_audit_rejects_invalid_deletions(self):
        for commands in ([2, -2], [2, -1, -1], [0], [41]):
            with self.assertRaises(ValueError):
                audit_commands(commands)

    def test_active_entrypoint_has_no_validation_selection(self):
        path = ROOT / "task-synthetic/evaluate.py"
        spec = importlib.util.spec_from_file_location("synthetic_entrypoint", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, "argv", [str(path), "--program_path", "/not-executed.cpp", "--results_dir", "/not-created"]):
            with patch.object(module, "evaluate", return_value=True) as evaluate:
                self.assertEqual(module.main(), 0)
        self.assertEqual(evaluate.call_args.kwargs, {"split": "search"})

    def test_validation_defaults_to_input_check_only(self):
        import validate
        with patch.object(sys, "argv", ["validate.py"]), patch.object(validate, "evaluate") as evaluate:
            self.assertEqual(validate.main(), 0)
            evaluate.assert_not_called()


class FitnessChecks(unittest.TestCase):
    def fixture(self):
        # Family A has two cases; family B has one. Families must have equal weight.
        manifest = {"split": "search", "version": "synthetic-v1", "families": ["A", "B"], "cases": []}
        records = []
        for name, family, trench in (("a1", "A", 100), ("a2", "A", 200), ("b1", "B", 400)):
            manifest["cases"].append({"file": name + ".in", "id": name, "family": family,
                                      "sha256": name, "stats": {"volume_lower_bound": 100, "final_live_volume": 40}})
            records.append({"test_file": str(SEARCH / (name + ".in")), "test_sha256": name,
                            "status": "ok", "solver_cpu_total_s": 0.1, "solver_peak_rss_mb": 10,
                            "trench_length_m": trench, "minimum_trench_lower_bound_m": 100,
                            "final_occupied_length_m": 40, "kpi": 40 / trench})
        return {"records": records}, manifest

    def test_family_balance_and_normalization(self):
        summary, manifest = self.fixture()
        metrics, correct = aggregate_report(summary, manifest, SEARCH, 0)
        self.assertTrue(correct)
        self.assertAlmostEqual(metrics["combined_score"], (0.75 + 0.25) / 2)
        self.assertAlmostEqual(metrics["public"]["mean_raw_kpi"], (0.4 + 0.2 + 0.1) / 3)
        self.assertNotAlmostEqual(metrics["combined_score"], (1 + 0.5 + 0.25) / 3)

    def test_bad_coverage_resources_or_inconsistent_reports_are_rejected(self):
        original, manifest = self.fixture()
        bad_cases = []
        missing = deepcopy(original)
        missing["records"].pop()
        bad_cases.append(missing)
        for key, value in (("test_sha256", "wrong"), ("status", "invalid"),
                           ("solver_cpu_total_s", 5.0), ("solver_peak_rss_mb", 256.0),
                           ("solver_cpu_total_s", float("nan")), ("trench_length_m", 80),
                           ("kpi", 0.9), ("test_file", str(VALIDATION / "a1.in"))):
            bad = deepcopy(original)
            bad["records"][0][key] = value
            bad_cases.append(bad)
        duplicate = deepcopy(original)
        duplicate["records"][1] = duplicate["records"][0]
        bad_cases.append(duplicate)
        for summary in bad_cases:
            with self.assertRaises(ValueError):
                aggregate_report(summary, manifest, SEARCH, 0)


if __name__ == "__main__":
    unittest.main()
