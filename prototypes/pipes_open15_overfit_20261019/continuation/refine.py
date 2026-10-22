from runtime import ROOT,PARENT,REPO,e
out=ROOT/'refined';out.mkdir(exist_ok=False)
for case,parent,prefix,count in [(8,ROOT/'case13/positions.txt',388,210),(15,PARENT/'future/1/11.txt',4999,4006)]:
 d=out/str(case);d.mkdir();(d/'pins.txt').write_text('\n'.join(parent.read_text().split()[:count])+'\n')
 best=None
 for method,modes in [('conditioned',range(4)),('conditioned_reverse',range(12))]:
  for mode in modes:
   dest=d/f'{method}-{mode}.txt';log=f'{method}-{mode}.log'
   rc=e.invoke([str(ROOT/method),str(REPO/'data/pipes/open'/f'{case}.in'),str(d/'pins.txt'),str(prefix),str(dest),str(mode)],d,log,180)
   if rc:print(case,method,mode,'ERROR',rc,flush=True);continue
   t=int((d/log).read_text());print(case,method,mode,t,flush=True)
   if best is None or t<best[0]:
    best=t,str(dest);e.save(d/'best.json',{'T':t,'plan':str(dest),'parent':str(parent)});(d/'best.txt').write_bytes(dest.read_bytes())
   if case==8 and t==4640:break
  if case==8 and best[0]==4640:break
