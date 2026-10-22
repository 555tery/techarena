"""Predeclared new seeds, regimes and long shared prefixes; no selection by score."""
import json
import random
from common import HERE,ROOT,e

def main():
    specs=[(920401,2,18,'iid',12000),(920402,2,18,'fifo',12000),
           (920403,3,12,'young',12000),(920404,14,17000,'lifo',20000),
           (920405,12,224,'walk',12000),(920406,10,5383,'burst',18000),
           (920407,0,0,'iid',12000),(920408,0,0,'runs',12000),
           (920409,2,18,'walk',200000),(920410,15,100000,'young',200000),
           (920411,8,388,'iid',12000),(920412,13,388,'fifo',12000),
           (920413,8,402,'young',12000),(920414,13,1111,'walk',12000)]
    out=HERE/'holdout';out.mkdir(exist_ok=True);rows=[]
    for seed,case,cut,kind,total in specs:
        rng=random.Random(seed);cmd=e.commands(ROOT/f'data/pipes/open/{case}.in')[:cut] if case else []
        live=[];pid=0;length=7
        for c in cmd:
            if c>0:pid+=1;live.append(pid)
            else:live.remove(-c)
        while len(cmd)<total-1:
            if live and (len(live)>256 or rng.random()<.49):
                if kind=='fifo':index=0
                elif kind=='lifo':index=len(live)-1
                elif kind=='young':index=len(live)-1-rng.randrange(min(16,len(live)))
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
        p=out/f'holdout-{seed}-{kind}.in';p.write_text('1\n'+str(total)+'\n'+'\n'.join(map(str,cmd))+'\n')
        rows.append({'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),'seed':seed,'family':kind,'prefix_case':case,'prefix_length':cut,**e.harness.parse_test(p)})
    (out/'manifest.json').write_text(json.dumps({'specs':specs,'selection':'fixed after proposal freeze, before its evaluation; no score-based seed rejection','tests':rows},indent=2)+'\n')

if __name__=='__main__':main()
