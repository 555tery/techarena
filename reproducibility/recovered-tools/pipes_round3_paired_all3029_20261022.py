"""One serial paired quality audit: exact trial22 vs current G4, control G5."""
import sys,json,time,subprocess,traceback,statistics,collections,math,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='paired-all3029';OLD='paired-trial22';NEW='final-online-audit';SUITE='paired-all3029'
OLDSHA='988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
NEWSHA='1af5bb2492546b8597bd7771b28844839aa79c90233579fe1bc4d44536135a69'
source=b.R/'research-campaigns/20261018T141843+0700-autonomous/releases'/OLDSHA/'solution.cpp'
def record(t,**kw):return b.record(dict(type=t,kind=K,**kw))
def run():
 a.pins();assert b.sha(source.read_bytes())==OLDSHA
 ns,nb=b.artifact(NEW,'cpp');assert b.sha(ns.read_bytes())==a.CPP_SHA and b.sha(nb.read_bytes())==NEWSHA
 ms=b.inputs('archive');assert len(ms)==3029 and len({m['id']for m in ms})==len({m['test_sha256']for m in ms})==3029
 assert all(m['split']=='archive'for m in ms)
 manifestsha=b.sha(b.MANIFEST.read_bytes());membership=[dict(id=m['id'],test_sha256=m['test_sha256'])for m in ms]
 member_sha=b.sha(json.dumps(membership,sort_keys=True,separators=(',',':')).encode())
 refs={}
 for r in b.read_jsonl(a.P/'records.jsonl')+b.rows():
  if r.get('type')=='evaluation'and r.get('language')=='cpp'and r.get('source_sha256')==a.CPP_SHA and r.get('binary_sha256')==a.CPP_BIN_SHA and r.get('status')=='ok':refs[(r['id'],r['test_sha256'])]=r
 c={m['id']:refs[(m['id'],m['test_sha256'])]for m in ms}
 assert all(c[m['id']]['response_sha256']==m['baseline_response_sha256']and c[m['id']]['kpi']==m['baseline_kpi']for m in ms)
 binary=b.E/'bin/paired-trial22-cpp';command=['clang++','-O2','-std=c++17',str(source),'-o',str(binary)]
 assert not any(r.get('type')=='paired_all3029_freeze'for r in b.rows()),'single frozen attempt; no automatic restart'
 record('paired_all3029_freeze',before_first_new_solver_execution=True,count=3029,split='archive',manifest=str(b.MANIFEST),manifest_sha256=manifestsha,ordered_membership_sha256=member_sha,
  old_source=str(source),old_source_sha256=OLDSHA,old_compile_command=command,current_source_sha256=a.CPP_SHA,current_G4_binary_sha256=NEWSHA,current_G4_flags=['-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=4'],
  control_G5_binary_sha256=a.CPP_BIN_SHA,control_G5_exact_actual_references=3029,old_reuse_forbidden=True,new_reuse_only_identical_source_binary_input_actual_complete_response=True,excluded=['sealed_final24','sensitivity_development36','development12'],one_serial_heavy_worker=True,no_Cj=True,no_UI=True,no_tuning=True,timing_scope='quality audit; reused control/127 current measurements prevent paired speed inference')
 print('PAIRED_FROZEN3029',member_sha,flush=True)
 q=subprocess.run(command,capture_output=True,text=True,timeout=90);assert q.returncode==0,q.stderr
 oldbinsha=b.sha(binary.read_bytes());b.record(dict(type='build',kind=OLD,language='cpp',source=str(source),source_sha256=OLDSHA,binary=str(binary),binary_sha256=oldbinsha,command=command,status=0,stderr=q.stderr[-1000:]))
 record('paired_all3029_binary_freeze',old_source_sha256=OLDSHA,old_binary_sha256=oldbinsha,current_G4_source_sha256=a.CPP_SHA,current_G4_binary_sha256=NEWSHA,control_G5_binary_sha256=a.CPP_BIN_SHA,compiler=shutil.which('clang++'),compiler_version=subprocess.check_output(['clang++','--version'],text=True).splitlines()[0])
 print('PAIRED_BUILD',oldbinsha,flush=True)
 vals={OLD:{},NEW:{}};invalid={OLD:[],NEW:[]};t=time.monotonic();running=[None]
 official=b._official
 def audited_official(meta,output,directory):
  try:return official(meta,output,directory)
  except Exception as e:
   record('paired_all3029_official_invalid',solver_kind=running[0],id=meta['id'],test_sha256=meta['test_sha256'],response_sha256=b.sha(output.read_bytes()),error=repr(e)[:2500]);raise
 b._official=audited_official
 for j,m in enumerate(ms):
  for k in ([OLD,NEW]if j%2==0 else[NEW,OLD]):
   running[0]=k
   try:
    r=b.batch(m,k,SUITE,'cpp');assert r['source_sha256']==(OLDSHA if k==OLD else a.CPP_SHA)and r['binary_sha256']==(oldbinsha if k==OLD else NEWSHA)and r['test_sha256']==m['test_sha256']and r['status']=='ok'
    vals[k][m['id']]=r
   except Exception as e:
    invalid[k].append(m['id']);record('paired_all3029_case_failure',solver_kind=k,id=m['id'],test_sha256=m['test_sha256'],error=repr(e)[:2500]);print('PAIRED_CASE_FAILURE',k,m['id'],repr(e)[:300],flush=True)
  if(j+1)%80==0 or j+1==len(ms):print('PAIRED3029',j+1,3029,'elapsed',round(time.monotonic()-t,1),'validOld',len(vals[OLD]),'validG4',len(vals[NEW]),'invalid',sum(map(len,invalid.values())),flush=True)
 assert b.sha(source.read_bytes())==OLDSHA and b.sha(binary.read_bytes())==oldbinsha and b.sha(ns.read_bytes())==a.CPP_SHA and b.sha(nb.read_bytes())==NEWSHA and b.sha(b.MANIFEST.read_bytes())==manifestsha
 def desc(x,y,ids):
  valid=[i for i in ids if i in x and i in y];ds=[x[i]['kpi']-y[i]['kpi']for i in valid]
  return dict(n_requested=len(ids),n_paired_valid=len(ds),wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),losses=sum(d< -1e-12 for d in ds),mean=statistics.fmean(ds)if ds else None,median=statistics.median(ds)if ds else None,minimum=min(ds)if ds else None,maximum=max(ds)if ds else None,candidate_mean=statistics.fmean(x[i]['kpi']for i in valid)if ds else None,baseline_mean=statistics.fmean(y[i]['kpi']for i in valid)if ds else None,complete_response_ties=sum(x[i]['response_sha256']==y[i]['response_sha256']for i in valid))
 groups={'all3029':[m['id']for m in ms],'Open15':[m['id']for m in ms if m.get('public_number')],'nonpublic3014':[m['id']for m in ms if not m.get('public_number')]}
 for field in ['provenance','family','stratum']:
  for value in sorted({str(m[field])for m in ms if m.get(field)is not None}):groups[field+':'+value]=[m['id']for m in ms if str(m.get(field))==value]
 for label,fn in [('short<=200',lambda n:n<=200),('medium201..99999',lambda n:200<n<100000),('long>=100000',lambda n:n>=100000)]:groups['length:'+label]=[m['id']for m in ms if fn(m['operation_count'])]
 comparisons={label:{g:desc(x,y,ids)for g,ids in groups.items()}for label,x,y in [('G4_vs_trial22',vals[NEW],vals[OLD]),('G5_vs_trial22',c,vals[OLD]),('G4_vs_G5',vals[NEW],c)]}
 public=[m for m in ms if m.get('public_number')];opens={label:math.fsum(m['weight']*v[m['id']]['kpi']for m in public if m['id']in v)for label,v in [('trial22',vals[OLD]),('G4',vals[NEW]),('G5',c)]}
 worst={}
 for label,x,y in [('G4_vs_trial22',vals[NEW],vals[OLD]),('G5_vs_trial22',c,vals[OLD]),('G4_vs_G5',vals[NEW],c)]:
  ranks=sorted([(x[m['id']]['kpi']-y[m['id']]['kpi'],m)for m in ms if m['id']in x and m['id']in y],key=lambda z:z[0])
  worst[label]=[dict(id=m['id'],delta=d,candidate_kpi=x[m['id']]['kpi'],baseline_kpi=y[m['id']]['kpi'],candidate_T=x[m['id']]['trench_length_m'],baseline_T=y[m['id']]['trench_length_m'],family=m.get('family'),provenance=m.get('provenance'),n=m['operation_count'])for d,m in ranks[:8]]
 result=record('paired_all3029_result',count=3029,valid_counts={k:len(v)for k,v in vals.items()},invalid_ids=invalid,old_source_sha256=OLDSHA,old_binary_sha256=oldbinsha,current_source_sha256=a.CPP_SHA,G4_binary_sha256=NEWSHA,G5_binary_sha256=a.CPP_BIN_SHA,manifest_sha256=manifestsha,ordered_membership_sha256=member_sha,actual_Open15_weighted=opens,comparisons=comparisons,worst=worst,validation_counts={k:dict(collections.Counter(r['validation']for r in v.values()))for k,v in vals.items()},CPP_resources_descriptive={k:dict(total_cpu_s=sum(r['solver_cpu_total_s']for r in v.values()),maximum_cpu_s=max(r['solver_cpu_total_s']for r in v.values()),maximum_rss_mib=max(r['solver_peak_rss_mb']for r in v.values()))for k,v in vals.items()},wall_s=time.monotonic()-t,sealed_final24_not_accessed=True,sensitivity36_not_included=True,no_language_port=True,no_platform=True,not_hidden_prediction=True)
 print('PAIRED_RESULT',json.dumps({k:result[k]for k in ['valid_counts','invalid_ids','actual_Open15_weighted','validation_counts','wall_s']}),flush=True)
 for label,q in comparisons.items():print(label,json.dumps({k:q[k]for k in ['all3029','nonpublic3014','length:short<=200','length:medium201..99999','length:long>=100000']}),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:record('paired_all3029_stopped',exception=repr(e),traceback=traceback.format_exc()[-2500:],no_automatic_restart=True);raise
