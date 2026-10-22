import json
import subprocess
from pathlib import Path
from build_proposal import HERE,ROOT,PRIOR,e

BF=[str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')]

def known_files():
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('prior_validation',PRIOR/'validate.py')
    # That module uses its local helper by name.
    import sys
    if str(PRIOR) not in sys.path:sys.path.insert(0,str(PRIOR))
    mod=module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.old_files()+sorted((PRIOR/'attacks').glob('*.in'))+sorted((PRIOR/'counterattacks').glob('*.in'))+sorted((PRIOR/'holdout').glob('*.in'))+sorted((PRIOR/'safety').glob('*.in'))

def screen(argv,path):
    cmd=e.commands(path)
    result=subprocess.run(list(map(str,argv)),input='\n'.join(map(str,cmd+[0]))+'\n',capture_output=True,text=True,check=True,timeout=30)
    lines=result.stdout.splitlines();assert len(lines)==len(cmd),(path,len(lines),len(cmd))
    active={};cells=set();pid=T=0
    for c,line in zip(cmd,lines):
        if c>0:
            digs,x=map(int,line.split());assert digs>=0 and x>=0
            T+=20*digs;assert x+c<=T
            used=set(range(x,x+c));assert not cells&used
            cells.update(used);pid+=1;active[pid]=(x,c)
        else:
            x,n=active.pop(-c);assert int(line)==x;cells.difference_update(range(x,x+n))
    return {'KPI':len(cells)/T,'T':T,'F':len(cells),'stderr':result.stderr}

def main():
    rows=[]
    for p in known_files():
        a=screen([PRIOR/'final/solver'],p);b=screen([HERE/'proposal/solver'],p)
        rows.append({'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),'baseline':a,'proposal':b})
        if a['T']!=b['T']:print(p.stem,a['KPI'],b['KPI'],b['stderr'],flush=True)
    (HERE/'known-screen.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
