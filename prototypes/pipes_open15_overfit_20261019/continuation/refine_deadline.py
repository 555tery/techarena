from runtime import ROOT,REPO,e
out=ROOT/'deadline-refined';out.mkdir(exist_ok=False)
for name,src in [('components2-0',ROOT/'components/2-0/pins.txt'),('components2-1',ROOT/'components/2-1/pins.txt'),('base',ROOT/'refined/15/pins.txt')]:
 d=out/name;d.mkdir();best=None
 for mode in range(2000,2008):
  dest=d/f'{mode}.txt';log=f'{mode}.log'
  assert e.invoke([str(ROOT/'conditioned_deadline'),str(REPO/'data/pipes/open/15.in'),str(src),'4999',str(dest),str(mode)],d,log,180)==0
  t=int((d/log).read_text());print(name,mode,t,flush=True)
  if best is None or t<best[0]:best=(t,str(dest));e.save(d/'best.json',{'T':t,'plan':str(dest),'pins':str(src)})
  if t==418780:break
 if best[0]==418780:break
