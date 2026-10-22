"""Fixed fresh seeds and causal regimes, declared before candidate evaluation."""
import json
import random
import sys
from build_online_fallback import HERE,ROOT,PREV,e

def main():
    holdout='--holdout' in sys.argv
    folder=HERE/('holdout' if holdout else 'neutral');folder.mkdir(exist_ok=True)
    specs=[(918301,0,0,'iid',10000),(918302,0,0,'lifo',10000),
           (918303,0,0,'fifo',10000),(918304,0,0,'walk',10000),
           (918305,1,6,'young',10000),(918306,2,18,'iid',10000),
           (918307,3,12,'lifo',10000),(918308,10,1000,'fifo',14000),
           (918309,14,1000,'walk',14000),(918310,12,34,'young',10000),
           (918311,0,0,'walk',200000),(918312,2,18,'young',200000)]
    if holdout:specs=[(seed+1000,case,cut,kind,total) for seed,case,cut,kind,total in specs]+[(919313,0,0,'runs',16000),(919314,0,0,'burst',16000)]
    rows=[]
    for seed,case,cut,kind,total in specs:
        rng=random.Random(seed)
        cmd=e.commands(ROOT/f'data/pipes/open/{case}.in')[:cut] if case else []
        live=[];pid=0
        for c in cmd:
            if c>0:pid+=1;live.append(pid)
            else:live.remove(-c)
        length=7
        while len(cmd)<total-1:
            if live and (len(live)>192 or rng.random()<.49):
                if kind=='lifo':index=len(live)-1
                elif kind=='fifo':index=0
                elif kind=='young':index=max(0,len(live)-1-rng.randrange(min(12,len(live))))
                else:index=rng.randrange(len(live))
                cmd.append(-live.pop(index))
            else:
                if kind=='walk':length=max(1,min(40,length+rng.choice([-2,-1,0,1,2])))
                elif kind=='runs':length=1+(len(cmd)//120)%40
                elif kind=='burst':length=rng.choice([1,2,3]) if len(cmd)%500<350 else rng.randint(25,40)
                elif kind=='young':length=rng.choice([1,1,2,3,4,20,40])
                else:length=rng.randint(1,40)
                cmd.append(length);pid+=1;live.append(pid)
        cmd.append(40)
        p=folder/f'neutral-{seed}-{kind}.in'
        p.write_text('1\n'+str(len(cmd))+'\n'+'\n'.join(map(str,cmd))+'\n')
        rows.append({'seed':seed,'family':kind,'open_case':case,'prefix_length':cut,
                     'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),**e.harness.parse_test(p)})
    (folder/'manifest.json').write_text(json.dumps({'selection':'fixed before candidate scores; no rejection by outcome','specs':specs,'tests':rows},indent=2)+'\n')

if __name__=='__main__':main()
