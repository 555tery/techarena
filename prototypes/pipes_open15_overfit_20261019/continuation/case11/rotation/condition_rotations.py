"""Verify PID1 cut rotations and run bounded local conditioned planners.

All layouts here intentionally use public future deletions. They are offline
plans, not an online policy. Every produced plan is replayed independently.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime import ROOT, REPO, e

OUT = ROOT / "case11" / "rotation"
INPUT11 = REPO / "data/pipes/open/11.in"
INPUT15 = REPO / "data/pipes/open/15.in"
SOURCE = REPO / "prototypes/pipes_open15_overfit_20261019/future/2/11.txt"
PREFIX = 4999


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_input(path: Path):
    raw = list(map(int, path.read_text().split()))
    width, n = raw[:2]
    commands = raw[2:2+n]
    if len(commands) != n or raw[2+n:] not in ([], [0]):
        raise ValueError(f"malformed input: {path}")
    lengths = [0]
    birth = [-1]
    death = [n]
    pid_at = [0] * n
    for t, c in enumerate(commands):
        if c > 0:
            pid = len(lengths)
            lengths.append(c)
            birth.append(t)
            death.append(n)
            pid_at[t] = pid
        elif c < 0:
            pid = -c
            if pid <= 0 or pid >= len(lengths) or death[pid] != n:
                raise ValueError(f"bad deletion at command {t}: PID {pid}")
            death[pid] = t
    return width, n, commands, lengths, birth, death, pid_at, raw[2+n:]


def read_positions(path: Path, pipes: int):
    pos = list(map(int, path.read_text().split()))
    if len(pos) != pipes:
        raise ValueError(f"{path}: got {len(pos)} positions for {pipes} pipes")
    if min(pos, default=0) < 0:
        raise ValueError(f"negative position in {path}")
    return [0] + pos


def replay(path: Path, positions: list[int]):
    width, n, cmd, lengths, birth, death, pid_at, extra = read_input(path)
    if len(positions) != len(lengths):
        raise ValueError("position/input pipe count mismatch")
    occupied: list[tuple[int, int]] = []
    live: dict[int, tuple[int, int]] = {}
    volume = peak = insertions = deletions = 0
    for t, c in enumerate(cmd):
        if c < 0:
            pid = -c
            if pid not in live:
                raise ValueError(f"{path}: command {t} deletes inactive PID {pid}")
            start, length = live.pop(pid)
            i = bisect.bisect_left(occupied, (start, pid))
            if i >= len(occupied) or occupied[i] != (start, pid):
                raise ValueError(f"{path}: active spatial index mismatch PID {pid}")
            occupied.pop(i)
            volume -= length
            deletions += 1
        elif c > 0:
            pid = pid_at[t]
            start, end = positions[pid], positions[pid] + c
            i = bisect.bisect_left(occupied, (start, pid))
            if i and occupied[i-1][0] + lengths[occupied[i-1][1]] > start:
                raise ValueError(f"{path}: command {t} PID {pid} overlaps PID {occupied[i-1][1]}")
            if i < len(occupied) and occupied[i][0] < end:
                raise ValueError(f"{path}: command {t} PID {pid} overlaps PID {occupied[i][1]}")
            occupied.insert(i, (start, pid))
            live[pid] = (start, c)
            volume += c
            peak = max(peak, volume)
            insertions += 1
    extent = max((positions[i] + lengths[i] for i in range(1, len(lengths))), default=0)
    if insertions != len(lengths)-1 or len(live) != sum(d == n for d in death[1:]):
        raise ValueError("replay totals mismatch")
    return {
        "input_sha256": sha(path), "pipes": len(lengths)-1,
        "insertions": insertions, "deletions": deletions,
        "survivors": len(live), "extent": extent,
        "trench_score": 20 * ((extent+19)//20),
        "volume_lower_bound": peak, "valid": True,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c11 = read_input(INPUT11)
    c15 = read_input(INPUT15)
    _, n11, cmds11, lengths, birth, death, _, _ = c11
    _, n15, cmds15, lengths15, _, _, _, _ = c15
    source_pos = read_positions(SOURCE, len(lengths)-1)
    if cmds11[:PREFIX] != cmds15[:PREFIX]:
        raise ValueError("the expected 4999-command common prefix changed")
    common_pipes = sum(c > 0 for c in cmds11[:PREFIX])
    if common_pipes != 4006:
        raise ValueError(f"expected 4006 common-prefix insertions, got {common_pipes}")
    source_report = replay(INPUT11, source_pos)
    cut = source_pos[1]
    if lengths[1] != 3 or birth[1] != 0 or death[1] != n11:
        raise ValueError(f"PID1 is not an immortal length-3 pipe: {lengths[1],birth[1],death[1],n11}")
    if any(source_pos[pid] < cut < source_pos[pid]+lengths[pid]
           for pid in range(2, len(lengths))):
        raise ValueError("some source pipe crosses PID1's left-edge cut")
    if any(source_pos[pid] < cut+3 and source_pos[pid]+lengths[pid] > cut
           for pid in range(2, len(lengths))):
        raise ValueError("some source pipe overlaps PID1's interval")

    variants = []
    for h in (source_report["extent"], 20820):
        if h < source_report["extent"]:
            continue
        for reflected in (False, True):
            staged = [0]
            for pid in range(1, len(lengths)):
                x, length = source_pos[pid], lengths[pid]
                staged.append(h-(x+length) if reflected else x)
            rotation_cut = staged[1]
            if any(staged[pid] < rotation_cut < staged[pid]+lengths[pid]
                   for pid in range(2, len(lengths))):
                raise ValueError(f"reflected={reflected}, H={h}: rotation cut is crossed")
            rotated = [0]
            for pid in range(1, len(lengths)):
                x = staged[pid]
                rotated.append(x-rotation_cut if x >= rotation_cut else x+(h-rotation_cut))
            name = f"mode2-H{h}-{'reflected' if reflected else 'direct'}.txt"
            dest = OUT / name
            dest.write_text("".join(f"{rotated[pid]}\n" for pid in range(1, len(rotated))))
            report = replay(INPUT11, rotated)
            if rotated[1] != 0 or report["extent"] > h:
                raise ValueError(f"bad rotation: {name}, pid1={rotated[1]}, extent={report['extent']}, H={h}")
            item = {
                "name": name, "H": h, "reflected_before_rotation": reflected,
                "cut_before_rotation": rotation_cut, "pid1_after_rotation": rotated[1],
                "sha256": sha(dest), "case11_replay": report,
                "case11_T": report["trench_score"],
            }
            variants.append(item)
            if h == source_report["extent"] and not reflected:
                canonical = OUT / "rotate-mode2.txt"
                canonical.write_bytes(dest.read_bytes())
                item["canonical_copy_sha256"] = sha(canonical)

    results = []
    for variant in variants:
        d = OUT / variant["name"].removesuffix(".txt")
        d.mkdir(exist_ok=True)
        candidate = OUT / variant["name"]
        pin_positions = read_positions(candidate, len(lengths)-1)
        pins = d / "pins.txt"
        pins.write_text("".join(f"{pin_positions[pid]}\n" for pid in range(1, common_pipes+1)))
        pair = {}
        case = 15
        inp, case_lengths = INPUT15, lengths15
        best = None
        for method, modes in (("conditioned_reverse", range(8)), ("conditioned", range(4))):
            exe = ROOT / method
            if not exe.is_file():
                raise FileNotFoundError(exe)
            for mode in modes:
                dest = d / f"case{case}-{method}-{mode}.txt"
                log = f"case{case}-{method}-{mode}.log"
                rc = e.invoke([str(exe), str(inp), str(pins), str(PREFIX), str(dest), str(mode)], d, log, 120)
                if rc != 0:
                    raise RuntimeError(f"planner failed case={case} method={method} mode={mode} rc={rc}")
                log_text = (d / log).read_text()
                match = re.findall(r"(?m)^\s*(\d+)\s*$", log_text)
                if not match:
                    raise ValueError(f"cannot parse trench score from {log}")
                report = replay(inp, read_positions(dest, len(case_lengths)-1))
                declared = int(match[-1])
                if report["trench_score"] != declared:
                    raise ValueError(f"score mismatch in {dest}: log={declared}, replay={report['trench_score']}")
                row = {"T": declared, "method": method, "mode": mode,
                       "positions": str(dest), "sha256": sha(dest), "replay": report}
                if best is None or (row["T"], method, mode) < (best["T"], best["method"], best["mode"]):
                    best = row
                print(json.dumps({"variant": variant["name"], "case": case,
                                  "method": method, "mode": mode, "T": declared}), flush=True)
        pair["11"] = {"T": variant["case11_T"], "method": "rotated raw mode2",
                      "positions": str(candidate), "sha256": sha(candidate),
                      "replay": variant["case11_replay"]}
        pair["15"] = best
        pair["score"] = 20361 / pair["11"]["T"] + 10 * 418757 / pair["15"]["T"]
        results.append({"variant": variant, "pins_sha256": sha(pins), "pair": pair})
        e.save(d / "result.json", results[-1])
    manifest = {
        "task": "Open15 case11 immortal-PID1 cyclic rotations and conditioned suffix search",
        "offline_future_deletions_used": True,
        "source_plan": str(SOURCE), "source_plan_sha256": sha(SOURCE),
        "case11_input_sha256": sha(INPUT11), "case15_input_sha256": sha(INPUT15),
        "source_case11_replay": source_report,
        "pid1": {"length": lengths[1], "birth_command": birth[1], "death_command": death[1],
                 "final_time": n11, "immortal": death[1] == n11,
                 "source_cut": cut, "other_pipes_cross_cut": 0},
        "common_prefix": {"commands": PREFIX, "insertions": common_pipes},
        "variants": results,
    }
    e.save(OUT / "report.json", manifest)
    print(json.dumps({"report": str(OUT / "report.json"),
                      "best_pairs": [{"variant": x["variant"]["name"],
                                      "T11": x["pair"]["11"]["T"],
                                      "T15": x["pair"]["15"]["T"],
                                      "score": x["pair"]["score"]}
                                     for x in results]}, indent=2))


if __name__ == "__main__":
    main()
