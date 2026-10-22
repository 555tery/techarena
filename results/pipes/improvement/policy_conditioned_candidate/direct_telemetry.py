#!/usr/bin/env python3
"""Direct solver replay to verify selector counters and action flips."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs/preflight/200000_uniform_random.in"
BASELINE = HERE / "bin/frozen_final_linux"
CANDIDATE = HERE / "bin/policy_conditioned_linux_diag"


def run(binary: Path, input_text: bytes) -> tuple[bytes, str]:
    proc = subprocess.run(
        [str(binary)], input=input_text, capture_output=True, check=True
    )
    return proc.stdout, proc.stderr.decode("utf-8", errors="replace")


def main() -> None:
    tokens = INPUT.read_text(encoding="ascii").split()
    count = int(tokens[1])
    commands = [int(token) for token in tokens[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError("input command count or terminator mismatch")
    solver_input = ("\n".join(map(str, commands)) + "\n").encode("ascii")
    baseline, baseline_stderr = run(BASELINE, solver_input)
    candidate, candidate_stderr = run(CANDIDATE, solver_input)
    baseline_lines = baseline.splitlines()
    candidate_lines = candidate.splitlines()
    if len(baseline_lines) != len(candidate_lines):
        raise RuntimeError("baseline and candidate emitted different reply counts")
    expected_lines = len(commands) - 1
    if len(candidate_lines) != expected_lines:
        raise RuntimeError(f"candidate reply count {len(candidate_lines)} != {expected_lines}")
    changed = [
        {"reply_index": index + 1, "baseline": old.decode(), "candidate": new.decode()}
        for index, (old, new) in enumerate(zip(baseline_lines, candidate_lines))
        if old != new
    ]
    result = {
        "input": str(INPUT.relative_to(ROOT)),
        "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "command_count": count,
        "baseline_binary_sha256": hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
        "candidate_binary_sha256": hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
        "baseline_stdout_sha256": hashlib.sha256(baseline).hexdigest(),
        "candidate_stdout_sha256": hashlib.sha256(candidate).hexdigest(),
        "reply_count": len(candidate_lines),
        "different_replies": len(changed),
        "first_different_replies": changed[:10],
        "candidate_stderr": candidate_stderr.strip(),
        "baseline_stderr": baseline_stderr.strip(),
    }
    out = HERE / "logs/direct_telemetry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
