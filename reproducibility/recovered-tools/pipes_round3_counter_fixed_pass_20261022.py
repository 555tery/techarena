import sys,json,subprocess,time
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b
path=Path('/tmp/pipes_parity_counter_screen395_20261022.py');pin='e2792e4023cb0157af421920055f11a4e863488afd12a837343ed451eede5185'
assert b.sha(path.read_bytes())==pin
assert len([q for q in b.rows()if q.get('type')=='exact_speed_pilot_result'])==3
assert not any(q.get('type')=='parity_counter_screen395_plan'and q.get('source_sha256')==pin for q in b.rows()),'one corrected counter pass only; review instead of rerun'
b.record(dict(type='parity_counter_screen395_plan',source=str(path),source_sha256=pin,detail_limit=12,
 scope='input-only counter reconstruction on frozen screen395, no geometry/policy/KPI replay, no solver, no final24',native_timings_complete=True,root_authorized_corrected_retry=True,previous_attempt_failed_before_input_scan=True))
args=[sys.executable,str(path),'--detail-limit','12'];started=time.monotonic();p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
scopes=[];summaries={};details=[]
for line in p.stdout:
 print(line.rstrip(),flush=True)
 label,payload=line.rstrip().split(' ',1);obj=json.loads(payload)
 if label=='scope':scopes.append(obj)
 elif label.startswith('summary:'):summaries[label[len('summary:'):]]=obj
 elif label=='low_kpi_latched_case':details.append(obj)
stderr=p.stderr.read();returncode=p.wait()
r=b.record(dict(type='parity_counter_screen395_result',source_sha256=pin,returncode=returncode,wall_s=time.monotonic()-started,
 scope=scopes,summaries=summaries,details=details,stderr=stderr[-3000:],
 interpretation='counter-only diagnostic, scopes explicitly distinguish exact/imported, no-core counterfactual and unknown handoff; suspicious tags descriptive, not causal; no unlatch implementation',
 final24_solver_outputs_still_sealed=True))
assert returncode==0,(returncode,stderr)
print('COUNTER_PASS_COMPLETE',json.dumps(dict(returncode=returncode,wall_s=r['wall_s'],groups=len(summaries),details=len(details))),flush=True)
