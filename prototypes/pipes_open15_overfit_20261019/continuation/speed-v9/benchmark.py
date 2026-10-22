"""Interleaved full interactive measurements against the accepted speed-v8."""
from pathlib import Path
import argparse
import json
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT/'speed-review-20261019'))
import verify_speed as v


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', default='speed-v9')
    parser.add_argument('--output', default='timing')
    parser.add_argument('--pairs', type=int, default=7)
    args = parser.parse_args()
    candidate = ROOT/args.candidate
    v.BASE = ROOT/'speed-v8'; v.FAST = candidate; v.HERE = candidate/args.output
    v.HERE.mkdir(exist_ok=False)
    assert v.sha(v.BASE/'solution.cpp') == '90cd2b21f6a290fae4c9a2e456a7c26934f526ecf3bae60de7502f300e0cc8fb'
    expected = json.loads((ROOT/'speed-review-20261019/paired-final/paired-0/fast/verification.json').read_text())
    pairs = []
    for pair in range(args.pairs):
        row = {}
        for label in (['baseline','fast'] if pair % 2 == 0 else ['fast','baseline']):
            summary = v.run(label, f'pair-{pair}', v.REPO/'data/pipes/open')
            assert summary['answers'] == expected['answers']
            assert abs(summary['score'] - expected['score']) < 1e-12
            raw = json.loads((v.HERE/f'pair-{pair}'/label/'harness/summary.json').read_text())
            summary['user_cpu_sum_s'] = sum(x['solver_cpu_user_s'] for x in raw['records'])
            summary['system_cpu_sum_s'] = sum(x['solver_cpu_system_s'] for x in raw['records'])
            row[label] = summary
        pairs.append(row)
    base = [x['baseline']['cpu_sum_s'] for x in pairs]
    fast = [x['fast']['cpu_sum_s'] for x in pairs]
    deltas = [b-f for b, f in zip(base, fast)]
    rng = random.Random(20261019)
    means = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(10000))
    result = {'status':'verified', 'candidate':args.candidate, 'pairs':args.pairs, 'workers':2,
              'source_sha256':v.sha(candidate/'solution.cpp'), 'score':expected['score'],
              'all_answers_identical':True, 'baseline_cpu_sums':base, 'candidate_cpu_sums':fast,
              'baseline_median':statistics.median(base), 'candidate_median':statistics.median(fast),
              'median_cpu_reduction_percent':100*(1-statistics.median(fast)/statistics.median(base)),
              'faster_pairs':sum(d>0 for d in deltas),
              'paired_mean_saved_seconds':statistics.mean(deltas),
              'paired_bootstrap_95_ci_seconds':[means[250],means[9749]],
              'candidate_user_cpu_median':statistics.median(x['fast']['user_cpu_sum_s'] for x in pairs),
              'baseline_user_cpu_median':statistics.median(x['baseline']['user_cpu_sum_s'] for x in pairs),
              'candidate_system_cpu_median':statistics.median(x['fast']['system_cpu_sum_s'] for x in pairs),
              'baseline_system_cpu_median':statistics.median(x['baseline']['system_cpu_sum_s'] for x in pairs),
              'measurements':pairs,
              'scope':'Local macOS interactive solver CPU; does not establish Windows/server speed. Small paired sample; bootstrap is descriptive.'}
    v.e.save(v.HERE/'result.json', result)
    print(json.dumps({k:x for k,x in result.items() if k!='measurements'},indent=2),flush=True)


if __name__ == '__main__':
    main()
