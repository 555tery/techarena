import json
from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());lengths=[x for x in j['cases'][12]['commands'] if x>0];pos=list(map(int,(ROOT/'case13/positions.txt').read_text().split()))
out=ROOT/'reflect13';out.mkdir(exist_ok=False);bestscore=0
for label,newpos in [('reflect3219',[3219-x-l for x,l in zip(pos,lengths)]),('reflect3220',[3220-x-l for x,l in zip(pos,lengths)]),('shift1',[x+1 for x in pos])]:
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
