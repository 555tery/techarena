"""Bounded public-only exchanges around one harmful replay endpoint."""
import argparse,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_overfit_20261019/continuation/local-deps'))
from ortools.sat.python import cp_model

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='local-exchange8');ap.add_argument('--target',type=int,default=5499)
    ap.add_argument('--source',type=Path,default=ROOT/'prototypes/pipes_g5420_cpu_20261020/solution.cpp');a=ap.parse_args()
    start=time.monotonic();out=HERE/'repairs'/a.name;out.mkdir(parents=True,exist_ok=False)
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    commands,pp=decode(a.source)[7]
    case=j['cases'][7];n=len(commands);birth={};death={};pos={};caps={};pids={};pid=T=0
    for step,(c,x,bid) in enumerate(zip(commands,pp,case['block_ids'])):
        if c>0:
            pid+=1;pids[pid]=bid;birth[bid]=step;death[bid]=n;pos[bid]=x;T=max(T,20*((x+c+19)//20));caps[bid]=T
        else:death[pids[-c]]=step
    target=a.target;L=lambda bid:j['blocks'][bid]['length']
    survivors={bid for bid in pos if birth[bid]>=388 and death[bid]==n}
    overlaps=lambda a,b: max(birth[a],birth[b])<min(death[a],death[b])
    starts=sorted({pos[bid] for bid in survivors if pos[bid]<pos[target]}|{346,480,578,633})
    trials=[];best=None
    for x in starts:
        if time.monotonic()-start>60:break
        blockers={b for b in pos if b!=target and overlaps(b,target) and pos[b]<x+L(target) and pos[b]+L(b)>x}
        if not blockers or not blockers<=survivors or len(blockers)>7:continue
        selected=blockers|{target};fixed=[b for b in pos if b not in selected]
        model=cp_model.CpModel();xs={};rect=[];empty=False
        for b in sorted(selected):
            cap=caps[b]-L(b);forbidden=[]
            for f in fixed:
                if not overlaps(b,f):continue
                l=max(0,pos[f]-L(b)+1);r=min(cap,pos[f]+L(f)-1)
                if l<=r:forbidden.append((l,r))
            forbidden.sort();runs=[];cursor=0
            for l,r in forbidden:
                if cursor<l:runs.append((cursor,l-1))
                cursor=max(cursor,r+1)
            if cursor<=cap:runs.append((cursor,cap))
            if not runs:empty=True;break
            z=model.new_int_var_from_domain(cp_model.Domain.from_intervals(runs),f'x{b}');xs[b]=z
            rect.append(model.new_fixed_size_interval_var(z,L(b),f'r{b}'))
            if b==target:model.add(z==x)
            elif any(l<=pos[b]<=r for l,r in runs):model.add_hint(z,pos[b])
        if empty:continue
        model.add_no_overlap(rect);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=.75
        solver.parameters.num_search_workers=1;solver.parameters.random_seed=20261020
        status=solver.solve(model);trials.append({'x':x,'blocks':len(selected),'status':solver.status_name(status)})
        if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
            best={b:solver.value(z) for b,z in xs.items() if solver.value(z)!=pos[b]};break
    if best:(out/'changes.json').write_text(json.dumps(best,indent=2)+'\n')
    result={'success':bool(best),'changes':best,'trials':trials,'elapsed':time.monotonic()-start,
            'source':str(a.source),'target':target,
            'scope':'public case8 branch-only local survivor exchange; all other placements fixed; endpoints<=old public trench at birth'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
