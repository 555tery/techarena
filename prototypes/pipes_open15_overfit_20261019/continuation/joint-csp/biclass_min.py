import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from runtime import ROOT,REPO,e
out=ROOT/'joint-csp';base=list(map(int,(out/'partial-17.txt').read_text().split()));initial=list(map(int,(out/'min2-17.txt.invalid-best').read_text().split()))
for mode in range(4):
 d=out/f'biclass/{mode}';p=list(map(int,(d/'partial.txt').read_text().split()));ini=initial[:]
 for i,x in enumerate(p):
  if base[i]<0:p[i]=-1
  if p[i]>=0:ini[i]=p[i]
 part=d/'relaxed.txt';part.write_text('\n'.join(map(str,p))+'\n');init=d/'initial.invalid.txt';init.write_text('\n'.join(map(str,ini))+'\n');dest=d/'solved.txt'
 rc=e.invoke([str(out/'repair_min2'),str(REPO/'data/pipes/open/11.in'),str(part),str(dest),'20799','30',str(137+mode),str(init)],d,'min.log',40);print(mode,rc,(d/'min.log').read_text()[-1200:],flush=True)
 if rc==0:e.save(d/'success.json',{'plan':str(dest),'H':20799});break
