"""Alternating full interactive CPU trials, fixed input and frozen source hashes."""
from pathlib import Path
import importlib.util,json,statistics,random,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location('verification',HERE/'verify_support.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
OUT=HERE/'timing'
OUT.mkdir(exist_ok=False)
expected=json.loads((ROOT/'speed-v17/verification-summary.json').read_text())['native_result']['answers']
orders=[['17','18','19'],['19','18','17'],['18','17','19'],['19','17','18'],['17','19','18'],['18','19','17']]
pairs=[]
for i,order in enumerate(orders):
    sample={}
    for variant in order:
        v.FAST=ROOT/('speed-v'+variant);v.HERE=OUT
        r=v.run('fast','pair-%d-v%s'%(i,variant),v.REPO/'data/pipes/open')
        assert r['answers']==expected and abs(r['score']-30.75747404826914)<1e-12
        raw=json.loads((OUT/('pair-%d-v%s'%(i,variant))/'fast/harness/summary.json').read_text())
        r['user_cpu_sum_s']=sum(x['solver_cpu_user_s'] for x in raw['records'])
        sample[variant]=r
    pairs.append(sample)
    v.e.save(OUT/'progress.json',{'completed_pairs':len(pairs),'pairs':pairs})
result={'status':'complete','baseline':'speed-v17','pair_count':len(pairs),'scope':'Local macOS clang interactive Open15; not Windows/server CPU','pairs':pairs,'comparisons':{}}
for variant in ['18','19']:
    before=[x['17']['cpu_sum_s'] for x in pairs];after=[x[variant]['cpu_sum_s'] for x in pairs]
    delta=[a-b for a,b in zip(before,after)];rng=random.Random(20261019)
    boot=sorted(statistics.mean(rng.choices(delta,k=len(delta))) for _ in range(10000))
    ub=[x['17']['user_cpu_sum_s'] for x in pairs];ua=[x[variant]['user_cpu_sum_s'] for x in pairs]
    result['comparisons'][variant]={'baseline_total_cpu_s':before,'candidate_total_cpu_s':after,'baseline_median':statistics.median(before),'candidate_median':statistics.median(after),'median_reduction_percent':100*(1-statistics.median(after)/statistics.median(before)),'paired_mean_saved_seconds':statistics.mean(delta),'bootstrap_95_ci_saved_seconds':[boot[250],boot[9749]],'faster_pairs':sum(d>0 for d in delta),'baseline_user_median':statistics.median(ub),'candidate_user_median':statistics.median(ua),'user_median_reduction_percent':100*(1-statistics.median(ua)/statistics.median(ub)),'total_speedup_established':boot[250]>0}
v.e.save(OUT/'result.json',result)
print(json.dumps(result['comparisons'],indent=2),flush=True)
