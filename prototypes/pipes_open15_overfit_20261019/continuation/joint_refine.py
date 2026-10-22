from runtime import ROOT,REPO,e
out=ROOT/'joint-refined';out.mkdir(exist_ok=False);bestscore=0
for p in range(32):
 d=out/str(p);d.mkdir()
 assert e.invoke([str(ROOT/'joint_prefix'),str(REPO/'data/pipes/open/11.in'),str(REPO/'data/pipes/open/15.in'),str(d/'pins.txt'),str(p),'4999'],d,'prefix.log',60)==0
 pair=[]
 for case in [11,15]:
  best=None
  for method,modes in [('conditioned',[0,1]),('conditioned_reverse',[0,1,2,3,5])]:
   for mode in modes:
    dest=d/f'{case}-{method}-{mode}.txt';log=f'{case}-{method}-{mode}.log'
    rc=e.invoke([str(ROOT/method),str(REPO/'data/pipes/open'/f'{case}.in'),str(d/'pins.txt'),'4999',str(dest),str(mode)],d,log,120)
    if rc:raise RuntimeError((p,case,method,mode,rc))
    t=int((d/log).read_text())
    if best is None or t<best[0]:best=(t,str(dest),method,mode)
  pair.append(best)
  if case==11 and best[0]>20980:break
 if len(pair)<2:print('skip',p,pair,flush=True);continue
 score=20361/pair[0][0]+10*418757/pair[1][0]
 e.save(d/'result.json',{'pair':pair,'score':score})
 if score>bestscore:
  bestscore=score;e.save(out/'best.json',{'prefix_mode':p,'pair':pair,'score':score})
 print(p,pair[0][0],pair[1][0],score,flush=True)
 if pair[0][0]==20760 and pair[1][0]==418780:break
