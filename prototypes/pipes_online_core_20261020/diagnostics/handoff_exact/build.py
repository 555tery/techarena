from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OLD=HERE.parents[2]/'pipes_closed_ready_20261020/candidates-fast/hybrid'
def sha(x):return hashlib.sha256(x).hexdigest()
def main():
 raw=(OLD/'solution.cpp').read_bytes();s=raw.decode();replacements=[]
 def patch(before,after):
  nonlocal s
  assert s.count(before)==1,before
  s=s.replace(before,after,1);replacements.append({'before':before,'after':after})
 patch('    bool emit = true;', '    bool emit = true;\n    std::int64_t lastDigs=0,lastStart=0; // current shadow placement reply')
 patch('    void printPlacement(std::int64_t digs, std::int64_t start) {','    void printPlacement(std::int64_t digs, std::int64_t start) {\n        lastDigs=digs;lastStart=start;')
 patch('  size_t step=0,replayPlacements=0,fallbackCommands=0,abortStep=0;', '  int livePositionDifferences=0;\n  size_t exactAdoptions=0,importHandoffs=0,resynchronizations=0;\n  size_t step=0,replayPlacements=0,fallbackCommands=0,abortStep=0;')
 patch('   if(shadow){if(c>0)shadow->place(c);else shadow->remove(-std::int64_t(c));}', '''   // Both allocators have seen exactly the same command prefix. Lengths,
   // PID count and activity therefore agree; only live positions and T differ.
   const bool equalBefore=livePositionDifferences==0&&physical->T==shadow->trenchLength;
   std::int64_t shadowOldStart=-1;
   if(c>0)shadow->place(c);
   else{shadowOldStart=shadow->pipes.at(size_t(-c)).start;shadow->remove(-std::int64_t(c));}''')
 patch('    if(c>0){int oldT=physical->T;physical->place(c,address);', '''    if(c>0){
     if(address!=shadow->lastStart)++livePositionDifferences;
     int oldT=physical->T;physical->place(c,address);''')
 patch('    }else{const int x=physical->pipes.at(size_t(-c)).first;physical->remove(-c);fastio::answer(x);}', '''    }else{const int x=physical->pipes.at(size_t(-c)).first;
     if(x!=shadowOldStart)--livePositionDifferences;
     physical->remove(-c);fastio::answer(x);}
    if(livePositionDifferences<0)throw runtime_error("negative live-position difference count");
    if(!equalBefore&&livePositionDifferences==0&&physical->T==shadow->trenchLength)++resynchronizations;''')
 patch('   shadow.reset();\n   online=make_unique<fallback_online::Allocator>();\n   importObserved(*online,*physical,observed);\n   physical.reset();vector<int>().swap(observed);vector<Test>().swap(tests);vector<bool>().swap(active);\n   if(c>0)online->place(c);else online->remove(-std::int64_t(c));', '''   if(equalBefore){
    // The shadow already consumed this command with output disabled. Adopt its
    // complete state and emit that command's stored response exactly once.
    online=std::move(shadow);++exactAdoptions;
    if(c>0)fastio::answer(online->lastDigs,online->lastStart);
    else fastio::answer(shadowOldStart);
    online->emit=true;
   }else{
    shadow.reset();++importHandoffs;
    online=make_unique<fallback_online::Allocator>();
    importObserved(*online,*physical,observed);
    if(c>0)online->place(c);else online->remove(-std::int64_t(c));
   }
   physical.reset();vector<int>().swap(observed);vector<Test>().swap(tests);vector<bool>().swap(active);''')
 patch('cerr<<"replay_placements="', 'cerr<<"exact_adoptions="<<exactAdoptions<<" import_handoffs="<<importHandoffs<<" resynchronizations="<<resynchronizations<<" live_position_differences="<<livePositionDifferences<<" replay_placements="')
 restored=s
 for row in reversed(replacements):
  assert restored.count(row['after'])==1
  restored=restored.replace(row['after'],row['before'],1)
 assert restored.encode()==raw
 path=HERE/'solution.cpp';path.write_text(s)
 subprocess.run(['clang++','-std=c++17','-O2',str(path),'-o',str(HERE/'solver')],check=True)
 (HERE/'build.json').write_text(json.dumps({'original_source_sha256':sha(raw),'source_sha256':sha(path.read_bytes()),'binary_sha256':sha((HERE/'solver').read_bytes()),'only_listed_replacements':True,'replacements':replacements,'equality':'O(1) live PID position difference count plus exact trench equality before current command; late resynchronization supported'},indent=2)+'\n')
 print(HERE/'build.json')
if __name__=='__main__':main()
