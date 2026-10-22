import sys,json,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='boundary-index';SHA='9360f94830f5556dbbeed937f4fc1930398ddb67d4efdbebe2f46ad5f0b8aafc';BIN='654ea00c36754726ad256ded769683b28fd6324704043b31ad98c30fe04a9cf3'
def run():
 assert any(q.get('type')=='boundary_full3029_result'and q.get('status')=='ok'for q in b.rows())
 s,bi=b.artifact(K,'cj');assert b.sha(s.read_bytes())==SHA and b.sha(bi.read_bytes())==BIN
 plan=next(q for q in b.rows()if q.get('type')=='boundary_native_speed_plan');meta={m['id']:m for m in b.inputs('archive')};ids=plan['large_live10']
 for j,i in enumerate(ids):
  for env in([None,'1']if j%2==0 else['1',None]):
   r=b.native(meta[i],K,'env-panel-archive','cj',processor_env=env);b.cj_resource_review(r)
   assert r['response_sha256']==meta[i]['baseline_response_sha256']and r['solver_peak_rss_mb']<230
  print('BOUNDARY_ENV',j+1,len(ids),flush=True)
 print('BOUNDARY_ENV_RESULT',json.dumps(b.native_env_pairs(K,ids,'archive','cj')),flush=True)
 h,_=b.harness();path=Path('/tmp/pipes_round2_protocol_20261022/late-cache-fork-199999.in')
 m=dict(h.parse_test(path),id='round2-late-cache-fork-199999',split='protocol',test_file=str(path),provenance='protocol-not-quality')
 refs=[q for q in b.read_jsonl(a.P/'records.jsonl')if q.get('type')=='evaluation'and q.get('id')==m['id']and q.get('language')=='cpp'and q.get('source_sha256')==a.CPP_SHA and q.get('binary_sha256')==a.CPP_BIN_SHA and q.get('test_sha256')==m['test_sha256']and q.get('status')=='ok'];assert refs
 ref=refs[-1];qs=[]
 for lang in['cj','cj-uncached']:
  for env in['1',None]:
   r=b.native(m,K,'boundary-late-cache-fork',lang,processor_env=env);b.cj_resource_review(r)
   assert r['response_sha256']==ref['response_sha256']and r['solver_peak_rss_mb']<230
   qs.append(r)
 r=b.record(dict(type='boundary_env_latefork_qualification',source=str(s),source_sha256=SHA,binary_sha256=BIN,heavy_env_panel10_complete=True,late_fork_matching_commands=199999,late_fork_divergence_command=200000,late_test_sha256=m['test_sha256'],late_cached_uncached_env1_UNSET_complete_cpp_response_parity=True,cpp_reference_source_sha256=a.CPP_SHA,cpp_reference_binary_sha256=a.CPP_BIN_SHA,cpp_reference_reused=True,late_maximum_cpu_s=max(q['solver_cpu_total_s']for q in qs),late_maximum_rss_mib=max(q['solver_peak_rss_mb']for q in qs),Open15_cached_uncached_complete_response_parity_already_passed=True,all_within_limits=True,final24_still_sealed=True,promotion=False))
 print('BOUNDARY_ENVFORK_RESULT',json.dumps(r),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:b.record(dict(type='boundary_envfork_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2000:]));raise
