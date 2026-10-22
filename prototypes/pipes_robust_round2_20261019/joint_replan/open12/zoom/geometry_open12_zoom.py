#!/usr/bin/env python3
"""Narrow Open12 BF-prefix zoom over command cuts 151, 256, and 384."""
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
SOURCE = REPO / "prototypes/pipes_v5_robust_20261019/candidate-v3/solution.cpp"
BUILDER = REPO / "prototypes/pipes_open15_overfit_20261019/continuation/conditioned.cpp"
INPUT = REPO / "data/pipes/open/12.in"
PROBE = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"
BOUND = 10260
PREFIXES = [151, 256, 384]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def trace_plan(commands, positions):
    assert len(positions) == sum(c > 0 for c in commands)
    maxend = max((x + c for x, c in zip(positions, [c for c in commands if c > 0])), default=0)
    occupied = bytearray(maxend + 1)
    active, T, live, peak_live, cursor = {}, 0, 0, 0, 0
    trace = []
    for ti, c in enumerate(commands, 1):
        if c > 0:
            pid = cursor + 1
            x = positions[cursor]
            cursor += 1
            assert x >= 0 and x + c <= len(occupied), (ti, pid, x, c)
            assert not any(occupied[x:x+c]), ("overlap", ti, pid, x, c)
            occupied[x:x+c] = b"\1" * c
            active[pid] = (x, c)
            live += c
            peak_live = max(peak_live, live)
            T = max(T, 20 * ((x + c + 19) // 20))
        else:
            assert -c in active, ("bad delete", ti, c)
            x, n = active.pop(-c)
            assert all(occupied[x:x+n]), ("bad occupancy at deletion", ti, c, x, n)
            occupied[x:x+n] = b"\0" * n
            live -= n
        trace.append(T)
    assert cursor == len(positions)
    return trace, {"valid": True, "allocation_count": cursor, "remaining_live_pipes": len(active),
                   "peak_live_volume_m": peak_live, "max_endpoint_m": maxend, "final_T_m": T}


def main():
    toks = list(map(int, INPUT.read_text().split()))
    commands = toks[2:2+toks[1]]
    assert len(commands) == 1501
    bf = subprocess.run([str(PROBE), "bestfit", str(TAPE)],
                        input="\n".join(map(str, commands + [0])) + "\n",
                        text=True, capture_output=True, check=True, timeout=30).stdout.splitlines()
    assert len(bf) == len(commands)
    bftrace, bt = [], 0
    for c, row in zip(commands, bf):
        if c > 0:
            d, _ = map(int, row.split())
            bt += 20*d
        bftrace.append(bt)

    comp = subprocess.run(["/usr/bin/clang++", "-std=c++17", "-O3", str(BUILDER), "-o", str(OUT/"geometry_conditioned")],
                          text=True, capture_output=True, timeout=45)
    (OUT/"geometry_compile.log").write_text(comp.stdout+comp.stderr)
    if comp.returncode:
        raise RuntimeError("conditioned builder compilation failed")
    binary = OUT/"geometry_conditioned"
    attempts = []
    for cut in PREFIXES:
        pins = [int(row.split()[1]) for c,row in zip(commands[:cut],bf[:cut]) if c > 0]
        pins_path = OUT/f"geometry_open12_prefix_{cut}_pins.txt"
        pins_path.write_text("\n".join(map(str,pins))+"\n")
        modes=[]
        for mode in range(4):
            dest=OUT/f"geometry_open12_prefix_{cut}_mode{mode}_positions.txt"
            p=subprocess.run([str(binary),str(INPUT),str(pins_path),str(cut),str(dest),str(mode)],
                             text=True,capture_output=True,timeout=20)
            (OUT/f"geometry_open12_prefix_{cut}_mode{mode}.log").write_text(p.stdout+p.stderr)
            row={"mode":mode,"returncode":p.returncode,"builder_T_m":int(p.stdout.split()[0]) if p.returncode==0 and p.stdout.split() else None}
            if p.returncode==0:
                pos=list(map(int,dest.read_text().split()))
                trace,physical=trace_plan(commands,pos)
                ratios=[trace[i]/bftrace[i] for i in range(len(commands)) if bftrace[i]>0]
                peak=max(ratios,default=1.0)
                ix=next(i for i in range(len(commands)) if bftrace[i]>0 and trace[i]/bftrace[i]==peak)
                row.update({"positions_file":dest.name,"positions_sha256":sha(dest),"position_count":len(pos),
                            "pinned_allocations":len(pins),"pinned_positions_match":pos[:len(pins)]==pins,
                            "physical_check":physical,"exact_T_10260":physical["final_T_m"]==BOUND,
                            "full_1501_max_ratio_target_over_BF":peak,"ratio_peak_command_1based":ix+1,
                            "ratio_peak_target_T_m":trace[ix],"ratio_peak_BF_T_m":bftrace[ix]})
            modes.append(row)
        attempts.append({"prefix_commands":cut,"pinned_allocations":len(pins),"pin_sha256":sha(pins_path),"modes":modes})

    exact=[(a["prefix_commands"],m) for a in attempts for m in a["modes"] if m.get("exact_T_10260")]
    chosen=min((m for _,m in exact),key=lambda m:(m["full_1501_max_ratio_target_over_BF"],m["mode"])) if exact else None
    baseline=json.loads((OUT.parent/"geometry_open12_audit.json").read_text())
    report={"scope":"Open12 narrow BF-prefix zoom only; cuts 151, 256, 384; four conditioned modes per cut",
            "candidate_v3_sha256":sha(SOURCE),"open12_input_sha256":sha(INPUT),"conditioned_builder_sha256":sha(BUILDER),
            "bound_T_m":BOUND,"current_v3_full_max_ratio":baseline["current_candidate_v3"]["max_ratio_all_1501_commands"],
            "previous_best_full_max_ratio":baseline["selected_exact_plan"]["all_1501_command_max_ratio_target_over_BF"],
            "tested_prefixes":PREFIXES,"exact_candidates_found":len(exact),"all_attempts":attempts,
            "selected_min_full_ratio_exact_candidate":None,"improves_previous_ratio":False,
            "selection_rule":"Among plans with independent physical replay T=10260, minimize max T_target/T_plain_BF across all 1501 commands, regardless of prefix length."}
    if chosen:
        src=OUT/chosen["positions_file"]
        dest=OUT/"geometry_open12_zoom_best_positions.txt"
        dest.write_bytes(src.read_bytes())
        pos=list(map(int,dest.read_text().split()))
        (OUT/"geometry_open12_zoom_best_pid_positions.tsv").write_text("pid\tstart_m\n"+"".join(f"{i+1}\t{x}\n" for i,x in enumerate(pos)))
        chosen={**chosen,"positions_file":dest.name,"positions_sha256":sha(dest),"pid_positions_file":"geometry_open12_zoom_best_pid_positions.tsv"}
        report["selected_min_full_ratio_exact_candidate"]=chosen
        report["improves_previous_ratio"]=chosen["full_1501_max_ratio_target_over_BF"] < report["previous_best_full_max_ratio"]
    report["sharedprefix_with_all_open15_current_v3"]=baseline["sharedprefix_with_current_v3_all15"]
    (OUT/"geometry_open12_zoom_audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"exact_count":len(exact),"selected":chosen,"improves_previous":report["improves_previous_ratio"],
                      "by_prefix":{str(a["prefix_commands"]):[(m["mode"],m.get("physical_check",{}).get("final_T_m"),m.get("full_1501_max_ratio_target_over_BF")) for m in a["modes"]] for a in attempts}},indent=2))


if __name__=="__main__":
    main()
