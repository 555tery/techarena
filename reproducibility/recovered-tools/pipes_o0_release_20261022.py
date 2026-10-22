from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,subprocess,sys,tempfile,time
sys.path.insert(0,'/tmp');import pipes_o0_evaluate_20261022 as ev
E=ev.EXP;R=ev.ROOT
records=[json.loads(s)for s in(E/'records.jsonl').open()]
for kind,sha in [('exact','424b6a1b44f540fcc45fcf9745a33ca420723a01ddaa0b195bff5e591dfe265f'),('paced-balanced','f309df0cf30f00c60c167d203e443a73145493670fabfd43d63c0562a92d61f4')]:
 rows={r['id']:r for r in records if r.get('suite')=='full-batch'and r.get('source_sha256')==sha}
 assert len(rows)==2661 and all(r['status']=='ok'for r in rows.values()),(kind,len(rows))
 if kind=='exact':assert all(r['response_equal']for r in rows.values())
source,binary=ev.solver('release');assert hashlib.sha256(source.read_bytes()).hexdigest()=='7fc47aef41b692d77156c4bad61778a9a1fcd11bedf56af450bedacca4eedf6b'
compiler=R/'prototypes/pipes_cj_tle_fix_20261020/toolchain105/cangjie/bin/cjc';sdk=subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip();start=time.monotonic()
p=subprocess.run([str(compiler),'-O0','-Woff','all','--set-runtime-rpath','--sysroot',sdk,'-p',str(source.parent),'-o',str(binary)],capture_output=True,text=True)
rec=dict(type='build',kind='release',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),returncode=p.returncode,wall_s=time.monotonic()-start)
if p.returncode:rec['errors']=p.stderr[-6000:]
else:rec['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
with(E/'records.jsonl').open('a')as f:f.write(json.dumps(rec)+'\n')
print(json.dumps(rec),flush=True);assert p.returncode==0
for meta in sorted((r for r in ev.rows if r.get('public_number')),key=lambda r:r['public_number']):ev.run(meta,'release','release-open15')
old=[json.loads(s)for s in(R/'tmp/pipes_hot_checks_20261021.jsonl').open()]
public15=next(r for r in ev.rows if r.get('public_number')==15)
ts=Path(public15['test_file']).read_bytes().split();commands=[int(x)for x in ts[2:2+200000]]
for old_record in old:
 if old_record.get('suite')!='transcript_boundary'or old_record.get('method')!='hot-o0'or not old_record.get('id','').startswith(('mismatch','truncated')):continue
 tag,cut=old_record['id'].split('-');cut=int(cut);sequence=commands[:cut]
 if tag=='mismatch':sequence+=[{100000:29,133152:12}.get(cut,commands[cut]+1 if 0<commands[cut]<40 else 1)]
 blob=('1\n'+str(len(sequence))+'\n'+'\n'.join(map(str,sequence))+'\n0\n').encode();assert hashlib.sha256(blob).hexdigest()==old_record['input_sha256']
 with tempfile.TemporaryDirectory(prefix='pipes-cache-boundary-')as temp:
  path=Path(temp)/'test.in';path.write_bytes(blob);meta=ev.h.parse_test(path);meta.update(id=old_record['id'],test_file=str(path),family='transcript_boundary',response_sha256=old_record['response_sha256'],kpi=old_record['kpi'])
  ev.run(meta,'release','release-transcript-boundary')
for meta in [r for r in ev.rows if r['id'].startswith(('a60a69','c51a00'))]:ev.run(meta,'release','release-unknown-200k')
known=[json.loads(s)for s in(E/'records.jsonl').open()]
for meta in [r['meta']for r in known if r.get('type')=='holdout_input']:
 reference=next(r for r in known if r.get('suite')=='final-holdout'and r.get('kind')=='baseline'and r['id']==meta['id'])
 meta.update(response_sha256=reference['response_sha256'],kpi=reference['kpi']);ev.run(meta,'release','release-unknown-200k')
# Exercise EOF, CRLF, explicit plus, buffer-boundary and fragmented reads.
ref=next(r for r in ev.rows if r.get('public_number')==1)
streams=[b' \t\r\n+1\r\n+4\n+15\n-2\n+3\n-1\n+0\n',b' '*4095+b'+1\n4\n15\n-2\n3\n-1\n0\n',b'1\n4\n15\n-2\n3\n-1\n0']
for index,stream in enumerate(streams):
 p=subprocess.run([str(binary)],input=stream,capture_output=True,env={**os.environ,'cjProcessorNum':'1'},timeout=10)
 digest=hashlib.sha256(p.stdout).hexdigest();assert p.returncode==0 and digest==ref['response_sha256'],(index,p.stderr)
 with(E/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='protocol_smoke',kind='release',case=index,returncode=p.returncode,response_sha256=digest,response_equal=True))+'\n')
p=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'cjProcessorNum':'1'})
for byte in streams[0]:p.stdin.write(bytes([byte]));p.stdin.flush();time.sleep(0.002)
p.stdin.close();output=p.stdout.read();error=p.stderr.read();p.wait(timeout=10);assert p.returncode==0 and hashlib.sha256(output).hexdigest()==ref['response_sha256'],error
with(E/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='protocol_smoke',kind='release',case='fragmented-one-byte',returncode=p.returncode,response_sha256=hashlib.sha256(output).hexdigest(),response_equal=True))+'\n')
# Record the default runtime separately; this is still Apple M1, not Windows.
previous=os.environ.pop('cjProcessorNum',None)
try:
 with tempfile.TemporaryDirectory(prefix='pipes-default-runtime-')as temp:
  base=SimpleNamespace(**ev.h.__dict__);base.parse_test=lambda path:dict(public15)
  result=ev.nh.run_case(base,[str(binary)],ev.NATIVE,Path(public15['test_file']),Path(temp)/'run',5,240)
  digest=hashlib.sha256(Path(result['judge_output_file']).read_bytes()).hexdigest();assert result['status']=='ok'and digest==public15['response_sha256']
  rec={key:result[key]for key in ['status','solver_cpu_total_s','solver_peak_rss_mb','kpi']};rec.update(type='evaluation',suite='release-default-runtime',kind='release',id=public15['id'],runtime_processors='default',response_sha256=digest,response_equal=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
  with(E/'records.jsonl').open('a')as f:f.write(json.dumps(rec)+'\n')
  print(json.dumps(rec),flush=True)
finally:
 if previous is not None:os.environ['cjProcessorNum']=previous
print('RELEASE_VERIFIED',hashlib.sha256(source.read_bytes()).hexdigest(),flush=True)
