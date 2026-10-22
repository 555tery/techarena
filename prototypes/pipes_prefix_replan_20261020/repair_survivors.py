"""Public-only survivor rearrangement with exact lifetime obstacle domains."""
import argparse
import json
import sys
import time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_overfit_20261019/continuation/local-deps'))
from ortools.sat.python import cp_model

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='survivors8');ap.add_argument('--target-end',type=int,default=1000)
    ap.add_argument('--seconds',type=float,default=45);a=ap.parse_args()
    dest=HERE/'repairs'/a.name;dest.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    source=ROOT/'prototypes/pipes_g5420_cpu_20261020/solution.cpp';tables=decode(source)
    ci=7;case=j['cases'][ci];commands,positions=tables[ci];n=len(commands)
    pid=0;birth={};death={};bid_by_pid={};pos={};caps={};T=0
    for step,(c,x,bid) in enumerate(zip(commands,positions,case['block_ids'])):
        if c>0:
            pid+=1;birth[bid]=step;death[bid]=n;bid_by_pid[pid]=bid;pos[bid]=x
            T=max(T,20*((x+c+19)//20));caps[bid]=T
        else:death[bid_by_pid[-c]]=step
    selected={bid for bid in birth if birth[bid]>=388 and death[bid]==n}
    # These branches have already diverged, hence every selected block is unique.
    assert all(all(c==ci for l,r,c in j['blocks'][bid]['intervals']) for bid in selected)
    fixed=[bid for bid in birth if bid not in selected]
    model=cp_model.CpModel();xs={};rect=[];domains={}
    for bid in sorted(selected):
        L=j['blocks'][bid]['length'];cap=min(caps[bid],a.target_end if bid==5499 else caps[bid])-L
        forbidden=[]
        for other in fixed:
            if death[other]<=birth[bid]:continue
            l=max(0,pos[other]-L+1);r=min(cap,pos[other]+j['blocks'][other]['length']-1)
            if l<=r:forbidden.append((l,r))
        forbidden.sort();runs=[];cursor=0
        for l,r in forbidden:
            if cursor<l:runs.append((cursor,l-1))
            cursor=max(cursor,r+1)
        if cursor<=cap:runs.append((cursor,cap))
        if not runs:
            result={'success':False,'status':'EMPTY_DOMAIN','block':bid,'target_end':a.target_end}
            (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result);return
        domains[bid]=runs
        x=model.new_int_var_from_domain(cp_model.Domain.from_intervals(runs),f'x{bid}');xs[bid]=x
        rect.append(model.new_fixed_size_interval_var(x,L,f'R{bid}'))
        if any(l<=pos[bid]<=r for l,r in runs):model.add_hint(x,pos[bid])
    model.add_no_overlap(rect)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=a.seconds
    solver.parameters.num_search_workers=1;solver.parameters.random_seed=20261020
    print(json.dumps({'selected':len(selected),'target_domain':domains[5499],'target_end':a.target_end}),flush=True)
    status=solver.solve(model);success=status in [cp_model.OPTIMAL,cp_model.FEASIBLE]
    if success:
        changes={bid:solver.value(x) for bid,x in xs.items() if solver.value(x)!=pos[bid]}
        (dest/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    result={'success':success,'status':solver.status_name(status),'changes':len(changes) if success else None,
            'elapsed':time.monotonic()-start,'target_end':a.target_end,'source':str(source),'stats':solver.response_stats(),
            'scope':'case8 branch unique final survivors; all other public blocks fixed; public-prefix T bounded by old plan'}
    (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
