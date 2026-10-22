"""Pure unit tests for microstream generation and fixed-layout certificates."""

import ast
import copy
from collections import Counter
from pathlib import Path
import unittest

from micro import (
    MICRO_FAMILIES,
    generate_micro,
    make_micro_specs,
    verify_layout_witness,
)


def independently_check(commands, metadata):
    """Reconstruct command legality and geometry without generator helpers."""
    witness = metadata["layout_witness"]
    cap = witness["capacity_m"]
    target_sections = witness["target_capacity_sections"]
    placement_rows = witness["placements"]
    placements = {row["pid"]: row for row in placement_rows}
    assert len(placements) == len(placement_rows)
    active = {}
    expected_pid = 1
    running, peak = 0, 0
    deletion_ops = {}

    assert len(commands) == len(witness["events"]) == metadata["operations"]
    for ordinal, (command, event) in enumerate(zip(commands, witness["events"]), start=1):
        assert isinstance(command, int) and not isinstance(command, bool) and command != 0
        assert event["op"] == ordinal and event["command"] == command
        if command > 0:
            assert event["kind"] == "insert"
            pid = expected_pid
            expected_pid += 1
            row = placements[pid]
            assert event["pid"] == pid
            assert event["length_m"] == command == row["length_m"]
            assert row["insert_op"] == ordinal
            x, length = row["start_m"], row["length_m"]
            assert 1 <= length <= 40 and 0 <= x <= cap - length
            for other_x, other_length in active.values():
                assert x + length <= other_x or other_x + other_length <= x
            assert event["start_m"] == x
            active[pid] = (x, length)
            running += length
            peak = max(peak, running)
        else:
            assert event["kind"] == "delete"
            pid = -command
            assert event["pid"] == pid and pid in active
            assert placements[pid]["delete_op"] == ordinal
            _, length = active.pop(pid)
            running -= length
            deletion_ops[pid] = ordinal

    assert set(placements) == set(range(1, expected_pid))
    for pid, row in placements.items():
        assert row["delete_op"] == deletion_ops.get(pid)
    final_volume = sum(length for _, length in active.values())
    assert active and final_volume > 0
    assert final_volume == metadata["final_volume_m"] == witness["final_volume_m"]
    assert len(active) == metadata["final_live_count"]
    assert peak == metadata["peak_volume_m"] == witness["peak_volume_m"]
    assert (target_sections - 1) * 20 < peak <= cap == 20 * target_sections
    assert metadata["target_capacity_sections"] == target_sections
    assert metadata["termination"]["appended_insertions"] == 0
    assert metadata["termination"]["appended_deletions"] == 0
    assert metadata["generator_attempt"] == 0
    return placements, deletion_ops, active


def phase(metadata, name):
    found = [p for p in metadata["phases"] if p["name"] == name]
    assert len(found) == 1, (name, found)
    return found[0]


def commands_in(commands, p):
    return commands[p["start_op"] - 1:p["end_op"]]


