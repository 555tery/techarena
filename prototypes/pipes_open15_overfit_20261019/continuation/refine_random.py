import json
from runtime import ROOT,REPO,e
out=ROOT/'random-refined';out.mkdir(exist_ok=False)
for case,bound,limit in [(8,4640,132),(15,418780,76)]:
 d=out/str(case);d.mkdir();src=ROOT/'refined'/str(case);best=json.loads((src/'best.json').read_text())['T']
 for mode in range(12,limit):
  dest=d/'trial.txt';log='trial.log'
  rc=e.invoke([str(ROOT/'conditioned_reverse'),str(REPO/'data/pipes/open'/f'{case}.in'),str(src/'pins.txt'),'388' if case==8 else '4999',str(dest),str(mode)],d,log,180)
  if rc:raise RuntimeError((case,mode,rc))
  t=int((d/log).read_text())
  with (d/'trials.jsonl').open('a') as f:f.write(json.dumps({'mode':mode,'T':t})+'\n')
  if t<best:
   best=t;(d/'best.txt').write_bytes(dest.read_bytes());e.save(d/'best.json',{'T':t,'mode':mode});print(case,mode,t,flush=True)
  if t==bound:break
 print(case,'finished',best,flush=True)
