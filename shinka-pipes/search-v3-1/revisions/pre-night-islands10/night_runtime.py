"""Bounded, run-local runtime hooks for a future SEARCH-v3.1 night run.

Importing this module is inert. ``install_night_runtime`` only patches one
runner instance; it does not launch Shinka or make model/evaluator calls.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import types
from typing import Any, Callable, Iterator, Mapping


PROTOCOL = "overnight-v1"
STATE_NAME = "night-runtime-state.json"
CLOCK_NAME = "night-clock.json"
FAILURES_NAME = "night-failures.jsonl"
STOP_REQUEST_NAME = "night-stop-request.json"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _locked_state(path: Path) -> Iterator[None]:
    """Cross-process lock shared by the runner and headless bridge requests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name("." + path.name + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _policy_values(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("version") != PROTOCOL:
        raise ValueError(f"night policy must use {PROTOCOL}")
    keys = (
        "target_generations",
        "includes_baseline",
        "max_failed_proposals",
        "max_proposals",
        "max_model_requests",
        "max_consecutive_infrastructure_errors",
        "soft_deadline_seconds",
        "hard_deadline_seconds",
    )
    values = {key: policy.get(key) for key in keys}
    if values["includes_baseline"] is not True:
        raise ValueError("overnight generation target must include generation 0")
    for key in keys:
        if key == "includes_baseline":
            continue
        if type(values[key]) is not int or values[key] <= 0:
            raise ValueError(f"night policy has invalid {key}")
    target = values["target_generations"]
    failed = values["max_failed_proposals"]
    if values["max_proposals"] != target - 1 + failed:
        raise ValueError("max_proposals must equal target generations minus baseline plus failed budget")
    if values["hard_deadline_seconds"] <= values["soft_deadline_seconds"]:
        raise ValueError("hard deadline must follow the soft deadline")
    return values


def _is_infrastructure_failure(stage: str, reason: str, metadata: Any) -> bool:
    """Recognize explicit transport/auth/quota failures; default to candidate."""
    if stage in {"evaluation_submit", "database", "scheduler"}:
        return True
    parts = [reason]
    if isinstance(metadata, Mapping):
        parts.extend(
            str(metadata.get(key) or "")
            for key in ("last_error_msg", "error_attempt", "error_msg")
        )
    message = " ".join(parts).lower()
    candidate_markers = (
        "could not extract code",
        "search text not found",
        "no changes applied",
        "no evolve-block regions found",
        "exact source duplicate",
        "patch_apply_failed",
    )
    if any(marker in message for marker in candidate_markers):
        return False
    infra_markers = (
        "headless query timed out",
        "headless command failed",
        "rate limit",
        "too many requests",
        "429",
        "quota",
        "usage limit",
        "not signed in",
        "unauthorized",
        "http 401",
        "status code 401",
        "authentication failed",
        "connection error",
        "connectionerror",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "timed out",
        "timeout",
        "service unavailable",
        "model not found",
        "invalid model",
        "context length exceeded",
    )
    return any(marker in message for marker in infra_markers)


class NightState:
    """Durable counters and shared wall-clock for one authorized run.

    The manager creates ``night-clock.json`` before starting the worker. Tests
    and local dry runs may omit it; then this object initializes the same clock
    from the supplied policy. Counters are protected across evaluator and
    headless bridge processes with an OS file lock.
    """

    def __init__(
        self,
        run: str | os.PathLike[str],
        policy: Mapping[str, Any],
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.run = Path(run).resolve()
        self.policy = _policy_values(policy)
        self.clock = clock
        self.path = self.run / STATE_NAME
        self.failures_path = self.run / FAILURES_NAME
        self.clock_path = self.run / CLOCK_NAME
        self.stop_request_path = self.run / STOP_REQUEST_NAME
        self._initialize()

    def _clock_values(self) -> dict[str, float]:
        saved = _read_json(self.clock_path)
        if saved is not None:
            started = float(saved["started_at"])
            soft = float(saved["soft_deadline"])
            hard = float(saved["hard_deadline"])
        else:
            env_soft = os.environ.get("PIPES_SEARCH_V31_SOFT_DEADLINE")
            env_hard = os.environ.get("PIPES_SEARCH_V31_HARD_DEADLINE")
            if env_soft is not None and env_hard is not None:
                soft = float(env_soft)
                hard = float(env_hard)
                started = soft - self.policy["soft_deadline_seconds"]
                _atomic_json(
                    self.clock_path,
                    {"started_at": started, "soft_deadline": soft, "hard_deadline": hard},
                )
            else:
                started = self.clock()
                soft = started + self.policy["soft_deadline_seconds"]
                hard = started + self.policy["hard_deadline_seconds"]
                _atomic_json(
                    self.clock_path,
                    {"started_at": started, "soft_deadline": soft, "hard_deadline": hard},
                )
        if not (started < soft < hard):
            raise ValueError("invalid persisted overnight deadline clock")
        return {"started_at": started, "soft_deadline": soft, "hard_deadline": hard}

    def _new_state(self) -> dict[str, Any]:
        return {
            "protocol": PROTOCOL,
            **self.policy,
            **self._clock_values(),
            "proposal_count": 0,
            "failed_proposal_count": 0,
            "model_requests_reserved": 0,
            "consecutive_infrastructure_errors": 0,
            "total_infrastructure_errors": 0,
            "reserved_generations": [],
            "failed_generations": [],
            "successful_proposal_generations": [],
            "next_generation_floor": 1,
            "submissions_stopped": False,
            "stop_reason": None,
            "updated_at": self.clock(),
        }

    def _initialize(self) -> None:
        with _locked_state(self.path):
            state = _read_json(self.path)
            if state is None:
                _atomic_json(self.path, self._new_state())
                return
            if state.get("protocol") != PROTOCOL:
                raise ValueError("existing night runtime state uses another protocol")
            for key, value in self.policy.items():
                if state.get(key) != value:
                    raise ValueError(f"night runtime policy changed across resume: {key}")
            clock = self._clock_values()
            for key, value in clock.items():
                if float(state.get(key, value)) != value:
                    raise ValueError(f"night clock changed across resume: {key}")

    def snapshot(self) -> dict[str, Any]:
        with _locked_state(self.path):
            state = _read_json(self.path)
            if state is None:
                raise RuntimeError("night runtime state disappeared")
            return state

    def _mutate(self, update: Callable[[dict[str, Any]], Any]) -> Any:
        with _locked_state(self.path):
            state = _read_json(self.path)
            if state is None:
                raise RuntimeError("night runtime state disappeared")
            result = update(state)
            state["updated_at"] = self.clock()
            _atomic_json(self.path, state)
            return result

    def _supervisor_alive(self) -> bool:
        raw = os.environ.get("PIPES_SEARCH_V31_SUPERVISOR")
        if not raw:
            return True
        try:
            pid = int(raw)
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False

    def _external_stop_reason(self) -> str | None:
        stop = _read_json(self.stop_request_path)
        if stop is not None:
            return str(stop.get("reason") or "supervisor_stop_request")
        if not self._supervisor_alive():
            return "supervisor_exited"
        return None

    def admission_reason(self, *, now: float | None = None) -> str | None:
        now = self.clock() if now is None else now
        state = self.snapshot()
        external = self._external_stop_reason()
        if external:
            return external
        if now >= state["hard_deadline"]:
            return "hard_deadline"
        if now >= state["soft_deadline"]:
            return "soft_deadline"
        if state["submissions_stopped"]:
            return state.get("stop_reason") or "submissions_stopped"
        if state["proposal_count"] >= state["max_proposals"]:
            return "proposal_budget"
        if state["failed_proposal_count"] >= state["max_failed_proposals"]:
            return "failed_proposal_budget"
        if state["model_requests_reserved"] >= state["max_model_requests"]:
            return "model_request_budget"
        if state["consecutive_infrastructure_errors"] >= state["max_consecutive_infrastructure_errors"]:
            return "infrastructure_error_limit"
        return None

    def request_stop(self, reason: str) -> None:
        def update(state: dict[str, Any]) -> None:
            state["submissions_stopped"] = True
            if not state.get("stop_reason"):
                state["stop_reason"] = reason

        self._mutate(update)

    def reserve_proposals(self, generations: list[int]) -> None:
        if not generations:
            return

        def update(state: dict[str, Any]) -> None:
            if state["proposal_count"] + len(generations) > state["max_proposals"]:
                raise RuntimeError("night proposal budget exhausted")
            already = set(state["reserved_generations"])
            if any(generation in already for generation in generations):
                raise RuntimeError("night runtime attempted to reuse a generation ID")
            state["proposal_count"] += len(generations)
            state["reserved_generations"].extend(generations)
            state["next_generation_floor"] = max(
                state["next_generation_floor"], max(generations) + 1
            )

        self._mutate(update)

    def record_failed_proposal(self, event: Mapping[str, Any]) -> dict[str, Any]:
        event_value = {
            "timestamp": self.clock(),
            "generation": int(event["generation"]),
            "failure_stage": str(event.get("failure_stage") or "unknown"),
            "failure_reason": str(event.get("failure_reason") or "")[:4000],
            "classification": "infrastructure" if event.get("infrastructure") else "candidate_or_search",
        }

        # Shinka's native attempt_log/failure.json remain the primary durable
        # record. This append-only summary makes night budgets auditable.
        with _locked_state(self.path):
            state = _read_json(self.path)
            if state is None:
                raise RuntimeError("night runtime state disappeared")
            failed_generations = set(state.get("failed_generations", []))
            if event_value["generation"] in failed_generations:
                return dict(state)
            if state["failed_proposal_count"] >= state["max_failed_proposals"]:
                raise RuntimeError("night failed-proposal budget exceeded")
            state["failed_proposal_count"] += 1
            failed_generations.add(event_value["generation"])
            state["failed_generations"] = sorted(failed_generations)
            state["next_generation_floor"] = max(
                state["next_generation_floor"], event_value["generation"] + 1
            )
            if event.get("infrastructure"):
                state["total_infrastructure_errors"] += 1
                state["consecutive_infrastructure_errors"] += 1
                if state["consecutive_infrastructure_errors"] >= state["max_consecutive_infrastructure_errors"]:
                    state["submissions_stopped"] = True
                    state["stop_reason"] = "infrastructure_error_limit"
            else:
                state["consecutive_infrastructure_errors"] = 0
            if state["failed_proposal_count"] >= state["max_failed_proposals"]:
                state["submissions_stopped"] = True
                state["stop_reason"] = "failed_proposal_budget"
            state["updated_at"] = self.clock()
            _atomic_json(self.path, state)
            with self.failures_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event_value, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return dict(state)

    def record_successful_proposal(self, generation: int) -> None:
        """Mark a proposal accepted for evaluation and break infra-error streak."""
        def update(state: dict[str, Any]) -> None:
            successful = set(state.get("successful_proposal_generations", []))
            successful.add(int(generation))
            state["successful_proposal_generations"] = sorted(successful)
            state["consecutive_infrastructure_errors"] = 0

        self._mutate(update)

    def reconcile_generation_sets(
        self,
        *,
        persisted_generations: set[int],
        failed_generations: set[int],
    ) -> list[int]:
        """Merge SQLite and journal evidence, returning proposals interrupted by restart."""
        interrupted: list[int] = []

        def update(state: dict[str, Any]) -> None:
            nonlocal interrupted
            reserved = set(map(int, state.get("reserved_generations", [])))
            failed = set(map(int, state.get("failed_generations", []))) | failed_generations
            # A submitted evaluator job is not completion evidence until its
            # Program row is durable. Killed jobs therefore become failures.
            successful = persisted_generations - {0}
            interrupted = sorted(reserved - failed - persisted_generations)
            attempted = reserved | failed | successful
            state["reserved_generations"] = sorted(attempted)
            state["failed_generations"] = sorted(failed)
            state["successful_proposal_generations"] = sorted(successful)
            state["proposal_count"] = max(state["proposal_count"], len(attempted))
            state["failed_proposal_count"] = max(
                state["failed_proposal_count"], len(failed)
            )
            if attempted:
                state["next_generation_floor"] = max(
                    state["next_generation_floor"], max(attempted) + 1
                )

        self._mutate(update)
        return interrupted

    def reserve_model_request(self, *, now: float | None = None) -> int:
        now = self.clock() if now is None else now
        with _locked_state(self.path):
            state = _read_json(self.path)
            if state is None:
                raise RuntimeError("night runtime state disappeared")
            external = self._external_stop_reason()
            reason = external
            if reason is None and now >= state["hard_deadline"]:
                reason = "hard_deadline"
            if reason is None and now >= state["soft_deadline"]:
                reason = "soft_deadline"
            if reason is None and state["submissions_stopped"]:
                reason = state.get("stop_reason") or "submissions_stopped"
            if reason is None and state["model_requests_reserved"] >= state["max_model_requests"]:
                reason = "model_request_budget"
            if reason is not None:
                state["submissions_stopped"] = True
                if not state.get("stop_reason"):
                    state["stop_reason"] = reason
                state["updated_at"] = self.clock()
                _atomic_json(self.path, state)
                raise RuntimeError(f"night run does not admit another model request: {reason}")
            state["model_requests_reserved"] += 1
            state["updated_at"] = self.clock()
            _atomic_json(self.path, state)
            return state["model_requests_reserved"]

    def mark_deadline_stop(self) -> str | None:
        now = self.clock()
        state = self.snapshot()
        external = self._external_stop_reason()
        if external:
            self.request_stop(external)
            return external
        if now >= state["hard_deadline"]:
            self.request_stop("hard_deadline")
            return "hard_deadline"
        if now >= state["soft_deadline"]:
            self.request_stop("soft_deadline")
            return "soft_deadline"
        return None

    def reconcile_runner(self, runner: Any) -> None:
        """Restore monotone generation IDs after Shinka reopens the SQLite DB."""
        state = self.snapshot()
        runner.next_generation_to_submit = max(
            int(getattr(runner, "next_generation_to_submit", 1)),
            int(state["next_generation_floor"]),
        )

    def id_ceiling(self) -> int:
        """Exclusive native generation-ID ceiling, including baseline slot 0."""
        state = self.snapshot()
        return min(
            state["target_generations"] + state["failed_proposal_count"],
            state["target_generations"] + state["max_failed_proposals"],
        )


def reserve_model_request(
    run: str | os.PathLike[str],
    *,
    policy: Mapping[str, Any] | None = None,
    limit: int | None = None,
    clock: Callable[[], float] = time.time,
) -> int:
    """Durably reserve one model request before calling the subscription bridge.

    The headless bridge should call this once per actual provider request. A
    denied reservation raises before any request is sent.
    """
    if policy is None:
        policy_path = Path(run).resolve().parent / "night-policy.json"
        if not policy_path.exists():
            # Run folders live under ``runs/``; the policy is two levels up.
            policy_path = Path(run).resolve().parent.parent / "night-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    state = NightState(run, policy, clock=clock)
    if limit is not None and limit != state.policy["max_model_requests"]:
        raise ValueError("model request limit must match the pinned night policy")
    return state.reserve_model_request()


def install_night_runtime(
    runner: Any,
    run: str | os.PathLike[str],
    policy: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.time,
    sleep: Callable[[float], Any] = asyncio.sleep,
) -> NightState:
    """Install bounded runtime behavior on this Shinka runner object only."""
    if getattr(runner, "_pipes_night_runtime_installed", False):
        return runner._pipes_night_state
    state = NightState(run, policy, clock=clock)
    runner._pipes_night_state = state
    runner._pipes_night_target = state.policy["target_generations"]

    original_count = runner._count_completed_generations_from_db

    async def count_completed(self):
        # Shinka's native count subtracts num_islands-1 copies, which becomes
        # wrong after dynamic island creation or when resuming a larger swarm.
        # Count distinct real generation IDs instead, excluding tagged copies.
        try:
            cursor = self.db.cursor
            cursor.execute(
                """SELECT DISTINCT generation FROM programs
                   WHERE COALESCE(CASE WHEN json_valid(metadata)
                     THEN json_extract(metadata, '$._is_island_copy') ELSE 0 END, 0) != 1
                     AND COALESCE(CASE WHEN json_valid(metadata)
                     THEN json_extract(metadata, '$._spawned_island') ELSE 0 END, 0) != 1"""
            )
            generations = {int(row[0]) for row in cursor.fetchall()}
            return min(len(generations), state.policy["target_generations"])
        except (AttributeError, sqlite3.Error):
            # During unusual setup paths before SQLite is attached, preserve the
            # pinned implementation; setup reconciliation will still guard IDs.
            return await original_count()

    runner._count_completed_generations_from_db = types.MethodType(count_completed, runner)

    original_setup = runner._setup_async

    async def setup(self, *args, **kwargs):
        result = await original_setup(*args, **kwargs)
        # Reconcile the run journal against real SQLite rows. Island copies do
        # not count as evaluations; unresolved reserved IDs mean the worker was
        # interrupted before terminal logging and are charged as infra failures.
        try:
            cursor = self.db.cursor
            cursor.execute(
                """SELECT DISTINCT generation FROM programs
                   WHERE COALESCE(CASE WHEN json_valid(metadata)
                     THEN json_extract(metadata, '$._is_island_copy') ELSE 0 END, 0) != 1
                     AND COALESCE(CASE WHEN json_valid(metadata)
                     THEN json_extract(metadata, '$._spawned_island') ELSE 0 END, 0) != 1"""
            )
            persisted_generations = {int(row[0]) for row in cursor.fetchall()}
            cursor.execute(
                """SELECT DISTINCT generation FROM attempt_log
                   WHERE status='failed' AND json_valid(details)
                     AND json_extract(details, '$.node_kind')='failed_proposal'"""
            )
            failure_generations = {int(row[0]) for row in cursor.fetchall()}
            interrupted = state.reconcile_generation_sets(
                persisted_generations=persisted_generations,
                failed_generations=failure_generations,
            )
            for generation in interrupted:
                state.record_failed_proposal(
                    {
                        "generation": generation,
                        "failure_stage": "interrupted_proposal_on_resume",
                        "failure_reason": "worker stopped before this proposal was evaluated or terminally recorded",
                        "infrastructure": True,
                    }
                )
        except Exception as exc:
            # Recovery ambiguity is an infrastructure error: stop after the
            # current work drains rather than risk reusing a failed generation.
            state.request_stop("resume_reconciliation_error")
            state._mutate(
                lambda raw: raw.update(
                    total_infrastructure_errors=raw["total_infrastructure_errors"] + 1,
                    consecutive_infrastructure_errors=raw["consecutive_infrastructure_errors"] + 1,
                )
            )
            runner._pipes_night_reconcile_error = repr(exc)
        state.reconcile_runner(self)
        return result

    runner._setup_async = types.MethodType(setup, runner)

    original_start = runner._start_proposals

    async def start(self, requested: int):
        reason = state.admission_reason(now=clock())
        if reason is not None:
            state.request_stop(reason)
            return await original_start(0)
        active = len(self.active_proposal_tasks)
        in_flight = self._get_in_flight_work_count()
        logical_remaining = max(
            0,
            state.policy["target_generations"]
            - int(self.completed_generations)
            - int(in_flight),
        )
        saved = state.snapshot()
        failed_slots = max(
            0,
            saved["max_failed_proposals"]
            - saved["failed_proposal_count"]
            - active,
        )
        proposal_slots = max(0, saved["max_proposals"] - saved["proposal_count"])
        generation_slots = max(0, state.id_ceiling() - self.next_generation_to_submit)
        free_concurrency = max(0, int(self.max_proposal_jobs) - active)
        count = min(
            max(0, int(requested)),
            logical_remaining,
            failed_slots,
            proposal_slots,
            generation_slots,
            free_concurrency,
        )
        if count <= 0:
            return await original_start(0)

        generations = list(
            range(self.next_generation_to_submit, self.next_generation_to_submit + count)
        )
        state.reserve_proposals(generations)
        # Upstream _start_proposals uses this one value both as an ID ceiling
        # and an evaluated target. Temporarily widen it only while assigning
        # IDs; all completion checks continue to see the logical target.
        logical_target = self.evo_config.num_generations
        self.evo_config.num_generations = state.id_ceiling()
        try:
            return await original_start(count)
        finally:
            self.evo_config.num_generations = logical_target

    runner._start_proposals = types.MethodType(start, runner)

    def remaining_slots(self):
        # Keep coordinator's native no-slots finalization path, but give each
        # terminal failure one fresh immutable generation ID.
        if state.admission_reason(now=clock()) is not None:
            return 0
        saved = state.snapshot()
        return min(
            max(0, state.id_ceiling() - self.next_generation_to_submit),
            max(0, saved["max_proposals"] - saved["proposal_count"]),
            max(0, saved["max_failed_proposals"] - saved["failed_proposal_count"] - len(self.active_proposal_tasks)),
        )

    runner._get_remaining_generation_slots = types.MethodType(remaining_slots, runner)

    def remaining_completed(self):
        return max(
            0,
            state.policy["target_generations"]
            - int(self.completed_generations)
            - int(self._get_in_flight_work_count()),
        )

    runner._get_remaining_completed_work = types.MethodType(remaining_completed, runner)

    original_generate = runner._generate_proposal_async

    async def generate(self, generation: int, task_id: str):
        try:
            result = await original_generate(generation, task_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.record_failed_proposal(
                {
                    "generation": generation,
                    "failure_stage": "unhandled_proposal_exception",
                    "failure_reason": repr(exc),
                    "infrastructure": True,
                }
            )
            return None
        if result is not None:
            state.record_successful_proposal(generation)
            return result
        saved = state.snapshot()
        if generation not in set(saved.get("failed_generations", [])):
            # Upstream catches some exceptions and returns None without calling
            # its terminal failure hook. Treat this unclassified hole as infra.
            state.record_failed_proposal(
                {
                    "generation": generation,
                    "failure_stage": "unrecorded_proposal_failure",
                    "failure_reason": "proposal returned without an evaluation job or terminal failure record",
                    "infrastructure": True,
                }
            )
        return None

    runner._generate_proposal_async = types.MethodType(generate, runner)

    original_terminal = runner._record_terminal_failed_proposal

    async def record_failure(self, **kwargs):
        repair_stop_installed = bool(getattr(self, "_search_v2_repair_installed", False))
        try:
            await original_terminal(**kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.record_failed_proposal(
                {
                    "generation": kwargs.get("generation", 0),
                    "failure_stage": kwargs.get("failure_stage"),
                    "failure_reason": f"terminal failure persistence failed: {exc!r}",
                    "infrastructure": True,
                }
            )
            state.request_stop("terminal_failure_persistence_error")
            if repair_stop_installed:
                self._search_v2_repair_stop = None
                self.should_stop.clear()
                self.finalization_complete.clear()
            raise
        stage = str(kwargs.get("failure_stage") or "")
        metadata = kwargs.get("meta_patch_data") or {}
        reason = str(kwargs.get("failure_reason") or "")
        infrastructure = _is_infrastructure_failure(stage, reason, metadata)
        after = state.record_failed_proposal(
            {
                "generation": kwargs["generation"],
                "failure_stage": stage,
                "failure_reason": kwargs.get("failure_reason"),
                "infrastructure": infrastructure,
            }
        )
        if repair_stop_installed:
            # SEARCH-v2's old wrapper sets stop immediately after logging. Its
            # diagnostics are superseded here; overnight mode drains instead.
            self._search_v2_repair_stop = None
            self.should_stop.clear()
            self.finalization_complete.clear()
        if after["submissions_stopped"]:
            self.slot_available.set()
        return None

    runner._record_terminal_failed_proposal = types.MethodType(record_failure, runner)

    original_run = runner._run_async

    async def run(self, *args, **kwargs):
        watcher = asyncio.create_task(_watch_run(self, state, clock=clock, sleep=sleep))
        try:
            return await original_run(*args, **kwargs)
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)

    runner._run_async = types.MethodType(run, runner)
    runner._pipes_night_runtime_installed = True
    return state


async def _watch_run(
    runner: Any,
    state: NightState,
    *,
    clock: Callable[[], float],
    sleep: Callable[[float], Any],
) -> None:
    """Stop intake at soft deadline and let Shinka drain; manager owns hard kill."""
    while True:
        reason = state.mark_deadline_stop()
        if reason is None:
            reason = state.admission_reason(now=clock())
            if reason in {"proposal_budget", "failed_proposal_budget", "model_request_budget", "infrastructure_error_limit"}:
                state.request_stop(reason)
        snapshot = state.snapshot()
        if reason is not None or snapshot["submissions_stopped"]:
            state.request_stop(reason or snapshot.get("stop_reason") or "stopped")
            # Hard deadline is externally enforced by night_manager's process
            # tree supervisor. The runner event is only a last-resort wakeup.
            if reason == "hard_deadline" or reason == "hard_deadline_supervisor_request":
                runner.should_stop.set()
                runner.slot_available.set()
                runner.finalization_complete.set()
                return
            if runner._get_in_flight_work_count() == 0:
                if getattr(runner, "failed_jobs_for_retry", None):
                    try:
                        await runner._retry_failed_db_jobs()
                    except Exception:
                        pass
                runner.should_stop.set()
                runner.slot_available.set()
                runner.finalization_complete.set()
                return
        await sleep(1.0)

