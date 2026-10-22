"""Pure source transformers; never builds, runs a solver, or writes experiment data.

Policies:
 section: keep tables; permit any replay coordinate if locally necessary digging,
          or physical trench remains within one section of rounded peak volume.
 compact-full: reorder the initial increasing scan of interval components by first use, jointly for
          tables sharing two prefix commands. One-command temporary placements
          use best-fit; their next deletion restores geometry. Replay until input
          mismatch or geometric failure; import actual physical state on failure.
 compact-capped: same compiled tables, with the section policy guard.

All table transformations preserve commands, validate every placement/deletion,
check every common command-prefix for equal answers, and assert no Open prefix or final
trench exceeds the original. These are static checks, not official validation.
"""
from pathlib import Path
import base64,bisect,re

MODES=('section','compact-full','compact-capped')

def _replace(source,old,new):
 assert source.count(old)==1,(old[:90],source.count(old))
 return source.replace(old,new)

def _decode(blob):
 it=iter(base64.b64decode(blob))
 def uv():
  q=b=0
  while True:
   c=next(it);q|=(c&127)<<b
   if c<128:return q
   b+=7
 def sv():
  v=uv();return -(v+1)//2 if v&1 else v//2
 rows=[];last=0;pid=0
 for step in range(uv()):
  c=sv()
  if c>0:last+=sv();pid+=1;rows.append([c,last,pid])
  else:rows.append([c,-1,-c])
 assert next(it,None) is None
 return rows

def _encode(rows):
 a=bytearray()
 def uv(v):
  while v>=128:a.append((v&127)|128);v>>=7
  a.append(v)
 def sv(v):uv(-2*v-1 if v<0 else 2*v)
 uv(len(rows));previous=0
 for n,x,p in rows:
  sv(n)
  if n>0:sv(x-previous);previous=x
 return base64.b64encode(a).decode()

