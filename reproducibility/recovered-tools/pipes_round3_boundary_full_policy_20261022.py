"""Single-worker frozen F qualification. No search, tuning or platform access."""
import sys,json,time,traceback,math,collections,difflib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b
K='boundary-full'
PARENT=b.E/'boundary-index/uncached/solution.cj'
PARENT_SHA='f1f6240fb7ca7e099408a02bb2aeb9926f4240425afbd7be4eebd25ee6a2ac4a'
CPPBIN='08bb7d5d6a06692b91bb49f69c4f278b0406bc3b4726d362f54d8e2ff7fd3338'
PATCH=Path('/tmp/pipes_full_replay_switch_round3_20261022.py')
DEADLINE=datetime(2026,10,22,23,39,40,tzinfo=ZoneInfo('Asia/Novosibirsk')).timestamp()
REFS={}
def deadline():
 if time.time()>=DEADLINE:raise TimeoutError('qualification hardstop before23:40')
def note(t,**kw):
 r=b.record(dict(type=t,kind=K,**kw));print(t,json.dumps(r,ensure_ascii=False),flush=True);return r
def pins():
 a.pins();assert b.sha(PARENT.read_bytes())==PARENT_SHA
 s,bi=b.artifact(K,'cpp');assert b.sha(s.read_bytes())==a.CPP_SHA and b.sha(bi.read_bytes())==CPPBIN
def initrefs():
 for p in [a.P/'records.jsonl',b.REC]:
  for r in b.read_jsonl(p):
   if r.get('type')in ['evaluation','interactive_evaluation'] and r.get('status')=='ok' and r.get('language')=='cpp' and r.get('source_sha256')==a.CPP_SHA and r.get('binary_sha256')==CPPBIN:
    REFS[(r['id'],r['test_sha256'])]=r
def ref(m,suite):
 deadline();key=(m['id'],m['test_sha256'])
 if key in REFS:return REFS[key]
 q=b.batch(m,K,suite+'-cpp','cpp');assert q['source_sha256']==a.CPP_SHA and q['binary_sha256']==CPPBIN
 REFS[key]=q;return q
def fm(m,r):
 return dict(m,baseline_response_sha256=r['response_sha256'],baseline_kpi=r['kpi'],baseline_trench_length_m=r['trench_length_m'])
def checked(m,suite,lang='cj'):
 r=ref(m,suite);q=b.batch(fm(m,r),K,suite,lang);b.cj_resource_review(q)
 assert q['response_sha256']==r['response_sha256'],('F Cj/CPP response mismatch',m['id'],lang)
 assert q['solver_cpu_total_s']<4.5 and q['solver_peak_rss_mb']<230.,q
 return q
def actualnative(m,suite,lang='cj',env='1'):
 r=ref(m,suite);deadline();q=b.native(fm(m,r),K,suite,lang,processor_env=env);b.cj_resource_review(q)
 assert q['response_sha256']==r['response_sha256'],('F native Cj/CPP response mismatch',m['id'],lang,env)
 assert q['solver_cpu_total_s']<4.5 and q['solver_peak_rss_mb']<230.,q
 return q
