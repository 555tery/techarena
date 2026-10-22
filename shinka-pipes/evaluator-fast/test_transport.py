"""Equivalence and rejection tests on generated fixtures, no corpus access."""

import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import evaluator
from fast_harness import build_harness, start_line_reader
from fixture_tools import build_tools, write_input
from reference import BASE, ROOT, check_reference, load_frozen
from selector_transport import ReadHub


class ReaderTests(unittest.TestCase):
    def test_identical_chunks_at_line_boundaries(self):
        variants = [b"", b"1 0\n", b"1 0\n20\n0\n", b"1 0", b"\n", b"x\xff\n",
                    b"1 0" + b" " * 4092 + b"\n", b"1 0" + b" " * 4093 + b"\n",
                    b"x" * 9000 + b"\n", b"x" * 4097, b"\r\n", b"0\x001\n"]
        for data in variants:
            with self.subTest(length=len(data), prefix=data[:10]):
                outputs = []
                for buffered in (False, True):
                    raw = io.BytesIO(data)
                    out = queue.Queue()
                    thread = build_harness(transport="buffered" if buffered else "reference").start_line_reader(raw, out, "fixture")
                    thread.join(1)
                    self.assertFalse(thread.is_alive())
                    result = []
                    while True:
                        item = out.get_nowait()
                        result.append(item)
                        if item is None:
                            break
                    self.assertFalse(raw.closed)  # Popen/parent retains ownership.
                    outputs.append(result)
                self.assertEqual(*outputs)

    def test_lf_returns_while_pipe_stays_open(self):
        read_fd, write_fd = os.pipe()
        raw = os.fdopen(read_fd, "rb", buffering=0)
        out = queue.Queue()
        thread = start_line_reader(raw, out, "fixture")
        try:
            os.write(write_fd, b"1 ")
            with self.assertRaises(queue.Empty):
                out.get(timeout=0.03)
            os.write(write_fd, b"0\n")
            self.assertEqual(out.get(timeout=0.5), b"1 0\n")
            self.assertTrue(thread.is_alive())
            os.write(write_fd, b"20\n0\n")
            self.assertEqual(out.get(timeout=0.5), b"20\n")
            self.assertEqual(out.get(timeout=0.5), b"0\n")
        finally:
            os.close(write_fd)
            thread.join(1)
            raw.close()
        self.assertFalse(thread.is_alive())
        self.assertIsNone(out.get(timeout=0.5))

    def test_read_error_is_forwarded_then_eof(self):
        class Broken(io.RawIOBase):
            def readable(self):
                return True

            def readinto(self, buffer):
                raise OSError("fixture read failure")

        for buffered in (False, True):
            raw, out = Broken(), queue.Queue()
            thread = build_harness(transport="buffered" if buffered else "reference").start_line_reader(raw, out, "fixture")
            thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(out.get_nowait(), ("reader_error", "fixture: OSError('fixture read failure')"))
            self.assertIsNone(out.get_nowait())
            self.assertFalse(raw.closed)
            raw.close()

    def test_no_other_harness_function_is_replaced(self):
        old, new = build_harness(transport="reference"), build_harness(transport="buffered")
        for name, value in vars(old).items():
            if callable(value) and hasattr(value, "__code__") and name != "start_line_reader":
                self.assertEqual(value.__code__, getattr(new, name).__code__, name)
        selector = build_harness()
        for name in ("wait_line", "read_response", "reap_with_stats", "terminate_and_reap", "main"):
            self.assertEqual(getattr(old, name).__code__, getattr(selector, name).__code__, name)
        self.assertEqual(old.run_case.__code__, selector.reference_run_case.__code__)

    def test_selector_chunks_match_reference_for_all_fragment_sizes(self):
        # feed() is the whole new parser; compare it with the exact bounded
        # readline contract at LF, EOF and long-line chunk boundaries.
        data = b"1 0\n\n" + b"x" * 4096 + b"\n" + b"y" * 4097 + b"z" * 4095 + b"\npartial"
        original = io.BytesIO(data)
        expected = []
        while line := original.readline(4097):
            expected.append(line)
        expected.append(None)
        for size in (1, 2, 3, 4095, 4096, 4097, 65536):
            with self.subTest(fragment_size=size):
                hub = ReadHub()
                out = hub.new_queue()
                try:
                    for start in range(0, len(data), size):
                        out.feed(data[start:start + size])
                    hub.finish(out)
                    self.assertEqual(list(out.items), expected)
                finally:
                    hub.close()

    def test_selector_services_both_pipes_and_keeps_unfinished_line(self):
        hub = ReadHub()
        pipes = [os.pipe(), os.pipe()]
        streams = [os.fdopen(pair[0], "rb", buffering=0) for pair in pipes]
        queues = [hub.new_queue(), hub.new_queue()]
        try:
            for index in range(2):
                hub.attach(streams[index], queues[index], str(index))
            os.write(pipes[0][1], b"1 ")
            os.write(pipes[1][1], b"20\n0\n")
            self.assertEqual(queues[1].get(timeout=0.5), b"20\n")
            self.assertEqual(queues[1].get(timeout=0.5), b"0\n")
            with self.assertRaises(queue.Empty):
                queues[0].get(timeout=0.03)
            os.write(pipes[0][1], b"0\n")
            self.assertEqual(queues[0].get(timeout=0.5), b"1 0\n")
            for _, fd in pipes:
                os.close(fd)
            self.assertIsNone(queues[0].get(timeout=0.5))
            self.assertIsNone(queues[1].get(timeout=0.5))
        finally:
            for stream in streams:
                stream.close()
            hub.close()

    def test_selector_read_error_is_forwarded_then_eof(self):
        hub = ReadHub()
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "rb", buffering=0)
        out = hub.new_queue()
        try:
            hub.attach(stream, out, "fixture")
            os.write(write_fd, b"ready")
            with mock.patch("selector_transport.os.read", side_effect=OSError("fixture read failure")):
                self.assertEqual(out.get(timeout=0.5), ("reader_error", "fixture: OSError('fixture read failure')"))
            self.assertIsNone(out.get(timeout=0.5))
            self.assertFalse(hub.selector.get_map())
            self.assertFalse(stream.closed)
        finally:
            os.close(write_fd)
            stream.close()
            hub.close()

    def test_selector_retries_interrupted_select_and_would_block_read(self):
        hub = ReadHub()
        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "rb", buffering=0)
        out = hub.new_queue()
        try:
            hub.attach(stream, out, "fixture")
            os.write(write_fd, b"1 0\n")
            original_select, original_read = hub.selector.select, os.read
            selects, reads = 0, 0

            def interrupted_select(timeout):
                nonlocal selects
                selects += 1
                if selects == 1:
                    raise InterruptedError()
                return original_select(timeout)

            def would_block_read(*args):
                nonlocal reads
                reads += 1
                if reads == 1:
                    raise BlockingIOError()
                return original_read(*args)

            with mock.patch.object(hub.selector, "select", side_effect=interrupted_select), \
                    mock.patch("selector_transport.os.read", side_effect=would_block_read):
                self.assertEqual(out.get(timeout=0.5), b"1 0\n")
            self.assertGreaterEqual(selects, 3)
            self.assertEqual(reads, 2)
        finally:
            os.close(write_fd)
            stream.close()
            hub.close()


class InteractiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="pipes-transport-fixtures-")
        cls.directory = Path(cls.temporary.name)
        cls.solver, cls.judge = build_tools(cls.directory)
        cls.test = cls.directory / "fixture.in"
        write_input(cls.test, [5, 7, -1, 8, -2])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def compare_mode(self, mode, accepted=False, expected_status=None):
        records, transcripts = [], []
        for transport in ("reference", "buffered", "selector"):
            harness = build_harness(transport=transport)
            child_pids = []
            original_popen = harness.subprocess.Popen

            def tracking_popen(*args, **kwargs):
                process = original_popen(*args, **kwargs)
                child_pids.append(process.pid)
                return process

            directory = self.directory / (mode + "-" + transport)
            response_timeout = 0.75 if mode in ("no_flush", "partial") else 5
            with mock.patch.object(harness.subprocess, "Popen", side_effect=tracking_popen):
                rec = harness.run_case([str(self.solver), mode], self.judge, self.test, directory, response_timeout, 15)
            for pid in child_pids:
                with self.assertRaises(ChildProcessError):
                    os.waitpid(pid, os.WNOHANG)
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            self.assertEqual(len(child_pids), 2)
            self.assertEqual(rec["status"] == "ok", accepted, rec)
            if expected_status:
                self.assertEqual(rec["status"], expected_status, rec)
            if accepted or mode in ("nonzero_exit", "no_exit", "no_flush", "partial"):
                self.assertIsNotNone(rec["solver_cpu_total_s"])
                self.assertGreaterEqual(rec["solver_cpu_total_s"], 0)
                self.assertGreater(rec["solver_peak_rss_mb"], 0)
            if mode in ("no_flush", "partial"):
                self.assertIn("solver did not flush", rec["detail"])
            if mode == "no_exit":
                self.assertIn("terminate shortly", rec["detail"])
            if mode == "stderr_pressure":
                self.assertEqual((directory / "solver_stderr.txt").stat().st_size, 262144)
            records.append(rec)
            transcript = directory / "judge_output.txt"
            transcripts.append(transcript.read_bytes() if transcript.exists() else None)
        self.assertEqual(len({record["status"] for record in records}), 1)
        if accepted:
            ignored = {"wall_orchestration_s", "judge_output_file", "interactor_report_file",
                       "candidate_stderr_file", "interactor_stderr_file"}
            for key in records[0]:
                if key in ignored or key.startswith(("solver_cpu", "interactor_cpu", "solver_peak", "interactor_peak")):
                    continue
                self.assertTrue(all(record[key] == records[0][key] for record in records), (mode, key))
            self.assertEqual(len(set(transcripts)), 1)
        # Let daemon readers observe EOF after the unchanged reference cleanup.
        deadline = time.monotonic() + 1
        while any(t.name.startswith("pipes-") for t in threading.enumerate()) and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertFalse([t.name for t in threading.enumerate() if t.name.startswith("pipes-")])

    def test_valid_and_boundary_responses(self):
        for mode in ("valid", "fragmented", "signed", "max_line", "stderr_pressure"):
            with self.subTest(mode=mode):
                self.compare_mode(mode, accepted=True)

    def test_malformed_responses_and_official_rejections(self):
        for mode in ("eof", "missing_lf", "empty", "extra", "one_token", "noninteger", "nonascii",
                     "too_long", "unterminated_long", "out_of_trench", "negative_dig", "out_of_range",
                     "overlap", "wrong_delete", "delete_extra", "after_zero"):
            with self.subTest(mode=mode):
                self.compare_mode(mode)

    def test_missing_flush_and_partial_response_timeout(self):
        for mode in ("no_flush", "partial"):
            with self.subTest(mode=mode):
                self.compare_mode(mode, expected_status="timeout")

    def test_final_zero_exit_deadline(self):
        self.compare_mode("no_exit", expected_status="timeout")

    def test_nonzero_solver_exit(self):
        self.compare_mode("nonzero_exit", expected_status="solver_error")


