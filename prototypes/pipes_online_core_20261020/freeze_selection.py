"""Freeze calibration selection before any final outcomes are observed."""
import datetime, json
from evaluate import HERE, sha
from summarize import load, stats

names=['baseline','old_hybrid','handoff_exact','primal_observed','primal_recent','hybrid_observed','hybrid_recent']
base=load('screen','calibration','baseline')
ss={n:stats(load('screen','calibration',n),base) for n in names}
public={n:sum(r['weight']*r['kpi'] for r in load('screen','open15',n).values()) for n in names}
reasons={}
for n in names:
    s=ss[n];why=[]
    if not s['resources_ok']:why.append('local bulk resources')
    if s['by_stratum']['ordinary']['family_macro_delta'] < .001:why.append('ordinary improvement <0.001')
    if s['by_stratum']['prefix']['family_macro_delta'] < -.002:why.append('prefix regression >0.002')
    if s['min_retention'] < .85:why.append('case retention <0.85')
    reasons[n]=why
eligible=[n for n in names if not reasons[n]]
scenarios={n:{str(p):public[n]+84*((1-p)*ss[n]['macro']['ordinary']+p*ss[n]['macro']['prefix']) for p in [0,1]} for n in names}
regret={n:max(max(scenarios[k][str(p)] for k in names)-scenarios[n][str(p)] for p in [0,1]) for n in names}
order=['primal_observed','primal_recent','hybrid_observed','hybrid_recent']
selected=next((n for n in order if n in eligible and regret[n] <= min(regret[k] for k in eligible)+.05),'baseline') if eligible else 'baseline'
core='primal_recent' if selected in ['primal_recent','hybrid_recent'] else 'primal_observed'
hybrid='hybrid_recent' if core=='primal_recent' else 'hybrid_observed'
final_names=['baseline','old_hybrid','handoff_exact',core,hybrid]
out=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected=selected,core=core,hybrid=hybrid,final_names=final_names,
    sources={n:sha(HERE/'candidates'/n/'solution.cpp') for n in final_names},
    binaries={n:sha(HERE/'candidates'/n/'solver') for n in final_names},
    experiment_sha256=sha(HERE/'experiment.json'),manifests={g:sha(HERE/'evaluation'/g/'manifest.json') for g in ['calibration','final','stress']},
    calibration_statistics=ss,open15_scores=public,ineligibility_reasons=reasons,scenarios=scenarios,max_regret=regret,
    criterion='Ordinary gain>=0.001, prefix>=-0.002, all retention>=0.85; minimax regret of Open15+84*macro across prefix share0/1, tie0.05 favors pure online.',
    final_rule='No retuning. Confirm ordinary macro>0, prefix delta>=-0.002, retention>=0.85, positive equal-stratum mean and both total-score endpoint deltas vs baseline>0; valid/limits in official protocol. Otherwise no promotion.',
    caveat='Scenario totals are sensitivity calculations, not estimates of official hidden score.')
path=HERE/'selection-freeze.json';assert not path.exists()
path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(selected=selected,regret=regret,eligible=eligible,final_names=final_names),indent=2))
