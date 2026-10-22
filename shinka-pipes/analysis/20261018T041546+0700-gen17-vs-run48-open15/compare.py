"""Fixed two-candidate Open15 check; no search, tuning, or validation access."""
import datetime
import hashlib
import json
import math
import pathlib
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).resolve().parent
REPO = OUT.parents[2]
NATIVE = REPO / 'shinka-pipes/evaluator-native'
sys.path.insert(0, str(NATIVE))
from build_native import build, check_reference


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def now():
    return datetime.datetime.now(ZoneInfo('Asia/Novosibirsk')).isoformat()


def main():
    if (OUT / 'manifest.json').exists():
        raise RuntimeError('Refusing to overwrite an existing comparison')
    old_path = REPO / 'results/pipes/improvement/run48_qualification/runs/open15/run-48/summary.json'
    old = json.loads(old_path.read_text())
    old_rows = {r['case']: r for r in old['records']}
    tests = REPO / 'data/pipes/open'
    inputs = sorted(tests.glob('*.in'), key=lambda p: int(p.stem))
    assert [p.name for p in inputs] == [f'{i}.in' for i in range(1, 16)]
    for path in inputs:
        assert sha(path) == old_rows[path.stem]['test_sha256']
    sources = {
        'gen17': (REPO / 'shinka-pipes/search-v2/runs/20261018T025030+0700-native/gen_17/main.cpp',
                  'cbd4e966ae32a164c31b98316d64113cf84735fb8e10706587eb8f8086e87dfb'),
        'run48': (REPO / 'results/pipes/improvement/run48_qualification/sources/run-48.cpp',
                  '95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39'),
    }
    reference = check_reference()
    manifest = {
        'status': 'prepared', 'started_at': now(), 'dataset': 'Open15',
        'authorization': 'User requested checking generation 17 and the candidate scoring 29.79021 on Open15.',
        'candidate_count': 2, 'case_count_per_candidate': 15, 'workers': 2,
        'fitness': 'sum of official test weight * final occupied length / final trench length',
        'limits': {'cpu_seconds_exclusive': 5, 'rss_mib_exclusive': 256,
                   'response_timeout_seconds': 5, 'wall_timeout_seconds': 180},
        'source_origins': {k: {'path': str(p), 'sha256': h} for k, (p, h) in sources.items()},
        'input_sha256': {p.name: sha(p) for p in inputs},
        'historical_run48_summary': {'path': str(old_path), 'sha256': sha(old_path)},
        'engine': 'native-direct-v1', 'reference': reference,
        'native_harness_sha256': sha(NATIVE / 'native_harness.py'),
        'comparison_script_sha256': sha(__file__),
        'validation_accessed': False, 'evolution_started': False,
        'shinka_run_modified': False, 'platform_accessed': False,
        'result_not_injected_into_search_feedback': True,
    }
    for name, (source, expected) in sources.items():
        assert sha(source) == expected
        target = OUT / 'sources' / f'{name}.cpp'
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(target) == expected
    save('manifest.json', manifest)
    native = build(OUT / 'checker')
    compiler = shutil.which('g++')
    manifest['compiler'] = subprocess.run([compiler, '--version'], capture_output=True, text=True, check=True).stdout
    manifest['checker_build'] = json.loads((OUT / 'checker/build.json').read_text())
    summaries = {}
    for name in sources:
        binary = OUT / 'binaries' / name
        binary.parent.mkdir(exist_ok=True)
        command = [compiler, '-O2', '-std=c++20', '-pipe', str(OUT / 'sources' / f'{name}.cpp'), '-o', str(binary)]
        compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
        (OUT / f'{name}-compile.log').write_text(compiled.stdout + compiled.stderr)
        compiled.check_returncode()
        manifest.setdefault('builds', {})[name] = {'command': command, 'binary_sha256': sha(binary)}
    manifest['status'] = 'running'
    save('manifest.json', manifest)
    for name in sources:
        command = [sys.executable, '-B', str(NATIVE / 'native_harness.py'), '--workers', '2',
                   '--solver', str(OUT / 'binaries' / name), '--name', name, '--interactor', str(native),
                   '--tests', str(tests), '--out', str(OUT / 'runs' / name),
                   '--response-timeout', '5', '--wall-timeout', '180', '--cpu-limit', '5', '--memory-limit-mb', '256']
        started = time.monotonic()
        print('START', name, flush=True)
        with (OUT / f'{name}-harness.log').open('w') as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        elapsed = time.monotonic() - started
        completed.check_returncode()
        summary = json.loads((OUT / 'runs' / name / 'summary.json').read_text())
        assert summary['case_count'] == summary['ok_count'] == 15
        assert math.isclose(summary['weight_sum'], 32.1, abs_tol=1e-12)
        for row in summary['records']:
            assert row['test_sha256'] == old_rows[row['case']]['test_sha256']
            assert row['status'] == 'ok'
            assert row['solver_cpu_total_s'] < 5 and row['solver_peak_rss_mb'] < 256
            assert row['judge_commands_seen_including_final_zero'] == row['operation_count'] + 1
            exact = row['official_weight'] * row['occupied_length_m'] / row['trench_length_m']
            assert math.isclose(row['weighted_score'], exact, abs_tol=1e-12)
        summaries[name] = summary
        manifest.setdefault('executions', {})[name] = {'command': command, 'returncode': completed.returncode,
            'wall_seconds': elapsed, 'summary_sha256': sha(OUT / 'runs' / name / 'summary.json')}
        save('manifest.json', manifest)
        print('DONE', name, summary['weighted_score_sum'], 'wall_s', round(elapsed, 2), flush=True)
    maps = {k: {r['case']: r for r in v['records']} for k, v in summaries.items()}
    comparison = []
    for i in range(1, 16):
        case = str(i)
        a, b, historical = maps['gen17'][case], maps['run48'][case], old_rows[case]
        assert b['trench_length_m'] == historical['trench_length_m']
        assert math.isclose(b['weighted_score'], historical['weighted_score'], abs_tol=1e-12)
        assert sha(b['judge_output_file']) == sha(historical['judge_output_file'])
        comparison.append({'case': i, 'test_sha256': a['test_sha256'], 'weight': a['official_weight'],
            'gen17_trench_m': a['trench_length_m'], 'run48_trench_m': b['trench_length_m'],
            'trench_delta_gen17_minus_run48_m': a['trench_length_m'] - b['trench_length_m'],
            'gen17_score': a['weighted_score'], 'run48_score': b['weighted_score'],
            'score_delta_gen17_minus_run48': a['weighted_score'] - b['weighted_score'],
            'gen17_output_sha256': sha(a['judge_output_file']), 'run48_output_sha256': sha(b['judge_output_file'])})
    result = {'dataset': 'Open15', 'candidate_count': 2, 'cases': 15, 'max_score': 32.1,
              'gen17': {}, 'run48': {}, 'historical_run48_reproduced': '15/15 scores, trench lengths and transcript SHA256',
              'per_case': comparison, 'validation_accessed': False, 'platform_accessed': False}
    for name, summary in summaries.items():
        result[name] = {'source_sha256': sources[name][1], 'weighted_score': summary['weighted_score_sum'],
            'valid_cases': summary['ok_count'], 'max_solver_cpu_seconds': max(r['solver_cpu_total_s'] for r in summary['records']),
            'max_solver_rss_mib': max(r['solver_peak_rss_mb'] for r in summary['records']),
            'evaluation_wall_seconds': manifest['executions'][name]['wall_seconds']}
    result['score_delta_gen17_minus_run48'] = result['gen17']['weighted_score'] - result['run48']['weighted_score']
    result['gen17_case_outcomes'] = {k: sum((r['score_delta_gen17_minus_run48'] > 1e-12 if k == 'wins' else
                                          r['score_delta_gen17_minus_run48'] < -1e-12 if k == 'losses' else
                                          abs(r['score_delta_gen17_minus_run48']) <= 1e-12) for r in comparison)
                                    for k in ('wins', 'losses', 'ties')}
    for source, expected in sources.values():
        assert sha(source) == expected
    assert check_reference() == reference
    assert {p.name: sha(p) for p in inputs} == manifest['input_sha256']
    save('comparison.json', result)
    manifest.update(status='completed', finished_at=now(), comparison_sha256=sha(OUT / 'comparison.json'))
    save('manifest.json', manifest)
    print(json.dumps({k: v for k, v in result.items() if k != 'per_case'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
