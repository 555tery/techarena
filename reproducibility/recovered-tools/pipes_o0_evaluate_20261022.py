from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,os,sys,tempfile,time
ROOT=Path('/Users/555tery/techarena'); EXP=ROOT/'prototypes/pipes_cj_online_o0_20261022'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'shinka-pipes/evaluator-native'))
import native_harness as nh
spec=importlib.util.spec_from_file_location('pipes_h',ROOT/'tools/pipes_harness.py'); h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
NATIVE=ROOT/'prototypes/pipes_all2537_comparison_20261020/native-build/native_runner'
rows=[json.loads(s) for file in [ROOT/'prototypes/pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl',ROOT/'prototypes/pipes_cj_tle15_20261021/fresh-checks/final-o0/records.jsonl'] for s in file.open()]
def solver(kind):
 if kind=='baseline':
  return ROOT/'prototypes/pipes_cj_tle15_20261021/candidate-final/solution.cj',ROOT/'prototypes/pipes_cj_tle15_20261021/bin/final-o0'
 return EXP/kind/'solution.cj', EXP/'bin'/f'{kind}-o0'
def run(meta,kind,suite):
 source,binary=solver(kind); path=Path(meta['test_file'])
 digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==meta['test_sha256'],path
 base=SimpleNamespace(**h.__dict__);base.parse_test=lambda p:dict(meta)
 os.environ['cjProcessorNum']='1'
 with tempfile.TemporaryDirectory(prefix='pipes-o0-') as temp:
  result=nh.run_case(base,[str(binary)],NATIVE,path,Path(temp)/'run',5,240)
  output=Path(result['judge_output_file'])
  response=hashlib.sha256(output.read_bytes()).hexdigest() if output.exists() else None
  rec={key:result.get(key) for key in ['status','detail','solver_cpu_user_s','solver_cpu_system_s','solver_cpu_total_s','solver_peak_rss_mb','kpi','trench_length_m','candidate_stderr']}
  rec.update(kpi_delta=(rec['kpi']-meta['kpi'] if rec.get('kpi') is not None and meta.get('kpi') is not None else None))
  rec.update(type='evaluation',suite=suite,kind=kind,id=meta['id'],family=meta.get('family'),operation_count=meta['operation_count'],test_sha256=digest,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),response_sha256=response,response_equal=(response==meta['response_sha256'] if meta.get('response_sha256') else None),within_limits=not nh.failed(result,5,256))
  with (EXP/'records.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
  print(json.dumps({k:rec[k] for k in ['suite','kind','id','status','solver_cpu_total_s','solver_peak_rss_mb','response_equal','within_limits']}),flush=True)
  if rec['status']!='ok' or rec['response_equal'] is False and not (kind.startswith('paced') or kind=='full-replay'):raise RuntimeError(rec)
 return rec
if __name__=='__main__':
 mode=sys.argv[1]; kinds=sys.argv[2:] or ['baseline','indices','dp']
 if mode=='panel':
  prefixes=['a60a69','c51a00','94a6ee']
  panel=[r for r in rows if r.get('public_number') in [9,14,15] or any(r['id'].startswith(p) for p in prefixes) or r['id'] in ['fresh-01','fresh-02','fresh-05','fresh-07','fresh-21'] or r['id']=='101237d28dabb7c44acac9ea76421af475341af35e0084118b2ab2948828042d']
 elif mode=='200k': panel=[r for r in rows if r['operation_count']==200000]
 elif mode=='all': panel=rows
 else:raise ValueError(mode)
 for i,r in enumerate(panel):
  order=kinds if i%2==0 else list(reversed(kinds))
  for kind in order:run(r,kind,mode)
