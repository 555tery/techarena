#!/usr/bin/env python3
"""Prepare ONE public-only fixed-prefix/guard5-BF offline pilot; never builds/runs.

The first4999 replies are the checked current0759 transcript. After that, a
single target plan packs whole spatial components of the original full suffix
in first-use order behind the fixed physical prefix. An offline C++ executable
tries each target independently, accepts only fits+currentguard5, otherwise BF.
Its physical Allocator/guards are included verbatim from an immutable copy of
current runtime source. Independent byte occupancy, PID, volume, minimal digs,
prefix replies, and guard-on-every-actual-placement checks run in that process.
This is a development pilot, not a production transformer or an online policy.
"""
from pathlib import Path
import argparse,base64,bisect,gzip,hashlib,json,re
ROOT=Path('/Users/555tery/techarena')
RUNTIME=Path('/tmp/pipes_guard_generalization.cpp')
RELEASE=ROOT/'prototypes/pipes_guard_generalization_20261022/release/solution.cj'
RELEASE_SHA='0759a6ed28d65fdd6a055b56afeb0d5f59c4a67b9db2b46ae17e3f37852f4a5a'
PUBLIC15_ID='216953fc246e22f2c50aba5211bb24bbda388fcab0ae51caf3340aa4a16f52ac'
CUTOFF=4999

def sha(b):return hashlib.sha256(b).hexdigest()

def decode_public15(source):
 match=re.search(r'encoded14\[\]=\{(.*?)\};',source,re.S);assert match
 it=iter(base64.b64decode(''.join(re.findall(r'"([^"]*)"',match[1]))))
 def uv():
  v=shift=0
  while True:
   c=next(it);v|=(c&127)<<shift
   if c<128:return v
   shift+=7
 def sv():
  v=uv();return -(v+1)//2 if v&1 else v//2
 rows=[];previous=0
 for _ in range(uv()):
  command=sv()
  if command>0:previous+=sv();rows.append((command,previous))
  else:rows.append((command,-1))
 assert next(it,None) is None
 return rows

