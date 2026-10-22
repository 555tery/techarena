#!/usr/bin/env python3
"""Independent gate-coverage diagnostics; no contest input is read."""
from pathlib import Path
import argparse,random,json,hashlib
ROOT=Path(__file__).resolve().parent

def design(split):
    if split.startswith('large_'):
        rng=random.Random(52019237 if split=='large_dev' else 7291631)
        rows=[]
        for i in range(6):
            rows.append(dict(name=f'{split}_{i:02d}',seed=rng.randrange(2**32),
                target_live=([5120,8192,12288][i%3] if split=='large_dev' else [6144,10240,14336][i%3]),
                operations=(30000 if split=='large_dev' else 60000),
                profile=('recent_geometric' if i<3 else 'old_tail_mix'),
                recent_window=([8,32,96][i%3] if split=='large_dev' else [12,48,128][i%3]),
                old_delete_p=(0 if i<3 else 0.035),
                size_profile=('small_uniform' if i%2 else 'small_units')))
        return dict(schema='fresh-large-lifo-coverage-v1',split=split,
            purpose='Independent gate coverage above4096 live objects, no contest input copied.',cases=rows)
    rng=random.Random(8102019 if split=='dev' else 3198217)
    rows=[]
    for i in range(12):
        target=[192,576,1536,3008][i%4] if split=='dev' else rng.choice([256,768,1280,2048,3328])
        profile=['recent_uniform','recent_geometric','old_tail_mix'][i//4] if split=='dev' else ['recent_geometric','old_tail_mix','recent_uniform'][i//4]
        rows.append(dict(name=f'{split}_{i:02d}_{profile}',seed=rng.randrange(2**32),
            target_live=target,operations=(10000 if split=='dev' else 18000),
            profile=profile,recent_window=rng.choice([8,16,32,64]),
            old_delete_p=(0.025 if profile=='old_tail_mix' else 0.0),
            size_profile=('small_units' if i%3==0 else 'small_uniform')))
    return dict(schema='fresh-lifo-gate-coverage-v1',split=split,
        purpose='Coverage of existing short-request LIFO confidence and scale gate, independently generated after policy design. No contest stream or old validation copied.',
        cases=rows)

def generate(row):
    rng=random.Random(row['seed']);active=[];pid=0;ops=[]
    for _ in range(row['operations']-1):
        n=len(active);target=row['target_live']
        insert=n<target or (n<target+12 and rng.random()<0.5)
        if insert:
            length=1 if row['size_profile']=='small_units' and rng.random()<.6 else rng.randint(1,8)
            pid+=1;active.append(pid);ops.append(length)
        else:
            if rng.random()<row['old_delete_p']:
                index=rng.randrange(n)
            elif row['profile']=='recent_geometric':
                rank=min(n-1,int(rng.expovariate(1/(row['recent_window']/3))))
                index=n-1-rank
            else:
                index=n-1-rng.randrange(min(n,row['recent_window']))
            ops.append(-active.pop(index))
    # End with a regular request; all final live objects remain ordinary.
    ops.append(rng.randint(1,8))
    return ops

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['dev','sealed','large_dev','large_sealed'],required=True);ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
    out=ROOT/'fresh_checks'/('lifo_'+args.split);out.mkdir(exist_ok=True)
    d=design(args.split);encoded=(json.dumps(d,indent=2)+'\n').encode();file=out/'design.json'
    if file.exists():assert file.read_bytes()==encoded
    else:file.write_bytes(encoded)
    if args.prepare_only:print(json.dumps(dict(status='design_only',cases=len(d['cases']),sha256=hashlib.sha256(encoded).hexdigest())));return
    rows=[]
    for row in d['cases']:
        ops=generate(row);text=f"1.0 {len(ops)}\n"+'\n'.join(map(str,ops+[0]))+'\n';f=out/(row['name']+'.in')
        if f.exists():assert f.read_text()==text
        else:f.write_text(text)
        rows.append(dict(name=row['name'],sha256=hashlib.sha256(text.encode()).hexdigest(),operations=len(ops)))
    (out/'manifest.json').write_text(json.dumps(dict(design_sha256=hashlib.sha256(encoded).hexdigest(),cases=rows),indent=2)+'\n');print(json.dumps(dict(status='generated',cases=len(rows),out=str(out))))
if __name__=='__main__':main()
