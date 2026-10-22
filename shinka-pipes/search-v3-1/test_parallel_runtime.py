"""Concurrent-proposal fixtures; no model calls or candidate execution."""

import json
from pathlib import Path
import tempfile
import types
import unittest

import parallel_runtime as p
from test_research import database, fixture_program


class ParallelTests(unittest.TestCase):
    def test_newly_completed_code_and_inflight_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            database(run, [(fixture_program(), "parent")])
            reservations = {}
            first = dict(run=run, reservations=reservations, generation=1, programs=[])
            second = dict(run=run, reservations=reservations, generation=2, programs=[])
            self.assertIsNone(p.reserve_source(first, "novel code"))
            self.assertIn("in-flight", p.reserve_source(second, "novel code"))
            self.assertIn("evaluated", p.reserve_source(second, "parent"))
            # A failed generation must not reserve that source forever.
            (run / "gen_1").mkdir()
            (run / "gen_1/failure.json").write_text("{}")
            self.assertIsNone(p.reserve_source(second, "novel code"))
            state = json.loads((run / "inflight-sources.json").read_text())
            self.assertEqual(list(state["sources"].values()), [2])

    def test_cross_receives_ledger_and_native_recommendations(self):
        from shinka.core.sampler import PromptSampler
        from shinka.database import Program
        parent = Program(id="parent", code="parent", language="cpp", combined_score=.5,
                         correct=True, metadata={"patch_name": "fixture"})
        inspiration = Program(id="inspiration", code="different", language="cpp", combined_score=.6,
                              correct=True, metadata={"patch_name": "other"})
        runner = types.SimpleNamespace(prompt_sampler=PromptSampler(
            language="cpp", patch_types=["cross"], patch_type_probs=[1.0]))
        p.install_crossover_feedback(runner)
        system, prompt, patch_type = runner.prompt_sampler.sample(
            parent=parent, archive_inspirations=[inspiration], top_k_inspirations=[],
            meta_recommendations="EXACT_LEDGER + NATIVE_META")
        self.assertEqual(patch_type, "cross")
        self.assertEqual(system.count("EXACT_LEDGER + NATIVE_META"), 1)
        self.assertIn("different", prompt)
        p.install_crossover_feedback(runner)
        system, _, _ = runner.prompt_sampler.sample(parent, [inspiration], [], "evidence")
        self.assertEqual(system.count("evidence"), 2)  # heading plus payload, not duplicated hooks


if __name__ == "__main__":
    unittest.main()
