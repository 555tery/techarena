"""Numeric and saved-artifact fixtures only; no candidate or input-stream execution."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import diagnose as d


def table(trenches, families=None):
    families = families or ["family"] * len(trenches)
    specs, records = [], []
    for i, (trench, family) in enumerate(zip(trenches, families)):
        name = f"c{i:02d}"
        specs.append({"id": name, "file": name + ".in", "family": family,
                      "stats": {"volume_lower_bound": 40}})
        records.append({"test_file": name + ".in", "trench_length_m": trench})
    return records, {"cases": specs}


class MathTests(unittest.TestCase):
    def test_mean_excess_is_not_inverse_mean_score(self):
        result = d.summarize(*table([40, 80]))
        self.assertEqual(result["worst_16_mean_score"], .75)
        self.assertEqual(result["mean_relative_excess"], .5)
        self.assertNotAlmostEqual(result["mean_relative_excess"], 1 / .75 - 1)

    def test_family_balance_is_preserved_with_unequal_toy_group_sizes(self):
        result = d.summarize(*table([40, 40, 80], ["a", "a", "b"]))
        self.assertEqual(result["mean_relative_excess"], .5)
        self.assertEqual(result["families"][0]["family"], "b")

    def test_moving_tail_and_fixed_baseline_tail_are_distinct(self):
        baseline = d.summarize(*table([80] + [40] * 16))
        candidate = d.summarize(*table([40] * 16 + [100]))
        for item in (baseline, candidate):
            item["combined_score"] = sum(r["score"] for r in item["streams"]) / 17
        d.compare(candidate, baseline)
        self.assertEqual(candidate["baseline_worst_16_mean_score"], 1)
        self.assertAlmostEqual(candidate["worst_16_mean_score"], 15.4 / 16)
        self.assertNotEqual(candidate["baseline_worst_16_ids"], [r["case"] for r in candidate["worst_16"]])
        self.assertEqual(candidate["changes_vs_baseline"], {"improved": 1, "regressed": 1, "tied": 15})


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="saved-search-diagnostics-")
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.v2, self.analysis = root / "search-v2", root / "analysis"
        self.run = self.v2 / "runs/example"
        self.patch = patch.multiple(d, V2=self.v2, RUNS=self.v2 / "runs", ANALYSIS=self.analysis)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.suite = self.v2 / "task/data/search"
        self.suite.mkdir(parents=True)
        families = [f"f{i:02d}" for i in range(16)]
        specs, records = [], []
        for i in range(128):
            name = f"s2_{i+1:03d}"
            digest = hashlib.sha256(name.encode()).hexdigest()
            specs.append({"id": name, "file": name + ".in", "family": families[i // 8],
                          "sha256": digest, "stats": {"volume_lower_bound": 80, "final_live_volume": 40}})
            records.append({"test_file": str(self.suite / (name + ".in")), "test_sha256": digest,
                            "status": "ok", "trench_length_m": 100, "minimum_trench_lower_bound_m": 80,
                            "final_occupied_length_m": 40, "kpi": .4,
                            "solver_cpu_total_s": .01, "solver_peak_rss_mb": 1})
        self.manifest = {"version": "search-v2", "split": "search", "case_count": 128,
                         "cases_per_family": 8, "families": families, "cases": specs}
        self.write(self.suite / "manifest.json", self.manifest)
        digest = hashlib.sha256((self.suite / "manifest.json").read_bytes()).hexdigest()
        self.write(self.v2 / "protocol.json", {"manifest_sha256": digest})
        self.results = self.run / "gen_0/results"
        self.write(self.results / "correct.json", {"correct": True})
        self.summary = {"records": records}
        self.write(self.results / "harness/summary.json", self.summary)
        program = self.run / "gen_0/main.cpp"
        program.write_text("// Saved fixture, never compiled or executed.\n")
        source_hash = hashlib.sha256(program.read_bytes()).hexdigest()
        run_manifest = {"suite": "search-v2", "search_manifest_sha256": digest,
                        "snapshot_sha256": "snapshot", "evaluator_sha256": "evaluator", "source_sha256": source_hash}
        self.write(self.run / "run-manifest.json", run_manifest)
        metrics, _ = d.aggregate_report(self.summary, self.manifest, self.suite, 0)
        metrics.update(program_sha256=source_hash, manifest_sha256=digest,
                       snapshot_sha256="snapshot", evaluator_sha256="evaluator")
        self.write(self.results / "metrics.json", metrics)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def test_saved_artifacts_work_without_any_input_files_or_subprocesses(self):
        self.assertEqual(list(self.suite.glob("*.in")), [])
        output = self.analysis / "snapshot"
        with patch("subprocess.Popen", side_effect=AssertionError("subprocess forbidden")), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(["--run-dir", str(self.run), "--out-dir", str(output)]), 0)
        report = json.loads((output / "diagnostics.json").read_text())
        baseline = report["generations"][0]
        self.assertEqual(len(baseline["worst_16"]), 16)
        self.assertEqual(len(baseline["families"]), 16)
        self.assertAlmostEqual(baseline["mean_relative_excess"], .25)
        self.assertEqual(baseline["changes_vs_baseline"]["tied"], 128)
        self.assertTrue(all(not p.endswith(".in") for p in report["input_sha256"]))

    def test_missing_completion_marker_is_reported_without_fake_metrics(self):
        (self.run / "gen_1").mkdir()
        report = d.collect(self.run, [0, 1])
        self.assertEqual(report["generations"][1], {"generation": 1, "status": "incomplete"})

    def test_source_provenance_mismatch_is_rejected(self):
        (self.run / "gen_0/main.cpp").write_text("tampered fixture")
        with self.assertRaisesRegex(ValueError, "provenance"):
            d.collect(self.run)

    def test_duplicate_case_and_resource_violations_are_rejected(self):
        for mutation in ("duplicate", "cpu", "rss", "nonfinite"):
            summary = json.loads(json.dumps(self.summary))
            if mutation == "duplicate":
                summary["records"][-1] = summary["records"][0]
            else:
                key = "solver_peak_rss_mb" if mutation == "rss" else "solver_cpu_total_s"
                summary["records"][0][key] = {"cpu": 5, "rss": 256, "nonfinite": float("nan")}[mutation]
            self.write(self.results / "harness/summary.json", summary)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                d.collect(self.run)

    def test_routes_and_existing_output_are_refused_before_reading(self):
        with patch.object(d, "context") as read_context:
            with self.assertRaises(ValueError):
                d.collect(Path(self.temporary.name) / "held-out")
            read_context.assert_not_called()
        with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            d.main(["--run-dir", str(self.run), "--out-dir", str(self.run / "diagnostics")])
        output = self.analysis / "existing"
        output.mkdir(parents=True)
        with patch.object(d, "collect") as collect, self.assertRaises(ValueError):
            d.main(["--run-dir", str(self.run), "--out-dir", str(output)])
        collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
