"""Public-prefix repairs plus a causal reference-layout handoff.

Only a frozen public table is decoded. Runtime still consumes one command and
flushes one response. Reference continuations use plain BF, never future input.
"""
import argparse,datetime,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRIOR=ROOT/'prototypes/pipes_prefix_replan_20261020'
PARENT=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
spec=importlib.util.spec_from_file_location('prefix_build',PRIOR/'build.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

HELPERS=r'''
// Rebuild a causal reference geometry from immutable, already observed PIDs.
void importReference(Allocator& out,const Allocator& actual,
                     const vector<int>& positions,int trench){
 out.emit=false;out.T=trench;out.pipes=actual.pipes;
 vector<pair<int,int>> live;live.reserve(out.pipes.size());
 for(size_t id=1;id<out.pipes.size();++id){
  out.pipes[id].first=positions.at(id);
  if(out.pipes[id].second>0)live.push_back(out.pipes[id]);
 }
 sort(live.begin(),live.end());int cursor=0;
 for(auto [x,n]:live){if(x<cursor||x+n>trench)throw runtime_error("reference overlap");out.add(cursor,x);cursor=x+n;}
 out.add(cursor,trench);
}
'''

MAIN=r'''
int main(){
 try{
  auto unpack=[](const char* const* data,size_t count){
   vector<Test> result;for(size_t idx=0;idx<count;++idx){
    auto a=decode(data[idx]);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;
    while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}
    if(k!=a.size())throw runtime_error("table tail");result.push_back(move(t));
   }return result;
  };
  auto tests=unpack(encoded,sizeof(encoded)/sizeof(*encoded));
  auto parent=unpack(parentEncoded,sizeof(parentEncoded)/sizeof(*parentEncoded));
  vector<bool>active(tests.size(),true);Allocator state,shadow;shadow.emit=false;
  vector<int>observed;observed.reserve(200000);robust_search::Planner planner;
  vector<int>oldPositions(1,0);oldPositions.reserve(100001);int oldTrench=0;
  unique_ptr<Allocator>reference;size_t differing=0;
  unsigned healed=0,blocked=0,extraRejected=0,shapeRejected=0,synchronized=0,started=0;
  unique_ptr<fallback_online::Allocator>online;
  bool replayDone=false;unsigned episode=0,stopped=0,proposals=0,rejected=0;
  int c;size_t step=0;unsigned replay=0,fallback=0,conflict=0;
  while(scanf("%d",&c)==1&&c!=0){
   const int shadowBefore=shadow.T;
   if(c>0)shadow.place(c,shadow.bf(c));else shadow.remove(-c);
   if(!replayDone){
    int address=-1,oldAddress=-1;bool agrees=true,matched=false;
    for(size_t i=0;i<tests.size();++i)if(active[i]){
     if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
     matched=true;
     if(c>0){
      int p=tests[i].pos[step],q=parent[i].pos[step];
      if(address>=0&&address!=p)agrees=false;
      if(oldAddress>=0&&oldAddress!=q)throw runtime_error("parent prefix conflict");
      address=p;oldAddress=q;
     }
    }
    if(!matched||!agrees||(c>0&&!state.fits(address,c))){
     if(matched)++conflict;replayDone=true;
     if(differing||state.T!=oldTrench){
      reference=make_unique<Allocator>();importReference(*reference,state,oldPositions,oldTrench);++started;
     }else{
      const size_t live=count_if(state.pipes.begin()+1,state.pipes.end(),[](auto p){return p.second>0;});
      if(state.T<shadowBefore&&live<=fallback_online::kMcMaxActivePipes){
       online=make_unique<fallback_online::Allocator>();importObserved(*online,state,observed);online->emit=false;++episode;
      }
     }
     fill(active.begin(),active.end(),false);
    }else{
     if(c>0){
      state.place(c,address);oldPositions.push_back(oldAddress);
      oldTrench=max(oldTrench,20*((oldAddress+c+19)/20));
      if(address!=oldAddress)++differing;++replay;
     }else{
      if(state.pipes.at(size_t(-c)).first!=oldPositions.at(size_t(-c)))--differing;
      state.remove(-c);
     }
     observed.push_back(c);planner.observe(c,state.g.size());fflush(stdout);++step;continue;
    }
   }
   if(reference){
    if(c>0){
     const int gx=reference->bf(c),bx=state.bf(c);int x=bx;
     const int bd=max(0,(bx+c-state.T+19)/20),gd=max(0,(gx+c-state.T+19)/20);
     auto bestGap=state.sizes.lower_bound({c,-1});auto ghostGap=state.g.find(gx);
     const bool sameShape=gx==bx||(bestGap!=state.sizes.end()&&ghostGap!=state.g.end()&&ghostGap->second-ghostGap->first==bestGap->first);
     if(!state.fits(gx,c))++blocked;
     else if(gd>bd)++extraRejected;
     else if(kGhostTieOnly&&!sameShape)++shapeRejected;
     else{x=gx;healed+=gx!=bx;}
     reference->place(c,gx);state.place(c,x);if(x!=gx)++differing;
    }else{
     const size_t id=size_t(-c);
     if(state.pipes.at(id).first!=reference->pipes.at(id).first){if(!differing)throw runtime_error("reference count");--differing;}
     reference->remove(-c);state.remove(-c);
    }
    if(!differing&&state.T==reference->T){reference.reset();++synchronized;}
    planner.observe(c,state.g.size());fflush(stdout);if(c>0)++fallback;++step;continue;
   }
   if(online&&(online->trenchLength>shadowBefore||online->activePipeCount>fallback_online::kMcMaxActivePipes||proposals>=fallback_online::kMcDecisionBudget)){
    adoptOnline(state,*online);online.reset();++stopped;
   }
   bool answered=false;
   if(online){
    if(c>0){
     adoptOnline(state,*online);const int bx=state.bf(c);
     const int bfDigs=max(0,(bx+c-state.T+19)/20);
     auto trial=make_unique<fallback_online::Allocator>(*online);trial->emit=false;trial->place(c);++proposals;
     if(trial->lastDigs<=bfDigs){
      printf("%lld %lld\n",(long long)trial->lastDigs,(long long)trial->lastStart);
      online=move(trial);answered=true;
     }else{online.reset();++rejected;++stopped;}
    }else{
     const auto x=online->pipes.at(size_t(-c)).start;online->remove(-c);
     printf("%lld\n",(long long)x);answered=true;
    }
   }
   if(!answered){if(c>0){int x=planner.choose(state,c,state.bf(c));state.place(c,x);}else state.remove(-c);}planner.observe(c,online?0:state.g.size());
   fflush(stdout);if(c>0)++fallback;++step;
  }
  planner.report();planner.reportMemo();planner.reportValidation();
  fprintf(stderr,"GHOST_HANDOFF started=%u canonical_choices=%u blocked=%u extra_dig_rejected=%u shape_rejected=%u synchronized=%u differing=%zu\n",started,healed,blocked,extraRejected,shapeRejected,synchronized,differing);
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%lld imported_ops=%zu episode=%u stopped=%u proposals=%u rejected_extra_dig=%u\n",replay,fallback,conflict,(long long)(online?online->trenchLength:state.T),observed.size(),episode,stopped,proposals,rejected);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('name',choices=['disabled','minimal','broad11','repair15','temporary9']);ap.add_argument('--ties',action='store_true');a=ap.parse_args()
    assert sha(PARENT)=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'
    source=PARENT.read_text();old=e.decode(PARENT);tables=[(list(c),list(p)) for c,p in old]
    repairs={'disabled':[],'minimal':['early11'],'broad11':['early11','permuted11'],
             'repair15':['early11','local-exchange8','exchange8-p397','instant-only'],
             'temporary9':['instant-only']}[a.name]
    changes={}
    for name in repairs:
        payload=json.loads((PRIOR/'repairs'/name/'changes.json').read_text())
        for bid,x in payload.items():
            bid=int(bid);assert bid not in changes or changes[bid]==x;changes[bid]=x
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text());audits=[]
    for ci,case in enumerate(j['cases']):
        commands,positions=tables[ci]
        for step,(c,bid) in enumerate(zip(commands,case['block_ids'])):
            if c>0 and bid in changes:positions[step]=changes[bid]
        cells=bytearray(case['lower_T']);pipes={};pid=T=oldT=F=peak=0
        for step,(c,x,ox) in enumerate(zip(commands,positions,old[ci][1])):
            if c>0:
                assert 0<=x and x+c<=len(cells) and not any(cells[x:x+c]),(ci,step,x,c)
                cells[x:x+c]=b'\1'*c;pid+=1;pipes[pid]=(x,c);F+=c;peak=max(peak,F)
                T=max(T,20*((x+c+19)//20));oldT=max(oldT,20*((ox+c+19)//20));assert T<=oldT
            else:
                px,L=pipes.pop(-c);assert all(cells[px:px+L]);cells[px:px+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        audits.append({'case':ci+1,'T':T,'F':F,'prefix_excavation_never_increased':True})
    for i in range(15):
        for k in range(i):
            for c,d,x,y in zip(tables[i][0],tables[k][0],tables[i][1],tables[k][1]):
                if c!=d:break
                assert x==y
    p=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');q=source.index('};',p)
    original=source[p:q];source=source[:p]+'\n'+e.encode(tables)+source[q:]
    at=source.index('struct Test{');source=source[:at]+'static const char* parentEncoded[]={'+original+'};\n'+source[at:]
    source=source[:source.rindex('int main(){')]+HELPERS+'\nstatic constexpr bool kGhostTieOnly='+('true' if a.ties else 'false')+';\n'+MAIN
    name=a.name+('-ties' if a.ties else '')
    out=HERE/name;out.mkdir(parents=True,exist_ok=False);(out/'solution.cpp').write_text(source)
    cmd=['clang++','-std=c++20','-O2',str(out/'solution.cpp'),'-o',str(out/'solver')]
    r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(PARENT),
          'build_command':cmd,'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'profile':a.name,'tie_only':a.ties,'changed_blocks':len(changes),'repairs':repairs,'audits':audits,'target_hardware_run':False,
          'runtime':'causal reference plain-BF, only on divergent physical prefix; no extra immediate excavation vs actual BF; unchanged ordinary path otherwise',
          'scope':'finite public-only plan construction; no general final-KPI dominance claim'}
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(name,meta['source_sha256'],flush=True)

if __name__=='__main__':main()
