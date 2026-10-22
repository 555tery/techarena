import json
from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());c=j['cases'][10];lens=[];live={};volume=0;peak=0;cut=0
for t,x in enumerate(c['commands']):
 if x>0:lens.append(x);live[len(lens)]=x;volume+=x
 else:volume-=live.pop(-x)
 if volume>peak:peak=volume;cut=t
out=ROOT/'peak-repair';out.mkdir(exist_ok=False)
for label,source in [('random',ROOT/'case11/rotation/raw-search-best-h20799.txt'),('mode2',PARENT/'future/2/11.txt'),('mode1',PARENT/'future/1/11.txt')]:
 pos=list(map(int,source.read_text().split()));live={};pid=0
 for x in c['commands'][:cut+1]:
  if x>0:pid+=1;live[pid]=(pos[pid-1],x)
  else:live.pop(-x)
 holes=[];end=0
 for x,n in sorted(live.values()):
  if x>end:holes.append((end,x))
  end=x+n
 high=max(x+n for x,n in zip(pos,lens))
 if end<high:holes.append((end,high))
 plan=[]
 for x,n in zip(pos,lens):
  if any(x<b and a<x+n for a,b in holes):plan.append(-1)
  else:plan.append(x-sum(b-a for a,b in holes if b<=x))
 d=out/label;d.mkdir();partial=d/'partial.txt';partial.write_text('\n'.join(map(str,plan))+'\n');print(label,'removed',plan.count(-1),'holes',holes,flush=True)
 for mode in range(8):
  dest=d/f'{mode}.txt';rc=e.invoke([str(ROOT/'repair'),str(REPO/'data/pipes/open/11.in'),str(partial),str(dest),'20760',str(mode),'0'],d,f'{mode}.log',120)
  print(label,mode,rc,(d/f'{mode}.log').read_text().strip(),flush=True)
  if rc==0:e.save(out/'success.json',{'source':str(source),'plan':str(dest),'mode':mode,'holes':holes,'removed':plan.count(-1)});raise SystemExit(0)
