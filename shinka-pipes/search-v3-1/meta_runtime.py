"""Run-local safeguards for Shinka's native asynchronous meta-analysis.

This adapter patches only one prepared runner instance. It keeps Shinka's native
three-step meta-analysis, bounds all proposal/meta requests through one shared
semaphore, rejects partial per-program summary batches, and preserves programs
added while a meta update is in flight.
"""

from __future__ import annotations

import asyncio
import logging
import types
from dataclasses import dataclass, field
from typing import Any, Callable


MAX_MODEL_REQUESTS = 2
VERSION = "native-meta-snapshot-v1"

NOTES = (
    "Native meta-analysis uses one request per evaluated program in step 1, "
    "then one request each for global insights and recommendations.",
    "The installed async batch API removes failed results without their indices; "
    "this adapter rejects the whole step-1 batch unless every response is present.",
    "A successful update consumes only the detached program snapshot it analyzed; "
    "new evaluations stay queued for the next update.",
    "Proposal and meta requests share a maximum of two active model calls.",
)

logger = logging.getLogger(__name__)


@dataclass
class MetaRuntime:
    """Diagnostics and controls attached to one Shinka runner instance."""

    semaphore: asyncio.Semaphore
    should_start_meta: Callable[[], bool]
    active_requests: int = 0
    max_active_requests: int = 0
    limited_requests: int = 0
    partial_batches: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    skipped_updates: int = 0
    _update_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def call_limited(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        async with self.semaphore:
            self.active_requests += 1
            self.limited_requests += 1
            self.max_active_requests = max(
                self.max_active_requests, self.active_requests
            )
            try:
                return await callback(*args, **kwargs)
            finally:
                self.active_requests -= 1

    def diagnostics(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "max_model_requests": MAX_MODEL_REQUESTS,
            "limited_requests": self.limited_requests,
            "max_active_requests": self.max_active_requests,
            "partial_batches": self.partial_batches,
            "successful_updates": self.successful_updates,
            "failed_updates": self.failed_updates,
            "skipped_updates": self.skipped_updates,
            "notes": list(NOTES),
        }


def _wrap_query(client: Any, runtime: MetaRuntime, label: str) -> None:
    original = getattr(client, "query", None)
    if original is None:
        raise TypeError(f"{label} client has no async query method")

    async def limited_query(*args: Any, **kwargs: Any) -> Any:
        return await runtime.call_limited(original, *args, **kwargs)

    client.query = limited_query


def _wrap_meta_batch_client(client: Any, runtime: MetaRuntime) -> None:
    """Bound native per-program requests and reject batches with any missing row."""
    sample_method = getattr(client, "_sample_kwargs_query_async_with_retry", None)
    batch_method = getattr(client, "batch_kwargs_query", None)
    if sample_method is None or batch_method is None:
        raise TypeError("native async meta client lacks the expected batch API")

    async def limited_sample(
        self: Any, *args: Any, **kwargs: Any
    ) -> Any:
        return await runtime.call_limited(sample_method, *args, **kwargs)

    client._sample_kwargs_query_async_with_retry = types.MethodType(
        limited_sample, client
    )

    async def complete_batch(*args: Any, **kwargs: Any) -> list[Any]:
        expected = kwargs.get("num_samples")
        if expected is None and args:
            expected = args[0]
        if type(expected) is not int or expected < 0:
            raise ValueError("meta batch must declare a non-negative num_samples")

        responses = await batch_method(*args, **kwargs)
        complete = (
            len(responses) == expected
            and all(
                response is not None
                and isinstance(getattr(response, "content", None), str)
                and bool(response.content.strip())
                for response in responses
            )
        )
        if not complete:
            runtime.partial_batches += 1
            logger.warning(
                "Discarding incomplete native meta step-1 batch: got %d/%d usable responses; "
                "the full program snapshot remains queued.",
                len(responses),
                expected,
            )
            return []
        return responses

    client.batch_kwargs_query = complete_batch


def _wrap_meta_update(meta: Any, runtime: MetaRuntime) -> None:
    original = getattr(meta, "update_meta_memory_async", None)
    sync = getattr(meta, "sync_summarizer", None)
    if original is None or sync is None:
        raise TypeError("runner meta summarizer is not Shinka's async summarizer")

    async def snapshot_update(best_program: Any = None) -> Any:
        async with runtime._update_lock:
            if not runtime.should_start_meta():
                runtime.skipped_updates += 1
                logger.info("Skipping a new meta-analysis because the run is draining.")
                return None, 0.0

            original_buffer = sync.evaluated_since_last_meta
            snapshot = list(original_buffer)
            if not snapshot:
                return await original(best_program)

            # The native method clears the entire live list after success. Give it
            # a detached working list so arrivals during its awaits can be split
            # from the snapshot it actually summarized.
            working_buffer = list(snapshot)
            total_before = sync.total_programs_processed
            sync.evaluated_since_last_meta = working_buffer
            result: Any = None
            try:
                result = await original(best_program)
                succeeded = (
                    isinstance(result, tuple)
                    and len(result) >= 1
                    and result[0] is not None
                )
                if succeeded:
                    arrivals = working_buffer[len(snapshot) :]
                    sync.evaluated_since_last_meta = arrivals
                    sync.total_programs_processed = total_before + len(snapshot)
                    runtime.successful_updates += 1
                else:
                    # Native early returns leave the working list intact. Restore
                    # the pre-update count defensively and retain every item.
                    sync.evaluated_since_last_meta = working_buffer
                    sync.total_programs_processed = total_before
                    runtime.failed_updates += 1
                return result
            except BaseException:
                # Cancellation/deadline shutdown must not lose queued programs.
                sync.evaluated_since_last_meta = working_buffer
                sync.total_programs_processed = total_before
                runtime.failed_updates += 1
                raise

    meta.update_meta_memory_async = snapshot_update


def install_meta(
    runner: Any,
    *,
    max_concurrency: int = MAX_MODEL_REQUESTS,
    should_start_meta: Callable[[], bool] | None = None,
) -> MetaRuntime | None:
    """Install native meta safeguards on one prepared runner instance.

    ``should_start_meta`` is checked before taking a snapshot or starting any
    model calls. It lets a run manager skip new meta batches while draining or
    after a soft deadline; a batch already in progress is allowed to finish.
    Returns ``None`` when native meta-analysis is disabled on this runner.
    """
    if max_concurrency != MAX_MODEL_REQUESTS:
        raise ValueError(f"prepared SEARCH-v3.1 requires concurrency={MAX_MODEL_REQUESTS}")
    if getattr(runner, "_pipes_meta_runtime", None) is not None:
        return runner._pipes_meta_runtime

    meta = getattr(runner, "meta_summarizer", None)
    if meta is None:
        return None
    meta_client = getattr(meta, "async_llm_client", None)
    proposal_client = getattr(runner, "llm", None)
    if meta_client is None or proposal_client is None:
        raise ValueError("meta and proposal clients must both be configured")

    runtime = MetaRuntime(
        semaphore=asyncio.Semaphore(max_concurrency),
        should_start_meta=should_start_meta or (lambda: True),
    )
    _wrap_query(proposal_client, runtime, "proposal")
    _wrap_query(meta_client, runtime, "meta")
    _wrap_meta_batch_client(meta_client, runtime)
    _wrap_meta_update(meta, runtime)
    runner._pipes_meta_runtime = runtime
    logger.info(
        "Installed %s: proposals and native meta share a %d-request limit.",
        VERSION,
        max_concurrency,
    )
    return runtime
