"""Standalone causal projection candidates; selection uses known inputs only."""
import argparse,datetime,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('coupled_build',ROOT/'prototypes/pipes_ghost_handoff_20261020/build_coupled.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
SUPPORT=r'''
static int projectAddress(int x,int n,int marker,bool early){
 if(!early)return x;
 if(x+n<=marker)return x;
 if(x>=marker&&x+n<=229)return x+2;
 if(x>=229&&x+n<=231)return x-(229-marker);
 if(x>=231)return x;return -1;
}
static int projectedT(int T,int x,int n){return max(T,20*((x+n+19)/20));}
static int preSync(Allocator&a,int n,int ref,int referenceT,int marker,int policy,bool early,unsigned&mapped,unsigned&missed){
 int q=projectAddress(ref,n,marker,early),bx=a.bf(n);
 if(q>=0&&a.fits(q,n)&&projectedT(a.T,q,n)<=referenceT&&(policy<13||projectedT(a.T,q,n)<=projectedT(a.T,bx,n))){++mapped;return q;}
 ++missed;
 if(policy==11&&a.fits(ref,n)&&projectedT(a.T,ref,n)<=referenceT)return ref;
 if((policy==12||policy==14)&&a.fits(ref,n)&&projectedT(a.T,ref,n)<=projectedT(a.T,bx,n))return ref;
 return bx;
}
'''
def main():
    ap=argparse.ArgumentParser();ap.add_argument('marker',type=int);ap.add_argument('policy',type=int,choices=[10,11,12,13,14,15,16,17]);ap.add_argument('--name');a=ap.parse_args()
    assert 3<=a.marker<=229 and sha(g.PARENT)=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'
    source=g.PARENT.read_text();tables=g.e.decode(g.PARENT);j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text());audit=[]
    for ci,case in enumerate(j['cases']):
        commands,positions=tables[ci]
        for s,(c,b) in enumerate(zip(commands,case['block_ids'])):
            if c>0 and b==21532:positions[s]=a.marker
        cells=bytearray(case['lower_T']);live={};pid=T=F=peak=0
        for c,x in zip(commands,positions):
            if c>0:
                assert 0<=x and x+c<=len(cells) and not any(cells[x:x+c]);cells[x:x+c]=b'\1'*c
                pid+=1;live[pid]=(x,c);F+=c;peak=max(peak,F);T=max(T,20*((x+c+19)//20))
            else:
                px,L=live.pop(-c);assert all(cells[px:px+L]);cells[px:px+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        audit.append({'case':ci+1,'T':T,'F':F})
    for i in range(15):
        for k in range(i):
            for ca,cb,x,y in zip(tables[i][0],tables[k][0],tables[i][1],tables[k][1]):
                if ca!=cb:break
                assert x==y
    lo=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');hi=source.index('};',lo)
    parent_blob=source[lo:hi];source=source[:lo]+'\n'+g.e.encode(tables)+source[hi:]
    pos=source.index('struct Test{');source=source[:pos]+'static const char* parentEncoded[]={'+parent_blob+'};\n'+source[pos:]
    core=g.CORE
    old='Allocator actual;size_t differing=0;bool coupled=false;'
    new='''Allocator actual;size_t differing=0;bool coupled=false;
  vector<int>prefix,lengths(1),referenceX(1);prefix.reserve(3);lengths.reserve(200001);referenceX.reserve(200001);
  map<int,int>coverage;unsigned mapped=0,missed=0,geometryFollowed=0;
  map<int,int>mirrors,tailMirrors;bool mirrorReady=false;unsigned mirrorFollowed=0;
  auto changeCount=[](map<int,int>&m,int k,int d){int v=(m[k]+=d);if(!v)m.erase(k);};
  auto bump=[&](int x,int d){int v=(coverage[x]+=d);if(!v)coverage.erase(x);};'''
    assert old in core;core=core.replace(old,new)
    core=core.replace('   parent.apply(c);','   if(prefix.size()<3)prefix.push_back(c);\n   parent.apply(c);')
    if a.policy>=15:
        core=core.replace('   parent.apply(c);','''   parent.apply(c);
   if(!parent.replayed&&!coupled&&differing&&!mirrorReady){
    mirrorReady=true;
    for(size_t id=1;id<actual.pipes.size();++id)if(actual.pipes[id].second){
     int key=actual.pipes[id].first+referenceX[id]+actual.pipes[id].second;
     changeCount(mirrors,key,1);if(id!=1)changeCount(tailMirrors,key,1);
    }
   }''')
    old='const int x=coupled?parent.lastX:actual.bf(c);'
    new=f'''const bool geometry=coverage.empty()&&actual.T<=parent.trench();
     const bool early=prefix.size()==3&&prefix[0]==3&&prefix[1]==2&&prefix[2]!=-2;
     const int x=coupled||geometry?parent.lastX:preSync(actual,c,parent.lastX,parent.trench(),{a.marker},{a.policy},early,mapped,missed);
     if(!coupled&&geometry)++geometryFollowed;'''
    assert old in core;core=core.replace(old,new)
    if a.policy>=15:
        old=f'const int x=coupled||geometry?parent.lastX:preSync(actual,c,parent.lastX,parent.trench(),{a.marker},{a.policy},early,mapped,missed);'
        fallback=f'preSync(actual,c,parent.lastX,parent.trench(),{a.marker},10,early,mapped,missed)' if a.policy==16 else 'actual.bf(c)'
        new=f'''const int x=[&](){{
      if(coupled||geometry)return parent.lastX;
      int C=-1;
      if(mirrors.size()==1)C=mirrors.begin()->first;
      else if({a.policy}!=17&&actual.pipes.size()>1&&actual.pipes[1].second&&tailMirrors.size()==1)C=tailMirrors.begin()->first;
      if(C>=0){{int q=C-parent.lastX-c;if(q>=0&&actual.fits(q,c)&&projectedT(actual.T,q,c)<=parent.trench()){{++mirrorFollowed;return q;}}}}
      return {fallback};
     }}();'''
        assert old in core;core=core.replace(old,new)
    old='   fflush(stdout);'
    new='''   // Signed endpoint coverage difference compares occupied unions exactly.
   // Equal unions permit this allocation; PID equality is needed for sticky coupling.
   int x,L,sign;
   if(c>0){lengths.push_back(c);referenceX.push_back(parent.lastX);x=actual.pipes.back().first;L=c;sign=1;}
   else{x=actual.pipes.at(size_t(-c)).first;L=lengths.at(size_t(-c));sign=-1;}
   if(x!=parent.lastX){bump(x,sign);bump(x+L,-sign);bump(parent.lastX,-sign);bump(parent.lastX+L,sign);}
   if(mirrorReady){
    if(coupled){mirrors.clear();tailMirrors.clear();mirrorReady=false;}
    else{int id=c>0?int(actual.pipes.size())-1:-c,key=x+parent.lastX+L;changeCount(mirrors,key,sign);if(id!=1)changeCount(tailMirrors,key,sign);}
   }
   if(coupled&&!coverage.empty())throw runtime_error("coupling coverage");
   fflush(stdout);'''
    assert old in core;core=core.replace(old,new)
    core=core.replace('  parent.report();','''  parent.report();
  fprintf(stderr,"PRE_SYNC mapped=%u missed=%u geometry_followed=%u mirror_followed=%u coverage_endpoints=%zu\\n",mapped,missed,geometryFollowed,mirrorFollowed,coverage.size());''')
    source=source[:source.rindex('int main(){')]+SUPPORT+core
    name=a.name or f'mapped-{a.marker}-{a.policy}';out=HERE/name;out.mkdir(exist_ok=False);(out/'solution.cpp').write_text(source)
    cmd=['clang++','-std=c++20','-O2',str(out/'solution.cpp'),'-o',str(out/'solver')]
    r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(g.PARENT),
      'profile':name,'marker':a.marker,'policy':a.policy,'build_command':cmd,'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'audits':audit,'shared_prefix_consistent':True,'target_hardware_run':False,
      'certificate':'Sticky PID coupling preserves T<=internal parent after coupling. Equal occupied unions permit only the current reference allocation. Accepted projected actions individually satisfy actual new T<=internal parent T.',
      'limitation':'Fallback after a projection miss has no universal no-loss guarantee. Extra CPU affects the budgeted internal parent.'}
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(name,meta['source_sha256'],flush=True)
if __name__=='__main__':main()
