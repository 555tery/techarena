#!/usr/bin/env python3
"""Benchmark online rounded allocation slots against the same stream sets."""
import json, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SIM=ROOT/"experiments/padded_sim"
OPEN=sorted((ROOT/"data/pipes/open").glob("*.in"),key=lambda p:int(p.stem))
SYNTH=sorted((ROOT/"experiments/generated").glob("*.in"))
OUT=ROOT/"results/strategy-padding"
ROW=re.compile(r"^(.*?) weight=([0-9.]+) alive=(\d+) H=(\d+) lb=(\d+) gap=(\d+) KPI=([0-9.eE+-]+)")

def run(q, files, preserve):
    args=[str(SIM),str(q),*map(str,files)]
    if preserve: args.append("--tail=preserve")
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,check=True)
    result={}
    for line in p.stdout.splitlines():
        m=ROW.match(line)
        if m:
            name,w,live,h,lb,gap,kpi=m.groups()
            result[Path(name).name]={"weight":float(w),"alive":int(live),"H":int(h),"lower_bound":int(lb),"gap":int(gap),"KPI":float(kpi)}
    if len(result)!=len(files): raise RuntimeError(p.stdout+p.stderr)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True); rows=[]
    for q in (1,2,3,4,5,8,10,20,40):
        for preserve in (False,True):
            op=run(q,OPEN,preserve); sy=run(q,SYNTH,preserve)
            rec={"quantum":q,"preserve_tail":preserve,
                 "open_weighted_score":sum(x["weight"]*x["KPI"] for x in op.values()),
                 "open_weight_sum":sum(x["weight"] for x in op.values()),
                 "synthetic_mean_KPI":sum(x["KPI"] for x in sy.values())/len(sy),
                 "synthetic_worst_KPI":min(x["KPI"] for x in sy.values()),
                 "synthetic_mean_H_over_lower_bound":sum(x["H"]/x["lower_bound"] for x in sy.values())/len(sy),
                 "open":op,"synthetic":sy}
            rows.append(rec)
            print(f"q={q:2d} tail={str(preserve):5s} open={rec['open_weighted_score']:.6f}/32.1"
                  f" synth={rec['synthetic_mean_KPI']:.6f} worst={rec['synthetic_worst_KPI']:.6f}"
                  f" H/lb={rec['synthetic_mean_H_over_lower_bound']:.4f}")
    (OUT/"matrix.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
