from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compare_reports import compare
import compare_reports


FAMILIES = [f"family_{i:02d}" for i in range(16)]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class CompareReportsFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "search-v2"
        self.suite = root / "task" / "data" / "search"
        self.suite.mkdir(parents=True)
        (root / "snapshot.json").write_text('{"fixture": "snapshot"}\n')
        cases = []
        for i in range(128):
            family = FAMILIES[i // 8]
            cases.append({
                "id": f"case_{i:03d}", "file": f"case_{i:03d}.in",
                "family": family, "sha256": _sha(f"input-metadata-{i}"),
            })
        self.manifest = {
            "split": "search", "version": "search-v2", "case_count": 128,
            "cases_per_family": 8, "families": FAMILIES, "cases": cases,
        }
        self.manifest_bytes = (json.dumps(self.manifest, sort_keys=True) + "\n").encode()
        (self.suite / "manifest.json").write_bytes(self.manifest_bytes)
        self.snapshot_sha = hashlib.sha256((root / "snapshot.json").read_bytes()).hexdigest()
        self.manifest_sha = hashlib.sha256(self.manifest_bytes).hexdigest()
        self.old = Path(self.temp.name) / "reference"
        self.fast = Path(self.temp.name) / "accelerated"
        self._write_run(self.old, "old", 1.0)
        self._write_run(self.fast, "fast", 0.7)

    def _write_run(self, root: Path, variant: str, wall_s: float):
        results = root
        harness_runs = results / "harness" / "runs"
        harness_runs.mkdir(parents=True)
        records = []
        for i, case in enumerate(self.manifest["cases"]):
            name = Path(case["file"]).stem
            strategy = "synthetic-search" if variant == "old" else "search-v2"
            case_dir = harness_runs / name
            case_dir.mkdir()
            transcript = case_dir / "judge_output.txt"
            transcript.write_bytes(f"official transcript for {i}\n".encode())
            records.append({
                "weight": 1.0,
                "test_sha256": case["sha256"],
                "operation_count": 8000,
                "placement_count": 4012,
                "peak_live_pipe_length_m": 70,
                "minimum_trench_lower_bound_m": 80,
                "final_occupied_length_m": 40,
                "kpi_upper_bound_from_live_volume": 0.5,
                "case": name,
                "test_file": str((self.suite / case["file"]).resolve()),
                "status": "ok",
                "detail": "",
                "judge_commands_seen_including_final_zero": 8001,
                "occupied_length_m": 40,
                "trench_length_m": 100,
                "kpi": 0.4,
                "weighted_score": 0.4,
                "official_weight": 1.0,
                "fraction_of_bound": 0.8,
                "lower_bound_to_actual_trench_ratio": 0.8,
                "wall_orchestration_s": wall_s,
                "solver_cpu_user_s": 0.1,
                "solver_cpu_system_s": 0.1,
                "solver_cpu_total_s": 0.2,
                "solver_peak_rss_mb": 2.0,
                "interactor_cpu_user_s": 0.05,
                "interactor_cpu_system_s": 0.05,
                "interactor_cpu_total_s": 0.1,
                "interactor_peak_rss_mb": 2.5,
                "candidate_stderr": "",
                "interactor_stderr": "Score = 40/100\n",
                "judge_output_file": str(transcript),
                "interactor_report_file": str(case_dir / "interactor_report.txt"),
                "candidate_stderr_file": str(case_dir / "solver_stderr.txt"),
                "interactor_stderr_file": str(case_dir / "interactor_stderr.txt"),
                "strategy": strategy,
                "cpu_limit_s": 5.0,
                "memory_limit_mb": 256.0,
                "solver_cpu_limit_exceeded": False,
                "solver_memory_limit_exceeded": False,
            })
        family_scores = {family: 0.75 for family in FAMILIES}
        metrics = {
            "combined_score": 0.75,
            "suite": "search",
            "corpus_version": "search-v2",
            "public": {
                "valid_cases": 128, "family_count": 16, "worst_family_score": 0.75,
                "mean_raw_kpi": 0.4, "max_solver_cpu_seconds": 0.2,
                "max_solver_rss_mib": 2.0,
            },
            "family_scores": family_scores,
            "fitness_definition": "family-balanced mean of rounded peak live volume / trench length",
            "program_sha256": "1" * 64,
            "manifest_sha256": self.manifest_sha,
            "snapshot_sha256": self.snapshot_sha,
            "evaluator_sha256": ("2" if variant == "old" else "3") * 64,
        }
        (results / "metrics.json").write_text(json.dumps(metrics) + "\n")
        (results / "correct.json").write_text('{"correct": true}\n')
        summary = {
            "strategy": "synthetic-search" if variant == "old" else "search-v2",
            "tests": [str((self.suite / case["file"]).resolve()) for case in self.manifest["cases"]],
            "case_count": 128,
            "ok_count": 128,
            "weighted_score_sum": 51.2,
            "weight_sum": 128.0,
            "mean_kpi_upper_bound_from_live_volume": 0.5,
            "mean_kpi_fraction_of_bound": 0.8,
            "worst_relative_regret_vs_bound": 0.2,
            "mean_lower_bound_to_actual_trench_ratio": 0.8,
            "min_lower_bound_to_actual_trench_ratio": 0.8,
            "mean_trench_to_lower_bound_ratio": 1.25,
            "is_official_open_test_set": False,
            "cpu_measurement": "solver child via wait4; interactor reported separately",
            "rss_measurement": "solver child ru_maxrss in MiB",
            "wall_measurement": "harness + solver + interactor wall time",
            "records": records,
        }
        (results / "harness" / "summary.json").write_text(json.dumps(summary) + "\n")

    def _compare(self):
        with patch.object(compare_reports, "SEARCH_V2_SUITE", self.suite):
            return compare(self.old, self.fast, self.manifest, self.suite)

    def test_identical_results_and_faster_case_wall_pass(self):
        report = self._compare()
        self.assertTrue(report["ok"], report["mismatches"][:5])
        self.assertEqual(report["counts"]["paired_cases"], 128)
        self.assertEqual(report["counts"]["transcripts_identical"], 128)
        self.assertEqual(report["score"]["old"]["combined_score"], 0.75)
        self.assertAlmostEqual(report["resources"]["speedups_old_over_fast"]["wall_sum_s"], 1 / 0.7)
        self.assertAlmostEqual(report["resources"]["per_family"]["family_00"]["wall_speedup_old_over_fast"], 1 / 0.7)
        self.assertNotEqual(report["identity"]["source_hashes_may_differ"]["evaluator_sha256"]["old"],
                            report["identity"]["source_hashes_may_differ"]["evaluator_sha256"]["fast"])
        self.assertNotEqual(report["artifacts"]["run_metadata"]["old"]["strategy"],
                            report["artifacts"]["run_metadata"]["fast"]["strategy"])

    def test_deterministic_case_change_is_reported(self):
        path = self.fast / "harness" / "summary.json"
        summary = json.loads(path.read_text())
        summary["records"][0]["trench_length_m"] = 120
        path.write_text(json.dumps(summary) + "\n")
        report = self._compare()
        self.assertFalse(report["ok"])
        self.assertTrue(any(m["scope"] == "case[case_000]" and m["field"] == "trench_length_m"
                            for m in report["mismatches"]))

    def test_transcript_hash_change_is_reported(self):
        path = self.fast / "harness" / "runs" / "case_000" / "judge_output.txt"
        path.write_text("different complete transcript\n")
        report = self._compare()
        self.assertFalse(report["ok"])
        self.assertEqual(report["counts"]["transcripts_identical"], 127)
        self.assertTrue(any(m["field"] == "judge_output_sha256" and m["scope"] == "case[case_000]"
                            for m in report["mismatches"]))

    def test_solver_cpu_limit_is_enforced_on_fresh_records(self):
        path = self.fast / "harness" / "summary.json"
        summary = json.loads(path.read_text())
        record = summary["records"][0]
        record["solver_cpu_user_s"] = 4.9
        record["solver_cpu_system_s"] = 0.1
        record["solver_cpu_total_s"] = 5.0
        fast_metrics = json.loads((self.fast / "metrics.json").read_text())
        fast_metrics["public"]["max_solver_cpu_seconds"] = 5.0
        (self.fast / "metrics.json").write_text(json.dumps(fast_metrics) + "\n")
        path.write_text(json.dumps(summary) + "\n")
        report = self._compare()
        self.assertFalse(report["ok"])
        self.assertTrue(any("below the 5 s limit" in m["reason"] for m in report["mismatches"]))

    def test_wrong_suite_path_returns_before_reading_manifest(self):
        forbidden_suite = Path(self.temp.name) / "validation"
        with patch.object(compare_reports, "SEARCH_V2_SUITE", self.suite):
            report = compare(self.old, self.fast, self.manifest, forbidden_suite)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["mismatches"]), 1)
        self.assertEqual(report["mismatches"][0]["field"], "suite_path")

    def test_transcript_outside_expected_case_path_is_never_hashed(self):
        outside = self.fast / "unrelated-output.txt"
        outside.write_text("must not be opened as a transcript\n")
        summary_path = self.fast / "harness" / "summary.json"
        summary = json.loads(summary_path.read_text())
        summary["records"][0]["judge_output_file"] = str(outside)
        summary_path.write_text(json.dumps(summary) + "\n")
        report = self._compare()
        self.assertFalse(report["ok"])
        self.assertIsNone(report["artifacts"]["per_case"]["case_000"]["judge_output_sha256"]["fast"])
        self.assertTrue(any(m["scope"] == "fast" and m["field"] == "case[case_000].judge_output_file"
                            and "exactly" in m["reason"] for m in report["mismatches"]))


if __name__ == "__main__":
    unittest.main()
