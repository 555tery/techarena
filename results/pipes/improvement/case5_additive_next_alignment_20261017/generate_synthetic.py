from __future__ import annotations
import json
import random
from pathlib import Path

OUT = Path('results/pipes/improvement/case5_additive_next_alignment_20261017/synthetic')
SEED = 20261017
SCENARIOS = [
    {'name':'fifo_additive', 'sizes':list(range(1,25)), 'counts':[100]*24, 'delete':'fifo', 'description':'Additive +1 blocks; delete the oldest half of each new block.'},
    {'name':'lifo_additive', 'sizes':list(range(4,28)), 'counts':[100]*24, 'delete':'lifo', 'description':'Additive +1 blocks; delete the newest half of each new block.'},
    {'name':'stride2_additive', 'sizes':list(range(1,21)), 'counts':[90+(i%3)*10 for i in range(20)], 'delete':'stride2', 'description':'Additive +1 blocks with varying block counts and alternating PID parity removals.'},
    {'name':'mixed_phase_shift', 'sizes':list(range(1,11))+list(range(12,22))+list(range(23,31)), 'counts':[100]*28, 'delete':'random', 'description':'Additive phases separated by jumps; remove a random half of each block.'},
]
OUT.mkdir(parents=True, exist_ok=True)
metadata=[]
for idx, spec in enumerate(SCENARIOS):
    rng=random.Random(SEED+idx)
    commands=[]
    next_pid=1
    for length,count in zip(spec['sizes'],spec['counts'],strict=True):
        block=list(range(next_pid,next_pid+count))
        commands.extend([length]*count)
        if spec['delete']=='fifo':
            removals=block[:count//2]
        elif spec['delete']=='lifo':
            removals=block[count-count//2:]
        elif spec['delete']=='stride2':
            removals=block[::2]
        else:
            removals=sorted(rng.sample(block,count//2))
        commands.extend(-pid for pid in removals)
        next_pid += count
    data=f'1.0 {len(commands)}\n'+'\n'.join(map(str,commands))+'\n'
    path=OUT/f'{spec["name"]}.in'
    path.write_text(data)
    metadata.append({'name':spec['name'],'seed':SEED+idx,'commands':len(commands),'placements':sum(spec['counts']),'sizes':spec['sizes'],'counts':spec['counts'],'deletion':spec['delete'],'description':spec['description']})
(OUT/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata,indent=2))
