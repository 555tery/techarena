#!/usr/bin/env python3
"""Future copied Shinka adapter; its runner must set PIPES_SEARCH_V31_ROOT."""

import os
from pathlib import Path
import sys

support = Path(os.environ.get("PIPES_SEARCH_V31_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(support))
from shinka_evaluate import main


if __name__ == "__main__":
    raise SystemExit(main())
