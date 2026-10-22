#!/usr/bin/env python3
"""Run paired solver replays and collect rollout telemetry on fresh synthetic inputs."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASELINE = HERE / "bin/frozen_final_linux"
CANDIDATE = HERE / "bin/policy_conditioned_linux_diag"
MANIFEST = HERE / "inputs/preflight_manifest.json"
OUT = HERE / "logs/direct_preflight"
EVAL_RE = re.compile(
    r"policy_eval op=(\d+) baseline_start=(-?\d+) p4_start=(-?\d+) "
    r"unique=(\d+) wins=(\d+) losses=(\d+) delta_sum_m=(-?\d+) choose_p4=(\d+)"
)


def replay(binary: Path, solver_input: bytes) -> tuple[bytes, str]:
    proc = subprocess.run([str(binary)], input=solver_input, capture_output=True, check=True)
    return proc.stdout, proc.stderr.decode("utf-8", errors="replace")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    OUT.mkdir(parents=True, exist_ok=True)
    for item in manifest["records"]:
        path = ROOT / item["file"]
        tokens = path.read_text(encoding="ascii").split()
        count = int(tokens[1])
        commands = [int(token) for token in tokens[2:]]
        if len(commands) != count + 1 or commands[-1] != 0:
            raise RuntimeError(f"bad command count or terminator: {path}")
        payload = ("\n".join(map(str, commands)) + "\n").encode("ascii")
        baseline, _baseline_stderr = replay(BASELINE, payload)
        candidate, candidate_stderr = replay(CANDIDATE, payload)
        baseline_lines = baseline.splitlines()
        candidate_lines = candidate.splitlines()
        if len(baseline_lines) != len(commands) - 1 or len(candidate_lines) != len(commands) - 1:
            raise RuntimeError(f"reply count mismatch on {path}")
        changed = sum(old != new for old, new in zip(baseline_lines, candidate_lines))
        counter_line = next(
            (line for line in candidate_stderr.splitlines() if line.startswith("mc_decisions=")), ""
        )
        evals = [
            {
                "op": int(m.group(1)),
                "baseline_start": int(m.group(2)),
                "p4_start": int(m.group(3)),
                "unique": int(m.group(4)),
                "wins": int(m.group(5)),
                "losses": int(m.group(6)),
                "delta_sum_m": int(m.group(7)),
                "choose_p4": bool(int(m.group(8))),
            }
            for m in EVAL_RE.finditer(candidate_stderr)
        ]
        rows.append({
            "case": item["case"],
            "file": item["file"],
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "operations": count,
            "reply_count": len(candidate_lines),
            "different_replies": changed,
            "baseline_stdout_sha256": hashlib.sha256(baseline).hexdigest(),
            "candidate_stdout_sha256": hashlib.sha256(candidate).hexdigest(),
            "policy_calls": int(re.search(r"policy_calls=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_checks": int(re.search(r"policy_checks=(\d+)", counter_line).group(1)) if counter_line else 0,
            "mc_rollouts": int(re.search(r"mc_rollouts=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_evaluations": int(re.search(r"policy_evaluations=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_p4_choices": int(re.search(r"policy_p4_choices=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_no_pair": int(re.search(r"policy_no_pair=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_nonimproving": int(re.search(r"policy_nonimproving=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_same_action": int(re.search(r"policy_same_action=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_mc": int(re.search(r"policy_skip_mc=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_cadence": int(re.search(r"policy_skip_cadence=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_budget": int(re.search(r"policy_skip_budget=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_history": int(re.search(r"policy_skip_history=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_gaps": int(re.search(r"policy_skip_gaps=(\d+)", counter_line).group(1)) if counter_line else 0,
            "policy_skip_active": int(re.search(r"policy_skip_active=(\d+)", counter_line).group(1)) if counter_line else 0,
            "rollout_evidence": evals,
            "candidate_stderr": candidate_stderr.strip(),
        })
    (OUT / "direct_preflight.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    columns = [key for key in rows[0] if key not in ("rollout_evidence", "candidate_stderr")]
    with (OUT / "direct_preflight.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in rows)
    print("cases", len(rows), "checks", sum(r["policy_checks"] for r in rows),
          "evaluations", sum(r["policy_evaluations"] for r in rows),
          "P4 choices", sum(r["policy_p4_choices"] for r in rows),
          "changed reply lines", sum(r["different_replies"] for r in rows))
    for row in rows:
        if row["policy_evaluations"] or row["policy_p4_choices"]:
            print(row["case"], "checks", row["policy_checks"],
                  "evals", row["policy_evaluations"], "P4", row["policy_p4_choices"],
                  "changed", row["different_replies"], "eval_detail", row["rollout_evidence"])


if __name__ == "__main__":
    main()
