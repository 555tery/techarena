"""Focused fixtures for the SEARCH-v3.1 native meta runtime adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from shinka.core import async_summarizer as native_meta
from shinka.core.summarizer import MetaSummarizer

from meta_runtime import install_meta


@dataclass
class FakeResponse:
    content: str
    cost: float = 0.01


@dataclass
class FakeProgram:
    id: str
    generation: int
    correct: bool = True
    metadata: dict = field(default_factory=dict)
    code: str = "int main() {}"
    combined_score: float = 0.5
    public_metrics: dict = field(default_factory=dict)
    text_feedback: str = ""


class RequestTracker:
    def __init__(self):
        self.active = 0
        self.maximum = 0

    async def request(self):
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            await asyncio.sleep(0.002)
        finally:
            self.active -= 1


class FakeAsyncLLM:
    """Small shape-compatible async client exercising native call paths."""

    def __init__(self, tracker: RequestTracker, *, fail_index: int | None = None):
        self.tracker = tracker
        self.fail_index = fail_index
        self.query_calls = 0
        self.on_batch_complete = None

    async def query(self, msg, system_msg, **kwargs):
        await self.tracker.request()
        self.query_calls += 1
        if "recommend" in system_msg.lower():
            return FakeResponse("1. Keep the best allocation policy.")
        return FakeResponse("Global pattern: preserve useful fit choices.")

    async def _sample_kwargs_query_async_with_retry(
        self, idx, msg, system_msg, *args, **kwargs
    ):
        await self.tracker.request()
        if idx == self.fail_index:
            return idx, None
        return idx, FakeResponse(f"summary-{idx}")

    async def batch_kwargs_query(
        self, num_samples, msg, system_msg, msg_history=None, model_sample_probs=None
    ):
        messages = [msg] * num_samples if isinstance(msg, str) else msg
        tasks = [
            self._sample_kwargs_query_async_with_retry(
                idx,
                item,
                system_msg,
                [],
                model_sample_probs,
                num_samples,
            )
            for idx, item in enumerate(messages)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        if self.on_batch_complete is not None:
            self.on_batch_complete()
        # Match Shinka's behavior: drop None rows and their indices.
        return [
            row[1]
            for row in results
            if isinstance(row, tuple) and row[1] is not None
        ]


def make_program(index: int) -> FakeProgram:
    return FakeProgram(
        id=f"p-{index}",
        generation=index,
        metadata={"patch_name": f"patch-{index}"},
        code=f"program_{index}",
    )


def make_runner(*, fail_index=None, should_start_meta=None):
    tracker = RequestTracker()
    proposal_llm = FakeAsyncLLM(tracker)
    meta_llm = FakeAsyncLLM(tracker, fail_index=fail_index)
    sync = MetaSummarizer(async_mode=True)
    async_meta = native_meta.AsyncMetaSummarizer(sync, meta_llm)
    runner = SimpleNamespace(llm=proposal_llm, meta_summarizer=async_meta)
    runtime = install_meta(runner, should_start_meta=should_start_meta)
    return runner, sync, proposal_llm, meta_llm, tracker, runtime


class MetaRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.formatter_patch = patch.object(
            native_meta,
            "construct_individual_program_msg",
            side_effect=lambda program, **kwargs: program.code,
        )
        self.formatter_patch.start()

    async def asyncTearDown(self):
        self.formatter_patch.stop()

    async def test_partial_step1_batch_preserves_all_programs(self):
        runner, sync, _, meta_llm, _, runtime = make_runner(fail_index=3)
        programs = [make_program(i) for i in range(8)]
        for program in programs:
            runner.meta_summarizer.add_evaluated_program(program)

        recommendations, cost = await runner.meta_summarizer.update_meta_memory_async()

        self.assertIsNone(recommendations)
        self.assertEqual(cost, 0.0)
        self.assertEqual(sync.evaluated_since_last_meta, programs)
        self.assertEqual(sync.total_programs_processed, 0)
        self.assertEqual(meta_llm.query_calls, 0)
        self.assertEqual(runtime.diagnostics()["partial_batches"], 1)
        self.assertEqual(runtime.diagnostics()["failed_updates"], 1)

    async def test_concurrent_arrival_survives_successful_snapshot(self):
        runner, sync, _, meta_llm, _, runtime = make_runner()
        programs = [make_program(i) for i in range(8)]
        for program in programs:
            runner.meta_summarizer.add_evaluated_program(program)
        arrival = make_program(99)
        meta_llm.on_batch_complete = lambda: sync.add_evaluated_program(arrival)

        recommendations, _ = await runner.meta_summarizer.update_meta_memory_async()

        self.assertIsNotNone(recommendations)
        self.assertEqual(sync.evaluated_since_last_meta, [arrival])
        self.assertEqual(sync.total_programs_processed, len(programs))
        self.assertEqual(runtime.diagnostics()["successful_updates"], 1)

    async def test_proposal_and_meta_requests_share_limit_of_two(self):
        runner, _, _, _, tracker, runtime = make_runner()
        for i in range(8):
            runner.meta_summarizer.add_evaluated_program(make_program(i))

        await asyncio.gather(
            runner.llm.query("proposal-1", "proposal"),
            runner.llm.query("proposal-2", "proposal"),
            runner.meta_summarizer.update_meta_memory_async(),
        )

        self.assertEqual(tracker.maximum, 2)
        self.assertLessEqual(runtime.diagnostics()["max_active_requests"], 2)
        self.assertGreater(runtime.diagnostics()["limited_requests"], 2)

    async def test_drain_callback_skips_new_batch_without_dropping_programs(self):
        runner, sync, _, meta_llm, _, runtime = make_runner(
            should_start_meta=lambda: False
        )
        programs = [make_program(i) for i in range(8)]
        for program in programs:
            runner.meta_summarizer.add_evaluated_program(program)

        result = await runner.meta_summarizer.update_meta_memory_async()

        self.assertEqual(result, (None, 0.0))
        self.assertEqual(sync.evaluated_since_last_meta, programs)
        self.assertEqual(meta_llm.query_calls, 0)
        self.assertEqual(runtime.diagnostics()["skipped_updates"], 1)

    async def test_runner_without_meta_analysis_is_a_noop(self):
        runner = SimpleNamespace(llm=FakeAsyncLLM(RequestTracker()), meta_summarizer=None)
        self.assertIsNone(install_meta(runner))


if __name__ == "__main__":
    unittest.main()
