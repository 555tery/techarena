import bisect,json
from runtime import ROOT,PARENT,REPO,e
j=json.loads((PARENT/'joint.json').read_text());a=j['cases'][10];b=j['cases'][14];lens=[x for x in a['commands'] if x>0];live={};pid=0;db={}
for t,x in enumerate(b['commands']):
 if x>0:pid+=1;live[pid]=x
 else:live.pop(-x);db[-x]=t
out=ROOT/'components-new';out.mkdir(exist_ok=False);overall=None
for source in [ROOT/'case11/rotation/raw-search-best-h20799.txt']:
 pos=list(map(int,source.read_text().split()));cs=[]
 for l,r in sorted((x,x+n) for x,n in zip(pos,lens)):
  if not cs or l>=cs[-1][1]:cs.append([l,r])
  else:cs[-1][1]=max(cs[-1][1],r)
 starts=[c[0] for c in cs];comp=[bisect.bisect_right(starts,x)-1 for x in pos];first=comp[0];full=[0]*len(cs);pin=[0]*len(cs);last=[0]*len(cs)
 for i,x in enumerate(pos[:4006]):
  k=comp[i];pin[k]+=lens[i]
  if i+1 in live:full[k]+=lens[i]
  else:last[k]=max(last[k],db.get(i+1,0))
 for mode in range(8):
  def key(k):
   w=cs[k][1]-cs[k][0]
   if k==first:return (-10,0,0)
   if mode//2==0:return (-full[k]/w,-full[k],k)
   if mode//2==1:return (-int(full[k]>0),last[k],k)
   if mode//2==2:return (-int(full[k]>0),-last[k],k)
   return (-int(full[k]>0),-int(pin[k]>0),k)
  order=sorted(range(len(cs)),key=key);at=0;newstart={}
  for k in order:newstart[k]=at;at+=cs[k][1]-cs[k][0]
  newpos=[]
  for x,n,k in zip(pos,lens,comp):
   rel=x-cs[k][0]
   if mode%2 and k!=first:rel=cs[k][1]-cs[k][0]-rel-n
   newpos.append(newstart[k]+rel)
  assert newpos[0]==0
  d=out/(source.parent.name+'-'+str(mode));d.mkdir();p11=d/'11.txt';p11.write_text('\n'.join(map(str,newpos))+'\n');pins=d/'pins.txt';pins.write_text('\n'.join(map(str,newpos[:4006]))+'\n');best=None
  for method,modes in [('conditioned',[0]),('conditioned_reverse',[1,2,3,5]),('conditioned_knapsack',[2000,2001,2002,2003])]:
   for m in modes:
    dest=d/f'15-{method}-{m}.txt';log=f'{method}-{m}.log'
    assert e.invoke([str(ROOT/method),str(REPO/'data/pipes/open/15.in'),str(pins),'4999',str(dest),str(m)],d,log,180)==0
    t=int((d/log).read_text())
    if best is None or t<best[0]:best=(t,str(dest))
    if t==418780:break
   if best[0]==418780:break
  t11=20*((max(x+n for x,n in zip(newpos,lens))+19)//20);score=20361/t11+10*418757/best[0]
  result={'source11':str(source),'mode':mode,'components':len(cs),'T11':t11,'T15':best[0],'plan11':str(p11),'plan15':best[1],'score':score};e.save(d/'result.json',result)
  print(source.parent.name,mode,t11,best[0],flush=True)
  if overall is None or score>overall['score']:overall=result;e.save(out/'best.json',overall)
  if t11<=20820 and best[0]==418780:break
 if overall and overall['T11']<=20820 and overall['T15']==418780:break
