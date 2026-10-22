from runtime import ROOT,REPO,e
out=ROOT/'knapsack-refined';out.mkdir(exist_ok=False)
for case,bound in [(8,4640),(15,418780)]:
 d=out/str(case);d.mkdir();src=ROOT/'refined'/str(case);best=10**9
 for mode in range(2000,2008):
  dest=d/f'{mode}.txt';log=f'{mode}.log'
  rc=e.invoke([str(ROOT/'conditioned_knapsack'),str(REPO/'data/pipes/open'/f'{case}.in'),str(src/'pins.txt'),'388' if case==8 else '4999',str(dest),str(mode)],d,log,180)
  if rc:raise RuntimeError((case,mode,rc))
  t=int((d/log).read_text());print(case,mode,t,flush=True)
  if t<best:
   best=t;(d/'best.txt').write_bytes(dest.read_bytes());e.save(d/'best.json',{'T':t,'mode':mode})
  if t==bound:break
