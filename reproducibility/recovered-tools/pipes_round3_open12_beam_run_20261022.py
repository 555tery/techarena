import sys,json,subprocess,time,tempfile
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;folder=Path('/tmp/pipes_open12_guard5_beam_20261022');m=json.loads((folder/'manifest.json').read_text())
assert any(q.get('type')=='boundary_native_speed_result'for q in b.rows())
assert not any(q.get('type')=='open12_beam_plan'for q in b.rows()),'one fixed beam run; no automatic rerun'
assert b.sha((folder/'beam.cpp').read_bytes())==m['beam_cpp_sha256']=='588c44a53635fa0d6556168567ba72dcc475adb5811d56038c7ddc3038c17c04'
assert b.sha((folder/'runtime_source.cpp').read_bytes())==m['hashes']['RUNTIME_SHA']
assert b.sha((folder/'prepared.in').read_bytes())==m['hashes']['PREPARED_SHA']
assert (m['width'],m['fixed_commands'],m['search_deadline_seconds'])==(16,154,180)
b.record(dict(type='open12_beam_plan',manifest_sha256=b.sha((folder/'manifest.json').read_bytes()),source_sha256=m['beam_cpp_sha256'],
 build_argv=m['build_argv'],run_argv=m['run_argv'],width=16,fixed_commands=154,search_deadline_seconds=180,
 baseline_audit_failure_stops=True,no_partial_candidate=True,no_parameter_tuning=True,final24_still_sealed=True,promotion=False))
t=time.monotonic();q=subprocess.run(m['build_argv'],capture_output=True,text=True)
b.record(dict(type='open12_beam_build',status=q.returncode,wall_s=time.monotonic()-t,stderr=q.stderr[-3000:],binary_sha256=b.sha((folder/'beam').read_bytes())if q.returncode==0 else None))
assert q.returncode==0,q.stderr
t=time.monotonic();q=subprocess.run(m['run_argv'],capture_output=True,text=True);r=json.loads(q.stdout)
r.update(type='open12_beam_execution',returncode=q.returncode,wall_s=time.monotonic()-t,stderr=q.stderr[-3000:],
 source_sha256=m['beam_cpp_sha256'],scope='one fixed offline public12 width16 beam under unchanged guard5; no online/generalization/optimality claim',promotion=False)
b.record(r)
if q.returncode==0 and r.get('status')=='ok'and r.get('gain'):
 meta=next(x for x in b.inputs('archive')if x.get('public_number')==12);assert meta['final_occupied_length_m']==m['F']
 response=Path(r['response_file'])
 with tempfile.TemporaryDirectory(prefix='pipes-open12-beam-official-')as td:checked=b._official(meta,response,Path(td))
 assert checked['trench_length_m']==r['finalT']
 r.update(official_complete_response_checker=True,official_score=checked,response_sha256=b.sha(response.read_bytes()))
r['type']='open12_beam_result';b.record(r);print('OPEN12_BEAM_RESULT',json.dumps(r),flush=True)
assert q.returncode==0 and r.get('status')=='ok','baseline audit or candidate validity failure; stop and root review'
