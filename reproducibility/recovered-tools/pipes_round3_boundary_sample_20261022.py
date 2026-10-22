import sys,os,json,subprocess,tempfile,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='boundary-index';SHA='9360f94830f5556dbbeed937f4fc1930398ddb67d4efdbebe2f46ad5f0b8aafc';BIN='654ea00c36754726ad256ded769683b28fd6324704043b31ad98c30fe04a9cf3'
def run():
 assert not any(q.get('type')=='boundary_sampling_profile'for q in b.rows()),'one shot already recorded'
 s,bi=b.artifact(K,'cj');assert b.sha(s.read_bytes())==SHA and b.sha(bi.read_bytes())==BIN
 plan=next(q for q in b.rows()if q.get('type')=='boundary_native_speed_plan');large=plan['large_live10']
 timed=[q for q in b.rows()if q.get('type')=='interactive_evaluation'and q.get('kind')==K and q.get('id')in large and q.get('suite','').startswith('boundary-native-repeat')and q.get('binary_sha256')==BIN]
 chosen=max(timed,key=lambda q:q['solver_cpu_total_s']);m=next(m for m in b.inputs('archive')if m['id']==chosen['id'])
 assert b.sha(Path(m['test_file']).read_bytes())==m['test_sha256']
 sample=Path('/tmp/pipes_boundary_sample_20261022.txt');assert not sample.exists();assert os.access('/usr/bin/sample',os.X_OK)
 b.record(dict(type='boundary_sampling_plan',id=m['id'],test_sha256=m['test_sha256'],source_sha256=SHA,binary_sha256=BIN,prior_cpu_s=chosen['solver_cpu_total_s'],envvariant='cjProcessorNum=1',duration_s=1,not_timegate=True,single_run=True,promotion=False))
 with tempfile.TemporaryDirectory(prefix='pipes-boundary-profile-')as td:
  d=Path(td);(d/'unused_answer.txt').write_text('');rd,wr=os.pipe()
  with (d/'native.err').open('wb')as err:
   p=subprocess.Popen([str(b.NATIVE),str(Path(m['test_file']).resolve()),'judge_output.txt','unused_answer.txt','interactor_report.txt','5','240','--',str(bi)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err,cwd=d,env={**os.environ,'cjProcessorNum':'1','PIPES_NATIVE_CONTROL_FD':str(wr)},pass_fds=(wr,),start_new_session=True)
   os.close(wr)
   with os.fdopen(rd,'rb')as control:
    pid=int(control.readline());time.sleep(.35)
    sp=subprocess.run(['/usr/bin/sample',str(pid),'1','-file',str(sample)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    p.wait(timeout=240);remaining=control.read();report=json.loads(remaining)
  assert report['solver_pid']==pid and p.returncode==0 and not report.get('error') and report['saw_zero']and report['solver_returncode']==report['official_returncode']==0 and report['has_usage'],report
  assert report['commands']==m['operation_count']+1
  response=b.sha((d/'judge_output.txt').read_bytes());assert response==m['baseline_response_sha256']
  cpu=report['cpu_user_s']+report['cpu_system_s'];rss=report['maxrss_raw']/1048576
  r=b.record(dict(type='boundary_sampling_profile',id=m['id'],source_sha256=SHA,binary_sha256=BIN,test_sha256=m['test_sha256'],response_sha256=response,status='ok',full_response_parity=True,authentic_solver_pid=pid,native_report=report,solver_cpu_total_s=cpu,solver_peak_rss_mb=rss,sample_returncode=sp.returncode,sample_file=str(sample)if sample.exists()else None,sample_stdout=sp.stdout.decode(errors='replace')[-1500:],sample_stderr=sp.stderr.decode(errors='replace')[-1500:],envvariant='cjProcessorNum=1',compiler='Cangjie1.0.5 -O0',not_timegate=True,promotion=False))
  print(json.dumps(r),flush=True);assert cpu<4.5 and rss<230
if __name__=='__main__':
 try:run()
 except BaseException as ex:b.record(dict(type='boundary_sampling_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2000:]));raise
