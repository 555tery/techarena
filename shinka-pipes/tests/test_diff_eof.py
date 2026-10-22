"""Regression checks for the real Shinka diff route; no candidate execution."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from synthetic_eval import check_candidate
import synthetic_eval
from shinka.edit.apply_diff import apply_diff_patch


class DiffCompatibilityTests(unittest.TestCase):
    def test_real_diff_output_passes_immutable_guard_with_optional_eof_newline(self):
        initial = ("#include <iostream>\n// EVOLVE-BLOCK-START\nint x = 1;\n"
                   "// EVOLVE-BLOCK-END\nint main() { return x; }\n")
        diff = "<<<<<<< SEARCH\nint x = 1;\n=======\nint x = 2;\n>>>>>>> REPLACE\n"
        updated, count, _, error, _, _ = apply_diff_patch(diff, original_str=initial, language="cpp", verbose=False)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertFalse(updated.endswith("\n"))
        with tempfile.TemporaryDirectory(prefix="pipes-diff-regression-") as tmp:
            task = Path(tmp)
            (task / "initial.cpp").write_text(initial)
            candidate = task / "candidate.cpp"
            with patch.object(synthetic_eval, "TASK", task):
                for text in (updated, updated+"\n"):
                    candidate.write_text(text)
                    check_candidate(candidate)
                for text in (updated.replace("return x;", "return 0;"),
                             updated.replace("#include <iostream>", "#include <fstream>"),
                             updated.replace("EVOLVE-BLOCK-END", "other-marker")):
                    candidate.write_text(text)
                    with self.assertRaises(ValueError):
                        check_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
