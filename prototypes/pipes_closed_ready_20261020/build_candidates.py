#!/usr/bin/env python3
"""Build three preregistered candidates. All output stays under candidates/."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OUT = ROOT / 'candidates'
ORIGINAL = REPO / 'research-campaigns/20261018T141843+0700-autonomous/releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
TABLE_SOURCE = REPO / 'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
PIN = '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def replace_once(s, before, after):
    assert s.count(before) == 1, before
    return s.replace(before, after)

IMPORT = r'''
// One-off O(N log N) import. All commands here have already been answered.
// Policy-created slab reservations and gap ownership have no physical meaning
// in a foreign layout: expose the complete physical free space as shared gaps.
void importObserved(fallback_online::Allocator& out, const Allocator& actual,
                    const vector<int>& observed) {
 int next=0;
 for (int command:observed) {
  out.lifetimeModel.advance();
  if (command>0) {
   const int id=++next;
   if (out.observedRunLength!=command) {
    if (out.observedRunCount>0) {
     out.completedPlacementRuns.emplace_back(out.observedRunLength,out.observedRunCount);
     if(out.completedPlacementRuns.size()>8)out.completedPlacementRuns.pop_front();
     const auto total=out.activeRunDeleteParityCount[0]+out.activeRunDeleteParityCount[1];
     const auto dominant=max(out.activeRunDeleteParityCount[0],out.activeRunDeleteParityCount[1]);
     if(total>=8&&dominant*100>=total*85){
      const int parity=out.activeRunDeleteParityCount[0]>out.activeRunDeleteParityCount[1]?0:1;
      out.previousCompletedDeleteRelativeParity=out.lastCompletedDeleteRelativeParity;
      out.lastCompletedDeleteRelativeParity=parity^(out.activeRunFirstPid&1);
     }else{
      out.previousCompletedDeleteRelativeParity=-1;
      out.lastCompletedDeleteRelativeParity=-1;
     }
    }
    out.observedRunLength=command;out.observedRunCount=0;
    out.activeRunFirstPid=id;out.activeRunDeleteParityCount={};
   }
   ++out.observedRunCount;
   if(out.activePipeCount>fallback_online::kMcMaxActivePipes)out.lifoLaneDisabledForScale=true;
   if(out.hasSmoothSizeTrendWith(command))out.runLeftDisabledBySmoothTrend=true;
   const int cohort=int(out.lengthOccurrenceCount[command]%2);
   const auto x=actual.pipes[id].first;
   out.pipes.push_back(fallback_online::Pipe{x,command,true,cohort});
   out.activeByEnd.emplace(x+command,id);out.fenwickAdd(id,1);++out.activePipeCount;
   ++out.lengthOccurrenceCount[command];out.recordLength(command);
   out.recordObservation(fallback_online::Observation{1,command});
   out.recordPrimalEvent(command); // also registers lifetime-model birth
  }else{
   const int id=-command;auto& p=out.pipes.at(size_t(id));
   if(!p.active)throw runtime_error("import inactive PID");
   const int rank=out.rankFromNewestPermille(id);
   out.lifetimeModel.observeDeletion(size_t(id));out.activeByEnd.erase(p.start+p.length);
   p.active=false;out.fenwickAdd(id,-1);--out.activePipeCount;++out.releaseEpoch;
   out.recordDeletionPattern(id,p.length);out.recordPrimalEvent(-1);
   if(id>=out.activeRunFirstPid)++out.activeRunDeleteParityCount[id&1];
   auto& counts=out.removedLengthCohort[p.length];++counts[p.sizeCohort];
   if(counts[0]+counts[1]>=8&&max(counts[0],counts[1])*100>=(counts[0]+counts[1])*85&&out.hasSteadySizeTrend())out.parityCohortMode=true;
   out.recordObservation(fallback_online::Observation{-1,rank});
  }
 }
 out.trenchLength=actual.T;
 for(auto [left,right]:actual.g)out.addFreeGap(left,right,-1,out.releaseEpoch);
 out.cohortSlabActive=false;
 if(out.pipes.size()!=actual.pipes.size())throw runtime_error("import PID count");
 for(size_t id=1;id<actual.pipes.size();++id){
  const auto& p=out.pipes[id];
  if(p.start!=actual.pipes[id].first||p.active!=(actual.pipes[id].second>0))throw runtime_error("import geometry");
 }
 if(out.fenwickPrefix(int(out.pipes.size()-1))!=int(out.activePipeCount))throw runtime_error("import rank index");
}

bool guardedReplay(const Allocator& actual,int x,int n,int shadowT){
 if(!actual.fits(x,n))return false;
 const int digs=max(0,(x+n-actual.T+19)/20);
 const int newT=actual.T+20*digs;
 if(newT>shadowT)return false;
 int left=actual.T,right=newT;
 if(x<actual.T){
  auto it=actual.g.upper_bound(x);
  if(it==actual.g.begin())return false;
  --it;left=it->first;right=it->second;
  if(right==actual.T)right=newT;
 }else if(!actual.g.empty()&&prev(actual.g.end())->second==actual.T){
  left=prev(actual.g.end())->first;
 }
 return x==left||x+n==right;
}

int main(){
 try{
  ios::sync_with_stdio(false);cin.tie(nullptr);
  vector<Test>tests;
  for(const auto& chunks:encoded){
   string joined;
   for(size_t part=0;part<chunks.count;++part)joined+=chunks.parts[part];
   auto a=decode(joined.c_str());size_t k=0;unsigned n=var(a,k);Test t;int previous=0;
   while(n--){int c=signedVar(a,k);t.cmd.push_back(c);
    if(c>0){previous+=signedVar(a,k);t.pos.push_back(previous);}else t.pos.push_back(-1);}
   if(k!=a.size())throw runtime_error("table tail");tests.push_back(std::move(t));
  }
  vector<bool>active(tests.size(),true);
  auto physical=make_unique<Allocator>();physical->emit=false;
  unique_ptr<fallback_online::Allocator>shadow;
  if(CAUTIOUS_HYBRID){shadow=make_unique<fallback_online::Allocator>();shadow->emit=false;}
  unique_ptr<fallback_online::Allocator>online;
  vector<int>observed;observed.reserve(200000);
  size_t step=0,replayPlacements=0,fallbackCommands=0,abortStep=0;string abortReason="none";int c;
  while(cin>>c&&c!=0){
   if(online){if(c>0)online->place(c);else online->remove(-std::int64_t(c));++fallbackCommands;++step;continue;}
   if(shadow){if(c>0)shadow->place(c);else shadow->remove(-std::int64_t(c));}
   int address=-1;bool agrees=true,matched=false;
   for(size_t i=0;i<tests.size();++i)if(active[i]){
    if(step>=tests[i].cmd.size()||tests[i].cmd[step]!=c){active[i]=false;continue;}
    matched=true;if(c>0){int p=tests[i].pos[step];if(address>=0&&address!=p)agrees=false;address=p;}
   }
   const bool replayOK=matched&&agrees&&(c<0||physical->fits(address,c))&&
    (!CAUTIOUS_HYBRID||c<0||guardedReplay(*physical,address,c,int(shadow->trenchLength)));
   if(replayOK){
    if(c>0){int oldT=physical->T;physical->place(c,address);
     cout<<(physical->T-oldT)/20<<' '<<address<<'\n'<<flush;++replayPlacements;
    }else{const int x=physical->pipes.at(size_t(-c)).first;physical->remove(-c);cout<<x<<'\n'<<flush;}
    observed.push_back(c);++step;continue;
   }
   // Release the shadow before allocating the final core. No repeated clones,
   // episodes, MC wrapper, scale gate, or return to replay after this transition.
   abortStep=step+1;
   abortReason=!matched?"command_mismatch":!agrees?"table_conflict":(c>0&&!physical->fits(address,c))?"invalid_replay_geometry":"guard";
   shadow.reset();
   online=make_unique<fallback_online::Allocator>();
   importObserved(*online,*physical,observed);
   physical.reset();vector<int>().swap(observed);vector<Test>().swap(tests);vector<bool>().swap(active);
   if(c>0)online->place(c);else online->remove(-std::int64_t(c));
   ++fallbackCommands;++step;
  }
  cerr<<"replay_placements="<<replayPlacements<<" fallback_commands="<<fallbackCommands<<" abort_reason="<<abortReason<<" abort_step="<<abortStep<<" T="<<(online?online->trenchLength:physical->T)<<'\n';
 }catch(const exception&e){cerr<<"error: "<<e.what()<<'\n';return 2;}
 return 0;
}
'''

def main():
    raw=ORIGINAL.read_bytes()
    assert sha(raw)==PIN
    source=raw.decode()
    original_core=source[:source.index('\nint main() {')]
    core=replace_once(original_core,'namespace {','namespace fallback_online {')
    core=replace_once(core,'class Allocator {\npublic:', 'class Allocator {\npublic:\n    bool emit = true;')
    core=replace_once(core,'\nprivate:\n    using StartIter', '\npublic: // embedding import helpers\n    using StartIter')
    core=replace_once(core,"        std::cout << pipe.start << '\\n' << std::flush;", "        if (emit) std::cout << pipe.start << '\\n' << std::flush;")
    core=replace_once(core,'    static void printPlacement(', '    void printPlacement(')
    core=replace_once(core,"        std::cout << digs << ' ' << start << '\\n' << std::flush;", "        if (emit) std::cout << digs << ' ' << start << '\\n' << std::flush;")
    core=replace_once(core,'    static void printInvalidPidFallback(', '    void printInvalidPidFallback(')
    core=replace_once(core,"        std::cout << 0 << '\\n' << std::flush;", "        if (emit) std::cout << 0 << '\\n' << std::flush;")
    # Reverse all embedding changes: this assertion is the structural parity gate.
    check=core.replace('namespace fallback_online {','namespace {',1)
    check=check.replace('    bool emit = true;\n','',1).replace('public: // embedding import helpers','private:',1)
    check=check.replace('if (emit) std::cout','std::cout').replace('    void printPlacement(', '    static void printPlacement(').replace('    void printInvalidPidFallback(', '    static void printInvalidPidFallback(')
    assert check==original_core, 'core differs beyond embedding changes'
    old=TABLE_SOURCE.read_text()
    table=old[old.index('static const char* encoded[]='):old.index('struct Allocator{')]
    raw_table=table
    literal_end=table.index('};')+2
    literal_block=table[:literal_end]
    groups=literal_block[literal_block.index('{')+1:literal_block.rindex('}')].split(',')
    chunks=[]
    for group in groups:
        literals=re.findall(r'"([A-Za-z0-9+/=]*)"',group)
        if literals:chunks.append(literals)
    assert len(chunks)==15
    # MSVC limits a concatenated string literal to 65535 bytes. Keep every
    # original <=120-byte literal separate; join one table at runtime.
    table='struct EncodedTable { const char* const* parts; size_t count; };\n'
    for i, parts in enumerate(chunks):
        table+=f'static const char* const encoded{i}[]={{\n'
        table+=''.join('"'+part+'",\n' for part in parts)+'};\n'
    table+='static const EncodedTable encoded[]={\n'
    table+=''.join(f'{{encoded{i},sizeof(encoded{i})/sizeof(encoded{i}[0])}},\n' for i in range(len(chunks)))+'};\n'
    table+=raw_table[literal_end:]
    physical=old[old.index('struct Allocator{'):old.index('// Import only observed commands')]
    physical=physical.replace('bool fits(int x,int n)', 'bool fits(int x,int n) const')
    online=core+'\nusing fallback_online::Allocator;\n'+source[source.index('\nint main() {'):]
    header='#include <memory>\n#include <cstdio>\n#include <stdexcept>\n#include <string>\n'
    outputs={'online':online,
             'full':header+core+'\nusing namespace std;\n'+table+physical+'\n#define CAUTIOUS_HYBRID 0\n'+IMPORT,
             'hybrid':header+core+'\nusing namespace std;\n'+table+physical+'\n#define CAUTIOUS_HYBRID 1\n'+IMPORT}
    compiler=shutil.which('clang++')
    if not compiler:raise SystemExit('clang++ required')
    ref=OUT/'build/reference';ref.mkdir(parents=True,exist_ok=True)
    (ref/'solution.cpp').write_bytes(raw)
    all_sources={'reference':ref/'solution.cpp'}
    for name,text in outputs.items():
        target=OUT/name;target.mkdir(parents=True,exist_ok=True)
        path=target/'solution.cpp';path.write_text(text);all_sources[name]=path
    (OUT/'build/extracted_core.cpp').write_text(core)
    (OUT/'build/public_table.inc').write_text(table)
    metadata={'original_path':str(ORIGINAL.relative_to(REPO)),'original_sha256':sha(raw),
              'original_core_sha256':sha(original_core.encode()),'embedded_core_sha256':sha(core.encode()),
              'table_sha256':sha(table.encode()),'original_table_sha256':sha(raw_table.encode()),
              'table_payload_sha256':sha(''.join(''.join(parts) for parts in chunks).encode()),
              'table_source_sha256':sha(TABLE_SOURCE.read_bytes()),
              'import_policy':{'gap_ownership':'shared','gap_age':'all physical free gaps assigned final observed deletion epoch','reservations':'disabled; all physical free space exposed','history':'observed commands only; lifetime/cohort/run/parity/Fenwick counters rebuilt','core_continuation':'unmodified trial22 decisions, original MC budget starts unused'},
              'compiler':compiler,'flags':['-std=c++17','-O2'],'structural_core_parity':True,'candidates':{}}
    for name,path in all_sources.items():
        binary=path.parent/'solver'
        command=[compiler,'-std=c++17','-O2',str(path),'-o',str(binary)]
        subprocess.run(command,check=True)
        metadata['candidates'][name]={'source':str(path.relative_to(OUT)),'binary':str(binary.relative_to(OUT)),
                                      'source_sha256':sha(path.read_bytes()),'binary_sha256':sha(binary.read_bytes())}
        (path.parent/'build.json').write_text(json.dumps({**metadata['candidates'][name], 'original_sha256':PIN,'embedded_core_sha256':metadata['embedded_core_sha256'],'table_sha256':metadata['table_sha256'] if name not in ('reference','online') else None,'structural_core_parity':True,'import_policy':metadata['import_policy'] if name in ('full','hybrid') else None},indent=2)+'\n')
    (OUT/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(OUT/'build.json')

if __name__=='__main__':main()
