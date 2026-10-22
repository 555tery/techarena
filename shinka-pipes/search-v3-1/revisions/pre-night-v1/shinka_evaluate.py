"""Publish future native results and paired feedback to a Shinka generation."""

import argparse
import json
from pathlib import Path
import uuid

from support import ROOT, digest
from research import VERSION, atomic_json, enrich_metrics, read_programs
from research_runner import checked_run
from selection import load_policy
from selection_runtime import enrich_selection, prepared_manifest


def evaluate_for_shinka(program, output, engine=None):
    program, output = Path(program).resolve(), Path(output).resolve()
    folder = program.parent
    run, manifest = checked_run(folder.parent)
    if (output != folder / "results" or program.name != "main.cpp"
            or not folder.name.startswith("gen_") or not folder.name[4:].isdigit()):
        raise ValueError("unexpected research generation paths")
    generation = int(folder.name[4:])
    if not 0 <= generation < manifest["target_generations"]:
        raise ValueError("generation is outside the authorized budget")
    if generation == 0 and digest(program) != manifest.get("source_sha256"):
        raise ValueError("baseline differs from the separately selected seed")
    if any((output / name).exists() for name in ("metrics.json", "correct.json", "native-evaluation.json")):
        raise ValueError("refusing to replace completed or previously started evaluation")
    context = None
    if generation:
        context = json.loads((folder / "research-context.json").read_text())
        if (context.get("version") != VERSION or context.get("generation") != generation
                or context.get("source_sha256") != digest(program)):
            raise ValueError("candidate lacks matching research proposal provenance")
    stage = ROOT / "evaluations" / run.name / folder.name / uuid.uuid4().hex
    status = {"status": "running", "generation": generation, "native_results_dir": str(stage)}
    atomic_json(output / "native-evaluation.json", status)
    if engine is None:
        from evaluator import evaluate
        engine = evaluate
    try:
        engine(program, stage, workers=2)
        metrics = json.loads((stage / "metrics.json").read_text())
        correct = json.loads((stage / "correct.json").read_text())
        if type(correct.get("correct")) is not bool:
            raise ValueError("missing evaluator correctness decision")
        if correct["correct"] and context:
            enrich_metrics(metrics, context, read_programs(run), manifest["search_manifest_sha256"])
        if correct["correct"]:
            search, search_sha = prepared_manifest(run)
            enrich_selection(metrics, generation, digest(program), read_programs(run) if generation else [],
                             search, search_sha, load_policy())
        metrics["native_evaluation_dir"] = str(stage)
        metrics["research_protocol"] = VERSION
        atomic_json(output / "metrics.json", metrics)
        atomic_json(output / "correct.json", correct)
        status.update(status="complete", correct=correct["correct"])
    except Exception as exc:
        # Never turn a bookkeeping failure into a partly scored success.
        status.update(status="research_error", error=str(exc))
        raise
    finally:
        atomic_json(output / "native-evaluation.json", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program_path", required=True)
    parser.add_argument("--results_dir", required=True)
    args = parser.parse_args()
    evaluate_for_shinka(args.program_path, args.results_dir)


if __name__ == "__main__":
    main()