def prepare():
 a.pins();assert b.sha(PARENT.read_bytes())==PARENT_SHA
 old=b.read_jsonl(a.P/'records.jsonl')
 build=next(q for q in old if q.get('type')=='build' and q.get('kind')=='core-full-comparative' and q.get('binary_sha256')==CPPBIN)
 if not any(q.get('type')=='build'and q.get('kind')==K and q.get('language')=='cpp'for q in b.rows()):
  b.record(dict(build,kind=K,command=None,alias_only=True,reference_command=build['command'],reference_records=str(a.P/'records.jsonl'),scope='unchanged pinned CPP G0 reference; no build'))
 pins();module=b._load_module(PATCH);code=module.apply_cj(PARENT.read_text())
 diff='\n'.join(difflib.unified_diff(PARENT.read_text().splitlines(),code.splitlines(),fromfile='boundary-index/uncached',tofile='boundary-full/uncached',n=2))
 assert sum(x.startswith('-')and not x.startswith('---')for x in diff.splitlines())==1
 assert sum(x.startswith('+')and not x.startswith('+++')for x in diff.splitlines())==1
 if not any(q.get('type')=='full_policy_freeze'for q in b.rows()):
  note('full_policy_freeze',before_first_F_execution=True,parent_source_sha256=PARENT_SHA,transformer=str(PATCH),transformer_sha256=b.sha(PATCH.read_bytes()),expected_uncached_sha256=b.sha(code.encode()),minimal_diff=diff,cpp_source_sha256=a.CPP_SHA,cpp_binary_sha256=CPPBIN,cache_rule='regenerate solely from same F uncached binary',compiler='Cangjie1.0.5 -O0',one_heavy_worker=True,deadline_local='2026-10-22T23:40:00+07:00',final24_still_sealed=True,no_policy_tuning=True)
 print('F_MINIMAL_DIFF\n'+diff,flush=True)
 if not any(q.get('type')=='build'and q.get('kind')==K and q.get('language')=='cj'and q.get('status')==0 for q in b.rows()):
  b.compile_cj_variant(K,PATCH,cpp_reference=K,uncached_source=PARENT,regenerate_output_cache=True)
 initrefs()
 artifacts={lang:dict(source=str(b.artifact(K,lang)[0]),source_sha256=b.sha(b.artifact(K,lang)[0].read_bytes()),binary=str(b.artifact(K,lang)[1]),binary_sha256=b.sha(b.artifact(K,lang)[1].read_bytes()))for lang in ['cpp','cj','cj-uncached']}
 note('full_open15_pass',all15_uncached_cached_exact_cpp=True,cache_from_same_F_policy=True,artifacts=artifacts,Open15=math.fsum(m['weight']*ref(m,'full-open')['kpi']for m in b.inputs('archive')if m.get('public_number')),final24_still_sealed=True)
def risk_eof():
 h,_=b.harness();archive=b.inputs('archive');p15=next(m for m in archive if m.get('public_number')==15);tokens=Path(p15['test_file']).read_text().split();commands=tokens[2:2+p15['operation_count']]
 existing=next(m for m in archive if m['id']=='15f382e19a19d13d3ec562ba5d5d43ee3a47a238e74874d79ab40182e09c4f10')
 assert Path(existing['test_file']).read_text().split()[2:2+4999]==commands[:4999]
 result=[]
 for n in [4999,10000,25000]:
  if n==4999:m=dict(existing)
  else:
   path=b.E/K/'protocol'/f'open15-natural-eof-{n}.in';path.parent.mkdir(parents=True,exist_ok=True)
   data='1\n'+str(n)+'\n'+'\n'.join(commands[:n])+'\n'
   if path.exists():assert path.read_text()==data
   else:path.write_text(data)
   m=dict(h.parse_test(path),id=f'full-open15-natural-eof-{n}',test_file=str(path),split='protocol',provenance='known-risk-diagnostic-not-quality-gate')
  deadline();f=actualnative(m,'full-risk-EOF')
  c=b.native(m,'boundary-index','full-risk-EOF-C','cj',processor_env='1');b.cj_resource_review(c)
  result.append(dict(n=n,id=m['id'],test_sha256=m['test_sha256'],F_KPI=f['kpi'],C_KPI=c['kpi'],delta=f['kpi']-c['kpi'],F_T=f['trench_length_m'],C_T=c['trench_length_m'],F_response_sha256=f['response_sha256'],C_response_sha256=c['response_sha256']))
 note('full_known_EOF_risk',cases=result,scope='known exact prefix risk; descriptive, not acceptance quality gate',final24_still_sealed=True)