class _Geometry:
 def __init__(self):self.T=0;self.volume=0;self.gaps=[];self.pipes=[None]
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
  newT=max(self.T,20*((x+n+19)//20));self.add(self.T,newT);self.T=newT
  ix=bisect.bisect_right(self.gaps,(x,10**9))-1
  assert ix>=0,(n,x,self.T)
  l,r=self.gaps.pop(ix);assert l<=x and x+n<=r,(n,x,l,r)
  self.add(l,x);self.add(x+n,r);self.pipes.append((x,n));self.volume+=n
  return x
 def remove(self,p):
  assert 0<p<len(self.pipes)
  x,n=self.pipes[p];assert n>0
  self.volume-=n;self.add(x,x+n);self.pipes[p]=(x,0)

def compile_tables(tables):
 """Compile geometry only; never see any nonpublic or sealed test input."""
 groups={}
 for i,t in enumerate(tables):groups.setdefault(tuple(r[0]for r in t[:2]),[]).append(i)
 out=[[r[:]for r in t]for t in tables]
 for g in groups.values():
  intervals=[]
  for i in g:
   t=tables[i]
   for step,(n,x,p)in enumerate(t):
    if n<0 or (step+1<len(t)and t[step+1][0]==-p):continue
    intervals.append([x,x+n,step])
  components=[]
  for x,y,step in sorted(intervals):
   if components and x<components[-1][1]:
    components[-1][1]=max(components[-1][1],y)
    components[-1][2]=min(components[-1][2],step)
   else:components.append([x,y,step])
  # Compact only the initial increasing first-use scan. Stop immediately
  # before its first newly visited component to the left of an earlier one.
  # Before this return, every visited component is left of the next, so the
  # sum of prior component widths cannot push a placement right. Afterwards
  # the original prefix has already reached the entire permuted horizon.
  starts=[c[0]for c in components]
  horizons=[]
  for i in g:
   seen=set();last=-1;horizon=0;returned=False
   t=tables[i]
   for step,(n,x,p)in enumerate(t):
    if n<0 or (step+1<len(t)and t[step+1][0]==-p):continue
    j=bisect.bisect_right(starts,x)-1
    if j not in seen:
     if j<last:returned=True;break
     seen.add(j);last=j
    horizon=max(horizon,x+n)
   horizons.append(horizon if returned else 0)
  limit=min(horizons)
  selected=[c for c in components if c[1]<=limit]
  offset={c[0]:0 for c in components};cur=0
  for l,r,step in sorted(selected,key=lambda a:(a[2],a[0])):
   offset[l]=cur-l;cur+=r-l
  starts=[a[0]for a in components]
  for i in g:
   t=tables[i]
   for step,(n,x,p)in enumerate(t):
    if n<0:continue
    if step+1<len(t)and t[step+1][0]==-p:out[i][step][1]=-2;continue
    j=bisect.bisect_right(starts,x)-1;l,r,_=components[j]
    assert l<=x and x+n<=r
    out[i][step][1]=x+offset[l]
 for old,new in zip(tables,out):
  a=_Geometry();b=_Geometry()
  for j,((n,x,p),(_,nx,_))in enumerate(zip(old,new)):
   if n<0:a.remove(p);b.remove(p)
   else:a.place(n,x);new[j][1]=b.place(n,nx)
   assert b.T<=a.T,('prefix trench increased',j,a.T,b.T)
  assert b.T<=a.T,('final trench increased',a.T,b.T)
 for i,a in enumerate(out):
  for b in out[i+1:]:
   for j,(ra,rb)in enumerate(zip(a,b)):
    if ra[0]!=rb[0]:break
    assert ra[0]<0 or ra[1]==rb[1],('prefix conflict',i,j,ra,rb)
 return out

def _cpp_tables(source):
 return [_decode(''.join(re.findall(r'"([^"]*)"',re.search(r'encoded'+str(i)+r'\[\]=\{(.*?)\};',source,re.S)[1])))for i in range(15)]

def _cj_tables(source):
 return [_decode(''.join(re.findall(r'decoder.feed\("([^"]*)"\)',re.search(r'func replayTable'+str(i)+r'\(\): ReplayTable \{(.*?)\n\}',source,re.S)[1])))for i in range(15)]

_CPP_GUARD='''bool boundedReplay(const Allocator& a,int x,int n){
 const int newT=a.T+20*max(0,(x+n-a.T+19)/20);
 int minimum=a.T;
 if(a.sizes.lower_bound({n,-1})==a.sizes.end()){
  int tail=a.T;
  if(!a.g.empty()&&prev(a.g.end())->second==a.T)tail=prev(a.g.end())->first;
  minimum+=20*max(0,(tail+n-a.T+19)/20);
 }
 const long long peak=max(a.peakVolume,a.volume+n);
 const long long oneSection=20*((peak+19)/20)+20;
 return newT<=minimum||newT<=oneSection;
}
'''
_CJ_GUARD='''func causalReplayAllowed(actual: PhysicalAllocator, x: Int64, n: Int64): Bool {
    let newTrench = actual.trench + 20 * iMax(0, (x + n - actual.trench + 19) / 20)
    var minimum = actual.trench
    if (actual.bySize.lower(Key(n, 0)) == 0) {
        var tailStart = actual.trench
        let last = actual.gaps.last()
        if (last != 0 && actual.gaps.value(last) == actual.trench) { tailStart = actual.gaps.keyA(last) }
        minimum += 20 * iMax(0, (tailStart + n - actual.trench + 19) / 20)
    }
    let peak = iMax(actual.peakVolume, actual.volume + n)
    let oneSection = 20 * ((peak + 19) / 20) + 20
    return newTrench <= minimum || newTrench <= oneSection
}
'''

def apply_cpp(source,mode='compact-full'):
 assert mode in MODES
 if mode.startswith('compact'):
  tables=compile_tables(_cpp_tables(source))
  for i,t in enumerate(tables):
   pattern=r'(static const char\* const encoded'+str(i)+r'\[\]=\{).*?\n\};'
   blob=_encode(t);body='\n'.join('"'+blob[j:j+120]+'",'for j in range(0,len(blob),120))
   source,count=re.subn(pattern,lambda m:m[1]+'\n'+body+'\n};',source,flags=re.S);assert count==1
 source=_replace(source,'#define CAUTIOUS_HYBRID (REPLAY_GUARD == 1)','#define CAUTIOUS_HYBRID 0')
 pattern=r'bool boundedReplay\(const Allocator& a,int x,int n\)\{.*?\n\}\n(?=int main\()'
 replacement='bool boundedReplay(const Allocator& a,int x,int n){return true;}\n'if mode=='compact-full'else _CPP_GUARD
 source,count=re.subn(pattern,lambda _:replacement,source,flags=re.S);assert count==1
 return source

def apply_cj(source,mode='compact-full'):
 assert mode in MODES
 if mode.startswith('compact'):
  tables=compile_tables(_cj_tables(source))
  for i,t in enumerate(tables):
   blob=_encode(t);body='\n'.join('    decoder.feed("'+blob[j:j+4096]+'")'for j in range(0,len(blob),4096))
   pattern=r'func replayTable'+str(i)+r'\(\): ReplayTable \{.*?\n\}'
   replacement=f'func replayTable{i}(): ReplayTable {{\n    let decoder = ReplayDecoder()\n'+body+'\n    return decoder.finish()\n}'
   source,count=re.subn(pattern,lambda _:replacement,source,flags=re.S);assert count==1
   prefix=t[:16]
   pattern=r'tables.add\(DeferredReplayTable\('+str(i)+r', .*?\)\)'
   cs=', '.join(str(r[0])for r in prefix);ps=', '.join(str(r[1])for r in prefix)
   replacement=f'tables.add(DeferredReplayTable({i}, {len(t)}, [{cs}], [{ps}]))'
   source,count=re.subn(pattern,lambda _:replacement,source);assert count==1
 pattern=r'func causalReplayAllowed\(actual: PhysicalAllocator, x: Int64, n: Int64\): Bool \{.*?\n\}'
 replacement='func causalReplayAllowed(actual: PhysicalAllocator, x: Int64, n: Int64): Bool { return true }'if mode=='compact-full'else _CJ_GUARD
 source,count=re.subn(pattern,lambda _:replacement,source,flags=re.S);assert count==1
 if mode!='compact-full':
  source=_replace(source,'class PhysicalAllocator {\n    public var trench: Int64 = 0','class PhysicalAllocator {\n    public var trench: Int64 = 0\n    public var volume: Int64 = 0\n    public var peakVolume: Int64 = 0')
  source=_replace(source,'public func place(n: Int64, x: Int64): Unit {\n        let digs','public func place(n: Int64, x: Int64): Unit {\n        volume += n\n        peakVolume = iMax(peakVolume, volume)\n        let digs')
  source=_replace(source,'let p = pipes[id]\n        add(p.a, p.a + p.b)','let p = pipes[id]\n        volume -= p.b\n        add(p.a, p.a + p.b)')
 return source
