"""Subscription-only bridge for a separately authorized SEARCH-v2 run."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from local_runtime import HEADLESS, check_prerequisites, subscription_environment


def check_baseline(work_dir: str) -> None:
    run = Path(work_dir).resolve()
    runs_root = (ROOT / "runs").resolve()
    if run == runs_root or not run.is_relative_to(runs_root):
        raise RuntimeError("SEARCH-v2 bridge only accepts its own future run directory")
    results = run / "gen_0/results"
    correct = json.loads((results / "correct.json").read_text())
    metrics = json.loads((results / "metrics.json").read_text())
    protocol = json.loads((ROOT / "protocol.json").read_text())
    run_manifest = json.loads((run / "run-manifest.json").read_text())
    snapshot = json.loads((ROOT / "snapshot.json").read_text())
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    snapshot_hash = sha(ROOT / "snapshot.json")
    source_hash = snapshot["files"]["task/initial.cpp"]
    evaluator_hash = snapshot["files"]["evaluator.py"]
    if (run_manifest.get("status") != "running" or run_manifest.get("suite") != "search-v2"
            or run_manifest.get("billing") != "subscription"
            or run_manifest.get("search_manifest_sha256") != protocol["manifest_sha256"]
            or run_manifest.get("snapshot_sha256") != snapshot_hash
            or run_manifest.get("source_sha256") != source_hash
            or run_manifest.get("evaluator_sha256") != evaluator_hash
            or sha(run / "gen_0/main.cpp") != source_hash
            or sha(ROOT / "task/initial.cpp") != source_hash
            or sha(ROOT / "evaluator.py") != evaluator_hash
            or metrics.get("program_sha256") != source_hash
            or metrics.get("evaluator_sha256") != evaluator_hash
            or metrics.get("snapshot_sha256") != snapshot_hash):
        raise RuntimeError("Model call blocked: baseline provenance does not match this frozen v2 run")
    if (correct.get("correct") is not True or metrics.get("suite") != "search"
            or metrics.get("corpus_version") != "search-v2"
            or metrics.get("public", {}).get("valid_cases") != 128
            or metrics.get("manifest_sha256") != protocol["manifest_sha256"]):
        raise RuntimeError("Model call blocked: baseline has not passed all 128 SEARCH-v2 cases")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", choices=["codex"])
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--allow", choices=["read-only"], required=True)
    parser.add_argument("--usage", action="store_true")
    parser.add_argument("--model", choices=["gpt-6-astra"], required=True)
    parser.add_argument("--reasoning-effort", choices=["xhigh"], required=True)
    args = parser.parse_args()
    check_baseline(args.work_dir)
    env = subscription_environment()
    env["PIPES_SEARCH_V2_ROOT"] = str(ROOT)
    check_prerequisites(env)
    node = shutil.which("node", path=env["PATH"])
    # Shinka's model URL supports effort only; pin Fast here for SEARCH-v2.
    # Headless translates --fast into Codex -c service_tier="fast".
    os.execve(node, [node, str(HEADLESS), *sys.argv[1:],
                     "--fast", "--billing", "subscription"], env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
