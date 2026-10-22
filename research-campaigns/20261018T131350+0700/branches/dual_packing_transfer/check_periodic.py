from pathlib import Path
import random,json,time
D=Path(__file__).resolve().parent
rng=random.Random(3619827);sets=[[0]*41,[0]+[k*65536 for k in range(1,41)]]
for k in [1,2,7,19,39,40]:
    p=[0]*41;p[k]=k*65536;sets.append(p)
for _ in range(32):sets.append([0]+[rng.randrange(k*65536+1) for k in range(1,41)])
started=time.time();checked=0
for prices in sets:
    b=1
    for k in range(2,41):
        if prices[k]*b>prices[b]*k:b=k
    dp=[0]*5001
    for c in range(1,5001):dp[c]=max(dp[c-1],max(dp[c-k]+prices[k] for k in range(1,min(40,c)+1)))
    for c in range(1601,5001):
        periods=(c-1600-1)//b+1;base=c-periods*b
        assert 0<=base<=1600 and dp[c]==dp[base]+periods*prices[b],(prices,b,c)
        checked+=1
report=dict(status='passed',price_sets=len(sets),capacities_checked=checked,max_capacity=5000,limit=1600,seed=3619827,elapsed_s=time.time()-started,meaning='Independent full-capacity DP versus periodic continuation; finite verification complements the mathematical exchange argument, not a universal proof.')
(D/'periodic-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
