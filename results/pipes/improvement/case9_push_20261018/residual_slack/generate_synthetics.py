#!/usr/bin/env python3
"""Predeclare eight fresh, varied streams for the zero-cost residual-gap screen."""
from pathlib import Path
import hashlib
import json
import random

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "synthetic_fresh"
OUT.mkdir(parents=True, exist_ok=True)
profiles = [
    {"name":"geom2_odd_136_fresh","sizes":[1,2,4,8,16,32],"counts":[136]*6,"delete":"odd_half"},
    {"name":"geom2_even_184_fresh","sizes":[1,2,4,8,16,32],"counts":[184]*6,"delete":"even_half"},
    {"name":"geom2_wobble_224_fresh","sizes":[1,2,4,8,16,32],"counts":[224,160,256,192,128,256],"delete":"odd_half"},
    {"name":"geom2_phase_shift_fresh","sizes":[1,2,4,8,16,32],"counts":[128,192,160,224,256,192],"delete":"alternating_parity"},
    {"name":"geom2_reverse_160_fresh","sizes":[1,2,4,8,16,32],"counts":[160]*6,"delete":"odd_half_reverse"},
    {"name":"scale3_192_fresh","sizes":[3,6,12,24],"counts":[192,160,224,256],"delete":"odd_half"},
    {"name":"geom2_random50_192_fresh","sizes":[1,2,4,8,16,32],"counts":[192]*6,"delete":"random_half","seed":7719},
    {"name":"geom2_odd40_240_fresh","sizes":[1,2,4,8,16,32],"counts":[240]*6,"delete":"odd_40pct"},
]
manifest={"title":"Case 9 zero-cost future-gap reservation screen","date":"2026-10-18","generated_before_candidate_runs":True,"profiles":[]}
for profile in profiles:
    commands=[]; next_pid=1; rng=random.Random(profile.get("seed",0))
    for phase,(size,count) in enumerate(zip(profile["sizes"],profile["counts"])):
        pids=list(range(next_pid,next_pid+count)); next_pid+=count
        commands.extend([size]*count)
        mode=profile["delete"]
        if mode=="odd_half": deleted=[p for p in pids if p%2==1][:count//2]
        elif mode=="even_half": deleted=[p for p in pids if p%2==0][:count//2]
        elif mode=="odd_half_reverse": deleted=[p for p in pids if p%2==1][:count//2][::-1]
        elif mode=="odd_40pct": deleted=[p for p in pids if p%2==1][:int(count*.40)]
        elif mode=="alternating_parity":
            parity=(phase+1)%2
            deleted=[p for p in pids if p%2==parity][:count//2]
        elif mode=="random_half": deleted=sorted(rng.sample(pids,count//2))
        else: raise ValueError(mode)
        commands.extend(-p for p in deleted)
    path=OUT/(profile["name"]+".in")
    path.write_text("1.0 %d\n%s\n0\n"%(len(commands),"\n".join(map(str,commands))),encoding="ascii")
    data=path.read_bytes()
    manifest["profiles"].append({**profile,"path":str(path.relative_to(ROOT)),"operations":len(commands),"sha256":hashlib.sha256(data).hexdigest()})
(ROOT/"synthetic_fresh_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
