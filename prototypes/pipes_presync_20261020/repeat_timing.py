"""Confirm a fresh loss on an unchanged physical branch; never tune sources."""
import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('paired',HERE/'evaluate.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def main():
    freeze=json.loads((HERE/'freeze.json').read_text());name=freeze['candidate'];assert e.sha(HERE/name/'solver')==freeze['binary_sha256']
    path=dict(e.files('fresh'))['public_07'];rows=[]
    for repeat in range(1,4):
        for strategy in ['baseline','candidate']:
            binary=e.g.BASE if strategy=='baseline' else HERE/name/'solver';dest=HERE/'measurements/official/timing-repeats'/f'r{repeat}'/strategy;dest.mkdir(parents=True,exist_ok=True)
            file=dest/'record.json'
            if file.exists():r=json.loads(file.read_text())
            else:
                r=e.g.p.e.h.run_case([str(binary)],e.ROOT/'tools/interactor',path,dest,5,180)
                r.update(id='public_07',strategy=strategy,repeat=repeat,test_sha256=e.sha(path),binary_sha256=e.sha(binary));file.write_text(json.dumps(r,indent=2)+'\n')
            assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256
            if strategy=='candidate':assert 'uncoupled_steps=0' in r['candidate_stderr'] and 'mirror_followed=0' in r['candidate_stderr']
            rows.append(r);print(repeat,strategy,r['trench_length_m'],round(r['solver_cpu_total_s'],6),flush=True)
    assert e.sha(HERE/name/'solution.cpp')==freeze['source_sha256']
    result={'records':rows,'source_sha256':freeze['source_sha256'],'purpose':'Unchanged branch: zero uncoupled steps and zero mirror placements. Repeats diagnose CPU-sensitive internal reference behavior; first fresh64 results remain unchanged.','pairs':[{'repeat':i,'baselineT':next(r['trench_length_m'] for r in rows if r['repeat']==i and r['strategy']=='baseline'),'candidateT':next(r['trench_length_m'] for r in rows if r['repeat']==i and r['strategy']=='candidate')} for i in range(1,4)]}
    (HERE/'timing-public07.json').write_text(json.dumps(result,indent=2)+'\n');print(result['pairs'],flush=True)
if __name__=='__main__':main()
