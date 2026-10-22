#!/usr/bin/env python3
"""Run the independent online oracle over the previously frozen 10 streams."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT))
from review import audit_streams  # noqa: E402

STRATEGIES = PROJECT / "results/pipes/improvement/strategies"
MANIFEST = STRATEGIES / "robustness_manifest.json"
INPUTS = STRATEGIES / "robustness_inputs"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_robustness_stream_oracle.py BINARY JSON_OUTPUT")
    binary = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2])
    manifest = json.loads(MANIFEST.read_text())
    if len(manifest["streams"]) != 10:
        raise ValueError("expected exactly 10 frozen robustness inputs")
    results = []
    for stream in manifest["streams"]:
        input_path = INPUTS / f"{stream['name']}.in"
        actual_hash = sha256(input_path)
        if actual_hash != stream["sha256"]:
            raise ValueError(f"input hash mismatch for {stream['name']}")
        case = audit_streams.parse_test(input_path)
        if len(case.commands) != stream["operation_count"]:
            raise ValueError(f"operation count mismatch for {stream['name']}")
        case.name = stream["name"]
        result = audit_streams.run_case(binary, case, 2.0)
        result["input_sha256"] = actual_hash
        result["seed"] = stream["seed"]
        if result["responses"] != result["commands"]:
            raise ValueError(f"response count mismatch for {stream['name']}")
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if len(results) != 10 or any(row["verdict"] != "OK" for row in results):
        raise ValueError("one or more robustness streams failed")
    report = {
        "binary": str(binary),
        "binary_sha256": sha256(binary),
        "source": str((PROJECT / "src/pipes.cpp").resolve()),
        "source_sha256": sha256(PROJECT / "src/pipes.cpp"),
        "suite_manifest_sha256": sha256(MANIFEST),
        "case_count": len(results),
        "command_count": sum(row["commands"] for row in results),
        "response_count": sum(row["responses"] for row in results),
        "pass": sum(row["verdict"] == "OK" for row in results),
        "fail": sum(row["verdict"] != "OK" for row in results),
        "cases": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
