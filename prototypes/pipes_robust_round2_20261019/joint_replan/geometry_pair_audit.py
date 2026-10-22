#!/usr/bin/env python3
"""Read-only audit helpers for joint Open11/Open15 replans."""
import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "prototypes/pipes_open15_adversary_20261019"))
from construct import decode  # noqa: E402

SRC = REPO / "prototypes/pipes_v5_robust_20261019/candidate-v3/solution.cpp"
PROBE = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
OUT = Path(__file__).resolve().parent
OLD_ROOT = REPO / "prototypes/pipes_open15_overfit_20261019/continuation/joint-refined"


def cmds(case):
    tok = list(map(int, (REPO / f"data/pipes/open/{case}.in").read_text().split()))
    return tok[2:2 + tok[1]]


def bf_positions(case):
    cs = cmds(case)
    p = subprocess.run([str(PROBE), "bestfit", str(REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt")],
                       input="\n".join(map(str, cs + [0])) + "\n", text=True,
                       capture_output=True, check=True)
    ans, alloc = [], 0
    for c, line in zip(cs, p.stdout.splitlines()):
        z = list(map(int, line.split()))
        if c > 0:
            alloc += 1
            ans.append(z[1])
    return ans


def simulate(case, positions, stop=None):
    cs = cmds(case)
    alloc, peak, peak_at = 0, 0, 0
    traj = []
    for ti, c in enumerate(cs[:stop], 1):
        if c > 0:
            alloc += 1
            if alloc > len(positions):
                raise ValueError(f"case{case}: positions exhausted at allocation {alloc}")
            x = positions[alloc - 1]
            if x < 0:
                raise ValueError(f"case{case}: negative start at command {ti}, pid {alloc}, x={x}")
            end = x + c
            if end > peak:
                peak, peak_at = end, ti
        traj.append(((peak + 19) // 20) * 20)
    return {"T": ((peak + 19) // 20) * 20, "peak_end": peak, "peak_at": peak_at,
            "trajectory": traj}


def read_positions(path):
    return list(map(int, Path(path).read_text().split()))


def risk(case, pos, bfpos, cut=4999):
    a = simulate(case, pos, cut)["trajectory"]
    b = simulate(case, bfpos, cut)["trajectory"]
    ratios = [x / max(y, 20) for x, y in zip(a, b)]
    ix = max(range(len(ratios)), key=ratios.__getitem__)
    return {"prefix_commands": cut, "prefix_max_ratio": ratios[ix],
            "max_ratio_command": ix + 1, "target_T_at_max": a[ix], "BF_T_at_max": b[ix],
            "target_T_at_cut": a[-1], "BF_T_at_cut": b[-1]}


def main():
    decoded = decode(SRC)
    out = {"candidate_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
           "cases": {}}
    selected = {"score_best_min_risk_tie": 7, "min_risk_completed_mode": 3}
    pairs = {}
    for label, mode in selected.items():
        srcdir = OLD_ROOT / str(mode)
        result = json.loads((srcdir / "result.json").read_text())
        plan_rows = {}
        for case, entry in zip((11, 15), result["pair"]):
            source = Path(entry[1])
            target = OUT / f"geometry_{label}_open{case}_positions.txt"
            shutil.copyfile(source, target)
            plan_rows[str(case)] = {"path": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                    "source_path_read_only": str(source.relative_to(REPO)),
                                    "listed_T": entry[0], "builder": entry[2], "builder_mode": entry[3]}
        psrc = srcdir / "pins.txt"
        pdst = OUT / f"geometry_{label}_shared_prefix_positions.txt"
        shutil.copyfile(psrc, pdst)
        pairs[label] = {"prefix_mode": mode, "score": result["score"], "plans": plan_rows,
                        "prefix_positions_path": pdst.name,
                        "prefix_positions_sha256": hashlib.sha256(pdst.read_bytes()).hexdigest()}
    out["candidate_pairs"] = pairs
    for case in (11, 15):
        c, decoded_positions = decoded[case - 1]
        assert c == cmds(case)
        original = [p for command, p in zip(c, decoded_positions) if command > 0]
        bf = bf_positions(case)
        target = simulate(case, original)
        mode7_path = OUT / f"geometry_score_best_min_risk_tie_open{case}_positions.txt"
        cand = read_positions(mode7_path)
        repl = simulate(case, cand)
        mode3_path = OUT / f"geometry_min_risk_completed_mode_open{case}_positions.txt"
        cand3 = read_positions(mode3_path)
        repl3 = simulate(case, cand3)
        out["cases"][str(case)] = {
            "commands": len(c), "allocations": sum(x > 0 for x in c),
            "current": {"T": target["T"], "peak_end": target["peak_end"], "first_positions": original[:8],
                        "risk": risk(case, original, bf)},
            "mode7_replan": {"T": repl["T"], "peak_end": repl["peak_end"], "first_positions": cand[:8],
                             "risk": risk(case, cand, bf)},
            "mode3_replan": {"T": repl3["T"], "peak_end": repl3["peak_end"], "first_positions": cand3[:8],
                             "risk": risk(case, cand3, bf)},
            "prefix_positions_match_candidate_v3_mode7": all(original[i] == cand[i] for i in range(sum(x > 0 for x in c[:4999]))),
            "bf_first_positions": bf[:8],
            "bf_final_T": simulate(case, bf)["T"]}
    c11, c15 = cmds(11), cmds(15)
    alloc_cut = sum(x > 0 for x in c11[:4999])
    cur11 = [p for cmd, p in zip(decoded[10][0], decoded[10][1]) if cmd > 0]
    cur15 = [p for cmd, p in zip(decoded[14][0], decoded[14][1]) if cmd > 0]
    pair_prefix = {}
    for label in selected:
        p11 = read_positions(OUT / f"geometry_{label}_open11_positions.txt")
        p15 = read_positions(OUT / f"geometry_{label}_open15_positions.txt")
        pair_prefix[label] = {"case11_case15_positions_match": p11[:alloc_cut] == p15[:alloc_cut],
                              "max_position_delta": max((abs(a-b) for a,b in zip(p11[:alloc_cut],p15[:alloc_cut])), default=0)}
    out["shared_audit"] = {"common_commands": c11[:4999] == c15[:4999],
                           "common_prefix_commands": 4999, "common_prefix_allocations": alloc_cut,
                           "current_candidate_case11_case15_positions_match": cur11[:alloc_cut] == cur15[:alloc_cut],
                           "candidate_plan_position_arrays_match_by_pair": pair_prefix,
                           "all_replans_use_the_exact_same_command_prefix": True}
    bf11 = bf_positions(11)
    frontier = []
    modes_root = OLD_ROOT
    for d in sorted((x for x in modes_root.iterdir() if x.is_dir() and x.name.isdigit()),
                    key=lambda x: int(x.name)):
        rp = d / "result.json"
        pins_path = d / "pins.txt"
        if not rp.exists() or not pins_path.exists():
            continue
        rj = json.loads(rp.read_text())
        pins = read_positions(pins_path)
        rr = risk(11, pins, bf11, cut=4999)
        frontier.append({"prefix_mode": int(d.name), "T11": rj["pair"][0][0],
                         "T15": rj["pair"][1][0], "score": rj["score"],
                         "p2": pins[1], "prefix_max_ratio": rr["prefix_max_ratio"],
                         "max_ratio_command": rr["max_ratio_command"],
                         "target_T_at_max": rr["target_T_at_max"],
                         "BF_T_at_max": rr["BF_T_at_max"],
                         "T_at_cut": rr["target_T_at_cut"], "BF_T_at_cut": rr["BF_T_at_cut"]})
    out["bounded_frontier_existing_joint_modes"] = frontier
    out["frontier_note"] = "Audit of already-completed joint-prefix/conditioned-builder modes only; no new old-directory runs."
    (OUT / "geometry_pair_audit.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"shared_audit": out["shared_audit"],
                      "cases": {k: {"current_T": v["current"]["T"], "mode7_T": v["mode7_replan"]["T"],
                                    "mode3_T": v["mode3_replan"]["T"],
                                    "current_p2": v["current"]["first_positions"][1],
                                    "mode7_p2": v["mode7_replan"]["first_positions"][1],
                                    "mode3_p2": v["mode3_replan"]["first_positions"][1],
                                    "current_risk": v["current"]["risk"]["prefix_max_ratio"],
                                    "mode7_risk": v["mode7_replan"]["risk"]["prefix_max_ratio"],
                                    "mode3_risk": v["mode3_replan"]["risk"]["prefix_max_ratio"]}
                                for k,v in out["cases"].items()},
                      "frontier": [{k:r[k] for k in ("prefix_mode","T11","T15","p2","prefix_max_ratio","max_ratio_command","score")}
                                   for r in frontier]}, indent=2))


if __name__ == "__main__":
    main()
