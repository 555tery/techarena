#!/usr/bin/env python3
"""Tiny fixtures only: never draws final entropy or writes final input files."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate as g


class TinyTests(unittest.TestCase):
    def test_hand_built_replay(self):
        commands = [20, 7, -1, 3, -2, -3]
        stats = g.analyse_commands(commands, [1, 2, 3, 6])
        self.assertEqual(stats["2"]["live_volume"], 27)
        self.assertEqual(stats["3"]["live_volume"], 7)
        self.assertTrue(stats["6"]["zero_final_volume"])
        self.assertEqual(g.encoded_input(commands), b"1\n6\n20\n7\n-1\n3\n-2\n-3\n")
        for bad in ([0], [-1], [1, -1, -1], [41]):
            with self.assertRaises(ValueError):
                g.analyse_commands(bad, [len(bad)])

    def test_tiny_families_and_literal_prefixes(self):
        design = json.loads((g.HERE / "design.json").read_text())
        self.assertEqual(len(design["families"]), 12)
        for fidx, spec in enumerate(design["families"]):
            for rep in range(4):
                n = 80  # synthetic fixture, not any final long stream
                seed = 9000 + fidx * 4 + rep
                commands, extras = g.build_stream(spec["id"], n, seed, rep)
                self.assertEqual(len(commands), n)
                self.assertEqual(commands, g.build_stream(spec["id"], n, seed, rep)[0])
                checkpoints = [16, 32, 48, 64, 80]
                stats = g.analyse_commands(commands, checkpoints)
                for cut in checkpoints:
                    raw = g.encoded_input(commands[:cut]).decode().splitlines()
                    self.assertEqual(raw[:2], ["1", str(cut)])
                    self.assertEqual(list(map(int, raw[2:])), commands[:cut])
                if spec["scale"] == "micro":
                    self.assertLessEqual(stats["80"]["max_live_volume"], 60)
                if spec["id"] == "prefix_branch":
                    self.assertEqual(extras["common_prefix_sha256"], hashlib.sha256(("\n".join(map(str, commands[:20])) + "\n").encode()).hexdigest())
        branches = [g.build_stream("prefix_branch", 80, 1234, r)[0] for r in range(4)]
        self.assertTrue(all(x[:20] == branches[0][:20] for x in branches))
        self.assertTrue(any(x[20:] != branches[0][20:] for x in branches[1:]))

    def test_freeze_guard(self):
        with tempfile.TemporaryDirectory(dir=g.HERE) as tmp:
            p = Path(tmp) / "freeze.json"
            payload = dict(schema_version=1, design_approved=True,
                           generator_sha256=g.sha(Path(g.__file__).read_bytes()),
                           design_sha256=g.sha((g.HERE / "design.json").read_bytes()),
                           solver_sha256={x: "a" * 64 for x in ("trial22", "bf", "ss")})
            p.write_text(json.dumps(payload))
            self.assertEqual(g.read_freeze(p)[0], payload)
            payload["generator_sha256"] = "b" * 64
            p.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                g.read_freeze(p)

    def test_cli_refuses_before_entropy(self):
        with tempfile.TemporaryDirectory(dir=g.HERE) as tmp:
            root = Path(tmp)
            with patch.object(g.secrets, "token_hex") as entropy:
                with self.assertRaises(SystemExit):
                    g.main(["--output", str(root / "new"), "--freeze", str(root / "missing.json")])
                with self.assertRaises(SystemExit):
                    g.main(["--output", str(root), "--freeze", str(root / "missing.json")])
                entropy.assert_not_called()
            self.assertFalse((root / "new").exists())


if __name__ == "__main__":
    unittest.main()
