"""Adversarial fixed tests against snapshots of actual Open15-overfit releases."""
import base64
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET = REPO / "prototypes/pipes_open15_overfit_20261019/continuation"
OLD = REPO / "prototypes/pipes_prefix_shock_20261019"
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public(case):
    path = REPO / "data/pipes/open" / f"{case}.in"
    tokens = path.read_text().split()
    return list(map(int, tokens[2:2 + int(tokens[1])]))


def decode(path):
    source = path.read_text()
    start = source.index("static const char* encoded[]={") + len("static const char* encoded[]={")
    end = source.index("};", start)
    tables = []
    for group in source[start:end].split(","):
        blob = base64.b64decode("".join(re.findall(r'"([A-Za-z0-9+/=]*)"', group)))
        offset = 0
        def var():
            nonlocal offset
            value = shift = 0
            while True:
                byte = blob[offset]
                offset += 1
                value |= (byte & 127) << shift
                if byte < 128:
                    return value
                shift += 7
        def signed():
            value = var()
            return -(value + 1) // 2 if value & 1 else value // 2
        n = var()
        commands, positions = [], []
        position = 0
        for _ in range(n):
            command = signed()
            commands.append(command)
            if command > 0:
                position += signed()
                positions.append(position)
            else:
                positions.append(None)
        assert offset == len(blob)
        tables.append((commands, positions))
    assert len(tables) == 15
    return tables


