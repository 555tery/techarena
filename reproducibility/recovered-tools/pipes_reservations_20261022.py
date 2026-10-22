from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,math,os,random,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
ROOT=Path('/Users/555tery/techarena'); E=ROOT/'prototypes/pipes_online_reservations_20261022'
E.mkdir(exist_ok=True); (E/'inputs').mkdir(exist_ok=True); (E/'bin').mkdir(exist_ok=True)
BASE=ROOT/'prototypes/pipes_current_hybrid_cj_20261020/cpp/solution.cpp'
REC=E/'records.jsonl'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def record(x):
 with REC.open('a')as f:f.write(json.dumps(x,ensure_ascii=False)+'\n')
def records():return [json.loads(s)for s in REC.open()]if REC.exists()else []
def build():
 code=BASE.read_text();patches=[]
 old='#define CAUTIOUS_HYBRID 1';new='#define CAUTIOUS_HYBRID 0';assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 old='    void beginCohortSlab(int length) {'
 new='''    long long reclaimedReservationMeters = 0;
    void releaseCohortReservation() {
#if RESERVATION_POLICY >= 1
        if (!cohortSlabActive || !cohortSlabExpanded) return;
        const auto n = observedRunLength;
        const auto deletedBegin = cohortSlabBase + std::int64_t(cohortSlabDeletedUsed) * n;
        const auto deletedEnd = cohortSlabBase + std::int64_t(cohortSlabDeleteCount) * n;
        const auto survivorBegin = cohortSlabBase + std::int64_t(cohortSlabDeleteCount + cohortSlabSurvivorUsed) * n;
        const auto survivorEnd = cohortSlabBase + std::int64_t(cohortSlabTailPipeCount) * n;
        if (deletedBegin < deletedEnd) { addFreeGap(deletedBegin, deletedEnd, -1, releaseEpoch); reclaimedReservationMeters += deletedEnd-deletedBegin; }
        if (survivorBegin < survivorEnd) { addFreeGap(survivorBegin, survivorEnd, -1, releaseEpoch); reclaimedReservationMeters += survivorEnd-survivorBegin; }
#endif
    }
    void beginCohortSlab(int length) {'''
 assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 old='''        if (observedRunLength != length) {
            if (observedRunCount > 0) {'''
 new='''        if (observedRunLength != length) {
            releaseCohortReservation();
            if (observedRunCount > 0) {'''
 assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 old='''        ++observedRunCount;
        const int sizeCohort'''
 new='''#if RESERVATION_POLICY == 2
        if (!cohortSlabActive && observedRunCount >= 64 && observedRunCount % 64 == 0) beginCohortSlab(length);
#endif
        ++observedRunCount;
        const int sizeCohort'''
 assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 old='''        const int expectedCount = (previous.second + last.second) / 2;
        if (expectedCount < 64) return;'''
 new='''        const int predictedCount = (previous.second + last.second) / 2;
        if (predictedCount < 64) return;
        const int expectedCount = RESERVATION_POLICY == 2 ? std::min(64,predictedCount) : predictedCount;'''
 assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 old='''  cerr<<"replay_placements="<<replayPlacements'''
 new='''  if(online) cerr<<"reclaimed_reservation_m="<<online->reclaimedReservationMeters<<'\\n';
  cerr<<"replay_placements="<<replayPlacements'''
 assert code.count(old)==1;code=code.replace(old,new);patches.append([old,new])
 path=Path('/tmp/pipes_reservations_dev.cpp');path.write_text(code)
 record(dict(type='protocol',base=str(BASE),base_sha256=digest(BASE.read_bytes()),patches=patches,dev_source_sha256=digest(code.encode()),variants={'cpp-base':0,'cpp-release':1,'cpp-chunk64':2},selection_gate='predeclared: DEV ordinary mean>=baseline, stable mean>=baseline-0.002, targeted mean>=baseline, all-case min delta>=-0.02; old regression mean>=0 and weighted score>=baseline; final unchanged gate and all answers valid; Cangjie1.0.5 O0 interactive CPU<5/RSS<256; no Windows speed extrapolation',final_gate='same fresh stratum means; no post-final tuning; actual Open15 max preserved',no_platform=True))
 for kind,variant in [('cpp-base',0),('cpp-release',1),('cpp-chunk64',2)]:
  proc=subprocess.run(['clang++','-O2','-std=c++17',f'-DRESERVATION_POLICY={variant}',str(path),'-o',str(E/'bin'/kind)],capture_output=True,text=True)
  record(dict(type='build',kind=kind,status=proc.returncode,stderr=proc.stderr[-1800:],binary_sha256=(digest((E/'bin'/kind).read_bytes())if proc.returncode==0 else None)))
  assert proc.returncode==0,proc.stderr
  print('BUILT',kind,flush=True)

