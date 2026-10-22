import sys,json,math,statistics,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
import pipes_speed_chain_round3_20261022 as chain
b=a.b
MODES=['H','B','M'];KINDS={m:'speed-'+m.lower()for m in MODES}
EXPECTED={'H':'e96a0ebe94ff7d8a5e46e6ad08090e354d8925a3549bc6d088768425d3785e9f',
 'B':'bb5917cf8baffd6da5ec247152b73371e9b7faf81224a95667b6a701eb215407',
 'M':'426a00aec06ae1587d713855a8f68e323e9369a9597b30be1046d6c838d9407f'}
PARENT='d09c660595c2f1ed33c502f5e34c1ed5cc57d83ba8aeed0bd9aff69fc28b5470'

def emit(label,q):print(label,json.dumps(q,ensure_ascii=False),flush=True)
def run():
 a.pins();assert b.sha(b.BASE_UNCACHED_CJ.read_bytes())==PARENT
 results=[q for q in b.rows()if q.get('type')=='development_screen_result'];assert len(results)==3 and all(not q['passes_fixed_gate']for q in results)
 assert any(q.get('type')=='oracle_class_pilot_result'for q in b.rows())
 prior=next(q for q in b.read_jsonl(a.P/'records.jsonl')if q.get('type')=='ring_pilot_panel_freeze')
 mc=[q['id']for q in prior['mc_active_cases']];large=prior['general_heavy_ids'];ids=mc+large
 assert len(ids)==len(set(ids))==20 and all(q['mc_decisions']==32 for q in prior['mc_active_cases'])
 meta={m['id']:m for m in b.inputs('archive')};assert all(i in meta for i in ids)
 plan=dict(type='exact_speed_pilot_plan',baseline_cached_source_sha256=a.CJ_SHA,baseline_binary_sha256=a.CJ_BIN_SHA,
  uncached_parent_source_sha256=PARENT,composer_sha256=b.sha(Path('/tmp/pipes_speed_chain_round3_20261022.py').read_bytes()),
  patches=[dict(path=p,sha256=s)for p,s in chain.PATCHES],mode_prefix_lengths={'H':2,'B':3,'M':4},
  expected_uncached_source_sha256=EXPECTED,mc_active10=prior['mc_active_cases'],large_live10=large,
  input_test_hashes={i:meta[i]['test_sha256']for i in ids},repeats_per_case=2,paired_observations_per_candidate=40,
  dedicated_fresh_baseline_run_for_every_candidate_pair=True,total_native_runs=240,
  order='repeat1 case even H/B/M, odd M/B/H; repeat2 inverse; pair baseline/candidate order alternates and inverses repeat2',
  gates=dict(all_complete_response_hashes_exact=True,overall_cpu_ratio_geomean_max=.98,worst_per_case_paired_ratio_median_max=1.05,strict_rss_mib=230.,strict_cpu_s=5.,pause_cpu_s=4.5),
  envvariant='cjProcessorNum=1',compiler='Cangjie1.0.5 -O0',one_heavy_worker=True,
  final24_not_used=True,no_threshold_tuning=True,promotion=False)
 previous=[q for q in b.rows()if q.get('type')=='exact_speed_pilot_plan']
 if previous:assert len(previous)==1 and previous[0]==plan
 else:b.record(plan)
 # No other build/mode may alter the baseline. These are exact speed patches only.
 for mode in MODES:
  kind=KINDS[mode]
  if not any(q.get('type')=='build'and q.get('kind')==kind and q.get('language')=='cj'for q in b.rows()):
   text=chain.apply_cj(b.BASE_UNCACHED_CJ.read_text(),mode);assert b.sha(text.encode())==EXPECTED[mode]
   b.compile_cj_variant(kind,'/tmp/pipes_speed_chain_round3_20261022.py',cpp_reference='baseline',
      uncached_source=b.BASE_UNCACHED_CJ,transformer_kwargs={'mode':mode},regenerate_output_cache=True)
  # Label the unchanged CPP reference; no compilation and no new policy.
  if not any(q.get('type')=='build'and q.get('kind')==kind and q.get('language')=='cpp'for q in b.rows()):
   b.record(dict(type='build',kind=kind,language='cpp',source=str(b.BASE_CPP),source_sha256=a.CPP_SHA,
    binary=str(b.BASE_CPP_BIN),binary_sha256=a.CPP_BIN_SHA,status=0,command=None,
    alias_only=True,alias_of='baseline',scope='unchanged CPP policy reference for exact Cj speed patch; no build'))
  source,binary=b.artifact(kind,'cj')
  emit('SPEED_CJ_BUILD_READY',dict(mode=mode,kind=kind,source_sha256=b.sha(source.read_bytes()),binary_sha256=b.sha(binary.read_bytes()),
   uncached_source_sha256=b.sha(b.artifact(kind,'cj-uncached')[0].read_bytes()),all15_uncached_and_cached_cpp_full_hash_parity=True))
 pins={k:dict(source_sha256=b.sha(b.artifact(k,'cj')[0].read_bytes()),binary_sha256=b.sha(b.artifact(k,'cj')[1].read_bytes()))for k in ['baseline']+list(KINDS.values())}
 b.record(dict(type='exact_speed_binary_freeze',artifacts=pins,before_native_pilot=True,gates=plan['gates'],panel_ids=ids,final24_still_sealed=True))
 pairs={mode:[]for mode in MODES};started=time.monotonic()
 for repeat in range(2):
  for j,i in enumerate(ids):
   order=MODES if(repeat+j)%2==0 else list(reversed(MODES))
   for mode in order:
    kind=KINDS[mode];index=MODES.index(mode)
    kinds=['baseline',kind]if(repeat+j+index)%2==0 else[kind,'baseline'];current={}
    for k in kinds:
     r=b.native(meta[i],k,f'speed3-{mode}-repeat{repeat+1}','cj',processor_env='1');b.cj_resource_review(r)
     assert r['binary_sha256']==pins[k]['binary_sha256']and r['source_sha256']==pins[k]['source_sha256']
     assert r['response_sha256']==meta[i]['baseline_response_sha256'],('exact full response hash mismatch',mode,i)
     if r['solver_peak_rss_mb']>=230:
      b.record(dict(type='speed_resource_review_stop',kind=k,id=i,rss_mib=r['solver_peak_rss_mb'],strict_pilot_rss_mib=230.,promotion=False));raise RuntimeError('speed panel RSS gate failed; root review')
     current[k]=r
    base=current['baseline'];candidate=current[kind]
    pairs[mode].append(dict(id=i,repeat=repeat+1,panel='mc-active'if i in mc else'large-live',baseline=base,candidate=candidate,
      ratio=candidate['solver_cpu_total_s']/base['solver_cpu_total_s']))
   if(j+1)%2==0:emit('SPEED_NATIVE_PROGRESS',dict(repeat=repeat+1,completed_cases=j+1,total_cases=20,native_runs_completed=(repeat*20+j+1)*6,elapsed_s=time.monotonic()-started))
 for mode,observations in pairs.items():
  assert len(observations)==40
  ratios=[q['ratio']for q in observations];percase={i:statistics.median(q['ratio']for q in observations if q['id']==i)for i in ids}
  geo=math.exp(statistics.fmean(math.log(x)for x in ratios));worst=max(percase.values());passed=geo<=.98 and worst<=1.05
  describe=lambda subset:dict(pairs=len(subset),geometric_cpu_ratio=math.exp(statistics.fmean(math.log(q['ratio'])for q in subset)),
    weighted_runtime_ratio=sum(meta[q['id']].get('weight',1)*q['candidate']['solver_cpu_total_s']for q in subset)/sum(meta[q['id']].get('weight',1)*q['baseline']['solver_cpu_total_s']for q in subset))
  result=b.record(dict(type='exact_speed_pilot_result',mode=mode,kind=KINDS[mode],n_cases=20,pairs=40,
    overall_geometric_cpu_ratio=geo,worst_per_case_paired_ratio_median=worst,worst_case_id=max(percase,key=percase.get),
    per_case_paired_ratio_median=percase,mc_active=describe([q for q in observations if q['panel']=='mc-active']),large_live=describe([q for q in observations if q['panel']=='large-live']),
    general_weighted_runtime_ratio=sum(meta[q['id']].get('weight',1)*q['candidate']['solver_cpu_total_s']for q in observations)/sum(meta[q['id']].get('weight',1)*q['baseline']['solver_cpu_total_s']for q in observations),
    candidate_total_cpu_s=sum(q['candidate']['solver_cpu_total_s']for q in observations),baseline_total_cpu_s=sum(q['baseline']['solver_cpu_total_s']for q in observations),
    max_candidate_cpu_s=max(q['candidate']['solver_cpu_total_s']for q in observations),max_baseline_cpu_s=max(q['baseline']['solver_cpu_total_s']for q in observations),
    max_candidate_rss_mib=max(q['candidate']['solver_peak_rss_mb']for q in observations),max_baseline_rss_mib=max(q['baseline']['solver_peak_rss_mb']for q in observations),
    all_complete_responses_exact=True,all_within_strict_limits=True,passes_fixed_native_gate=passed,
    artifacts=dict(baseline=pins['baseline'],candidate=pins[KINDS[mode]]),envvariant='cjProcessorNum=1',final24_still_sealed=True,promotion=False,
    interpretation='local M1/macOS20-case exact speed pilot; all process threads counted; conditional sample weights, not hidden distribution or Windows proof; no automatic promotion'))
  emit('EXACT_SPEED_RESULT',result)
 emit('EXACT_SPEED_PILOT_COMPLETE',dict(native_runs=240,final24_solver_evaluations=sum(q.get('id','').startswith('round3-final')and q.get('type')in['evaluation','interactive_evaluation']for q in b.rows()),promotion=False))

if __name__=='__main__':
 try:run()
 except BaseException as ex:
  b.record(dict(type='exact_speed_pilot_stopped_for_review',exception=repr(ex),traceback=traceback.format_exc()[-2500:],promotion=False));raise
