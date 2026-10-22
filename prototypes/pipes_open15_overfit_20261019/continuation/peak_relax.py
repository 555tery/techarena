import sys,json
import numpy as np
from runtime import ROOT,REPO,e
sys.path.insert(0,str(ROOT/'case11'));from milp_repair import read_case,allowed_intervals
_,n,cmd,lens,born,died,_=read_case(REPO/'data/pipes/open/11.in');pos=list(map(int,(ROOT/'peak-repair/random/partial.txt').read_text().split()));mov={i+1 for i,x in enumerate(pos) if x<0};initial=len(mov);released=[];H=20760
for iteration in range(12):
 bad=[p for p in mov if not allowed_intervals(p,mov,H,lens,born,died,pos)]
 if not bad:break
 for pid in bad:
  cap=H-lens[pid];diff=np.zeros(cap+2,dtype=np.int32);ranges=[]
  for q in range(1,len(lens)):
   if q in mov or max(born[pid],born[q])>=min(died[pid],died[q]):continue
   l=max(0,pos[q-1]-lens[pid]+1);r=min(cap,pos[q-1]+lens[q]-1)
   if l<=r:
    weight=1000000 if q==1 else 1;diff[l]+=weight;diff[r+1]-=weight;ranges.append((q,l,r))
  costs=np.cumsum(diff[:-1]);x=int(np.argmin(costs));blockers=[q for q,l,r in ranges if l<=x<=r];assert 1 not in blockers
  for q in blockers:mov.add(q);pos[q-1]=-1
  released.append({'pid':pid,'candidate':x,'blockers':blockers})
 if len(mov)>initial+35:break
out=ROOT/'peak-relax';out.mkdir();(out/'partial.txt').write_text('\n'.join(map(str,pos))+'\n');e.save(out/'release.json',{'initial':initial,'movable':len(mov),'released':released});print('movable',len(mov),flush=True)
rc=e.invoke([sys.executable,'-B',str(ROOT/'milp_partial.py'),'--input',str(REPO/'data/pipes/open/11.in'),'--source-positions',str(out/'partial.txt'),'--output-positions',str(out/'milp.txt'),'--target','20760','--seconds','120'],out,'milp.log',220)
print('rc',rc);print('\n'.join((out/'milp.log').read_text().splitlines()[-20:]))
