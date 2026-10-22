"""Register observed inputs and produce causal parent traces for late-prefix search."""
import datetime, hashlib, importlib.util, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREV=ROOT/'prototypes/pipes_presync_20261020'
spec=importlib.util.spec_from_file_location('prev_eval',PREV/'evaluate.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    tables=e.g.p.e.decode(e.g.BASE.parent/'solution.cpp') if hasattr(e.g.p.e,'decode') else None
    if tables is None:
        import sys
        sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
        from construct import decode
        tables=decode(e.g.BASE.parent/'solution.cpp')
    joint=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    changes=json.loads((ROOT/'prototypes/pipes_prefix_replan_20261020/final/build.json').read_text())['changes']
    changes={int(k):v for k,v in changes.items() if int(k)!=21532}
    files=e.files('known')+[(f'prev64-{i}',p) for i,p in e.files('fresh')]+[(f'diag-{i}',p) for i,p in e.files('diagnostic')]
    files=list({sha(p):(i,p) for i,p in files}.values())
    rows=[];affected=[];trace=HERE/'reference';trace.mkdir(exist_ok=True)
    for ident,path in files:
        parts=path.read_text().split();n=int(parts[1]);commands=list(map(int,parts[2:2+n]))
        rows.append({'id':ident,'path':str(path),'sha256':sha(path),'n':n})
        active=list(range(15));done=False;replays=[];affected_here=False
        for step,c in enumerate(commands):
            if not done: active=[i for i in active if step<len(tables[i][0]) and tables[i][0][step]==c]
            if not active:done=True
            bid=joint['cases'][active[0]]['block_ids'][step] if not done else -1
            planned=changes.get(bid,-1) if c>0 else -1
            if planned>=0:affected_here=True
            replays.append((int(not done),planned,bid))
        if not affected_here:continue
        dest=trace/(ident+'.json')
        if dest.exists():r=json.loads(dest.read_text());assert r['test_sha256']==sha(path)
        else:
            p=subprocess.run([str(e.g.BASE)],input='\n'.join(map(str,commands+[0]))+'\n',capture_output=True,text=True,check=True,timeout=60)
            lines=p.stdout.splitlines();assert len(lines)==n
            rr=[];T=0
            for c,line,(replay,planned,bid) in zip(commands,lines,replays):
                if c>0:digs,x=map(int,line.split());T+=20*digs
                else:x=int(line)
                rr.append([c,x,T,replay,planned,bid])
            r={'id':ident,'source_path':str(path),'test_sha256':sha(path),'rows':rr,'T':T}
            dest.write_text(json.dumps(r)+'\n');(trace/(ident+'.stderr')).write_text(p.stderr)
        affected.append(r);print(ident,n,r['T'],flush=True)
    with (HERE/'search.in').open('w') as f:
        f.write(str(len(affected))+'\n')
        for r in affected:
            f.write(f"{r['id']} {len(r['rows'])} {r['T']}\n")
            f.writelines(' '.join(map(str,row))+'\n' for row in r['rows'])
    (HERE/'known.json').write_text(json.dumps({'tests':rows,'affected_ids':[r['id'] for r in affected],
        'parent_source_sha256':sha(e.g.BASE.parent/'solution.cpp'),'parent_binary_sha256':sha(e.g.BASE),
        'scope':'All previously observed inputs; selection/regression only'},indent=2)+'\n')
    print('known',len(rows),'affected',len(affected),flush=True)
if __name__=='__main__':main()
