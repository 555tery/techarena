"""Temporary SQLite fixtures for completed-evaluation island control.

These tests use Shinka's real ProgramDatabase and synthetic Program rows. They
do not invoke a model, compiler, evaluator, solver, or benchmark input.
"""

import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from shinka.database.async_dbase import AsyncProgramDatabase
from shinka.database.dbase import DatabaseConfig, Program, ProgramDatabase

import islands_runtime as runtime


def open_db(path: Path, *, islands=2):
    config = DatabaseConfig(
        db_path=str(path),
        num_islands=islands,
        archive_size=30,
        enable_dynamic_islands=True,
        stagnation_threshold=100,
        migration_interval=8,
        migration_rate=0.1,
        island_elitism=True,
        island_spawn_strategy="archive_random",
        enforce_island_separation=True,
    )
    return ProgramDatabase(config)


def make_program(generation, *, parent=None, score=0.5, correct=True, code=None):
    return Program(
        id=f"fixture-{generation}",
        code=code or f"int fixture_{generation}() {{ return {generation}; }}",
        language="cpp",
        parent_id=parent,
        generation=generation,
        combined_score=score,
        correct=correct,
        complexity=1.0,
        metadata={"fixture": True},
    )


def install(db, *, max_islands=10, stagnation=12, migration=8):
    async_db = AsyncProgramDatabase(db, max_workers=1)
    adapter = runtime.install_island_runtime(
        async_db,
        initial_islands=2,
        max_islands=max_islands,
        stagnation_evaluations=stagnation,
        migration_evaluations=migration,
        migration_rate=0.1,
        island_elitism=True,
        spawn_strategy="archive_random",
    )
    return async_db, adapter


def close_async_db(async_db):
    async_db.executor.shutdown(wait=True)
    async_db.write_executor.shutdown(wait=True)


def add_candidate(db, generation, *, parent, score, correct=True):
    program = make_program(generation, parent=parent, score=score, correct=correct)
    db.add(program, defer_maintenance=True)
    return program


async def maintain(async_db, program):
    await async_db.run_program_maintenance_async(program)


