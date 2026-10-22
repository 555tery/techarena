"""Single-worker paired rollouts, exact source hashes and separate post-freeze inputs."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PREV=ROOT/'prototypes/pipes_presync_20261020'
spec=importlib.util.spec_from_file_location('prior',PREV/'evaluate.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def files(group):
    if group=='known':return [(r['id'],Path(r['path'])) for r in json.loads((HERE/'known.json').read_text())['tests']]
    if group in ['open15','stress']:return p.files(group)
    if group=='diagnostic':
        folder=HERE/'diagnostics';m=json.loads((folder/'manifest.json').read_text());return [(r['name'],folder/r['filename']) for r in m['cases']]
    if group=='fresh':
        f=json.loads((HERE/'freeze.json').read_text());result=[]
        for item in f['fresh_sets']:
            assert sha(HERE/item['manifest'])==item['manifest_sha256']
            assert sha(HERE/item['generator'])==item['generator_sha256']
            folder=(HERE/item['manifest']).parent;m=json.loads((folder/'manifest.json').read_text())
            for r in m['cases']:
                path=folder/r['filename'];assert sha(path)==r['sha256'];result.append((item['prefix']+r['name'],path))
        assert len(result)==96;return result
    raise ValueError(group)
def baseline_cache():
    out=p.cached_baseline();binary=sha(p.g.BASE)
    for file in PREV.glob('*.json'):
        try:data=json.loads(file.read_text())
        except (ValueError,OSError):continue
        if not isinstance(data,dict):continue
        for r in data.get('records',[]):
            if r.get('strategy')=='baseline' and r.get('binary_sha256')==binary:out[r['test_sha256']]=r
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('group',choices=['known','open15','stress','fresh','diagnostic']);ap.add_argument('--candidate',required=True)
    ap.add_argument('--mode',choices=['screen','official'],default='screen');ap.add_argument('--names',default='baseline,candidate');ap.add_argument('--ids');ap.add_argument('--tag',default='');ap.add_argument('--affected',action='store_true')
    a=ap.parse_args();directory=HERE/a.candidate;build=json.loads((directory/'build.json').read_text())
    assert sha(directory/'solution.cpp')==build['source_sha256'] and sha(directory/'solver')==build['binary_sha256']
    if a.group=='fresh':
        f=json.loads((HERE/'freeze.json').read_text());assert f['candidate']==a.candidate and f['source_sha256']==build['source_sha256'] and f['binary_sha256']==build['binary_sha256']
    cases=files(a.group)
    if a.ids:cases=[(i,path) for i,path in cases if i in a.ids.split(',')]
    if a.affected:
        affected=set(json.loads((HERE/'known.json').read_text())['affected_ids']);cases=[(i,path) for i,path in cases if i in affected]
    cache=baseline_cache();commands={'baseline':[str(p.g.BASE)],'candidate':[str(directory/'solver')],'bestfit':p.g.p.e.BF}
    records=[]
    for ident,path in cases:
        for name in a.names.split(','):
            binary=sha(commands[name][0]);test=sha(path)
            dest=HERE/'measurements'/a.mode/a.group/(a.candidate if name=='candidate' else name)/(ident+('-'+a.tag if a.tag else ''));dest.mkdir(parents=True,exist_ok=True)
            record=dest/'record.json'
            if record.exists():r=json.loads(record.read_text());assert r['test_sha256']==test and r['binary_sha256']==binary
            else:
                if name=='baseline' and a.mode=='screen' and a.group=='known' and test in cache:r=dict(cache[test]);r['reused_baseline_record']=True
                elif a.mode=='screen':r=p.g.p.e.screen(commands[name],path)
                else:r=p.g.p.e.h.run_case(commands[name],ROOT/'tools/interactor',path,dest,5,180)
                r.update(id=ident,strategy=name,source_path=str(path),test_sha256=test,binary_sha256=binary);record.write_text(json.dumps(r,indent=2)+'\n')
            assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,(ident,name,r)
            if a.group=='open15' and name=='candidate':
                assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
                assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
            records.append(r);print(ident,name,round(r['kpi'],8),round(r['solver_cpu_total_s'],4),flush=True)
    pairs=[]
    for ident,path in cases:
        r={x['strategy']:x for x in records if x['id']==ident}
        if 'baseline' in r and 'candidate' in r:pairs.append({'id':ident,'baseline':r['baseline']['kpi'],'candidate':r['candidate']['kpi'],
            'baselineT':r['baseline']['trench_length_m'],'candidateT':r['candidate']['trench_length_m'],'delta':r['candidate']['kpi']-r['baseline']['kpi']})
    out={'records':records,'pairs':pairs,'candidate':a.candidate,'group':a.group,'mode':a.mode,'source_sha256':build['source_sha256'],
        'binary_sha256':build['binary_sha256'],'platform_actions':0,'host':'macOS arm64, one solver worker; Windows/G5420 unmeasured'}
    if pairs:
        ds=[r['delta'] for r in pairs];out.update(n=len(ds),wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),losses=sum(d<-1e-12 for d in ds),mean_delta=sum(ds)/len(ds),worst_delta=min(ds),best_delta=max(ds))
    out['maximum_cpu_s']=max(r['solver_cpu_total_s'] for r in records);out['maximum_rss_mib']=max(r['solver_peak_rss_mb'] for r in records)
    assert sha(directory/'solver')==build['binary_sha256'] and sha(directory/'solution.cpp')==build['source_sha256']
    suffix=('-affected' if a.affected else '')+('-'+a.tag if a.tag else '')
    (HERE/f'{a.mode}-{a.group}-{a.candidate}{suffix}.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['records','pairs']},indent=2),flush=True)
if __name__=='__main__':main()
