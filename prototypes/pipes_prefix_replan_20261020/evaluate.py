"""Local paired rollouts. Fresh inputs are opened only after source freeze."""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('memory_eval',ROOT/'prototypes/pipes_memory_robust_20261019/evaluate.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
BASE=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solver'
CAUSAL=ROOT/'prototypes/pipes_memory_robust_20261019/causal-final/solver'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def tests(group):
    if group in ['regression','open15']:return e.tests(group)
    if group=='prior-confirmation':
        directory=ROOT/'prototypes/pipes_memory_robust_20261019/evaluation/confirmation'
    elif group=='round1-regression': directory=HERE/'evaluation/fresh'
    elif group in ['fresh','fresh-conservative','remaining']: directory=HERE/'evaluation'/group
    elif group=='stress':
        p=ROOT/'prototypes/pipes_memory_robust_20261019'
        return [(f.stem,f) for f in [p/'evaluation/sealed-final/f05-stress-200k-high-live-set.in',p/'resource-stress/grow-after-warm-search.in',p/'resource-stress/late-planner-allocation.in']]
    else:raise ValueError(group)
    m=json.loads((directory/'manifest.json').read_text())
    return [(r['id'],directory/r['file']) for r in m['tests']]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('group');ap.add_argument('--candidate',required=True)
    ap.add_argument('--mode',choices=['screen','official'],default='screen');ap.add_argument('--names',default='baseline,candidate')
    ap.add_argument('--ids');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    solver=HERE/a.candidate/'solver';build=json.loads((HERE/a.candidate/'build.json').read_text())
    assert build['source_sha256']==sha(HERE/a.candidate/'solution.cpp') and build['binary_sha256']==sha(solver)
    if a.group.startswith('fresh'):
        frozen=json.loads((HERE/('freeze-conservative.json' if a.group=='fresh-conservative' else 'freeze.json')).read_text())
        assert frozen['source_sha256']==build['source_sha256'] and frozen['binary_sha256']==sha(solver)
    files=tests(a.group)
    if a.ids: files=[(i,p) for i,p in files if i in a.ids.split(',')]
    solvers={'baseline':[str(BASE)],'candidate':[str(solver)],'bestfit':e.BF,'causal':[str(CAUSAL)]}
    jobs=[(i,p,n) for i,p in files for n in a.names.split(',')]
    def run(job):
        ident,path,name=job;binary=sha(solvers[name][0]);test=sha(path)
        dest=HERE/'measurements'/a.mode/a.group/(a.candidate if name=='candidate' else name)/ident
        dest.mkdir(parents=True,exist_ok=True);record=dest/'record.json'
        if record.exists():
            r=json.loads(record.read_text());assert r['test_sha256']==test and r['binary_sha256']==binary
        else:
            if a.mode=='screen':r=e.screen(solvers[name],path)
            else:r=e.h.run_case(solvers[name],ROOT/'tools/interactor',path,dest,5,180)
            r.update(id=ident,strategy=name,source_path=str(path),test_sha256=test,binary_sha256=binary)
            record.write_text(json.dumps(r,indent=2)+'\n')
        assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,(ident,name,r)
        if a.group=='open15' and name=='candidate':
            assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
            assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
        return r
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(run,jobs):
            rows.append(r)
            print(r['id'],r['strategy'],round(r['kpi'],6),round(r['solver_cpu_total_s'],3),flush=True)
    pairs=[]
    for ident,path in files:
        records={r['strategy']:r for r in rows if r['id']==ident}
        if 'baseline' in records and 'candidate' in records:
            pairs.append({'id':ident,'baseline':records['baseline']['kpi'],'candidate':records['candidate']['kpi'],
                          'delta':records['candidate']['kpi']-records['baseline']['kpi']})
    meta={'records':rows,'pairs':pairs,'group':a.group,'candidate':a.candidate,'source_sha256':build['source_sha256'],
          'platform_actions':0,'host':'macOS arm64; not Windows/G5420','official':a.mode=='official'}
    if pairs:
        d=[p['delta'] for p in pairs]
        meta.update(wins=sum(x>1e-12 for x in d),ties=sum(abs(x)<=1e-12 for x in d),losses=sum(x<-1e-12 for x in d),
                    mean_delta=sum(d)/len(d),worst_delta=min(d),best_delta=max(d))
    (HERE/f'{a.mode}-{a.group}-{a.candidate}.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({k:v for k,v in meta.items() if k not in ['records','pairs']},indent=2),flush=True)

if __name__=='__main__':main()
