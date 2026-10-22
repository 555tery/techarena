"""Structural contracts for diversity and generator mechanisms, no candidate runs."""

import json
import random
import unittest

from characteristics import characterize, Fenwick
from generate import expanded_source, FAMILIES, LEGACY, MAIN, NEW, STRESS, generate_case, kth_active, make_specs


class DiversityTests(unittest.TestCase):
    def test_all_legacy_mechanisms_and_equal_new_block_are_retained(self):
        main = make_specs("search")
        self.assertEqual((len(LEGACY), len(NEW), len(FAMILIES), len(main)), (16, 16, 32, 128))
        self.assertEqual(sum(s["mechanism_block"] == "broad_prior" for s in main), 64)
        self.assertEqual(sum(s["regime"] == "high" for s in main), 87)
        self.assertEqual(sum(s["regime"] == "moderate" for s in main), 33)
        self.assertEqual(sum(s["regime"] == "rounding" for s in main), 8)

    def test_kth_live_pid_matches_independent_sorted_set(self):
        rng, tree, active = random.Random(71), Fenwick(200), set()
        for step in range(500):
            pid = rng.randrange(1, 201)
            if pid in active:
                active.remove(pid)
                tree.add(pid, -1)
            else:
                active.add(pid)
                tree.add(pid, 1)
            if active:
                ordered = sorted(active)
                for rank in {1, len(active), rng.randrange(1, len(active) + 1)}:
                    self.assertEqual(kth_active(tree, rank), ordered[rank - 1])

    def test_isolated_deletions_and_protected_background(self):
        spec = next(s for s in make_specs("search") if s["family"] == "isolated_recent_churn" and s["variant"] == 0)
        commands = expanded_source(spec, 92731, 4_096)
        f = characterize(commands)["features"]
        self.assertEqual(f["delete_run_max"], 1)
        self.assertGreater(f["deletions"], 0)
        self.assertGreater(f["old_survivor_volume_over_final"], 0)
        self.assertLess(f["right_censored_pipe_fraction"], 1)

    def test_legacy_fifo_and_lifo_remain_exact(self):
        for family, choose in (("fifo", min), ("lifo", max)):
            spec = next(s for s in make_specs("search") if s["family"] == family and s["variant"] == 0)
            commands, actual, stats = generate_case(spec)
            active, pid = set(), 0
            for command in commands:
                if command > 0:
                    pid += 1
                    active.add(pid)
                else:
                    self.assertEqual(-command, choose(active))
                    active.remove(-command)
            self.assertGreater(stats["deletions"], 0)
            self.assertEqual(actual["termination"]["appended_deletions"], 0)

    def test_new_prepared_corpus_covers_gaps_without_losing_other_regimes(self):
        manifest = json.loads((MAIN / "manifest.json").read_text())
        f = [c["features"] for c in manifest["cases"]]
        self.assertGreaterEqual(sum(x["final_to_bound"] >= .95 for x in f), 87)
        self.assertGreaterEqual(sum(.30 <= x["final_to_bound"] < .95 for x in f), 33)
        self.assertGreaterEqual(sum(x["operations"] < 2_000 for x in f), 8)
        self.assertGreaterEqual(sum(x["delete_fraction"] < .05 for x in f), 2)
        self.assertGreaterEqual(sum(x["share_length_le2"] >= .8 for x in f), 2)
        self.assertGreaterEqual(sum(x["initial_insert_run_over_n"] >= .35 for x in f), 2)
        self.assertGreaterEqual(sum(x["delete_run_max"] == 1 for x in f), 4)
        recency = [x for x in f if x["deletion_age_rank_mean"] is not None and x["deletion_age_rank_mean"] >= .9 and x["lifo_deletion_fraction"] < .3]
        self.assertTrue(any(x["size_lag1_correlation"] is not None and x["size_lag1_correlation"] > .1 for x in recency))
        self.assertTrue(any(x["size_lag1_correlation"] is not None and x["size_lag1_correlation"] < -.1 for x in recency))
        self.assertGreaterEqual(sum(x["mean_load_over_peak"] < .65 for x in f), 8)
        self.assertGreaterEqual(sum(x["mean_load_over_peak"] > .80 for x in f), 8)
        self.assertEqual(max(x["operations"] for x in f), 200_000)
        self.assertTrue(all(c["termination"]["appended_insertions"] == 0 for c in manifest["cases"]))

    def test_terminal_drain_cases_reproduce_at_real_horizons(self):
        manifests = [json.loads((p / "manifest.json").read_text()) for p in (MAIN, STRESS)]
        saved = {c["id"]: c for m in manifests for c in m["cases"]}
        selected = [next(s for s in make_specs("search") if s["family"] == family and s["variant"] == variant)
                    for family, variant in (("uniform_churn", 3), ("long_prefill_recent", 3), ("partial_drain", 0), ("short_rounding", 2))]
        for spec in selected:
            commands, actual, stats = generate_case(spec)
            self.assertEqual(stats, saved[spec["id"]]["stats"])
            self.assertEqual(actual["termination"], saved[spec["id"]]["termination"])
            self.assertEqual(len(commands), saved[spec["id"]]["operations"])


if __name__ == "__main__":
    unittest.main()
