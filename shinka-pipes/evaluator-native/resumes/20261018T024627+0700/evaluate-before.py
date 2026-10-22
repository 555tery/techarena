#!/usr/bin/env python3
"""Fixed SEARCH-v2 entrypoint, also safe when Shinka copies this file."""

import argparse
import os
from pathlib import Path
import sys

support = Path(os.environ.get("PIPES_SEARCH_V2_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(support))
from evaluator import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    args = parser.parse_args()
    evaluate(Path(args.program_path), Path(args.results_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
