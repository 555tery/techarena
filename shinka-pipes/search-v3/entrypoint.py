#!/usr/bin/env python3
"""Prepared Shinka evaluator adapter. --check is read-only; no run launcher here."""

import argparse
from pathlib import Path

from evaluator import evaluate, load_search


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--program_path", type=Path)
    parser.add_argument("--results_dir", type=Path)
    args = parser.parse_args()
    if args.check:
        if args.program_path or args.results_dir:
            parser.error("--check cannot execute a candidate")
        manifest = load_search()
        print(f"SEARCH-v3 ready: {manifest['case_count']} main cases; F/T; workers=2; candidate_evaluations=0")
        return 0
    if not args.program_path or not args.results_dir:
        parser.error("provide --check or an explicitly authorized candidate and results directory")
    evaluate(args.program_path, args.results_dir, workers=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
