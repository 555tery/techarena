"""Precommitted independent mechanisms; never reads contest inputs/results."""
import argparse, hashlib, importlib.util, json, random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261018T131350+0700'

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def design(split):
    general=load('general_generator',OLD/'generate_checks.py')
    lifo=load('lifo_generator',OLD/'generate_lifo_checks.py')
    seed=391721409 if split=='dev' else 1873264109
    rng=random.Random(seed);rows=[]
    for r in general.specs('sealed'):
        r.update(seed=rng.randrange(2**32),operations=(16000 if split=='dev' else 60000))
        rows.append(dict(kind='general',name=f'{split}_{len(rows):02}_{r["family"]}',spec=r))
    for r in lifo.design('large_sealed')['cases']:
        r.update(seed=rng.randrange(2**32),operations=(36000 if split=='dev' else 100000))
        rows.append(dict(kind='lifo',name=f'{split}_{len(rows):02}_large_recent',spec=r))
    for i in range(6):
        rows.append(dict(kind='frames',name=f'{split}_{len(rows):02}_frames',spec=dict(seed=rng.randrange(2**32),operations=20000 if split=='dev' else 80000,retain_probability=[.08,.2,.35][i%3],max_frame=[8,32,128][i%3],size_limit=[4,8,40][i%3],shift=i>=3)))
    for i in range(6):
        rows.append(dict(kind='micro',name=f'{split}_{len(rows):02}_micro',spec=dict(seed=rng.randrange(2**32),operations=80+i*40,max_live=3+i*2,size_limit=40)))
    return dict(version='independent-autonomous-v1',split=split,contest_inputs_read=False,solver_results_read=False,cases=rows)

def custom(row):
    r=row['spec'];rng=random.Random(r['seed']);ops=[];alive=[];pid=0
    def insert(length):
        nonlocal pid
        pid+=1;alive.append(pid);ops.append(length);return pid
    def delete(p):
        alive.remove(p);ops.append(-p)
    if row['kind']=='micro':
        while len(ops)<r['operations']:
            if not alive or (len(alive)<r['max_live'] and rng.random()<.66):insert(rng.randint(1,r['size_limit']))
            else:delete(rng.choice(alive))
    else:
        while len(ops)<r['operations']:
            frame=[]
            for _ in range(rng.randint(1,r['max_frame'])):
                if len(ops)>=r['operations']:break
                hi=40 if r['shift'] and len(ops)>r['operations']//2 else r['size_limit']
                frame.append(insert(rng.randint(1,hi)))
            for p in reversed(frame):
                if len(ops)>=r['operations']:break
                if rng.random()>r['retain_probability']:delete(p)
            if alive and rng.random()<.06 and len(ops)<r['operations']:delete(rng.choice(alive))
    if not alive:
        # Keep the length exactly as preregistered, with a nonempty final layout.
        ops[-1]=1
    return ops

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--split',choices=['dev','release'],required=True);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    d=ROOT/'fresh'/a.split;d.mkdir(exist_ok=True);value=design(a.split);encoded=json.dumps(value,indent=2)+'\n';p=d/'design.json'
    if p.exists() and p.read_text()!=encoded:raise ValueError('design changed')
    p.write_text(encoded)
    if a.prepare_only:return
    general=load('general',OLD/'generate_checks.py');lifo=load('lifo',OLD/'generate_lifo_checks.py');records=[]
    for row in value['cases']:
        if row['kind']=='general':ops=general.generate(row['spec'])
        elif row['kind']=='lifo':ops=lifo.generate(row['spec'])
        else:ops=custom(row)
        data=(f'1.0 {len(ops)}\n'+'\n'.join(map(str,ops+[0]))+'\n').encode();path=d/(row['name']+'.in')
        if path.exists() and path.read_bytes()!=data:raise ValueError('input changed')
        path.write_bytes(data);records.append(dict(name=row['name'],sha256=hashlib.sha256(data).hexdigest(),operations=len(ops),kind=row['kind']))
    (d/'manifest.json').write_text(json.dumps(dict(design_sha256=hashlib.sha256(encoded.encode()).hexdigest(),cases=records),indent=2)+'\n')
    print(json.dumps(dict(split=a.split,cases=len(records))))

if __name__=='__main__':main()