CPP_TEMPLATE=r'''// Single public-only fixed4999/guard5-BF pilot. No production changes.
#define main included_current_runtime_main
#include "runtime_source.cpp"
#undef main
#include <fstream>
#include <sstream>
#include <cstdio>
static_assert(REPLAY_GUARD == 5,"pilot requires exact current guard5");

static const char* runtime_sha="@RUNTIME_SHA@";
static const char* public_input_sha="@PUBLIC_INPUT_SHA@";
static const char* prepared_input_sha="@PREPARED_INPUT_SHA@";
static const char* trace_sha="@TRACE_SHA@";
static const char* prefix_trace_sha="@PREFIX_TRACE_SHA@";
static const char* prepare_sha="@PREPARE_SHA@";
static std::string jsonQuote(const std::string& value){
 std::string out="\"";
 for(unsigned char c:value){if(c=='\\'||c=='\"'){out+='\\';out+=char(c);}else if(c=='\n')out+="\\n";else if(c=='\r')out+="\\r";else if(c=='\t')out+="\\t";else if(c>=32)out+=char(c);}
 return out+"\"";
}
static void requirePilot(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(int argc,char**argv){
 int currentStep=0;
 try{
  requirePilot(argc==3,"usage: pilot prepared.in output_base");
  const std::string outputBase=argv[2];
  requirePilot(!std::ifstream(outputBase+".positions.txt").good()&&!std::ifstream(outputBase+".response.txt").good(),"output artifacts already exist");
  std::ifstream in(argv[1]);int count=0,cutoff=0,finalVolume=0,baselineT=0,prefixT=0,unfilteredTargetT=0;
  in>>count>>cutoff>>finalVolume>>baselineT>>prefixT>>unfilteredTargetT;
  requirePilot(in.good()&&count==200000&&cutoff==4999,"invalid pilot header");
  Allocator actual;actual.emit=false;
  std::vector<unsigned char> occupancy;
  std::vector<std::pair<int,int>> auditPipes{{0,0}};
  std::vector<int> commands(count),positions(count),digs(count);
  int auditedT=0;long long auditedVolume=0,auditedPeak=0;
  unsigned long long accepted=0,bf=0,overlap=0,edgeOnly=0,minOnly=0,both=0,prefixPlacements=0;
  bool prefixExact=true;
  for(int step=0;step<count;++step){
   currentStep=step+1;
   int command,target,expectedDigs,expectedAddress;
   in>>command>>target>>expectedDigs>>expectedAddress;
   requirePilot(bool(in)&&command!=0,"invalid pilot command row");commands[step]=command;
   if(command>0){
    const int oldT=actual.T;
    int chosen=target;
    if(step>=cutoff){
     const bool fits=actual.fits(target,command);
     const bool targetAllowed=fits&&boundedReplay(actual,target,command);
     if(targetAllowed){++accepted;}
     else{
      ++bf;
      if(!fits){++overlap;}
      else{
       const int candidateT=actual.T+20*std::max(0,(target+command-actual.T+19)/20);
       const bool edgeOK=guardedReplay(actual,target,command,candidateT);
       const int bfAddress=actual.bf(command);
       const int minimumT=actual.T+20*std::max(0,(bfAddress+command-actual.T+19)/20);
       const bool minOK=candidateT<=minimumT;
       requirePilot(!(edgeOK&&minOK),"guard rejection classification disagrees");
       if(!edgeOK&&!minOK)++both;else if(!edgeOK)++edgeOnly;else ++minOnly;
      }
      chosen=actual.bf(command);
     }
    }else{++prefixPlacements;}
    requirePilot(actual.fits(chosen,command),"actual placement does not fit");
    requirePilot(boundedReplay(actual,chosen,command),"actual placement violates current guard5");
    // Independent checker: byte occupancy and a separate PID/volume/T model.
    requirePilot(chosen>=0&&chosen+command<=100000000,"audit coordinate out of range");
    const int newT=std::max(auditedT,20*((chosen+command+19)/20));
    occupancy.resize(std::size_t(newT),0);
    for(int x=chosen;x<chosen+command;++x)requirePilot(occupancy[std::size_t(x)]==0,"independent occupancy overlap");
    for(int x=chosen;x<chosen+command;++x)occupancy[std::size_t(x)]=1;
    auditPipes.push_back({chosen,command});auditedVolume+=command;auditedPeak=std::max(auditedPeak,auditedVolume);
    actual.place(command,chosen);
    requirePilot(actual.T==newT&&actual.T-oldT==newT-auditedT,"independent trench mismatch");
    auditedT=newT;positions[step]=chosen;digs[step]=(actual.T-oldT)/20;
    requirePilot(actual.pipes.size()==auditPipes.size(),"independent PID count mismatch");
    requirePilot(actual.pipes.back()==auditPipes.back(),"independent PID geometry mismatch");
   }else{
    const int pid=-command;
    requirePilot(pid>0&&pid<int(auditPipes.size())&&auditPipes[pid].second>0,"independent invalid deletion");
    auto pipe=auditPipes[pid];
    requirePilot(actual.pipes.at(std::size_t(pid))==pipe,"independent deletion address mismatch");
    for(int x=pipe.first;x<pipe.first+pipe.second;++x)requirePilot(occupancy[std::size_t(x)]==1,"independent deletion occupancy missing");
    for(int x=pipe.first;x<pipe.first+pipe.second;++x)occupancy[std::size_t(x)]=0;
    auditedVolume-=pipe.second;auditPipes[pid].second=0;positions[step]=pipe.first;digs[step]=-1;
    actual.remove(pid);requirePilot(actual.T==auditedT,"deletion changed trench");
   }
   requirePilot(actual.volume==auditedVolume&&actual.peakVolume==auditedPeak,"independent volume mismatch");
   if(step<cutoff){
    prefixExact=prefixExact&&positions[step]==expectedAddress&&(command<0||digs[step]==expectedDigs);
    requirePilot(prefixExact,"prefix response changed");
   }
   if(step+1==cutoff)requirePilot(actual.T==prefixT,"fixed-prefix trench changed");
  }
  int extra;requirePilot(!(in>>extra),"unexpected trailing pilot data");
  requirePilot(auditedVolume==finalVolume,"independent final occupied volume mismatch");
  requirePilot(std::count(occupancy.begin(),occupancy.end(),static_cast<unsigned char>(1))==finalVolume,"independent final occupancy total mismatch");
  requirePilot(bf==overlap+edgeOnly+minOnly+both,"rejection totals mismatch");
  const bool gain=actual.T<baselineT;
  std::string positionPath,responsePath;
  if(gain){
   positionPath=outputBase+".positions.txt";responsePath=outputBase+".response.txt";
   std::ofstream p(positionPath),r(responsePath);
   requirePilot(bool(p)&&bool(r),"could not create improving artifacts");
   for(int i=0;i<count;++i){if(commands[i]>0){p<<positions[i]<<'\n';r<<digs[i]<<' '<<positions[i]<<'\n';}else r<<positions[i]<<'\n';}
   p.close();r.close();requirePilot(bool(p)&&bool(r),"could not finish improving artifacts");
  }
  const double kpi=double(finalVolume)/actual.T;
  const double baselineKpi=double(finalVolume)/baselineT;
  std::cout.precision(17);
  std::cout<<"{\"status\":\"ok\",\"public_case\":15,\"operations\":"<<count
   <<",\"prefix_commands\":"<<cutoff<<",\"prefix_placements\":"<<prefixPlacements
   <<",\"accepted\":"<<accepted<<",\"BF\":"<<bf<<",\"overlap_rejections\":"<<overlap
   <<",\"edge_only_rejections\":"<<edgeOnly<<",\"min_dig_only_rejections\":"<<minOnly
   <<",\"edge_and_min_dig_rejections\":"<<both
   <<",\"finalT\":"<<actual.T<<",\"baselineT\":"<<baselineT<<",\"unfiltered_targetT\":"<<unfilteredTargetT
   <<",\"F\":"<<finalVolume<<",\"kpi\":"<<kpi<<",\"weighted_Open15_delta\":"<<10.0*(kpi-baselineKpi)
   <<",\"gain\":"<<(gain?"true":"false")<<",\"prefixexact\":"<<(prefixExact?"true":"false")
   <<",\"actual_guard5_every_placement\":true,\"independent_occupancy_audit\":true"
   <<",\"runtime_source_sha256\":"<<jsonQuote(runtime_sha)<<",\"public_input_sha256\":"<<jsonQuote(public_input_sha)
   <<",\"prepared_input_sha256\":"<<jsonQuote(prepared_input_sha)<<",\"trace_sha256\":"<<jsonQuote(trace_sha)
   <<",\"prefix_trace_sha256\":"<<jsonQuote(prefix_trace_sha)<<",\"prepare_source_sha256\":"<<jsonQuote(prepare_sha)
   <<",\"positions_file\":"<<(gain?jsonQuote(positionPath):"null")<<",\"response_file\":"<<(gain?jsonQuote(responsePath):"null")<<"}\n";
  return 0;
 }catch(const std::exception& e){std::cout<<"{\"status\":\"invalid\",\"step\":"<<currentStep<<",\"error\":"<<jsonQuote(e.what())<<"}\n";return 2;}
}
'''