def early():
 prepare();risk_eof()
 ms=[m for m in b.read_jsonl(b.MANIFEST)if m['split']=='sensitivity_development'];assert len(ms)==36
 qs=[]
 for j,m in enumerate(ms):
  qs.append(checked(m,'full-sensitivity36'))
  if(j+1)%6==0:print('F_SENSITIVITY36',j+1,36,flush=True)
 note('full_sensitivity36_pass',count=36,all_actual_cached_complete_responses_exact_cpp=True,maximum_cpu_s=max(q['solver_cpu_total_s']for q in qs),maximum_rss_mib=max(q['solver_peak_rss_mb']for q in qs),final24_still_sealed=True)
 prior=next(q for q in b.read_jsonl(a.P/'records.jsonl')if q.get('type')=='ring_pilot_panel_freeze');ids=[q['id']for q in prior['mc_active_cases']]+prior['general_heavy_ids'];assert len(ids)==len(set(ids))==20
 meta={m['id']:m for m in b.inputs('archive')};qs=[]
 note('full_native20_plan',ids=ids,test_hashes={i:meta[i]['test_sha256']for i in ids},fixed_existing_panel=True,repeats=1,strict_cpu_s=4.5,strict_rss_mib=230,quality_reference='CPP G0 actual complete response',final24_still_sealed=True)
 for j,i in enumerate(ids):
  qs.append(actualnative(meta[i],'full-native20'))
  print('F_NATIVE20',j+1,20,'maxcpu',max(q['solver_cpu_total_s']for q in qs),flush=True)
 note('full_native20_pass',count=20,all_actual_complete_responses_exact_cpp=True,maximum_cpu_s=max(q['solver_cpu_total_s']for q in qs),maximum_rss_mib=max(q['solver_peak_rss_mb']for q in qs),final24_still_sealed=True)
 envqs=[]
 for j,i in enumerate(prior['general_heavy_ids']):
  envqs.append(actualnative(meta[i],'full-env10',env=None))
  print('F_ENV10',j+1,10,flush=True)
 h,_=b.harness();path=Path('/tmp/pipes_round2_protocol_20261022/late-cache-fork-199999.in');m=dict(h.parse_test(path),id='round2-late-cache-fork-199999',test_file=str(path),split='protocol',provenance='protocol-not-quality')
 late=[]
 for lang in ['cj','cj-uncached']:
  for env in ['1',None]:late.append(actualnative(m,'full-late199999',lang,env))
 note('full_env_latefork_pass',heavy_envUNSET_count=10,heavy_env1_covered_native20=True,all_exact_CPP=True,late_matching_commands=199999,late_cached_uncached_env1_UNSET=True,late_test_sha256=m['test_sha256'],late_maximum_cpu_s=max(q['solver_cpu_total_s']for q in late),late_maximum_rss_mib=max(q['solver_peak_rss_mb']for q in late),env_maximum_cpu_s=max(q['solver_cpu_total_s']for q in envqs),env_maximum_rss_mib=max(q['solver_peak_rss_mb']for q in envqs),final24_still_sealed=True)
 artifacts={lang:dict(source=str(b.artifact(K,lang)[0]),source_sha256=b.sha(b.artifact(K,lang)[0].read_bytes()),binary=str(b.artifact(K,lang)[1]),binary_sha256=b.sha(b.artifact(K,lang)[1].read_bytes()))for lang in ['cpp','cj','cj-uncached']}
 if not any(q.get('type')=='selection_freeze'for q in b.rows()):
  finals=b.inputs('sealed_final',allow_final=True);assert len(finals)==24
  b.record(dict(type='selection_freeze',selected=K,artifacts=artifacts,fixed_gates=dict(guard_switch_only=True,Open15_exact=True,sensitivity36_exact=True,native20_cpu_below4_5_rss_below230=True,late199999_env_pass=True),before_final=True,final_input_count=24,final_test_hashes=[m['test_sha256']for m in finals],promotion='root decision only; no post-final tuning'))
 note('full_early_qualification_pass',artifacts=artifacts,actual3029_pending=True,final24_frozen_not_yet_run=True,Windows_server_unverified=True)
