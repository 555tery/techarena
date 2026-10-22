from pathlib import Path
from types import SimpleNamespace
import base64,hashlib,json,math,os,re,statistics,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp');import pipes_o0_evaluate_20261022 as ev
R=Path('/Users/555tery/techarena');E=R/'prototypes/pipes_guard_generalization_20261022';OLD=R/'prototypes/pipes_online_reservations_20261022';REC=E/'records.jsonl';(E/'bin').mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def rows():return [json.loads(s)for s in REC.open()]if REC.exists()else []
def record(r):
 with REC.open('a')as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
FROZEN={r['id']:r for r in map(json.loads,(OLD/'records.jsonl').open())if r['type']=='evaluation'and r.get('suite')=='regression'and r.get('kind')=='cj-release'}
assert len(FROZEN)==2661
KINDS={'full':(0,0),'lazy-full':(1,0),'cautious':(1,1),'local':(1,2),'volume':(1,3),'online':(1,4),'edge-local':(1,5),'edge-volume':(1,6)}
EVAL_CACHE={(r['suite'],r['kind'],r['id'],r['binary_sha256']):r for r in rows()if r['type']=='evaluation'}
def source_build():
 path=Path('/tmp/pipes_reservations_dev.cpp');code=path.read_text();patches=[]
 def patch(a,b):
  nonlocal code
  assert code.count(a)==1,(a[:100],code.count(a));code=code.replace(a,b);patches.append([a,b])
 patch('#define CAUTIOUS_HYBRID 0','#define CAUTIOUS_HYBRID (REPLAY_GUARD == 1)')
 patch('''            if (tailPlacement && !cohortSlabExpanded) {
                const std::int64_t missing = cohortSlabEnd - trenchLength;''','''            if (tailPlacement && (LAZY_SLAB || !cohortSlabExpanded)) {
                const std::int64_t requiredEnd = LAZY_SLAB ? start + length : cohortSlabEnd;
                const std::int64_t missing = requiredEnd - trenchLength;''')
 patch('''                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);''','''                if (digs > 0 && occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);''')
 patch('''const auto deletedEnd = cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n;''','''const auto deletedEnd = LAZY_SLAB ? std::min(trenchLength,cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n) : cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n;''')
 patch('''const auto survivorEnd = cohortSlabBase + std::int64_t(cohortSlabTailPipeCount) * n;''','''const auto survivorEnd = LAZY_SLAB ? std::min(trenchLength,cohortSlabBase + std::int64_t(cohortSlabTailPipeCount) * n) : cohortSlabBase + std::int64_t(cohortSlabTailPipeCount) * n;''')
 patch(''' bool emit=true; int T=0;map<int,int>g;''',''' bool emit=true; int T=0;long long volume=0,peakVolume=0;map<int,int>g;''')
 patch(''' void place(int n,int x){int digs=''', ''' void place(int n,int x){volume+=n;peakVolume=max(peakVolume,volume);int digs=''')
 patch('''auto p=pipes[id];add(p.first,p.first+p.second);pipes[id].second=0;''','''auto p=pipes[id];volume-=p.second;add(p.first,p.first+p.second);pipes[id].second=0;''')
 patch('''int main(){
 try{''','''bool boundedReplay(const Allocator& a,int x,int n){
 const int newT=a.T+20*max(0,(x+n-a.T+19)/20);
 if(REPLAY_GUARD==2){
  int minimum=a.T;
  if(a.sizes.lower_bound({n,-1})==a.sizes.end()){
   int tail=a.T;
   if(!a.g.empty()&&prev(a.g.end())->second==a.T)tail=prev(a.g.end())->first;
   minimum+=20*max(0,(tail+n-a.T+19)/20);
  }
  return newT<=minimum;
 }
 if(REPLAY_GUARD==3)return newT<=20*((max(a.peakVolume,a.volume+n)+19)/20);
 return true;
}
int main(){
 try{
  if(REPLAY_GUARD==4){
   fallback_online::Allocator core;int command;
   while(fastio::readInteger(command)&&command!=0){if(command>0)core.place(command);else core.remove(-std::int64_t(command));}
   cerr<<"pure_online T="<<core.trenchLength<<'\\n';return 0;
  }''')
 patch('''(!CAUTIOUS_HYBRID||c<0||guardedReplay(*physical,address,c,int(shadow->trenchLength)));''','''(!CAUTIOUS_HYBRID||c<0||guardedReplay(*physical,address,c,int(shadow->trenchLength)))&&
     (c<0||boundedReplay(*physical,address,c));''')
 cpp=Path('/tmp/pipes_guard_generalization.cpp');cpp.write_text(code)
 record(dict(type='protocol',base_cpp=str(path),base_cpp_sha256=sha(path.read_bytes()),base_cj=str(OLD/'solution.cj'),base_cj_sha256=sha((OLD/'solution.cj').read_bytes()),cpp_sha256=sha(code.encode()),patches=patches,candidates=KINDS,core_gate='lazy-full vs full: calibration ordinary/series/motif means >=0, interruption >=0, min>=-0.02; archive macro >=0 and min>=-0.02; causal no parameter search',policy_choice='minimax total-contest-score regret across provenance ordinary465, archive-long>=100k, archive-short<=200, directed150, new ordinary+series+motif calibration, and all archive nonpublic. Bonus exact expected top2 of4 without replacement, each pool >=11. Tie within0.02 total points prefers cautious, then local, volume, online, full. No threshold tuning after final. Core may be rejected separately.',final_gate='selected vs same policy with frozen old core and vs full baseline: validity/resources required, ordinary/series/motif mean not lower than same-policy old-core by0.002, interruption mean >=0, same-policy min>=-0.02. Policy risk evaluated by full score and worst losses, not assume full dominates.',target='Cangjie1.0.5 -O0; process CPU user+system5s,RSS256MiB,one worker; M1 measurements not Windows/G5420',no_platform=True))
 for k,(lazy,guard)in list(KINDS.items())[:6]:
  b=E/'bin'/k
  q=subprocess.run(['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1',f'-DLAZY_SLAB={lazy}',f'-DREPLAY_GUARD={guard}',str(cpp),'-o',str(b)],capture_output=True,text=True)
  record(dict(type='build',kind=k,cpp_sha256=sha(cpp.read_bytes()),binary_sha256=sha(b.read_bytes())if q.returncode==0 else None,status=q.returncode,stderr=q.stderr[-2000:]))
  assert q.returncode==0,q.stderr
  print('BUILT',k,flush=True)

