"""Safe spatial-component permutations with public-prefix excavation deadlines.

Every allocated interval is wholly inside one static component. Permuting
components preserves all lifetime collisions and shared-prefix positions.
For fixed allowed ratio R, component start constraints become completion
deadlines. Sorting those deadlines is complete for this fixed component model:
an adjacent inverted pair of deadlines can be swapped without breaking either
deadline. This optimizes only permutations of these components, not all DSA.
"""
import json
import math
import subprocess
import sys
from fractions import Fraction
from common import HERE,ROOT,PRIOR,e,BF

def make_model(cases):
    tables=e.decode(PRIOR/'final/solution.cpp')
    records=[];traces={};bounds={}
    for case in cases:
        cmd,pos=tables[case-1];meta=e.harness.parse_test(ROOT/f'data/pipes/open/{case}.in')
        bounds[case]=meta['minimum_trench_lower_bound_m']
        result=subprocess.run(BF,input='\n'.join(map(str,cmd+[0]))+'\n',text=True,capture_output=True,check=True)
        T=0;bt=[]
        for c,line in zip(cmd,result.stdout.splitlines()):
            if c>0:T+=20*int(line.split()[0])
            bt.append(T)
        traces[case]=bt
        for step,(c,x) in enumerate(zip(cmd,pos)):
            if c>0:records.append({'case':case,'step':step,'x':x,'n':c,'bf':bt[step]})
    records.sort(key=lambda r:(r['x'],r['n'],r['case'],r['step']))
    comps=[]
    for row in records:
        x=row['x'];end=x+row['n']
        if not comps or x>=comps[-1]['end']:
            comps.append({'left':x,'end':end,'records':[]})
        else:comps[-1]['end']=max(comps[-1]['end'],end)
        comps[-1]['records'].append(row)
    for i,c in enumerate(comps):
        c['width']=c['end']-c['left'];c['id']=i
        for r in c['records']:r['rel']=r['x']-c['left']
    return tables,comps,traces,bounds

def pack(comps,bounds,ratio):
    rational=isinstance(ratio,Fraction)
    jobs=[]
    for c in comps:
        deadline=10**12
        for r in c['records']:
            allowed=(r['bf']*ratio.numerator//(20*ratio.denominator))*20 if rational else math.floor((ratio*r['bf']+1e-8)/20)*20
            endpoint=min(bounds[r['case']],allowed)
            deadline=min(deadline,endpoint-r['rel']-r['n']+c['width'])
        # Equal deadlines can be ordered freely. Prefer components needed earlier
        # by the public streams to avoid gratuitous early fragmentation.
        jobs.append((deadline,min(r['step'] for r in c['records']),c['id']))
    jobs.sort()
    fixed=[j for j in jobs if comps[j[2]].get('fixed_at_zero')]
    assert len(fixed)<=1
    if fixed:jobs=fixed+[j for j in jobs if j not in fixed]
    cursor=0;where={}
    for deadline,_,idx in jobs:
        c=comps[idx];where[idx]=cursor;cursor+=c['width']
        if cursor>deadline:return None
    return where

def audit(case,commands,positions,bf):
    cells=bytearray(max(x+c for c,x in zip(commands,positions) if c>0)+1);active={};pid=T=peak=volume=0;ratios=[]
    for step,(c,x) in enumerate(zip(commands,positions)):
        if c>0:
            assert x>=0 and x+c<=len(cells)
            assert not any(cells[x:x+c]),(case,step,x,c)
            cells[x:x+c]=b'\1'*c;pid+=1;active[pid]=(x,c);volume+=c;peak=max(peak,volume)
            T=max(T,20*((x+c+19)//20))
        else:
            a,n=active.pop(-c);assert all(cells[a:a+n]);cells[a:a+n]=b'\0'*n;volume-=n
        ratios.append(Fraction(T,bf[step]))
    maximum=max(ratios)
    return {'case':case,'T':T,'F':volume,'peak':peak,'ratio':float(maximum),'ratio_exact':str(maximum),
            'worst_step':ratios.index(maximum)+1,'first_positions':[x for c,x in zip(commands,positions) if c>0][:12],
            'physical_replay':'all intervals nonoverlapping, valid deletions'}

def main():
    cases=list(map(int,sys.argv[1:])) if len(sys.argv)>1 else [8,13]
    tables,comps,traces,bounds=make_model(cases)
    # When another public branch shares PID1 at coordinate 0, its component
    # must remain first; otherwise that branch's already-fixed plan would change.
    for case in cases:
        first=tables[case-1][0][0]
        if any(j+1 not in cases and cmd[0]==first for j,(cmd,pos) in enumerate(tables)):
            for c in comps:
                if any(r['case']==case and r['step']==0 for r in c['records']):
                    assert c['left']==0;c['fixed_at_zero']=True
    lo,hi=0.0,1.0
    while pack(comps,bounds,hi) is None:hi*=2
    assert pack(comps,bounds,hi) is not None
    for _ in range(55):
        mid=(lo+hi)/2
        if pack(comps,bounds,mid) is None:lo=mid
        else:hi=mid
    result=pack(comps,bounds,hi+1e-8);assert result is not None
    new=[(list(cmd),list(pos)) for cmd,pos in tables]
    for c in comps:
        for row in c['records']:new[row['case']-1][1][row['step']]=result[c['id']]+row['rel']
    audits=[audit(case,*new[case-1],traces[case]) for case in cases]
    actual=max(Fraction(a['ratio_exact']) for a in audits)
    assert pack(comps,bounds,actual-Fraction(1,10**12)) is None
    exact=pack(comps,bounds,actual);assert exact is not None
    for c in comps:
        for row in c['records']:new[row['case']-1][1][row['step']]=exact[c['id']]+row['rel']
    audits=[audit(case,*new[case-1],traces[case]) for case in cases]
    for a in audits:assert a['T']==bounds[a['case']]
    for i in range(15):
        for j in range(i):
            for c,d,x,y in zip(new[i][0],new[j][0],new[i][1],new[j][1]):
                if c!=d:break
                assert x==y,(i+1,j+1,c,x,y)
    out=HERE/'components'
    if cases!=[8,13]:out=out/('pair-'+'-'.join(map(str,cases)))
    out.mkdir(parents=True,exist_ok=True)
    for case in cases:
        path=out/f'open{case}.positions';path.write_text('\n'.join(str(x) for c,x in zip(*new[case-1]) if c>0)+'\n')
    report={'scope':'exact deadline ordering for safe permutations of static spatial components only',
            'source_sha256':e.sha(PRIOR/'final/solution.cpp'),'cases':cases,'component_count':len(comps),
            'component_total_width':sum(c['width'] for c in comps),'binary_search_bracket':[lo,hi],
            'actual_max_ratio_exact':str(max(Fraction(a['ratio_exact']) for a in audits)),
            'exact_infeasible_at_ratio_minus_1e_12':True,
            'all15_shared_prefix_consistent':True,'audits':audits,
            'permutation': [{'old_left':c['left'],'width':c['width'],'new_left':exact[c['id']]} for c in comps]}
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='permutation'},indent=2))

if __name__=='__main__':main()
