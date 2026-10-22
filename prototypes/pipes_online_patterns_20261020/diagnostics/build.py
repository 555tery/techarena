from pathlib import Path
import subprocess,hashlib,json,sys
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[1]/'pipes_online_core_20261020'
# Args: old input path, state-focus command (0 disables), one-action forced start (-1 disables).
HEAD='''#include <iomanip>\n#include <fstream>\n#include <sstream>\n#include <string>\n#include <cstdlib>\nstatic long long focusStep=0,forceStep=0,forceStart=-1;\n'''
METHOD=r'''
    void preSnapshot(int c){
      std::cerr<<std::setprecision(17)<<"{\"type\":\"pre_command\",\"step\":"<<diagnosticStep<<",\"command\":"<<c<<",\"T\":"<<trenchLength<<",\"active\":"<<activePipeCount<<",\"mc\":"<<mcDecisionsUsed<<",\"model_age\":"<<(primalStep-primalModelStep)<<",\"parity\":"<<parityCohortMode<<",\"alternating\":"<<alternatingDeleteMode<<",\"smooth\":"<<runLeftDisabledBySmoothTrend<<",\"slab\":"<<cohortSlabActive<<",\"gaps\":[";
      bool comma=false;for(auto [l,r]:freeByStart){if(comma)std::cerr<<",";comma=true;std::cerr<<"["<<l<<","<<r<<","<<gapCohort.at(l)<<","<<gapFreedAt.at(l)<<"]";}
      std::cerr<<"],\"request_freq\":[";for(int i=1;i<=40;++i){if(i>1)std::cerr<<",";std::cerr<<primalRecentRequests[i];}std::cerr<<"]}\n";
    }
    void decisionSnapshot(int length,bool highSide,
        const std::vector<std::pair<std::int64_t,std::int64_t>>& candidates,
        StartIter legacyBest,StartIter best){
      diagnosticDPActive=diagnosticDPActive||primalScoredDecisions>diagnosticDPBefore;
      diagnosticLegacy=legacyBest==freeByStart.end()?-1:legacyBest->first;
      diagnosticSelected=best==freeByStart.end()?-1:best->first;
      diagnosticHigh=highSide;
      if(diagnosticStep!=focusStep)return;
      std::cerr<<std::setprecision(17)<<"{\"step\":"<<diagnosticStep<<",\"length\":"<<length<<",\"T\":"<<trenchLength<<",\"active\":"<<activePipeCount<<",\"gaps\":"<<freeByStart.size()<<",\"high\":"<<highSide<<",\"parity\":"<<parityCohortMode<<",\"smooth\":"<<runLeftDisabledBySmoothTrend<<",\"alternating\":"<<alternatingDeleteMode<<",\"slab\":"<<cohortSlabActive<<",\"mc\":"<<mcDecisionsUsed<<",\"dp\":"<<primalScoredDecisions<<",\"model_age\":"<<(primalStep-primalModelStep)<<",\"recentDeletes\":"<<primalRecentDeletes<<",\"legacy\":"<<diagnosticLegacy<<",\"selected\":"<<diagnosticSelected<<",\"candidates\":[";
      bool comma=false;for(auto [g,x]:candidates){if(comma)std::cerr<<",";comma=true;std::cerr<<"["<<x<<","<<g<<","<<primalGapLoss(g,length)<<","<<primalGapValue[g]<<","<<primalGapValue[g-length]<<"]";}
      std::cerr<<"],\"request_freq\":[";for(int i=1;i<=40;++i){if(i>1)std::cerr<<",";std::cerr<<primalRecentRequests[i];}
      std::cerr<<"],\"legacy_freq\":[";for(int i=1;i<=40;++i){if(i>1)std::cerr<<",";std::cerr<<recentFrequency[i];}
      std::cerr<<"],\"gap_hist\":[";comma=false;for(size_t i=1;i<primalGapCounts.size();++i)if(primalGapCounts[i]){if(comma)std::cerr<<",";comma=true;std::cerr<<"["<<i<<","<<primalGapCounts[i]<<"]";}
      std::cerr<<"]}\n";
    }
'''
TAIL=r'''
int main(int argc,char**argv){
 std::ifstream file(argv[1]);double weight;int n;file>>weight>>n;
 if(argc>2)focusStep=std::stoll(argv[2]);if(argc>4){forceStep=std::stoll(argv[3]);forceStart=std::stoll(argv[4]);}
 fallback_online::Allocator a;a.emit=false;
 for(int step=1;step<=n;++step){int c;file>>c;a.diagnosticStep=step;
  if(step==focusStep)a.preSnapshot(c);
  const auto oldT=a.trenchLength;const auto oldMC=a.mcDecisionsUsed;
  if(c>0)a.place(c);else a.remove(-std::int64_t(c));
  std::cout<<step<<","<<c<<","<<(c>0?a.lastStart:-1)<<","<<(a.trenchLength-oldT)<<","<<a.trenchLength<<","<<a.freeByStart.size()<<","<<a.diagnosticDPActive<<","<<a.diagnosticLegacy<<","<<a.diagnosticSelected<<","<<a.diagnosticHigh<<","<<oldMC<<","<<a.mcDecisionsUsed<<","<<a.primalScoredDecisions<<","<<a.activePipeCount<<","<<a.primalRecentDeletes<<"\n";
 }
}
'''
for name,source in [('baseline',OLD/'candidates/baseline/solution.cpp'),('current',OLD/'release/solution.cpp'),('no_dp',OLD/'release/solution.cpp'),('mc_off_dp',OLD/'release/solution.cpp'),('fresh',OLD/'release/solution.cpp'),('legacy_tie',OLD/'release/solution.cpp')]:
 if len(sys.argv)>1 and name not in sys.argv[1:]:continue
 s=source.read_text();s=s[:s.index('\nint main()')];s=s.replace('using fallback_online::Allocator;','')
 s=s.replace('    bool emit = true;','''    bool emit = true;
    std::int64_t lastStart=0,lastDigs=0,diagnosticLegacy=-1,diagnosticSelected=-1;
    long long diagnosticStep=0;bool diagnosticDPActive=false,diagnosticHigh=false;
    std::size_t diagnosticDPBefore=0;''',1)
 s=s.replace('    void place(int length) {\n        lifetimeModel.advance();','    void place(int length) {\n        diagnosticDPActive=false;diagnosticLegacy=diagnosticSelected=-1;diagnosticDPBefore=primalScoredDecisions;\n        lifetimeModel.advance();',1)
 s=s.replace('    void printPlacement(std::int64_t digs, std::int64_t start) {','    void printPlacement(std::int64_t digs, std::int64_t start) {\n        lastStart=start;lastDigs=digs;',1)
 marker='        if (recycleRecent && best != freeByStart.end()) {'
 s=s.replace(marker,'        decisionSnapshot(length,highSide,candidates,legacyBest,best);\n'+marker,1)
 insert='    bool hasSameLengthRecentRun(int length) const {'
 index=s.rfind(insert);assert index>0;s=s[:index]+METHOD+'\n'+s[index:]
 # One forced actual endpoint on the original state; suffix returns to current policy.
 needle='            start = consumeAtSide(gap, length, highSide);'
 s=s.replace(needle,'''            if(diagnosticStep==forceStep&&forceStart>=0){
              auto forced=freeByStart.upper_bound(forceStart);if(forced==freeByStart.begin())throw std::runtime_error("forced placement not free");--forced;
              if(forceStart!=forced->first&&forceStart+length!=forced->second)throw std::runtime_error("forced interior endpoint");
              gap=forced;highSide=forceStart!=forced->first;
            }
'''+needle,1)
 if name=='no_dp':s=s.replace('const bool ordinaryLargeMode = !parityCohortMode &&','const bool ordinaryLargeMode = false && !parityCohortMode &&',1)
 if name=='mc_off_dp':s=s.replace('#if defined(MC_ROLLOUT_DISABLED)','#if defined(MC_ROLLOUT_DISABLED)',1).replace('        if (mcDecisionsUsed >= kMcDecisionBudget ||','        if (diagnosticDPActive) return baselineGap->first;\n        if (mcDecisionsUsed >= kMcDecisionBudget ||',1)
 if name=='legacy_tie':
  s=s.replace('double primalBestScore = std::numeric_limits<double>::infinity();\n                StartIter primalBest = freeByStart.end();','double primalBestScore = primalGapLoss(legacyBest->second-legacyBest->first,length);\n                StartIter primalBest = legacyBest;',1)
  s=s.replace('                        (tied && addressPreferred)) {','                        (false && tied && addressPreferred)) {',1)
 if name=='fresh':s=s.replace('        if (primalModelDirty || primalStep - primalModelStep >= 64 ||','        if (true || primalModelDirty || primalStep - primalModelStep >= 64 ||',1)
 # Fresh call before MC sees updated decision status from decisionSnapshot.
 target=HERE/name;target.mkdir(exist_ok=True);(target/'solution.cpp').write_text(HEAD+s+TAIL)
 subprocess.run(['clang++','-std=c++17','-O2',str(target/'solution.cpp'),'-o',str(target/'solver')],check=True)
 print(name,flush=True)
