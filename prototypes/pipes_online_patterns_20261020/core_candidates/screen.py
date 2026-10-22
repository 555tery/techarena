import importlib.util,json,time,statistics,collections
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[2]
old=R/'prototypes/pipes_online_core_20261020'
spec=importlib.util.spec_from_file_location('old_core_eval',old/'evaluate.py');ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)
names=['baseline','dp_stability_gate','dp_recency_mix']
binaries={n:((old/'candidates/primal_recent/solver') if n=='baseline' else H/n/'solver') for n in names}
assert ev.sha(old/'candidates/primal_recent/solution.cpp')==ev.sha(old/'release/solution.cpp')
rows=[];start=time.time()
for group in ['calibration','final','open15']:
 for i,c in enumerate(ev.cases(group)):
  if 'sha256' in c: assert ev.sha(c['path'])==c['sha256']
  for n in names:
   dest=H/'measurements'/group/n/(c['id']+'.json');dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():
    row=json.loads(dest.read_text());assert row['binary_sha256']==ev.sha(binaries[n])
   else:
    try:
     row=ev.screen(binaries[n],c['path']);row.pop('candidate_stderr',None)
    except Exception as e: row={'status':'error','detail':repr(e)}
    row.update(group=group,name=n,id=c['id'],family=c['family'],stratum=c['stratum'],test_sha256=ev.sha(c['path']),binary_sha256=ev.sha(binaries[n]))
    dest.write_text(json.dumps(row,indent=2)+'\n')
   rows.append(row)
  if i%32==0: print(group,i,round(time.time()-start),flush=True)
(H/'records.json').write_text(json.dumps(rows,indent=2)+'\n')
base={(r['group'],r['id']):r for r in rows if r['name']=='baseline'}
summary={}
for n in names:
 ns={}
 for g in ['calibration','final','dev192','open15']:
  rs=[r for r in rows if r['name']==n and (r['group']==g or(g=='dev192' and r['group']!='open15'))]
  pairs=[(r['kpi']-base[(r['group'],r['id'])]['kpi'],r) for r in rs]
  family=collections.defaultdict(list)
  for d,r in pairs: family[(r['stratum'],r['family'])].append(d)
  strata={s:statistics.mean(statistics.mean(v) for (ss,f),v in family.items() if ss==s) for s in {r['stratum'] for r in rs}}
  worst=min(pairs,key=lambda p:p[0]);best=max(pairs,key=lambda p:p[0])
  ns[g]={'n':len(rs),'mean_delta':statistics.mean(p[0] for p in pairs),'family_macro_delta':statistics.mean(statistics.mean(v) for v in family.values()),'stratum_macro_delta':strata,'wins':sum(d>1e-12 for d,r in pairs),'ties':sum(abs(d)<=1e-12 for d,r in pairs),'losses':sum(d< -1e-12 for d,r in pairs),'worst':{'id':worst[1]['id'],'group':worst[1]['group'],'delta':worst[0]},'best':{'id':best[1]['id'],'delta':best[0]},'weighted_score':sum(r['weight']*r['kpi'] for r in rs),'max_cpu':max(r['solver_cpu_total_s'] for r in rs),'max_rss':max(r['solver_peak_rss_mb'] for r in rs)}
 summary[n]=ns
summary['errors']=[r for r in rows if r['status']!='ok']
(H/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
