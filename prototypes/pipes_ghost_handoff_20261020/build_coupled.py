"""Exact virtual parent execution plus a physical-identity coupling certificate.

The selected live geometry is always real. Only the already observed public
prefix is repaired. Once live PID coordinates agree, following every virtual
parent address preserves real T<=virtual T by induction for arbitrary suffixes.
This is relative to the internally executed CPU-budgeted parent, not a claim
of bit-identical timing to a separately launched executable.
"""
import argparse,datetime,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
spec=importlib.util.spec_from_file_location('pb',ROOT/'prototypes/pipes_prefix_replan_20261020/build.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

CORE=r'''
struct ParentCore {
 vector<Test> tests;vector<bool>active;Allocator state,shadow;
 vector<int> observed;robust_search::Planner planner;
 unique_ptr<fallback_online::Allocator>online;
 bool replayDone=false,replayed=false;size_t step=0;int selected=-1,lastX=-1;
 unsigned replay=0,fallback=0,conflict=0,episode=0,stopped=0,proposals=0,rejected=0;
 ParentCore(vector<Test> t):tests(move(t)),active(tests.size(),true){state.emit=false;shadow.emit=false;observed.reserve(200000);}
 int trench()const{return online?int(online->trenchLength):state.T;}
 void apply(int c){
  replayed=false;selected=-1;const int shadowBefore=shadow.T;
  if(c>0)shadow.place(c,shadow.bf(c));else shadow.remove(-c);
  if(!replayDone){
   int address=-1;bool agrees=true,matched=false;
   for(size_t i=0;i<tests.size();++i)if(active[i]){
    if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
    matched=true;selected=int(i);
    if(c>0){int p=tests[i].pos[step];if(address>=0&&address!=p)agrees=false;address=p;}
   }
   if(!matched||!agrees||(c>0&&!state.fits(address,c))){
    if(matched)++conflict;replayDone=true;
    const size_t live=count_if(state.pipes.begin()+1,state.pipes.end(),[](auto p){return p.second>0;});
    if(state.T<shadowBefore&&live<=fallback_online::kMcMaxActivePipes){
     online=make_unique<fallback_online::Allocator>();importObserved(*online,state,observed);online->emit=false;++episode;
    }
    fill(active.begin(),active.end(),false);
   }else{
    replayed=true;
    if(c>0){lastX=address;state.place(c,address);++replay;}
    else{lastX=state.pipes.at(size_t(-c)).first;state.remove(-c);}
    observed.push_back(c);planner.observe(c,state.g.size());++step;return;
   }
  }
  if(online&&(online->trenchLength>shadowBefore||online->activePipeCount>fallback_online::kMcMaxActivePipes||proposals>=fallback_online::kMcDecisionBudget)){
   adoptOnline(state,*online);online.reset();++stopped;
  }
  bool answered=false;
  if(online){
   if(c>0){
    adoptOnline(state,*online);const int bx=state.bf(c),bfDigs=max(0,(bx+c-state.T+19)/20);
    auto trial=make_unique<fallback_online::Allocator>(*online);trial->emit=false;trial->place(c);++proposals;
    if(trial->lastDigs<=bfDigs){lastX=int(trial->lastStart);online=move(trial);answered=true;}
    else{online.reset();++rejected;++stopped;}
   }else{lastX=int(online->pipes.at(size_t(-c)).start);online->remove(-c);answered=true;}
  }
  if(!answered){
   if(c>0){lastX=planner.choose(state,c,state.bf(c));state.place(c,lastX);}
   else{lastX=state.pipes.at(size_t(-c)).first;state.remove(-c);}
  }
  planner.observe(c,online?0:state.g.size());if(c>0)++fallback;++step;
 }
 void report(){
  planner.report();planner.reportMemo();planner.reportValidation();
  fprintf(stderr,"PARENT_CORE replay=%u fallback=%u table_conflict=%u T=%d imported_ops=%zu episode=%u stopped=%u proposals=%u rejected_extra_dig=%u\n",replay,fallback,conflict,trench(),observed.size(),episode,stopped,proposals,rejected);
 }
};

int main(){
 try{
  auto unpack=[](const char* const* data,size_t count){
   vector<Test> result;for(size_t idx=0;idx<count;++idx){
    auto a=decode(data[idx]);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;
    while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}
    if(k!=a.size())throw runtime_error("table tail");result.push_back(move(t));
   }return result;
  };
  auto physicalTables=unpack(encoded,sizeof(encoded)/sizeof(*encoded));
  ParentCore parent(unpack(parentEncoded,sizeof(parentEncoded)/sizeof(*parentEncoded)));
  Allocator actual;size_t differing=0;bool coupled=false;
  unsigned certificates=0,followed=0,uncoupled=0,replay=0,fallback=0;
  int c;
  while(scanf("%d",&c)==1&&c!=0){
   parent.apply(c);
   if(parent.replayed){
    coupled=false;
    if(c>0){
     int x=physicalTables.at(size_t(parent.selected)).pos.at(parent.step-1);
     if(!actual.fits(x,c))throw runtime_error("physical replay conflict");
     actual.place(c,x);if(x!=parent.lastX)++differing;++replay;
    }else{
     if(actual.pipes.at(size_t(-c)).first!=parent.lastX){if(!differing)throw runtime_error("prefix count");--differing;}
     actual.remove(-c);
    }
   }else{
    // Parent just processed c; live-count equality is unchanged by this new
    // allocation iff actual follows lastX. Deletion compares pre-event starts.
    if(!differing&&actual.T<=parent.trench()){
     // Before an allocation the reference may have just grown; its address is
     // still legal in actual because all old live intervals agree.
     if(!coupled){coupled=true;++certificates;}
    }
    if(c>0){
     const int x=coupled?parent.lastX:actual.bf(c);
     if(coupled&&!actual.fits(x,c))throw runtime_error("coupling fit");
     actual.place(c,x);if(x!=parent.lastX)++differing;
    }else{
     if(actual.pipes.at(size_t(-c)).first!=parent.lastX){if(!differing)throw runtime_error("fallback count");--differing;}
     actual.remove(-c);
    }
    if(coupled){++followed;if(differing||actual.T>parent.trench())throw runtime_error("coupling invariant");}
    else{++uncoupled;if(!differing&&actual.T<=parent.trench()){coupled=true;++certificates;}}
    if(c>0)++fallback;
   }
   fflush(stdout);
  }
  parent.report();
  fprintf(stderr,"COUPLING certificates=%u followed=%u uncoupled_steps=%u differing=%zu physical_T=%d parent_T=%d\n",certificates,followed,uncoupled,differing,actual.T,parent.trench());
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=0 T=%d imported_ops=%zu\n",replay,fallback,actual.T,parent.observed.size());
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}return 0;
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('name',choices=['coupled-control','coupled-minimal','coupled-buffer40']);a=ap.parse_args()
    assert sha(PARENT)=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'
    source=PARENT.read_text();old=e.decode(PARENT);tables=[(list(c),list(p)) for c,p in old]
    x={'coupled-control':229,'coupled-minimal':3,'coupled-buffer40':38}[a.name]
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text());audits=[]
    for ci,case in enumerate(j['cases']):
        commands,positions=tables[ci]
        for step,(c,bid) in enumerate(zip(commands,case['block_ids'])):
            if c>0 and bid==21532:positions[step]=x
        cells=bytearray(case['lower_T']);active={};pid=T=ot=F=peak=0
        for step,(c,p,op) in enumerate(zip(commands,positions,old[ci][1])):
            if c>0:
                assert 0<=p and p+c<=len(cells) and not any(cells[p:p+c]);cells[p:p+c]=b'\1'*c
                pid+=1;active[pid]=(p,c);F+=c;peak=max(peak,F);T=max(T,20*((p+c+19)//20));ot=max(ot,20*((op+c+19)//20));assert T<=ot
            else:
                px,L=active.pop(-c);assert all(cells[px:px+L]);cells[px:px+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        audits.append({'case':ci+1,'T':T,'F':F,'public_prefix_excavation_never_increased':True})
    for i in range(15):
        for k in range(i):
            for c,d,p,q in zip(tables[i][0],tables[k][0],tables[i][1],tables[k][1]):
                if c!=d:break
                assert p==q
    p=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');q=source.index('};',p)
    blob=source[p:q];source=source[:p]+'\n'+e.encode(tables)+source[q:]
    pos=source.index('struct Test{');source=source[:pos]+'static const char* parentEncoded[]={'+blob+'};\n'+source[pos:]
    source=source[:source.rindex('int main(){')]+CORE
    out=HERE/a.name;out.mkdir(parents=True,exist_ok=False);(out/'solution.cpp').write_text(source)
    cmd=['clang++','-std=c++20','-O2',str(out/'solution.cpp'),'-o',str(out/'solver')]
    r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(PARENT),
          'build_command':cmd,'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile':a.name,
          'changed_blocks':int(x!=229),'public_PID2_position':x,'audits':audits,'target_hardware_run':False,
          'certificate':'after live PID coordinates agree and actualT<=virtualParentT, follow full virtual parent exactly; terminalT dominance vs internally executed reference',
          'limitation':'No such guarantee before coupling. CPU timers may make virtual parent differ from separately executed parent.'}
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(a.name,meta['source_sha256'],flush=True)
if __name__=='__main__':main()
