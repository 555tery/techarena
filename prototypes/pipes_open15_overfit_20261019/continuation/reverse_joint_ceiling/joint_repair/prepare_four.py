#!/usr/bin/env python3
"""Prepare a four-variable repair while fixing all other coordinates."""
from pathlib import Path
import json,hashlib
REPO=Path(__file__).resolve().parents[5]
ROOT=Path(__file__).resolve().parent
CONT=ROOT.parents[1]
SRC=CONT/'joint-csp'
SOURCE=CONT/'surgery-all-prefix/0/partial.txt'
FULL=SRC/'min2-17.txt.invalid-best'
DATA=REPO/'data/pipes/open/11.in'
VARIABLES=[6135,6339,6213,6214]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

tok=DATA.read_text().split(); n=int(tok[1]); cmd=list(map(int,tok[2:2+n]))
size=[0]; birth=[-1]; death=[n]
for t,c in enumerate(cmd):
    if c>0:size.append(c);birth.append(t);death.append(n)
    else:death[-c]=t
full=list(map(int,FULL.read_text().split())); pins=list(map(int,SOURCE.read_text().split()))
assert len(full)==len(size)-1==len(pins)
special=[i for i in range(1,len(size)) if birth[i]<4999 and death[i]>=4999]
# Stronger subset requested by coordinator: prefix PID survives 11 but dies before Open15 EOF.
t15=CONT.parent/'future/2/15.txt'
# Derive Open15 death table only to compute this exact subset.
t15tok=(REPO/'data/pipes/open/15.in').read_text().split();n15=int(t15tok[1]);c15=list(map(int,t15tok[2:2+n15]));d15=[n15]
for c in c15:
    if c>0:d15.append(n15)
    else:d15[-c]=len(d15)-1 # overwritten below with event index separately
# Rebuild cleanly with command index.
d15=[n15];pid=0
for t,c in enumerate(c15):
    if c>0:pid+=1;d15.append(n15)
    else:d15[-c]=t
special=[i for i in range(1,len(size)) if birth[i]<4999 and death[i]>=4999 and d15[i]<n15]
assert len(special)==66 and all(pins[i-1]>=0 and full[i-1]==pins[i-1] for i in special)
assert full[0]==0
assert all(1<=i<len(size) for i in VARIABLES)
# Independent online physical scan that records all overlapping live pairs.
occ=[[] for _ in range(max(full[i-1]+size[i] for i in range(1,len(size)))+1)]
active=set(); conflicts=set(); pid=0;vol=0;peak=0
for t,c in enumerate(cmd):
    if c>0:
        pid+=1;p=full[pid-1]
        for x in range(p,p+c):
            for q in occ[x]: conflicts.add(tuple(sorted((pid,q))))
        for x in range(p,p+c):occ[x].append(pid)
        active.add(pid);vol+=c;peak=max(peak,vol)
    else:
        q=-c;p=full[q-1]
        for x in range(p,p+size[q]):
            assert q in occ[x]
            occ[x].remove(q)
        active.remove(q);vol-=size[q]
expected={(6135,6339),(6213,6214)}
assert conflicts==expected,conflicts
partial=full.copy()
for pid in VARIABLES:partial[pid-1]=-1
pout=ROOT/'partial-four.txt';iout=ROOT/'initial-invalid.txt'
pout.write_text(''.join(f'{x}\n' for x in partial));iout.write_text(''.join(f'{x}\n' for x in full))
report={'case':11,'commands':n,'allocations':len(size)-1,'base_H':max(full[i-1]+size[i] for i in range(1,len(size))),
 'base_peak_live_volume':peak,'base_conflicts':[list(x) for x in sorted(conflicts)],'movable_pids':VARIABLES,
 'fixed_special_prefix_pids':len(special),'all_special_match_surgery_prefix':True,'pid1_address':full[0],
 'sha256':{'input11':sha(DATA),'surgery_prefix_partial':sha(SOURCE),'invalid_full_plan':sha(FULL),
 'partial_four':sha(pout),'initial_invalid':sha(iout)}}
(ROOT/'prepare-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
