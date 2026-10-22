#!/usr/bin/env python3
"""Shinka fitness entrypoint: fixed SEARCH corpus only; no validation/Open15."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from synthetic_eval import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    args = parser.parse_args()
    evaluate(Path(args.program_path), Path(args.results_dir), split="search")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
