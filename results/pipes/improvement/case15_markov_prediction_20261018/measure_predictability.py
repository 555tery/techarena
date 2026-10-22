from __future__ import annotations
import argparse, csv, json, math
from collections import Counter, deque
from pathlib import Path

W=2048
ALPHA=8.0
K=40

def summarize(rows):
    n=len(rows)
    if not n: return {'n':0}
    dlog=[r['marginal_logloss']-r['markov_logloss'] for r in rows]
    dtop=[r['markov_correct']-r['marginal_correct'] for r in rows]
    dbrier=[r['marginal_brier']-r['markov_brier'] for r in rows]
    def ci(xs):
        mean=sum(xs)/len(xs)
        if len(xs)<2:return [mean,mean]
        variance=sum((x-mean)**2 for x in xs)/(len(xs)-1)
        se=math.sqrt(variance/len(xs))
        return [mean-1.96*se,mean+1.96*se]
    def ece(which):
        buckets=[[] for _ in range(10)]
        for r in rows:
            prob=r[which+'_confidence']; correct=r[which+'_correct']
            buckets[min(9,int(prob*10))].append((prob,correct))
        return sum(len(b)/n*abs(sum(x for x,_ in b)/len(b)-sum(y for _,y in b)/len(b)) for b in buckets if b)
    return {
      'n':n,
      'markov_top1_accuracy':sum(r['markov_correct'] for r in rows)/n,
      'marginal_top1_accuracy':sum(r['marginal_correct'] for r in rows)/n,
      'top1_delta_markov_minus_marginal':sum(dtop)/n,
      'top1_delta_normal95_ci':ci(dtop),
      'markov_logloss':sum(r['markov_logloss'] for r in rows)/n,
      'marginal_logloss':sum(r['marginal_logloss'] for r in rows)/n,
      'logloss_gain_marginal_minus_markov':sum(dlog)/n,
      'logloss_gain_normal95_ci':ci(dlog),
      'markov_brier':sum(r['markov_brier'] for r in rows)/n,
      'marginal_brier':sum(r['marginal_brier'] for r in rows)/n,
      'brier_gain_marginal_minus_markov':sum(dbrier)/n,
      'brier_gain_normal95_ci':ci(dbrier),
      'markov_top1_ece':ece('markov'),
      'marginal_top1_ece':ece('marginal'),
      'row_support':{
        'median':sorted(r['row_support'] for r in rows)[n//2],
        'ge_4_fraction':sum(r['row_support']>=4 for r in rows)/n,
        'ge_8_fraction':sum(r['row_support']>=8 for r in rows)/n,
      },
    }

def analyze(input_path:Path, output_path:Path):
    tokens=input_path.read_text().split()
    if len(tokens)<2: raise ValueError(f'bad input: {input_path}')
    n=int(tokens[1]); commands=list(map(int,tokens[2:]))
    if len(commands)==n+1 and commands[-1]==0: commands.pop()
    if len(commands)!=n: raise ValueError(f'command count mismatch in {input_path}: {len(commands)} != {n}')
    responses=output_path.read_text().splitlines()
    if len(responses)!=n: raise ValueError(f'answer line count mismatch: {len(responses)} != {n}')
    expansion=[]
    for cmd,line in zip(commands,responses):
        fields=line.split()
        if cmd>0:
            if len(fields)!=2: raise ValueError(f'bad placement response {line!r}')
            expansion.append(int(fields[0])>0)
        else:
            if len(fields)!=1: raise ValueError(f'bad removal response {line!r}')
            expansion.append(False)
    freq=Counter(); size_window=deque(); trans=Counter(); trans_window=deque(); last=None
    pending=None; evaluated=[]; expansion_count=0; placement_count=0
    for cmd,is_expand in zip(commands,expansion):
        if cmd<0: continue
        x=cmd; placement_count+=1
        if pending is not None:
            actual=x
            row=pending
            p=row['markov_probs']; q=row['marginal_probs']
            row['actual']=actual
            row['markov_correct']=int(max(range(K),key=lambda z:(p[z],-z))+1==actual)
            row['marginal_correct']=int(max(range(K),key=lambda z:(q[z],-z))+1==actual)
            row['markov_confidence']=max(p); row['marginal_confidence']=max(q)
            row['markov_logloss']=-math.log(max(p[actual-1],1e-15))
            row['marginal_logloss']=-math.log(max(q[actual-1],1e-15))
            row['markov_brier']=sum((p[j]-(1.0 if j==actual-1 else 0.0))**2 for j in range(K))
            row['marginal_brier']=sum((q[j]-(1.0 if j==actual-1 else 0.0))**2 for j in range(K))
            evaluated.append(row)
        if last is not None:
            trans_window.append((last,x)); trans[last,x]+=1
            if len(trans_window)>W:
                a,b=trans_window.popleft(); trans[a,b]-=1
        size_window.append(x); freq[x]+=1
        if len(size_window)>W: freq[size_window.popleft()]-=1
        total=len(size_window); den=total+K
        marginal=[(freq[j]+1)/den for j in range(1,K+1)]
        row_counts=[trans[x,j] for j in range(1,K+1)]
        row_support=sum(row_counts)
        norm=row_support+ALPHA
        markov=[(row_counts[j-1]+ALPHA*marginal[j-1])/norm for j in range(1,K+1)]
        if is_expand: expansion_count+=1
        pending={
          'placement_index':placement_count,'current_length':x,'is_expansion':is_expand,
          'row_support':row_support,'markov_probs':markov,'marginal_probs':marginal,
        }
        last=x
    all_stats=summarize(evaluated)
    expansion_stats=summarize([r for r in evaluated if r['is_expansion']])
    result={
      'input':str(input_path),'answer':str(output_path),'commands':n,
      'placements':placement_count,'baseline_expansions':expansion_count,
      'evaluated_next_arrivals':len(evaluated),
      'model':{'window_placements':W,'dirichlet_global_prior_strength':ALPHA,'labels':K,
               'conditioning':'P(next positive pipe length | current positive pipe length)',
               'baseline':'rolling marginal over previous 2048 positive pipe lengths with Laplace-1 smoothing'},
      'all_next_arrivals':all_stats,
      'at_expansion_decisions':expansion_stats,
    }
    return result, evaluated

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--answer',type=Path,required=True)
    ap.add_argument('--json',type=Path,required=True)
    ap.add_argument('--csv',type=Path)
    args=ap.parse_args()
    result,rows=analyze(args.input,args.answer)
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(result,indent=2)+'\n')
    if args.csv:
        args.csv.parent.mkdir(parents=True,exist_ok=True)
        cols=['placement_index','current_length','actual','is_expansion','row_support','markov_correct','marginal_correct','markov_confidence','marginal_confidence','markov_logloss','marginal_logloss','markov_brier','marginal_brier']
        with args.csv.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
            for r in rows:w.writerow({k:r[k] for k in cols})
    print(json.dumps({'input':str(args.input),'expansions':result['baseline_expansions'],
                      'all':result['all_next_arrivals'],'expansion':result['at_expansion_decisions']},indent=2))
if __name__=='__main__': main()
