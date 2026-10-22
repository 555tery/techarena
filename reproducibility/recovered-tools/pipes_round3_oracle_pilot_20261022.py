import sys,json,subprocess,time,tempfile
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as adapter
b=adapter.b
assert {q['kind']for q in b.rows()if q.get('type')=='development_screen_result'}==set(adapter.VARIANTS),'finish the three development screens first'
assert not any(q.get('type')=='oracle_class_pilot_plan'for q in b.rows()),'one-shot pilot already planned/executed; review instead of rerun'
p=Path('/tmp/pipes_oracle_class_pilot_20261022');m=json.loads((p/'manifest.json').read_text())
assert b.sha((p/'pilot.cpp').read_bytes())==m['pilot_cpp_sha256']=='3b446fa878434e10b42f7b4c06791d5b7da0159d777530cb39c84196d47eddda'
assert m['hashes']['PREPARE_SHA']=='39990ad8cbc5619b17c45707fe47dd095f36f81ede8e31e0cc3e8f328d13f0c3'
assert b.sha(Path(m['files']['runtime_source.cpp']).read_bytes())==m['hashes']['RUNTIME_SHA']
assert b.sha(Path(m['files']['prepared.in']).read_bytes())==m['hashes']['PREPARED_INPUT_SHA']
b.record(dict(type='oracle_class_pilot_plan',manifest_sha256=b.sha((p/'manifest.json').read_bytes()),
 pilot_source_sha256=m['pilot_cpp_sha256'],prepare_source_sha256=m['hashes']['PREPARE_SHA'],build_argv=m['build_argv'],run_argv=m['run_argv'],
 scope='one fixed offline public15 oracle-class diagnostic; one future survival bit per PID; no production or round3 quality/final change',one_shot=True))
t=time.monotonic();build=subprocess.run(m['build_argv'],capture_output=True,text=True)
b.record(dict(type='oracle_class_pilot_build',status=build.returncode,wall_s=time.monotonic()-t,stderr=build.stderr[-3000:],pilot_source_sha256=m['pilot_cpp_sha256']))
assert build.returncode==0,build.stderr
t=time.monotonic();q=subprocess.run(m['run_argv'],capture_output=True,text=True,timeout=240);r=json.loads(q.stdout)
r.update(type='oracle_class_pilot_execution',returncode=q.returncode,wall_s=time.monotonic()-t,
 binary_sha256=b.sha(Path(m['run_argv'][0]).read_bytes()),pilot_source_sha256=m['pilot_cpp_sha256'],stderr=q.stderr[-3000:],
 scope='offline public15, one future survival bit per PID; not an online candidate or production integration',promotion=False)
b.record(r)
if q.returncode==0 and r.get('status')=='ok' and r.get('gain'):
 meta=next(x for x in b.inputs('archive')if x.get('public_number')==15)
 with tempfile.TemporaryDirectory(prefix='pipes-round3-oracle-official-')as td:checked=b._official(meta,Path(r['response_file']),Path(td))
 assert checked['trench_length_m']==r['finalT']and abs(checked['kpi']-r['kpi'])<1e-12
 r.update(official_complete_response_checker=True,official_score=checked,response_sha256=b.sha(Path(r['response_file']).read_bytes()))
r['type']='oracle_class_pilot_result';b.record(r);print('ORACLE_CLASS_PILOT_RESULT',json.dumps(r,ensure_ascii=False),flush=True)
assert q.returncode==0 and r.get('status')=='ok',r
