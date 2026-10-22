import hashlib
import json
import shutil
import tempfile
import threading
import types
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch

import mixed_seed_runtime as mixed
from research_runner import _seed_meta_queue
import selection_runtime as selection_adapter
from support import ROOT


def row(generation, island, *, correct=True, metadata=None, score=0.5, ident=None):
    return {"id": ident or f"p-{generation}-{island}", "generation": generation,
            "island_idx": island, "correct": correct, "combined_score": score,
            "metadata": metadata or {}}


class MixedSeedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = mixed.load_plan(ROOT)

    def test_pinned_plan_hashes_and_seed_slots(self):
        plan = self.plan
        self.assertEqual(plan["plan_sha256"], hashlib.sha256((ROOT / "seed-plan.json").read_bytes()).hexdigest())
        self.assertEqual([mixed.initial_seed_for_generation(plan, i)["lineage_id"] for i in range(1, 8)],
                         list(range(1, 8)))
        self.assertIsNone(mixed.initial_seed_for_generation(plan, 8))
        self.assertEqual([s["kind"] for s in plan["seeds"]].count("strong"), 2)
        self.assertEqual([s["kind"] for s in plan["seeds"]].count("simple"), 2)
        self.assertEqual([s["kind"] for s in plan["seeds"]].count("independent"), 4)

    def test_plan_rejects_changed_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            shutil.copy2(ROOT / "seed-plan.json", target / "seed-plan.json")
            shutil.copytree(ROOT / "seeds", target / "seeds")
            path = target / "seeds" / "independent-task.txt"
            path.write_text(path.read_text() + " changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash changed"):
                mixed.load_plan(target)

    def test_fixed_and_independent_candidates_keep_run_protected_source(self):
        plan = self.plan
        run_scaffold = plan["seeds"][0]["source"]
        run_prefix, _, run_suffix = mixed._split_source(run_scaffold)
        for lineage in range(1, 4):
            source = mixed.seed_code(plan, lineage, run_scaffold)
            prefix, _, suffix = mixed._split_source(source)
            self.assertEqual(prefix, run_prefix)
            self.assertEqual(suffix, run_suffix)

        prompt_scaffold = plan["seeds"][4]["scaffold"]
        # The prompt has an optional final newline difference in some frozen snapshots.
        prompt_prefix, _, prompt_suffix = mixed._split_source(prompt_scaffold)
        mutated_response = prompt_prefix + "\n  // independent mutable logic\n" + prompt_suffix
        candidate = mixed.independent_candidate(mutated_response, prompt_scaffold, run_scaffold)
        prefix, block, suffix = mixed._split_source(candidate)
        self.assertEqual(prefix, run_prefix)
        self.assertEqual(suffix, run_suffix)
        self.assertIn("independent mutable logic", block)

        without_final_newline = prompt_scaffold[:-1] if prompt_scaffold.endswith("\n") else prompt_scaffold + "\n"
        candidate = mixed.independent_candidate(mutated_response, without_final_newline, run_scaffold)
        self.assertEqual(mixed.protected_parts(candidate), (run_prefix, run_suffix))

    def test_seed_roots_and_warmup_ignore_placeholder_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            programs = [row(0, 0)]
            programs.extend(row(0, i, metadata={"_is_island_copy": True}) for i in range(1, 8))
            for generation in range(1, 8):
                assignment = mixed.reserve_assignment(run, programs, generation, self.plan)
                self.assertEqual((assignment["phase"], assignment["lineage_id"]), ("seed", generation))
                programs.append(row(generation, generation, metadata={"mixed_seed": {
                    "phase": "seed", "lineage_id": generation}}))

            assigned = []
            for generation in range(8, 32):
                assignment = mixed.reserve_assignment(run, programs, generation, self.plan)
                self.assertEqual(assignment["phase"], "warmup")
                assigned.append((generation, assignment))
                programs.append(row(generation, assignment["lineage_id"], metadata={"mixed_seed": assignment}))
            status = mixed.warmup_status(programs)
            self.assertTrue(status["complete"])
            self.assertEqual(status["correct_per_lineage"], [4] * 8)
            self.assertIsNone(mixed.reserve_assignment(run, programs, 32, self.plan))
            self.assertTrue(json.loads((run / mixed.STATE_NAME).read_text())["isolation_released"])

    def test_reservations_wait_at_lineage_quota_and_retry_failed_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            programs = [row(0, 0)]
            programs.extend(row(0, i, metadata={"_is_island_copy": True}) for i in range(1, 8))
            for generation in range(1, 8):
                assignment = mixed.reserve_assignment(run, programs, generation, self.plan)
                ok = generation != 3
                programs.append(row(generation, generation, correct=ok, metadata={"mixed_seed": assignment}))
            retry = mixed.reserve_assignment(run, programs, 8, self.plan)
            self.assertEqual((retry["phase"], retry["lineage_id"], retry["retry"]), ("seed", 3, 1))
            programs.append(row(8, 3, metadata={"mixed_seed": retry}))
            self.assertEqual(mixed.reserve_assignment(run, programs, 9, self.plan)["phase"], "warmup")

        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            programs = [row(0, 0)]
            programs.extend(row(0, i, metadata={"_is_island_copy": True}) for i in range(1, 8))
            for generation in range(1, 8):
                assignment = mixed.reserve_assignment(run, programs, generation, self.plan)
                programs.append(row(generation, generation, metadata={"mixed_seed": assignment}))
            for generation in range(8, 32):
                assignment = mixed.reserve_assignment(run, programs, generation, self.plan)
                self.assertFalse(assignment.get("wait", False))
            blocked = mixed.reserve_assignment(run, programs, 32, self.plan)
            self.assertTrue(blocked["wait"])
            state = json.loads((run / mixed.STATE_NAME).read_text())
            reservations = [v for k, v in state["assignments"].items()
                             if int(k) >= 8 and v.get("phase") == "warmup"]
            by_lineage = [sum(item["lineage_id"] == i for item in reservations) for i in range(8)]
            self.assertEqual(by_lineage, [3] * 8)

    def test_state_file_updates_are_serialized_across_reservers_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            programs = [row(0, 0)]
            programs.extend(row(0, i, metadata={"_is_island_copy": True}) for i in range(1, 8))
            barrier = threading.Barrier(7)

            def reserve(generation):
                barrier.wait(timeout=5)
                return mixed.reserve_assignment(run, programs, generation, self.plan)

            with ThreadPoolExecutor(max_workers=8) as executor:
                assignments = list(executor.map(reserve, range(1, 8)))
            self.assertEqual({a["lineage_id"] for a in assignments}, set(range(1, 8)))
            state = json.loads((run / mixed.STATE_NAME).read_text())
            self.assertEqual(set(state["assignments"]), {str(i) for i in range(1, 8)})

            # Reach a stale-snapshot release boundary: either the final slot is
            # reserved before release, or release wins and the stale caller is
            # told that normal shared search may proceed. Neither write may be lost.
            programs = [row(0, 0)]
            programs.extend(row(0, i, metadata={"_is_island_copy": True}) for i in range(1, 8))
            for generation in range(1, 8):
                programs.append(row(generation, generation, metadata={"mixed_seed": {
                    "phase": "seed", "lineage_id": generation}}))
            next_generation = 8
            for island in range(8):
                for ordinal in range(1, 3):
                    generation = 8 + island * 2 + ordinal
                    programs.append(row(generation, island, metadata={"mixed_seed": {
                        "phase": "warmup", "lineage_id": island}}))
            complete = list(programs)
            complete.extend(row(25 + island, island, metadata={"mixed_seed": {
                "phase": "warmup", "lineage_id": island}}) for island in range(8))
            gate = threading.Barrier(2)

            def reserve_stale():
                gate.wait(timeout=5)
                return mixed.reserve_assignment(run, programs, next_generation, self.plan)

            def release_complete():
                gate.wait(timeout=5)
                return mixed.mark_isolation_released(run, complete)

            with ThreadPoolExecutor(max_workers=2) as executor:
                reserved = executor.submit(reserve_stale)
                released = executor.submit(release_complete)
                assignment, release_result = reserved.result(), released.result()
            final = json.loads((run / mixed.STATE_NAME).read_text())
            self.assertTrue(final["isolation_released"])
            self.assertTrue(release_result)
            stored = final["assignments"].get(str(next_generation))
            self.assertEqual(stored, assignment)

    def test_first_meta_batch_collapses_to_one_best_program_per_lineage(self):
        queue = []
        programs = []
        for island in range(8):
            for j in range(4):
                generation = j if island == 0 else j + 1
                ident = f"i{island}-g{generation}"
                queue.append(types.SimpleNamespace(id=ident))
                programs.append(row(generation, island, score=0.4 + j / 100,
                                    ident=ident, metadata={"mixed_seed": {"phase": "warmup"}}))
        for island in range(1, 8):
            ident = f"copy-{island}"
            queue.append(types.SimpleNamespace(id=ident))
            programs.append(row(0, island, score=0.99, ident=ident,
                                metadata={"_is_island_copy": True}))
        summarizer = types.SimpleNamespace(evaluated_since_last_meta=queue)
        selected = _seed_meta_queue(summarizer, programs)
        self.assertEqual(selected, 8)
        self.assertEqual(len(summarizer.evaluated_since_last_meta), 8)
        self.assertEqual({p.id for p in summarizer.evaluated_since_last_meta},
                         {f"i{i}-g{3 if i == 0 else 4}" for i in range(8)})


class MixedSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_parent_is_the_placeholder_in_its_assigned_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "gen_2").mkdir()
            source = "fixed baseline source"
            sha = hashlib.sha256(source.encode()).hexdigest()
            programs = [row(0, 0, ident="base")]
            pool = [{"id": "base", "generation": 0, "source_sha256": sha,
                     "island_idx": 0, "mean": .5, "family_scores": {},
                     "regression": {"tail_loss": 0., "max_case_loss": 0.}}]
            objects = {"base": types.SimpleNamespace(id="base", code=source, correct=True,
                island_idx=0, generation=0, combined_score=.5)}
            for island in range(1, 8):
                ident = f"copy-{island}"
                programs.append(row(0, island, ident=ident,
                                    metadata={"_is_island_copy": True}))
                pool.append({"id": ident, "generation": 0, "source_sha256": sha,
                             "island_idx": island, "mean": .5, "family_scores": {},
                             "regression": {"tail_loss": 0., "max_case_loss": 0.}})
                objects[ident] = types.SimpleNamespace(id=ident, code=source, correct=True,
                    island_idx=island, generation=0, combined_score=.5)
            db = types.SimpleNamespace(
                sample_with_fix_mode_async=AsyncMock(return_value=(objects["copy-7"], [objects["copy-7"]],
                                                                    [objects["copy-7"]], False)),
                get_async=AsyncMock(side_effect=lambda ident: objects.get(ident)),
                config=types.SimpleNamespace(num_archive_inspirations=2, num_top_k_inspirations=2),
            )
            adapter_policy = {"parent_cycle": ["score", "score", "robust", "score", "specialist"],
                              "tail_fraction": .1, "robust_mean_tolerance": .005,
                              "numeric_tolerance": 1e-12}
            with patch.object(selection_adapter, "refresh", return_value=pool), \
                 patch.object(selection_adapter, "read_programs", return_value=programs):
                selection_adapter.install_database_sampling(
                    db, run, {}, "manifest", adapter_policy, 8, 50,
                    mixed_plan=MixedSeedRuntimeTests.plan, runner=None)
                selected, archive, top, needs_fix = await db.sample_with_fix_mode_async(target_generation=2)
            self.assertFalse(needs_fix)
            self.assertEqual(selected.id, "copy-2")
            self.assertEqual(selected.island_idx, 2)
            self.assertEqual(archive, [])
            self.assertEqual(top, [])
            decision = json.loads((run / "gen_2" / "selection-context.json").read_text())
            self.assertEqual(decision["mixed_seed"]["lineage_id"], 2)
            self.assertEqual(decision["selected_parent"]["island_idx"], 2)
            self.assertEqual(decision["mode"], "mixed-seed-root")


if __name__ == "__main__":
    unittest.main()
