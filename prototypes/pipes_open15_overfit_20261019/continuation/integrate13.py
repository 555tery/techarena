import json
from runtime import ROOT,REPO,e
from export import export
out=ROOT/'integrate13';out.mkdir(exist_ok=False)
p=(ROOT/'case13/positions.txt').read_text().split();(out/'pins.txt').write_text('\n'.join(p[:210])+'\n')
best=None
for mode in range(4):
 dest=out/f'8-{mode}.txt'
 rc=e.invoke([str(ROOT/'conditioned'),str(REPO/'data/pipes/open/8.in'),str(out/'pins.txt'),'388',str(dest),str(mode)],out,f'{mode}.log',180)
 assert rc==0,(mode,rc)
 t=int((out/f'{mode}.log').read_text());print(mode,t,flush=True)
 if best is None or t<best[0]:best=t,dest
plans={str(i):str(ROOT/'conditioned-plans'/str(i)/'best.txt') for i in range(1,16)}
plans['13']=str(ROOT/'case13/positions.txt');plans['8']=str(best[1]);e.save(out/'mapping.json',plans)
if best[0]==4640:export(plans,ROOT/'release-v2')
