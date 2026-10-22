# OPEN15_FULL_OVERFIT. Bounded-domain CSP around causal shared-prefix layout.
import sys,json,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime import ROOT,PARENT,REPO,e
import numpy as np
j=json.loads((PARENT/'joint.json').read_text());c=j['cases'][10];lens=[0];born=[0];dead=[len(c['commands'])]
for t,x in enumerate(c['commands']):
 if x>0:lens.append(x);born.append(t);dead.append(len(c['commands']))
 else:dead[-x]=t
nd=200000;db=[nd]*(len(lens))
for t,x in enumerate(j['cases'][14]['commands']):
 if x<0 and -x<len(lens):db[-x]=t
protected={i for i in range(1,4007) if dead[i]>=4999 and db[i]<nd}|{1}
out=ROOT/'joint-csp';H=20799
pos=[-1]+list(map(int,(ROOT/'surgery-all-prefix/0/partial.txt').read_text().split()))
for it in range(20):
 part=out/f'partial-{it}.txt';part.write_text('\n'.join(map(str,pos[1:]))+'\n');dest=out/f'plan-{it}.txt'
 rc=e.invoke([str(out/'repair_csp'),str(REPO/'data/pipes/open/11.in'),str(part),str(dest),str(H),'15',str(271+it)],out,f'run-{it}.log',25)
 log=(out/f'run-{it}.log').read_text();print(it,rc,log[:550],flush=True)
 if rc==0:
  pins=out/f'pins-{it}.txt';pins.write_text('\n'.join(dest.read_text().split()[:4006])+'\n')
  for method,m in [('conditioned_reverse',2),('conditioned_knapsack',2002)]:
   p15=out/f'15-{it}-{method}.txt';e.invoke([str(ROOT/method),str(REPO/'data/pipes/open/15.in'),str(pins),'4999',str(p15),str(m)],out,f'15-{it}-{method}.log',180)
   print('RESULT15',it,method,(out/f'15-{it}-{method}.log').read_text(),flush=True)
  break
 ids=set(map(int,re.findall(r'DEAD placed (\d+)',log)+re.findall(r'conflict (\d+)',log)+re.findall(r'EMPTY (\d+)',log)))
 if not ids:break
 released=set()
 for pid in ids:
  # Cheapest additional feasible slot: minimize removed volume, protect shared-prefix destined-for-removal strips.
  cap=H-lens[pid];diff=np.zeros(cap+2,dtype=np.int64);ranges=[]
  for q in range(1,len(lens)):
   if pos[q]<0 or max(born[pid],born[q])>=min(dead[pid],dead[q]):continue
   l=max(0,pos[q]-lens[pid]+1);r=min(cap,pos[q]+lens[q]-1)
   if l<=r:
    cost=100000000 if q in protected else 1000+lens[q]
    diff[l]+=cost;diff[r+1]-=cost;ranges.append((q,l,r))
  costs=np.cumsum(diff[:-1]);costs[costs==0]=1000000000
  x=int(np.argmin(costs));qs={q for q,l,r in ranges if l<=x<=r}
  if not qs&protected:released |= qs
 if not released:break
 for q in released:pos[q]=-1
 print('released',sorted(released),'total',pos[1:].count(-1),flush=True)