def inputs(split):return [r for r in map(json.loads,(E/'input_manifest.jsonl').open())if r.get('type')=='input'and r['split']==split]
def batch(m,kind,suite):
 b=E/'bin'/kind;data=Path(m['test_file']).read_bytes();assert sha(data)==m['test_sha256'];tokens=data.split();n=m['operation_count'];assert int(tokens[1])==n
 stream=b'\n'.join(tokens[2:2+n])+b'\n0\n';bsha=sha(b.read_bytes())
 key=(suite,kind,m['id'],bsha)
 if key in EVAL_CACHE:return EVAL_CACHE[key]
 with tempfile.TemporaryDirectory(prefix='pipes-guard-')as temp:
  d=Path(temp);(d/'commands').write_bytes(stream)
  with(d/'commands').open('rb')as fi,(d/'out').open('wb')as fo,(d/'err').open('wb')as fe:
   proc=subprocess.Popen([str(b)],stdin=fi,stdout=fo,stderr=fe,env={**os.environ,'cjProcessorNum':'1'});_,status,u=os.wait4(proc.pid,0);proc.returncode=os.waitstatus_to_exitcode(status)
  assert proc.returncode==0,(m['id'],kind,(d/'err').read_text()[-1000:])
  outputsha=sha((d/'out').read_bytes());ref=FROZEN.get(m['id']);validation='full_response_parity';detail=''
  if ref and ref['response_sha256']==outputsha:trench=ref['trench_length_m'];kpi=ref['kpi']
  else:
   validation='official_checker_on_complete_response';(d/'empty').write_text('')
   with(d/'out').open('rb')as fi:
    q=subprocess.run([str(ev.EXP/'bin/official-offline'),m['test_file'],str(d/'checked'),str(d/'empty'),str(d/'report')],stdin=fi,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=d)
   text=q.stderr.decode();match=ev.h.SCORE_RE.search(text);assert q.returncode==0 and match,(m['id'],kind,text[-1200:])
   occupied,trench=int(match[1]),int(match[2]);assert occupied==m['final_occupied_length_m'];kpi=occupied/trench
  rec=dict(type='evaluation',suite=suite,kind=kind,id=m['id'],family=m.get('family'),stratum=m.get('stratum'),operation_count=n,test_sha256=m['test_sha256'],binary_sha256=bsha,response_sha256=outputsha,kpi=kpi,trench_length_m=trench,weight=m.get('weight',1.),status='ok',validation=validation,solver_cpu_total_s=u.ru_utime+u.ru_stime,solver_peak_rss_mb=u.ru_maxrss/1048576,candidate_stderr=(d/'err').read_text()[-1200:],resource_scope='batch dev only; final Cj resources official interactive')
  record(rec);EVAL_CACHE[key]=rec;return rec

