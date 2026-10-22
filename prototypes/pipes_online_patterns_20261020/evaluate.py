"""One-worker paired whole-stream evaluation with explicit split provenance."""
import argparse, importlib.util, json, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'prototypes/pipes_online_core_20261020'
PREV=ROOT/'prototypes/pipes_closed_ready_20261020'
spec=importlib.util.spec_from_file_location('previous_evaluator',PREV/'evaluate.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
h,screen,sha=prior.h,prior.screen,prior.sha

def from_manifest(folder):
    m=json.loads((folder/'manifest.json').read_text())
    return [dict(c,path=folder/c['file']) for c in m['cases']]

def cases(group):
    if group=='open15':return prior.cases(group)
    if group=='dev':
        return [dict(c,id=tag+'-'+g+'-'+c['id'],round=tag,split=g) for tag,folder in [('core',OLD),('ready',PREV)] for g in ['calibration','final'] for c in from_manifest(folder/'evaluation'/g)]
    return from_manifest(HERE/'evaluation'/group)

def source(name):
    p=HERE/'candidates'/name/'solution.cpp'
    if p.exists():return p
    return HERE/'core_candidates'/name/'solution.cpp'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('group',choices=['dev','open15','calibration','final','stress'])
    ap.add_argument('--names',required=True);ap.add_argument('--mode',choices=['screen','official'],default='screen');a=ap.parse_args()
    if a.group=='final':
        frozen=json.loads((HERE/'selection-freeze.json').read_text())
        assert sha(HERE/'evaluation/final/manifest.json')==frozen['manifests']['final']
        for n in a.names.split(','):
            assert sha(source(n))==frozen['sources'][n]
            assert sha(source(n).with_name('solver'))==frozen['binaries'][n]
    rows=[]
    for c in cases(a.group):
        if 'sha256' in c:assert sha(c['path'])==c['sha256']
        for name in a.names.split(','):
            src=source(name);binary=src.with_name('solver');dest=HERE/'measurements'/a.mode/a.group/name/c['id'];dest.mkdir(parents=True,exist_ok=True)
            record=dest/'record.json'
            if record.exists():
                r=json.loads(record.read_text());assert r['binary_sha256']==sha(binary) and r['test_sha256']==sha(c['path'])
            else:
                started=time.time()
                try:r=screen(binary,c['path']) if a.mode=='screen' else h.run_case([str(binary)],ROOT/'tools/interactor',c['path'],dest,5,240)
                except Exception as exc:r=dict(status='error',detail=repr(exc),kpi=None,solver_cpu_total_s=None,solver_peak_rss_mb=None)
                r.update(id=c['id'],strategy=name,family=c['family'],stratum=c['stratum'],source_sha256=sha(src),binary_sha256=sha(binary),test_sha256=sha(c['path']),input_path=str(c['path']),mode=a.mode,started_at_unix=started)
                r['resources_ok']=r['solver_cpu_total_s'] is not None and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb'] is not None and r['solver_peak_rss_mb']<256
                record.write_text(json.dumps(r,indent=2)+'\n')
            if a.mode=='official':
                p=HERE/'measurements/screen'/a.group/name/c['id']/'record.json'
                if p.exists():
                    b=json.loads(p.read_text());assert b['trench_length_m']==r['trench_length_m']
            if r['status']!='ok':print('FAIL',name,c['id'],r.get('detail'),flush=True)
            rows.append(r)
    (HERE/f'{a.mode}-{a.group}-{a.names.replace(",","-")}.json').write_text(json.dumps(dict(records=rows,workers=1,platform_actions=0),indent=2)+'\n')
    print(json.dumps(dict(group=a.group,n=len(rows),invalid=sum(r['status']!='ok' for r in rows),resources_failed=sum(not r['resources_ok'] for r in rows))),flush=True)

if __name__=='__main__':main()