class IslandRuntimeTests(unittest.TestCase):
    def test_dynamic_spawning_respects_cap_and_counts_baseline_once(self):
        with tempfile.TemporaryDirectory() as directory:
            db = open_db(Path(directory) / "programs.sqlite")
            baseline = make_program(0, score=0.9)
            db.add(baseline)
            async_db, adapter = install(db, max_islands=3, stagnation=2, migration=100)

            async def run():
                for generation, score in ((1, 0.95), (2, 0.8), (3, 0.7)):
                    program = add_candidate(db, generation, parent=baseline.id, score=score)
                    await maintain(async_db, program)

                # Generation 3 reaches two completed evaluations after the
                # last improvement and creates exactly one new island.
                self.assertEqual(runtime.current_island_count(async_db), 3)
                state = runtime.runtime_state(async_db)
                self.assertEqual(state["completed_evaluations"], 4)  # gen0 baseline + gen1..3
                self.assertEqual(state["processed_generations"], [0, 1, 2, 3])

                for generation in range(4, 9):
                    program = add_candidate(
                        db, generation, parent=baseline.id, score=0.6 - generation / 100
                    )
                    await maintain(async_db, program)
                self.assertEqual(runtime.current_island_count(async_db), 3)
                db.cursor.execute("SELECT DISTINCT island_idx FROM programs ORDER BY island_idx")
                self.assertEqual([row[0] for row in db.cursor.fetchall()], [0, 1, 2])

            try:
                asyncio.run(run())
            finally:
                close_async_db(async_db)
                db.close()

    def test_new_island_migrates_candidates_and_keeps_its_leader(self):
        with tempfile.TemporaryDirectory() as directory:
            db = open_db(Path(directory) / "programs.sqlite")
            baseline = make_program(0, score=0.9)
            db.add(baseline)
            db.cursor.execute(
                "SELECT id FROM programs WHERE generation=0 AND island_idx=1 ORDER BY timestamp LIMIT 1"
            )
            island_one_seed = db.cursor.fetchone()[0]
            async_db, _ = install(db, max_islands=4, stagnation=2, migration=8)

            async def run():
                for generation, parent, score in (
                    (1, baseline.id, 0.95),
                    (2, island_one_seed, 0.72),
                    (3, baseline.id, 0.65),
                ):
                    program = add_candidate(db, generation, parent=parent, score=score)
                    await maintain(async_db, program)

                self.assertEqual(runtime.current_island_count(async_db), 3)
                db.cursor.execute(
                    "SELECT id FROM programs WHERE island_idx=2 ORDER BY timestamp DESC LIMIT 1"
                )
                island_two_seed = db.cursor.fetchone()[0]
                for generation, score in ((4, 0.70), (5, 0.75), (6, 0.80), (7, 0.99)):
                    program = add_candidate(
                        db, generation, parent=island_two_seed, score=score
                    )
                    if generation == 7:
                        # Keep earlier islands from sending a migrant into I2
                        # before its source turn. This isolates the property
                        # under test from random destination collisions.
                        with patch(
                            "shinka.database.islands.random.choice",
                            side_effect=lambda options: options[0],
                        ):
                            await maintain(async_db, program)
                    else:
                        await maintain(async_db, program)

                state = runtime.runtime_state(async_db)
                self.assertEqual(state["completed_evaluations"], 8)
                # Migration was invoked with all active islands. At
                # least one eligible generation>0 program leaves island 2.
                db.cursor.execute("SELECT id, island_idx, migration_history FROM programs")
                moved_from_two = []
                for row in db.cursor.fetchall():
                    history = json.loads(row["migration_history"] or "[]")
                    if any(event.get("from") == 2 and event.get("generation") == 8 for event in history):
                        moved_from_two.append(row["id"])
                self.assertTrue(moved_from_two)

                # The best evaluated program on island 2 is protected by
                # Shinka's elitist migration policy.
                db.cursor.execute(
                    "SELECT island_idx FROM programs WHERE id='fixture-7'"
                )
                self.assertEqual(db.cursor.fetchone()[0], 2)

            try:
                asyncio.run(run())
            finally:
                close_async_db(async_db)
                db.close()

    def test_spawns_are_spaced_from_the_previous_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            db = open_db(Path(directory) / "programs.sqlite")
            baseline = make_program(0, score=0.9)
            db.add(baseline)
            async_db, _ = install(db, max_islands=4, stagnation=2, migration=100)

            async def run():
                for generation, score in ((1, 0.95), (2, 0.8), (3, 0.7)):
                    program = add_candidate(db, generation, parent=baseline.id, score=score)
                    await maintain(async_db, program)
                self.assertEqual(runtime.current_island_count(async_db), 3)

                one_after_spawn = add_candidate(
                    db, 4, parent=baseline.id, score=0.69
                )
                await maintain(async_db, one_after_spawn)
                # A stale best-generation counter used to allow another spawn
                # on the first candidate after an earlier spawn.
                self.assertEqual(runtime.current_island_count(async_db), 3)

                second_after_spawn = add_candidate(
                    db, 5, parent=baseline.id, score=0.68
                )
                await maintain(async_db, second_after_spawn)
                self.assertEqual(runtime.current_island_count(async_db), 4)

            try:
                asyncio.run(run())
            finally:
                close_async_db(async_db)
                db.close()

    def test_restart_restores_count_counter_and_does_not_count_replay_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "programs.sqlite"
            db = open_db(path)
            baseline = make_program(0, score=0.9)
            db.add(baseline)
            async_db, _ = install(db, max_islands=4, stagnation=2, migration=100)

            async def first_session():
                for generation, score in ((1, 0.95), (2, 0.8), (3, 0.7)):
                    program = add_candidate(db, generation, parent=baseline.id, score=score)
                    await maintain(async_db, program)

            try:
                asyncio.run(first_session())
                before = runtime.runtime_state(async_db)
                self.assertEqual(before["completed_evaluations"], 4)
                self.assertEqual(before["island_count"], 3)
            finally:
                close_async_db(async_db)
                db.close()

            resumed_db = open_db(path, islands=2)
            resumed_async, _ = install(
                resumed_db, max_islands=4, stagnation=2, migration=100
            )

            async def resumed_session():
                restored = runtime.runtime_state(resumed_async)
                self.assertEqual(restored["completed_evaluations"], 4)
                self.assertEqual(runtime.current_island_count(resumed_async), 3)

                # Replaying a completed maintenance event cannot increment
                # the counter or trigger a duplicate spawn.
                replay = resumed_db.get("fixture-3")
                await maintain(resumed_async, replay)
                after_replay = runtime.runtime_state(resumed_async)
                self.assertEqual(after_replay["completed_evaluations"], 4)
                self.assertEqual(after_replay["island_count"], 3)

                for generation, score in ((4, 0.68), (5, 0.66)):
                    program = add_candidate(
                        resumed_db, generation, parent="fixture-3", score=score
                    )
                    await maintain(resumed_async, program)
                self.assertEqual(runtime.current_island_count(resumed_async), 4)

            try:
                asyncio.run(resumed_session())
            finally:
                close_async_db(resumed_async)
                resumed_db.close()

    def test_runtime_rejects_multiple_db_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            db = open_db(Path(directory) / "programs.sqlite")
            db.add(make_program(0, score=0.9))
            async_db = AsyncProgramDatabase(db, max_workers=2)
            try:
                with self.assertRaisesRegex(ValueError, "one DB worker"):
                    runtime.install_island_runtime(async_db)
            finally:
                close_async_db(async_db)
                db.close()


if __name__ == "__main__":
    unittest.main()
