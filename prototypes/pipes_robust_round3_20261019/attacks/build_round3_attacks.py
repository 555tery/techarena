#!/usr/bin/env python3
"""Freeze a small round-3 attack suite against the round-2 final solver.

Only the actual frozen target and causal Best-Fit executable are used for the
local screen. Candidate KPI values are deliberately kept out of the handoff
manifest so the coordinator can perform the first official comparison blind.
"""
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROUND2 = REPO / "prototypes/pipes_robust_round2_20261019"
TARGET = ROUND2 / "final/solver"
SOURCE = ROUND2 / "final/solution.cpp"
BF = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def decode_tables(source):
    start = source.index("static const char* encoded[]={") + len("static const char* encoded[]={")
    end = source.index("};", start)
    tables = []
    for group in source[start:end].split(","):
        blob = base64.b64decode("".join(re.findall(r'"([A-Za-z0-9+/=]*)"', group)))
        at = 0

        def varint():
            nonlocal at
            value = shift = 0
            while True:
                byte = blob[at]
                at += 1
                value |= (byte & 127) << shift
                if byte < 128:
                    return value
                shift += 7

        def signed():
            value = varint()
            return -(value + 1) // 2 if value & 1 else value // 2

        n = varint()
        commands, positions, last = [], [], 0
        for _ in range(n):
            command = signed()
            commands.append(command)
            if command > 0:
                last += signed()
                positions.append(last)
            else:
                positions.append(None)
        assert at == len(blob)
        tables.append((commands, positions))
    assert len(tables) == 15
    return tables


def public_commands(case):
    tokens = (REPO / f"data/pipes/open/{case}.in").read_text().split()
    n = int(tokens[1])
    return list(map(int, tokens[2:2 + n]))


def encode(commands):
    return f"1\n{len(commands)}\n" + "\n".join(map(str, commands)) + "\n"


def parse_commands(commands):
    live, volume = {}, 0
    next_pid = 0
    for command in commands:
        if command > 0:
            next_pid += 1
            live[next_pid] = command
            volume += command
        else:
            pid = -command
            assert pid in live, ("invalid input pid", pid)
            volume -= live.pop(pid)
    return live, volume


