"""Predeclared neutral smoke streams, never used for choosing the candidate."""
import json
import random
from experiment import HERE, harness, sha

def main():
    folder=HERE/'neutral';folder.mkdir(exist_ok=True)
    rows=[]
    for seed in [67219,67220,67221,67222,67223,67224]:
        rng=random.Random(seed);live=[];cmds=[];pid=0
        for i in range(6000 if seed!=67224 else 200000):
            if live and (len(live)>130 or rng.random()<.48):
                ix=rng.randrange(len(live)) if seed%2 else len(live)-1
                cmds.append(-live.pop(ix))
            else:
                length=rng.randint(1,40) if seed%3 else rng.choice([1,2,3,20,39,40])
                pid+=1;live.append(pid);cmds.append(length)
        p=folder/f'neutral-{seed}.in'
        p.write_text('1\n'+str(len(cmds))+'\n'+'\n'.join(map(str,cmds))+'\n')
        meta=harness.parse_test(p)
        rows.append({'file':str(p),'sha256':sha(p),**meta})
    (folder/'manifest.json').write_text(json.dumps({'seeds':[67219,67220,67221,67222,67223,67224],
       'selection':'fixed prior to candidate validation; no best-of-seed selection','tests':rows},indent=2)+'\n')

if __name__=='__main__':main()
