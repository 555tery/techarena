#!/usr/bin/env python3
"""Prepare one public15 offline lifetime-class pilot, never build or run it.

Fixed current0759 prefix4999. Suffix final survivors use leftmost fitting gap,
left edge; future-deleted pipes use rightmost fitting gap, right edge. No fit:
minimum tail extension, same class side. This uses public future information
solely to construct a table; it is not a causal online policy.
"""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,re
PARENT=Path('/tmp/pipes_fixedprefix_suffix_pilot_20261022.py')
PARENT_SHA='58f4cebcdea697f05cdcd7362bd2b5baeb4af8939527cd7687dc7174cdb21b08'
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha(PARENT.read_bytes())==PARENT_SHA,'pinned audit skeleton changed'
spec=importlib.util.spec_from_file_location('fixedprefix_pilot_parent',PARENT)
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
ROOT,RUNTIME,RELEASE=parent.ROOT,parent.RUNTIME,parent.RELEASE
RELEASE_SHA,PUBLIC15_ID,CUTOFF=parent.RELEASE_SHA,parent.PUBLIC15_ID,parent.CUTOFF
INDEX_SOURCE=ROOT/'results/pipes/policy-comparison/source.cpp'
INDEX_SOURCE_SHA='bf04dc2cf7dd18fb1e4cf28f42366e164ab4de668e0be6fb5243709cc4147bb6'
RUNTIME_SHA='ae7e1e0a54510ee9a8d396670e2d40c2439d9286e8e13cd3ea93be8820b4c891'

INDEX_CPP=r'''
// Reuse the bounded size-class sets from policy-comparison/source.cpp.
// Class40 holds all lengths >=40. All fitting gaps, including tail, participate.
struct FitClassIndex {
 std::set<int> starts[41];
 std::size_t count=0;std::uint64_t fingerprint=0;
 static std::uint64_t token(int l,int r){
  std::uint64_t z=(std::uint64_t(std::uint32_t(l))<<32)|std::uint32_t(r);
  z+=0x9e3779b97f4a7c15ULL;z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
  z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);
 }
 void add(int l,int r){
  if(l>=r)return;
  requirePilot(starts[std::min(40,r-l)].insert(l).second,"duplicate class-index gap");
  ++count;fingerprint^=token(l,r);
 }
 void erase(int l,int r){
  requirePilot(l<r&&starts[std::min(40,r-l)].erase(l)==1,"missing class-index gap");
  --count;fingerprint^=token(l,r);
 }
 int choose(int length,bool survivor)const{
  int answer=-1;
  for(int c=length;c<=40;++c)if(!starts[c].empty()){
   const int x=survivor?*starts[c].begin():*starts[c].rbegin();
   if(answer<0||(survivor?x<answer:x>answer))answer=x;
  }
  return answer;
 }
 // Local mirror mutation is performed before exact physical Allocator mutation.
 // Hash has a separately maintained physical-local accumulator, not a gap scan.
 std::uint64_t physicalFingerprint=0;
 void physicalErase(int l,int r){physicalFingerprint^=token(l,r);erase(l,r);}
 void physicalAdd(int l,int r){if(l<r)add(l,r);}
 std::vector<std::pair<int,int>> beforePlace(const Allocator& a,int x,int n){
  const int newT=a.T+20*std::max(0,(x+n-a.T+19)/20);
  int l=0,r=0;
  if(newT>a.T){
   l=a.T;r=newT;
   if(!a.g.empty()){auto tail=std::prev(a.g.end());if(tail->second==a.T){l=tail->first;physicalErase(tail->first,tail->second);}}
  }else{
   auto it=a.g.upper_bound(x);requirePilot(it!=a.g.begin(),"index placement has no physical gap");--it;
   l=it->first;r=it->second;physicalErase(l,r);
  }
  requirePilot(l<=x&&x+n<=r,"index placement outside affected gap");
  physicalAdd(l,x);physicalAdd(x+n,r);
  std::vector<std::pair<int,int>> touched;
  if(l<x)touched.push_back({l,x});if(x+n<r)touched.push_back({x+n,r});
  return touched;
 }
 std::vector<std::pair<int,int>> beforeRemove(const Allocator& a,int pid){
  auto p=a.pipes.at(std::size_t(pid));int l=p.first,r=l+p.second;
  auto right=a.g.lower_bound(l);
  if(right!=a.g.begin()){auto left=std::prev(right);if(left->second==l){l=left->first;physicalErase(left->first,left->second);}}
  if(right!=a.g.end()&&right->first==r){r=right->second;physicalErase(right->first,right->second);}
  physicalAdd(l,r);return {{l,r}};
 }
 void checkLocal(const Allocator& a,const std::vector<std::pair<int,int>>& touched){
  requirePilot(count==a.g.size(),"class-index physical gap count mismatch");
  for(auto p:touched){auto it=a.g.find(p.first);requirePilot(it!=a.g.end()&&it->second==p.second,"class-index local physical gap mismatch");physicalFingerprint^=token(it->first,it->second);}
  requirePilot(fingerprint==physicalFingerprint,"class-index physical gap fingerprint mismatch");
 }
};
'''