def full():
 pins();initrefs();assert any(q.get('type')=='full_early_qualification_pass'for q in b.rows())
 ms=b.inputs('archive');assert len(ms)==3029
 note('full3029_F_plan',count=3029,actual_F_only=True,reuse_only_same_source_binary_input_actual_complete_response=True,cpp_reference_source_sha256=a.CPP_SHA,cpp_reference_binary_sha256=CPPBIN,strict_cpu_s=4.5,strict_rss_mib=230.,deadline_local='23:39:40',final24_still_sealed=True)
 t=time.monotonic();qs=[];ds=[]
 for j,m in enumerate(ms):
  q=checked(m,'full-F3029');qs.append(q);ds.append(q['kpi']-m['baseline_kpi'])
  if(j+1)%40==0 or j+1==len(ms):print('F_FULL3029',j+1,len(ms),'elapsed',round(time.monotonic()-t,2),'maxcpu',max(x['solver_cpu_total_s']for x in qs),'maxrss',max(x['solver_peak_rss_mb']for x in qs),flush=True)
 note('full3029_F_pass',count=3029,all_actual_complete_responses_exact_cpp=True,maximum_cpu_s=max(q['solver_cpu_total_s']for q in qs),maximum_rss_mib=max(q['solver_peak_rss_mb']for q in qs),total_cpu_s=sum(q['solver_cpu_total_s']for q in qs),wall_s=time.monotonic()-t,comparison_vs_current_C=dict(wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),losses=sum(d< -1e-12 for d in ds),mean=sum(ds)/len(ds),minimum=min(ds),maximum=max(ds)),validation_counts=dict(collections.Counter(q['validation']for q in qs)),final24_still_sealed=True)
def final24():
 pins();initrefs();selection=b._selection();assert selection['selected']==K
 ms=b.inputs('sealed_final',allow_final=True);assert len(ms)==24
 existing=[q for q in b.rows()if q.get('type')=='full_final24_result'];assert not existing,'one frozen final pass only'
 note('full_final24_plan',count=24,selection_frozen=True,no_postfinal_policy_changes=True,comparators='CPP C/G5 vs CPP F/G0 and exact F cached Cj',independent_final=True)
 vals=[]
 for j,m in enumerate(ms):
  c=b.batch(m,'baseline','full-final24-C','cpp');r=ref(m,'full-final24-F');q=checked(m,'full-final24-F')
  vals.append(dict(id=m['id'],C_KPI=c['kpi'],F_KPI=q['kpi'],delta=q['kpi']-c['kpi'],C_T=c['trench_length_m'],F_T=q['trench_length_m'],F_response_sha256=q['response_sha256'],F_CPP_response_sha256=r['response_sha256'],test_sha256=m['test_sha256']))
  if(j+1)%3==0:print('F_FINAL24',j+1,24,flush=True)
 ds=[x['delta']for x in vals]
 note('full_final24_result',count=24,all_F_cached_Cj_complete_responses_exact_F_CPP=True,comparisons=dict(wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),losses=sum(d< -1e-12 for d in ds),mean=sum(ds)/24,minimum=min(ds),maximum=max(ds)),cases=vals,no_postfinal_policy_changes=True)
def main():
 mode=sys.argv[1]
 if mode in ['early','all']:early()
 if mode in ['full','all']:full()
 if mode in ['final','all']:final24()
 if mode=='all':note('full_F_qualification_complete',finished_before_deadline=time.time()<DEADLINE,Windows_server_unverified=True,root_promotion_only=True)
if __name__=='__main__':
 try:main()
 except BaseException as ex:
  note('full_F_stopped_for_review',exception=repr(ex),traceback=traceback.format_exc()[-3500:],promotion=False);raise
