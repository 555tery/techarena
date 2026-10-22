from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,threading,time
sys.path.insert(0,'/tmp');import pipes_o0_evaluate_20261022 as ev
E=ev.EXP
sources={}
for kind in sys.argv[1:] or ['exact','paced-balanced']:
 s,b=ev.solver(kind);assert b.exists()
 sources[kind]=(s,b,hashlib.sha256(s.read_bytes()).hexdigest(),hashlib.sha256(b.read_bytes()).hexdigest())
known=[json.loads(s) for s in(E/'records.jsonl').open()]
done={(r.get('source_sha256'),r.get('id')) for r in known if r.get('type')=='evaluation' and r.get('suite')=='full-batch' and r.get('status')=='ok'}
checker=E/'bin/official-offline';assert checker.exists()
checkerhash=hashlib.sha256(checker.read_bytes()).hexdigest()
with(E/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='batch_protocol',mode='command_stream_batch',checker_binary_sha256=checkerhash,checker_source='prototypes/pipes_all2537_comparison_20261020/native-build/official_checker.cpp',resource_scope='whole solver process CPU and RSS, no interactive pipe overhead; interactive resources measured separately',cases=len(ev.rows),kinds=list(sources)))+'\n')
start=time.monotonic();completed=0
for index,meta in enumerate(ev.rows):
 path=Path(meta['test_file']);data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==meta['test_sha256']
 tokens=data.split();n=int(tokens[1]);assert n==meta['operation_count']
 assert len(tokens)==n+2 or len(tokens)==n+3 and tokens[-1]==b'0'
 stream=b'\n'.join(tokens[2:2+n])+b'\n0\n'
 order=list(sources) if index%2==0 else list(reversed(sources))
 for kind in order:
  source,binary,sha,bsha=sources[kind]
  if(sha,meta['id'])in done:continue
  with tempfile.TemporaryDirectory(prefix='pipes-o0-batch-')as temp:
   d=Path(temp);inp=d/'commands';out=d/'response';err=d/'stderr';inp.write_bytes(stream)
   with inp.open('rb')as fi,out.open('wb')as fo,err.open('wb')as fe:
    p=subprocess.Popen([str(binary)],stdin=fi,stdout=fo,stderr=fe,env={**os.environ,'cjProcessorNum':'1'})
    timer=threading.Timer(240,p.kill);timer.daemon=True;timer.start()
    try:
     _,status,usage=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status)
    finally:timer.cancel()
   response=hashlib.sha256(out.read_bytes()).hexdigest();equal=response==meta['response_sha256']
   status='ok'if p.returncode==0 else 'solver_error';validity='inherited_from_exact_response_parity';kpi=meta['kpi'];trench=meta['trench_length_m'];detail=''
   if not equal or index==0:
    (d/'unused-answer').write_text('')
    with out.open('rb')as fo:
     verify=subprocess.run([str(checker),str(path),str(d/'checked-copy'),str(d/'unused-answer'),str(d/'checker-report')],stdin=fo,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=d)
    text=verify.stderr.decode(errors='replace');match=ev.h.SCORE_RE.search(text)
    if verify.returncode!=0 or not match:status='invalid';detail=text[-1200:];kpi=None;trench=None
    else:
     occupied=int(match[1]);trench=int(match[2]);kpi=occupied/trench;assert occupied==meta['final_occupied_length_m']
    validity='official_checker_on_complete_response'
   rec=dict(type='evaluation',suite='full-batch',mode='command_stream_batch',kind=kind,id=meta['id'],family=meta.get('family'),cohort=meta.get('cohort'),operation_count=n,test_sha256=meta['test_sha256'],test_file=str(path),source_sha256=sha,binary_sha256=bsha,solver_cpu_user_s=usage.ru_utime,solver_cpu_system_s=usage.ru_stime,solver_cpu_total_s=usage.ru_utime+usage.ru_stime,solver_peak_rss_mb=usage.ru_maxrss/1048576,status=status,detail=detail,response_sha256=response,response_equal=equal,kpi=kpi,trench_length_m=trench,kpi_delta=(kpi-meta['kpi']if kpi is not None else None),weight=meta['weight'],validation=validity)
   with(E/'records.jsonl').open('a')as f:f.write(json.dumps(rec)+'\n')
   completed+=1
   if status!='ok'or kind=='exact'and not equal:
    print('FAIL',json.dumps(rec),flush=True);raise RuntimeError(rec)
 if(index+1)%64==0 or index+1==len(ev.rows):
  print(json.dumps(dict(progress=index+1,total=len(ev.rows),new_records=completed,elapsed_s=round(time.monotonic()-start,1))),flush=True)
for kind,(source,binary,sha,bsha)in sources.items():assert hashlib.sha256(source.read_bytes()).hexdigest()==sha and hashlib.sha256(binary.read_bytes()).hexdigest()==bsha
print('COMPLETE',flush=True)