def cpp_template():
 s=parent.CPP_TEMPLATE
 s=s.replace('// Single public-only fixed4999/guard5-BF pilot. No production changes.',
  '// One public-only fixed4999/oracle-class pilot. No production changes.')
 anchor='int main(int argc,char**argv){'
 assert s.count(anchor)==1;s=s.replace(anchor,INDEX_CPP+'\n'+anchor)
 s=s.replace('Allocator actual;actual.emit=false;','Allocator actual;actual.emit=false;FitClassIndex fitIndex;')
 s=s.replace('bool prefixExact=true;','bool prefixExact=true;unsigned long long survivors=0,temporary=0,fitting=0,tailDigs=0;')
 start=s.index('    if(step>=cutoff){')
 end=s.index('    requirePilot(actual.fits(chosen,command)',start)
 s=s[:start]+r'''    if(step>=cutoff){
     requirePilot(target==0||target==1,"invalid oracle lifetime class");
     const bool survivor=target==1;
     if(survivor)++survivors;else ++temporary;
     const int gapStart=fitIndex.choose(command,survivor);
     const bool exactHasFit=actual.sizes.lower_bound({command,-1})!=actual.sizes.end();
     requirePilot((gapStart>=0)==exactHasFit,"class-index fit existence disagrees");
     if(gapStart>=0){
      auto gap=actual.g.find(gapStart);
      requirePilot(gap!=actual.g.end()&&gap->second-gap->first>=command,"class-index chosen gap invalid");
      chosen=survivor?gap->first:gap->second-command;++fitting;
     }else{
      int tailStart=actual.T;
      if(!actual.g.empty()){auto tail=std::prev(actual.g.end());if(tail->second==actual.T)tailStart=tail->first;}
      const int minDigs=std::max(0,(tailStart+command-actual.T+19)/20);
      requirePilot(minDigs>0,"no-fit request needs no digs");
      const int newT=actual.T+20*minDigs;
      chosen=survivor?tailStart:newT-command;++tailDigs;
     }
     ++accepted;
    }else{++prefixPlacements;}
''' +s[end:]
 s=s.replace('    actual.place(command,chosen);','    const auto touched=fitIndex.beforePlace(actual,chosen,command);\n    actual.place(command,chosen);fitIndex.checkLocal(actual,touched);')
 s=s.replace('    actual.remove(pid);requirePilot(actual.T==auditedT,"deletion changed trench");','    const auto touched=fitIndex.beforeRemove(actual,pid);\n    actual.remove(pid);fitIndex.checkLocal(actual,touched);requirePilot(actual.T==auditedT,"deletion changed trench");')
 # A single full terminal map scan is an index audit, never part of selection.
 s=s.replace('  const bool gain=actual.T<baselineT;',r'''  std::uint64_t terminalHash=0;std::size_t terminalCount=0;
  for(auto gap:actual.g){terminalHash^=FitClassIndex::token(gap.first,gap.second);++terminalCount;
   requirePilot(fitIndex.starts[std::min(40,gap.second-gap.first)].count(gap.first)==1,"terminal index member missing");}
  requirePilot(terminalHash==fitIndex.fingerprint&&terminalCount==fitIndex.count,"terminal full index audit mismatch");
  const bool gain=actual.T<baselineT;''')
 s=s.replace('<<",\\\"F\\\":"<<finalVolume', '<<",\\\"survivor_insertions\\\":"<<survivors<<",\\\"temporary_insertions\\\":"<<temporary\n   <<",\\\"fitting_insertions\\\":"<<fitting<<",\\\"tail_dig_insertions\\\":"<<tailDigs\n   <<",\\\"F\\\":"<<finalVolume')
 s=s.replace('<<",\\\"unfiltered_targetT\\\":"<<unfilteredTargetT','')
 return s

