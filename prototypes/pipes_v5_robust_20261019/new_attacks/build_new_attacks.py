#!/usr/bin/env python3
"""Build bounded structured-search adversaries for frozen release-v5.

The prefix is an exact Open15 command prefix whose cumulative replay trench is
at most 2x causal Best-Fit at every prefix step. After the first off-table
removal, enumerate deletion subsets, then greedily seek lengths that fit BF's
current gaps but force the replayed geometry to grow. This is a targeted local
search, not a hidden-test distribution or a claim about all algorithms.
"""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGET = REPO / "prototypes/pipes_v5_graves_20261019/target"
OLD_MANIFEST = REPO / "prototypes/pipes_v5_graves_20261019/manifest.json"


def decode_tables(source):
    start = source.index("static const char* encoded[]={") + len("static const char* encoded[]={")
    end = source.index("};", start)
    tables = []
    for group in source[start:end].split(","):
        blob = base64.b64decode("".join(re.findall(r'"([A-Za-z0-9+/=]*)"', group)))
        offset = 0

        def varint():
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
            value = varint()
            return -(value + 1) // 2 if value & 1 else value // 2

        count = varint()
        commands, positions, last = [], [], 0
        for _ in range(count):
            command = signed()
            commands.append(command)
            if command > 0:
                last += signed()
                positions.append(last)
            else:
                positions.append(None)
        assert offset == len(blob)
        tables.append((commands, positions))
    assert len(tables) == 15
    return tables


