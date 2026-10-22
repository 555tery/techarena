"""Subscription bridge with an independent SEARCH-v3 baseline/provenance gate."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from support import ROOT, PARENT, digest, reference


def check_baseline(work_dir):
    run = Path(work_dir).resolve()
    if run == ROOT / "runs" or not run.is_relative_to(ROOT / "runs"):
        raise RuntimeError("SEARCH-v3 bridge only accepts its own run namespace")
    manifest = json.loads((run / "run-manifest.json").read_text())
    generations = manifest.get("target_generations")
    if (manifest.get("status") != "running" or manifest.get("suite") != "search-v3"
            or manifest.get("billing") != "subscription" or type(generations) is not int or generations < 2):
        raise RuntimeError("a separately authorized SEARCH-v3 run and budget are required")
    protocol = json.loads((ROOT / "protocol.json").read_text())
    correct = json.loads((run / "gen_0/results/correct.json").read_text())
    metrics = json.loads((run / "gen_0/results/metrics.json").read_text())
    snapshot_hash = digest(ROOT / "snapshot.json")
    evaluator_hash = digest(ROOT / "evaluator.py")
    source_hash = digest(run / "gen_0/main.cpp")
    if (correct.get("correct") is not True or metrics.get("suite") != "search"
            or metrics.get("corpus_version") != "search-v3" or metrics.get("public", {}).get("valid_cases") != 128
            or metrics.get("manifest_sha256") != protocol["manifest_sha256"]["search"]
            or manifest.get("search_manifest_sha256") != protocol["manifest_sha256"]["search"]
            or metrics.get("program_sha256") != source_hash or manifest.get("source_sha256") != source_hash
            or metrics.get("snapshot_sha256") != snapshot_hash or manifest.get("snapshot_sha256") != snapshot_hash
            or metrics.get("evaluator_sha256") != evaluator_hash or manifest.get("evaluator_sha256") != evaluator_hash
            or metrics.get("native_workers") != 2 or metrics.get("stress_evaluated") is not False):
        raise RuntimeError("model call blocked: no matching full SEARCH-v3 main baseline")


def main():
    if sys.argv[1:] == ["--check"]:
        from evaluator import verify_snapshot
        verify_snapshot()
        print("SEARCH-v3 bridge support verified; no auth commands, model call or candidate execution.")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", choices=["codex"])
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--allow", choices=["read-only"], required=True)
    parser.add_argument("--usage", action="store_true")
    parser.add_argument("--model", choices=["gpt-6-astra"], required=True)
    parser.add_argument("--reasoning-effort", choices=["xhigh"], required=True)
    args = parser.parse_args()
    from evaluator import verify_snapshot
    verify_snapshot()
    check_baseline(args.work_dir)
    reference()
    sys.path.insert(0, str(PARENT))
    from local_runtime import HEADLESS, check_prerequisites, subscription_environment
    env = subscription_environment()
    env["PIPES_SEARCH_V3_ROOT"] = str(ROOT)
    env["SHINKA_HEADLESS_COMMAND"] = str(ROOT / "headless.sh")
    check_prerequisites(env)
    node = shutil.which("node", path=env["PATH"])
    os.execve(node, [node, str(HEADLESS), *sys.argv[1:], "--fast", "--billing", "subscription"], env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
