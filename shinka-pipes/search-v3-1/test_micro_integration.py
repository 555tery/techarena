"""Corpus revision contracts; no candidate, model or held-out input is used."""

from collections import Counter
import json
from pathlib import Path
import unittest

from generate import MAIN, STRESS, generate_case, make_specs
from micro import MICRO_FAMILIES, verify_layout_witness
from support import ROOT, digest


class MicroIntegrationTests(unittest.TestCase):
    def test_original_main_inputs_and_stress_remain_unchanged(self):
        previous = ROOT / "revisions/pre-micro-r1"
        old = json.loads((previous / "task/data/search/manifest.json").read_text())
        current = json.loads((MAIN / "manifest.json").read_text())
        self.assertEqual(current["cases"][:128], old["cases"])
        for case in old["cases"]:
            self.assertEqual(digest(MAIN / case["file"]), case["sha256"])
        self.assertEqual(digest(STRESS / "manifest.json"), digest(previous / "stress/data/manifest.json"))
        self.assertEqual(digest(ROOT / "fitness.py"), digest(previous / "fitness.py"))
        for case in json.loads((STRESS / "manifest.json").read_text())["cases"]:
            self.assertEqual(digest(STRESS / case["file"]), case["sha256"])

    def test_all_micro_inputs_reproduce_and_have_feasible_capacity(self):
        manifest = json.loads((MAIN / "manifest.json").read_text())
        micro = {c["id"]: c for c in manifest["cases"] if c["family"] in MICRO_FAMILIES}
        self.assertEqual(len(micro), 24)
        self.assertEqual(Counter(c["stats"]["volume_lower_bound"] for c in micro.values()), {20: 8, 40: 8, 60: 8})
        self.assertTrue(any(c["operations"] < 32 for c in micro.values()))
        for spec in make_specs("search"):
            if spec["id"] not in micro:
                continue
            commands, actual, stats = generate_case(spec)
            saved = micro[spec["id"]]
            self.assertEqual(stats, saved["stats"])
            self.assertEqual(actual["layout_witness"], saved["layout_witness"])
            self.assertEqual(actual["termination"], saved["termination"])
            tokens = (MAIN / saved["file"]).read_text().split()
            self.assertEqual(commands, list(map(int, tokens[2:2 + int(tokens[1])])))
            verify_layout_witness(commands, saved)
            self.assertLessEqual(len(commands), 128)
            self.assertGreater(stats["deletions"], 0)
            self.assertGreater(stats["final_live_volume"], 0)
            self.assertGreaterEqual(saved["final_to_bound"], .5)

    def test_protocol_and_future_baseline_require_the_whole_new_corpus(self):
        manifest = json.loads((MAIN / "manifest.json").read_text())
        protocol = json.loads((ROOT / "protocol.json").read_text())
        self.assertEqual((manifest["case_count"], len(manifest["families"])), (152, 38))
        self.assertEqual((protocol["case_count"], protocol["family_count"]), (152, 38))
        self.assertEqual(protocol["manifest_sha256"]["search"], digest(MAIN / "manifest.json"))
        self.assertEqual(protocol["family_weights"], "1/38")
        self.assertEqual(Counter(c["family"] for c in manifest["cases"]), {f: 4 for f in manifest["families"]})
        self.assertEqual(protocol["native_workers"], 2)
        self.assertFalse(protocol["baseline_evaluated"])
        self.assertFalse(protocol["stress_in_fitness"])
        self.assertFalse(protocol["stress_in_feedback"])
        self.assertEqual(protocol["authorized_generations"], 800)
        plan = json.loads((ROOT / "next-run.json").read_text())
        self.assertEqual((plan["model"], plan["reasoning_effort"], plan["service_tier"]), ("gpt-6.1-sol", "xhigh", "default"))
        self.assertEqual(plan["baseline_source"], "seeds/strong_v2_gen17.cpp")
        self.assertEqual(plan["authorized_generations"], 800)
        self.assertTrue(plan["launch_authorized"])
        self.assertFalse(plan["open15_access"])
        self.assertFalse(plan["validation_access"])


if __name__ == "__main__":
    unittest.main()
