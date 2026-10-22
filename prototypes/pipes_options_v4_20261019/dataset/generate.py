"""Policy-blind matched-prefix continuations. No solver imports or score access."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import secrets

FAMILIES = ['renewal', 'complements', 'size_survival', 'bursts',
            'alternating_support', 'anchors', 'ring_queue', 'bursty_lengths']
BRANCHES = ['growth', 'drain', 'size_shift', 'early_stop']
ROOT = Path(__file__).resolve().parents[1]

class Stream:
    def __init__(self):
        self.commands, self.live, self.lengths = [], {}, [0]
    def add(self, length):
        pid = len(self.lengths)
        self.lengths.append(length); self.live[pid] = length; self.commands.append(length)
    def delete(self, rng, mode='random'):
        if not self.live: return False
        ids = list(self.live)
        pid = min(ids) if mode == 'fifo' else max(ids) if mode == 'lifo' else (
            max(ids, key=lambda x:self.live[x]) if mode == 'large' else rng.choice(ids))
        self.commands.append(-pid); del self.live[pid]
        return True
    def replay(self, commands):
        for c in commands:
            if c > 0: self.add(c)
            else: self.commands.append(c); del self.live[-c]

def prefix(family, rng, n=24, live_cap=8):
    s=Stream()
    for i in range(n):
        l = rng.randint(1,12)
        p, mode = .56, 'random'
        if family == 'complements': l=rng.choice([3,7,9,11,13,17]); mode='fifo'
        elif family == 'size_survival': l=rng.choice([2,3,4,9,10,12]); mode='large'
        elif family == 'bursts': p=.90 if i%10<6 else .10; mode='lifo'
        elif family == 'alternating_support': l=rng.randint(1,5) if i%12<6 else rng.randint(18,32); mode='fifo'
        elif family == 'anchors': l=rng.randint(20,40) if i<3 else rng.randint(1,8); mode='lifo'
        elif family == 'ring_queue': l=rng.randint(4,18) if i%11<7 else rng.randint(1,4); p=.70 if i%17<10 else .20; mode='fifo'
        elif family == 'bursty_lengths': l=[3,17,8,12,27,4][(i//5)%6]; p=.85 if i%9<6 else .10; mode='lifo'
        if not s.live or (len(s.live)<live_cap and rng.random()<p): s.add(l)
        else: s.delete(rng,mode)
    return s.commands

def extend(commands, branch, rng, n=64):
    s=Stream();s.replay(commands)
    if branch=='early_stop': return s.commands
    while len(s.commands)<n:
        j=len(s.commands)-len(commands)
        l=rng.randint(1,12); p=.85;mode='random'
        if branch=='drain': p=.10 if j<16 else .52;mode='fifo'
        elif branch=='size_shift': l=rng.randint(13,40);p=.60;mode='large'
        if not s.live or rng.random()<p:s.add(l)
        else:s.delete(rng,mode)
    return s.commands

def write(path, commands):
    raw=('1\n'+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n0\n').encode()
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    live={};pid=0;peak=0
    for c in commands:
        if c>0:pid+=1;live[pid]=c
        else:del live[-c]
        peak=max(peak,sum(live.values()))
    return {'sha256':hashlib.sha256(raw).hexdigest(),'n':len(commands),'final_volume':sum(live.values()),'peak_volume':peak}

def generate(phase):
    target=ROOT/'data'/phase
    if target.exists():raise ValueError('No overwrites or resampling')
    if phase=='final' and not (ROOT/'freeze.json').exists():raise ValueError('Final requires freeze')
    target.mkdir(parents=True)
    seeds={};records=[]
    for family in FAMILIES[:4] if phase!='final' else FAMILIES:
        for rep in range(2):
            base=f'{family}_{rep}'; seed=secrets.randbits(128);seeds[base]=seed
            common=prefix(family,random.Random(seed))
            for branch in BRANCHES:
                branchseed=int.from_bytes(hashlib.sha256(f'{seed}:{branch}'.encode()).digest(),'big')
                commands=extend(common,branch,random.Random(branchseed))
                name=f'{base}_{branch}'
                meta=write(target/f'{name}.in',commands)
                records.append(dict(name=name,family=family,rep=rep,branch=branch,base=base,
                                    common_prefix=common,seed=seed,branch_seed=branchseed,**meta))
    if phase=='final':
        # Independent long streams for resource correctness. Their scores have
        # their own scope, not extra weight in the matched-fork quality mean.
        for family in FAMILIES[4:]:
            seed=secrets.randbits(128);seeds['resource_'+family]=seed
            commands=prefix(family,random.Random(seed),200000,200000 if family in ('anchors','ring_queue') else 8)
            name='resource_'+family
            records.append(dict(name=name,family=family,branch='resource',seed=seed,
                                **write(target/f'{name}.in',commands)))
    manifest={'phase':phase,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'seeds':seeds,'records':records,'count':len(records)}
    (ROOT/'data'/f'{phase}.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'phase':phase,'count':len(records)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['train0','train1','train2','dev','final']);generate(p.parse_args().phase)
