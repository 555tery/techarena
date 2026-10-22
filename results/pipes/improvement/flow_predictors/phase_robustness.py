#!/usr/bin/env python3
"""Held-out temporal/phase checks for validation-selected k=11 on open case 8."""
import json, math, random, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
c=analyze.load(ROOT/'data/pipes/open/8.in')
ops=c['ops']; n=c['n']; train_end=int(.40*n); val_end=int(.60*n); k=11
rates,_=analyze.modulo_fit(ops,k,val_end)
counts=[0]*k; active=0; next_pid=1; events=[]
for t,x in enumerate(ops):
    if x>0:
        counts[next_pid%k]+=1; active+=1; next_pid+=1
    elif x<0:
        residue=(-x)%k
        if t>=val_end and active:
            den=sum(counts[j]*rates[j] for j in range(k))
            pred=[counts[j]*rates[j]/den for j in range(k)]
            base=[counts[j]/active for j in range(k)]
            b1=sum((pred[j]-(j==residue))**2 for j in range(k))
            b0=sum((base[j]-(j==residue))**2 for j in range(k))
            p_pid=rates[residue]/den; p0_pid=1/active
            events.append({'t':t,'pid':-x,'length':c['length'][-x],
                           'delta_ll':math.log(p_pid/p0_pid),
                           'brier_improvement':b0-b1,
                           'pred_class':max(range(k),key=lambda j:pred[j]),
                           'predicted_probability':max(pred),
                           'actual_class_probability':pred[residue],
                           'correct':int(max(range(k),key=lambda j:pred[j])==residue),
                           'base_correct':int(max(range(k),key=lambda j:base[j])==residue),
                           'active':active})
        counts[residue]-=1; active-=1

def mean(xs): return statistics.mean(xs) if xs else None

def summarise(rows):
    if not rows:return {'n':0}
    return {'n':len(rows),
       'delta_logloss_per_event_vs_uniform_active_pid':mean([r['delta_ll'] for r in rows]),
       'brier_improvement_vs_uniform_residue_distribution':mean([r['brier_improvement'] for r in rows]),
       'class_accuracy':mean([r['correct'] for r in rows]),
       'uniform_riskset_class_accuracy':mean([r['base_correct'] for r in rows]),
       'accuracy_gain_vs_uniform_riskset':mean([r['correct']-r['base_correct'] for r in rows]),
       'mean_predicted_top_class_probability':mean([r['predicted_probability'] for r in rows]),
       'mean_actual_class_probability':mean([r['actual_class_probability'] for r in rows]),
       'mean_active_pid_count':mean([r['active'] for r in rows])}

quartiles=[]
for q in range(4):
    lo=val_end+(n-val_end)*q//4; hi=val_end+(n-val_end)*(q+1)//4
    rows=[r for r in events if lo<=r['t']<hi]
    quartiles.append({'ops':[lo,hi],'metrics':summarise(rows)})
lengths={}
for length in sorted(set(c['length'][1:])):
    rows=[r for r in events if r['length']==length]
    if len(rows)>=10:lengths[str(length)]=summarise(rows)
# Non-overlapping 128-operation blocks are the resampling units. This addresses
# temporal dependence better than iid event resampling, but not dataset selection.
block_width=128; test_blocks=[]
for lo in range(val_end,n,block_width):
    hi=min(n,lo+block_width)
    rows=[r for r in events if lo<=r['t']<hi]
    if rows:test_blocks.append(rows)
# Bootstrap blocks, retaining the original number of events in each replicate.
rng=random.Random(20261016); reps=10000; boot_ll=[]; boot_brier=[]
for _ in range(reps):
    sample=[]
    while len(sample)<len(events):
        sample.extend(rng.choice(test_blocks))
    sample=sample[:len(events)]
    boot_ll.append(mean([r['delta_ll'] for r in sample]))
    boot_brier.append(mean([r['brier_improvement'] for r in sample]))
boot_ll.sort();boot_brier.sort()
def ci(a):return [a[int(.025*(len(a)-1))],a[int(.975*(len(a)-1))]]
# Split-specific deletion-parity prevalence. Not used to fit or score the k=11 model.
parity=[]
for name,lo,hi in [('train',0,train_end),('validation',train_end,val_end),('test',val_end,n)]:
    rows=[ops[t] for t in range(lo,hi) if ops[t]<0]
    parity.append({'split':name,'deletions':len(rows),'odd_pid_share':sum((-x)%2 for x in rows)/len(rows) if rows else None})
result={'case':8,'input_sha256':__import__('hashlib').sha256((ROOT/'data/pipes/open/8.in').read_bytes()).hexdigest(),
 'protocol':{'fit_and_choose_k':'first 40% operations fit; next 20% selects k among 2..16; k=11 selected; rates refit through 60%; final 40% is held-out test',
             'phase_slices':'four equal operation-time quarters of the held-out final 40%; fixed k=11 and fixed rates, no test retuning',
             'uncertainty':'10,000 bootstrap replicates resampling nonempty nonoverlapping 128-operation blocks with fixed seed 20261016; percentile 95% CI'},
 'test':summarise(events),'test_logloss_improvement_block_ci95':ci(boot_ll),
 'test_brier_improvement_block_ci95':ci(boot_brier),'nonempty_128op_blocks':len(test_blocks),
 'test_quartiles':quartiles,'test_by_target_pipe_length_min10':lengths,
 'pid_parity_by_split':parity,'fitted_rate_ratios_by_pid_mod_11':rates,
 'note':'Exploratory selected case/k on 15 public cases; block CI is conditional on that selection and one input, not a hidden-test generalization interval.'}
(OUT/'case8_k11_phase_robustness.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
