"""Paired original-official-interactor checks; immutable binary/input hashes."""
import concurrent.futures
import datetime
import json
import sys
from build_online_fallback import HERE,ROOT,PREV,e

BF=[str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')]

def old_files():
    return sorted((PREV/'new_attacks').glob('*.in'))+sorted((PREV/'counterattacks').glob('*.in'))+sorted((ROOT/'prototypes/pipes_v5_graves_20261019/suite').glob('*.in'))

def run(groups,which):
    strategies={'baseline':[str(PREV/'candidate-v3/solver')],'online-fallback':[str(HERE/'online-fallback/solver')],
                'budgeted':[str(HERE/'budgeted/solver')],
                'budgeted-inclusive':[str(HERE/'budgeted-inclusive/solver')],
                'final':[str(HERE/'final/solver')],'final-plan':[str(HERE/'final-plan/solver')],
                'replanned':[str(HERE/'replanned/solver')],'combined':[str(HERE/'combined/solver')],'bestfit':BF}
    files={'known':old_files(),'neutral':sorted((HERE/'neutral').glob('*.in')),
           'holdout':sorted((HERE/'holdout').glob('*.in')),
           'new':sorted((HERE/'attacks').glob('*.in')),
           'open15':[ROOT/f'data/pipes/open/{i}.in' for i in range(1,16)],
           'safety':sorted((HERE/'safety').glob('*.in')),
           'counter':sorted((HERE/'counterattacks').glob('*.in'))}
    jobs=[(g,s,p) for g in groups for p in files[g] for s in which]
    def execute(job):
        group,strategy,path=job
        out=HERE/'evaluations'/group/strategy/path.stem
        digest=e.sha(strategies[strategy][0]);input_sha=e.sha(path)
        record_path=out/'record.json'
        if record_path.exists() and json.loads(record_path.read_text())['status']!='ok':
            # Preserve the interrupted attempt. Both unchanged baseline and candidate
            # were externally interrupted; serial unchanged-baseline retry succeeded.
            out=out/'retry-serial';record_path=out/'record.json'
        if record_path.exists():
            record=json.loads(record_path.read_text());assert record['binary_sha256']==digest and record['test_sha256']==input_sha
        else:
            record=e.harness.run_case(strategies[strategy],ROOT/'tools/interactor',path,out,5,180)
            record.update(strategy=strategy,group=group,binary_sha256=digest)
            record_path.write_text(json.dumps(record,indent=2)+'\n')
        assert record['status']=='ok',record
        assert record['solver_cpu_total_s']<5 and record['solver_peak_rss_mb']<256,record
        assert record['judge_commands_seen_including_final_zero']==record['operation_count']+1
        if group=='open15' and strategy!='bestfit':
            assert record['trench_length_m']==record['minimum_trench_lower_bound_m'],record
            assert 'fallback=0' in record['candidate_stderr'] and 'table_conflict=0' in record['candidate_stderr']
        return record
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1 if any(g in ['neutral','safety','holdout'] for g in groups) else 4) as pool:
        for r in pool.map(execute,jobs):
            results.append(r)
            print(r['group'],r['strategy'],r['case'],round(r['kpi'],6),flush=True)
    summary={'records':results,'official_interactor_sha256':e.sha(ROOT/'tools/interactor'),
             'harness_sha256':e.sha(ROOT/'tools/pipes_harness.py'),'platform_actions':0}
    key='-'.join(groups)+'__'+'-'.join(which)
    (HERE/('official-'+key+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
    return results

if __name__=='__main__':run(sys.argv[1].split(','),sys.argv[2].split(','))
