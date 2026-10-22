"""Separate manual validation. Default checks inputs; --run evaluates a locked source."""

import argparse
import json
from pathlib import Path
import shutil

from synthetic_eval import TASK, VALIDATION, digest, evaluate, load_suite


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--program_path", type=Path)
    parser.add_argument("--results_dir", type=Path)
    args = parser.parse_args()
    if args.run and (args.program_path is None or args.results_dir is None):
        parser.error("--run requires --program_path and a new --results_dir")
    manifest = load_suite(VALIDATION, "validation")
    if not args.run:
        print(json.dumps({"status": "validation_inputs_checked_only", "cases": manifest["case_count"],
                          "families": len(manifest["families"]), "candidate_evaluations": 0}))
        return 0
    args.results_dir.mkdir(parents=True, exist_ok=False)
    locked = args.results_dir / "candidate.cpp"
    shutil.copyfile(args.program_path, locked)
    lock = {"candidate_sha256": digest(locked), "baseline_sha256": digest(TASK / "initial.cpp"),
            "validation_manifest_sha256": digest(VALIDATION / "manifest.json"),
            "feedback_to_search": False,
            "selection_policy": "Candidate selected before validation. Repeated adaptive use compromises this split."}
    (args.results_dir / "selection-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    baseline_ok = evaluate(TASK / "initial.cpp", args.results_dir / "baseline", "validation")
    candidate_ok = evaluate(locked, args.results_dir / "candidate", "validation")
    comparison = {**lock, "baseline_correct": baseline_ok, "candidate_correct": candidate_ok}
    if baseline_ok and candidate_ok:
        baseline = json.loads((args.results_dir / "baseline/metrics.json").read_text())
        candidate = json.loads((args.results_dir / "candidate/metrics.json").read_text())
        comparison.update(baseline_score=baseline["combined_score"], candidate_score=candidate["combined_score"],
                          score_delta=candidate["combined_score"] - baseline["combined_score"],
                          family_deltas={f: candidate["family_scores"][f] - baseline["family_scores"][f]
                                         for f in baseline["family_scores"]})
    (args.results_dir / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    return 0 if baseline_ok and candidate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
