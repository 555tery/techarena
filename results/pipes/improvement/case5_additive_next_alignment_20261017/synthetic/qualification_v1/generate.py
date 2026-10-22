from __future__ import annotations
import hashlib, json, random
from pathlib import Path

ROOT=Path('results/pipes/improvement/case5_additive_next_alignment_20261017/synthetic/qualification_v1')
OUT=ROOT/'traces'
SEED_START=20261031
COUNT_OPTIONS=[40,45,46,60,80,100,125,160]
DELETE_OPTIONS=['fifo','lifo','stride2','random','mixed']
TRUNCATIONS=[0.62,0.80,1.0]

def build_sizes(rng: random.Random, idx: int):
    start=rng.randint(1,6)
    blocks=rng.randint(7,15)
    family=idx%5
    if family==0:
        sizes=list(range(start,min(40,start+blocks)))
        label='strict_ascending_plus_one'
    elif family==1:
        sizes=list(range(start,min(40,start+blocks)))
        if len(sizes)>5:
            at=rng.randint(3,len(sizes)-2)
            sizes[at]=sizes[at-1]
            for j in range(at+1,len(sizes)):
                sizes[j]=sizes[j-1]+1
        label='ascending_with_one_repeat'
    elif family==2:
        sizes=list(range(start,min(40,start+blocks)))
        if len(sizes)>6:
            at=rng.randint(3,len(sizes)-3)
            jump=rng.choice([2,3])
            for j in range(at,len(sizes)):
                sizes[j]+=jump-1
        label='ascending_with_phase_jump'
    elif family==3:
        step=rng.choice([2,3])
        sizes=list(range(start,min(40,start+blocks*step),step))
        label=f'step_{step}_ascending'
    else:
        sizes=list(range(start,min(40,start+blocks)))[::-1]
        label='descending_plus_one'
    return sizes,label

manifest=[]
for idx in range(20):
    seed=SEED_START+idx
    rng=random.Random(seed)
    sizes,label=build_sizes(rng,idx)
    counts=[rng.choice(COUNT_OPTIONS) for _ in sizes]
    deletion=DELETE_OPTIONS[(idx*3+1)%len(DELETE_OPTIONS)]
    truncate=TRUNCATIONS[(idx//2)%len(TRUNCATIONS)]
    commands=[]
    pid=1
    for block_idx,(length,count) in enumerate(zip(sizes,counts,strict=True)):
        pids=list(range(pid,pid+count))
        commands.extend([length]*count)
        mode=deletion
        if mode=='mixed': mode='fifo' if block_idx%2==0 else 'random'
        if mode=='fifo': removed=pids[:count//2]
        elif mode=='lifo': removed=pids[count-count//2:]
        elif mode=='stride2': removed=pids[::2]
        else: removed=sorted(rng.sample(pids,count//2))
        commands.extend(-p for p in removed)
        pid+=count
    keep=max(1,int(len(commands)*truncate))
    commands=commands[:keep]
    path=OUT/f's{idx+1:02d}.in'
    text=f'1.0 {len(commands)}\n'+'\n'.join(map(str,commands))+'\n'
    path.write_text(text)
    manifest.append({'name':path.stem,'seed':seed,'family':label,'sizes':sizes,'counts':counts,'deletion':deletion,'truncation_fraction':truncate,'commands':len(commands),'sha256':hashlib.sha256(text.encode()).hexdigest()})
(ROOT/'manifest.json').write_text(json.dumps({'seed_start':SEED_START,'streams':manifest},indent=2)+'\n')
print(json.dumps({'streams':len(manifest),'commands_total':sum(x['commands'] for x in manifest),'manifest':str(ROOT/'manifest.json')},indent=2))