def panel(split,kinds):
 ms=inputs(split)
 for i,m in enumerate(ms):
  for k in(kinds if i%2==0 else kinds[::-1]):batch(m,k,split)
  if(i+1)%4==0 or i+1==len(ms):print('PANEL',split,i+1,len(ms),flush=True)

def old_core():
 for i,m in enumerate(ev.rows):
  batch(m,'lazy-full','archive-core')
  if(i+1)%128==0 or i+1==len(ev.rows):print('CORE',i+1,len(ev.rows),flush=True)

def old_policies():
 core={r['id']:r for r in rows()if r['type']=='evaluation'and r['suite']=='archive-core'and r['kind']=='lazy-full'};assert len(core)==2661
 known=rows();done={(r['id'],r['kind'])for r in known if r['type']=='evaluation'and r['suite']=='archive-policy'}
 for i,m in enumerate(ev.rows):
  ref=core[m['id']];match=re.search(r'abort_step=(\d+)',ref['candidate_stderr']);abort=int(match[1])if match else-1
  for k in ['cautious','local','volume','online','edge-local','edge-volume']:
   if(m['id'],k)in done:continue
   # Every template's first placement is x=0, ceil(length/20) sections.
   # If command2 mismatches, every replay guard accepted that same first
   # placement and imports the same single-command physical history.
   # Pure online is certified only for empty imports, not metadata identity.
   if abort in[1,2]and(k!='online'or abort==1):
    rec={**ref,'suite':'archive-policy','kind':k,'binary_sha256':sha((E/'bin'/k).read_bytes()),'validation':'control_flow_certificate','certificate':'identical replay prefix up to mismatch step<=2; all first positions0 and minimally dug; identical fresh lazy online import','status':'certified_equivalent','candidate_stderr':None,'solver_cpu_total_s':None,'solver_peak_rss_mb':None}
    record(rec)
   else:batch(m,k,'archive-policy')
  if(i+1)%128==0 or i+1==len(ev.rows):print('POLICY',i+1,len(ev.rows),flush=True)

def canon_dedup():
 new={r['command_sha256']:r['id']for r in inputs('calibration')+inputs('final')};assert len(new)==len(inputs('calibration')+inputs('final'))
 older=list(ev.rows)
 for p,types in[(OLD/'records.jsonl',{'input'}),(ev.EXP/'records.jsonl',{'fresh_input','holdout_input'})]:
  older.extend(r.get('meta',r)for r in map(json.loads,p.open())if r['type']in types)
 seen=set();hits=[]
 for m in older:
  if m['test_sha256']in seen:continue
  seen.add(m['test_sha256']);t=Path(m['test_file']).read_bytes().split();n=int(t[1]);h=sha(b'\n'.join(t[2:2+n])+b'\n')
  if h in new:hits.append((new[h],m['id']))
 record(dict(type='command_dedup_audit',prior_unique_test_count=len(seen),new_unique_commands=len(new),hits=hits,scope='canonical command tokens only, header weight/whitespace/optional terminating0 excluded; old streams processed locally, not used to generate tests'))
 assert not hits,hits
 print('COMMAND_DEDUP',len(new),'vs',len(seen),'prior, no overlap',flush=True)

