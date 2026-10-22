"""Run-local, completed-evaluation island control for SEARCH-v3.1.

This adapter patches one AsyncProgramDatabase instance. It does not change the
installed Shinka package. Native generation-based island triggers are disabled
on that runner instance; spawning and migration are scheduled from distinct,
persisted evaluated generation IDs instead.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import types
from typing import Any

from shinka.database import ProgramDatabase


VERSION = "search-v31-completed-islands-v1"
STATE_KEY = "pipes_search_v31_island_runtime_v1"
logger = logging.getLogger(__name__)


def _native_worker_count(executor: Any) -> int | None:
    return getattr(executor, "_max_workers", None)


def _is_copy(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("_is_island_copy") or metadata.get("_spawned_island"))


def _json_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _island_indices(db: ProgramDatabase) -> list[int]:
    db.cursor.execute(
        "SELECT DISTINCT island_idx FROM programs WHERE island_idx IS NOT NULL ORDER BY island_idx"
    )
    return [int(row[0]) for row in db.cursor.fetchall()]


def _validated_island_count(indices: list[int]) -> int:
    if not indices:
        return 0
    expected = list(range(indices[-1] + 1))
    if indices != expected:
        raise ValueError(f"island indices must be contiguous from 0; found {indices}")
    return len(indices)


def _save_state(db: ProgramDatabase, state: dict[str, Any]) -> None:
    db._update_metadata_in_db(STATE_KEY, json.dumps(state, sort_keys=True))


def _load_state(db: ProgramDatabase) -> dict[str, Any] | None:
    db.cursor.execute("SELECT value FROM metadata_store WHERE key = ?", (STATE_KEY,))
    row = db.cursor.fetchone()
    if not row or not row[0]:
        return None
    try:
        state = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("stored island runtime state is invalid JSON") from exc
    if not isinstance(state, dict) or state.get("version") != VERSION:
        raise ValueError("stored island runtime state has an unknown version")
    return state


def _evaluated_rows(db: ProgramDatabase) -> list[dict[str, Any]]:
    db.cursor.execute(
        """SELECT id, generation, correct, combined_score, island_idx, metadata
           FROM programs ORDER BY timestamp, generation, id"""
    )
    rows = []
    for raw in db.cursor.fetchall():
        row = dict(raw)
        metadata = _json_metadata(row.get("metadata"))
        generation = int(row["generation"])
        if generation < 0 or _is_copy(metadata):
            continue
        row["metadata_dict"] = metadata
        rows.append(row)
    return rows


def _rebuild_state(db: ProgramDatabase, policy: dict[str, Any]) -> dict[str, Any]:
    """Recover counts from persisted evaluated rows if this hook is first installed."""
    rows = _evaluated_rows(db)
    processed: list[int] = []
    best_score = None
    best_at = 0
    for row in rows:
        generation = int(row["generation"])
        if generation in processed:
            continue
        processed.append(generation)
        score = row.get("combined_score")
        if row.get("correct") and isinstance(score, (int, float)) and math.isfinite(score):
            if best_score is None or float(score) > best_score:
                best_score = float(score)
                best_at = len(processed)

    island_count = _validated_island_count(_island_indices(db))
    return {
        "version": VERSION,
        "policy": policy,
        "processed_generations": processed,
        "completed_evaluations": len(processed),
        "best_score": best_score,
        "last_best_evaluation": best_at,
        "last_migration_evaluation": 0,
        "last_spawn_evaluation": 0,
        "island_count": island_count,
        "pending_action": None,
    }


def _read_or_rebuild_state(db: ProgramDatabase, policy: dict[str, Any]) -> dict[str, Any]:
    state = _load_state(db)
    if state is None:
        state = _rebuild_state(db, policy)
        _save_state(db, state)
        return state
    if state.get("policy") != policy:
        raise ValueError("island runtime policy differs from the persisted run policy")
    # SQLite rows are authoritative if a process stopped after committing a
    # spawn but before the state record was updated.
    actual_count = _validated_island_count(_island_indices(db))
    if actual_count > int(state.get("island_count", 0)):
        state["island_count"] = actual_count
    return state


def _set_config_island_count(db: ProgramDatabase, count: int) -> None:
    db.config.num_islands = count
    if db.island_manager is not None:
        db.island_manager.config = db.config
        db.island_manager.assignment_strategy.config = db.config
        db.island_manager.migration_strategy.config = db.config
    if db.island_sampler is not None:
        db.island_sampler.config = db.config


def _has_migration_event(db: ProgramDatabase, completed_count: int) -> bool:
    db.cursor.execute("SELECT migration_history FROM programs")
    for row in db.cursor.fetchall():
        raw = row[0]
        if not raw:
            continue
        try:
            history = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if any(
            isinstance(event, dict)
            and event.get("generation") == completed_count
            and "from" in event
            and "to" in event
            for event in history
        ):
            return True
    return False


class IslandRuntime:
    """Stateful controller; methods that touch SQLite run on the writer lane."""

    def __init__(
        self,
        *,
        initial_islands: int = 2,
        max_islands: int = 6,
        stagnation_evaluations: int = 12,
        migration_evaluations: int = 8,
        migration_rate: float = 0.1,
        island_elitism: bool = True,
        spawn_strategy: str = "archive_random",
    ):
        if type(initial_islands) is not int or initial_islands < 2:
            raise ValueError("initial_islands must be an integer >= 2")
        if type(max_islands) is not int or max_islands < initial_islands:
            raise ValueError("max_islands must be an integer >= initial_islands")
        if type(stagnation_evaluations) is not int or stagnation_evaluations < 1:
            raise ValueError("stagnation_evaluations must be a positive integer")
        if type(migration_evaluations) is not int or migration_evaluations < 1:
            raise ValueError("migration_evaluations must be a positive integer")
        if not isinstance(migration_rate, (int, float)) or not 0 < migration_rate <= 1:
            raise ValueError("migration_rate must be in (0, 1]")
        if type(island_elitism) is not bool:
            raise ValueError("island_elitism must be boolean")
        if spawn_strategy not in {"archive_random", "best", "initial"}:
            raise ValueError("unsupported Shinka island spawn strategy")

        self.policy = {
            "initial_islands": initial_islands,
            "max_islands": max_islands,
            "stagnation_evaluations": stagnation_evaluations,
            "migration_evaluations": migration_evaluations,
            "migration_rate": float(migration_rate),
            "island_elitism": island_elitism,
            "spawn_strategy": spawn_strategy,
        }
        self.state: dict[str, Any] | None = None

    def restore(self, db: ProgramDatabase) -> dict[str, Any]:
        state = _read_or_rebuild_state(db, self.policy)
        count = _validated_island_count(_island_indices(db))
        if count < self.policy["initial_islands"]:
            raise ValueError(
                f"expected at least {self.policy['initial_islands']} initialized islands; found {count}"
            )
        if count > self.policy["max_islands"]:
            raise ValueError("persisted island count exceeds the configured maximum")
        state["island_count"] = count
        _set_config_island_count(db, count)
        _save_state(db, state)
        self.state = state
        return state

    def process_completed(self, db: ProgramDatabase, program_id: str) -> dict[str, Any]:
        state = _read_or_rebuild_state(db, self.policy)
        actual_count = _validated_island_count(_island_indices(db))
        if actual_count < self.policy["initial_islands"]:
            raise ValueError("fewer initialized islands than configured")
        if actual_count > self.policy["max_islands"]:
            raise ValueError("actual island count exceeds the configured maximum")
        state["island_count"] = actual_count
        _set_config_island_count(db, actual_count)

        # Recover a spawn or migration that may have committed just before an
        # interrupted process stopped. The pending intent was persisted first.
        state = self._recover_pending_action(db, state)

        db.cursor.execute(
            "SELECT generation, correct, combined_score, metadata FROM programs WHERE id = ?",
            (program_id,),
        )
        row = db.cursor.fetchone()
        if row is None:
            raise ValueError("completed program is missing from the Shinka database")
        metadata = _json_metadata(row["metadata"])
        generation = int(row["generation"])
        if generation < 0 or _is_copy(metadata):
            self.state = state
            return state

        processed = [int(g) for g in state["processed_generations"]]
        if generation not in processed:
            processed.append(generation)
            state["processed_generations"] = processed
            state["completed_evaluations"] = len(processed)
            score = row["combined_score"]
            if row["correct"] and isinstance(score, (int, float)) and math.isfinite(score):
                current_best = state.get("best_score")
                if current_best is None or float(score) > float(current_best):
                    state["best_score"] = float(score)
                    state["last_best_evaluation"] = len(processed)
            # Persist counting before any spawn/migration side effect. Replay
            # after restart sees this generation and cannot count it twice.
            _save_state(db, state)

        count = int(state["completed_evaluations"])
        # A spawn starts a fresh search window even if the prior best is much
        # older. Keep the best-improvement timestamp intact for diagnostics,
        # and anchor the next spawn to whichever happened more recently.
        stagnation_anchor = max(
            int(state.get("last_best_evaluation", 0)),
            int(state.get("last_spawn_evaluation", 0)),
        )
        evaluations_since_activity = count - stagnation_anchor
        if (
            evaluations_since_activity >= self.policy["stagnation_evaluations"]
            and actual_count < self.policy["max_islands"]
        ):
            next_idx = max(_island_indices(db), default=-1) + 1
            state["pending_action"] = {"kind": "spawn", "island_idx": next_idx}
            _save_state(db, state)
            state = self._recover_pending_action(db, state)

        count = int(state["completed_evaluations"])
        if count - int(state.get("last_migration_evaluation", 0)) >= self.policy[
            "migration_evaluations"
        ]:
            state["pending_action"] = {"kind": "migration", "completed_count": count}
            _save_state(db, state)
            state = self._recover_pending_action(db, state)

        self.state = state
        return state

    def _recover_pending_action(
        self, db: ProgramDatabase, state: dict[str, Any]
    ) -> dict[str, Any]:
        action = state.get("pending_action")
        if not isinstance(action, dict):
            return state
        kind = action.get("kind")
        actual = _validated_island_count(_island_indices(db))
        _set_config_island_count(db, actual)

        if kind == "spawn":
            target_idx = int(action["island_idx"])
            if actual > target_idx:
                spawned = True  # Recover after DB commit, before state commit.
            elif actual >= self.policy["max_islands"]:
                spawned = False
            else:
                db.config.island_spawn_strategy = self.policy["spawn_strategy"]
                spawned = db.island_manager.spawn_new_island()
                actual = _validated_island_count(_island_indices(db))
            if spawned:
                if actual != target_idx + 1:
                    raise ValueError("spawned island index does not match pending intent")
                state["island_count"] = actual
                state["last_spawn_evaluation"] = int(state["completed_evaluations"])
            state["pending_action"] = None
            _set_config_island_count(db, actual)
            _save_state(db, state)
            return state

        if kind == "migration":
            completed_count = int(action["completed_count"])
            if not _has_migration_event(db, completed_count):
                _set_config_island_count(db, actual)
                db.config.migration_rate = self.policy["migration_rate"]
                db.config.island_elitism = self.policy["island_elitism"]
                try:
                    db.island_manager.perform_migration(completed_count)
                finally:
                    # `migration_interval=0` prevents Shinka's native
                    # generation-based scheduler from duplicating this move.
                    db.config.migration_rate = 0.0
            state["last_migration_evaluation"] = completed_count
            state["pending_action"] = None
            _save_state(db, state)
            return state

        raise ValueError(f"unknown pending island operation {kind!r}")


def install_island_runtime(
    async_db: Any,
    *,
    initial_islands: int = 2,
    max_islands: int = 6,
    stagnation_evaluations: int = 12,
    migration_evaluations: int = 8,
    migration_rate: float = 0.1,
    island_elitism: bool = True,
    spawn_strategy: str = "archive_random",
) -> IslandRuntime:
    """Install completed-evaluation island control on one async DB instance.

    Call after AsyncProgramDatabase initialization and before the first sample.
    One read/write database worker is required so the hook's state transitions
    cannot race Shinka's program insertions or sampling.
    """
    if getattr(async_db, "_pipes_island_runtime_installed", False):
        runtime = async_db._pipes_island_runtime
        if runtime.policy != {
            "initial_islands": initial_islands,
            "max_islands": max_islands,
            "stagnation_evaluations": stagnation_evaluations,
            "migration_evaluations": migration_evaluations,
            "migration_rate": float(migration_rate),
            "island_elitism": island_elitism,
            "spawn_strategy": spawn_strategy,
        }:
            raise ValueError("island runtime is already installed with another policy")
        return runtime

    if _native_worker_count(getattr(async_db, "executor", None)) != 1 or _native_worker_count(
        getattr(async_db, "write_executor", None)
    ) != 1:
        raise ValueError("completed-evaluation island runtime requires one DB worker")

    runtime = IslandRuntime(
        initial_islands=initial_islands,
        max_islands=max_islands,
        stagnation_evaluations=stagnation_evaluations,
        migration_evaluations=migration_evaluations,
        migration_rate=migration_rate,
        island_elitism=island_elitism,
        spawn_strategy=spawn_strategy,
    )

    # Suppress native generation-modulo operations for every worker connection
    # created from this shared config. The local controller below invokes the
    # same Shinka operations at completed-evaluation boundaries.
    config = async_db.sync_db.config
    config.enable_dynamic_islands = False
    config.migration_interval = 0
    config.num_islands = max(int(getattr(config, "num_islands", 0)), initial_islands)
    config.island_spawn_strategy = spawn_strategy
    state = runtime.restore(async_db.sync_db)

    original_maintenance = async_db.run_program_maintenance_async
    lock = asyncio.Lock()

    async def maintenance(self, program, verbose=False, recompute_embeddings=False):
        async with lock:
            semaphore = getattr(self, "_db_semaphore", None)
            if semaphore is None:
                raise ValueError("AsyncProgramDatabase has no serialized DB semaphore")
            async with semaphore:
                await original_maintenance(
                    program,
                    verbose=verbose,
                    recompute_embeddings=recompute_embeddings,
                )
                loop = asyncio.get_running_loop()

                def process():
                    local_db = ProgramDatabase(
                        self.sync_db.config,
                        embedding_model=self.sync_db.embedding_model,
                    )
                    try:
                        return runtime.process_completed(local_db, program.id)
                    finally:
                        local_db.close()

                state_after = await loop.run_in_executor(self.write_executor, process)
                runtime.state = state_after
                self.sync_db.config.num_islands = int(state_after["island_count"])

    async_db.run_program_maintenance_async = types.MethodType(maintenance, async_db)
    async_db._pipes_island_runtime = runtime
    async_db._pipes_island_runtime_installed = True
    runtime.state = state
    return runtime


def current_island_count(async_db: Any) -> int:
    """Return the restored/current island count for selection hooks."""
    runtime = getattr(async_db, "_pipes_island_runtime", None)
    if runtime is not None and runtime.state is not None:
        return int(runtime.state["island_count"])
    return int(async_db.sync_db.config.num_islands)


def runtime_state(async_db: Any) -> dict[str, Any]:
    """Return a defensive copy of this runner's last persisted runtime state."""
    runtime = getattr(async_db, "_pipes_island_runtime", None)
    if runtime is None or runtime.state is None:
        raise ValueError("island runtime is not installed/restored")
    return json.loads(json.dumps(runtime.state))