def main():
    snapshots = HERE / "snapshots"
    snapshots.mkdir(exist_ok=True)
    profiles = {}
    decoded = {}
    for version in ["release-v1", "release-v2", "release-v3"]:
        origin = TARGET / version
        build = json.loads((origin / "build.json").read_text())
        assert sha(origin / "solution.cpp") == build["source_sha256"]
        assert sha(origin / "solver") == build["binary_sha256"]
        target = snapshots / version
        if target.exists():
            assert sha(target / "solution.cpp") == build["source_sha256"]
            assert sha(target / "solver") == build["binary_sha256"]
        else:
            target.mkdir()
            for name in ["solution.cpp", "solver", "build.json", "plan-audit.json"]:
                shutil.copy2(origin / name, target / name)
        decoded[version] = decode(target / "solution.cpp")
        audit = json.loads((target / "plan-audit.json").read_text())
        profiles[version] = {"origin": str(origin.relative_to(REPO)), **build,
                             "audited_open15_score": audit["weighted_score"],
                             "snapshot": str(target.relative_to(REPO))}
    # Preserve later snapshots evaluated on the already-fixed suite. They did
    # not participate in selecting these inputs.
    for target in sorted(snapshots.glob("release-*")):
        if target.name in profiles:
            continue
        build = json.loads((target / "build.json").read_text())
        assert sha(target / "solution.cpp") == build["source_sha256"]
        assert sha(target / "solver") == build["binary_sha256"]
        audit = json.loads((target / "plan-audit.json").read_text())
        profiles[target.name] = {"origin": str((TARGET / target.name).relative_to(REPO)), **build,
                                 "audited_open15_score": audit["weighted_score"],
                                 "snapshot": str(target.relative_to(REPO)),
                                 "input_selection": "Added after the six-input suite was fixed."}
    all_commands = {case: public(case) for case in range(1, 16)}
    # Causal BF engine: no replay decisions are used in bestfit mode.
    bf_trenches = {}
    for case, commands in all_commands.items():
        response = subprocess.run([str(OLD / "allocator-probe"), "bestfit", str(OLD / "tape.txt")],
            input="\n".join(map(str, commands + [0])) + "\n", text=True,
            capture_output=True, check=True, timeout=20).stdout.splitlines()
        assert len(response) == len(commands)
        trench = 0
        trajectory = []
        for command, line in zip(commands, response):
            if command > 0:
                trench += 20 * int(line.split()[0])
            trajectory.append(trench)
        bf_trenches[case] = trajectory
    candidates = []
    for version, tables in decoded.items():
        for case, (commands, positions) in enumerate(tables, 1):
            assert commands == all_commands[case]
            active = {}
            pid = trench = 0
            best = []
            for cut, (command, position) in enumerate(zip(commands, positions), 1):
                if command > 0:
                    pid += 1
                    active[pid] = command
                    trench = max(trench, (position + command + 19) // 20 * 20)
                else:
                    del active[-command]
                refill = (bf_trenches[case][cut-1] + 39) // 40
                count = cut + len(active) + refill
                if not active or cut == len(commands) or count > 200000:
                    continue
                F = 40 * refill
                ratio = F / max(F, trench)
                best.append((ratio, count, cut, F, trench, len(active)))
            best.sort()
            for row in best[:3]:
                candidates.append({"version": version, "case": case,
                                   "predicted_kpi": row[0], "operations": row[1], "prefix": row[2],
                                   "F": row[3], "replay_prefix_trench": row[4], "live_pids_at_cut": row[5]})
            if version == "release-v3":
                for minimum in [128, 1024, 4096]:
                    eligible = [row for row in best if row[2] >= minimum]
                    if eligible:
                        row = eligible[0]
                        candidates.append({"version": version, "case": case,
                                           "predicted_kpi": row[0], "operations": row[1], "prefix": row[2],
                                           "F": row[3], "replay_prefix_trench": row[4],
                                           "live_pids_at_cut": row[5], "minimum_prefix": minimum})
    candidates.sort(key=lambda c: c["predicted_kpi"])
    (HERE / "prefix-scan.json").write_text(json.dumps(candidates, indent=2) + "\n")
    # Select one independently targeted trap for each release, plus the weakest
    # exact-prefix branch for several public cases of the current release.
    selected = []
    for version in decoded:
        selected.append(next(c for c in candidates if c["version"] == version))
    used = {(c["version"], c["case"], c["prefix"]) for c in selected}
    current_cases = set()
    for c in candidates:
        key = (c["version"], c["case"], c["prefix"])
        if c["version"] == "release-v3" and c["case"] not in current_cases and key not in used:
            selected.append(c)
            used.add(key)
            current_cases.add(c["case"])
        if len(current_cases) >= 4:
            break
    for minimum in [128, 1024, 4096]:
        selected.append(next(c for c in candidates if c.get("minimum_prefix") == minimum))
    inputs = HERE / "suite"
    inputs.mkdir(exist_ok=True)
    test_rows = []
    seen = {}
    for number, candidate in enumerate(selected, 1):
        case, cut = candidate["case"], candidate["prefix"]
        original = all_commands[case]
        seq = original[:cut]
        active = {}
        pid = 0
        for command in seq:
            if command > 0:
                pid += 1
                active[pid] = command
            else:
                del active[-command]
        possible_next = {other[cut] for other in all_commands.values()
                         if len(other) > cut and other[:cut] == seq}
        first_pid = next(p for p in sorted(active) if -p not in possible_next)
        seq += [-first_pid] + [-p for p in sorted(active) if p != first_pid]
        seq += [40] * (candidate["F"] // 40)
        key = tuple(seq)
        if key in seen:
            row = seen[key]
            if candidate["version"] not in row["targeted_releases"]:
                row["targeted_releases"].append(candidate["version"])
            if case not in row["public_cases_sharing_prefix"]:
                row["public_cases_sharing_prefix"].append(case)
            continue
        name = f"grave-{len(test_rows)+1:02d}-open{case}-p{cut}"
        path = inputs / (name + ".in")
        path.write_text(f"1\n{len(seq)}\n" + "\n".join(map(str, seq)) + "\n")
        meta = parse_test(path)
        assert meta["kpi_upper_bound_from_live_volume"] == 1
        assert len(seq) == candidate["operations"]
        assert seq[:cut] == original[:cut] and seq[cut] != original[cut]
        row = {"name": name, **candidate, **meta,
                          "file": str(path.relative_to(REPO)),
                          "first_suffix_command": seq[cut],
                          "targeted_releases": [candidate["version"]],
                          "public_cases_sharing_prefix": [case],
                          "all_public_matching_branches_rejected_at_divergence": True}
        test_rows.append(row)
        seen[key] = row
    manifest = {"scope": "Fixed counterexamples to actual snapshots of the Open15-maximizing method; no target changes, no platform use.",
                "profiles": profiles, "tests": test_rows,
                "mechanism": "An exact public prefix forces the memorized plan's irreversible future reservations; a new valid suffix clears live pipes and restores at least the causal BF prefix capacity. Final volume attains the stream peak; BF has KPI 1, replay keeps its oversized trench.",
                "not_a_universal_all_algorithms_claim": True,
                "selection": "Deterministic scan of public prefixes against frozen releases; one worst trap per release and four further current-release cases.",
                "platform_actions": 0}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profiles": profiles, "selected": test_rows}, indent=2))


if __name__ == "__main__":
    main()
