#!/usr/bin/env python3
"""Independent occupancy replay of the best compact-prefix Open11 attempt."""
from pathlib import Path
import hashlib,json,math
REPO=Path(__file__).resolve().parents[4]; ROOT=Path(__file__).resolve().parent
OVER=ROOT.parents[1]; DATA=REPO/'data/pipes/open'
CUT=4999; PREFIX_ALLOCS=4006

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replay(k,plan_path):
    tok=(DATA/f'{k}.in').read_text().split(); n=int(tok[1]); cmd=list(map(int,tok[2:2+n]))
    pos=list(map(int,Path(plan_path).read_text().split()))
    allocs=sum(c>0 for c in cmd); assert len(pos)==allocs,(k,len(pos),allocs)
    h=max((p+c for p,c in zip(pos,[x for x in cmd if x>0])),default=0)
    occ=[0]*(h+1); sizes=[0]; pid=0; active_volume=0; peak=0; peak_at=0; dels=0
    for t,c in enumerate(cmd):
        if c>0:
            pid+=1;p=pos[pid-1]
            assert p>=0
            for x in range(p,p+c):
                if occ[x]:raise AssertionError((k,t,pid,'overlap',occ[x],x))
            for x in range(p,p+c):occ[x]=pid
            sizes.append(c);active_volume+=c
            if active_volume>peak:peak=active_volume;peak_at=t
        else:
            q=-c;p=pos[q-1];s=sizes[q]
            for x in range(p,p+s):
                if occ[x]!=q:raise AssertionError((k,t,q,'bad deletion occupancy',x,occ[x]))
                occ[x]=0
            active_volume-=s;dels+=1
    return {'case':k,'commands':n,'allocations':allocs,'deletions':dels,'survivors':allocs-dels,
      'H':h,'T':20*math.ceil(h/20),'peak_live_volume':peak,'peak_at_command':peak_at,'plan_sha256':sha(plan_path)}

plan=ROOT/'conditioned11/reverse_5_positions.txt'; pins=list(map(int,(ROOT/'pins15_componentpacked.txt').read_text().split()))
result=replay(11,plan); vals=list(map(int,plan.read_text().split()))
assert vals[:PREFIX_ALLOCS]==pins and vals[0]==0
# Raw mode-2 case15 is checked here as a reference plan too.
raw15=OVER/'future/2/15.txt'; raw_result=replay(15,raw15)
report={'scope':'independent cell-occupancy replay; offline conditioned plan only; no native harness',
  'common_prefix_commands':4999,'prefix_allocations':4006,'pid1_address':vals[0],
  'pins_match':True,'case11_candidate':result,'raw_case15_mode2_reference':raw_result,
  'sha256':{'input11':sha(DATA/'11.in'),'input15':sha(DATA/'15.in'),
    'pins':sha(ROOT/'pins15_componentpacked.txt'),'candidate11':sha(plan),'raw15_mode2':sha(raw15)}}
(ROOT/'reverse-attempt-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
