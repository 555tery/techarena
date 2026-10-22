"""Paired CPU measurements and exact transcript parity; no platform calls."""
from pathlib import Path
import hashlib
import json
import random
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from runtime import REPO, e

BASE = ROOT / 'release-v5'
FAST = ROOT / 'speed-v1'
CHECKER = REPO / 'prototypes/pipes_architecture_v2_20261018/checker/native_runner'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def generate_delete_divergence():
    """Exercise the first mismatch on deletion, including a crowded late prefix."""
    out = HERE / 'delete-divergence'
    out.mkdir(exist_ok=False)
    rows = []
    for case in [5, 9, 11, 13, 15]:
        tokens = (REPO / f'data/pipes/open/{case}.in').read_text().split()
        n = int(tokens[1]); commands = list(map(int, tokens[2:2+n]))
        for kind, cut in [('early', min(20, n-1)), ('late', n-20)]:
            seq = commands[:cut]; live = {}; pid = 0
            for c in seq:
                if c > 0:
                    pid += 1; live[pid] = c
                else:
                    del live[-c]
            victims = [i for i in live if -i != commands[cut]]
            assert victims
            victim = victims[-1]; seq.append(-victim); del live[victim]
            rng = random.Random(20261019000 + case * 10 + (kind == 'late'))
            for k in range(min(160, 200000-len(seq))):
                if live and k % 3 == 0:
                    v = rng.choice(list(live)); seq.append(-v); del live[v]
                else:
                    size = rng.randint(1, 40); seq.append(size); pid += 1; live[pid] = size
            path = out / f'{case:02d}_{kind}.in'
            path.write_text('1\n' + str(len(seq)) + '\n' + '\n'.join(map(str, seq)) + '\n0\n')
            rows.append({'path': str(path), 'sha256': sha(path), 'prefix': cut,
                         'first_mismatch': 'deletion', 'scope': 'correctness only'})
    e.save(HERE / 'delete-divergence.json', rows)
    return out


def run(label, suite, tests):
    source = BASE if label == 'baseline' else FAST
    build = json.loads((source / 'build.json').read_text())
    assert sha(source/'solution.cpp') == build['source_sha256']
    assert sha(source/'solver') == build['binary_sha256']
    out = HERE / suite / label
    out.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): sha(p) for p in sorted(tests.glob('*.in'))}
    command = [sys.executable, '-B', str(e.NATIVE/'native_harness.py'), '--workers', '2',
               '--solver', str(source/'solver'), '--interactor', str(CHECKER),
               '--tests', str(tests), '--out', str(out/'harness'), '--name', label,
               '--cpu-limit', '5', '--memory-limit-mb', '256',
               '--response-timeout', '5', '--wall-timeout', '180']
    assert e.invoke(command, out, 'run.log', 900) == 0
    s = json.loads((out/'harness/summary.json').read_text())
    assert s['ok_count'] == s['case_count'] == len(inputs)
    assert inputs == {str(p): sha(p) for p in sorted(tests.glob('*.in'))}
    assert sha(source/'solution.cpp') == build['source_sha256']
    assert sha(source/'solver') == build['binary_sha256']
    for row in s['records']:
        assert row['solver_cpu_total_s'] < 5 and row['solver_peak_rss_mb'] < 256
        assert row['judge_commands_seen_including_final_zero'] == row['operation_count']+1
        assert 'table_conflict=0' in row['candidate_stderr']
    summary = {'source_sha256': build['source_sha256'], 'binary_sha256': build['binary_sha256'],
               'cases': s['case_count'], 'score': s['weighted_score_sum'],
               'cpu_sum_s': sum(x['solver_cpu_total_s'] for x in s['records']),
               'max_cpu_s': max(x['solver_cpu_total_s'] for x in s['records']),
               'max_rss_mib': max(x['solver_peak_rss_mb'] for x in s['records']),
               'answers': {x['case']: sha(x['judge_output_file']) for x in s['records']},
               'per_case_cpu': {x['case']: x['solver_cpu_total_s'] for x in s['records']}}
    e.save(out/'verification.json', summary)
    print(suite, label, summary['cpu_sum_s'], summary['score'], flush=True)
    return summary


def main():
    assert sha(BASE/'solution.cpp') == '7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
    assert sha(CHECKER) == '0b62cb0a755aaab7529c1dfafb82deb1d12174ce01aca460c09864054d8e5ab7'
    expected = json.loads((BASE/'open/harness/summary.json').read_text())
    expected_answers = {x['case']: sha(x['judge_output_file']) for x in expected['records']}
    pairs = []
    for i in range(5):
        rows = {}
        order = ['baseline', 'fast'] if i % 2 == 0 else ['fast', 'baseline']
        for label in order:
            rows[label] = run(label, f'paired-{i}', REPO/'data/pipes/open')
            assert rows[label]['answers'] == expected_answers
        assert abs(rows['fast']['score'] - 30.75747404826914) < 1e-12
        pairs.append(rows)
    extra = []
    for name, tests in [('positive-divergence', ROOT/'divergence'),
                        ('delete-divergence', generate_delete_divergence())]:
        b = run('baseline', name, tests); f = run('fast', name, tests)
        assert b['answers'] == f['answers']
        extra.append({'suite': name, 'baseline': b, 'fast': f, 'exact_transcript_parity': True})
    base = [x['baseline']['cpu_sum_s'] for x in pairs]
    fast = [x['fast']['cpu_sum_s'] for x in pairs]
    baseline_median = statistics.median(base); fast_median = statistics.median(fast)
    result = {'status': 'verified', 'platform_submissions': 0,
              'scope': 'same Open15 plans and identical outputs; CPU optimization only',
              'score': pairs[0]['fast']['score'], 'timing_pairs': 5,
              'workers': 2, 'metric': 'sum of native solver user+system CPU seconds over 15 tests',
              'baseline_cpu_sums_s': base, 'fast_cpu_sums_s': fast,
              'baseline_median_cpu_sum_s': baseline_median, 'fast_median_cpu_sum_s': fast_median,
              'speedup_ratio': baseline_median / fast_median,
              'cpu_reduction_percent': 100*(1-fast_median/baseline_median),
              'exact_open_answer_parity': True, 'exact_divergence_answer_parity': True,
              'candidate_checks': 5*15+30+10, 'baseline_checks': 5*15+30+10,
              'candidate_source': str(FAST/'solution.cpp'),
              'candidate_source_sha256': sha(FAST/'solution.cpp'),
              'baseline_source_sha256': sha(BASE/'solution.cpp'),
              'max_candidate_cpu_s': max([x['fast']['max_cpu_s'] for x in pairs] + [x['fast']['max_cpu_s'] for x in extra]),
              'max_candidate_rss_mib': max([x['fast']['max_rss_mib'] for x in pairs] + [x['fast']['max_rss_mib'] for x in extra]),
              'pairs': pairs, 'extra': extra,
              'limitations': 'Local macOS clang++ measurements; server CPU and ranking impact unmeasured.'}
    e.save(HERE/'result.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['pairs','extra']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
