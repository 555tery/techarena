import sys,os,json,subprocess,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;path=Path('/tmp/pipes_boundary_stress_round3_20261022.py');pin='30d2e251e839f06f8c2691c8f86633e7102f863a622c96362f8037f711f4cda5';expected='b931cf0962f146bf33be15db9d92a9e2d7f8eb5ea26e89a05d69202f6687a472'
assert b.sha(path.read_bytes())==pin
assert not any(q.get('type')=='boundary_stress_plan'for q in b.rows()),'one structural stress; no automatic rerun'
module=b._load_module(path);code=module.second_harness();assert b.sha(code.encode())==expected
parent=b._load_module('/tmp/pipes_boundary_hash_round3_20261022.py');assert code.count(parent._CLASSES)==1
b.record(dict(type='boundary_stress_plan',module_sha256=pin,harness_sha256=expected,same_boundary_class_literal=True,
 scope='structural correctness only:200k live/400k keys/max cap and200k historical PIDs with active<=4096/reuse/radix; outside native timing and quality pools',
 compiler='Cangjie1.0.5 -O0',final24_still_sealed=True))
source=b._immutable_source(b.E/'boundary-stress/solution.cj',code);binary=b.E/'bin/boundary-stress-cj'
b._compile_cj_source('boundary-stress','cj-structural',source,binary,module_sha256=pin,harness_sha256=expected)
t=time.monotonic()
with tempfile.TemporaryDirectory(prefix='pipes-boundary-stress-')as td:
 d=Path(td)
 with(d/'out').open('wb')as fo,(d/'err').open('wb')as fe:
  p=subprocess.Popen([str(binary)],stdout=fo,stderr=fe,env={**os.environ,'cjProcessorNum':'1'})
  _,status,usage=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status)
 out=(d/'out').read_text();err=(d/'err').read_text()
passed=p.returncode==0 and 'BOUNDARY_STRESS_DIFFERENTIAL_OK'in out
r=b.record(dict(type='boundary_stress_result',status='ok'if passed else'failed',returncode=p.returncode,stdout=out[-4000:],stderr=err[-4000:],
 source_sha256=expected,binary_sha256=b.sha(binary.read_bytes()),cpu_user_s=usage.ru_utime,cpu_system_s=usage.ru_stime,
 cpu_total_s=usage.ru_utime+usage.ru_stime,peak_rss_mib=usage.ru_maxrss/1048576,wall_s=time.monotonic()-t,
 structural_correctness_only=True,outside_native_speed_quality_pool=True,promotion=False,final24_still_sealed=True))
print('BOUNDARY_STRESS_RESULT',json.dumps(r),flush=True)
assert passed,'Boundary structural stress failed; candidate stopped for root review'
