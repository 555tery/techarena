"""Focused unit tests for overnight runtime accounting; no solver/model calls."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent
SITE = HERE.parent / ".venv" / "lib" / "python3.12" / "site-packages"
if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))

from night_runtime import NightState, _is_infrastructure_failure, install_night_runtime
from shinka.core.async_runner import ShinkaEvolveRunner


def policy(*, target=3, failed=2, requests=3):
    return {
        "version": "overnight-v1",
        "target_generations": target,
        "includes_baseline": True,
        "max_failed_proposals": failed,
        "max_proposals": target - 1 + failed,
        "max_model_requests": requests,
        "max_consecutive_infrastructure_errors": 3,
        "soft_deadline_seconds": 100,
        "hard_deadline_seconds": 120,
    }


class FakeClock:
    def __init__(self, now=1_000.0):
        self.now = now

    def __call__(self):
        return self.now


def make_runner(target=3):
    runner = object.__new__(ShinkaEvolveRunner)
    runner.evo_config = SimpleNamespace(num_generations=target, max_api_costs=None)
    runner.max_proposal_jobs = 2
    runner.max_evaluation_jobs = 2
    runner.max_db_workers = 1
    runner.next_generation_to_submit = 1
    runner.assigned_generations = set()
    runner.active_proposal_tasks = {}
    runner.running_jobs = []
    runner.failed_jobs_for_retry = {}
    runner.completed_generations = 1
    runner.total_api_cost = 0.0
    runner.verbose = False
    runner.should_stop = asyncio.Event()
    runner.slot_available = asyncio.Event()
    runner.finalization_complete = asyncio.Event()
    runner.failure_calls = []
    runner.proposal_gate = asyncio.Event()

    async def wait_for_release(self, generation, task_id):
        if generation == 1:
            await self.proposal_gate.wait()
        return SimpleNamespace(generation=generation)

    async def setup(self):
        return None

    async def run(self):
        return None

    async def count(self):
        return 0

    async def terminal(self, **kwargs):
        self.failure_calls.append(kwargs)

    runner._generate_proposal_async = wait_for_release.__get__(runner)
    runner._setup_async = setup.__get__(runner)
    runner._run_async = run.__get__(runner)
    runner._count_completed_generations_from_db = count.__get__(runner)
    runner._record_terminal_failed_proposal = terminal.__get__(runner)
    runner._start_proposals = ShinkaEvolveRunner._start_proposals.__get__(runner)
    runner._get_in_flight_work_count = ShinkaEvolveRunner._get_in_flight_work_count.__get__(runner)
    runner._get_completed_job_work_count = lambda: 0
    return runner


class NightRuntimeTests(unittest.TestCase):
    def test_model_request_budget_is_atomic_across_threads(self):
        import tempfile

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "runs" / "trial"
            state = NightState(run, policy(requests=3), clock=clock)

            def reserve(_):
                try:
                    return state.reserve_model_request()
                except RuntimeError:
                    return None

            with ThreadPoolExecutor(max_workers=12) as pool:
                results = list(pool.map(reserve, range(20)))
            self.assertEqual(sum(value is not None for value in results), 3)
            self.assertEqual(state.snapshot()["model_requests_reserved"], 3)

    def test_clock_and_counters_survive_resume_and_soft_deadline_blocks_calls(self):
        import tempfile

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "trial"
            state = NightState(run, policy(), clock=clock)
            self.assertEqual(state.reserve_model_request(), 1)
            clock.now += 110
            resumed = NightState(run, policy(), clock=clock)
            self.assertEqual(resumed.snapshot()["started_at"], 1_000.0)
            self.assertEqual(resumed.snapshot()["model_requests_reserved"], 1)
            with self.assertRaisesRegex(RuntimeError, "soft_deadline"):
                resumed.reserve_model_request()

    def test_no_deadline_survives_a_day_and_resume_but_obeys_manual_stop(self):
        import tempfile
        from unittest.mock import patch
        clock = FakeClock()
        no_deadline = {**policy(), "soft_deadline_seconds": None, "hard_deadline_seconds": None}
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"PIPES_SEARCH_V31_SOFT_DEADLINE": "1", "PIPES_SEARCH_V31_HARD_DEADLINE": "2"}
        ):
            state = NightState(directory, no_deadline, clock=clock)
            self.assertEqual(state.reserve_model_request(), 1)
            clock.now += 86400
            resumed = NightState(directory, no_deadline, clock=clock)
            self.assertEqual(resumed.snapshot()["started_at"], 1000.0)
            self.assertIsNone(resumed.snapshot()["hard_deadline"])
            self.assertIsNone(resumed.mark_deadline_stop())
            self.assertIsNone(resumed.admission_reason())
            self.assertEqual(resumed.reserve_model_request(), 2)
            (Path(directory) / "night-stop-request.json").write_text('{"reason":"user_stop"}')
            self.assertEqual(resumed.mark_deadline_stop(), "user_stop")
            with self.assertRaisesRegex(RuntimeError, "user_stop"):
                resumed.reserve_model_request()

    def test_partial_deadline_configuration_is_rejected(self):
        import tempfile
        for key in ("soft_deadline_seconds", "hard_deadline_seconds"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "invalid"):
                    NightState(directory, {**policy(), key: None})

    def test_actual_pinned_start_proposals_assigns_immutable_hole_then_continues(self):
        import tempfile

        async def scenario():
            clock = FakeClock()
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory) / "trial"
                runner = make_runner()
                connection = sqlite3.connect(":memory:")
                connection.execute("CREATE TABLE programs (generation INTEGER, metadata TEXT)")
                connection.execute("CREATE TABLE attempt_log (generation INTEGER, status TEXT, details TEXT)")
                connection.execute("INSERT INTO programs VALUES (0, '{}')")
                runner.db = SimpleNamespace(cursor=connection.cursor())
                state = install_night_runtime(runner, run, policy(), clock=clock)
                await runner._start_proposals(2)
                self.assertEqual(runner.next_generation_to_submit, 3)
                self.assertEqual(state.snapshot()["proposal_count"], 2)
                self.assertEqual(runner.evo_config.num_generations, 3)
                await asyncio.sleep(0)
                self.assertIn(2, state.snapshot()["successful_proposal_generations"])

                await runner._record_terminal_failed_proposal(
                    generation=1,
                    failure_stage="proposal",
                    failure_reason="No changes applied",
                    meta_patch_data={"last_error_msg": "No changes applied"},
                )
                self.assertEqual(state.snapshot()["failed_proposal_count"], 1)
                self.assertEqual(state.snapshot()["consecutive_infrastructure_errors"], 0)
                self.assertEqual(state.id_ceiling(), 4)

                gen1_task = next(
                    task for task in runner.active_proposal_tasks.values()
                    if task.get_name() == "proposal_1"
                )
                gen1_task.cancel()
                await asyncio.gather(gen1_task, return_exceptions=True)
                runner.active_proposal_tasks.clear()
                connection.execute("INSERT INTO programs VALUES (2, '{}')")
                await runner._start_proposals(1)
                self.assertEqual(runner.next_generation_to_submit, 4)
                self.assertEqual(runner.evo_config.num_generations, 3)
                await asyncio.sleep(0)
                connection.execute("INSERT INTO programs VALUES (3, '{}')")
                self.assertEqual(await runner._count_completed_generations_from_db(), 3)
                runner.completed_generations = 3
                self.assertEqual(runner._get_remaining_completed_work(), 0)
                proposals_before = state.snapshot()["proposal_count"]
                await runner._start_proposals(1)
                self.assertEqual(runner.next_generation_to_submit, 4)
                self.assertEqual(state.snapshot()["proposal_count"], proposals_before)
                self.assertEqual(proposals_before, 3)
                self.assertEqual(
                    set(state.snapshot()["successful_proposal_generations"]), {2, 3}
                )
                for task in list(runner.active_proposal_tasks.values()):
                    task.cancel()
                await asyncio.gather(
                    *runner.active_proposal_tasks.values(), return_exceptions=True
                )
                connection.close()

        asyncio.run(scenario())

    def test_resume_marks_reserved_unresolved_generation_as_infra_failure(self):
        import tempfile

        async def scenario():
            clock = FakeClock()
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory) / "trial"
                state = NightState(run, policy(), clock=clock)
                state.reserve_proposals([1])
                # Submission was accepted, but the worker died before a
                # durable Program row appeared in SQLite. Resume must charge
                # this ID as interrupted instead of treating it as complete.
                state.record_successful_proposal(1)

                runner = make_runner()
                connection = sqlite3.connect(":memory:")
                connection.execute("CREATE TABLE programs (generation INTEGER, metadata TEXT)")
                connection.execute("CREATE TABLE attempt_log (generation INTEGER, status TEXT, details TEXT)")
                connection.execute("INSERT INTO programs VALUES (0, '{}')")
                runner.db = SimpleNamespace(cursor=connection.cursor())
                install_night_runtime(runner, run, policy(), clock=clock)
                await runner._setup_async()

                saved = state.snapshot()
                self.assertEqual(saved["failed_proposal_count"], 1)
                self.assertEqual(saved["total_infrastructure_errors"], 1)
                self.assertEqual(runner.next_generation_to_submit, 2)
                self.assertEqual(state.id_ceiling(), 4)
                self.assertTrue((run / "night-failures.jsonl").exists())
                connection.close()

        asyncio.run(scenario())

    def test_completion_count_uses_distinct_real_generations_not_island_count(self):
        import tempfile

        async def scenario():
            clock = FakeClock()
            with tempfile.TemporaryDirectory() as directory:
                run = Path(directory) / "trial"
                runner = make_runner()
                connection = sqlite3.connect(":memory:")
                connection.execute("CREATE TABLE programs (generation INTEGER, metadata TEXT)")
                connection.execute("CREATE TABLE attempt_log (generation INTEGER, status TEXT, details TEXT)")
                connection.executemany(
                    "INSERT INTO programs VALUES (?, ?)",
                    [
                        (0, "{}"),
                        (0, '{"_is_island_copy": true}'),
                        (1, "{}"),
                        (2, '{"_spawned_island": true}'),
                    ],
                )
                runner.db = SimpleNamespace(cursor=connection.cursor())
                install_night_runtime(runner, run, policy(), clock=clock)
                self.assertEqual(await runner._count_completed_generations_from_db(), 2)
                connection.close()

        asyncio.run(scenario())

    def test_infrastructure_markers_exclude_ordinary_patch_failures(self):
        self.assertTrue(_is_infrastructure_failure("proposal", "Headless query timed out", {}))
        self.assertTrue(_is_infrastructure_failure("proposal", "HTTP 429 rate limit", {}))
        self.assertTrue(_is_infrastructure_failure("proposal", "Not signed in", {}))
        self.assertFalse(_is_infrastructure_failure("proposal", "No changes applied", {}))
        self.assertFalse(_is_infrastructure_failure("proposal", "Could not extract code", {}))

    def test_success_resets_infrastructure_streak(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            state = NightState(Path(directory) / "trial", policy(), clock=FakeClock())
            state.reserve_proposals([1, 2])
            state.record_failed_proposal(
                {"generation": 1, "failure_stage": "proposal", "failure_reason": "429", "infrastructure": True}
            )
            self.assertEqual(state.snapshot()["consecutive_infrastructure_errors"], 1)
            state.record_successful_proposal(2)
            self.assertEqual(state.snapshot()["consecutive_infrastructure_errors"], 0)


if __name__ == "__main__":
    unittest.main()
