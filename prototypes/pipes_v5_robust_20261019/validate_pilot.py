"""Original official interactive checks for one frozen candidate and fixed suites."""
import concurrent.futures
import json
import sys
from pathlib import Path
from experiment import HERE, ROOT, BASE, harness, sha

BF=[str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')]

def main():
    v3='--v3' in sys.argv
    v2='--v2' in sys.argv or v3
    candidate_name='candidate-v3' if v3 else 'candidate-v2' if v2 else 'candidate'
    candidate=HERE/candidate_name/'solver'
    assert candidate.exists()
    freeze=json.loads((HERE/candidate_name/'build.json').read_text())
    assert sha(candidate)==freeze['binary_sha256']
    strategies={'v5':[str(BASE/'target/solver')],candidate_name:[str(candidate)],'bestfit':BF}
    if not v2:strategies['candidate-firstfit']=[str(HERE/'candidate-firstfit/solver')]
    groups={
        'new':sorted((HERE/'new_attacks').glob('*.in')),
        'known':sorted((BASE/'suite').glob('*.in')),
        'neutral':sorted((HERE/'neutral').glob('*.in')),
        'open15':[ROOT/f'data/pipes/open/{i}.in' for i in range(1,16)],
        'counterattack':sorted((HERE/'counterattacks').glob('*.in')),
    }
    jobs=[]
    for group,paths in groups.items():
        names=([candidate_name] if v2 else ['candidate','candidate-firstfit']) if group in ['known','open15'] else list(strategies)
        jobs.extend((group,name,path) for path in paths for name in names)
    def execute(job):
        group,name,path=job
        out=HERE/'evaluations'/group/name/path.stem
        binary_sha=sha(strategies[name][0]);input_sha=sha(path)
        record_file=out/'record.json'
        if record_file.exists():
            record=json.loads(record_file.read_text())
            assert record['binary_sha256']==binary_sha and record['test_sha256']==input_sha
        else:
            record=harness.run_case(strategies[name],ROOT/'tools/interactor',path,out,5,180)
            record.update(strategy=name,group=group,binary_sha256=binary_sha)
            record_file.write_text(json.dumps(record,indent=2)+'\n')
        assert record['status']=='ok',record
        assert record['solver_cpu_total_s']<5 and record['solver_peak_rss_mb']<256,record
        if group=='open15':
            assert record['trench_length_m']==record['minimum_trench_lower_bound_m'],record
            assert 'fallback=0' in record['candidate_stderr'],record['candidate_stderr']
            assert 'table_conflict=0' in record['candidate_stderr']
        return record
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(execute,jobs):
            records.append(result)
            print(result['group'],result['strategy'],result['case'],round(result['kpi'],6),flush=True)
    summary={'records':records,'candidate':freeze,'firstfit_candidate':json.loads((HERE/'candidate-firstfit/build.json').read_text()),'official_interactor_sha256':sha(ROOT/'tools/interactor'),
             'harness_sha256':sha(ROOT/'tools/pipes_harness.py'),'platform_actions':0}
    (HERE/('official-results-v3.json' if v3 else 'official-results-v2.json' if v2 else 'official-results.json')).write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':main()
