import json,sys
from pathlib import Path
from runtime import ROOT,PARENT,REPO,e
e.quota()
assert e.invoke(['/usr/bin/clang++','-std=c++17','-O3',str(ROOT/'conditioned.cpp'),'-o',str(ROOT/'conditioned')],ROOT,'compile-conditioned.log',120)==0
j=json.loads((PARENT/'joint.json').read_text());cases={c['case']:c for c in j['cases']}
out=ROOT/'conditioned-plans';out.mkdir(exist_ok=False)
for number in [1,2,3,4,6,7,10,12,14,5,9,11,13,8,15]:
 c=cases[number];d=out/str(number);d.mkdir();prefix=1;pin=[0]
 if number in [5,9]:prefix=125;pin=list(range(125))
 if number==8:prefix=388;pin=list(map(int,(out/'13/best.txt').read_text().split()))[:210]
 if number==15:prefix=4999;pin=list(map(int,(out/'11/best.txt').read_text().split()))[:4006]
 (d/'pins.txt').write_text('\n'.join(map(str,pin))+'\n');best=None
 for mode in range(4):
  dest=d/f'{mode}.txt';log=f'{mode}.log';rc=e.invoke([str(ROOT/'conditioned'),str(REPO/'data/pipes/open'/f'{number}.in'),str(d/'pins.txt'),str(prefix),str(dest),str(mode)],d,log,180)
  if rc:raise RuntimeError((number,mode,rc))
  t=int((d/log).read_text());print(number,mode,t,flush=True)
  if best is None or t<best[0]:best=(t,mode)
 (d/'best.txt').write_bytes((d/f'{best[1]}.txt').read_bytes())
 e.save(d/'best.json',{'T':best[0],'mode':best[1],'prefix':prefix,'lower_T':c['lower_T']})
