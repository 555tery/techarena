#!/usr/bin/env python3
"""Independent domain audit of the four-endpoint repair neighborhood."""
from pathlib import Path
from itertools import product
import hashlib,json,re
ROOT=Path(__file__).resolve().parent; CONT=ROOT.parents[1]; REPO=Path(__file__).resolve().parents[5]
DATA=REPO/'data/pipes/open/11.in'; SOURCE=CONT/'surgery-all-prefix/0/partial.txt'
BASE=CONT/'joint-csp/min2-17.txt.invalid-best'; CPP=CONT/'joint-csp/repair_min2.cpp'; BIN=CONT/'joint-csp/repair_min2'
VARIABLES=[6135,6339,6213,6214];H=20800

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=DATA.read_text().split();n=int(t[1]);cmd=list(map(int,t[2:2+n]));L=[0];B=[-1];D=[n]
for k,c in enumerate(cmd):
 if c>0:L.append(c);B.append(k);D.append(n)
 else:D[-c]=k
tok15=(REPO/'data/pipes/open/15.in').read_text().split();n15=int(tok15[1]);cmd15=list(map(int,tok15[2:2+n15]));D15=[n15];pid15=0
for k,c in enumerate(cmd15):
 if c>0:pid15+=1;D15.append(n15)
 else:D15[-c]=k
partial=list(map(int,(ROOT/'partial-four.txt').read_text().split()));initial=list(map(int,(ROOT/'initial-invalid.txt').read_text().split()))
source=list(map(int,SOURCE.read_text().split()))
invalid_best=Path(str(ROOT/'four-free-repair.txt')+'.invalid-best')
result=list(map(int,invalid_best.read_text().split())) if invalid_best.exists() else initial
special=[i for i in range(1,len(L)) if B[i]<4999 and D[i]>=4999 and D15[i]<n15]
# Exact allowed domains for the 4 variables against all fixed PIDs.
doms={}
for v in VARIABLES:
 diff=[0]*(H+2)
 for j,p in enumerate(partial,1):
  if p<0 or max(B[v],B[j])>=min(D[v],D[j]):continue
  lo=max(0,p-L[v]+1);hi=min(H-L[v],p+L[j]-1)
  if lo<=hi:diff[lo]+=1;diff[hi+1]-=1
 running=0;dom=[]
 for x in range(H-L[v]+1):
  running+=diff[x]
  if running==0:dom.append(x)
 doms[str(v)]=dom
solutions=[]
def rec(k,chosen):
 if k==len(VARIABLES):solutions.append(chosen.copy());return
 v=VARIABLES[k]
 for x in doms[str(v)]:
  if all(x+L[v]<=y or y+L[u]<=x for u,y in chosen.items()):
   chosen[v]=x;rec(k+1,chosen);chosen.pop(v)
rec(0,{})
# Confirm all pairs in plan and peak/height by independent cell occupancy replay.
h=max(result[i-1]+L[i] for i in range(1,len(L)))
occ=[[] for _ in range(h+1)];conflicts=set();vol=peak=0;peak_at=0;pid=0
for it,c in enumerate(cmd):
 if c>0:
  pid+=1;p=result[pid-1]
  for x in range(p,p+c):
   for q in occ[x]:conflicts.add(tuple(sorted((pid,q))))
  for x in range(p,p+c):occ[x].append(pid)
  vol+=c
  if vol>peak:peak=vol;peak_at=it
 else:
  q=-c;p=result[q-1]
  for x in range(p,p+L[q]):
   assert q in occ[x];occ[x].remove(q)
  vol-=L[q]
assert len(special)==66 and all(source[i-1]>=0 and source[i-1]==result[i-1] for i in special)
report={'scope':'bounded exact audit of four released endpoints; no platform or native harness',
 'case11':{'commands':n,'allocations':len(L)-1,'H':h,'T':20*((h+19)//20),'peak_live_volume':peak,'peak_at_command':peak_at},
 'released_pids':VARIABLES,'domain_starts_against_fixed_background':doms,
 'valid_joint_assignments_in_four_pid_neighborhood':len(solutions),'example_assignments':solutions[:3],
 'remaining_conflict_pairs':[list(x) for x in sorted(conflicts)],
 'special_prefix_pids':len(special),'all_match_source':True,'pid1_address':result[0],
 'repair_log_tail':(ROOT/'four-free-repair.log').read_text(errors='replace')[-600:],
 'sha256':{'input11':sha(DATA),'prefix_partial_source':sha(SOURCE),'base_invalid_plan':sha(BASE),
 'solver_source':sha(CPP),'solver_binary':sha(BIN),'partial_four':sha(ROOT/'partial-four.txt'),
 'initial_invalid':sha(ROOT/'initial-invalid.txt'),'attempted_invalid_best':sha(invalid_best) if invalid_best.exists() else None,
 'repair_log':sha(ROOT/'four-free-repair.log')}}
(ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
