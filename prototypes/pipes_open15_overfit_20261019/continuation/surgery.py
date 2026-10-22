import json,bisect
from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());a=j['cases'][10];b=j['cases'][14]
def lifetimes(c):
 lens=[];born=[];dead=[]
 for t,x in enumerate(c['commands']):
  if x>0:lens.append(x);born.append(t);dead.append(len(c['commands']))
  else:dead[-x-1]=t
 return lens,born,dead
lens,born,dead=lifetimes(a);_,_,db=lifetimes(b)
source=ROOT/'case11/rotation/raw-search-best-h20799.txt';pos=list(map(int,source.read_text().split()));H=max(x+l for x,l in zip(pos,lens));cut=pos[0];assert all(not(x<cut<x+l) for x,l in zip(pos,lens));pos=[x-cut if x>=cut else x+H-cut for x in pos]
chosen=[i for i in range(4006) if dead[i]==len(a['commands']) and db[i]<len(b['commands'])];cuts=sorted({0,H}|{v for i in chosen for v in (pos[i],pos[i]+lens[i])});segs=list(zip(cuts,cuts[1:]));chosen_by_start={pos[i]:i for i in chosen};rest=[k for k,(l,r) in enumerate(segs) if l not in chosen_by_start];selected=[k for k,(l,r) in enumerate(segs) if l in chosen_by_start]
out=ROOT/'surgery';out.mkdir(exist_ok=False)
for ordermode in range(3):
 order=rest+sorted(selected,key=lambda k:(db[chosen_by_start[segs[k][0]]] if ordermode==0 else -db[chosen_by_start[segs[k][0]]] if ordermode==1 else segs[k][0]));starts={};cursor=0
 for k in order:starts[k]=cursor;cursor+=segs[k][1]-segs[k][0]
 plan=[];removed=[]
 for i,(x,l) in enumerate(zip(pos,lens)):
  k=bisect.bisect_right(cuts,x)-1
  if x+l>segs[k][1]:plan.append(-1);removed.append(i);assert dead[i]<4999
  else:plan.append(starts[k]+x-segs[k][0])
 d=out/str(ordermode);d.mkdir();partial=d/'partial.txt';partial.write_text('\n'.join(map(str,plan))+'\n');print('mode',ordermode,'strips',len(chosen),'repair',len(removed),flush=True);best=None
 for rm in range(8):
  dest11=d/f'11-{rm}.txt';log=f'repair-{rm}.log';rc=e.invoke([str(ROOT/'repair'),str(REPO/'data/pipes/open/11.in'),str(partial),str(dest11),str(H),str(rm),'1'],d,log,180)
  if rc:continue
  pins=d/f'pins-{rm}.txt';pins.write_text('\n'.join(dest11.read_text().split()[:4006])+'\n')
  for method,modes in [('conditioned',[0]),('conditioned_reverse',[2,3]),('conditioned_knapsack',[2002,2003])]:
   for m in modes:
    dest=d/f'15-r{rm}-{method}-{m}.txt';log=f'15-r{rm}-{method}-{m}.log'
    assert e.invoke([str(ROOT/method),str(REPO/'data/pipes/open/15.in'),str(pins),'4999',str(dest),str(m)],d,log,180)==0
    t=int((d/log).read_text());print(ordermode,rm,method,m,t,flush=True)
    if best is None or t<best['T15']:
     best={'T11':20*((H+19)//20),'T15':t,'plan11':str(dest11),'plan15':str(dest),'source11':str(source),'surgery_pipes':len(removed),'strips':len(chosen)};e.save(d/'best.json',best)
    if t==418780:break
   if best and best['T15']==418780:break
  if best and best['T15']==418780:break
 if best and best['T15']==418780:break
