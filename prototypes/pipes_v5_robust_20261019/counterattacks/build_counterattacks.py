#!/usr/bin/env python3
"""Build two bounded counterattacks against the frozen v5 repair candidates.

The inputs use exact public prefixes. Metrics for both candidate binaries and
causal Best-Fit are measured by their batch executables, not inferred from a
simulated fallback policy. This is a local counterexample generator, not an
official interactor run.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROBUST = HERE.parent
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_public(case):
    toks = list(map(int, (REPO / f"data/pipes/open/{case}.in").read_text().split()))
    n = toks[1]
    commands = toks[2:2+n]
    assert len(commands) == n
    return commands


def run_solver(path, commands, probe=False):
    argv = [str(path)]
    if probe:
        argv += ["bestfit", str(REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt")]
    run = subprocess.run(argv, input="\n".join(map(str, commands + [0])) + "\n",
                         capture_output=True, text=True, check=True, timeout=30)
    lines = run.stdout.splitlines()
    assert len(lines) == len(commands), (path, len(lines), len(commands))
    trench, volume, next_pid = 0, 0, 0
    active, placements, trace = {}, {}, []
    for c, line in zip(commands, lines):
        if c > 0:
            digs, start = map(int, line.split())
            trench += 20 * digs
            assert start + c <= trench, (path, c, line, trench)
            assert all(start + c <= a or b <= start for a, b in placements.values()), (path, c, line)
            next_pid += 1
            active[next_pid] = c
            placements[next_pid] = (start, start+c)
            volume += c
        else:
            start = int(line)
            old = placements.pop(-c)
            assert start == old[0], (path, c, line, old)
            active.pop(-c)
            volume -= old[1]-old[0]
        trace.append(trench)
    return {"T_m": trench, "F_m": volume, "KPI": volume / trench if trench else 0,
            "trace_T_m": trace, "stderr": run.stderr.strip()}


def encode_input(commands):
    return "1\n%d\n" % len(commands) + "\n".join(map(str, commands)) + "\n"


def first_table_decision(case, cut):
    tables = json.loads((ROBUST / "candidate-tables.json").read_text())
    return tables[case-1][0][cut]


def main():
    cases = [
        {"name": "counterattack-open2-p4-mixed-fill", "case": 2, "cut": 4,
         "suffix": [10, 3],
         "mechanism": "quiet-prefix geometry: the replayed pipes leave a 9m largest gap, while causal BF leaves 13m; after divergence both fallbacks must grow for size 10, then fit size 3 without further trench growth.",
         "purpose": "Open2 quiet-prefix small-geometry trap for Best-Fit and First-Fit fallbacks"},
        {"name": "counterattack-open10-p5-24", "case": 10, "cut": 5,
         "suffix": [24],
         "mechanism": "the repaired Open10 table preserves its first four compact placements but reserves a remote 1m pipe at command 5; an off-table 24m allocation retains that trench under either fallback.",
         "purpose": "residual Open10 reserve shifted from the prior p3 trigger to p5"},
    ]
    candidates = ROBUST / "candidate/solver"
    firstfit = ROBUST / "candidate-firstfit/solver"
    bf_probe = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
    rows = []
    for t in cases:
        public = read_public(t["case"])
        prefix = public[:t["cut"]]
        commands = prefix + t["suffix"]
        assert t["suffix"] and t["suffix"][0] != public[t["cut"]]
        # PID validity and final volume are also enforced by parse_test.
        out = HERE / (t["name"] + ".in")
        out.write_text(encode_input(commands))
        parsed = parse_test(out)
        assert parsed is not None
        actual = {
            "candidate_bestfit_fallback": run_solver(candidates, commands),
            "candidate_firstfit_fallback": run_solver(firstfit, commands),
            "causal_plain_bestfit": run_solver(bf_probe, commands, probe=True),
        }
        prefix_metrics = {
            "candidate": run_solver(candidates, prefix),
            "candidate_firstfit": run_solver(firstfit, prefix),
            "causal_plain_bestfit": run_solver(bf_probe, prefix, probe=True),
        }
        # The target's full prefix trace is checked stepwise against causal BF.
        ratios = [a / b if b else (1.0 if a == 0 else float("inf"))
                  for a, b in zip(prefix_metrics["candidate"]["trace_T_m"],
                                  prefix_metrics["causal_plain_bestfit"]["trace_T_m"])]
        first_divergent = t["suffix"][0]
        row = {
            **t,
            "file": out.name,
            "commands": commands,
            "first_divergent_command": first_divergent,
            "expected_table_command_at_cut": first_table_decision(t["case"], t["cut"]),
            "public_prefix_sha256": hashlib.sha256(encode_input(prefix).encode()).hexdigest(),
            "input_sha256": sha(out),
            "max_prefix_ratio_candidate_vs_causal_BF": max(ratios, default=1.0),
            "prefix_metrics": {k: {x: v[x] for x in ["T_m", "F_m", "KPI", "stderr"]}
                               for k, v in prefix_metrics.items()},
            "full_metrics": {k: {x: v[x] for x in ["T_m", "F_m", "KPI", "stderr"]}
                             for k, v in actual.items()},
        }
        rows.append(row)
        print(t["name"], json.dumps(row["full_metrics"], sort_keys=True))

    # Keep the generator's reported new inputs disjoint from both prior suites.
    hashes = {r["input_sha256"] for r in rows}
    for old_manifest in [ROBUST / "new_attacks/manifest.json", REPO / "prototypes/pipes_v5_graves_20261019/manifest.json"]:
        if old_manifest.exists():
            old = json.loads(old_manifest.read_text())
            for item in old.get("tests", []):
                digest = item.get("input_sha256") or item.get("test_sha256")
                assert digest not in hashes, (old_manifest, digest)
    manifest = {
        "title": "Counterattacks against repaired release-v5 candidates",
        "scope": "Two local, legal streams for the frozen candidate and candidate-firstfit batch executables.",
        "candidate_binary_sha256": sha(candidates),
        "candidate_firstfit_binary_sha256": sha(firstfit),
        "causal_bestfit_probe_sha256": sha(bf_probe),
        "search": "Hand-structured quiet Open2 geometry case plus the parent-requested delayed Open10 reserve trigger. Every final target KPI is measured by actual candidate batch execution; plain Best-Fit is measured by allocator-probe.",
        "official_interactor_validation": "pending parent agent",
        "tests": rows,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
