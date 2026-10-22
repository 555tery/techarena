import sys,json,time,traceback,collections
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='boundary-index';SHA='9360f94830f5556dbbeed937f4fc1930398ddb67d4efdbebe2f46ad5f0b8aafc';BIN='654ea00c36754726ad256ded769683b28fd6324704043b31ad98c30fe04a9cf3';SUITE='boundary-full3029'
def run():
 a.pins();s,bi=b.artifact(K,'cj');assert b.sha(s.read_bytes())==SHA and b.sha(bi.read_bytes())==BIN
 assert any(q.get('type')=='boundary_native_speed_result'and q.get('passes_fixed_native_gate')for q in b.rows())
 assert any(q.get('type')=='boundary_stress_result'and q.get('status')=='ok'for q in b.rows())
 ms=b.inputs('archive');assert len(ms)==3029
 for m in ms:assert m['baseline_record_source_sha256']==a.CPP_SHA and m['baseline_record_binary_sha256']==a.CPP_BIN_SHA and m['baseline_response_sha256']
 if not any(q.get('type')=='boundary_full3029_plan'for q in b.rows()):b.record(dict(type='boundary_full3029_plan',count=3029,source_sha256=SHA,binary_sha256=BIN,reference_cpp_source_sha256=a.CPP_SHA,reference_cpp_binary_sha256=a.CPP_BIN_SHA,reject_any_response_hash_difference=True,cpp_not_rerun=True,reuse_only_identical_source_binary_input_complete_response=True,envvariant='cjProcessorNum=1',pause_cpu_s=4.5,strict_rss_mib=230,final24_still_sealed=True,promotion=False))
 t=time.monotonic();qs=[]
 for j,m in enumerate(ms):
  q=b.batch(m,K,SUITE,'cj');b.cj_resource_review(q)
  assert q['source_sha256']==SHA and q['binary_sha256']==BIN and q['test_sha256']==m['test_sha256']
  assert q['response_sha256']==m['baseline_response_sha256'],('Boundary exact parity rejected',m['id'])
  assert q['solver_peak_rss_mb']<230.,q
  qs.append(q)
  if(j+1)%40==0 or j+1==len(ms):print('BOUNDARY_FULL',j+1,len(ms),'elapsed',round(time.monotonic()-t,2),'maxcpu',max(x['solver_cpu_total_s']for x in qs),'maxrss',max(x['solver_peak_rss_mb']for x in qs),flush=True)
 assert b.sha(s.read_bytes())==SHA and b.sha(bi.read_bytes())==BIN
 r=b.record(dict(type='boundary_full3029_result',status='ok',count=len(qs),source=str(s),source_sha256=SHA,binary_sha256=BIN,all_actual_complete_responses_exact=True,reference_cpp_source_sha256=a.CPP_SHA,reference_cpp_binary_sha256=a.CPP_BIN_SHA,cpp_not_rerun=True,zero_invalid_or_local_limit_violations=True,maximum_cpu_s=max(x['solver_cpu_total_s']for x in qs),maximum_rss_mib=max(x['solver_peak_rss_mb']for x in qs),total_cpu_s=sum(x['solver_cpu_total_s']for x in qs),validation_counts=dict(collections.Counter(q['validation']for q in qs)),wall_s=time.monotonic()-t,envvariant='cjProcessorNum=1',resource_scope='actual candidate process user+system/RSS; batch full archive plus separately fixed native20 gate',final24_still_sealed=True,env_latefork_pending=True,promotion=False))
 print('BOUNDARY_FULL_RESULT',json.dumps(r),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:b.record(dict(type='boundary_full3029_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2000:],promotion=False));raise
