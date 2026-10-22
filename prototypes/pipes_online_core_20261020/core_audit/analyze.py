import json,statistics,collections
from pathlib import Path
here=Path(__file__).resolve().parent
rows=json.loads((here/'records.json').read_text())
base={(r['group'],r['id']):r for r in rows if r['name']=='baseline'}
summary={}
for name in ['parity_decay64','primal_window256']:
    sub=[r for r in rows if r['name']==name]
    stats={}
    for group in ['calibration','final','open15','dev192']:
        rs=[r for r in sub if r['group']==group or (group=='dev192' and r['group']!='open15')]
        ds=[r['kpi']-base[(r['group'],r['id'])]['kpi'] for r in rs]
        families=collections.defaultdict(list)
        strata=collections.defaultdict(list)
        for r,d in zip(rs,ds):
            families[(r['stratum'],r['family'])].append(d)
            strata[r['stratum']].append(d)
        worst=min(zip(ds,rs),key=lambda t:t[0])
        stats[group]={'n':len(rs),'mean_delta':statistics.mean(ds),'family_macro_delta':statistics.mean(statistics.mean(v) for v in families.values()),'stratum_mean_delta':{k:statistics.mean(v) for k,v in strata.items()},'wins':sum(d>1e-12 for d in ds),'ties':sum(abs(d)<=1e-12 for d in ds),'losses':sum(d< -1e-12 for d in ds),'worst':{'id':worst[1]['id'],'group':worst[1]['group'],'delta':worst[0]},'baseline_kpi_sum':sum(base[(r['group'],r['id'])]['kpi'] for r in rs),'candidate_kpi_sum':sum(r['kpi'] for r in rs),'max_cpu':max(r['solver_cpu_total_s'] for r in rs),'max_rss':max(r['solver_peak_rss_mb'] for r in rs)}
    summary[name]=stats
summary['errors']=[r for r in rows if r['status']!='ok']
(here/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
