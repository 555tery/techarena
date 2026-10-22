import sys,json,math,statistics,time,traceback
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='boundary-index';SHA='9360f94830f5556dbbeed937f4fc1930398ddb67d4efdbebe2f46ad5f0b8aafc';BIN='654ea00c36754726ad256ded769683b28fd6324704043b31ad98c30fe04a9cf3'
def run():
 a.pins();s,bi=b.artifact(K,'cj');assert b.sha(s.read_bytes())==SHA and b.sha(bi.read_bytes())==BIN
 assert any(q.get('type')=='boundary_open15_qualification'for q in b.rows())
 assert any(q.get('type')=='boundary_stress_result'and q.get('status')=='ok'for q in b.rows())
 assert any(q.get('type')=='two_pipe_deadline_result'and q.get('status')=='ok'for q in b.rows())
 prior=next(q for q in b.read_jsonl(a.P/'records.jsonl')if q.get('type')=='ring_pilot_panel_freeze')
 mc=[q['id']for q in prior['mc_active_cases']];large=prior['general_heavy_ids'];ids=mc+large;assert len(ids)==len(set(ids))==20
 meta={m['id']:m for m in b.inputs('archive')}
 plan=dict(type='boundary_native_speed_plan',candidate_source_sha256=SHA,candidate_binary_sha256=BIN,
  baseline_source_sha256=a.CJ_SHA,baseline_binary_sha256=a.CJ_BIN_SHA,
  mc_active10=mc,large_live10=large,test_hashes={i:meta[i]['test_sha256']for i in ids},
  repeats=2,fresh_pairs=40,native_runs=80,pair_order='baseline/candidate on even case in repeat1, inverse on odd; entire pair order inversed repeat2',
  gates=dict(all_full_response_hashes_exact=True,geometric_cpu_ratio_max=.98,worst_case_paired_median_ratio_max=1.05,strict_rss_mib=230.,strict_cpu_s=5.,review_pause_cpu_s=4.5),
  exploratory_structural_candidate=True,worst_case_O1_not_proved=True,envvariant='cjProcessorNum=1',compiler='Cangjie1.0.5 -O0',
  final24_not_used=True,promotion=False,no_threshold_tuning=True)
 old=[q for q in b.rows()if q.get('type')=='boundary_native_speed_plan']
 if old:assert len(old)==1 and old[0]==plan
 else:b.record(plan)
 observations=[];t=time.monotonic()
 for repeat in range(2):
  for j,i in enumerate(ids):
   current={}
   for kind in(['baseline',K]if(repeat+j)%2==0 else[K,'baseline']):
    q=b.native(meta[i],kind,f'boundary-native-repeat{repeat+1}','cj',processor_env='1');b.cj_resource_review(q)
    assert q['source_sha256']==(a.CJ_SHA if kind=='baseline'else SHA)
    assert q['binary_sha256']==(a.CJ_BIN_SHA if kind=='baseline'else BIN)
    assert q['response_sha256']==meta[i]['baseline_response_sha256'],(kind,i,'complete CPP/parent hash mismatch')
    assert q['solver_peak_rss_mb']<230.,('strict boundary RSS gate',kind,i,q['solver_peak_rss_mb'])
    current[kind]=q
   base,candidate=current['baseline'],current[K]
   observations.append(dict(id=i,repeat=repeat+1,panel='mc-active'if i in mc else'large-live',baseline=base,candidate=candidate,
    ratio=candidate['solver_cpu_total_s']/base['solver_cpu_total_s']))
   if(j+1)%2==0:print('BOUNDARY_NATIVE_PROGRESS',repeat+1,j+1,20,'runs',(repeat*20+j+1)*2,'elapsed',time.monotonic()-t,flush=True)
 ratios=[q['ratio']for q in observations];percase={i:statistics.median(q['ratio']for q in observations if q['id']==i)for i in ids}
 geo=math.exp(statistics.fmean(math.log(x)for x in ratios));worst=max(percase.values());passed=geo<=.98 and worst<=1.05
 describe=lambda subset:dict(pairs=len(subset),geometric_cpu_ratio=math.exp(statistics.fmean(math.log(q['ratio'])for q in subset)),
  weighted_runtime_ratio=sum(meta[q['id']].get('weight',1.)*q['candidate']['solver_cpu_total_s']for q in subset)/sum(meta[q['id']].get('weight',1.)*q['baseline']['solver_cpu_total_s']for q in subset))
 result=b.record(dict(type='boundary_native_speed_result',kind=K,source=str(s),source_sha256=SHA,binary_sha256=BIN,n_cases=20,pairs=40,native_runs=80,
  geometric_cpu_ratio=geo,worst_per_case_paired_ratio_median=worst,worst_case_id=max(percase,key=percase.get),per_case_paired_ratio_median=percase,
  mc_active=describe([q for q in observations if q['panel']=='mc-active']),large_live=describe([q for q in observations if q['panel']=='large-live']),
  weighted_runtime_ratio=sum(meta[q['id']].get('weight',1.)*q['candidate']['solver_cpu_total_s']for q in observations)/sum(meta[q['id']].get('weight',1.)*q['baseline']['solver_cpu_total_s']for q in observations),
  candidate_total_cpu_s=sum(q['candidate']['solver_cpu_total_s']for q in observations),baseline_total_cpu_s=sum(q['baseline']['solver_cpu_total_s']for q in observations),
  max_candidate_cpu_s=max(q['candidate']['solver_cpu_total_s']for q in observations),max_baseline_cpu_s=max(q['baseline']['solver_cpu_total_s']for q in observations),
  max_candidate_rss_mib=max(q['candidate']['solver_peak_rss_mb']for q in observations),max_baseline_rss_mib=max(q['baseline']['solver_peak_rss_mb']for q in observations),
  all_complete_responses_exact=True,all_within_strict_limits=True,passes_fixed_native_gate=passed,wall_s=time.monotonic()-t,
  envvariant='cjProcessorNum=1',compiler='Cangjie1.0.5 -O0',exploratory_structural_candidate=True,full3029_not_yet_run=True,env_latefork_not_yet_run=True,
  no_competing_jobs=True,final24_still_sealed=True,promotion=False,
  interpretation='local M1/macOS selected20-case exact speed pilot; all process threads counted; deterministic hash has no worst-caseO1 proof; requires full archive/env/latefork before promotion'))
 print('BOUNDARY_NATIVE_RESULT',json.dumps(result),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:
  b.record(dict(type='boundary_native_stopped_for_review',exception=repr(ex),traceback=traceback.format_exc()[-2500:],promotion=False));raise
