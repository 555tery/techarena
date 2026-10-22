#!/usr/bin/env python3
"""Copy-safe Shinka entrypoint for the separately prepared native evaluator."""

import os
from pathlib import Path
import sys

support = Path(os.environ.get("PIPES_NATIVE_EVALUATOR_ROOT", Path(__file__).resolve().parent))
if not (support / "native_runner.cpp").is_file():
    raise RuntimeError("set PIPES_NATIVE_EVALUATOR_ROOT to evaluator-native")
sys.path.insert(0, str(support))
from evaluate_native import main


if __name__ == "__main__":
    raise SystemExit(main())
