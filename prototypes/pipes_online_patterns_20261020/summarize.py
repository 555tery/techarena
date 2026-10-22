"""Paired stats; no IID interpretation of synthetic tests."""
import argparse, collections, json, random, statistics
from evaluate import HERE

def load(mode, group, name):
    return {p.parent.name:json.loads(p.read_text()) for p in sorted((HERE/'measurements'/mode/group/name).glob('*/record.json'))}

def stats(rows, base):
    assert set(rows) == set(base) and rows
    assert all(r['status']=='ok' for r in list(rows.values())+list(base.values()))
    ds = {k:r['kpi']-base[k]['kpi'] for k,r in rows.items()}
    families = collections.defaultdict(list)
    for k,r in rows.items():
        families[(r['stratum'],r['family'])].append(k)
    macro = {s:statistics.mean(statistics.mean(rows[k]['kpi'] for k in ids) for (t,f),ids in families.items() if t==s) for s in set(r['stratum'] for r in rows.values())}
    bystratum = {}
    for s in macro:
        ids=[k for k in rows if rows[k]['stratum']==s]
        fd=[statistics.mean(ds[k] for k in ids2) for (t,f),ids2 in families.items() if t==s]
        rng=random.Random(2026102047)
        boot=sorted(statistics.mean(rng.choices(fd,k=len(fd))) for _ in range(4000))
        bystratum[s]=dict(n=len(ids),family_macro_delta=statistics.mean(fd),mean_delta=statistics.mean(ds[k] for k in ids),
             family_bootstrap95=[boot[100],boot[3899]],wins=sum(ds[k]>1e-12 for k in ids),ties=sum(abs(ds[k])<=1e-12 for k in ids),losses=sum(ds[k]<-1e-12 for k in ids))
    worst=sorted(ds,key=ds.get)[:8]
    return dict(n=len(rows),macro=macro,by_stratum=bystratum,mean=statistics.mean(r['kpi'] for r in rows.values()),
        mean_delta=statistics.mean(ds.values()),wins=sum(x>1e-12 for x in ds.values()),ties=sum(abs(x)<=1e-12 for x in ds.values()),losses=sum(x<-1e-12 for x in ds.values()),
        min_retention=min(rows[k]['kpi']/base[k]['kpi'] for k in rows),
        worst=[dict(id=k,delta=ds[k],old_T=base[k]['trench_length_m'],new_T=rows[k]['trench_length_m']) for k in worst],
        weighted_score=sum(r['weight']*r['kpi'] for r in rows.values()),
        max_cpu=max(r['solver_cpu_total_s'] for r in rows.values()),max_rss=max(r['solver_peak_rss_mb'] for r in rows.values()),resources_ok=all(r['resources_ok'] for r in rows.values()))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('group');ap.add_argument('--names',required=True);ap.add_argument('--mode',default='screen');ap.add_argument('--base',default='baseline');a=ap.parse_args()
    baseline=load(a.mode,a.group,a.base)
    result={n:stats(load(a.mode,a.group,n),baseline) for n in a.names.split(',')}
    (HERE/f'analysis-{a.mode}-{a.group}-{a.names.replace(",","-")}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
