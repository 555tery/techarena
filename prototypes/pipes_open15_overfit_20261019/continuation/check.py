"""Official native checks for the marked public-overfit solver. No platform access."""
import json,sys,hashlib,random,re
from pathlib import Path
from runtime import ROOT,PARENT,REPO,e
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate_divergence():
 d=ROOT/'divergence';d.mkdir(exist_ok=False);rows=[]
 for case in json.loads((PARENT/'joint.json').read_text())['cases']:
  for kind in ['early','late']:
   commands=case['commands'];cut=min(20,len(commands)-1) if kind=='early' else min(len(commands),199980)
   seq=commands[:cut];live={};pid=0
   for c in seq:
    if c>0:pid+=1;live[pid]=c
    else:live.pop(-c)
   avoid=commands[cut] if cut<len(commands) else 0;c=40 if avoid!=40 else 39;seq.append(c);pid+=1;live[pid]=c
   rng=random.Random(2026101900+case['case'])
   for k in range(min(100,200000-len(seq))):
    if live and k%3==0:
     p=rng.choice(list(live));seq.append(-p);live.pop(p)
    else:c=rng.randint(1,40);seq.append(c);pid+=1;live[pid]=c
   p=d/f"{case['case']:02d}_{kind}.in";p.write_text('1\n'+str(len(seq))+'\n'+'\n'.join(map(str,seq))+'\n0\n');rows.append({'path':str(p),'sha256':sha(p),'prefix':cut,'commands':len(seq),'scope':'correctness under prefix divergence, not hidden score'})
 e.save(ROOT/'divergence.json',rows)
def run(release,phase):
 e.quota();build=json.loads((release/'build.json').read_text());assert sha(release/'solution.cpp')==build['source_sha256'] and sha(release/'solver')==build['binary_sha256']
 checker=REPO/'prototypes/pipes_architecture_v2_20261018/checker/native_runner';info=json.loads(checker.with_name('build.json').read_text());assert sha(checker)==info['binary_sha256'];assert sha(e.NATIVE/'native_runner.cpp')==info['adapter_sha256']
 if phase=='divergence' and not (ROOT/'divergence').exists():generate_divergence()
 tests=REPO/'data/pipes/open' if phase in ['open','repeat'] else ROOT/'divergence';files=sorted(tests.glob('*.in'));inputs={str(p):sha(p) for p in files}
 out=release/phase;out.mkdir(exist_ok=False)
 rc=e.invoke([sys.executable,'-B',str(e.NATIVE/'native_harness.py'),'--workers','2','--solver',str(release/'solver'),'--interactor',str(checker),'--tests',str(tests),'--out',str(out/'harness'),'--name','OPEN15_FULL_OVERFIT','--cpu-limit','5','--memory-limit-mb','256','--response-timeout','5','--wall-timeout','180'],out,'run.log',900)
 s=json.loads((out/'harness/summary.json').read_text());assert rc==0 and s['case_count']==s['ok_count']==len(files),(rc,s['ok_count'])
 assert {str(p):sha(p) for p in files}==inputs
 assert sha(release/'solver')==build['binary_sha256'] and sha(release/'solution.cpp')==build['source_sha256']
 for x in s['records']:
  assert x['solver_cpu_total_s']<5 and x['solver_peak_rss_mb']<256
  assert x['judge_commands_seen_including_final_zero']==x['operation_count']+1
  assert 'table_conflict=0' in x['candidate_stderr']
  if phase=='divergence':assert int(re.search(r'fallback=(\d+)',x['candidate_stderr']).group(1))>0
 if phase in ['open','repeat']:
  expected={str(c['case']):c for c in json.loads((release/'plan-audit.json').read_text())['cases']}
  for x in s['records']:
   assert x['trench_length_m']==expected[x['case']]['T']
   assert x['test_sha256']==expected[x['case']]['input_sha256']
   assert 'fallback=0 ' in x['candidate_stderr']
 if phase=='repeat':
  prior=json.loads((release/'open/harness/summary.json').read_text())
  before={x['case']:sha(Path(x['judge_output_file'])) for x in prior['records']}
  assert before=={x['case']:sha(Path(x['judge_output_file'])) for x in s['records']}
 e.save(out/'verification.json',{'correct':True,'cases':len(files),'score':s['weighted_score_sum'],'max_cpu':max(x['solver_cpu_total_s'] for x in s['records']),'max_rss':max(x['solver_peak_rss_mb'] for x in s['records']),'inputs':inputs,**build})
 print(json.dumps({'phase':phase,'cases':len(files),'score':s['weighted_score_sum'],'max_cpu':max(x['solver_cpu_total_s'] for x in s['records']),'max_rss':max(x['solver_peak_rss_mb'] for x in s['records'])}),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),sys.argv[2])
