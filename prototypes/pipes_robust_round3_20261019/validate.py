"""Original official interactor, immutable hashes, explicit prior-result reuse."""
import concurrent.futures
import json
import sys
from common import HERE,ROOT,PRIOR,e,BF,known_files

def run(groups,names):
    strategies={'baseline':[str(PRIOR/'final/solver')],'proposal':[str(HERE/'proposal/solver')],
                'final':[str(HERE/'final/solver')],'plan-only':[str(HERE/'plan-only/solver')],'bestfit':BF}
    strategies.update(candidate=[str(HERE/'candidate/solver')],**{'plans-only':[str(HERE/'plans-only/solver')]})
    strategies['candidate-physical']=[str(HERE/'candidate-physical/solver')]
    sources={'known':known_files(),'fresh':sorted((HERE/'attacks').glob('*.in')),
             'holdout':sorted((HERE/'holdout').glob('*.in')),
             'counter':sorted((HERE/'counterattacks').glob('*.in')),
             'open15':[ROOT/f'data/pipes/open/{i}.in' for i in range(1,16)]}
    reuse={}
    for path in (PRIOR/'evaluations').rglob('record.json'):
        r=json.loads(path.read_text())
        if r.get('strategy')=='final' and r['status']=='ok':
            assert r['binary_sha256']==e.sha(PRIOR/'final/solver')
            reuse[r['test_sha256']]=r
    jobs=[(g,n,p) for g in groups for p in sources[g] for n in names]
    def execute(job):
        group,name,path=job;out=HERE/'evaluations'/group/name/path.stem
        digest=e.sha(strategies[name][0]);test_digest=e.sha(path);record_path=out/'record.json'
        if record_path.exists():
            r=json.loads(record_path.read_text());assert r['binary_sha256']==digest and r['test_sha256']==test_digest
        elif name=='baseline' and test_digest in reuse:
            r=dict(reuse[test_digest]);r['reused_previous_round_record']=True
        else:
            r=e.harness.run_case(strategies[name],ROOT/'tools/interactor',path,out,5,180)
        r.update(strategy=name,group=group,binary_sha256=digest)
        out.mkdir(parents=True,exist_ok=True);record_path.write_text(json.dumps(r,indent=2)+'\n')
        assert r['test_sha256']==test_digest and r['status']=='ok',r
        assert r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256,r
        assert r['judge_commands_seen_including_final_zero']==r['operation_count']+1
        if group=='open15' and name!='bestfit':
            assert r['trench_length_m']==r['minimum_trench_lower_bound_m'],r
            assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
        return r
    records=[]
    workers=1 if any(g in ['known','holdout'] for g in groups) else 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(execute,jobs):
            records.append(r);print(r['group'],r['strategy'],r['case'],round(r['kpi'],6),flush=True)
    data={'records':records,'official_interactor_sha256':e.sha(ROOT/'tools/interactor'),
          'harness_sha256':e.sha(ROOT/'tools/pipes_harness.py'),'platform_actions':0}
    (HERE/('official-'+'-'.join(groups)+'__'+'-'.join(names)+'.json')).write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':run(sys.argv[1].split(','),sys.argv[2].split(','))
