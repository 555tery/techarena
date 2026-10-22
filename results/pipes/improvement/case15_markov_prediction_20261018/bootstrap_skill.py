from __future__ import annotations
import csv, json, random, sys
from collections import defaultdict
from pathlib import Path

BLOCK=1024
REPLICATES=2000
SEED=20261018

def percentile(xs, q):
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(pos); alpha=pos-lo
    return ys[lo]*(1-alpha)+ys[min(lo+1,len(ys)-1)]*alpha

def run(csv_path: Path):
    rows=list(csv.DictReader(csv_path.open()))
    out={}
    rng=random.Random(SEED)
    for scope, subset in [('all',rows),('expansions',[r for r in rows if r['is_expansion']=='True'])]:
        groups=defaultdict(lambda:[0,0.0,0.0,0.0])
        for r in subset:
            block=(int(r['placement_index'])-1)//BLOCK
            agg=groups[block]; agg[0]+=1
            agg[1]+=int(r['markov_correct'])-int(r['marginal_correct'])
            agg[2]+=float(r['marginal_logloss'])-float(r['markov_logloss'])
            agg[3]+=float(r['marginal_brier'])-float(r['markov_brier'])
        blocks=list(groups.values())
        denom=sum(x[0] for x in blocks)
        means=[sum(x[j] for x in blocks)/denom for j in (1,2,3)]
        boot=[[],[],[]]
        for _ in range(REPLICATES):
            sample=[blocks[rng.randrange(len(blocks))] for _ in range(len(blocks))]
            n=sum(x[0] for x in sample)
            for k,j in enumerate((1,2,3)):
                boot[k].append(sum(x[j] for x in sample)/n)
        out[scope]={
          'n_events':len(subset),'block_size_placements':BLOCK,'blocks':len(blocks),
          'metrics':['top1_markov_minus_marginal','logloss_marginal_minus_markov','brier_marginal_minus_markov'],
          'mean_differences':means,
          'block_bootstrap_95_ci':[[percentile(boot[k],.025),percentile(boot[k],.975)] for k in range(3)],
          'replicates':REPLICATES,'seed':SEED,
        }
    return out

if __name__=='__main__':
    result=run(Path(sys.argv[1]))
    out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
