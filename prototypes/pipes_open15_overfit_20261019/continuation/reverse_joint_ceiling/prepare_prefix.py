#!/usr/bin/env python3
"""Compact the spatial connected components of raw Open15 mode-2's common prefix."""
from pathlib import Path
import hashlib, json, math
REPO=Path(__file__).resolve().parents[4]
ROOT=Path(__file__).resolve().parent
OVER=ROOT.parents[1]
DATA=REPO/'data/pipes/open'
CUT=4999

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(k):
    t=(DATA/f'{k}.in').read_text().split(); n=int(t[1]); c=list(map(int,t[2:2+n]))
    size=[0]; birth=[-1]; death=[n]; pidat=[0]*n
    for i,x in enumerate(c):
        if x>0: pid=len(size); pidat[i]=pid; size.append(x); birth.append(i); death.append(n)
        else: death[-x]=i
    return c,size,birth,death,pidat

def main():
    c11,s11,b11,d11,pa11=load(11); c15,s15,b15,d15,pa15=load(15)
    common=0
    for a,b in zip(c11,c15):
        if a!=b: break
        common+=1
    assert CUT<=common
    npre=sum(x>0 for x in c15[:CUT])
    raw=list(map(int,(OVER/'future/2/15.txt').read_text().split()))
    assert len(raw)==len(s15)-1 and npre==4006
    # Components are connected components of the union of every prefix PID's
    # address interval. Translating/reflection of a whole component preserves
    # every within-component overlap relation; packed components are disjoint.
    spans=sorted((raw[pid-1],raw[pid-1]+s15[pid],pid) for pid in range(1,npre+1))
    comps=[]
    for l,r,pid in spans:
        if comps and l<=comps[-1]['right']:
            comps[-1]['right']=max(comps[-1]['right'],r)
            comps[-1]['pids'].append(pid)
        else: comps.append({'left':l,'right':r,'pids':[pid]})
    p1comp=next(i for i,x in enumerate(comps) if 1 in x['pids'])
    # Put PID1's component first and reflect it, placing PID1 at address zero.
    order=[p1comp]+[i for i in range(len(comps)) if i!=p1comp]
    pins=[None]*npre; offset=0; placed=[]
    for ci in order:
        comp=comps[ci]; left=comp['left']; right=comp['right']; width=right-left
        reflect=(ci==p1comp)
        for pid in comp['pids']:
            old=raw[pid-1]
            local=(right-(old+s15[pid])) if reflect else (old-left)
            pins[pid-1]=offset+local
        placed.append({'source_component':ci,'source_interval':[left,right],
                       'target_interval':[offset,offset+width],
                       'width':width,'pid_count':len(comp['pids']),'reflected':reflect})
        offset+=width
    assert offset==sum(x['right']-x['left'] for x in comps)
    assert pins[0]==0
    path=ROOT/'pins15_componentpacked.txt'; path.write_text(''.join(f'{x}\n' for x in pins))
    # Validate all prefix commands under the transformed pins, independent of any builder.
    for label,cmd,size,pidat in [('11',c11,s11,pa11),('15',c15,s15,pa15)]:
        live=[0]*(offset+40); active=set(); alloc=0
        for t,c in enumerate(cmd[:CUT]):
            if c>0:
                pid=pidat[t]; p=pins[pid-1]
                for x in range(p,p+c):
                    if live[x]: raise AssertionError((label,t,pid,'overlap',live[x],x))
                for x in range(p,p+c): live[x]=pid
                active.add(pid); alloc+=1
            else:
                pid=-c
                assert pid in active,(label,t,pid,'inactive delete')
                p=pins[pid-1]
                for x in range(p,p+size[pid]):
                    if live[x]!=pid: raise AssertionError((label,t,pid,'missing live occupancy',x,live[x]))
                    live[x]=0
                active.remove(pid)
        assert alloc==npre
    raw_H=max(raw[i]+s15[i+1] for i in range(npre))
    report={'scope':'offline shared-prefix experiment; uses known future plan only to construct a compact prefix; no online/generalization claim',
      'common_prefix_commands':common,'prefix_commands':CUT,'prefix_allocations':npre,
      'raw15_mode2_prefix_H':raw_H,'raw15_mode2_prefix_T':20*math.ceil(raw_H/20),
      'raw15_pids_above_case11_ceiling':sum(raw[i]+s15[i+1]>20760 for i in range(npre)),
      'component_count':len(comps),'component_union_width':offset,
      'component_widths_descending':sorted([x['right']-x['left'] for x in comps],reverse=True),
      'placement_order':placed,'packed_prefix_H':max(pins[i]+s15[i+1] for i in range(npre)),
      'packed_prefix_T':20*math.ceil(max(pins[i]+s15[i+1] for i in range(npre))/20),
      'pid1_address':pins[0],'independent_prefix_replay_cases':[11,15],
      'sha256':{'input11':sha(DATA/'11.in'),'input15':sha(DATA/'15.in'),
        'raw15_mode2':sha(OVER/'future/2/15.txt'),'future_plans_cpp':sha(OVER/'future_plans.cpp'),
        'pins15_componentpacked':sha(path)}}
    (ROOT/'prefix-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='placement_order'},indent=2))
if __name__=='__main__': main()
