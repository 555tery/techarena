"""Recompute component deadlines after individual lifetime obstructions move."""
import argparse,json,sys,time
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'prototypes/pipes_robust_round3_20261019'))
import component_deadlines as d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--cases',default='11,15');ap.add_argument('--name',default='permuted11');a=ap.parse_args()
    dest=HERE/'repairs'/a.name;dest.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    cases=list(map(int,a.cases.split(',')));tables=d.e.decode(a.source)
    records=[];traces={};bounds={}
    import subprocess
    for case in cases:
        commands,positions=tables[case-1];bounds[case]=d.e.harness.parse_test(ROOT/f'data/pipes/open/{case}.in')['minimum_trench_lower_bound_m']
        lines=subprocess.run(d.BF,input='\n'.join(map(str,commands+[0]))+'\n',capture_output=True,text=True,check=True).stdout.splitlines()
        bf=T=0;traces[case]=[]
        for step,(c,x,line) in enumerate(zip(commands,positions,lines)):
            if c>0:
                bf+=20*int(line.split()[0]);T=max(T,20*((x+c+19)//20))
                records.append({'case':case,'step':step,'x':x,'n':c,'bf':bf,'cap':T})
            traces[case].append(bf)
    records.sort(key=lambda r:(r['x'],r['n'],r['case'],r['step']));comps=[]
    for row in records:
        x=row['x'];end=x+row['n']
        if not comps or x>=comps[-1]['end']:comps.append({'left':x,'end':end,'records':[]})
        else:comps[-1]['end']=max(comps[-1]['end'],end)
        comps[-1]['records'].append(row)
    for i,c in enumerate(comps):
        c['width']=c['end']-c['left'];c['id']=i
        for r in c['records']:r['rel']=r['x']-c['left']
    for case in cases:
        first=tables[case-1][0][0]
        if any(ci+1 not in cases and cmd[0]==first for ci,(cmd,pos) in enumerate(tables)):
            for c in comps:
                if any(r['case']==case and r['step']==0 for r in c['records']):c['fixed_at_zero']=True
    def pack(ratio):
        jobs=[]
        for c in comps:
            deadline=10**12
            for r in c['records']:
                endpoint=min(bounds[r['case']],r['cap'],int((ratio*r['bf']+1e-8)//20)*20)
                deadline=min(deadline,endpoint-r['rel']-r['n']+c['width'])
            jobs.append((deadline,min(r['step'] for r in c['records']),c['id']))
        jobs.sort();fixed=[j for j in jobs if comps[j[2]].get('fixed_at_zero')]
        jobs=fixed+[j for j in jobs if j not in fixed] if fixed else jobs
        cursor=0;where={}
        for deadline,_,i in jobs:
            where[i]=cursor;cursor+=comps[i]['width']
            if cursor>deadline:return None
        return where
    lo=0.;hi=1.
    while pack(hi) is None:
        hi*=2
        if hi>1024:raise RuntimeError('no deadline ordering within old prefix caps')
    for _ in range(32):
        mid=(lo+hi)/2
        if pack(mid) is None:lo=mid
        else:hi=mid
    where=pack(hi+1e-8);assert where is not None
    new=[(list(c),list(p)) for c,p in tables]
    for c in comps:
        for r in c['records']:new[r['case']-1][1][r['step']]=where[c['id']]+r['rel']
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text());changes={}
    for ci in range(15):
        for c,bid,x,old in zip(new[ci][0],j['cases'][ci]['block_ids'],new[ci][1],tables[ci][1]):
            if c>0 and x!=old:
                assert bid not in changes or changes[bid]==x;changes[bid]=x
    audits=[d.audit(c,*new[c-1],traces[c]) for c in cases]
    (dest/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
    result={'success':True,'source':str(a.source),'cases':cases,'component_count':len(comps),'changes':len(changes),
            'max_ratio':max(x['ratio'] for x in audits),'audits':audits,'elapsed':time.monotonic()-start,
            'scope':'safe static component permutation after lifetime moves, prefix T never above input source'}
    (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
