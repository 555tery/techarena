"""Paired native CPU experiment against speed-v4, with exact output parity."""
from pathlib import Path
import argparse
import json
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'speed-review-20261019'))
import verify_speed as v

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--pairs', type=int, default=5)
    parser.add_argument('--baseline', choices=['speed-v4','speed-v5'], default='speed-v4')
    parser.add_argument('--timing-only', action='store_true')
    args = parser.parse_args()
    v.BASE = ROOT/args.baseline
    v.FAST = ROOT/args.candidate
    v.HERE = HERE/args.output
    v.HERE.mkdir(exist_ok=False, parents=True)
    expected_hashes = {'speed-v4':'01e1c58621276de7b04b3dd1138c3549fc85934b3eb422f8f8cedc887d319368',
                       'speed-v5':'d11fe47b4c15d4437c8b34dc516748dfab8b778c5c4f0758d3d4df484bf0c438'}
    assert v.sha(v.BASE/'solution.cpp') == expected_hashes[args.baseline]
    assert v.sha(v.CHECKER) == '0b62cb0a755aaab7529c1dfafb82deb1d12174ce01aca460c09864054d8e5ab7'
    expected = json.loads((ROOT/'speed-review-20261019/paired-final/paired-0/fast/verification.json').read_text())
    pairs = []
    for i in range(args.pairs):
        result = {}
        for label in (['baseline','fast'] if i%2==0 else ['fast','baseline']):
            result[label] = v.run(label, f'paired-{i}', v.REPO/'data/pipes/open')
            assert result[label]['answers'] == expected['answers']
            assert abs(result[label]['score'] - expected['score']) < 1e-12
        pairs.append(result)
    extras = []
    suites = [] if args.timing_only else [('positive-divergence',ROOT/'divergence'),
                        ('delete-divergence',ROOT/'speed-review-20261019/paired-final/delete-divergence')]
    for suite,tests in suites:
        candidate = v.run('fast',suite,tests)
        reference = json.loads((ROOT/f'speed-review-20261019/paired-final/{suite}/fast/verification.json').read_text())
        assert candidate['answers'] == reference['answers']
        extras.append(candidate)
    base = [p['baseline']['cpu_sum_s'] for p in pairs]
    fast = [p['fast']['cpu_sum_s'] for p in pairs]
    bm,fm = statistics.median(base),statistics.median(fast)
    result = {'status':'verified','platform_submissions':0,'score':expected['score'],
              'baseline':args.baseline,'candidate':args.candidate,'candidate_source':str(v.FAST/'solution.cpp'),
              'candidate_source_sha256':v.sha(v.FAST/'solution.cpp'),
              'baseline_source_sha256':v.sha(v.BASE/'solution.cpp'),
              'timing_pairs':args.pairs,'workers':2,'baseline_cpu_sums_s':base,'candidate_cpu_sums_s':fast,
              'baseline_median_cpu_sum_s':bm,'candidate_median_cpu_sum_s':fm,
              'cpu_reduction_percent':100*(1-fm/bm),'faster_pairs':sum(f<b for b,f in zip(base,fast)),
              'candidate_checks':15*args.pairs+sum(x['cases'] for x in extras),'baseline_new_checks':15*args.pairs,
              'candidate_max_cpu_s':max(p['fast']['max_cpu_s'] for p in pairs),
              'candidate_max_rss_mib':max(p['fast']['max_rss_mib'] for p in pairs),
              'exact_open_answer_parity':True,'exact_divergence_answer_parity':True if extras else 'not repeated in timing-only comparison',
              'limitations':'Local macOS user+system CPU; no server timing or submission.',
              'pairs':pairs,'extras':extras}
    v.e.save(v.HERE/'result.json',result)
    print(json.dumps({k:x for k,x in result.items() if k not in ['pairs','extras']},indent=2),flush=True)

if __name__ == '__main__':
    main()
