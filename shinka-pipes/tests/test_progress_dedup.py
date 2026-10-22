"""The repaired generation ledger must not duplicate failed nodes in the UI."""

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from progress_ui import Handler, visualization


class ProgressDedupTests(unittest.TestCase):
    def test_only_unpersisted_attempts_get_virtual_nodes(self):
        with tempfile.TemporaryDirectory(prefix="pipes-progress-test-") as temporary:
            path = Path(temporary) / "db.sqlite"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE programs(generation INTEGER)")
                db.execute("INSERT INTO programs VALUES(1)")
            nodes = [{"generation": 1, "id": "virtual1"}, {"generation": 2, "id": "virtual2"}]
            handler = Handler.__new__(Handler)
            with patch.object(visualization.DatabaseRequestHandler, "_load_failed_proposal_nodes", return_value=nodes):
                self.assertEqual(handler._load_failed_proposal_nodes(str(path)), [nodes[1]])


if __name__ == "__main__":
    unittest.main()
