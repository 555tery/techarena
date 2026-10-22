"""Transactional online proposals, compared with BF on the same actual state."""
import datetime
import importlib.util
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/'prototypes/pipes_robust_round2_20261019'
spec=importlib.util.spec_from_file_location('round2build',PRIOR/'build_online_fallback.py')
r2=importlib.util.module_from_spec(spec);spec.loader.exec_module(r2)
e=r2.e

MAIN=r'''
int main(){
 try{
  vector<Test>tests;for(const char*s:encoded){auto a=decode(s);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}if(k!=a.size())throw runtime_error("table tail");tests.push_back(move(t));}
  vector<bool>active(tests.size(),true);Allocator state,shadow;shadow.emit=false;
  vector<int>observed;observed.reserve(200000);
  unique_ptr<fallback_online::Allocator>online;
  bool replayDone=false;unsigned episode=0,stopped=0,proposals=0,rejected=0;
  int c;size_t step=0;unsigned replay=0,fallback=0,conflict=0;
  while(scanf("%d",&c)==1&&c!=0){
   const int shadowBefore=shadow.T;
   if(c>0)shadow.place(c,shadow.bf(c));else shadow.remove(-c);
   if(!replayDone){
    int address=-1;bool agrees=true,matched=false;
    for(size_t i=0;i<tests.size();++i)if(active[i]){
     if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
     matched=true;if(c>0){int p=tests[i].pos[step];if(address>=0&&address!=p)agrees=false;address=p;}
    }
    if(!matched||!agrees||(c>0&&!state.fits(address,c))){
     if(matched)++conflict;replayDone=true;
     const size_t live=count_if(state.pipes.begin()+1,state.pipes.end(),[](auto p){return p.second>0;});
     if(state.T<shadowBefore&&live<=fallback_online::kMcMaxActivePipes){
      online=make_unique<fallback_online::Allocator>();importObserved(*online,state,observed);online->emit=false;++episode;
     }
     fill(active.begin(),active.end(),false);
    }else{
     if(c>0){state.place(c,address);++replay;}else state.remove(-c);
     observed.push_back(c);fflush(stdout);++step;continue;
    }
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
   if(!answered){if(c>0)state.place(c,state.bf(c));else state.remove(-c);}
   fflush(stdout);if(c>0)++fallback;++step;
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%lld imported_ops=%zu episode=%u stopped=%u proposals=%u rejected_extra_dig=%u\n",replay,fallback,conflict,(long long)(online?online->trenchLength:state.T),observed.size(),episode,stopped,proposals,rejected);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
'''

def main():
    parent=PRIOR/'final/solution.cpp'
    assert e.sha(parent)=='3a0164597619fcccc52e2f5fc60f9c391853eb3e36f8dd7e39185a98c3539a00'
    source=parent.read_text();source=source[:source.rindex('int main(){')]
    source=source.replace('class Allocator {\npublic:', 'class Allocator {\npublic:\n    bool emit=true; std::int64_t lastDigs=0,lastStart=0;',1)
    old='static void printPlacement(std::int64_t digs, std::int64_t start) {\n        std::cout << digs << \' \' << start << \'\\n\' << std::flush;\n    }'
    new='void printPlacement(std::int64_t digs, std::int64_t start) {\n        lastDigs=digs;lastStart=start;\n        if(emit)std::cout << digs << \' \' << start << \'\\n\' << std::flush;\n    }'
    assert source.count(old)==1
    source=source.replace(old,new)
    old="std::cout << pipe.start << '\\n' << std::flush;"
    assert source.count(old)==1
    source=source.replace(old,"if(emit)std::cout << pipe.start << '\\n' << std::flush;")
    dest=HERE/'proposal';dest.mkdir(parents=True,exist_ok=True)
    (dest/'solution.cpp').write_text(source+MAIN)
    result=subprocess.run(['clang++','-std=c++20','-O2',str(dest/'solution.cpp'),'-o',str(dest/'solver')],capture_output=True,text=True)
    (dest/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
    metadata={'source_sha256':e.sha(dest/'solution.cpp'),'binary_sha256':e.sha(dest/'solver'),
              'parent_source_sha256':e.sha(parent),'tables_unchanged':True,
              'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'proposal_budget':'existing kMcDecisionBudget=32','live_state_cap':'existing kMcMaxActivePipes=4096',
              'local_guarantee':'accept online proposal only if its immediate digs <= physical-state BF immediate digs',
              'not_guaranteed':'final trench dominance; placements can still change later fragmentation',
              'selection':'one runtime candidate, before round3 attack/holdout scores'}
    (dest/'build.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