class MicroSpecTests(unittest.TestCase):
    def test_spec_block_is_six_families_four_variants_and_balanced_sections(self):
        specs = make_micro_specs()
        self.assertEqual(len(specs), 24)
        self.assertEqual(Counter(s["family"] for s in specs), {name: 4 for name in MICRO_FAMILIES})
        self.assertEqual(Counter(s["parameters"]["sections"] for s in specs), {1: 8, 2: 8, 3: 8})
        self.assertEqual([s["id"] for s in specs[:3]], [
            "s31_129_micro_gap_refill", "s31_130_micro_gap_refill", "s31_131_micro_gap_refill",
        ])
        self.assertEqual(specs[-1]["id"], "s31_152_micro_partial_drain")
        for spec in specs:
            with self.subTest(case=spec["id"]):
                self.assertEqual(spec["role"], "search")
                self.assertEqual(spec["regime"], "micro")
                self.assertEqual(spec["mechanism_block"], "micro")
                self.assertEqual(spec["parameters"]["sections"],
                                 1 + (MICRO_FAMILIES.index(spec["family"]) + spec["variant"]) % 3)
                self.assertIn("search-v3.1/micro-r1/", spec["seed_namespace"])
                self.assertGreaterEqual(spec["operation_budget"], 48)
                self.assertLessEqual(spec["operation_budget"], 80)
                self.assertNotIn("score", spec)

    def test_all_streams_are_deterministic_legal_and_witness_feasible(self):
        short_streams = []
        very_short = []
        initial_counts = {1: set(), 2: set(), 3: set()}
        initial_sizes = {1: set(), 2: set(), 3: set()}
        initial_prefixes = set()
        for spec in make_micro_specs():
            with self.subTest(case=spec["id"]):
                commands, metadata = generate_micro(spec)
                again, again_metadata = generate_micro(spec)
                self.assertEqual(commands, again)
                self.assertEqual(metadata, again_metadata)
                self.assertGreaterEqual(len(commands), 8)
                self.assertLessEqual(len(commands), min(80, spec["operation_budget"]))
                self.assertEqual(metadata["seed"], spec["design_seed"])
                self.assertEqual(metadata["generator_attempt"], 0)
                placements, deleted, active = independently_check(commands, metadata)
                self.assertTrue(verify_layout_witness(commands, metadata))
                cold = phase(metadata, "coldstart")
                cold_commands = commands_in(commands, cold)
                self.assertGreaterEqual(len(cold_commands), 4)
                self.assertLessEqual(len(cold_commands), 20)
                self.assertTrue(all(command > 0 for command in cold_commands))
                small_lengths = {command for command in cold_commands if command <= 8}
                self.assertGreaterEqual(len(small_lengths), 3)
                initial_counts[spec["parameters"]["sections"]].add(len(cold_commands))
                initial_sizes[spec["parameters"]["sections"]].update(cold_commands)
                initial_prefixes.add(tuple(cold_commands[:3]))
                deletion_count = sum(command < 0 for command in commands)
                if spec["family"] == "micro_neighbor_coalescence":
                    self.assertEqual(deletion_count, 2)
                elif spec["family"] == "micro_partial_drain":
                    self.assertGreaterEqual(deletion_count, 1)
                    self.assertLessEqual(deletion_count, 15)
                else:
                    self.assertGreaterEqual(deletion_count, 4)
                    self.assertLessEqual(deletion_count, 15)
                self.assertTrue(active)
                self.assertTrue(all(1 <= pid <= len(placements) for pid in deleted))
                if len(commands) < 32:
                    short_streams.append(spec["id"])
                if len(commands) <= 12:
                    very_short.append(spec["id"])
        self.assertGreaterEqual(len(short_streams), 6,
                                "microstreams should include several horizons below 32 commands")
        self.assertTrue(very_short, "at least one stream should have 12 or fewer commands")
        self.assertGreaterEqual(len(initial_prefixes), 18, "coldstart prefixes should vary across seeds")
        for sections in (1, 2, 3):
            self.assertGreaterEqual(len(initial_counts[sections]), 2,
                                    f"coldstart counts should vary at {sections * 20} m")
            self.assertGreaterEqual(len(initial_sizes[sections]), 6,
                                    f"small lengths should vary at {sections * 20} m")
        self.assertEqual((min(initial_counts[1]), max(initial_counts[1])), (4, 9))

    def test_each_family_has_its_declared_structural_mechanism(self):
        generated = {}
        neighbor_pair_starts = set()
        for spec in make_micro_specs():
            commands, metadata = generate_micro(spec)
            placements, _, _ = independently_check(commands, metadata)
            generated[(spec["family"], spec["variant"])] = (commands, metadata, placements)

        for variant in range(4):
            with self.subTest(family="micro_gap_refill", variant=variant):
                commands, meta, placements = generated[("micro_gap_refill", variant)]
                created = phase(meta, "separated_hole_creation")
                refill = phase(meta, "holes_refill")
                victims = created["victim_pids"]
                victim_rows = sorted((placements[pid] for pid in victims), key=lambda row: row["start_m"])
                self.assertGreaterEqual(len(victims), 3)
                for left, right in zip(victim_rows, victim_rows[1:]):
                    self.assertLess(left["start_m"] + left["length_m"], right["start_m"])
                refill_events = meta["layout_witness"]["events"][refill["start_op"] - 1:refill["end_op"]]
                inserts = [event for event in refill_events if event["kind"] == "insert"]
                self.assertTrue(inserts)
                for victim in victim_rows:
                    lo, hi = victim["start_m"], victim["start_m"] + victim["length_m"]
                    self.assertTrue(any(lo <= event["start_m"] and
                                        event["start_m"] + event["length_m"] <= hi
                                        for event in inserts))
                self.assertTrue(all(command < 0 for command in commands_in(commands, created)))

            with self.subTest(family="micro_neighbor_coalescence", variant=variant):
                commands, meta, placements = generated[("micro_neighbor_coalescence", variant)]
                deleted = phase(meta, "neighboring_deletions")
                neighbor_pair_starts.add(deleted["pair_index"])
                refill = phase(meta, "coalesced_gap_refill")
                left_pid, right_pid = deleted["victim_pids"]
                left, right = placements[left_pid], placements[right_pid]
                self.assertEqual(left["start_m"] + left["length_m"], right["start_m"])
                self.assertEqual(commands_in(commands, deleted), [-left_pid, -right_pid])
                event = meta["layout_witness"]["events"][refill["start_op"] - 1]
                self.assertGreater(event["length_m"], max(left["length_m"], right["length_m"]))
                self.assertLessEqual(event["length_m"], left["length_m"] + right["length_m"])
                self.assertEqual(event["start_m"], left["start_m"])

            with self.subTest(family="micro_short_churn", variant=variant):
                commands, meta, _ = generated[("micro_short_churn", variant)]
                churn = phase(meta, "short_replacement_churn")
                body = commands_in(commands, churn)
                self.assertGreaterEqual(churn["rounds"], 4)
                self.assertLessEqual(churn["rounds"], 12)
                self.assertEqual(len(body), churn["rounds"] * 2)
                self.assertTrue(all(body[i] < 0 and body[i + 1] > 0
                                    for i in range(0, len(body), 2)))
                self.assertEqual(len(churn["replacement_pairs"]), churn["rounds"])

            with self.subTest(family="micro_size_shift", variant=variant):
                commands, meta, _ = generated[("micro_size_shift", variant)]
                ramp_name = "request_large_to_small" if variant % 2 else "request_small_to_large"
                ramp = phase(meta, ramp_name)
                requested = [c for c in commands_in(commands, ramp) if c > 0]
                released = phase(meta, "release_size_shift_region")
                self.assertIn(len(released["victim_pids"]), (3, 4))
                self.assertEqual(len(requested), len(released["victim_pids"]))
                if variant % 2:
                    self.assertEqual(requested, sorted(requested, reverse=True))
                else:
                    self.assertEqual(requested, sorted(requested))
                self.assertGreater(max(requested), min(requested))

            with self.subTest(family="micro_tail_reuse", variant=variant):
                commands, meta, placements = generated[("micro_tail_reuse", variant)]
                release, reuse = phase(meta, "release_tail"), phase(meta, "tail_reuse")
                victims = release["victim_pids_right_to_left"]
                initial_count = len(commands_in(commands, phase(meta, "coldstart")))
                self.assertLessEqual(len(victims), initial_count - 1)
                self.assertGreaterEqual(len(victims), 2)
                starts = [placements[pid]["start_m"] for pid in victims]
                self.assertEqual(starts, sorted(starts, reverse=True))
                self.assertTrue(all(command < 0 for command in commands_in(commands, release)))
                lo, hi = reuse["tail_start_m"], reuse["tail_start_m"] + reuse["tail_length_m"]
                inserted = [event for event in meta["layout_witness"]["events"]
                            if reuse["start_op"] <= event["op"] <= reuse["end_op"]]
                self.assertTrue(inserted)
                self.assertTrue(all(event["kind"] == "insert" and lo <= event["start_m"]
                                    and event["start_m"] + event["length_m"] <= hi
                                    for event in inserted))

            with self.subTest(family="micro_partial_drain", variant=variant):
                commands, meta, _ = generated[("micro_partial_drain", variant)]
                drain = phase(meta, "partial_drain")
                body = commands_in(commands, drain)
                self.assertEqual(drain["end_op"], len(commands))
                self.assertTrue(all(command < 0 for command in body))
                self.assertGreaterEqual(len(body), 1)
                self.assertLessEqual(len(body), 15)
                self.assertGreater(meta["final_volume_m"], 0)
                self.assertGreaterEqual(meta["final_volume_m"], meta["target_capacity_m"] // 2)
                self.assertLess(meta["final_volume_m"], meta["peak_volume_m"])

        self.assertGreaterEqual(len(neighbor_pair_starts), 2,
                                "neighbor coalescence should move across initial positions")
        self.assertTrue(any(index > 0 for index in neighbor_pair_starts),
                        "neighbor pair must not always be the first two PIDs")

    def test_certificate_verifier_rejects_mutated_geometry_and_termination(self):
        spec = next(s for s in make_micro_specs() if s["family"] == "micro_gap_refill")
        commands, metadata = generate_micro(spec)
        moved = copy.deepcopy(metadata)
        moved["layout_witness"]["placements"][0]["start_m"] += 1
        with self.assertRaises(ValueError):
            verify_layout_witness(commands, moved)
        wrong_pid = copy.deepcopy(metadata)
        delete_index = next(i for i, command in enumerate(commands) if command < 0)
        wrong_pid["layout_witness"]["events"][delete_index]["pid"] += 1000
        with self.assertRaises(ValueError):
            verify_layout_witness(commands, wrong_pid)
        appended = copy.deepcopy(metadata)
        appended["termination"]["appended_deletions"] = 1
        with self.assertRaises(ValueError):
            verify_layout_witness(commands, appended)

    def test_generator_source_has_no_filesystem_or_process_imports(self):
        source = Path(__file__).with_name("micro.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {"os", "pathlib", "subprocess", "socket", "urllib", "requests", "sqlite3"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & forbidden)


if __name__ == "__main__":
    unittest.main()

