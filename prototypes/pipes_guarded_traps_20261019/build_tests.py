"""Construct valid fixed tests against frozen replay plans; no solver tuning."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = REPO / "prototypes/pipes_open15_overfit_20261019"
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_after(commands):
    active = {}
    pid = 0
    for c in commands:
        if c > 0:
            pid += 1
            active[pid] = c
        else:
            del active[-c]
    return active


def export_tape(commands, positions, path):
    # Independent full byte occupancy replay: every placement and deletion.
    cells = bytearray()
    active = {}
    pid = 0
    rows = []
    for command in commands:
        if command > 0:
            pid += 1
            pos = positions[pid - 1]
            end = pos + command
            if end > len(cells):
                cells.extend(b"\0" * (((end + 19) // 20) * 20 - len(cells)))
            assert not any(cells[pos:end])
            cells[pos:end] = b"\1" * command
            active[pid] = (pos, command)
        else:
            pos, length = active.pop(-command)
            assert all(cells[pos:pos + length])
            cells[pos:pos + length] = b"\0" * length
        rows.append(f"{command} {pos}\n")
    path.write_text(str(len(commands)) + "\n" + "".join(rows))
    return {"trench_m": len(cells), "final_occupied_m": sum(cells),
            "full_public_plan_byte_replay": "passed", "tape_sha256": sha(path)}


def main():
    joint = json.loads((OLD / "joint.json").read_text())
    case = next(c for c in joint["cases"] if c["case"] == 15)
    commands = case["commands"]
    shared_places = list(map(int, (OLD / "best-positions.txt").read_text().split()))
    joint_positions = [shared_places[b] for b in case["block_ids"] if b >= 0]
    reverse_path = OLD / "future/2/15.txt"
    reverse_positions = list(map(int, reverse_path.read_text().split()))
    profiles = {}
    for name, positions in [("joint", joint_positions), ("reverse", reverse_positions)]:
        profiles[name] = export_tape(commands, positions, HERE / (name + "-tape.txt"))
    profiles["joint"]["origin"] = "Frozen prefix-consistent joint Open15 best-positions plan, same as the previous diagnostic."
    profiles["joint"]["source_sha256"] = sha(OLD / "best-positions.txt")
    profiles["reverse"]["origin"] = "Existing future/2/15.txt, reverse permanent-pipe order with backward BF temporary packing; optimized for public case15 only, not jointly prefix-compatible with all Open15."
    profiles["reverse"]["source_sha256"] = sha(reverse_path)
    # Ordinary BF coordinates, produced by the previously checked causal control.
    old_probe = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
    output = subprocess.run([str(old_probe), "bestfit", str(HERE / "joint-tape.txt")],
        input="\n".join(map(str, commands + [0])) + "\n", text=True,
        capture_output=True, check=True, timeout=20).stdout.splitlines()
    bfpos, active, pid, trench = {}, {}, 0, 0
    cuts = {}
    for index, (c, line) in enumerate(zip(commands, output), 1):
        if c > 0:
            digs, pos = map(int, line.split())
            trench += digs * 20
            pid += 1
            bfpos[pid] = pos
            active[pid] = c
        else:
            del active[-c]
        if index in [32, 128, 4096]:
            cuts[index] = (dict(active), trench)
    # Exact survivor-subset refinement of the bounded window search.
    survivors = [11, 12, 13, 14, 22]
    assert sum(cuts[32][0][p] for p in survivors) == 24
    fragment = commands[:32] + [-p for p in sorted(cuts[32][0]) if p not in survivors] + [28] * 3 + [1] * 12
    tests = [("joint-fragmentation", fragment,
              "Keep PIDs 11,12,13,14,22 (24 m) compact in BF, scattered in frozen joint replay; refill with 3x28 and 12x1.",
              "joint", {"prefix_n": 32, "retained_pids": survivors})]
    beam = json.loads((HERE / "beam-suffix.json").read_text())
    tests.append(("joint-multiphase", commands[:32] + beam["suffix_commands"],
                  "Fixed bounded-beam suffix repeatedly changes lifetimes within the same BF arena; terminal 1 m pipes restore full 120 m final loading.",
                  "joint", {"prefix_n": 32, "suffix_sha256": sha(HERE / "beam-suffix.json")}))
    for cut in [128, 4096]:
        alive, bf_trench = cuts[cut]
        refill_count = (bf_trench + 39) // 40
        test = commands[:cut] + [-p for p in sorted(alive)] + [40] * refill_count
        tests.append((f"reverse-reservation-{cut}", test,
                      "After a real public prefix, clear active pipes and restore at least the prefix peak volume with 40 m pipes. Frozen reverse plan has already excavated for its expected distant future.",
                      "reverse", {"prefix_n": cut, "refill_count_40m": refill_count}))
    tests.append(("public-case15-control", commands,
                  "Unmodified public case15 commands, normalized local weight 1; validates each full frozen tape.",
                  "control", {"prefix_n": len(commands)}))
    inputs = HERE / "inputs"
    inputs.mkdir(exist_ok=True)
    records = []
    for name, cmd, mechanism, target, parameters in tests:
        path = inputs / (name + ".in")
        path.write_text(f"1\n{len(cmd)}\n" + "\n".join(map(str, cmd)) + "\n")
        meta = parse_test(path)
        common = 0
        for x, y in zip(commands, cmd):
            if x != y: break
            common += 1
        assert common == parameters["prefix_n"]
        if target != "control":
            assert meta["kpi_upper_bound_from_live_volume"] == 1
        records.append({"name": name, "file": str(path.relative_to(REPO)), "target_profile": target,
                        "common_command_prefix": common, "mechanism": mechanism,
                        "parameters": parameters, **meta})
    manifest = {"purpose": "User-authorized adversarial test construction, fixed existing replay plans; no platform use or solver optimization.",
                "source_public_case": "data/pipes/open/15.in", "source_sha256": sha(REPO / "data/pipes/open/15.in"),
                "profiles": profiles, "tests": records,
                "selection": "Joint probe chosen by bounded prefix-window geometry search; reverse tests target pre-existing irreversible reservations. All selected to expose known mechanisms, not an unseen benchmark.",
                "platform_actions": 0}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profiles": profiles, "tests": [{"name": r["name"], "n": r["operation_count"], "F": r["final_occupied_length_m"], "prefix": r["common_command_prefix"], "params": r["parameters"]} for r in records]}, indent=2))


if __name__ == "__main__":
    main()