class Stream:
 def __init__(self):self.commands=[];self.lengths=[0];self.active=[];self.position={};self.occupied=0;self.peak=0
 def add(self,n):
  assert 1<=n<=40
  pid=len(self.lengths);self.lengths.append(n);self.position[pid]=len(self.active);self.active.append(pid);self.commands.append(n);self.occupied+=n;self.peak=max(self.peak,self.occupied);return pid
 def delete(self,pid):
  i=self.position.pop(pid);last=self.active.pop()
  if i<len(self.active):self.active[i]=last;self.position[last]=i
  self.commands.append(-pid);self.occupied-=self.lengths[pid]
 def run(self,n,count,parity=0):
  ids=[self.add(n)for _ in range(count)]
  for pid in ids[parity::2]:self.delete(pid)

def generate(split,index):
 final=split=='final';seed=(202610225000 if final else 202610224000)+index;r=random.Random(seed);s=Stream()
 group=index%3
 if group in (0,1):
  # Long-lived background is part of the process from the start, never a terminal filler.
  block=([192,640,2304,5632]if final else[128,512,2048,4096])[index//3%4]
  if final:block+=r.choice([-1,1])
  start=r.choice([2,3,5])if final else[2,4,6,8][index//3%4]
  step=r.choice([1,2])if final else 1
  for _ in range(2*block):s.add(20)
  sizes=[start+step*j for j in range(min((39-start)//step+1,8 if final else 6))]
  s.run(sizes[0],block);s.run(sizes[1],block)
  if group==0:
   family='interrupted_reservation';stratum='targeted'
   # Interrupt at a small unseen fraction of the predicted third run.
   short=r.choice([3,17,71,129])if final else[1,5,31,96][index//3%4]
   for _ in range(short):s.add(sizes[2])
   if index//3%2==0:
    for _ in range(block//2):s.add(r.choice([9,13,19,27,35])if final else r.randint(1,40))
   # The other half stop immediately: these measure irreversible reserve growth.
  else:
   family='stable_cohort_staircase';stratum='stable'
   for n in sizes[2:]:s.run(n,block,parity=(index//6%2 if final else 0))
   for _ in range(block//4):s.add(sizes[-1])
 else:
  family=['phase_churn','batch_churn','size_lifetime_switch','mixed_fifo_lifo'][index//3%4];stratum='ordinary'
  live=([96,384,3072,12288]if final else[64,256,2048,8192])[index//3%4]
  n=200000 if index//3>=2 else(45000 if final else 20000)
  if 8*live>=n:live=n//16
  for _ in range(7*live):s.add(40)
  for _ in range(live):s.add(r.randint(8,32))
  fixed_count=7*live;oldest=fixed_count+1;pending=[];period=2309 if final else 2048
  while len(s.commands)+2<=n:
   t=(len(s.commands)-8*live)//2;phase=(t//period)%4
   if family=='phase_churn':
    pid=r.choice(s.active[fixed_count:])if phase in (1,3)else (oldest if phase==0 else len(s.lengths)-1)
    if phase==0:
     while pid not in s.position:pid+=1
     oldest=pid
    length=r.randint(*([(1,12),(17,30),(28,40),(5,35)][phase]))
   elif family=='batch_churn':
    if not pending:
     center=r.choice(s.active[fixed_count:]);pending=[p for p in range(max(fixed_count+1,center-16),min(len(s.lengths),center+17))if p in s.position]
    pid=pending.pop();length=1+((t//(97 if final else 64))* (7 if final else 3))%40
   elif family=='size_lifetime_switch':
    choices=[r.choice(s.active[fixed_count:])for _ in range(8)];pid=(min if phase%2==0 else max)(choices,key=lambda p:s.lengths[p]);length=r.choice([7,31,39]if final else[8,24,36])
   else:
    if phase%2==0:
     while oldest not in s.position:oldest+=1
     pid=oldest
    else:
     pid=len(s.lengths)-1
     while pid not in s.position:pid-=1
    length=r.randint(1,40)
   s.delete(pid);s.add(length)
  if len(s.commands)<n:s.add(20)
 n=len(s.commands);assert 0<n<=200000
 bound=s.occupied/(20*math.ceil(s.peak/20));assert bound>=.85,(split,index,bound)
 return s,dict(id=f'{split}-reserve-{index+1:02d}',family=family,stratum=stratum,seed=seed,weight=1.,operation_count=n,placement_count=len(s.lengths)-1,final_occupied_length_m=s.occupied,peak_live_pipe_length_m=s.peak,minimum_trench_lower_bound_m=20*math.ceil(s.peak/20),kpi_upper_bound_from_live_volume=bound)

def freeze():
 known={r['meta']['id']:r['meta']for r in records()if r['type']=='input'}
 pending=[]
 for split,count in [('dev',24),('final',36)]:
  for i in range(count):
   s,m=generate(split,i);raw=('1\n'+str(m['operation_count'])+'\n'+'\n'.join(map(str,s.commands))+'\n').encode();path=E/'inputs'/f'{m["id"]}.in';m.update(test_file=str(path),test_sha256=digest(raw));pending.append((split,path,raw,m))
 for split,path,raw,m in pending:
   if m['id']in known:assert known[m['id']]['test_sha256']==m['test_sha256'];continue
   path.write_bytes(raw);record(dict(type='input',split=split,meta=m))
 record(dict(type='generator_freeze',generator_source=Path(__file__).read_text(),note='Before all evaluations: initial volume-bound validation rejected phase-shrink construction; corrected using permanent initial background7x churn count. No solver results observed. Final36 remain unseen.'))
 for split,count in [('dev',24),('final',36)]:
  print('FROZEN',split,count,flush=True)

sys.path.insert(0,'/tmp');import pipes_o0_evaluate_20261022 as ev
def evaluate(m,kind,suite):
 binary=E/'bin'/kind;data=Path(m['test_file']).read_bytes();assert digest(data)==m['test_sha256'];tokens=data.split();assert int(tokens[1])==m['operation_count'];stream=b'\n'.join(tokens[2:2+m['operation_count']])+b'\n0\n'
 with tempfile.TemporaryDirectory(prefix='pipes-reserve-')as temp:
  d=Path(temp);(d/'commands').write_bytes(stream)
  with(d/'commands').open('rb')as fi,(d/'out').open('wb')as fo,(d/'err').open('wb')as fe:
   p=subprocess.Popen([str(binary)],stdin=fi,stdout=fo,stderr=fe,env={**os.environ,'cjProcessorNum':'1'});_,status,u=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status)
  assert p.returncode==0,(kind,m['id'],(d/'err').read_text())
  output_sha=digest((d/'out').read_bytes());expected=FULL_REFERENCE.get(m['id'])if suite=='regression'else None
  validation='official_checker_on_complete_response'
  if expected and output_sha==expected['response_sha256']:
   occupied=m['final_occupied_length_m'];trench=expected['trench_length_m'];validation='complete_response_parity_with_frozen_full_replay'
  else:
   (d/'empty').write_text('')
   with(d/'out').open('rb')as fi:
    q=subprocess.run([str(ev.EXP/'bin/official-offline'),m['test_file'],str(d/'checked'),str(d/'empty'),str(d/'report')],stdin=fi,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=d)
   match=ev.h.SCORE_RE.search(q.stderr.decode());assert q.returncode==0 and match,(kind,m['id'],q.stderr[-1000:])
   occupied,trench=int(match[1]),int(match[2]);assert occupied==m['final_occupied_length_m']
  rec=dict(type='evaluation',suite=suite,kind=kind,id=m['id'],stratum=m.get('stratum'),family=m.get('family'),operation_count=m['operation_count'],test_sha256=m['test_sha256'],binary_sha256=digest(binary.read_bytes()),source_sha256=(digest((E/'solution.cj').read_bytes())if kind=='cj-release'else None),kpi=occupied/trench,trench_length_m=trench,response_sha256=output_sha,status='ok',solver_cpu_total_s=u.ru_utime+u.ru_stime,solver_peak_rss_mb=u.ru_maxrss/1048576,candidate_stderr=(d/'err').read_text()[-1400:],weight=m['weight'],validation=validation,resource_scope='batch complete execution; Cangjie resources also checked official interactive')
  record(rec);return rec

FULL_REFERENCE={r['id']:r for r in map(json.loads,(ev.EXP/'records.jsonl').open())if r['type']=='evaluation'and r.get('suite')=='full-batch'and r.get('kind')=='full-replay'}
assert len(FULL_REFERENCE)==2661

def build_cj():
 source=ev.EXP/'full-replay/solution.cj';code=source.read_text()
 old='''        if (observedRunLength != length) {
            if (observedRunCount > 0) {'''
 new='''        if (observedRunLength != length) {
            releaseCohortReservation()
            if (observedRunCount > 0) {'''
 assert code.count(old)==1;code=code.replace(old,new)
 old='''    @OverflowWrapping
    public func beginCohortSlab(length: Int64): Unit {'''
 new='''    // A slab reserves two disjoint bands. When a size run ends early,
    // return only the still unassigned suffix of each band to the gap indices.
    // Already placed pipes and all answers remain fixed.
    @OverflowWrapping
    private func releaseCohortReservation(): Unit {
        if (!cohortSlabActive || !cohortSlabExpanded) { return }
        let length = observedRunLength
        let deletedBegin = cohortSlabBase + cohortSlabDeletedUsed * length
        let deletedEnd = cohortSlabBase + cohortSlabDeleteCount * length
        let survivorBegin = cohortSlabBase + (cohortSlabDeleteCount + cohortSlabSurvivorUsed) * length
        let survivorEnd = cohortSlabBase + cohortSlabTailPipeCount * length
        if (deletedBegin < deletedEnd) { addFreeGap(deletedBegin, deletedEnd, -1, releaseEpoch) }
        if (survivorBegin < survivorEnd) { addFreeGap(survivorBegin, survivorEnd, -1, releaseEpoch) }
    }

    @OverflowWrapping
    public func beginCohortSlab(length: Int64): Unit {'''
 assert code.count(old)==1;code=code.replace(old,new)
 path=E/'solution.cj';assert not path.exists();path.write_text(code)
 compiler=ROOT/'prototypes/pipes_cj_tle_fix_20261020/toolchain105/cangjie/bin/cjc';sdk=subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip()
 proc=subprocess.run([str(compiler),'-O0','-Woff','all','--set-runtime-rpath','--sysroot',sdk,'-p',str(E),'-o',str(E/'bin/cj-release')],capture_output=True,text=True)
 record(dict(type='build',kind='cj-release',parent_sha256=digest(source.read_bytes()),source_sha256=digest(path.read_bytes()),compiler='Cangjie1.0.5 -O0',status=proc.returncode,stderr=proc.stderr[-2000:],binary_sha256=digest((E/'bin/cj-release').read_bytes())if proc.returncode==0 else None))
 assert proc.returncode==0,proc.stderr
 print('CJ_BUILT',digest(path.read_bytes()),flush=True)

def panel(split,kinds):
 known=records();metas=[r['meta']for r in known if r['type']=='input'and r['split']==split];done={(r['id'],r['kind'],r.get('binary_sha256'))for r in known if r['type']=='evaluation'}
 for i,m in enumerate(metas):
  for k in(kinds if i%2==0 else kinds[::-1]):
   if(m['id'],k,digest((E/'bin'/k).read_bytes()))not in done:evaluate(m,k,split)
  if(i+1)%4==0:print('PANEL',split,i+1,len(metas),flush=True)

def regression(kinds):
 known=records();done={(r['id'],r['kind'],r.get('binary_sha256'))for r in known if r['type']=='evaluation'}
 for i,m in enumerate(ev.rows):
  for k in(kinds if i%2==0 else kinds[::-1]):
   if(m['id'],k,digest((E/'bin'/k).read_bytes()))not in done:evaluate(m,k,'regression')
  if(i+1)%128==0:print('REGRESSION',i+1,len(ev.rows),flush=True)

def interactive(m,kind,suite):
 if kind=='old-full':source,binary=ev.solver('full-replay')
 else:source,binary=E/'solution.cj',E/'bin/cj-release'
 sha=digest(source.read_bytes());path=Path(m['test_file']);assert digest(path.read_bytes())==m['test_sha256']
 existing=[r for r in records()if r['type']=='interactive_evaluation'and r['id']==m['id']and r['kind']==kind and r['suite']==suite and r['source_sha256']==sha]
 if existing:return existing[-1]
 base=SimpleNamespace(**ev.h.__dict__);base.parse_test=lambda _:dict(m);os.environ['cjProcessorNum']='1'
 with tempfile.TemporaryDirectory(prefix='pipes-reserve-native-')as temp:
  result=ev.nh.run_case(base,[str(binary)],ev.NATIVE,path,Path(temp)/'run',5,240)
  output=Path(result['judge_output_file']);outsha=digest(output.read_bytes())if output.exists()else None
  rec={key:result.get(key)for key in ['status','detail','solver_cpu_user_s','solver_cpu_system_s','solver_cpu_total_s','solver_peak_rss_mb','kpi','trench_length_m','candidate_stderr']}
  rec.update(type='interactive_evaluation',suite=suite,kind=kind,id=m['id'],family=m.get('family'),stratum=m.get('stratum'),operation_count=m['operation_count'],test_sha256=m['test_sha256'],source_sha256=sha,binary_sha256=digest(binary.read_bytes()),response_sha256=outsha,within_limits=not ev.nh.failed(result,5,256),runtime_threads_env='cjProcessorNum=1',timing_scope='whole solver process user+system; macOS M1, not Windows G5420')
  record(rec)
  assert rec['within_limits'],rec
  return rec

def select():
 known=records();current=digest((E/'solution.cj').read_bytes())
 regression_rows={r['id']:r for r in known if r['type']=='evaluation'and r['suite']=='regression'and r['kind']=='cj-release'and r['source_sha256']==current}
 assert len(regression_rows)==2661,len(regression_rows)
 delta=[r['kpi']-FULL_REFERENCE[i]['kpi']for i,r in regression_rows.items()]
 assert min(delta)>=-.02 and sum(delta)>=-1e-12,(min(delta),sum(delta))
 pub=[r for r in ev.rows if r.get('public_number')];assert len(pub)==15
 score=sum(r['weight']*regression_rows[r['id']]['kpi']for r in pub);assert abs(score-30.75747404826914)<1e-10,score
 new_records=[json.loads(s)for s in(ev.EXP/'records.jsonl').open()]
 resource_candidates=[r for r in new_records if r['type']=='evaluation'and r.get('kind')=='full-replay'and r.get('suite')in['full-new-independent','full-final-holdout']]
 ids=[r['id']for r in sorted(resource_candidates,key=lambda r:r['solver_cpu_total_s'],reverse=True)[:5]]
 assert len(ids)==5
 record(dict(type='selection_freeze',selected='reclaim unassigned cohort reservation only; chunk64 rejected by old-regression min gate',source_sha256=current,binary_sha256=digest((E/'bin/cj-release').read_bytes()),regression_cases=2661,min_delta=min(delta),mean_delta=sum(delta)/len(delta),open15=score,unseen_final=[r['meta']['test_sha256']for r in known if r['type']=='input'and r['split']=='final'],resource_ids=ids,final_gate='mean delta ordinary>=0, stable>=-0.002, targeted>=0; min delta>=-0.02; no subsequent policy tuning; all interactive valid within M1-local CPU/RSS; not a target Windows guarantee'))
 print('SELECTED',current,'old delta',sum(delta)/len(delta),'minimum',min(delta),flush=True)

def final_native():
 known=records();freeze=next(r for r in known[::-1]if r['type']=='selection_freeze');assert freeze['source_sha256']==digest((E/'solution.cj').read_bytes())
 metas=[r['meta']for r in known if r['type']=='input'and r['split']=='final'];assert [m['test_sha256']for m in metas]==freeze['unseen_final']
 for i,m in enumerate(metas):
  for k in(['old-full','new-full']if i%2==0 else['new-full','old-full']):interactive(m,k,'unseen-final')
  if(i+1)%4==0:print('FINAL',i+1,len(metas),flush=True)

def resources():
 known=records();freeze=next(r for r in known[::-1]if r['type']=='selection_freeze');assert freeze['source_sha256']==digest((E/'solution.cj').read_bytes())
 for m in[r for r in ev.rows if r.get('public_number')]:interactive(m,'new-full','open15')
 old=[json.loads(s)for s in(ev.EXP/'records.jsonl').open()]
 metas={r['meta']['id']:r['meta']for r in old if r['type']in['fresh_input','holdout_input']}
 for i,ident in enumerate(freeze['resource_ids']):
  for k in(['old-full','new-full']if i%2==0 else['new-full','old-full']):interactive(metas[ident],k,'worst-observed-200k')
  print('RESOURCE',i+1,len(freeze['resource_ids']),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='prepare':build();freeze()
 elif mode=='build-cj':build_cj()
 elif mode=='select':select()
 elif mode=='final-native':final_native()
 elif mode=='resources':resources()
 elif mode in('dev','final'):panel(mode,sys.argv[2:]or['cpp-base','cpp-release','cpp-chunk64'])
 elif mode=='regression':regression(sys.argv[2:]or['cpp-base','cpp-release','cpp-chunk64'])
 else:raise ValueError(mode)
