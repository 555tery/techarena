from pathlib import Path
import subprocess
r=Path('prototypes/pipes_closed_ready_20261020/candidates-fast')
out=Path('prototypes/pipes_online_core_20261020/diagnostics')
s=(r/'online/solution.cpp').read_text();s=s[:s.index('\nint main() {')]
s=s.replace('using fallback_online::Allocator;','')
s=s.replace('bool emit = true;','bool emit = true; std::int64_t lastDigs=0,lastStart=0;')
s=s.replace('    void printPlacement(std::int64_t digs, std::int64_t start) {','    void printPlacement(std::int64_t digs, std::int64_t start) {\n        lastDigs=digs;lastStart=start;')
h=(r/'hybrid/solution.cpp').read_text();physical=h[h.index('struct Allocator{'):h.index('bool guardedReplay(')]
tail=r'''
#include <fstream>
#include <string>
using Core=fallback_online::Allocator;
void snapshot(const char*tag,const Core& a){
 std::int64_t free=0,largest=0;std::array<int,42>hist{};for(auto [l,r]:a.freeByStart){free+=r-l;largest=std::max(largest,r-l);++hist[std::min<int>(41,int(r-l))];}
 std::cerr<<tag<<" free="<<free<<" largest="<<largest<<" hist=";for(int i=1;i<=41;++i)if(hist[i])std::cerr<<i<<":"<<hist[i]<<";";std::cerr<<" T="<<a.trenchLength<<" active="<<a.activePipeCount<<" gaps="<<a.freeByStart.size()<<" shared="<<a.freeBySizeShared.size()<<" own0="<<a.freeBySizeCohort[0].size()<<" own1="<<a.freeBySizeCohort[1].size()<<" epoch="<<a.releaseEpoch<<" parity="<<a.parityCohortMode<<" alternating="<<a.alternatingDeleteMode<<" smooth="<<a.runLeftDisabledBySmoothTrend<<" slab="<<a.cohortSlabActive<<" run="<<a.observedRunLength<<":"<<a.observedRunCount<<" mc="<<a.mcDecisionsUsed<<":"<<a.mcRolloutsRun<<" primal="<<a.primalScoredDecisions<<":"<<a.primalModelRebuilds<<" model="<<a.primalModelStep<<":"<<a.causalRiskReady<<" relative="<<a.lastCompletedDeleteRelativeParity<<":"<<a.previousCompletedDeleteRelativeParity<<"\n";
}
void geometry(Core&a,const Allocator&p){
 a.freeByStart.clear();a.freeBySize.clear();a.freeBySizeAge.clear();a.gapFreedAt.clear();a.gapCohort.clear();a.freeBySizeCohort[0].clear();a.freeBySizeCohort[1].clear();a.freeBySizeShared.clear();a.primalGapCounts={};a.activeByEnd.clear();
 a.trenchLength=p.T;
 for(size_t id=1;id<a.pipes.size();++id){a.pipes[id].start=p.pipes[id].first;if(a.pipes[id].active)a.activeByEnd.emplace(a.pipes[id].start+a.pipes[id].length,int(id));}
 for(auto [l,r]:p.g)a.addFreeGap(l,r,-1,a.releaseEpoch);
 a.cohortSlabActive=false;a.primalModelDirty=true;
}
int main(int argc,char**argv){
 const int abort=std::stoi(argv[2]);std::ifstream f(argv[1]);double weight;int n;f>>weight>>n;std::vector<int>cmd(n);for(auto&x:cmd)f>>x;
 std::ifstream answers(argv[3]);Allocator hp,op;hp.emit=op.emit=false;Core online;online.emit=false;std::vector<int>observed;
 std::vector<std::unique_ptr<Core>>v;std::vector<std::string>names={"O","OI","Oshared","H","Hkeep","Hcold","Hmc"};
 int firstprefix=0;bool equal=false;
 for(int step=1;step<=n;++step){int c=cmd[step-1];
  if(step==abort){
   equal=hp.T==op.T&&hp.pipes==op.pipes;
   std::cerr<<"HANDOFF step="<<step<<" equal="<<equal<<" first_prefix_divergence="<<firstprefix<<"\n";
   v.push_back(std::make_unique<Core>(online));
   auto oi=std::make_unique<Core>();importObserved(*oi,op,observed);v.push_back(std::move(oi));
   auto os=std::make_unique<Core>(online);geometry(*os,op);v.push_back(std::move(os));
   auto h=std::make_unique<Core>();importObserved(*h,hp,observed);v.push_back(std::move(h));
   auto hk=std::make_unique<Core>(online);geometry(*hk,hp);v.push_back(std::move(hk));
   auto hc=std::make_unique<Core>(*v[3]);hc->parityCohortMode=false;hc->alternatingDeleteMode=false;hc->strideTwoDeleteTransitions=0;hc->runLeftDisabledBySmoothTrend=false;hc->lifoLaneDisabledForScale=false;hc->completedPlacementRuns.clear();hc->recentDeleteRanksPermille.clear();v.push_back(std::move(hc));
   auto hm=std::make_unique<Core>(*v[3]);hm->mcDecisionsUsed=online.mcDecisionsUsed;hm->mcRolloutsRun=online.mcRolloutsRun;v.push_back(std::move(hm));
   for(size_t i=0;i<v.size();++i){v[i]->emit=false;snapshot(names[i].c_str(),*v[i]);}
  }
  if(step<abort){
   if(c>0){online.place(c);long long digs,x;answers>>digs>>x;hp.place(c,int(x));op.place(c,int(online.lastStart));if(!firstprefix&&x!=online.lastStart)firstprefix=step;}
   else{online.remove(-c);long long x;answers>>x;hp.remove(-c);op.remove(-c);}
   observed.push_back(c);continue;
  }
  if(step==474||step==491||step==3485||step==19116){for(size_t i=0;i<v.size();++i)snapshot((names[i]+"_BEFORE_"+std::to_string(step)).c_str(),*v[i]);}
  std::cout<<step<<","<<c;
  for(auto&a:v){auto before=a->trenchLength;if(c>0)a->place(c);else a->remove(-std::int64_t(c));std::cout<<","<<(c>0?a->lastStart:-1)<<","<<(a->trenchLength-before)<<","<<a->trenchLength<<","<<a->freeByStart.size();}
  std::cout<<"\n";
 }
 for(size_t i=0;i<v.size();++i)snapshot((names[i]+"_FINAL").c_str(),*v[i]);
}
'''
s='#include <memory>\n#include <cstdio>\n#include <string>\n'+s+'\nusing namespace std;\n'+physical+tail
(out/'trace.cpp').write_text(s)
subprocess.run(['clang++','-std=c++17','-O2',str(out/'trace.cpp'),'-o',str(out/'trace')],check=True)
