from runtime import ROOT,REPO,e
out=ROOT/'joint-knapsack';out.mkdir(exist_ok=False)
for p in [4,20,18,2]:
 d=out/str(p);d.mkdir();pins=ROOT/'joint-refined'/str(p)/'pins.txt';pair=[]
 for case,bound in [(11,20760),(15,418780)]:
  best=None
  for mode in range(2000,2008):
   dest=d/f'{case}-{mode}.txt';log=f'{case}-{mode}.log'
   assert e.invoke([str(ROOT/'conditioned_knapsack'),str(REPO/'data/pipes/open'/f'{case}.in'),str(pins),'4999',str(dest),str(mode)],d,log,180)==0
   t=int((d/log).read_text())
   if best is None or t<best[0]:best=(t,str(dest))
   if t==bound:break
  pair.append(best);print(p,case,best[0],flush=True)
 e.save(d/'result.json',{'pair':pair,'score':20361/pair[0][0]+10*418757/pair[1][0]})