def batch(binary, commands, probe=False):
    args = [str(binary)]
    if probe:
        args.extend(["bestfit", str(TAPE)])
    result = subprocess.run(args, input="\n".join(map(str, commands + [0])) + "\n",
                           text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(commands), (binary, len(lines), len(commands))
    trench = volume = pid = 0
    places, trace = {}, []
    for command, line in zip(commands, lines):
        if command > 0:
            dig, start = map(int, line.split())
            trench += 20 * dig
            assert start + command <= trench, (binary, command, line, trench)
            if len(places) < 1000:
                assert all(start + command <= a or b <= start for a, b in places.values()), (binary, command, line)
            pid += 1
            places[pid] = (start, start + command)
            volume += command
        else:
            start = int(line)
            old_start, old_end = places.pop(-command)
            assert start == old_start, (binary, command, start, old_start)
            volume -= old_end - old_start
        trace.append(trench)
    return {"T": trench, "F": volume, "KPI": volume / trench if trench else 0.0,
            "trace": trace, "places": places, "stderr": result.stderr.strip()}


def prefix_state(commands, positions):
    """Reconstruct the target plan's live PID/size state without score claims."""
    live = {}
    for pid, command in enumerate(commands, 1):
        if command > 0:
            live[pid] = command
        else:
            live.pop(-command)
    assert len(positions) >= len(commands)
    return live


def prior_round2_hashes():
    hashes, files = set(), []
    for path in ROUND2.rglob("*.in"):
        files.append(path)
        hashes.add(sha_file(path))
    for manifest_path in ROUND2.rglob("manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:
            continue
        for rows in manifest.values():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                for key in ("input_sha256", "test_sha256", "sha256"):
                    value = row.get(key)
                    if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
                        hashes.add(value)
    return hashes, files


def select_open14_deletes(live, special_pid, target_volume):
    assert live.get(special_pid) == 23
    chosen, removed = [special_pid], live[special_pid]
    remaining = target_volume - removed
    candidates = sorted(((n, pid) for pid, n in live.items() if pid != special_pid),
                        key=lambda pair: (-pair[0], pair[1]))
    for size, pid in candidates:
        if size <= remaining:
            chosen.append(pid)
            removed += size
            remaining -= size
            if remaining == 0:
                break
    assert removed == target_volume, (target_volume, removed, remaining)
    return chosen


def main():
    assert sha_file(SOURCE) == "3a0164597619fcccc52e2f5fc60f9c391853eb3e36f8dd7e39185a98c3539a00"
    assert sha_file(TARGET) == "7983381dbab408b50b9a99e8895ec26399140a4cb3e01abdb1e51bdc38075316"
    target_sha, bf_sha = sha_file(TARGET), sha_file(BF)
    tables = decode_tables(SOURCE.read_text())
    public = {case: public_commands(case) for case in range(1, 16)}
    assert all(tables[i - 1][0] == public[i] for i in range(1, 16))
    old_hashes, old_files = prior_round2_hashes()

    specs = []
    # Open2 ends at command 18 with a strict state trench advantage over its
    # shadow BF (20m vs 40m); the following stream forces the gated episode to
    # begin, grow past shadow BF, and stop.
    for name, suffix in [
        ("budgeted-open2-episode-36-5-delete12", [-13, 36, 5, -12]),
        ("budgeted-open2-episode-36-5-delete10", [-13, 36, 5, -10]),
    ]:
        specs.append({"name": name, "case": 2, "cut": 18, "suffix": suffix,
                      "mechanism": "budgeted-online episode after strict target-T advantage; episode grows past shadow BF and stops"})

    # Open12's tuned plan is identical to BF at operation 151; it changes
    # geometry after that point and reaches a very different state by 224.
    # The suffix intentionally mismatches the table after the full 224-command
    # common prefix, then performs one ordinary fallback placement.
    specs.extend([
        {"name": "open12-p224-delete1-refill20", "case": 12, "cut": 224,
         "suffix": [-1, 20], "mechanism": "late Open12 table geometry followed by a verified mismatch and fallback"},
        {"name": "open12-p224-delete168-refill2", "case": 12, "cut": 224,
         "suffix": [-168, 2], "mechanism": "late Open12 table geometry followed by a different verified mismatch and fallback"},
    ])

    open14_cut = 17161
    open14_prefix = tables[13][0][:open14_cut]
    live14 = parse_commands(open14_prefix)[0]
    for removed in (1550, 1800):
        deleted = select_open14_deletes(live14, 17156, removed)
        suffix = [-pid for pid in deleted]
        specs.append({"name": f"open14-late-rank-exposure-remove{removed}", "case": 14,
                      "cut": open14_cut, "suffix": suffix,
                      "mechanism": f"late rank shift at PID 17156; delete {removed}m of active volume after mismatch to expose fixed trench overhead"})

    tests = []
    cache = {}
    for spec in specs:
        case, cut = spec["case"], spec["cut"]
        prefix = tables[case - 1][0][:cut]
        assert prefix == public[case][:cut]
        commands = prefix + spec["suffix"]
        digest = sha_bytes(encode(commands).encode())
        assert digest not in old_hashes, ("prior round2 duplicate", spec["name"])
        assert len(commands) <= 200000
        live, prefix_volume = parse_commands(prefix)
        assert all(-command in live for command in spec["suffix"] if command < 0)
        assert parse_commands(commands)[0] is not None
        target = batch(TARGET, commands)
        bf = batch(BF, commands, probe=True)
        assert target["KPI"] < 0.9, (spec["name"], target["KPI"])
        assert bf["KPI"] >= 0.9, (spec["name"], bf["KPI"])
        diag = target["stderr"]
        imported = re.search(r"imported_ops=(\d+)", diag)
        assert imported and int(imported.group(1)) >= cut, (spec["name"], diag)
        if spec["name"].startswith("budgeted-open2"):
            assert "episode=1" in diag and "stopped=1" in diag, (spec["name"], diag)
        if spec["name"].startswith("open14-"):
            assert int(spec["suffix"][0]) == -17156

        if cut not in cache:
            ptarget = batch(TARGET, prefix)
            pbf = batch(BF, prefix, probe=True)
            ratios = [a / b if b else (1.0 if a == 0 else float("inf"))
                      for a, b in zip(ptarget["trace"], pbf["trace"])]
            cache[cut] = {"ptarget": ptarget, "pbf": pbf,
                          "max_ratio": max(ratios, default=1.0),
                          "min_ratio": min(ratios, default=1.0),
                          "prefix_hash": sha_bytes(encode(prefix).encode())}
        ps = cache[cut]
        rank_shift = None
        if case == 14:
            pid = 17156
            target_pos = ps["ptarget"]["places"][pid][0]
            bf_pos = ps["pbf"]["places"][pid][0]
            assert target_pos == 19032 and bf_pos == 1797
            rank_shift = {"pid": pid, "length_m": 23,
                          "target_position_m": target_pos,
                          "causal_BF_position_m": bf_pos}
        filename = spec["name"] + ".in"
        (HERE / filename).write_text(encode(commands))
        tests.append({
            "name": spec["name"], "file": filename, "case": case,
            "shared_prefix_cut": cut, "shared_prefix_source": f"data/pipes/open/{case}.in",
            "shared_prefix_source_sha256": sha_file(REPO / f"data/pipes/open/{case}.in"),
            "shared_prefix_commands_sha256": ps["prefix_hash"],
            "shared_prefix_first_commands": prefix[:20] if cut <= 20 else None,
            "suffix": spec["suffix"], "suffix_length": len(spec["suffix"]),
            "mechanism": spec["mechanism"],
            "rank_shift_evidence": rank_shift,
            "max_cumulative_prefix_ratio_target_vs_causal_BF": ps["max_ratio"],
            "min_cumulative_prefix_ratio_target_vs_causal_BF": ps["min_ratio"],
            "prefix_T_target_m": ps["ptarget"]["T"], "prefix_T_causal_BF_m": ps["pbf"]["T"],
            "prefix_volume_m": prefix_volume,
            "causal_BF_final": {"T": bf["T"], "F": bf["F"], "KPI": bf["KPI"]},
            "actual_target_screen": {
                "full_shared_prefix_imported_before_mismatch": int(imported.group(1)) >= cut,
                "budgeted_episode_triggered": "episode=1" in diag,
                "budgeted_episode_stopped": "stopped=1" in diag,
                "target_KPI_below_0_90": True,
            },
            "target_final_KPI": "withheld for blind official first comparison",
            "input_sha256": sha_bytes((HERE / filename).read_bytes()),
        })

    # Round-2 Open12 command 151 is a negative screen: the tuned target and
    # causal BF have exactly identical geometry there, so no immediate
    # post-151 geometry trap is claimed. The late risk starts later.
    p151t = batch(TARGET, public[12][:151])
    p151b = batch(BF, public[12][:151], probe=True)
    assert p151t["T"] == p151b["T"] == 1260
    assert p151t["places"] == p151b["places"]
    manifest = {
        "title": "Round 3 fresh attacks against frozen round2/final/solver",
        "target_source_sha256": sha_file(SOURCE), "target_binary_sha256": target_sha,
        "causal_bestfit_probe_sha256": bf_sha,
        "selection": "Six fresh streams across three mechanisms: a triggered/stopped budgeted online episode, late Open12 table geometry, and late Open14 rank-shift exposure. Open8/Open11 drain templates were not used.",
        "local_screen": "Every listed stream was executed by the actual frozen target binary after the forced post-prefix mismatch and by the causal Best-Fit probe. Local gate: target KPI < 0.90, causal BF KPI >= 0.90, valid PID replies. Target KPI values are withheld for the blind official comparison.",
        "official_interactor_validation": "pending root",
        "prior_round2_input_file_count_excluded": len(old_files),
        "prior_round2_unique_hash_count_excluded": len(old_hashes),
        "prior_round2_scope": str(ROUND2.relative_to(REPO)),
        "open12_prefix151_negative_screen": {
            "target_T_m": p151t["T"], "causal_BF_T_m": p151b["T"],
            "same_live_layout_claim": "checked from decoded positions and allocator state; both trench 1260m and same active placements",
            "attack_claim": "none; immediate prefix-151 geometry candidate rejected",
        },
        "tests": tests,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"frozen {len(tests)} streams; prior hashes excluded={len(old_hashes)}; candidate KPI withheld")


if __name__ == "__main__":
    main()