def extend_guards():
 p=Path('/tmp/pipes_guard_generalization.cpp');code=p.read_text();old=code
 a=''' const int newT=a.T+20*max(0,(x+n-a.T+19)/20);
 if(REPLAY_GUARD==2){'''
 b=''' const int newT=a.T+20*max(0,(x+n-a.T+19)/20);
 if((REPLAY_GUARD==5||REPLAY_GUARD==6)&&!guardedReplay(a,x,n,newT))return false;
 if(REPLAY_GUARD==2||REPLAY_GUARD==5){'''
 assert code.count(a)==1;code=code.replace(a,b);a2='if(REPLAY_GUARD==3)return newT';b2='if(REPLAY_GUARD==3||REPLAY_GUARD==6)return newT';assert code.count(a2)==1;code=code.replace(a2,b2);p.write_text(code)
 record(dict(type='candidate_extension',reason='DEV refinement before aggregate policy scores/selection/final: isolate original edge-placement constraint while replacing expensive shadow by causal necessity or volume budget. No numerical thresholds added.',parent_cpp_sha256=sha(old.encode()),cpp_sha256=sha(code.encode()),patches=[[a,b],[a2,b2]],candidates={'edge-local':5,'edge-volume':6},tie_order=['cautious','edge-volume','edge-local','local','volume','online','lazy-full','full'],original_core_and_final_gates_unchanged=True))
 for k,g in [('edge-local',5),('edge-volume',6)]:
  b=E/'bin'/k;q=subprocess.run(['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1',f'-DREPLAY_GUARD={g}',str(p),'-o',str(b)],capture_output=True,text=True)
  record(dict(type='build',kind=k,cpp_sha256=sha(code.encode()),binary_sha256=sha(b.read_bytes())if q.returncode==0 else None,status=q.returncode,stderr=q.stderr[-1800:]));assert q.returncode==0,q.stderr
  print('BUILT',k,flush=True)

def expected_top2(v):
 x=sorted(v);n=len(x);assert n>=4
 return math.fsum(y*(math.comb(i,3)+math.comb(i,2)*(n-i-1))for i,y in enumerate(x))/math.comb(n,4)

def score_table():
 known=rows();meta={m['id']:m for m in ev.rows};arch={k:{}for k in KINDS};arch['full']=FROZEN
 for r in known:
  if r['type']!='evaluation':continue
  if r['suite']=='archive-core':arch['lazy-full'][r['id']]=r
  elif r['suite']=='archive-policy':arch[r['kind']][r['id']]=r
 for k in KINDS:assert len(arch[k])==2661,(k,len(arch[k]))
 cals={(r['id'],r['kind']):r for r in known if r['type']=='evaluation'and r['suite']=='calibration'}
 cm={m['id']:m for m in inputs('calibration')};assert len(cals)==len(cm)*len(KINDS)
 freeze={r['id']:r for r in json.loads((R/'prototypes/pipes_current_hybrid_cj_20261020/freeze.json').read_text())['cases']}
 osha=set()
 for project in['pipes_online_core_20261020','pipes_closed_ready_20261020']:
  for split in['calibration','final','stress']:
   osha.update(r['sha256']for r in json.loads((R/f'prototypes/{project}/evaluation/{split}/manifest.json').read_text())['cases']if r.get('stratum')=='ordinary')
 for v in['search-v2','search-v3','search-v3-1']:osha.update(r['sha256']for r in json.loads((R/f'shinka-pipes/{v}/task/data/search/manifest.json').read_text())['cases'])
 nonpub=[i for i,m in meta.items()if not m.get('public_number')];ordinary=[i for i in nonpub if i in freeze and meta[i]['test_sha256']in osha];assert len(ordinary)==465
 traps={'prototypes/pipes_guarded_traps_20261019','prototypes/pipes_open15_adversary_20261019','prototypes/pipes_prefix_shock_20261019','prototypes/pipes_v5_graves_20261019','prototypes/pipes_presync_transport_20261020','prototypes/pipes_presync_20261020','prototypes/pipes_prefix_replan_20261020'}
 direct=[i for i in nonpub if i in freeze and freeze[i]['source_group']in traps];assert len(direct)==150
 long=[i for i in nonpub if meta[i]['operation_count']>=100000];short=[i for i in nonpub if meta[i]['operation_count']<=200]
 nc=[i for i,m in cm.items()if m['stratum']in['ordinary','series','motif']];assert len(nc)>=11
 scenarios={'ordinary465':(ordinary,ordinary),'long_archive':(long,long),'short_archive':(short,short),'directed150':(direct,direct),'all_nonpublic':(nonpub,nonpub),'new_ordinary_calibration':(nc,nc),'ordinary_cheap_long_expensive':(ordinary,long)}
 opens={k:math.fsum(m['weight']*arch[k][i]['kpi']for i,m in meta.items()if m.get('public_number'))for k in KINDS};assert abs(opens['full']-30.75747404826914)<1e-10
 matrix={k:{}for k in KINDS}
 for k in KINDS:
  def get(i):return cals[i,k]['kpi']if i in cm else arch[k][i]['kpi']
  for name,(cheap,expensive)in scenarios.items():
   assert len(cheap)>=11 and len(expensive)>=4
   matrix[k][name]=opens[k]+44*statistics.fmean(get(i)for i in cheap)+40*statistics.fmean(get(i)for i in expensive)+10*expected_top2([get(i)for i in expensive])
 best={s:max(matrix[k][s]for k in KINDS)for s in scenarios};regrets={k:max(best[s]-matrix[k][s]for s in scenarios)for k in KINDS};bestregret=min(regrets.values());order=['cautious','edge-volume','edge-local','local','volume','online','lazy-full','full'];selected=next(k for k in order if regrets[k]<=bestregret+.02)
 return arch,cm,opens,matrix,regrets,selected

