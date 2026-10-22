"""Paired complete rollouts; unopened inputs require a frozen executable."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];GHOST=ROOT/'prototypes/pipes_ghost_handoff_20261020'
spec=importlib.util.spec_from_file_location('ghost_eval',GHOST/'evaluate.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def files(group):
    if group=='known':return [(r['id'],Path(r['path'])) for r in json.loads((HERE/'known.json').read_text())['tests']]
    if group in ['open15','stress']:return g.tests(group)
    if group=='diagnostic':
        folder=HERE/'diagnostics';m=json.loads((folder/'manifest.json').read_text())
        return [(r['id'],folder/r['file']) for r in m['tests']]
    if group=='fresh':
        folder=HERE/'evaluation/fresh';m=json.loads((folder/'manifest.json').read_text());rows=m.get('streams',m.get('tests',m.get('cases')))
        assert len(rows)==64
        result=[]
        for r in rows:
            path=folder/r.get('input_file',r.get('file',r.get('filename')))
            assert sha(path)==r['sha256']
            result.append((r.get('id',r.get('name')),path))
        return result
    raise ValueError(group)
def cached_baseline():
    cache=g.parent_cache();binary=sha(g.BASE)
    for file in GHOST.glob('*.json'):
        data=json.loads(file.read_text())
        for row in data.get('records',[]):
            if row.get('strategy')=='baseline' and row.get('binary_sha256')==binary:cache[row['test_sha256']]=dict(row)
    return cache
def main():
    ap=argparse.ArgumentParser();ap.add_argument('group',choices=['known','open15','stress','fresh','diagnostic']);ap.add_argument('--candidate',required=True)
    ap.add_argument('--mode',choices=['screen','official'],default='screen');ap.add_argument('--names',default='baseline,candidate');ap.add_argument('--ids');ap.add_argument('--tag',default='')
    a=ap.parse_args();directory=HERE/a.candidate;build=json.loads((directory/'build.json').read_text())
    assert sha(directory/'solution.cpp')==build['source_sha256'] and sha(directory/'solver')==build['binary_sha256']
    if a.group=='fresh':
        freeze=json.loads((HERE/'freeze.json').read_text());assert freeze['candidate']==a.candidate
        assert freeze['source_sha256']==build['source_sha256'] and freeze['binary_sha256']==build['binary_sha256']
        assert sha(HERE/'evaluation/fresh/manifest.json')==freeze['fresh_manifest_sha256']
        assert sha(HERE/'evaluation/generate_fresh.py')==freeze['fresh_generator_sha256']
    cases=files(a.group)
    if a.ids:cases=[(i,p) for i,p in cases if i in a.ids.split(',')]
    cache=cached_baseline();commands={'baseline':[str(g.BASE)],'candidate':[str(directory/'solver')],
      'previous':[str(GHOST/'coupled-buffer40/solver')],'bestfit':g.p.e.BF}
    rows=[]
    for ident,path in cases:
        for name in a.names.split(','):
            binary=sha(commands[name][0]);test=sha(path)
            dest=HERE/'measurements'/a.mode/a.group/(a.candidate if name=='candidate' else name)/ident;dest.mkdir(parents=True,exist_ok=True);record=dest/'record.json'
            if record.exists():
                r=json.loads(record.read_text());assert r['test_sha256']==test and r['binary_sha256']==binary
            else:
                if name=='baseline' and a.mode=='screen' and a.group=='known' and test in cache:
                    r=dict(cache[test]);r['reused_baseline_record']=True
                elif a.mode=='screen':r=g.p.e.screen(commands[name],path)
                else:r=g.p.e.h.run_case(commands[name],ROOT/'tools/interactor',path,dest,5,180)
                r.update(id=ident,strategy=name,source_path=str(path),test_sha256=test,binary_sha256=binary)
                record.write_text(json.dumps(r,indent=2)+'\n')
            assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,(ident,name,r)
            if a.group=='open15' and name=='candidate':
                assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
                assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
            rows.append(r);print(ident,name,round(r['kpi'],8),round(r['solver_cpu_total_s'],4),flush=True)
    pairs=[]
    for ident,path in cases:
        r={x['strategy']:x for x in rows if x['id']==ident}
        if 'candidate' in r and 'baseline' in r:pairs.append({'id':ident,'baseline':r['baseline']['kpi'],'candidate':r['candidate']['kpi'],
          'baselineT':r['baseline']['trench_length_m'],'candidateT':r['candidate']['trench_length_m'],'delta':r['candidate']['kpi']-r['baseline']['kpi']})
    out={'records':rows,'pairs':pairs,'candidate':a.candidate,'group':a.group,'mode':a.mode,'source_sha256':build['source_sha256'],
      'binary_sha256':build['binary_sha256'],'platform_actions':0,'host':'macOS arm64, single solver worker; Windows/G5420 unmeasured'}
    if pairs:
        ds=[p['delta'] for p in pairs];out.update(wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),losses=sum(d<-1e-12 for d in ds),
          mean_delta=sum(ds)/len(ds),worst_delta=min(ds),best_delta=max(ds))
    out['maximum_cpu_s']=max(r['solver_cpu_total_s'] for r in rows);out['maximum_rss_mib']=max(r['solver_peak_rss_mb'] for r in rows)
    assert sha(directory/'solver')==build['binary_sha256'] and sha(directory/'solution.cpp')==build['source_sha256']
    filename=HERE/f'{a.mode}-{a.group}-{a.candidate}{"-"+a.tag if a.tag else ""}.json';filename.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['records','pairs']},indent=2),flush=True)
if __name__=='__main__':main()
