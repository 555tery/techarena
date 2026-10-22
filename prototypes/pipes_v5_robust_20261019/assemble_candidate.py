"""Freeze two reviewable candidates; public ceiling is a mandatory gate."""
import datetime
import json
import shutil
import sys
from experiment import HERE, ROOT, BASE, build, decode, harness, sha

def main():
    v3='--v3' in sys.argv
    v2='--v2' in sys.argv or v3
    original=decode(BASE/'target/solution.cpp')
    tables=json.loads((HERE/'compact-tables.json').read_text())
    # The BF-close Open2 plan is rejected: it creates a new .5-vs-1 grave.
    tables[1]=original[1]
    for case in [10,14]:
        p=HERE/'replan/geometry_open10_prefix_best_positions.txt' if v2 and case==10 else HERE/f'replan/geometry_open{case:02d}_positions.txt'
        if v3 and case==14:p=HERE/'replan/geometry_open14_cumulative_best_positions.txt'
        offsets=iter(map(int,p.read_text().split()));cmds=tables[case-1][0]
        tables[case-1]=(cmds,[next(offsets) if c>0 else None for c in cmds])
        assert next(offsets,None) is None
    for i in range(15):
        for j in range(i):
            for c,d,p,q in zip(tables[i][0],tables[j][0],tables[i][1],tables[j][1]):
                if c!=d:break
                assert p==q,(i+1,j+1,c,p,q)
    audit=[]
    for case,(cmds,pos) in enumerate(tables,1):
        cells=set();pipes={};pid=T=volume=peak=0
        for c,x in zip(cmds,pos):
            if c>0:
                assert x>=0 and x+c<=100000000
                occupied=set(range(x,x+c));assert not cells&occupied,(case,pid+1)
                cells.update(occupied);pid+=1;pipes[pid]=(x,c)
                T=max(T,20*((x+c+19)//20));volume+=c;peak=max(peak,volume)
            else:
                a,b=pipes.pop(-c);cells.difference_update(range(a,a+b));volume-=b
        meta=harness.parse_test(ROOT/f'data/pipes/open/{case}.in')
        assert T==meta['minimum_trench_lower_bound_m'],(case,T,meta)
        assert volume==len(cells)==meta['final_occupied_length_m']
        changed=sum(p!=q for p,q,c in zip(pos,original[case-1][1],cmds) if c>0)
        audit.append({'case':case,'T':T,'F':volume,'peak':peak,'changed_allocations':changed})
    suffix='-v3' if v3 else '-v2' if v2 else ''
    (HERE/f'candidate{suffix}-plan-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (HERE/f'candidate{suffix}-tables.json').write_text(json.dumps(tables)+'\n')
    selections=[('candidate'+suffix,'bestfit')] if v2 else [('candidate','bestfit'),('candidate-firstfit','firstfit-fast')]
    for name,policy in selections:
        binary=build('replanned'+suffix+'-'+policy,policy,tables)
        dest=HERE/name;dest.mkdir(exist_ok=True)
        for filename in ['solver','solution.cpp','build.json']:shutil.copy2(binary.parent/filename,dest/filename)
        meta=json.loads((dest/'build.json').read_text())
        meta.update(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    role='table-only primary candidate' if policy=='bestfit' else 'fallback First-Fit ablation',
                    old_Open2_table_preserved=True,table_cases_changed=[1,3,4,6,7,10,14],
                    selection=('v3: extend Open10 BF prefix to entire initial positive phase and Open14 to sampled exact prefix8192; optimize whole-stream prefix excavation ratio; all suites diagnostic' if v3 else 'v2: extend Open10 BF prefix to entire initial positive phase after counterattack; other tables unchanged; all suites now diagnostic' if v2 else '9 prior graves + public-only packing criterion; new attack results and neutral validation not used for selection'),
                    Open10_pinned_prefix_commands=5383 if v2 else 3,
                    Open14_pinned_prefix_commands=8192 if v3 else 8)
        (dest/'build.json').write_text(json.dumps(meta,indent=2)+'\n')
        print(name,meta['binary_sha256'],flush=True)

if __name__=='__main__':main()
