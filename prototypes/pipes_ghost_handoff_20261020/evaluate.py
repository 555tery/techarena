"""Paired full-stream screen and official frozen confirmation."""
import argparse,concurrent.futures,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRIOR=ROOT/'prototypes/pipes_prefix_replan_20261020'
spec=importlib.util.spec_from_file_location('prior_eval',PRIOR/'evaluate.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
BASE=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solver'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tests(group):
    if group in ['open15','stress']:return p.tests(group)
    if group=='known':
        result=[];seen=set()
        for prefix,g in [('known81','regression'),('prior24','prior-confirmation'),('round1','fresh'),('round2','fresh-conservative'),('remaining','remaining')]:
            for ident,path in p.tests(g):
                h=sha(path)
                if h not in seen:result.append((prefix+'-'+ident,path));seen.add(h)
        return result
    if group in ['fresh','early-diagnostics']:
        folder=HERE/'evaluation'/group;m=json.loads((folder/'manifest.json').read_text())
        return [(r['id'],folder/r['input_file']) for r in m['streams']]
    raise ValueError(group)
def parent_cache():
    cache={};binary=sha(BASE)
    for f in ['screen-regression-instant.json','screen-prior-confirmation-instant.json','official-fresh-final.json','official-fresh-conservative-conservative.json','official-remaining-final.json']:
        r=json.loads((PRIOR/f).read_text())
        for row in r['records']:
            if row['strategy']=='baseline' and row['binary_sha256']==binary:cache[row['test_sha256']]=row
    return cache
def main():
    ap=argparse.ArgumentParser();ap.add_argument('group');ap.add_argument('--candidate',required=True)
    ap.add_argument('--mode',choices=['screen','official'],default='screen');ap.add_argument('--names',default='baseline,candidate')
    ap.add_argument('--ids');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    solver=HERE/a.candidate/'solver';build=json.loads((HERE/a.candidate/'build.json').read_text())
    assert sha(solver)==build['binary_sha256'] and sha(HERE/a.candidate/'solution.cpp')==build['source_sha256']
    if a.group=='fresh':
        f=json.loads((HERE/'freeze.json').read_text());assert f['source_sha256']==build['source_sha256'] and f['binary_sha256']==sha(solver)
    files=tests(a.group)
    if a.ids:files=[(i,path) for i,path in files if i in a.ids.split(',')]
    solvers={'baseline':[str(BASE)],'candidate':[str(solver)],'bestfit':p.e.BF}
    cache=parent_cache();jobs=[(i,path,n) for i,path in files for n in a.names.split(',')]
    def run(job):
        ident,path,name=job;binary=sha(solvers[name][0]);h=sha(path)
        dest=HERE/'measurements'/a.mode/a.group/(a.candidate if name=='candidate' else name)/ident
        dest.mkdir(parents=True,exist_ok=True);record=dest/'record.json'
        if record.exists():
            r=json.loads(record.read_text());assert r['test_sha256']==h and r['binary_sha256']==binary
        else:
            if name=='baseline' and a.mode=='screen' and h in cache:
                r=dict(cache[h]);r['reused_original_validation']=r['validation'] if 'validation' in r else 'official interactive'
            elif a.mode=='screen':r=p.e.screen(solvers[name],path)
            else:r=p.e.h.run_case(solvers[name],ROOT/'tools/interactor',path,dest,5,180)
            r.update(id=ident,strategy=name,source_path=str(path),test_sha256=h,binary_sha256=binary)
            record.write_text(json.dumps(r,indent=2)+'\n')
        assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,(ident,name,r)
        if a.group=='open15' and name=='candidate':
            assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
            assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
        return r
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(run,jobs):
            rows.append(r);print(r['id'],r['strategy'],round(r['kpi'],7),round(r['solver_cpu_total_s'],3),flush=True)
    pairs=[]
    for ident,path in files:
        records={r['strategy']:r for r in rows if r['id']==ident}
        if 'baseline' in records and 'candidate' in records:
            pairs.append({'id':ident,'baseline':records['baseline']['kpi'],'candidate':records['candidate']['kpi'],
                          'delta':records['candidate']['kpi']-records['baseline']['kpi']})
    r={'records':rows,'pairs':pairs,'group':a.group,'candidate':a.candidate,'source_sha256':build['source_sha256'],
       'binary_sha256':build['binary_sha256'],'platform_actions':0,'host':'macOS arm64; not Windows/G5420'}
    if pairs:
        ds=[x['delta'] for x in pairs];r.update(wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),
          losses=sum(d<-1e-12 for d in ds),mean_delta=sum(ds)/len(ds),worst_delta=min(ds),best_delta=max(ds))
    (HERE/f'{a.mode}-{a.group}-{a.candidate}.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['records','pairs']},indent=2),flush=True)
if __name__=='__main__':main()
