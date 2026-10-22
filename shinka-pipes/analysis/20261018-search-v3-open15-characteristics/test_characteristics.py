"""Small independent oracles. No solver, compiler, checker or model execution."""

import importlib.util
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from analyze import characterize, Fenwick, load_case, OPEN, parse_input, PROJECT, quantile


class CharacteristicTests(unittest.TestCase):
    def test_hand_computed_lifetimes_and_deletion_order(self):
        result = characterize([10, 20, 30, -2, 5, -1, 40, -3])
        f = result["features"]
        self.assertEqual((f["peak_volume"], f["final_volume"], f["volume_bound"]), (75, 45, 80))
        self.assertEqual(f["peak_live_count"], 3)
        self.assertEqual(f["final_to_bound"], 45 / 80)
        self.assertAlmostEqual(f["deletion_age_rank_mean"], 1 / 6)
        self.assertEqual(f["fifo_deletion_fraction"], 2 / 3)
        self.assertEqual(f["lifo_deletion_fraction"], 0.)
        self.assertEqual(f["completed_lifetime_median_over_n"], 5 / 8)
        self.assertEqual(f["right_censored_pipe_fraction"], 2 / 5)
        self.assertEqual(f["survivor_age_median_over_n"], .25)
        self.assertEqual(f["first_peak_position"], 7 / 8)
        self.assertEqual(f["initial_insert_run"], 3)
        self.assertEqual(result["load_curve"][-1], .6)

    def test_deletion_age_rank_against_brute_force(self):
        for seed in range(10):
            rng, live, commands, next_pid = random.Random(seed), {}, [], 1
            ranks, oldest, newest = [], 0, 0
            volumes, peak_counts, peak = [], [], 0
            for step in range(200):
                if len(live) > 1 and rng.random() < .45:
                    pid = rng.choice(list(live))
                    ordered = sorted(live)
                    rank = ordered.index(pid) / (len(ordered) - 1)
                    ranks.append(rank)
                    oldest += rank == 0
                    newest += rank == 1
                    commands.append(-pid)
                    del live[pid]
                else:
                    length = rng.randint(1, 40)
                    live[next_pid] = length
                    commands.append(length)
                    next_pid += 1
                volumes.append(sum(live.values()))
                peak_counts.append(len(live))
                peak = max(peak, volumes[-1])
            f = characterize(commands)["features"]
            with self.subTest(seed=seed):
                self.assertEqual(f["peak_volume"], peak)
                self.assertEqual(f["final_volume"], sum(live.values()))
                self.assertEqual(f["peak_live_count"], max(peak_counts))
                self.assertAlmostEqual(f["deletion_age_rank_mean"], sum(ranks) / len(ranks))
                self.assertAlmostEqual(f["fifo_deletion_fraction"], oldest / len(ranks))
                self.assertAlmostEqual(f["lifo_deletion_fraction"], newest / len(ranks))

    def test_no_deletions_are_censored_not_zero_lifetimes(self):
        f = characterize([2, 2, 2, 2])["features"]
        self.assertEqual(f["right_censored_pipe_fraction"], 1.)
        self.assertIsNone(f["completed_lifetime_median_over_n"])
        self.assertIsNone(f["deletion_age_rank_mean"])
        self.assertEqual(f["adjacent_equal_size_fraction"], 1.)
        self.assertEqual(f["max_same_size_allocation_run"], 4)

    def test_optional_zero_and_invalid_envelopes(self):
        self.assertEqual(parse_input(b"1 2 10 20 0"), (1., [10, 20]))
        self.assertEqual(parse_input(b"1 2 10 20"), (1., [10, 20]))
        for content in (b"nan 1 10", b"1 2 10", b"1 0 0", b"1 1 10 0 0"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_input(content)
        for commands in ([0], [41], [-1], [1, -1, -1], [1, -1]):
            with self.subTest(commands=commands), self.assertRaises(ValueError):
                characterize(commands)

    def test_forbidden_input_path_rejected_before_read(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected read")):
            with self.assertRaises(ValueError):
                load_case(PROJECT / "shinka-pipes/validation-v1/data/not-opened.in", "validation", "none")

    def test_fenwick_updates_and_quantiles(self):
        tree = Fenwick(5)
        for pid in (1, 3, 4):
            tree.add(pid, 1)
        self.assertEqual([tree.prefix(i) for i in range(6)], [0, 1, 1, 2, 3, 3])
        tree.add(3, -1)
        self.assertEqual(tree.prefix(3), 1)
        self.assertEqual(quantile([0, 2, 4], .75), 3.)
        self.assertIsNone(quantile([], .5))

    def test_open_basic_stats_match_existing_independent_parser(self):
        path = PROJECT / "tools/pipes_harness.py"
        spec = importlib.util.spec_from_file_location("_workload_audit_parser", path)
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        for i in range(1, 16):
            file = OPEN / f"{i}.in"
            weight, commands = parse_input(file.read_bytes())
            f = characterize(commands, weight)["features"]
            expected = parser.parse_test(file)
            with self.subTest(case=i):
                self.assertEqual(f["weight"], expected["weight"])
                self.assertEqual(f["operations"], expected["operation_count"])
                self.assertEqual(f["insertions"], expected["placement_count"])
                self.assertEqual(f["peak_volume"], expected["peak_live_pipe_length_m"])
                self.assertEqual(f["final_volume"], expected["final_occupied_length_m"])
                self.assertEqual(f["volume_bound"], expected["minimum_trench_lower_bound_m"])


if __name__ == "__main__":
    unittest.main()