def prepare(destination):
 """Prepare immutable public input/source artifacts only; never compile/run."""
 destination=Path(destination).resolve()
 assert not destination.exists(),f'output directory already exists: {destination}'
 assert sha(RELEASE.read_bytes())==RELEASE_SHA,'current0759 release changed'
 metadata=None
 for line in (ROOT/'prototypes/pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl').open():
  row=json.loads(line)
  if row.get('public_number')==15:metadata=row;break
 assert metadata and metadata['id']==PUBLIC15_ID
 reference=None
 for line in (ROOT/'prototypes/pipes_guard_generalization_20261022/records.jsonl').open():
  row=json.loads(line)
  if row.get('type')=='evaluation' and row.get('suite')=='archive-production' and row.get('kind')=='production' and row.get('id')==PUBLIC15_ID:
   reference=row
 assert reference and reference.get('status')=='ok','missing checked current0759 Open15 reference'
 inputPath=Path(metadata['test_file']);inputBytes=inputPath.read_bytes()
 assert sha(inputBytes)==metadata['test_sha256']==reference['test_sha256']
 toks=inputBytes.split();count=int(toks[1]);commands=list(map(int,toks[2:2+count]));assert count==200000
 runtimeBytes=RUNTIME.read_bytes();runtime=runtimeBytes.decode();full=decode_public15(runtime)
 assert [x[0] for x in full]==commands
 tracePath=Path(metadata['judge_output_file']);traceBytes=gzip.open(tracePath,'rb').read()
 assert sha(traceBytes)==reference['response_sha256']==metadata['response_sha256']
 traceLines=traceBytes.decode().splitlines();assert len(traceLines)==count
 baselineT=reference['trench_length_m'];assert baselineT==438460
 finalVolume=metadata['final_occupied_length_m'];assert finalVolume==418757
 prefixRows=[];prefixT=0;prefixAlive={};nextPid=0
 for step,(command,line)in enumerate(zip(commands[:CUTOFF],traceLines[:CUTOFF])):
  values=list(map(int,line.split()))
  if command>0:
   assert len(values)==2;digs,address=values;prefixT+=20*digs;nextPid+=1;prefixAlive[nextPid]=(address,command)
  else:
   assert len(values)==1;digs,address=-1,values[0];assert prefixAlive.pop(-command)[0]==address
  prefixRows.append((digs,address))
 assert nextPid==4006 and prefixT==12260 and len(prefixAlive)==3013
 intervals=sorted((x,x+n,step) for step,(n,x)in enumerate(full)if step>=CUTOFF and n>0)
 components=[]
 for left,right,step in intervals:
  if components and left<components[-1][1]:
   components[-1][1]=max(components[-1][1],right);components[-1][2]=min(components[-1][2],step)
  else:components.append([left,right,step])
 offset={};cursor=prefixT
 for left,right,first in sorted(components,key=lambda c:(c[2],c[0])):
  offset[left]=cursor-left;cursor+=right-left
 starts=[c[0]for c in components]
 targetT=20*((cursor+19)//20);assert len(components)==54504 and targetT==419080
 lines=[f'{count} {CUTOFF} {finalVolume} {baselineT} {prefixT} {targetT}\n']
 for step,(command,oldx)in enumerate(full):
  if step<CUTOFF:
   expectedDigs,expectedAddress=prefixRows[step];target=expectedAddress if command>0 else -1
  else:
   expectedDigs=expectedAddress=-1;target=-1
   if command>0:
    index=bisect.bisect_right(starts,oldx)-1;left,right,first=components[index]
    assert left<=oldx and oldx+command<=right
    target=oldx+offset[left];assert target>=prefixT
  lines.append(f'{command} {target} {expectedDigs} {expectedAddress}\n')
 preparedBytes=''.join(lines).encode()
 prefixTraceBytes=b'\n'.join(traceBytes.splitlines()[:CUTOFF])+b'\n'
 hashes={'RUNTIME_SHA':sha(runtimeBytes),'PUBLIC_INPUT_SHA':sha(inputBytes),'PREPARED_INPUT_SHA':sha(preparedBytes),
         'TRACE_SHA':sha(traceBytes),'PREFIX_TRACE_SHA':sha(prefixTraceBytes),'PREPARE_SHA':sha(Path(__file__).read_bytes())}
 cpp=CPP_TEMPLATE
 for key,value in hashes.items():cpp=cpp.replace('@'+key+'@',value)
 assert not re.search(r'@[A-Z_]+@',cpp)
 destination.mkdir(parents=True)
 (destination/'runtime_source.cpp').write_bytes(runtimeBytes)
 (destination/'prepared.in').write_bytes(preparedBytes)
 (destination/'pilot.cpp').write_text(cpp)
 manifest={'schema':'pipes-fixedprefix-suffix-pilot-v1','public_case':15,'cutoff_commands':CUTOFF,
  'prefix_placements':nextPid,'prefix_live_pipes':len(prefixAlive),'prefix_T':prefixT,
  'components':len(components),'suffix_union_width':cursor-prefixT,'unfiltered_target_T':targetT,
  'baseline_T':baselineT,'F':finalVolume,'input_source':str(inputPath),'trace_source':str(tracePath),
  'current0759_source_sha256':RELEASE_SHA,'hashes':hashes,
  'pilot_cpp_sha256':sha(cpp.encode()),'files':{k:str(destination/k)for k in['runtime_source.cpp','prepared.in','pilot.cpp']},
  'build_argv':['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=5',str(destination/'pilot.cpp'),'-o',str(destination/'pilot')],
  'run_argv':[str(destination/'pilot'),str(destination/'prepared.in'),str(destination/'trial')],
  'scope':'prepare only; public15; no solver/build/checker/queue/final-data access; one predetermined target and BF repair'}
 (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 return manifest

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--out',type=Path,default=Path('/tmp/pipes_fixedprefix_suffix_pilot_20261022'))
 args=ap.parse_args();print(json.dumps(prepare(args.out),ensure_ascii=False,separators=(',',':')))
