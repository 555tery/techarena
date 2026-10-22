from pathlib import Path
import base64,bisect,re

def decode_tables(source):
 tables=[]
 for i in range(15):
  z=re.search(r'encoded'+str(i)+r'\[\]=\{(.*?)\};',source,re.S)
  a=base64.b64decode(''.join(re.findall('"([^"]*)"',z[1])));it=iter(a)
  def uv():
   q=b=0
   while True:
    c=next(it);q|=(c&127)<<b
    if c<128:return q
    b+=7
  def sv():
   v=uv();return -(v+1)//2 if v&1 else v//2
  N=uv();rows=[];last=0;pid=0
  for step in range(N):
   c=sv()
   if c>0:last+=sv();pid+=1;rows.append([c,last,pid])
   else:rows.append([c,-1,-c])
  tables.append(rows)
 return tables

def compact(tables):
 # Group tables by two equal positive prefix commands: unlike an arbitrary ID
 # mapping, this groups precisely tables whose prefix answers must agree.
 # Their common plan uses the union of all non-transient pipe intervals.
 groups=[]
 for i,t in enumerate(tables):
  found=None
  for g in groups:
   if [r[0] for r in tables[g[0]][:2]]==[r[0]for r in t[:2]]:found=g;break
  if found is None:groups.append([i])
  else:found.append(i)
 out=[[r[:]for r in t]for t in tables]
 for g in groups:
  intervals=[]
  for i in g:
   t=tables[i]
   for step,(n,x,p)in enumerate(t):
    if n<0 or (step+1<len(t)and t[step+1][0]==-p):continue
    intervals.append([x,x+n,step])
  components=[]
  for x,y,step in sorted(intervals):
   if components and x<components[-1][1]:components[-1][1]=max(components[-1][1],y);components[-1][2]=min(components[-1][2],step)
   else:components.append([x,y,step])
  limit=min(max(x+n for n,x,p in tables[i] if n>0) for i in g)
  selected=[c for c in components if c[1]<=limit]
  offset={c[0]:0 for c in components};cur=0
  for l,r,step in sorted(selected,key=lambda a:(a[2],a[0])):offset[l]=cur-l;cur+=r-l
  starts=[a[0]for a in components]
  for i in g:
   t=tables[i]
   for step,(n,x,p)in enumerate(t):
    if n<0:continue
    if step+1<len(t)and t[step+1][0]==-p:out[i][step][1]=-2;continue
    j=bisect.bisect_right(starts,x)-1;l,r,first=components[j];assert l<=x and x+n<=r
    out[i][step][1]=x+offset[l]
 return out

class Geometry:
 def __init__(self):self.T=0;self.volume=0;self.peak=0;self.gaps=[];self.pipes=[None]
 def add(self,l,r):
  if l>=r:return
  ix=bisect.bisect_left(self.gaps,(l,))
  if ix and self.gaps[ix-1][1]==l:l=self.gaps.pop(ix-1)[0];ix-=1
  if ix<len(self.gaps) and self.gaps[ix][0]==r:r=self.gaps.pop(ix)[1]
  self.gaps.insert(ix,(l,r))
 def bestfit(self,n):
  gs=[(r-l,l)for l,r in self.gaps if r-l>=n]
  if gs:return min(gs)[1]
  return self.gaps[-1][0]if self.gaps and self.gaps[-1][1]==self.T else self.T
 def place(self,n,x):
  if x==-2:x=self.bestfit(n)
  newT=max(self.T,20*((x+n+19)//20));ix=bisect.bisect_right(self.gaps,(x,10**9))-1
  left=self.T;right=newT
  if x<self.T:left,right=self.gaps[ix];assert left<=x and (x+n<=right or right==self.T);right=newT if right==self.T else right
  elif self.gaps and self.gaps[-1][1]==self.T:left=self.gaps[-1][0]
  edge=x==left or x+n==right
  minimum=max(self.T,20*((self.bestfit(n)+n+19)//20))
  self.volume+=n;self.peak=max(self.peak,self.volume)
  volumeT=20*((self.peak+19)//20)
  self.add(self.T,newT);self.T=newT
  ix=bisect.bisect_right(self.gaps,(x,10**9))-1;l,r=self.gaps.pop(ix);assert l<=x and x+n<=r
  self.add(l,x);self.add(x+n,r);self.pipes.append((x,n))
  return x,edge,newT-minimum,newT-volumeT
 def remove(self,p):
  x,n=self.pipes[p];self.volume-=n;self.add(x,x+n);self.pipes[p]=(x,0)

if __name__=='__main__':
 a=decode_tables(Path('/tmp/pipes_guard_generalization.cpp').read_text());b=compact(a)
 for i,(old,new)in enumerate(zip(a,b),1):
  oldg=Geometry();g=Geometry();fails={};maxslack=0;changes=0
  for step,((n,x,p),(_,nx,_))in enumerate(zip(old,new),1):
   if n<0:oldg.remove(p);g.remove(p);continue
   oldg.place(n,x);newx,edge,extra,slack=g.place(n,nx);changes+=x!=newx;maxslack=max(maxslack,slack)
   for mode,ok in [('edge-local',edge and extra<=0),('local',extra<=0),('volume',slack<=0),('one-section',extra<=0 or slack<=20),('max-pipe',extra<=0 or slack<=40)]:
    if not ok and mode not in fails:fails[mode]=(step,n,newx,extra,slack)
  print(i,'oldT',oldg.T,'newT',g.T,'changes',changes,'maxslack',maxslack,'firstfail',fails)
