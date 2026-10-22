#!/usr/bin/env python3
"""Publish native SEARCH-v2 results into an explicitly resumed Shinka run."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid


def atomic_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def evaluate_for_shinka(program, output, plan_path, engine=None):
    plan = json.loads(Path(plan_path).read_text())
    support, run = Path(plan["native_root"]).resolve(), Path(plan["run_dir"]).resolve()
    program, output = Path(program).resolve(), Path(output).resolve()
    generation_dir = output.parent
    if generation_dir.parent != run or program != generation_dir / "main.cpp":
        raise ValueError("native Shinka evaluation must use this run's generation source")
    if not generation_dir.name.startswith("gen_"):
        raise ValueError("invalid generation directory")
    generation = int(generation_dir.name.removeprefix("gen_"))
    expected_name = "native-results" if generation == plan["recovered_generation"] else "results"
    if (not plan["first_generation"] <= generation < plan["target_generations"]
            or output.name != expected_name or plan["workers"] != 2
            or plan["suite"] != "search-v2"):
        raise ValueError("evaluation outside the explicitly authorized resume scope")
    for name, expected in plan["native_sha256"].items():
        if hashlib.sha256((support / name).read_bytes()).hexdigest() != expected:
            raise ValueError("native evaluator changed during run: " + name)
    if any((output / name).exists() for name in ("metrics.json", "correct.json", "harness", "native-evaluation.json")):
        raise ValueError("refusing to overwrite evaluation artifacts")
    # Keep the old partial gen4 report in place. Native artifacts have a fresh
    # directory outside the original run, as required by the verified engine.
    stage = support / "shinka-evaluations" / run.name / generation_dir.name / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    status = {"status": "running", "generation": generation, "workers": 2,
              "engine": "native-direct-v1", "native_results_dir": str(stage), "started_at_unix": started}
    atomic_json(output / "native-evaluation.json", status)
    sys.path.insert(0, str(support))
    if engine is None:
        from evaluate_native import evaluate
        engine = evaluate
    engine(program, stage, workers=2)
    metrics = json.loads((stage / "metrics.json").read_text())
    correct = json.loads((stage / "correct.json").read_text())
    if not isinstance(correct.get("correct"), bool) or "combined_score" not in metrics:
        raise ValueError("incomplete native result")
    metrics.update(native_evaluation_dir=str(stage), native_workers=2,
                   shinka_resume_plan=str(Path(plan_path).resolve()))
    if (stage / "harness").is_dir():
        (output / "harness").symlink_to(stage / "harness", target_is_directory=True)
    atomic_json(output / "metrics.json", metrics)
    atomic_json(output / "correct.json", correct)
    status.update(status="complete", correct=correct["correct"], finished_at_unix=time.time(),
                  wall_s=time.time() - started)
    atomic_json(output / "native-evaluation.json", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    args = parser.parse_args()
    evaluate_for_shinka(args.program_path, args.results_dir, os.environ["PIPES_NATIVE_SHINKA_PLAN"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
