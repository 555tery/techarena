"""Supervisor tests use fake processes/clocks, never launch an experiment."""

import json
from pathlib import Path
import signal
import tempfile
import types
import unittest
from unittest.mock import patch

import night_manager as manager


class SupervisorTests(unittest.TestCase):
    def test_hard_deadline_retains_original_clock_and_kills_only_owned_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            now = [100.0]
            (run / "night-clock.json").write_text(json.dumps({
                "started_at": 90.0, "soft_deadline": 95.0, "hard_deadline": 107.0}))
            child = types.SimpleNamespace(pid=12345, returncode=None)
            child.poll = lambda: child.returncode
            child.wait = lambda **kwargs: child.returncode
            signals = []

            class FakeTree:
                def __init__(self, pid):
                    self.known = {pid: 99.0}
                    self.errors = set()
                def capture(self):
                    pass
                def send(self, sig):
                    signals.append(sig)
                    if sig == signal.SIGKILL:
                        child.returncode = -9
                def confirm_cleanup(self):
                    return True

            def sleep(seconds):
                now[0] += seconds

            policy = {"soft_deadline_seconds": 23400, "hard_deadline_seconds": 25200}
            fake_runtime = types.SimpleNamespace(subscription_environment=lambda: {})
            with patch.object(manager, "prepared_run", return_value=(run, {}, policy)), \
                    patch.object(manager, "ProcessTree", FakeTree), \
                    patch.object(manager.subprocess, "Popen", return_value=child) as launch, \
                    patch.object(manager.time, "time", side_effect=lambda: now[0]), \
                    patch.object(manager.time, "monotonic", side_effect=lambda: now[0]), \
                    patch.object(manager.time, "sleep", side_effect=sleep), \
                    patch.dict("sys.modules", {"local_runtime": fake_runtime}):
                self.assertEqual(manager.supervise(run), -9)
            self.assertEqual(now[0], 107.0)
            self.assertEqual(signals[0], signal.SIGTERM)
            self.assertIn(signal.SIGKILL, signals)
            self.assertTrue(launch.call_args.kwargs["start_new_session"])
            outcome = json.loads((run / "night-supervisor.json").read_text())
            self.assertEqual(outcome["started_at"], 90.0)
            self.assertEqual(outcome["status"], "stopped_hard_deadline")

    def test_expired_resume_does_not_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "night-clock.json").write_text(json.dumps({"hard_deadline": 1.0}))
            with patch.object(manager, "prepared_run", return_value=(run, {}, {})), \
                    patch.object(manager.subprocess, "Popen") as launch, \
                    self.assertRaisesRegex(RuntimeError, "expired"):
                manager.supervise(run)
            launch.assert_not_called()

    def test_disabled_deadlines_do_not_kill_worker_after_a_day(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            now = [100.0]
            child = types.SimpleNamespace(pid=12345, returncode=None)
            child.poll = lambda: child.returncode
            child.wait = lambda **kwargs: child.returncode
            signals = []
            class FakeTree:
                def __init__(self, pid):
                    self.known, self.errors = {pid: 99.0}, set()
                def capture(self):
                    pass
                def send(self, sig):
                    signals.append(sig)
                def confirm_cleanup(self):
                    return True
            def sleep(seconds):
                now[0] += 30000
                if now[0] > 86400:
                    child.returncode = 0
            policy = {"soft_deadline_seconds": None, "hard_deadline_seconds": None}
            stale_env = {"PIPES_SEARCH_V31_SOFT_DEADLINE": "1", "PIPES_SEARCH_V31_HARD_DEADLINE": "2"}
            fake_runtime = types.SimpleNamespace(subscription_environment=lambda: dict(stale_env))
            with patch.object(manager, "prepared_run", return_value=(run, {}, policy)), \
                    patch.object(manager, "ProcessTree", FakeTree), \
                    patch.object(manager.subprocess, "Popen", return_value=child) as launch, \
                    patch.object(manager.time, "time", side_effect=lambda: now[0]), \
                    patch.object(manager.time, "monotonic", side_effect=lambda: now[0]), \
                    patch.object(manager.time, "sleep", side_effect=sleep), \
                    patch.dict("sys.modules", {"local_runtime": fake_runtime}):
                self.assertEqual(manager.supervise(run), 0)
            self.assertNotIn(signal.SIGTERM, signals)
            self.assertFalse((run / "night-stop-request.json").exists())
            self.assertIsNone(json.loads((run / "night-clock.json").read_text())["hard_deadline"])
            self.assertEqual(json.loads((run / "night-supervisor.json").read_text())["status"], "worker_finished")
            self.assertNotIn("PIPES_SEARCH_V31_HARD_DEADLINE", launch.call_args.kwargs["env"])

    def test_unconfirmed_cleanup_blocks_resume_even_if_worker_exited(self):
        import psutil
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "night-clock.json").write_text(json.dumps({"hard_deadline": 200.0}))
            (run / "night-supervisor.json").write_text(json.dumps({
                "worker_pid": 12345, "worker_created_at": 1.0,
                "status": "worker_finished", "cleanup_confirmed": False}))
            with patch.object(manager, "prepared_run", return_value=(run, {}, {})), \
                    patch.object(manager.time, "time", return_value=100.0), \
                    patch.object(psutil, "Process", side_effect=psutil.NoSuchProcess(12345)), \
                    patch.object(manager.subprocess, "Popen") as launch, \
                    self.assertRaisesRegex(RuntimeError, "confirmed cleanup"):
                manager.supervise(run)
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