def prepare(destination):
 destination=Path(destination).resolve();assert not destination.exists(),destination
 assert sha(RELEASE.read_bytes())==RELEASE_SHA,'current0759 source changed'
 assert sha(INDEX_SOURCE.read_bytes())==INDEX_SOURCE_SHA,'pinned class-index reference changed'
 runtimeBytes=RUNTIME.read_bytes();assert sha(runtimeBytes)==RUNTIME_SHA,'current physical source changed'
 metadata=None
 for line in (ROOT/'prototypes/pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl').open():
  row=json.loads(line)
  if row.get('public_number')==15:metadata=row;break
 assert metadata and metadata['id']==PUBLIC15_ID
 reference=None
 for line in (ROOT/'prototypes/pipes_guard_generalization_20261022/records.jsonl').open():
  row=json.loads(line)
  if row.get('type')=='evaluation' and row.get('suite')=='archive-production' and row.get('kind')=='production' and row.get('id')==PUBLIC15_ID:reference=row
 assert reference and reference.get('status')=='ok'
 inputPath=Path(metadata['test_file']);inputBytes=inputPath.read_bytes()
 assert sha(inputBytes)==metadata['test_sha256']==reference['test_sha256']
 toks=inputBytes.split();count=int(toks[1]);commands=list(map(int,toks[2:2+count]));assert len(commands)==count==200000
 assert toks[2+count:]==[b'0'],'unexpected public-input terminator'
 tracePath=Path(metadata['judge_output_file']);traceBytes=gzip.open(tracePath,'rb').read()
 assert sha(traceBytes)==metadata['response_sha256']==reference['response_sha256']
 traceLines=traceBytes.decode().splitlines();assert len(traceLines)==count
 finalVolume=metadata['final_occupied_length_m'];baselineT=reference['trench_length_m']
 assert finalVolume==418757 and baselineT==438460
 # Future information is reduced to exactly one bit per PID, never coordinates.
 positiveCount=sum(c>0 for c in commands);deleted={-c for c in commands if c<0}
 assert all(0<p<=positiveCount for p in deleted)
 prefixRows=[];prefixT=0;prefixAlive={};nextPid=0
 for command,line in zip(commands[:CUTOFF],traceLines[:CUTOFF]):
  values=list(map(int,line.split()))
  if command>0:
   assert len(values)==2;digs,address=values;prefixT+=20*digs;nextPid+=1;prefixAlive[nextPid]=(address,command)
  else:
   assert len(values)==1;digs,address=-1,values[0];assert prefixAlive.pop(-command)[0]==address
  prefixRows.append((digs,address))
 assert nextPid==4006 and prefixT==12260 and len(prefixAlive)==3013
 lines=[f'{count} {CUTOFF} {finalVolume} {baselineT} {prefixT} 0\n'];pid=0
 for step,command in enumerate(commands):
  if command>0:pid+=1
  if step<CUTOFF:
   expectedDigs,expectedAddress=prefixRows[step];target=expectedAddress if command>0 else -1
  else:
   expectedDigs=expectedAddress=-1;target=int(pid not in deleted) if command>0 else -1
  lines.append(f'{command} {target} {expectedDigs} {expectedAddress}\n')
 preparedBytes=''.join(lines).encode();prefixTraceBytes=b'\n'.join(traceBytes.splitlines()[:CUTOFF])+b'\n'
 hashes={'RUNTIME_SHA':sha(runtimeBytes),'PUBLIC_INPUT_SHA':sha(inputBytes),'PREPARED_INPUT_SHA':sha(preparedBytes),
 'TRACE_SHA':sha(traceBytes),'PREFIX_TRACE_SHA':sha(prefixTraceBytes),'PREPARE_SHA':sha(Path(__file__).read_bytes())}
 cpp=cpp_template()
 for key,value in hashes.items():cpp=cpp.replace('@'+key+'@',value)
 assert not re.search(r'@[A-Z_]+@',cpp)
 destination.mkdir(parents=True)
 (destination/'runtime_source.cpp').write_bytes(runtimeBytes);(destination/'prepared.in').write_bytes(preparedBytes);(destination/'pilot.cpp').write_text(cpp)
 manifest={'schema':'pipes-fixedprefix-oracle-class-pilot-v1','public_case':15,'cutoff_commands':CUTOFF,
 'prefix_placements':4006,'prefix_live_pipes':3013,'prefix_T':prefixT,'baseline_T':baselineT,'F':finalVolume,
 'oracle':'one public-future bit per PID: survives final / eventually deleted; suffix only',
 'index':'min(gapLength,40) ordered-address sets; query <=40 classes incl tail; O(log N) local split/merge updates',
 'index_reference':str(INDEX_SOURCE),'index_reference_sha256':INDEX_SOURCE_SHA,'parent_audit_skeleton_sha256':PARENT_SHA,
 'current0759_source_sha256':RELEASE_SHA,'input_source':str(inputPath),'trace_source':str(tracePath),'hashes':hashes,
 'pilot_cpp_sha256':sha(cpp.encode()),'files':{k:str(destination/k)for k in ['runtime_source.cpp','prepared.in','pilot.cpp']},
 'build_argv':['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=5',str(destination/'pilot.cpp'),'-o',str(destination/'pilot')],
 'run_argv':[str(destination/'pilot'),str(destination/'prepared.in'),str(destination/'trial')],
 'scope':'preparation only, one fixed offline public15 hypothesis; strict unchanged guard5 per placement; independent occupancy; write positions/response iff gain'}
 (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');return manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('/tmp/pipes_oracle_class_pilot_20261022'))
 args=ap.parse_args();print(json.dumps(prepare(args.out),ensure_ascii=False,separators=(',',':')))
