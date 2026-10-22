"""Constrain Shinka's Headless calls to local, read-only Codex subscription use."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from local_runtime import HEADLESS, TASK, check_prerequisites, subscription_environment


def check_initial_baseline(work_dir: str) -> None:
    results = Path(work_dir).resolve() / "gen_0/results"
    try:
        correct = json.loads((results / "correct.json").read_text())
        metrics = json.loads((results / "metrics.json").read_text())
        snapshot = json.loads((TASK / "snapshot.json").read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError("Model call blocked: initial search baseline has no valid evaluator report.") from exc
    if (correct.get("correct") is not True or metrics.get("suite") != "search"
            or metrics.get("public", {}).get("valid_cases") != 32
            or metrics.get("manifest_sha256") != snapshot["snapshot_sha256"]["data/search/manifest.json"]):
        raise RuntimeError("Model call blocked: initial search baseline did not pass all 32 cases.")


def main() -> int:
    env = subscription_environment()
    if sys.argv[1:] == ["--check"]:
        check_prerequisites(env)
        print("Local Codex + Headless available; ChatGPT auth; no model or Docker call.")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", choices=["codex"])
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--allow", choices=["read-only"], required=True)
    parser.add_argument("--usage", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--reasoning-effort")
    args = parser.parse_args()
    check_initial_baseline(args.work_dir)
    check_prerequisites(env)
    node = shutil.which("node", path=env["PATH"])
    assert node is not None
    os.execve(node, [node, str(HEADLESS), *sys.argv[1:], "--billing", "subscription"], env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
