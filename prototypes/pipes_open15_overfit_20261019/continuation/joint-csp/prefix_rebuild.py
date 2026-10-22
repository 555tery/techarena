# OPEN15_FULL_OVERFIT: keep grouped live prefix, repack histories and both suffixes.
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from runtime import ROOT,PARENT,REPO,e
out=ROOT/'joint-csp/prefix-rebuild';out.mkdir(exist_ok=False)
j=json.loads((PARENT/'joint.json').read_text());c=j['cases'][10]['commands'];inp=out/'prefix.in';inp.write_text('1\n4999\n'+'\n'.join(map(str,c[:4999]))+'\n0\n')
part=out/'partial.txt';part.write_text('\n'.join((ROOT/'surgery-all-prefix/0/partial.txt').read_text().split()[:4006])+'\n')
pins=out/'pins.txt';rc=e.invoke([str(ROOT/'repair'),str(inp),str(part),str(pins),'20799','0','1'],out,'repair.log',60);print('prefix',rc,(out/'repair.log').read_text(),flush=True)
if rc:raise SystemExit(rc)
for case in [11,15]:
 best=10**9
 for method,modes in [('conditioned',[0,1]),('conditioned_reverse',[0,1,2,3,4,5,6,7]),('conditioned_knapsack',[2000,2001,2002,2003])]:
  for m in modes:
   dest=out/f'{case}-{method}-{m}.txt';log=f'{case}-{method}-{m}.log';rc=e.invoke([str(ROOT/method),str(REPO/f'data/pipes/open/{case}.in'),str(pins),'4999',str(dest),str(m)],out,log,180)
   if rc:continue
   T=int((out/log).read_text());print(case,method,m,T,flush=True)
   if T<best:best=T;e.save(out/f'best-{case}.json',{'T':T,'plan':str(dest),'prefix':str(pins)})
   if T<=(20800 if case==11 else 418780):break
  if best<=(20800 if case==11 else 418780):break
