#!/usr/bin/env python3
"""Copy-safe Shinka entrypoint; requires an explicit support root when copied."""

import os
from pathlib import Path
import sys

support = Path(os.environ.get("PIPES_FAST_EVALUATOR_ROOT", Path(__file__).resolve().parent))
if not (support / "fast_harness.py").is_file():
    raise RuntimeError("set PIPES_FAST_EVALUATOR_ROOT to the prepared evaluator-fast directory")
sys.path.insert(0, str(support))
from evaluator import main


if __name__ == "__main__":
    raise SystemExit(main())
