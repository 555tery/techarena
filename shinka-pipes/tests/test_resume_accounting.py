"""No model/evaluator run: prove one terminal failure consumes one persisted slot."""

import asyncio
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resume_current import install_terminal_failure_accounting


class ResumeAccountingTests(unittest.TestCase):
    def test_failure_is_persisted_once_without_repeating_original_accounting(self):
        with tempfile.TemporaryDirectory(prefix="pipes-resume-accounting-") as temporary:
            db = sqlite3.connect(":memory:")
            db.execute("CREATE TABLE programs (generation INTEGER)")
            recorder = AsyncMock()
            async def persist(**kwargs):
                db.execute("INSERT INTO programs VALUES (?)", (kwargs["generation"],))
                return object()
            writer = AsyncMock(side_effect=persist)
            runner = types.SimpleNamespace(
                _record_terminal_failed_proposal=recorder,
                _persist_failed_generation=writer,
                async_db=types.SimpleNamespace(get_persisted_generation_ids_async=AsyncMock(
                    side_effect=lambda: [r[0] for r in db.execute("SELECT generation FROM programs")]
                )), results_dir=temporary,
            )
            install_terminal_failure_accounting(runner)
            asyncio.run(runner._record_terminal_failed_proposal(generation=12, api_costs=0.1))
            self.assertEqual(recorder.await_count, 1)
            self.assertEqual(writer.await_count, 1)
            self.assertEqual(db.execute("SELECT count(*) FROM programs").fetchone()[0], 1)
            # If a row already exists, no second Program/cost writer is invoked.
            asyncio.run(runner._record_terminal_failed_proposal(generation=12, api_costs=0.1))
            self.assertEqual(writer.await_count, 1)
            self.assertEqual(recorder.await_count, 1)
            db.close()


if __name__ == "__main__":
    unittest.main()
