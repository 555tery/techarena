"""Transport parity on generated fixtures only; no SEARCH inputs are opened."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "evaluator-fast"))
from fixture_tools import build_tools, write_input
from fast_harness import build_harness as old_harness
from build_native import build
import native_harness


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="pipes-native-fixtures-")
        cls.directory = Path(cls.temporary.name)
        cls.solver, cls.official = build_tools(cls.directory)
        cls.native = build(cls.directory / "build")
        cls.adversarial = cls.directory / "adversarial"
        subprocess.run([shutil.which("g++"), "-O2", "-std=c++20", str(ROOT / "fixtures/adversarial.cpp"),
                        "-o", str(cls.adversarial)], capture_output=True, text=True, timeout=120, check=True)
        cls.test = cls.directory / "fixture.in"
        write_input(cls.test, [5, 7, -1, 8, -2])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def check_mode(self, mode, accepted=False, timeout=False):
        old = old_harness(transport="selector")
        new = native_harness.build_harness()
        records = []
        for label, harness, judge in (("old", old, self.official), ("native", new, self.native)):
            response = 0.75 if mode in ("no_flush", "partial") else 5
            directory = self.directory / (mode + "-" + label)
            record = harness.run_case([str(self.solver), mode], judge, self.test, directory, response, 15)
            self.assertEqual(record["status"] == "ok", accepted, (mode, label, record))
            if timeout:
                self.assertEqual(record["status"], "timeout", record)
            if label == "native":
                native = json.loads((directory / "native_report.json").read_text())
                self.assertTrue(native["has_usage"], native)
                self.assertGreaterEqual(record["solver_cpu_total_s"], 0)
                self.assertGreater(record["solver_peak_rss_mb"], 0)
                with self.assertRaises(ProcessLookupError):
                    os.kill(native["solver_pid"], 0)
            records.append(record)
        if accepted:
            ignored = {"wall_orchestration_s", "judge_output_file", "interactor_report_file", "candidate_stderr_file", "interactor_stderr_file"}
            for key in records[0]:
                if key in ignored or key.startswith(("solver_cpu", "interactor_cpu", "solver_peak", "interactor_peak")):
                    continue
                self.assertEqual(records[0][key], records[1][key], (mode, key))
            self.assertEqual(Path(records[0]["judge_output_file"]).read_bytes(), Path(records[1]["judge_output_file"]).read_bytes())

    def test_valid_and_boundaries(self):
        for mode in ("valid", "fragmented", "signed", "max_line", "stderr_pressure"):
            with self.subTest(mode=mode):
                self.check_mode(mode, True)

    def test_malformed_and_checker_rejections(self):
        for mode in ("eof", "missing_lf", "empty", "extra", "one_token", "noninteger", "nonascii", "too_long",
                     "unterminated_long", "out_of_trench", "negative_dig", "out_of_range", "overlap",
                     "wrong_delete", "delete_extra", "after_zero", "nonzero_exit"):
            with self.subTest(mode=mode):
                self.check_mode(mode)

    def test_response_and_exit_timeouts(self):
        for mode in ("no_flush", "partial", "no_exit"):
            with self.subTest(mode=mode):
                self.check_mode(mode, timeout=True)

    def test_overall_wall_deadline(self):
        new = native_harness.build_harness()
        record = new.run_case([str(self.solver), "partial"], self.native, self.test,
                              self.directory / "overall-wall", 5, 0.3)
        self.assertEqual(record["status"], "timeout")
        self.assertLess(record["wall_orchestration_s"], 2)

    def test_large_integer_normalization_prefill_and_after_zero_flood(self):
        for mode, accepted in (("huge_zero", True), ("prefill", True), ("huge_integer", False), ("zero_flood", False)):
            with self.subTest(mode=mode):
                results = []
                for name, harness, checker in (("old", old_harness(), self.official), ("native", native_harness.build_harness(), self.native)):
                    rec = harness.run_case([str(self.adversarial), mode], checker, self.test,
                                           self.directory / f"adversarial-{mode}-{name}", 5, 15)
                    self.assertEqual(rec["status"] == "ok", accepted, rec)
                    results.append(rec)
                if accepted:
                    self.assertEqual(results[0]["trench_length_m"], results[1]["trench_length_m"])
                    self.assertEqual(Path(results[0]["judge_output_file"]).read_bytes(), Path(results[1]["judge_output_file"]).read_bytes())

    def test_solver_cpu_is_separate_and_memory_failure_skips_following_case(self):
        harness = native_harness.build_harness()
        record = harness.run_case([str(self.adversarial), "cpu"], self.native, self.test,
                                  self.directory / "cpu-identity", 5, 15)
        self.assertEqual(record["status"], "ok", record)
        self.assertGreater(record["solver_cpu_total_s"], 0.08)
        self.assertLess(record["solver_cpu_total_s"], 1)
        self.assertLess(record["interactor_cpu_total_s"], 0.08, record)
        memory = harness.run_case([str(self.adversarial), "memory"], self.native, self.test,
                                  self.directory / "memory-limit", 5, 15)
        self.assertEqual(memory["status"], "ok", memory)
        self.assertGreaterEqual(memory["solver_peak_rss_mb"], 256)
        skipped = harness.run_case([str(self.solver), "valid"], self.native, self.test,
                                   self.directory / "must-not-run", 5, 15)
        self.assertEqual(skipped["status"], "skipped")
        self.assertFalse((self.directory / "must-not-run/native_report.json").exists())

    def test_proven_failure_skips_following_case(self):
        harness = native_harness.build_harness()
        record = harness.run_case([str(self.solver), "extra"], self.native, self.test,
                                  self.directory / "fail-fast-first", 5, 15)
        self.assertNotEqual(record["status"], "ok")
        skipped = harness.run_case([str(self.solver), "valid"], self.native, self.test,
                                   self.directory / "fail-fast-second", 5, 15)
        self.assertEqual(skipped["status"], "skipped")
        self.assertIsNone(skipped["solver_cpu_total_s"])
        self.assertFalse((self.directory / "fail-fast-second").exists())

    def invoke_pool(self, label, workers, mode, count=8):
        inputs = self.directory / (label + "-inputs")
        inputs.mkdir()
        for index in range(1, count + 1):
            write_input(inputs / f"{index}.in", [index, index + 2, -1, index + 3, -2])
        out = self.directory / label
        argv = ["native_harness.py", "--workers", str(workers), "--solver", f"{self.solver} {mode}",
                "--interactor", str(self.native), "--tests", str(inputs), "--out", str(out)]
        with patch.object(sys, "argv", argv):
            code = native_harness.main()
        return code, json.loads((out / "summary.json").read_text())

    def test_parallel_matches_serial_and_keeps_canonical_order(self):
        code, serial = self.invoke_pool("serial-valid", 1, "valid", 12)
        self.assertEqual(code, 0)
        code, parallel = self.invoke_pool("parallel-valid", 4, "valid", 12)
        self.assertEqual(code, 0)
        self.assertEqual([r["case"] for r in parallel["records"]], [str(i) for i in range(1, 13)])
        for old, new in zip(serial["records"], parallel["records"]):
            for key in ("trench_length_m", "occupied_length_m", "kpi", "weighted_score",
                        "fraction_of_bound", "judge_commands_seen_including_final_zero"):
                self.assertEqual(old[key], new[key], key)
            self.assertEqual(Path(old["judge_output_file"]).read_bytes(), Path(new["judge_output_file"]).read_bytes())
            report = json.loads((Path(new["judge_output_file"]).parent / "native_report.json").read_text())
            self.assertTrue(report["has_usage"])
            self.assertGreater(new["solver_peak_rss_mb"], 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(report["solver_pid"], 0)
        self.assertEqual(serial["weighted_score_sum"], parallel["weighted_score_sum"])

    def test_parallel_stops_scheduling_after_proven_failure(self):
        code, summary = self.invoke_pool("parallel-invalid", 2, "extra")
        self.assertEqual(code, 1)
        records = summary["records"]
        executed = [r for r in records if r["status"] != "skipped"]
        self.assertEqual(len(executed), 2)
        self.assertTrue(all(r["status"] != "ok" for r in executed))
        self.assertTrue(all(r["solver_cpu_total_s"] is None for r in records[2:]))
        self.assertFalse((self.directory / "parallel-invalid/runs/3").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