class ContractTests(unittest.TestCase):
    def test_reference_hashes(self):
        self.assertEqual(len(check_reference()["checked_files"]), 33)

    def test_resource_and_score_checks_are_unchanged(self):
        aggregate = load_frozen("synthetic_eval.py", shared=True).aggregate_report
        # These names/records are in memory only. No input file is opened.
        directory = Path("/fixture-only-search")
        manifest = {"split": "search", "version": "search-v2", "families": ["one", "two"], "cases": []}
        records = []
        for index, (family, trench) in enumerate((("one", 40), ("one", 80), ("two", 20))):
            name, sha = f"fixture-{index}.in", str(index) * 64
            manifest["cases"].append({"id": index, "file": name, "sha256": sha, "family": family,
                                      "stats": {"volume_lower_bound": 20, "final_live_volume": 10}})
            records.append({"test_file": str(directory / name), "test_sha256": sha, "status": "ok",
                            "solver_cpu_total_s": 0.01, "solver_peak_rss_mb": 2,
                            "trench_length_m": trench, "minimum_trench_lower_bound_m": 20,
                            "final_occupied_length_m": 10, "kpi": 10 / trench})
        summary = {"records": records}
        metrics, correct = aggregate(summary, manifest, directory, 0)
        self.assertTrue(correct)
        self.assertEqual(metrics["family_scores"], {"one": 0.375, "two": 1.0})
        self.assertEqual(metrics["combined_score"], 0.6875)
        for key, value in (("solver_cpu_total_s", 5), ("solver_peak_rss_mb", 256),
                           ("solver_cpu_total_s", float("nan")), ("solver_peak_rss_mb", float("inf")),
                           ("solver_cpu_limit_exceeded", True), ("solver_memory_limit_exceeded", True),
                           ("trench_length_m", 21), ("kpi", 0.9), ("test_sha256", "wrong"),
                           ("status", "invalid")):
            modified = json.loads(json.dumps(summary))
            modified["records"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                aggregate(modified, manifest, directory, 0)
        for modified, returncode in (({"records": records[:-1]}, 0), (summary, 1),
                                     ({"records": [records[0], records[0], records[2]]}, 0)):
            with self.assertRaises(ValueError):
                aggregate(modified, manifest, directory, returncode)

    def test_evaluator_refuses_live_results_before_any_suite_load(self):
        with mock.patch.object(evaluator, "load_frozen", side_effect=AssertionError("no loader should run")):
            with self.assertRaises(ValueError):
                evaluator.evaluate(Path("unused.cpp"), BASE / "runs/unused")
            with self.assertRaises(ValueError):
                evaluator.evaluate(Path("unused.cpp"), BASE.parent / "runs/unused")

    def test_evaluator_preserves_flags_and_uses_all_search(self):
        self.assertEqual(evaluator.LIMIT_ARGUMENTS,
                         ["--response-timeout", "5", "--wall-timeout", "180", "--cpu-limit", "5",
                          "--memory-limit-mb", "256"])
        base = load_frozen("evaluator.py")
        self.assertEqual(base.SEARCH, BASE / "task/data/search")
        self.assertEqual(base.aggregate_report.__code__, load_frozen("synthetic_eval.py", shared=True).aggregate_report.__code__)

    def test_evaluator_orchestration_without_running_a_candidate(self):
        with tempfile.TemporaryDirectory(prefix="pipes-fast-orchestration-") as temporary:
            directory = Path(temporary)
            program, search, out = directory / "fixture.cpp", directory / "search", directory / "output"
            program.write_text("// fixture, never compiled\n")
            search.mkdir()
            (search / "manifest.json").write_text("{}\n")
            reference = load_frozen("evaluator.py")
            manifest = {"fixture": "manifest"}
            base = SimpleNamespace(TASK=BASE / "task", SEARCH=search,
                                   load_search=mock.Mock(return_value=manifest),
                                   check_candidate=mock.Mock(), write_result=reference.write_result)
            aggregate = mock.Mock(return_value=({"combined_score": 0.75}, True))
            commands = []

            def fake_run(command, **options):
                commands.append((command, options))
                if len(commands) == 3:
                    (out / "harness").mkdir()
                    (out / "harness/summary.json").write_text('{"fixture": "summary"}')
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            modules = {"evaluator.py": base, "synthetic_eval.py": SimpleNamespace(aggregate_report=aggregate)}
            with mock.patch.object(evaluator, "load_frozen", side_effect=lambda name, **_: modules[name]), \
                    mock.patch.object(evaluator.shutil, "which", return_value="/fixture/g++"), \
                    mock.patch.object(evaluator.subprocess, "run", side_effect=fake_run):
                self.assertTrue(evaluator.evaluate(program, out))
            self.assertEqual(len(commands), 3)
            self.assertEqual(commands[0][0][1:4], ["-O2", "-std=c++20", "-pipe"])
            self.assertEqual(commands[1][0][1:4], ["-O2", "-std=c++17", "-pipe"])
            harness_command, options = commands[2]
            self.assertEqual(harness_command[1], str(evaluator.HARNESS))
            self.assertEqual(harness_command[harness_command.index("--tests") + 1], str(search))
            self.assertEqual(harness_command[-8:], evaluator.LIMIT_ARGUMENTS)
            self.assertEqual(options["timeout"], 128 * 180 + 60)
            aggregate.assert_called_once_with({"fixture": "summary"}, manifest, search, 0)
            base.load_search.assert_called_once_with()
            base.check_candidate.assert_called_once_with(program)
            self.assertEqual(json.loads((out / "correct.json").read_text()), {"correct": True})
            self.assertEqual(json.loads((out / "metrics.json").read_text())["combined_score"], 0.75)

    def test_existing_results_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="pipes-fast-output-guard-") as temporary:
            out = Path(temporary)
            marker = out / "metrics.json"
            marker.write_text('{"original":true}')
            with self.assertRaises(ValueError):
                evaluator.evaluate(Path("unused.cpp"), out)
            self.assertEqual(marker.read_text(), '{"original":true}')

    def test_copied_shinka_entrypoint_check_starts_no_evaluations(self):
        with tempfile.TemporaryDirectory(prefix="pipes-fast-entrypoint-") as temporary:
            copied = Path(temporary) / "evaluate.py"
            copied.write_bytes((ROOT / "evaluate.py").read_bytes())
            result = subprocess.run([sys.executable, "-B", str(copied), "--check"], capture_output=True,
                                    text=True, timeout=30, check=True,
                                    env={**os.environ, "PIPES_FAST_EVALUATOR_ROOT": str(ROOT)})
            self.assertEqual(json.loads(result.stdout)["evaluations_started"], 0)
            self.assertEqual(json.loads(result.stdout)["support_files_unchanged"], 33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
