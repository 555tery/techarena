from pathlib import Path
import json,statistics,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'speed-review-20261019'))
import verify_speed as v
v.BASE=ROOT/'speed-v8';v.FAST=HERE;v.HERE=HERE/'fallback-timing'
tests=ROOT/'speed-custom-review-20261019/fallback-inputs'
rows=[]
for i in range(3):
 row={}
 for label in (['baseline','fast'] if i%2==0 else ['fast','baseline']):
  row[label]=v.run(label,f'pair-{i}',tests)
  raw=json.loads((v.HERE/f'pair-{i}'/label/'harness/summary.json').read_text())
  row[label]['user_cpu_s']=sum(x['solver_cpu_user_s'] for x in raw['records'])
  row[label]['system_cpu_s']=sum(x['solver_cpu_system_s'] for x in raw['records'])
  assert all('replay=0' in x['candidate_stderr'] for x in raw['records'])
 assert row['baseline']['answers']==row['fast']['answers']
 rows.append(row)
b=[r['baseline']['cpu_sum_s'] for r in rows];f=[r['fast']['cpu_sum_s'] for r in rows]
r={'status':'verified','scope':'Exact BF runtime parity on six new 200k operation streams, not allocator quality or generalization evidence','pairs':3,'workers':2,'candidate_source_sha256':v.sha(HERE/'solution.cpp'),'baseline_source_sha256':v.sha(v.BASE/'solution.cpp'),'candidate_checks':18,'baseline_checks':18,'exact_answer_parity':True,'baseline_cpu':b,'candidate_cpu':f,'baseline_median':statistics.median(b),'candidate_median':statistics.median(f),'median_cpu_reduction_percent':100*(1-statistics.median(f)/statistics.median(b)),'faster_pairs':sum(x>y for x,y in zip(b,f)),'max_candidate_cpu_s':max(x['fast']['max_cpu_s'] for x in rows),'max_candidate_rss_mib':max(x['fast']['max_rss_mib'] for x in rows),'per_family':{c:{'baseline_median':statistics.median(x['baseline']['per_case_cpu'][c] for x in rows),'candidate_median':statistics.median(x['fast']['per_case_cpu'][c] for x in rows)}for c in rows[0]['fast']['per_case_cpu']},'rows':rows,'limitations':'Local macOS native interactive CPU only; Windows and platform time unmeasured.'}
v.e.save(v.HERE/'result.json',r)
print(json.dumps({k:x for k,x in r.items() if k!='rows'},indent=2),flush=True)
