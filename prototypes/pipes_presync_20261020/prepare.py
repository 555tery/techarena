"""Known-only reference traces for bounded pre-synchronization search."""
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
GHOST=ROOT/'prototypes/pipes_ghost_handoff_20261020'
spec=importlib.util.spec_from_file_location('ge',GHOST/'evaluate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'));from construct import decode
PARENT=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    tables=decode(PARENT/'solution.cpp');files=g.tests('known')+[(f'last48-{i}',p) for i,p in g.tests('fresh')]+[(f'early-{i}',p) for i,p in g.tests('early-diagnostics')]
    files=list({sha(p):(i,p) for i,p in files}.values());affected=[];meta=[]
    trace=HERE/'reference';trace.mkdir(exist_ok=True)
    for ident,path in files:
        parts=path.read_text().split();n=int(parts[1]);commands=list(map(int,parts[2:2+n]))
        meta.append({'id':ident,'path':str(path),'sha256':sha(path),'n':n})
        if commands[0]!=3:continue
        result=subprocess.run([str(PARENT/'solver')],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,check=True,timeout=60)
        lines=result.stdout.splitlines();assert len(lines)==n
        active=list(range(15));done=False;rows=[];T=pid=0;live={}
        for step,(c,line) in enumerate(zip(commands,lines)):
            if c>0:
                digs,x=map(int,line.split());assert digs>=0 and x>=0;T+=20*digs;pid+=1;live[pid]=(x,c)
            else:
                x=int(line);assert x==live[-c][0];del live[-c]
            replay=False
            if not done:
                active=[ci for ci in active if step<len(tables[ci][0]) and tables[ci][0][step]==c]
                if active:
                    if c>0:assert len({tables[ci][1][step] for ci in active})==1 and tables[active[0]][1][step]==x
                    replay=True
                else:done=True
            rows.append((c,x,T,int(replay)))
        affected.append((ident,rows,T));(trace/(ident+'.stderr')).write_text(result.stderr)
        (trace/(ident+'.json')).write_text(json.dumps({'id':ident,'source_path':str(path),'test_sha256':sha(path),'rows':rows,'T':T})+'\n')
    with (HERE/'search.in').open('w') as f:
        f.write(str(len(affected))+'\n')
        for ident,rows,T in affected:
            f.write(f'{ident} {len(rows)} {T}\n')
            f.writelines(' '.join(map(str,r))+'\n' for r in rows)
    (HERE/'known.json').write_text(json.dumps({'tests':meta,'affected_ids':[i for i,r,T in affected],
        'parent_source_sha256':sha(PARENT/'solution.cpp'),'parent_binary_sha256':sha(PARENT/'solver'),
        'scope':'227 previously observed inputs; selection, not fresh confirmation'},indent=2)+'\n')
    print('known',len(files),'affected',len(affected),flush=True)
if __name__=='__main__':main()
