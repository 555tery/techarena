import csv, json
from collections import deque
from pathlib import Path

root=Path('results/pipes/improvement/case15_opportunity_loss')
rows=list(csv.DictReader((root/'runs/baseline_features.csv').open()))
hist=deque()
freq=[0]*41
features=[]
for r in rows:
    q=int(r['length'])
    h=len(hist)
    fit_count=[0]+[int(r[f'fit_count_{x}']) for x in range(1,41)]
    fit_volume=[0]+[int(r[f'fit_volume_{x}']) for x in range(1,41)]
    total_missing=sum(freq[x] for x in range(1,41) if fit_count[x]==0)
    weighted_capacity=sum(freq[x]*fit_count[x] for x in range(1,41))
    fvol=int(r['free_volume'])
    weighted_usable=sum(freq[x]*fit_volume[x] for x in range(1,41))
    features.append({
      'op':int(r['op']), 'q':q, 'growth':int(r['digs'])>0,
      'active':int(r['active_pipes']), 'free':fvol, 'gaps':int(r['gap_count']),
      'max_gap':int(r['largest_gap']), 'h':h,
      'recent_long_share':sum(freq[8:41])/h if h else 0.0,
      'missing_share':total_missing/h if h else 0.0,
      'coverage':sum(1 for x in range(1,41) if freq[x]>0 and fit_count[x]>0)/max(1,sum(1 for x in range(1,41) if freq[x]>0)),
      'weighted_gap_count':weighted_capacity/h if h else 0.0,
      'weighted_usable_fraction':weighted_usable/(h*fvol) if h and fvol else 0.0,
      'large_fit8':fit_count[8], 'large_fit20':fit_count[20],
      'large_vol8':fit_volume[8], 'large_vol20':fit_volume[20]
    })
    hist.append(q); freq[q]+=1
    if len(hist)>256:
        freq[hist.popleft()]-=1

exp=[i for i,f in enumerate(features) if f['growth']]
for horizon in [1,8,32,128]:
    for f in features:
        f[f'next_growth_{horizon}']=False
    j=0
    for i,f in enumerate(features):
        while j<len(exp) and exp[j]<i: j+=1
        if j<len(exp) and exp[j]<i+horizon:
            f[f'next_growth_{horizon}']=True

def summarize(label, subset, horizon):
    positive=sum(bool(x[f'next_growth_{horizon}']) for x in subset)
    vals=[x[label] for x in subset]
    vals.sort()
    def quant(p):
        return vals[min(len(vals)-1,int(p*(len(vals)-1)))] if vals else None
    return {'n':len(subset),'future_growth_n':positive,'future_growth_rate':positive/len(subset) if subset else None,'median':quant(.5),'p90':quant(.9)}

out={'rows':len(features),'expansions':len(exp),'windows':{}}
eligible=[f for f in features if f['h']>=64 and f['free']>0]
for horizon in [8,32,128]:
    out['windows'][str(horizon)]={
      'all':summarize('missing_share',eligible,horizon),
      'recent_long_ge_half':summarize('missing_share',[x for x in eligible if x['recent_long_share']>=.5],horizon),
      'recent_long_lt_half':summarize('missing_share',[x for x in eligible if x['recent_long_share']<.5],horizon),
      'top_decile_missing':summarize('missing_share', sorted(eligible,key=lambda x:x['missing_share'])[-max(1,len(eligible)//10):],horizon),
      'bottom_decile_missing':summarize('missing_share', sorted(eligible,key=lambda x:x['missing_share'])[:max(1,len(eligible)//10)],horizon),
      'top_decile_usable':summarize('weighted_usable_fraction', sorted(eligible,key=lambda x:x['weighted_usable_fraction'])[-max(1,len(eligible)//10):],horizon),
      'bottom_decile_usable':summarize('weighted_usable_fraction', sorted(eligible,key=lambda x:x['weighted_usable_fraction'])[:max(1,len(eligible)//10)],horizon)
    }
# Request sizes are known on the current operation. Compare direct expansion states with same request size non-expansion states.
by_q={}
for q in range(1,41):
    sub=[f for f in features if f['q']==q]
    if not sub: continue
    ex=[f for f in sub if f['growth']]
    no=[f for f in sub if not f['growth']]
    def med(name, a):
      v=sorted(x[name] for x in a)
      return v[len(v)//2] if v else None
    by_q[str(q)]={'n':len(sub),'expansions':len(ex),'expansion_rate':len(ex)/len(sub),
                  'exp_free_median':med('free',ex),'nonexp_free_median':med('free',no),
                  'exp_maxgap_median':med('max_gap',ex),'nonexp_maxgap_median':med('max_gap',no),
                  'exp_gaps_median':med('gaps',ex),'nonexp_gaps_median':med('gaps',no)}
out['by_request_size']=by_q
(root/'runs/liquidity_diagnostics.json').write_text(json.dumps(out,indent=2)+'\n')
for h, d in out['windows'].items():
    print('horizon',h)
    for key,v in d.items(): print(key,v)
print('by q 8-40:')
for q,v in by_q.items():
    if int(q)>=8 and v['expansions']:
        print(q,v)
