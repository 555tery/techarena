import sys,json,os,time,subprocess,tempfile,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;PATCH=Path('/tmp/pipes_boundary_hash_round3_20261022.py')
PATCH_SHA='0ba2a1116f5307e5db4598e78a95d9e5757a0695a44601f36ab390de49415805'
HARNESS_SHA='c47ea3d5800f2fe704c97f11a1e9b650004470f5c986a0a5f0af026a6eae0cfe'
UNCACHED_SHA='f1f6240fb7ca7e099408a02bb2aeb9926f4240425afbd7be4eebd25ee6a2ac4a'
KIND='boundary-index'

def run():
 a.pins();assert b.sha(PATCH.read_bytes())==PATCH_SHA
 assert not any(q.get('type')=='boundary_differential_plan'for q in b.rows()),'single staged differential attempt; review instead of automatic retry'
 module=b._load_module(PATCH);code=module.differential_harness();assert b.sha(code.encode())==HARNESS_SHA
 transformed=module.apply_cj(b.BASE_UNCACHED_CJ.read_text());assert b.sha(transformed.encode())==UNCACHED_SHA
 assert module.apply_cj(b.BASE_UNCACHED_CJ.read_text())==transformed
 b.record(dict(type='boundary_differential_plan',transformer_sha256=PATCH_SHA,harness_sha256=HARNESS_SHA,
  baseline_cpp_sha256=a.CPP_SHA,baseline_cpp_binary_sha256=a.CPP_BIN_SHA,baseline_cj_sha256=a.CJ_SHA,
  parent_uncached_sha256=b.BASE_UNCACHED_CJ_SHA,expected_uncached_sha256=UNCACHED_SHA,
  compiler='Cangjie1.0.5 -O0',envvariant='cjProcessorNum=1',one_heavy_worker=True,
  stages='standalone differential, then all15 uncached/cached CPP complete hashes; speed separate after root review',final24_still_sealed=True))
 source=b._immutable_source(b.E/'boundary-differential/solution.cj',code);binary=b.E/'bin/boundary-differential-cj'
 b._compile_cj_source('boundary-differential','cj-differential',source,binary,transformer_sha256=PATCH_SHA,harness_sha256=HARNESS_SHA)
 started=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='pipes-boundary-differential-')as td:
  d=Path(td)
  with (d/'out').open('wb')as fo,(d/'err').open('wb')as fe:
   proc=subprocess.Popen([str(binary)],stdout=fo,stderr=fe,env={**os.environ,'cjProcessorNum':'1'})
   _,status,usage=os.wait4(proc.pid,0);proc.returncode=os.waitstatus_to_exitcode(status)
  stdout=(d/'out').read_text();stderr=(d/'err').read_text()
 ok=proc.returncode==0 and 'BOUNDARY_INDEX_DIFFERENTIAL_OK'in stdout
 r=b.record(dict(type='boundary_differential_result',status='ok'if ok else'failed',returncode=proc.returncode,
  stdout=stdout[-4000:],stderr=stderr[-4000:],solver_cpu_user_s=usage.ru_utime,solver_cpu_system_s=usage.ru_stime,
  solver_cpu_total_s=usage.ru_utime+usage.ru_stime,solver_peak_rss_mb=usage.ru_maxrss/1048576,
  wall_s=time.monotonic()-started,harness_sha256=HARNESS_SHA,binary_sha256=b.sha(binary.read_bytes()),
  standalone_same_index_implementation=True,promotion=False))
 print('BOUNDARY_DIFFERENTIAL',json.dumps(r),flush=True)
 assert ok,'Boundary differential failed; candidate stopped for review'
 b.compile_cj_variant(KIND,PATCH,cpp_reference='baseline',uncached_source=b.BASE_UNCACHED_CJ,regenerate_output_cache=True)
 # An alias labels the unchanged CPP policy for later exact-response native checks; no C++ build.
 b.record(dict(type='build',kind=KIND,language='cpp',source=str(b.BASE_CPP),source_sha256=a.CPP_SHA,
  binary=str(b.BASE_CPP_BIN),binary_sha256=a.CPP_BIN_SHA,status=0,command=None,alias_only=True,alias_of='baseline',
  scope='same unchanged current CPP reference, not a compilation or new quality candidate'))
 artifacts={}
 for lang in ['cj-uncached','cj']:
  s,bi=b.artifact(KIND,lang);artifacts[lang]=dict(source=str(s),source_sha256=b.sha(s.read_bytes()),binary=str(bi),binary_sha256=b.sha(bi.read_bytes()))
 r=b.record(dict(type='boundary_open15_qualification',kind=KIND,transformer_sha256=PATCH_SHA,
  differential_pass=True,all15_uncached_complete_cpp_parent_parity=True,all15_cached_complete_cpp_parent_parity=True,
  cache_from_same_uncached_policy=True,artifacts=artifacts,promotion=False,
  native_speed_not_yet_run=True,structure_stress_not_yet_run=True,full3029_not_yet_run=True,env_latefork_not_yet_run=True,final24_still_sealed=True))
 print('BOUNDARY_OPEN15_QUALIFIED',json.dumps(r),flush=True)

if __name__=='__main__':
 try:run()
 except BaseException as ex:
  b.record(dict(type='boundary_stage_stopped_for_review',exception=repr(ex),traceback=traceback.format_exc()[-3000:],promotion=False));raise