class Allocator:
    def __init__(self):
        self.trench = 0
        self.gaps = []
        self.pipes = [None]

    def clone(self):
        result = Allocator()
        result.trench = self.trench
        result.gaps = self.gaps.copy()
        result.pipes = self.pipes.copy()
        return result

    def add_gap(self, left, right):
        if left >= right:
            return
        merged = []
        for a, b in self.gaps:
            if b < left or a > right:
                merged.append((a, b))
            else:
                left, right = min(left, a), max(right, b)
        merged.append((left, right))
        self.gaps = sorted(merged)

    def place(self, length, planned=None):
        if planned is None:
            fits = sorted((b - a, a) for a, b in self.gaps if b - a >= length)
            if fits:
                planned = fits[0][1]
            else:
                tails = [a for a, b in self.gaps if b == self.trench]
                planned = tails[-1] if tails else self.trench
        if planned + length > self.trench:
            new_trench = ((planned + length + 19) // 20) * 20
            self.add_gap(self.trench, new_trench)
            self.trench = new_trench
        for index, (left, right) in enumerate(self.gaps):
            if left <= planned and planned + length <= right:
                self.gaps.pop(index)
                self.add_gap(left, planned)
                self.add_gap(planned + length, right)
                break
        else:
            raise ValueError(f"illegal placement {length}@{planned}, gaps={self.gaps}")
        self.pipes.append((planned, length))

    def remove(self, pid):
        pos, length = self.pipes[pid]
        if pos is None:
            raise ValueError(f"double deletion pid={pid}")
        self.pipes[pid] = (None, 0)
        self.add_gap(pos, pos + length)


def public_commands(case):
    values = list(map(int, (REPO / f"data/pipes/open/{case}.in").read_text().split()[2:]))
    return values[:-1] if values and values[-1] == 0 else values


def replay_prefix(case, cut, tables, public):
    commands, positions = tables[case - 1]
    replay, bf = Allocator(), Allocator()
    active, pid, peak_ratio = {}, 0, 1.0
    for step, (command, pos) in enumerate(zip(commands[:cut], positions[:cut]), 1):
        if command > 0:
            pid += 1
            active[pid] = command
            replay.place(command, pos)
            bf.place(command)
        else:
            del active[-command]
            replay.remove(-command)
            bf.remove(-command)
        ratio = replay.trench / bf.trench if bf.trench else (1.0 if replay.trench == 0 else float("inf"))
        peak_ratio = max(peak_ratio, ratio)
        if peak_ratio > 2.00000001:
            return None
    matches = [idx for idx, stream in public.items() if stream[:cut] == commands[:cut]]
    next_commands = {public[idx][cut] for idx in matches if cut < len(public[idx])}
    divergent = [pid for pid in active if -pid not in next_commands]
    if not divergent:
        return None
    return replay, bf, active, peak_ratio, divergent[0], matches


def fill_after_deletions(bf, replay, volume, max_additions=48):
    additions = []
    for _ in range(max_additions):
        differential = []
        for length in range(1, 41):
            next_bf, next_replay = bf.clone(), replay.clone()
            old_bf, old_replay = bf.trench, replay.trench
            next_bf.place(length)
            next_replay.place(length)
            db, dr = next_bf.trench - old_bf, next_replay.trench - old_replay
            if db == 0 and dr > 0:
                differential.append((-dr / length, -dr, -length, length, next_bf, next_replay))
        if differential:
            _, _, _, length, bf, replay = min(differential)
            volume += length
            additions.append(length)
            continue
        if volume / bf.trench >= 0.9:
            break
        common = []
        for length in range(1, 41):
            next_bf, next_replay = bf.clone(), replay.clone()
            old_bf, old_replay = bf.trench, replay.trench
            next_bf.place(length)
            next_replay.place(length)
            if next_bf.trench == old_bf and next_replay.trench == old_replay:
                common.append((-length, length, next_bf, next_replay))
        if not common:
            break
        _, length, bf, replay = min(common)
        volume += length
        additions.append(length)
    return bf, replay, volume, additions


def build():
    target_source = TARGET / "solution.cpp"
    tables = decode_tables(target_source.read_text())
    public = {case: public_commands(case) for case in range(1, 16)}
    for case, (commands, _) in enumerate(tables, 1):
        assert commands == public[case]

    old = json.loads(OLD_MANIFEST.read_text())
    old_hashes = {row.get("test_sha256") or row.get("input_sha256") for row in old.get("tests", [])}
    pool = []
    cut_ranges = {
        1: range(1, 15), 2: range(3, 25), 3: range(1, 22), 4: range(3, 20),
        5: range(1, 3), 6: range(1, 20), 7: range(1, 3), 8: range(1, 2),
        9: range(1, 2), 10: range(1, 3), 11: range(1, 2), 12: range(3, 38),
        13: range(0, 1), 14: range(1, 8), 15: range(1, 2),
    }
    for case, cuts in cut_ranges.items():
        for cut in cuts:
            if cut == 0:
                continue
            prefix = replay_prefix(case, cut, tables, public)
            if prefix is None:
                continue
            replay0, bf0, active, ratio, first_delete, matches = prefix
            ids = sorted(active)
            if len(ids) > 15 or len(ids) < 2:
                continue
            volume0 = sum(active.values())
            ranked = []
            # Enumerate deletion subsets. The first deletion must reject every
            # still-matching Open15 branch; subsequent deletes shape free gaps.
            for mask in range(1 << len(ids)):
                deleted = [pid for bit, pid in enumerate(ids) if mask >> bit & 1]
                if first_delete not in deleted or len(deleted) == len(ids):
                    continue
                bf, replay = bf0.clone(), replay0.clone()
                volume = volume0
                for pid in deleted:
                    bf.remove(pid)
                    replay.remove(pid)
                    volume -= active[pid]
                max_bf_gap = max((b - a for a, b in bf.gaps), default=0)
                max_replay_gap = max((b - a for a, b in replay.gaps), default=0)
                gap_advantage = max_bf_gap - max_replay_gap
                if gap_advantage > 0:
                    ranked.append((gap_advantage, volume / bf.trench, deleted, bf, replay, volume))
            ranked.sort(key=lambda row: (-row[0], -row[1]))
            for gap_advantage, _, deleted, bf, replay, volume in ranked[:32]:
                bf, replay, final_volume, additions = fill_after_deletions(bf, replay, volume)
                bf_kpi = final_volume / bf.trench if bf.trench else 0.0
                replay_kpi = final_volume / replay.trench if replay.trench else 0.0
                if bf_kpi < 0.9 or replay_kpi >= 0.9 or final_volume <= 0:
                    continue
                suffix = [-first_delete] + [-pid for pid in deleted if pid != first_delete] + additions
                commands = public[case][:cut] + suffix
                digest = hashlib.sha256(("1\n%d\n" % len(commands) + "\n".join(map(str, commands)) + "\n").encode()).hexdigest()
                if digest in old_hashes or any(row["input_sha256"] == digest for row in pool):
                    continue
                pool.append({
                    "input_sha256": digest,
                    "case": case, "cut": cut, "prefix": public[case][:cut], "suffix": suffix,
                    "commands": commands, "first_divergent_command": suffix[0],
                    "matching_tables_before_divergence": matches,
                    "target_prefix_T_m": replay0.trench, "bestfit_prefix_T_m": bf0.trench,
                    "max_prefix_ratio": ratio, "final_volume_m": final_volume,
                    "target_predicted_T_m": replay.trench, "bestfit_predicted_T_m": bf.trench,
                    "target_predicted_KPI": replay_kpi, "bestfit_predicted_KPI": bf_kpi,
                    "gap_advantage_after_deletions_m": gap_advantage,
                    "deletion_subset": deleted, "refill_lengths": additions,
                    "family": "delete-and-refill geometry search",
                })
    # Keep unique candidates with varied public origins and cuts; case 3 gets
    # priority because it was absent from the existing nine-input suite.
    pool.sort(key=lambda row: (row["target_predicted_KPI"], -row["bestfit_predicted_KPI"], len(row["commands"])))
    selected, used_cases, used_hashes = [], set(), set()
    counts = {}
    for preferred in (3, 6, 4, 12, 1, 7, 14, 5, 9, 10, 11, 15):
        candidate = next((row for row in pool if row["case"] == preferred and row["input_sha256"] not in used_hashes), None)
        if candidate is None:
            # input_sha256 is filled below; compute it here for this candidate.
            candidate = next((row for row in pool if row["case"] == preferred and hashlib.sha256(("1\n%d\n" % len(row["commands"]) + "\n".join(map(str, row["commands"])) + "\n").encode()).hexdigest() not in used_hashes), None)
        if candidate:
            digest = hashlib.sha256(("1\n%d\n" % len(candidate["commands"]) + "\n".join(map(str, candidate["commands"])) + "\n").encode()).hexdigest()
            if digest in old_hashes or digest in used_hashes:
                continue
            candidate["input_sha256"] = digest
            selected.append(candidate)
            used_cases.add(preferred)
            used_hashes.add(digest)
            counts[preferred] = counts.get(preferred, 0) + 1
    for candidate in pool:
        if len(selected) >= 10:
            break
        if candidate["case"] == 2:
            continue  # Open2 already has a dedicated quiet-geometry test.
        limit = {3: 4, 6: 3, 12: 3, 1: 2, 4: 2}.get(candidate["case"], 2)
        if counts.get(candidate["case"], 0) >= limit:
            continue
        digest = hashlib.sha256(("1\n%d\n" % len(candidate["commands"]) + "\n".join(map(str, candidate["commands"])) + "\n").encode()).hexdigest()
        if digest in old_hashes or digest in used_hashes:
            continue
        candidate["input_sha256"] = digest
        selected.append(candidate)
        used_hashes.add(digest)
        counts[candidate["case"]] = counts.get(candidate["case"], 0) + 1
    if len(selected) < 6:
        print("Only", len(selected), "qualifying candidates; all scanned:", len(pool))
        print(json.dumps([{k: r.get(k) for k in ("case", "cut", "target_predicted_KPI", "bestfit_predicted_KPI", "max_prefix_ratio")} for r in pool[:30]], indent=2))
        raise SystemExit("Need at least six unique inputs; expand the bounded search before delivery.")

    # Write only within this subdirectory.
    from pipes_harness import parse_test
    rows = []
    selected_names = {f"attack-{idx:02d}-open{row['case']}-p{row['cut']}.in" for idx, row in enumerate(selected, 1)}
    for stale in HERE.glob("attack-*.in"):
        if stale.name not in selected_names:
            stale.unlink()
    for idx, row in enumerate(selected, 1):
        name = f"attack-{idx:02d}-open{row['case']}-p{row['cut']}"
        path = HERE / f"{name}.in"
        path.write_text(f"1\n{len(row['commands'])}\n" + "\n".join(map(str, row["commands"])) + "\n")
        parsed = parse_test(path)
        assert parsed["final_occupied_length_m"] == row["final_volume_m"]
        assert parsed["kpi_upper_bound_from_live_volume"] >= row["bestfit_predicted_KPI"] - 1e-9
        assert row["commands"][:row["cut"]] == public[row["case"]][:row["cut"]]
        assert row["commands"][row["cut"]] != public[row["case"]][row["cut"]]
        row = {k: v for k, v in row.items() if k != "commands"}
        row["name"] = name
        row["file"] = str(path.relative_to(REPO))
        row["operation_count"] = parsed["operation_count"]
        row["input_sha256"] = parsed["test_sha256"]
        row["public_input_sha256"] = hashlib.sha256((REPO / f"data/pipes/open/{row['case']}.in").read_bytes()).hexdigest()
        row["official_interactor_validation"] = "pending parent agent"
        rows.append(row)
    manifest = {
        "target_source_sha256": json.loads((REPO / "prototypes/pipes_v5_graves_20261019/target.json").read_text())["source_sha256"],
        "scope": "New release-v5 geometry attacks only; generated without modifying the frozen source or prior suites.",
        "search": "For each bounded Open15 prefix, require cumulative max T_replay/T_plain_BF <= 2; reject a valid PID deletion that diverges from all matching tables; enumerate subsets of active deletions; greedily place lengths that fit plain-BF gaps but grow the replayed fallback geometry. Subset beam retained the top 32 free-gap advantages per prefix.",
        "selection": "Unique input hashes against all tests in the existing v5 manifest; prioritize Open3, then other cases, then fill by target KPI.",
        "suite_size": len(rows),
        "official_interactor_validation": "pending parent agent; input syntax and PID validity checked by pipes_harness.parse_test",
        "not_claimed": "Targeted counterexamples to this frozen release and its fallback state; not universal attacks against every Open15-trained algorithm or unseen-distribution estimates.",
        "tests": rows,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps([{k: r[k] for k in ("name", "case", "cut", "max_prefix_ratio", "target_predicted_KPI", "bestfit_predicted_KPI", "operation_count", "file")} for r in rows], indent=2))


if __name__ == "__main__":
    sys.path.insert(0, str(REPO / "tools"))
    build()
