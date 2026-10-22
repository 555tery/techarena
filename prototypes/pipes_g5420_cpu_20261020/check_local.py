"""Native-host smoke tests only; does not estimate Windows/G5420 timing."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('harness',ROOT/'tools/pipes_harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    prior=ROOT/'prototypes/pipes_memory_robust_20261019'
    stress=[prior/'evaluation/sealed-final/f05-stress-200k-high-live-set.in',
            prior/'resource-stress/grow-after-warm-search.in',prior/'resource-stress/late-planner-allocation.in']
    jobs=[('cache32',ROOT/f'data/pipes/open/{i}.in',True) for i in range(1,16)]
    jobs += [(name,p,False) for name in ['cache32','cache128'] for p in stress]
    rows=[]
    for name,path,public in jobs:
        dest=HERE/'local-checks'/name/path.stem;dest.mkdir(parents=True,exist_ok=True)
        solver=HERE/name/'solver';record=dest/'record.json'
        if record.exists():
            r=json.loads(record.read_text());assert r['binary_sha256']==sha(solver) and r['test_sha256']==sha(path)
        else:
            r=h.run_case([str(solver)],ROOT/'tools/interactor',path,dest,5,180)
            r.update(binary_sha256=sha(solver),test_sha256=sha(path),profile=name,public=public)
            record.write_text(json.dumps(r,indent=2)+'\n')
        assert r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,r
        if public:assert r['trench_length_m']==r['minimum_trench_lower_bound_m'] and 'fallback=0' in r['candidate_stderr'],r
        rows.append(r);print(name,path.stem,round(r['kpi'],6),round(r['solver_cpu_total_s'],3),flush=True)
    summary={'target_hardware_run':False,'execution_host':'macOS arm64; not Windows/G5420',
       'purpose':'protocol, score and resource smoke on current host; not a hardware speed conversion',
       'records':rows,'max_local_CPU_s':max(r['solver_cpu_total_s'] for r in rows),'max_local_RSS_MiB':max(r['solver_peak_rss_mb'] for r in rows)}
    (HERE/'local-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
