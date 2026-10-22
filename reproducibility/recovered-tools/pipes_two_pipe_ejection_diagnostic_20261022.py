#!/usr/bin/env python3
"""Prepare ONE bounded public15 two-pipe diagnostic; never builds/searches/runs.

Search budget is fixed at4096 candidate-pair expansions, no beam. The prepared
search driver requires a separately built exact runtime auditor. All other PID
coordinates remain unchanged. Prefix10000 and baseline-T envelope25000 apply.
"""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,re
PARENT=Path('/tmp/pipes_fixedprefix_suffix_pilot_20261022.py')
PARENT_SHA='58f4cebcdea697f05cdcd7362bd2b5baeb4af8939527cd7687dc7174cdb21b08'
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha(PARENT.read_bytes())==PARENT_SHA
spec=importlib.util.spec_from_file_location('fixed_audit_parent',PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
INDEX_SOURCE=p.ROOT/'prototypes/pipes_prefix_replan_20261020/left_moves.py'
RUNTIME_SHA='ae7e1e0a54510ee9a8d396670e2d40c2439d9286e8e13cd3ea93be8820b4c891'
CPP=r'''// Public-only two-relocation diagnostic auditor; exact production physics.
#define main included_current_runtime_main
#include "runtime_source.cpp"
#undef main
#include <fstream>
#include <sstream>
static_assert(REPLAY_GUARD==5,"unchanged guard5 required");
static const char* runtimeSha="@RUNTIME_SHA@";
static const char* inputSha="@INPUT_SHA@";
static const char* traceSha="@TRACE_SHA@";
static const char* preparedSha="@PREPARED_SHA@";
static const char* generatorSha="@GENERATOR_SHA@";
static std::string jq(const std::string&s){std::string o="\"";for(char c:s){if(c=='\\'||c=='\"')o+='\\';if(c=='\n')o+="\\n";else o+=c;}return o+"\"";}
static void need(bool c,const char*s){if(!c)throw std::runtime_error(s);}
int main(int argc,char**argv){int step=-1;
 try{
  need(argc==5,"usage: auditor prepared.in changes.txt output_base emit0or1");
  std::ifstream in(argv[1]),ch(argv[2]);const std::string outBase=argv[3];bool emit=std::string(argv[4])=="1";
  need(bool(in)&&bool(ch),"input unavailable");
  int N,K,protectedUntil,F,baselineT,target;in>>N>>K>>protectedUntil>>F>>baselineT>>target;
  need(bool(in)&&N==200000&&K==10000&&protectedUntil==25000&&baselineT==438460,"wrong prepared header");
  std::map<int,int> changes;int changeCount;ch>>changeCount;need(bool(ch)&&(changeCount==0||changeCount==2),"wrong change count");
  for(int i=0;i<changeCount;++i){int id,x;ch>>id>>x;need(bool(ch)&&id>0&&x>=0&&changes.emplace(id,x).second,"bad relocation row");}
  int extra;need(!(ch>>extra),"trailing changes");
  Allocator a;a.emit=false;
  std::vector<unsigned char> occ;
  std::vector<std::pair<int,int>> pipes{{0,0}};
  std::vector<int>commands(N),positions(N),digs(N);
  int pid=0,auditT=0,actualChanged=0,targetOldT=-1,targetMinimumT=-1;bool targetHasFit=false;
  long long V=0,peak=0;bool prefixExact=true,envelope=true;
  for(step=0;step<N;++step){
   int c,baseX,baseDigs,baseReplyX,baseT;in>>c>>baseX>>baseDigs>>baseReplyX>>baseT;
   need(bool(in)&&c!=0,"invalid prepared command");commands[step]=c;
   if(c>0){
    ++pid;int x=baseX;auto m=changes.find(pid);if(m!=changes.end()){x=m->second;need(step>=K,"relocated frozen PID");need(x!=baseX,"unchanged relocation");++actualChanged;}
    if(pid==target){
     targetOldT=a.T;targetHasFit=a.sizes.lower_bound({c,-1})!=a.sizes.end();
     int fallback=a.bf(c);targetMinimumT=a.T+20*std::max(0,(fallback+c-a.T+19)/20);
    }
    need(a.fits(x,c),"placement overlap/outside physical gap");
    need(boundedReplay(a,x,c),"strict guard5 rejection");
    int nt=std::max(auditT,20*((x+c+19)/20));need(x>=0&&x+c<=100000000,"coordinate outside protocol");
    occ.resize(std::size_t(nt),0);
    for(int j=x;j<x+c;++j)need(occ[j]==0,"independent overlap");
    for(int j=x;j<x+c;++j)occ[j]=1;
    pipes.push_back({x,c});V+=c;peak=std::max(peak,V);
    int oldT=a.T;a.place(c,x);need(a.T==nt&&a.pipes.back()==pipes.back(),"physical/audit placement differs");
    auditT=nt;positions[step]=x;digs[step]=(a.T-oldT)/20;
   }else{
    int id=-c;need(id>0&&id<int(pipes.size())&&pipes[id].second>0,"independent bad deletion");
    auto z=pipes[id];need(a.pipes.at(id)==z,"physical/audit deletion differs");
    for(int j=z.first;j<z.first+z.second;++j)need(occ[j]==1,"independent deletion missing occupancy");
    for(int j=z.first;j<z.first+z.second;++j)occ[j]=0;
    V-=z.second;pipes[id].second=0;positions[step]=z.first;digs[step]=-1;a.remove(id);
   }
   need(a.T==auditT&&a.volume==V&&a.peakVolume==peak,"independent physics differs");
   if(changeCount==0)need(positions[step]==baseReplyX&&(c<0||digs[step]==baseDigs)&&a.T==baseT,"baseline response/trench differs");
   if(step<K){prefixExact=prefixExact&&positions[step]==baseReplyX&&(c<0||digs[step]==baseDigs);need(prefixExact,"fixed prefix response differs");}
   if(step<protectedUntil){envelope=envelope&&a.T<=baseT;need(envelope,"protected T envelope exceeded");}
   // For every unselected positive PID its coordinate is copied literally.
   if(c>0&&changes.count(pid)==0)need(positions[step]==baseX,"unselected PID moved");
  }
  need(!(in>>extra),"trailing prepared data");need(actualChanged==changeCount,"relocation PID absent");
  need(V==F&&std::count(occ.begin(),occ.end(),static_cast<unsigned char>(1))==F,"wrong final occupancy");
  const bool gain=a.T<baselineT;
  if(changeCount==0)need(a.T==baselineT,"baseline T differs");
  if(emit&&gain){
   need(!std::ifstream(outBase+".positions.txt").good()&&!std::ifstream(outBase+".response.txt").good(),"output already exists");
   std::ofstream ps(outBase+".positions.txt"),rs(outBase+".response.txt");need(bool(ps)&&bool(rs),"cannot create improving outputs");
   for(int t=0;t<N;++t)if(commands[t]>0){ps<<positions[t]<<'\n';rs<<digs[t]<<' '<<positions[t]<<'\n';}else rs<<positions[t]<<'\n';
   ps.close();rs.close();need(bool(ps)&&bool(rs),"cannot finish improving outputs");
  }
  std::cout.precision(17);
  std::cout<<"{\"status\":\"ok\",\"finalT\":"<<a.T<<",\"baselineT\":"<<baselineT<<",\"gain\":"<<(gain?"true":"false")
   <<",\"changed_PIDs\":"<<actualChanged<<",\"prefixexact\":true,\"envelope25000\":true,\"guard5_every_placement\":true,\"independent_occupancy\":true"
   <<",\"target_preT\":"<<targetOldT<<",\"target_has_fit\":"<<(targetHasFit?"true":"false")<<",\"target_minimumT\":"<<targetMinimumT
   <<",\"weighted_Open15_delta\":"<<10.0*F*(1.0/a.T-1.0/baselineT)
   <<",\"runtime_sha256\":"<<jq(runtimeSha)<<",\"public_input_sha256\":"<<jq(inputSha)<<",\"trace_sha256\":"<<jq(traceSha)
   <<",\"prepared_sha256\":"<<jq(preparedSha)<<",\"generator_sha256\":"<<jq(generatorSha)
   <<",\"positions_file\":"<<(emit&&gain?jq(outBase+".positions.txt"):"null")<<",\"response_file\":"<<(emit&&gain?jq(outBase+".response.txt"):"null")<<"}\n";
  return 0;
 }catch(const std::exception&e){std::cout<<"{\"status\":\"invalid\",\"step0\":"<<step<<",\"error\":"<<jq(e.what())<<"}\n";return 2;}
}
'''
SEARCH=r'''#!/usr/bin/env python3
"""Run the fixed4096-pair public-only diagnostic using an already-built auditor.

No compilation, solver submission or production mutation. Static geometry uses
exact existing IntervalIndex; full unchanged C++ physics validates every pair.
This is a bounded two-relocation neighborhood, not beam or global optimization.
"""
from pathlib import Path
import argparse,ast,bisect,hashlib,json,subprocess,tempfile
from typing import Iterable
BUDGET=4096
SEED_CAP=64
EDGES_PER_BLOCKER_CAP=64
HERE=Path(__file__).resolve().parent
INDEX=Path('@INDEX_SOURCE@')
INDEX_SHA='@INDEX_SHA@'
def sha(x):return hashlib.sha256(x).hexdigest()
def load_index():
 raw=INDEX.read_bytes();assert sha(raw)==INDEX_SHA,'pinned IntervalIndex changed'
 tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='IntervalIndex'];assert len(nodes)==1
 ns={'bisect':bisect,'Iterable':Iterable};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(INDEX),'exec'),ns);return ns['IntervalIndex']
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--auditor',type=Path,required=True);ap.add_argument('--out-base',type=Path,default=HERE/'trial');args=ap.parse_args()
 manifest=json.loads((HERE/'manifest.json').read_text());data=(HERE/'prepared.in').read_bytes();assert sha(data)==manifest['hashes']['PREPARED_SHA']
 assert sha(args.auditor.parent.joinpath('runtime_source.cpp').read_bytes())==manifest['hashes']['RUNTIME_SHA']
 lines=data.decode().splitlines();N,K,protect,F,baseT,target=map(int,lines[0].split());rows=[tuple(map(int,l.split()))for l in lines[1:]];assert len(rows)==N
 birth=[-1];death=[N];length=[0];pos=[-1];pid=0;Tbefore=[0]*N;baseTrace=[]
 for t,(c,x,d,rx,T)in enumerate(rows):
  Tbefore[t]=baseTrace[-1]if baseTrace else 0;baseTrace.append(T)
  if c>0:pid+=1;birth.append(t);death.append(N);length.append(c);pos.append(x)
  else:death[-c]=t
 assert target==max(range(1,pid+1),key=lambda i:(pos[i]+length[i],i))
 IntervalIndex=load_index();spatial=IntervalIndex([(pos[i],pos[i]+length[i],i)for i in range(1,pid+1)])
 temporal=IntervalIndex([(birth[i],death[i],i)for i in range(1,pid+1)])
 def alive(i,t):return birth[i]<t<death[i]
 def overlaps_life(i,j):return max(birth[i],birth[j])<min(death[i],death[j])
 def conflicts(i,x,ignore):
  for j in spatial.query(x,x+length[i]):
   if j not in ignore and overlaps_life(i,j):return True
  return False
 def at_birth(i):
  t=birth[i];v=[(pos[j],pos[j]+length[j],j)for j in temporal.query(t,t+1)if j!=i and alive(j,t)];v.sort();return v
 def baseline_edges(i):
  v=at_birth(i);T=Tbefore[birth[i]];gaps=[];left=0
  for l,r,j in v:
   assert l>=left,'baseline active geometry overlaps'
   if l>left:gaps.append((left,l))
   left=r
  if left<T:gaps.append((left,T))
  edges=set()
  for l,r in gaps:
   if r-l>=length[i]:edges.update((l,r-length[i]))
  if not edges:
   tail=left
   if gaps and gaps[-1][1]==T:tail=gaps[-1][0]
   nt=T+20*max(0,(tail+length[i]-T+19)//20);edges.update((tail,nt-length[i]))
  return sorted(x for x in edges if x!=pos[i] and x>=0 and x+length[i]<=baseT-20)[:EDGES_PER_BLOCKER_CAP]
 with tempfile.TemporaryDirectory(prefix='pipes-ejection-')as td:
  changePath=Path(td)/'changes.txt'
  def audit(changes,emit=False):
   changePath.write_text(str(len(changes))+'\n'+''.join(f'{i} {x}\n'for i,x in sorted(changes.items())))
   proc=subprocess.run([str(args.auditor.resolve()),str(HERE/'prepared.in'),str(changePath),str(args.out_base.resolve()),str(int(emit))],capture_output=True,text=True)
   try:r=json.loads(proc.stdout)
   except Exception as e:raise RuntimeError('auditor returned non-JSON: '+proc.stdout[:200]+proc.stderr[:200])from e
   if proc.returncode not in (0,2):raise RuntimeError('auditor crashed: '+proc.stderr[:200])
   assert(proc.returncode==0)==(r.get('status')=='ok');return r
  baseline=audit({})
  if baseline.get('status')!='ok':
   print(json.dumps({'status':'baseline_invalid','baseline_audit':baseline,'expansions':0,'budget':BUDGET,'search_started':False}));return 2
  assert baseline['finalT']==baseT
  # Explicit prestate evidence; absence of a fit is not inferred from final holes.
  baselineTarget={'preT':baseline['target_preT'],'has_fit':baseline['target_has_fit'],'minimumT':baseline['target_minimumT']}
  if birth[target]<K:print(json.dumps({'status':'target_frozen','baseline_audit':baseline,'expansions':0}));return 0
  active=at_birth(target);seeds=set();T=Tbefore[birth[target]];targetLen=length[target]
  # Remove exactly one baseline-active blocker; adjacent intervals determine the
  # only new merged physical gap. Both endpoints are candidates, never interiors.
  for k,(l,r,blocker)in enumerate(active):
   if birth[blocker]<K:continue
   left=active[k-1][1]if k else 0;right=active[k+1][0]if k+1<len(active)else T
   if right-left>=targetLen:
    for x in (left,right-targetLen):
     if x!=pos[target]and x>=0 and x+targetLen<=baseT-20:seeds.add((x,blocker))
   elif k+1==len(active):
    nt=T+20*max(0,(left+targetLen-T+19)//20)
    for x in (left,nt-targetLen):
     if x!=pos[target]and x>=0 and x+targetLen<=baseT-20:seeds.add((x,blocker))
  # Lifetime collision with any third unchanged PID rules out this fixed pair.
  # Neighborhood fixed before execution: first64 geometry-feasible seeds by
  # (target coordinate, blocker PID), first64 alternate blocker edges by address.
  # Thus <=64*64=4096 pairs; seed/edge caps are NOT impossibility bounds.
  validSeeds=[];seedChecks=0
  for x,b in sorted(seeds):
   seedChecks+=1
   if not conflicts(target,x,{target,b}):validSeeds.append((x,b))
   if len(validSeeds)==SEED_CAP:break
  endpointLeaders=sorted(((pos[j]+length[j],j)for j in range(1,pid+1)),reverse=True)[:3]
  cache={};streams=[]
  for x,b in validSeeds:
   if b not in cache:cache[b]=baseline_edges(b)
   streams.append((x,b,iter(cache[b])))
  expansions=0;futureRejected=0;boundRejected=0;audits=0;invalid=0;reasons={};bestT=baseT;best=None
  # Round-robin gives every deterministic seed a chance within the fixed budget.
  # Pruning by closure cardinality is only neighborhood restriction, not proof.
  while streams and expansions<BUDGET:
   remaining=[]
   for tx,b,it in streams:
    if expansions>=BUDGET:break
    try:bx=next(it)
    except StopIteration:continue
    remaining.append((tx,b,it));expansions+=1
    if overlaps_life(target,b)and max(tx,bx)<min(tx+targetLen,bx+length[b]):futureRejected+=1;continue
    if conflicts(b,bx,{b,target}):futureRejected+=1;continue
    # Sound lower bound for exactly this pair: all other PID endpoints persist.
    unmoved=next(end for end,j in endpointLeaders if j not in (target,b))
    optimistic=20*((max(unmoved,tx+targetLen,bx+length[b])+19)//20)
    if optimistic>=bestT:boundRejected+=1;continue
    r=audit({target:tx,b:bx});audits+=1
    if r.get('status')!='ok':
     invalid+=1;key=r.get('error','unknown');reasons[key]=reasons.get(key,0)+1;continue
    if r['finalT']<bestT:bestT=r['finalT'];best={target:tx,b:bx}
   streams=remaining
  output=None
  if best is not None:
   output=audit(best,True);assert output['status']=='ok'and output['finalT']==bestT<baseT
  print(json.dumps({'status':'ok','scope':'bounded two-pipe diagnostic; no beam/global-optimality claim','budget':BUDGET,'expansions':expansions,'budget_exhausted':expansions==BUDGET and bool(streams),
   'target_PID':target,'target_prestate':baselineTarget,'seed_count':len(seeds),'seed_checks':seedChecks,'selected_seed_cap':SEED_CAP,'edges_per_blocker_cap':EDGES_PER_BLOCKER_CAP,'future_nonoverlap_seeds':len(validSeeds),'future_rejections':futureRejected,'endpoint_bound_rejections':boundRejected,
   'full_candidate_audits':audits,'guard_or_physics_invalid':invalid,'rejection_reasons':reasons,'baseline_audit':baseline,'baselineT':baseT,'finalT':bestT,'gain':bestT<baseT,
   'selected_changes':best,'output':output,'input_hashes':manifest['hashes'],'search_source_sha256':sha(Path(__file__).read_bytes())},separators=(',',':')))
 return 0
if __name__=='__main__':raise SystemExit(main())
'''

def prepare(destination):
 out=Path(destination).resolve();assert not out.exists(),out
 assert sha(p.RELEASE.read_bytes())==p.RELEASE_SHA
 rb=p.RUNTIME.read_bytes();assert sha(rb)==RUNTIME_SHA
 metadata=None
 for line in (p.ROOT/'prototypes/pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl').open():
  r=json.loads(line)
  if r.get('public_number')==15:metadata=r;break
 assert metadata and metadata['id']==p.PUBLIC15_ID
 ref=None
 for line in (p.ROOT/'prototypes/pipes_guard_generalization_20261022/records.jsonl').open():
  r=json.loads(line)
  if r.get('type')=='evaluation'and r.get('suite')=='archive-production'and r.get('kind')=='production'and r.get('id')==p.PUBLIC15_ID:ref=r
 assert ref and ref['status']=='ok'
 ib=Path(metadata['test_file']).read_bytes();assert sha(ib)==metadata['test_sha256']==ref['test_sha256']
 tok=ib.split();N=int(tok[1]);commands=list(map(int,tok[2:2+N]));assert N==200000 and tok[2+N:]==[b'0']
 tb=gzip.open(metadata['judge_output_file'],'rb').read();assert sha(tb)==metadata['response_sha256']==ref['response_sha256']
 trace=tb.decode().splitlines();assert len(trace)==N
 baselineT=ref['trench_length_m'];F=metadata['final_occupied_length_m'];assert baselineT==438460 and F==418757
 rows=[];T=0;pid=0;coordinates=[]
 for t,(c,line)in enumerate(zip(commands,trace)):
  v=list(map(int,line.split()))
  if c>0:assert len(v)==2;d,x=v;T+=20*d;pid+=1;coordinates.append((x+c,pid));bx=x
  else:assert len(v)==1;d,x=-1,v[0];bx=-1
  rows.append(f'{c} {bx} {d} {x} {T}\n')
 target=max(coordinates)[1];assert target==130252
 prepared=(f'{N} 10000 25000 {F} {baselineT} {target}\n'+''.join(rows)).encode()
 h={'RUNTIME_SHA':sha(rb),'INPUT_SHA':sha(ib),'TRACE_SHA':sha(tb),'PREPARED_SHA':sha(prepared),'GENERATOR_SHA':sha(Path(__file__).read_bytes())}
 cpp=CPP
 for k,v in h.items():cpp=cpp.replace('@'+k+'@',v)
 search=SEARCH.replace('@INDEX_SOURCE@',str(INDEX_SOURCE)).replace('@INDEX_SHA@',sha(INDEX_SOURCE.read_bytes()))
 assert not re.search(r'@[A-Z_]+@',cpp+search)
 out.mkdir(parents=True);(out/'runtime_source.cpp').write_bytes(rb);(out/'prepared.in').write_bytes(prepared);(out/'auditor.cpp').write_text(cpp);(out/'search.py').write_text(search)
 manifest={'schema':'pipes-two-pipe-ejection-diagnostic-v1','public_case':15,'fixed_commands':10000,'protected_T_commands':25000,'budget_pairs':4096,'seed_cap':64,'blocker_edge_cap':64,'beam':False,'baseline_T':baselineT,'F':F,'target_PID':target,
 'hashes':h,'auditor_cpp_sha256':sha(cpp.encode()),'search_py_sha256':sha(search.encode()),'IntervalIndex_source':str(INDEX_SOURCE),'IntervalIndex_sha256':sha(INDEX_SOURCE.read_bytes()),'parent_audit_sha256':PARENT_SHA,
 'build_argv':['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=5',str(out/'auditor.cpp'),'-o',str(out/'auditor')],
 'run_argv':['python3',str(out/'search.py'),'--auditor',str(out/'auditor'),'--out-base',str(out/'trial')],
 'scope':'prepare only; sole evaluator must build/run after review; exactly two relocated PIDs, fixed public baseline; write full outputs iff strict T gain'}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');return manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=Path('/tmp/pipes_two_pipe_ejection_diagnostic_20261022'))
 args=ap.parse_args();print(json.dumps(prepare(args.out),ensure_ascii=False,separators=(',',':')))
