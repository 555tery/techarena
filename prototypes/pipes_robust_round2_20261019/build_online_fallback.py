"""Embed the frozen causal online allocator and import the actual replay state.

All statistics come exclusively from commands already read. No moves or
excavation rollback are performed when the exact-prefix table stops matching.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREV=ROOT/'prototypes/pipes_v5_robust_20261019'
spec=importlib.util.spec_from_file_location('prior_experiment',PREV/'experiment.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
ONLINE=ROOT/'research-campaigns/20261018T141843+0700-autonomous/releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'

SEED=r'''
// Import only observed commands and their immutable physical positions.
void importObserved(fallback_online::Allocator& out,const Allocator& actual,
                    const vector<int>& observed){
 int next=0;
 for(int command:observed){
  out.lifetimeModel.advance();
  if(command>0){
   const int id=++next;
   if(out.observedRunLength!=command){
    if(out.observedRunCount){
     out.completedPlacementRuns.emplace_back(out.observedRunLength,out.observedRunCount);
     if(out.completedPlacementRuns.size()>8)out.completedPlacementRuns.pop_front();
    }
    out.observedRunLength=command;out.observedRunCount=0;
    out.activeRunFirstPid=id;out.activeRunDeleteParityCount={};
   }
   ++out.observedRunCount;
   const int cohort=out.lengthOccurrenceCount[command]%2;
   const auto x=actual.pipes[id].first;
   out.pipes.push_back(fallback_online::Pipe{x,command,true,cohort});
   out.activeByEnd.emplace(x+command,id);out.fenwickAdd(id,1);++out.activePipeCount;
   ++out.lengthOccurrenceCount[command];out.recordLength(command);
   out.recordObservation(fallback_online::Observation{1,command});out.recordPrimalEvent(command);
  }else{
   const int id=-command;auto& p=out.pipes[id];
   const int rank=out.rankFromNewestPermille(id);
   out.lifetimeModel.observeDeletion(id);out.activeByEnd.erase(p.start+p.length);
   p.active=false;out.fenwickAdd(id,-1);--out.activePipeCount;
   out.recordDeletionPattern(id,p.length);out.recordPrimalEvent(-1);
   out.recordObservation(fallback_online::Observation{-1,rank});
   ++out.removedLengthCohort[p.length][p.sizeCohort];
   if(id>=out.activeRunFirstPid)++out.activeRunDeleteParityCount[id&1];
  }
 }
 out.trenchLength=actual.T;
 for(auto [left,right]:actual.g)out.addFreeGap(left,right,-1,++out.releaseEpoch);
 // A slab reservation made by a different placement policy cannot be imported.
 out.cohortSlabActive=false;
 if(out.activePipeCount>fallback_online::kMcMaxActivePipes)out.lifoLaneDisabledForScale=true;
 if(out.pipes.size()!=actual.pipes.size())throw runtime_error("import PID count");
 for(size_t id=1;id<actual.pipes.size();++id){
  const auto& p=out.pipes[id];
  if(p.start!=actual.pipes[id].first||p.active!=(actual.pipes[id].second>0))throw runtime_error("import geometry");
 }
 if(out.fenwickPrefix(int(out.pipes.size()-1))!=int(out.activePipeCount))throw runtime_error("import rank index");
}
'''

MAIN=r'''
int main(){
 try{
  vector<Test>tests;for(const char*s:encoded){auto a=decode(s);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}if(k!=a.size())throw runtime_error("table tail");tests.push_back(move(t));}
  vector<bool>active(tests.size(),true);Allocator state;
  vector<int> observed;observed.reserve(200000);
  unique_ptr<fallback_online::Allocator> online;
  int c;size_t step=0;unsigned replay=0,fallback=0,conflict=0;
  while(scanf("%d",&c)==1&&c!=0){
   if(!online){
    int address=-1;bool agrees=true,matched=false;
    for(size_t i=0;i<tests.size();++i)if(active[i]){
     if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
     matched=true;if(c>0){int p=tests[i].pos[step];if(address>=0&&address!=p)agrees=false;address=p;}
    }
    if(!matched||!agrees||(c>0&&!state.fits(address,c))){
     if(matched)++conflict;
     online=make_unique<fallback_online::Allocator>();importObserved(*online,state,observed);
     fill(active.begin(),active.end(),false);
    }else{
     if(c>0){state.place(c,address);++replay;}else state.remove(-c);
     observed.push_back(c);fflush(stdout);++step;continue;
    }
   }
   if(c>0){online->place(c);++fallback;}else online->remove(-c);
   ++step;
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%lld imported_ops=%zu\n",replay,fallback,conflict,(long long)(online?online->trenchLength:state.T),observed.size());
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
'''

def build():
    frozen=PREV/'candidate-v3/solution.cpp'
    assert e.sha(frozen)=='a3d414a4872796fb570753c0e61db5c80dc59c1b8cbd7ec57e95dec345aff53a'
    source=frozen.read_text();source=source[:source.rindex('int main(){')]
    online=ONLINE.read_text();online=online[:online.rindex('int main()')]
    online=online.replace('namespace {','namespace fallback_online {',1)
    a=online.index('class Allocator {')
    online=online[:a]+online[a:].replace('private:', 'public: // Local embedding: access helpers for observed-state import.',1)
    source=source.replace('// Separate experimental branch;', '// Round2: on mismatch import the ACTUAL layout and observed history into the causal online allocator.\n// Separate experimental branch;')
    dest=HERE/'online-fallback';dest.mkdir(parents=True,exist_ok=True)
    (dest/'solution.cpp').write_text('#include <memory>\n'+online+'\n'+source+'\n'+SEED+'\n'+MAIN)
    result=subprocess.run(['clang++','-std=c++20','-O2',str(dest/'solution.cpp'),'-o',str(dest/'solver')],text=True,capture_output=True)
    (dest/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
    metadata={'baseline_source_sha256':e.sha(frozen),'online_source':str(ONLINE.relative_to(ROOT)),
              'online_source_sha256':e.sha(ONLINE),'source_sha256':e.sha(dest/'solution.cpp'),
              'binary_sha256':e.sha(dest/'solver'),'tables_unchanged':True,
              'handoff':'actual positions, trench and PIDs; observed history only; free cohorts conservatively unknown'}
    (dest/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':build()