def select():
 assert not any(r['type']=='evaluation'and r['suite']=='final'for r in rows()),'final already observed'
 arch,cm,opens,matrix,regrets,selected=score_table()
 cals={(r['id'],r['kind']):r for r in rows()if r['type']=='evaluation'and r['suite']=='calibration'}
 core_delta=[arch['lazy-full'][i]['kpi']-FROZEN[i]['kpi']for i in FROZEN];assert min(core_delta)>=-.02 and statistics.fmean(core_delta)>=0
 for g in{m['stratum']for m in cm.values()}:
  z=[cals[i,'lazy-full']['kpi']-cals[i,'full']['kpi']for i,m in cm.items()if m['stratum']==g];assert statistics.fmean(z)>=-1e-12 and min(z)>=-.02,(g,min(z))
 assert selected not in ['full'],'baseline chosen without new core'
 final=inputs('final');record(dict(type='selection_freeze',selected=selected,lazy_core=True,opens=opens,scenario_scores=matrix,max_regrets=regrets,rule='minimax max regret over7 named scenarios;0.02 total-points tie prefers cautious/edge-volume/edge-local/local/volume/online/lazy-full/full',source_cpp_sha256=sha(Path('/tmp/pipes_guard_generalization.cpp').read_bytes()),candidate_binary_sha256=sha((E/'bin'/selected).read_bytes()),final_inputs=[m['test_sha256']for m in final],final_input_count=len(final),core_archive_mean_delta=statistics.fmean(core_delta),core_archive_min_delta=min(core_delta),final_policy_gate='holdout minimax regret vs all frozen candidates no worse than full baseline; no post-final policy switching; Cj complete responses must match selected CPP and official interactive resources valid',target_windows_g5420_measured=False))
 print(json.dumps(dict(selected=selected,opens=opens,regrets=regrets,scores=matrix),ensure_ascii=False,indent=2),flush=True)
 guard=KINDS[selected][1];b=E/'bin/same-policy-oldcore';q=subprocess.run(['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=0',f'-DREPLAY_GUARD={guard}','/tmp/pipes_guard_generalization.cpp','-o',str(b)],capture_output=True,text=True);assert q.returncode==0,q.stderr
 record(dict(type='build',kind='same-policy-oldcore',guard_mode=guard,cpp_sha256=sha(Path('/tmp/pipes_guard_generalization.cpp').read_bytes()),binary_sha256=sha(b.read_bytes()),status=q.returncode))

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='build':source_build()
 elif mode=='extend-guards':extend_guards()
 elif mode=='select':select()
 elif mode=='dedup':canon_dedup()
 elif mode in['calibration','final']:panel(mode,sys.argv[2:]or list(KINDS))
 elif mode=='old-core':old_core()
 elif mode=='old-policies':old_policies()
 else:raise ValueError(mode)
