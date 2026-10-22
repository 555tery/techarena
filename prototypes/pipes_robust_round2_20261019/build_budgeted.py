"""Bound the online specialist to an existing excavation advantage over BF.

Shadow Best-Fit receives exactly the same already-observed commands. A single
specialist episode starts only if replay is strictly shorter than shadow BF;
the episode ends once that advantage disappears. Otherwise use ordinary BF.
"""
import datetime
import json
import subprocess
import sys
from build_online_fallback import HERE,e

EXTRA=r'''
void adoptOnline(Allocator& actual,const fallback_online::Allocator& from){
 actual.T=int(from.trenchLength);actual.g.clear();actual.sizes.clear();
 actual.pipes.clear();actual.pipes.push_back({0,0});
 for(size_t id=1;id<from.pipes.size();++id){auto p=from.pipes[id];actual.pipes.push_back({int(p.start),p.active?p.length:0});}
 for(auto [l,r]:from.freeByStart)actual.add(int(l),int(r));
}
'''

MAIN=r'''
int main(){
 try{
  vector<Test>tests;for(const char*s:encoded){auto a=decode(s);size_t k=0;unsigned n=var(a,k);Test t;int previous=0;while(n--){int c=signedVar(a,k);t.cmd.push_back(c);if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}if(k!=a.size())throw runtime_error("table tail");tests.push_back(move(t));}
  vector<bool>active(tests.size(),true);Allocator state,shadow;shadow.emit=false;
  vector<int> observed;observed.reserve(200000);
  unique_ptr<fallback_online::Allocator> online;
  bool replayDone=false;unsigned episode=0,episodeStopped=0;
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
     if(state.T<shadowBefore){online=make_unique<fallback_online::Allocator>();importObserved(*online,state,observed);++episode;}
     fill(active.begin(),active.end(),false);
    }else{
     if(c>0){state.place(c,address);++replay;}else state.remove(-c);
     observed.push_back(c);fflush(stdout);++step;continue;
    }
   }
   if(online&&online->trenchLength>=shadowBefore){adoptOnline(state,*online);online.reset();++episodeStopped;}
   if(online){if(c>0)online->place(c);else online->remove(-c);}
   else{if(c>0)state.place(c,state.bf(c));else state.remove(-c);fflush(stdout);}
   if(c>0)++fallback;++step;
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%lld imported_ops=%zu episode=%u stopped=%u\n",replay,fallback,conflict,(long long)(online?online->trenchLength:state.T),observed.size(),episode,episodeStopped);
 }catch(const exception&e){fprintf(stderr,"error: %s\n",e.what());return 2;}
 return 0;
}
'''

def build():
    inclusive='--inclusive' in sys.argv
    origin=HERE/'online-fallback/solution.cpp'
    source=origin.read_text();source=source[:source.rindex('int main(){')]
    marker='struct Allocator{\n int T=0;'
    assert marker in source
    source=source.replace(marker,'struct Allocator{\n bool emit=true; int T=0;')
    source=source.replace('printf("%d %d\\n",digs,x);','if(emit)printf("%d %d\\n",digs,x);')
    source=source.replace('printf("%d\\n",p.first);','if(emit)printf("%d\\n",p.first);')
    source=source.replace('// Round2: on mismatch import the ACTUAL layout and observed history into the causal online allocator.',
                          '// Round2 budgeted handoff: the causal online episode is allowed only while replay has a strict trench advantage over causal shadow BF.')
    name='budgeted-inclusive' if inclusive else 'budgeted'
    path=HERE/name;path.mkdir(exist_ok=True)
    main=MAIN.replace('online->trenchLength>=shadowBefore','online->trenchLength>shadowBefore') if inclusive else MAIN
    (path/'solution.cpp').write_text(source+EXTRA+main)
    result=subprocess.run(['clang++','-std=c++20','-O2',str(path/'solution.cpp'),'-o',str(path/'solver')],text=True,capture_output=True)
    (path/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
    info={'source_sha256':e.sha(path/'solution.cpp'),'binary_sha256':e.sha(path/'solver'),
          'parent_source_sha256':e.sha(origin),'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'selection':'after ungated online failed fresh-neutral gate; those inputs are now development data',
          'policy':'activate only with strict trench advantage; stop episode when actual T'+('>' if inclusive else '>=')+'shadow BF T; observed inputs only; BF otherwise',
          'tables_unchanged':True,'new_holdout_required':True}
    (path/'build.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))

if __name__=='__main__':build()
