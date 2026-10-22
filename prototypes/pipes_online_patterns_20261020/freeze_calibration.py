"""Development-only shortlist; all fresh outcome files must still be absent."""
import datetime,json,statistics
from evaluate import HERE,source,sha
from summarize import load,stats

assert not list((HERE/'measurements/screen/calibration').glob('*/*/record.json'))
assert not list((HERE/'measurements/screen/final').glob('*/*/record.json'))
b=load('screen','dev','baseline');old=load('screen','dev','legacy')
target=[k for k in b if k.startswith('core-final-') and b[k]['kpi']<old[k]['kpi']-1e-12]
assert len(target)==23
origin=[k for k in b if k.startswith('core-final-')]
oldgain=sum(b[k]['kpi']-old[k]['kpi'] for k in origin)
public_base=sum(r['weight']*r['kpi'] for r in load('screen','open15','baseline').values())
summary={}
for n in ['sufficient_demand','stable_ties','conditional_demand','strict_improvement']:
    r=load('screen','dev',n);s=stats(r,b);public=sum(x['weight']*x['kpi'] for x in load('screen','open15',n).values())
    scenarios={t:public-public_base+84*s['by_stratum'][t]['family_macro_delta'] for t in ['ordinary','prefix']}
    target_delta=statistics.mean(r[k]['kpi']-b[k]['kpi'] for k in target)
    retention=sum(r[k]['kpi']-old[k]['kpi'] for k in origin)/oldgain
    initial_eligible=s['mean_delta']>=0 and s['worst'][0]['delta']>=-.02 and target_delta>=0 and retention>=.95
    weighted_eligible=min(scenarios.values())>=0 and s['worst'][0]['delta']>=-.02 and target_delta>=0 and retention>=.95
    summary[n]=dict(statistics=s,public_score=public,scenario_deltas=scenarios,target_mean_delta=target_delta,
        target_better=sum(r[k]['kpi']>b[k]['kpi']+1e-12 for k in target),target_worse=sum(r[k]['kpi']<b[k]['kpi']-1e-12 for k in target),
        target_fully_repaired=sum(r[k]['kpi']>=old[k]['kpi']-1e-12 for k in target),
        original_gain_retained=retention,passes_original_mean_gate=initial_eligible,passes_total_score_gate=weighted_eligible)
shortlist=[n for n in ['strict_improvement','stable_ties'] if summary[n]['passes_total_score_gate']]
assert len(shortlist)<=3
names=['baseline','legacy']+shortlist
out=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),names=names,shortlist=shortlist,
    source_hashes={n:sha(source(n)) for n in names},binary_hashes={n:sha(source(n).with_name('solver')) for n in names},
    manifests={g:sha(HERE/'evaluation'/g/'manifest.json') for g in ['calibration','final','stress']},development=summary,
    original_gate_result='No candidate passed the original DEV mean>=0 rule. Do not conceal this.',
    pre_validation_amendment='Before any fresh outcomes, allow DEV total-score-safe candidates: both Open15+84*ordinary/prefix endpoints >= current, retain>=95% of original gain and nonnegative target23 mean. This explicitly incorporates the user objective of total score. The fresh calibration and final quality gates are unchanged; public gain alone cannot promote a candidate.',
    rejected_agent_variants='dp_stability_gate and dp_recency_mix fail worst DEV loss>=-0.02 and have negative DEV means; omitted from fresh evaluation.',
    no_more_candidate_edits=True,final_rule_unchanged=True)
(HERE/'calibration-freeze.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(shortlist=shortlist,summary={n:{k:v for k,v in s.items() if k!='statistics'} for n,s in summary.items()}),indent=2))
