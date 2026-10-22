"""Apply the frozen calibration rule before observing final outcomes."""
import datetime,json,statistics
from evaluate import HERE,source,sha
from summarize import load,stats

assert not list((HERE/'measurements/screen/final').glob('*/*/record.json'))
assert not (HERE/'selection-freeze.json').exists()
prior=json.loads((HERE/'calibration-freeze.json').read_text())
base=load('screen','calibration','baseline')
strata=['stable_patterns','changing_patterns','neutral','public_prefix']
public={n:sum(r['weight']*r['kpi'] for r in load('screen','open15',n).values()) for n in prior['names']}
results={}
for n in ['baseline']+prior['shortlist']:
    rows=load('screen','calibration',n);s=stats(rows,base)
    checks=dict(valid=len(rows)==96 and all(r['status']=='ok' for r in rows.values()),
        resources=s['resources_ok'],stratum_floor=min(s['macro'][t]-stats(base,base)['macro'][t] for t in strata)>=-.002,
        individual_retention=s['min_retention']>=.95,
        equal_stratum_gain=statistics.mean(s['by_stratum'][t]['family_macro_delta'] for t in strata)>0)
    results[n]=dict(statistics=s,checks=checks,eligible=n=='baseline' or all(checks.values()),
        endpoints={t:public[n]+84*s['macro'][t] for t in strata})
eligible=[n for n,v in results.items() if v['eligible']]
best_endpoint={t:max(results[n]['endpoints'][t] for n in eligible) for t in strata}
regret={n:max(best_endpoint[t]-results[n]['endpoints'][t] for t in strata) for n in eligible}
minimum=min(regret.values())
tied=[n for n in eligible if regret[n]<=minimum+.02]
selected='baseline' if 'baseline' in tied else min(tied,key=lambda n:(len(source(n).read_text()),regret[n],n))
names=['baseline','legacy']+([] if selected=='baseline' else [selected])
for n in prior['names']:
    assert sha(source(n))==prior['source_hashes'][n]
    assert sha(source(n).with_name('solver'))==prior['binary_hashes'][n]
for g in ['calibration','final','stress']:
    assert sha(HERE/'evaluation'/g/'manifest.json')==prior['manifests'][g]
out=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected=selected,
    sources={n:sha(source(n)) for n in names},binaries={n:sha(source(n).with_name('solver')) for n in names},
    manifests=prior['manifests'],public_scores=public,calibration=results,minimax_regret=regret,tie_margin=.02,
    calibration_freeze_sha256=sha(HERE/'calibration-freeze.json'),final_unobserved=True,
    official_resource_confirmation_pending=True,no_final_retuning=True)
(HERE/'selection-freeze.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(selected=selected,eligible=eligible,minimax_regret=regret,checks={n:v['checks'] for n,v in results.items()}),indent=2))
