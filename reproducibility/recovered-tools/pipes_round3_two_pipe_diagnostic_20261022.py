import sys,json,subprocess,time,tempfile
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;folder=Path('/tmp/pipes_two_pipe_ejection_deadline_20261022')
assert any(q.get('type')=='boundary_open15_qualification'for q in b.rows())
assert not any(q.get('type')=='two_pipe_deadline_plan'for q in b.rows()),'one fixed bounded run; no automatic rerun'
m=json.loads((folder/'manifest.json').read_text())
pins=[(Path('/tmp/pipes_two_pipe_ejection_deadline_20261022.py'),'5b55848a4a5011fe32d33e987148a8327b33770146042dd5227abe6e738ddd51'),
(folder/'auditor.cpp','5ec299afb2133359a795530e04e335e18ed2d4770bdb4ee070b1ce5dc67fef12'),
(folder/'search.py','88430cc5c37ebc3b04bba3310a42a6bdbe2cfb58be8b7f34448cbd8c245d4dad'),
(folder/'runtime_source.cpp',m['hashes']['RUNTIME_SHA']),(folder/'prepared.in',m['hashes']['PREPARED_SHA']),
(Path(m['IntervalIndex_source']),m['IntervalIndex_sha256'])]
for path,pin in pins:assert b.sha(path.read_bytes())==pin,str(path)
assert m['search_deadline_seconds']==180 and m['budget_pairs']==4096 and m['fixed_commands']==10000 and m['protected_T_commands']==25000
b.record(dict(type='two_pipe_deadline_plan',manifest_sha256=b.sha((folder/'manifest.json').read_bytes()),
 source_pins={str(path):pin for path,pin in pins},build_argv=m['build_argv'],run_argv=m['run_argv'],search_deadline_seconds=180,
 finish_current_full_audit=True,baseline_and_second_best_audit_outside_deadline=True,
 scope='one fixed bounded two-relocation public15 diagnostic; no beam/global optimality claim; no production mutation',promotion=False))
t=time.monotonic();q=subprocess.run(m['build_argv'],capture_output=True,text=True)
b.record(dict(type='two_pipe_deadline_build',status=q.returncode,wall_s=time.monotonic()-t,stderr=q.stderr[-3000:],
 binary_sha256=b.sha((folder/'auditor').read_bytes())if q.returncode==0 else None))
assert q.returncode==0,q.stderr
t=time.monotonic();q=subprocess.run(m['run_argv'],capture_output=True,text=True);r=json.loads(q.stdout)
r.update(type='two_pipe_deadline_execution',returncode=q.returncode,wall_s=time.monotonic()-t,stderr=q.stderr[-3000:],
 scope='bounded two-pipe diagnostic on one public15, not an online candidate or global impossibility proof',promotion=False)
b.record(r)
if q.returncode==0 and r.get('status')=='ok'and r.get('gain'):
 meta=next(m for m in b.inputs('archive')if m.get('public_number')==15)
 output=r['output'];response=Path(output['response_file'])
 with tempfile.TemporaryDirectory(prefix='pipes-two-pipe-official-')as td:checked=b._official(meta,response,Path(td))
 assert checked['trench_length_m']==r['finalT']
 r.update(official_complete_response_checker=True,official_score=checked,response_sha256=b.sha(response.read_bytes()))
r['type']='two_pipe_deadline_result';b.record(r);print('TWO_PIPE_DEADLINE_RESULT',json.dumps(r),flush=True)
assert q.returncode==0 and r.get('status')=='ok',r
