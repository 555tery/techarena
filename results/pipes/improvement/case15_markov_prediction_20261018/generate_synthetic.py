from __future__ import annotations
import hashlib, json, random
from pathlib import Path
OUT=Path(__file__).resolve().parent/'synthetic'
SEEDS=[20261018201,20261018213,20261018227,20261018239,20261018251,20261018263]
INITIAL=700
EVENTS=40_000

def draw(i, t, prev, rng):
    phase=t//10_000
    if i==1: return rng.randint(1,40)
    if i==2:
        return prev if rng.random()<0.75 else rng.randint(1,40)
    if i==3:
        cycle=(4,8,12,20,32,16)
        value=cycle[t%len(cycle)]
        return rng.randint(1,40) if rng.random()<0.10 else value
    if i==4:
        return max(1,min(40,prev+rng.choice((-1,1))))
    if i==5:
        bands=((1,10),(10,20),(21,30),(31,40))
        lo,hi=bands[phase]
        return rng.randint(lo,hi)
    # Markov anti-persistence between two disjoint size bands.
    if 1<=prev<=8:
        return rng.randint(25,40) if rng.random()<0.82 else rng.randint(1,8)
    if 25<=prev<=40:
        return rng.randint(1,8) if rng.random()<0.82 else rng.randint(25,40)
    return rng.randint(1,8) if rng.random()<0.5 else rng.randint(25,40)

def gen(i):
    rng=random.Random(SEEDS[i-1])
    commands=[]; live=[]; pid=1; prev=rng.randint(1,40)
    for t in range(INITIAL):
        size=draw(i,t,prev,rng); commands.append(size); live.append(pid); pid+=1; prev=size
    descriptions={
      1:'uniform iid sizes; random deletions',
      2:'first-order size persistence P(same)=0.75; LIFO deletions',
      3:'noisy six-size cycle; FIFO deletions',
      4:'bounded random walk in size; newest-5%-biased deletions',
      5:'four independent size phases; median-rank deletions',
      6:'first-order anti-persistent short/long bands; alternating newest/oldest deletions',
    }
    for t in range(EVENTS):
        if t%2==0:
            size=draw(i,t,prev,rng); commands.append(size); live.append(pid); pid+=1; prev=size
        else:
            if i==1: idx=rng.randrange(len(live))
            elif i==2: idx=len(live)-1
            elif i==3: idx=0
            elif i==4:
                if rng.random()<0.85:
                    lo=max(0,len(live)-max(1,len(live)//20)); idx=rng.randrange(lo,len(live))
                else: idx=rng.randrange(len(live))
            elif i==5:
                idx=max(0,min(len(live)-1,len(live)//2+rng.randint(-20,20)))
            else: idx=len(live)-1 if (t//2000)%2==0 else 0
            commands.append(-live.pop(idx))
    path=OUT/f'markov_case_{i:02d}.in'
    path.write_text(f'1.0 {len(commands)}\n'+'\n'.join(map(str,commands))+'\n')
    return {'name':path.stem,'seed':SEEDS[i-1],'commands':len(commands),'initial_live':INITIAL,
            'final_live':len(live),'description':descriptions[i],
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
OUT.mkdir(parents=True,exist_ok=True)
rows=[gen(i) for i in range(1,7)]
(OUT/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
