"""One user-authorized Open15 check of the frozen current SEARCH-v3.1 leader."""
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
NATIVE = REPO / 'shinka-pipes/evaluator-native'
RUN = REPO / 'shinka-pipes/search-v3-1/runs/20261018T062832+0700-mixed'
SOURCE = RUN / 'gen_61/main.cpp'
EXPECTED = 'cca58bed19e387150d42706cde80e3dad24ad49a5f0f6258a33f17e45f718fcf'
sys.path.insert(0, str(NATIVE))
from build_native import build, check_reference


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def now():
    return datetime.now(ZoneInfo('Asia/Novosibirsk')).isoformat()


def main():
    if (OUT / 'manifest.json').exists():
        raise RuntimeError('Refusing to overwrite an existing check')
    assert sha(SOURCE) == EXPECTED
    previous = REPO / 'shinka-pipes/analysis/20261018T041546+0700-gen17-vs-run48-open15'
    lab_manifest_path = REPO / 'results/pipes/improvement/case9_push_20261018/manifest.json'
    lab = json.loads(lab_manifest_path.read_text())['latest_research_update']['current_leader_plus_c2_open15']
    baselines = {
        'search_v31_gen0_v2_gen17': previous / 'runs/gen17/summary.json',
        'run48': previous / 'runs/run48/summary.json',
        'local_lab_leader_c2': REPO / lab['open15_report'],
    }
    historical = {k: json.loads(p.read_text()) for k, p in baselines.items()}
    old_rows = {k: {str(r['case']): r for r in s['records']} for k, s in historical.items()}
    tests = REPO / 'data/pipes/open'
    inputs = sorted(tests.glob('*.in'), key=lambda p: int(p.stem))
    assert [p.name for p in inputs] == [f'{i}.in' for i in range(1, 16)]
    for summary in historical.values():
        assert summary['case_count'] == summary['ok_count'] == 15
        assert math.isclose(summary['weight_sum'], 32.1, abs_tol=1e-12)
    for p in inputs:
        assert all(sha(p) == rows[p.stem]['test_sha256'] for rows in old_rows.values())
    assert sha(REPO / lab['source_path']) == lab['source_sha256']
    reference = check_reference()
    snapshot = REPO / 'shinka-pipes/search-v3-1/snapshot.json'
    source_copy = OUT / 'source.cpp'
    shutil.copyfile(SOURCE, source_copy)
    assert sha(source_copy) == EXPECTED
    manifest = {
        'status': 'prepared', 'started_at': now(), 'authorization': 'User: проверь текущий код на опен 15',
        'dataset': 'Open15', 'candidate_count': 1, 'case_count': 15, 'workers': 2,
        'generation': 61, 'idea': 'stratified_growth_horizon', 'source_path': str(SOURCE),
        'source_sha256': EXPECTED, 'source_copy': str(source_copy),
        'search_F_T': 0.8595614664833043, 'snapshot_sha256': sha(snapshot),
        'metric': 'sum of official weights times final live volume divided by final trench length',
        'limits': {'cpu_seconds_exclusive': 5, 'rss_mib_exclusive': 256,
                   'response_timeout_seconds': 5, 'wall_timeout_seconds': 180},
        'input_sha256': {p.name: sha(p) for p in inputs},
        'historical_summaries': {k: {'path': str(p), 'sha256': sha(p)} for k, p in baselines.items()},
        'reference': reference, 'script_sha256': sha(__file__),
        'native_harness_sha256': sha(NATIVE / 'native_harness.py'),
        'validation_accessed': False, 'stress_accessed': False, 'platform_accessed': False,
        'shinka_run_modified': False, 'result_injected_into_search_feedback': False,
    }
    save('manifest.json', manifest)
    native = build(OUT / 'checker')
    compiler = shutil.which('g++')
    command = [compiler, '-O2', '-std=c++20', '-pipe', str(source_copy), '-o', str(OUT / 'solver')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (OUT / 'compile.log').write_text(result.stdout + result.stderr)
    result.check_returncode()
    manifest.update(status='running', compiler=subprocess.run([compiler, '--version'], capture_output=True,
        text=True, check=True).stdout, compile_command=command, solver_sha256=sha(OUT / 'solver'),
        checker_build=json.loads((OUT / 'checker/build.json').read_text()))
    save('manifest.json', manifest)
    command = [sys.executable, '-B', str(NATIVE / 'native_harness.py'), '--workers', '2',
        '--solver', str(OUT / 'solver'), '--name', 'SEARCH-v3.1-gen61', '--interactor', str(native),
        '--tests', str(tests), '--out', str(OUT / 'open15'), '--response-timeout', '5',
        '--wall-timeout', '180', '--cpu-limit', '5', '--memory-limit-mb', '256']
    started = time.monotonic()
    with (OUT / 'harness.log').open('w') as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=900)
    elapsed = time.monotonic() - started
    completed.check_returncode()
    summary = json.loads((OUT / 'open15/summary.json').read_text())
    assert summary['case_count'] == summary['ok_count'] == 15
    assert math.isclose(summary['weight_sum'], 32.1, abs_tol=1e-12)
    per_case = []
    for row in summary['records']:
        case = str(row['case'])
        assert row['test_sha256'] == manifest['input_sha256'][case + '.in']
        assert row['status'] == 'ok' and row['solver_cpu_total_s'] < 5 and row['solver_peak_rss_mb'] < 256
        assert row['judge_commands_seen_including_final_zero'] == row['operation_count'] + 1
        assert math.isclose(row['weighted_score'], row['official_weight'] * row['occupied_length_m'] / row['trench_length_m'], abs_tol=1e-12)
        item = dict(case=int(case), weight=row['official_weight'], trench_m=row['trench_length_m'],
            F_T=row['occupied_length_m']/row['trench_length_m'], weighted_score=row['weighted_score'],
            cpu_s=row['solver_cpu_total_s'], rss_mib=row['solver_peak_rss_mb'])
        for name, rows in old_rows.items():
            previous_row = rows[case]
            assert previous_row['official_weight'] == row['official_weight']
            item[name + '_trench_m'] = previous_row['trench_length_m']
            item[name + '_score_delta'] = row['weighted_score'] - previous_row['weighted_score']
        per_case.append(item)
    score = sum(r['weighted_score'] for r in summary['records'])
    assert math.isclose(score, summary['weighted_score_sum'], abs_tol=1e-12)
    comparisons = {}
    for name, old in historical.items():
        comparisons[name] = dict(weighted_score=old['weighted_score_sum'], delta=score-old['weighted_score_sum'],
            wins=sum(p[name+'_score_delta'] > 1e-12 for p in per_case),
            losses=sum(p[name+'_score_delta'] < -1e-12 for p in per_case),
            ties=sum(abs(p[name+'_score_delta']) <= 1e-12 for p in per_case))
    report = dict(generation=61, source_sha256=EXPECTED, valid_cases=15, weighted_score=score,
        formal_maximum=32.1, max_cpu_s=max(r['cpu_s'] for r in per_case),
        max_rss_mib=max(r['rss_mib'] for r in per_case), wall_seconds=elapsed,
        comparisons=comparisons, per_case=per_case)
    save('comparison.json', report)
    with (OUT / 'comparison.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=list(per_case[0]));writer.writeheader();writer.writerows(per_case)
    assert sha(SOURCE) == sha(source_copy) == EXPECTED
    assert sha(snapshot) == manifest['snapshot_sha256']
    assert {p.name: sha(p) for p in inputs} == manifest['input_sha256']
    assert check_reference() == reference
    manifest.update(status='completed', finished_at=now(), harness_command=command,
        harness_returncode=completed.returncode, wall_seconds=elapsed,
        summary_sha256=sha(OUT / 'open15/summary.json'), comparison_sha256=sha(OUT / 'comparison.json'))
    save('manifest.json', manifest)
    print(json.dumps({k:v for k,v in report.items() if k!='per_case'}, indent=2),flush=True)


if __name__ == '__main__':
    main()
