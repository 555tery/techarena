import json
from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());c=j['cases'][12];lengths=[x for x in c['commands'] if x>0];pos=list(map(int,(ROOT/'case13/positions.txt').read_text().split()));assert -1 not in c['commands']
out=ROOT/'rotate13';out.mkdir(exist_ok=False)
for H,reflect in [(3219,False),(3220,False),(3219,True),(3220,True)]:
 base=[H-x-l for x,l in zip(pos,lengths)] if reflect else pos
 cut=base[0];assert all(not (x<cut<x+l) for x,l in zip(base,lengths))
 newpos=[x-cut if x>=cut else x+H-cut for x in base];label=f'{H}-{reflect}'
 d=out/label;d.mkdir();(d/'13.txt').write_text('\n'.join(map(str,newpos))+'\n');(d/'pins.txt').write_text('\n'.join(map(str,newpos[:210]))+'\n');best=None
 for method,modes in [('conditioned',range(4)),('conditioned_reverse',range(8))]:
  for mode in modes:
   dest=d/f'8-{method}-{mode}.txt';log=f'{method}-{mode}.log'
   assert e.invoke([str(ROOT/method),str(REPO/'data/pipes/open/8.in'),str(d/'pins.txt'),'388',str(dest),str(mode)],d,log,120)==0
   t=int((d/log).read_text())
   if best is None or t<best[0]:best=(t,str(dest))
   if t==4640:break
  if best[0]==4640:break
 e.save(d/'best.json',{'T':best[0],'plan8':best[1],'plan13':str(d/'13.txt')});print(label,best,flush=True)
 if best[0]==4640:break
