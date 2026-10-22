# OPEN15_FULL_OVERFIT. Group shared-prefix holes by BOTH known continuations.
import json,bisect,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());a=j['cases'][10];b=j['cases'][14]
def life(c):
 l=[];bo=[];d=[]
 for t,x in enumerate(c['commands']):
  if x>0:l.append(x);bo.append(t);d.append(len(c['commands']))
  else:d[-x-1]=t
 return l,bo,d
lens,born,dead=life(a);_,_,db=life(b);source=ROOT/'case11/rotation/raw-search-best-h20799.txt';pos=list(map(int,source.read_text().split()));H=max(x+l for x,l in zip(pos,lens));chosen=[i for i in range(4006) if dead[i]>=4999 and db[i]<200000];cuts=sorted({0,H}|{v for i in chosen for v in (pos[i],pos[i]+lens[i])});segs=list(zip(cuts,cuts[1:]));chosen_at={pos[i]:i for i in chosen};rest=[k for k,(l,r) in enumerate(segs) if l not in chosen_at];sel=[k for k,(l,r) in enumerate(segs) if l in chosen_at];out=ROOT/'joint-csp/biclass';out.mkdir(exist_ok=False)
for mode in range(4):
 def key(k):
  i=chosen_at[segs[k][0]];temp=dead[i]<9999
  return (int(temp) if mode&1 else int(not temp),dead[i] if temp and mode<2 else db[i])
 order=rest+sorted(sel,key=key);starts={};cursor=0
 for k in order:starts[k]=cursor;cursor+=segs[k][1]-segs[k][0]
 plan=[]
 for x,l in zip(pos,lens):
  k=bisect.bisect_right(cuts,x)-1;plan.append(-1 if x+l>segs[k][1] else starts[k]+x-segs[k][0])
 d=out/str(mode);d.mkdir();part=d/'partial.txt';part.write_text('\n'.join(map(str,plan))+'\n');print('MODE',mode,'removed',plan.count(-1),flush=True)
 for rm in range(8):
  dest=d/f'11-{rm}.txt';rc=e.invoke([str(ROOT/'repair'),str(REPO/'data/pipes/open/11.in'),str(part),str(dest),str(H),str(rm),'1'],d,f'greedy-{rm}.log',60)
  print('greedy',mode,rm,rc,(d/f'greedy-{rm}.log').read_text().strip(),flush=True)
  if rc==0:e.save(d/'success.json',{'plan':str(dest),'H':H});break
