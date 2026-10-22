"""Bounded official local evaluations for the user-authorized campaign."""
import argparse
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CAMPAIGN = Path(__file__).resolve().parent
REPO = CAMPAIGN.parents[1]
NATIVE = REPO / 'shinka-pipes/evaluator-native'
sys.path.insert(0, str(REPO / 'shinka-pipes/search-v3-1'))
from usage_guard import gate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def quota():
    return gate(CAMPAIGN, min_remaining_percent=65, max_age_seconds=60)


@contextmanager
def evaluation_slot():
    """At most two local batches; each runs at most two official cases."""
    streams = [(CAMPAIGN / f'.evaluation-slot-{i}').open('a+') for i in range(2)]
    taken = None
    try:
        while taken is None:
            quota()
            for stream in streams:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    taken = stream
                    break
                except BlockingIOError:
                    pass
            if taken is None:
                time.sleep(.2)
        yield
    finally:
        if taken is not None:
            fcntl.flock(taken.fileno(), fcntl.LOCK_UN)
        for stream in streams:
            stream.close()


def invoke(command, out, log_name, timeout):
    import psutil
    quota()
    with (out / log_name).open('w') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, cwd=REPO, start_new_session=True)
        record = CAMPAIGN / 'processes' / f'{process.pid}.json'
        record.parent.mkdir(exist_ok=True)
        save(record, {'pid': process.pid, 'created_at': psutil.Process(process.pid).create_time(),
            'out': str(out), 'command': command, 'started_at': time.time(), 'status': 'running'})
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            process.wait(timeout=5)
            raise
        finally:
            value = json.loads(record.read_text())
            value.update(status='finished', returncode=process.poll(), finished_at=time.time())
            save(record, value)
    return code


def prepare_checker():
    sys.path.insert(0, str(NATIVE))
    from build_native import build
    checker = CAMPAIGN / 'checker/native_runner'
    with (CAMPAIGN / '.checker-build.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not checker.exists():
            quota()
            build(checker.parent)
        info = json.loads((checker.parent / 'build.json').read_text())
        if digest(checker) != info['binary_sha256'] or digest(NATIVE / 'native_runner.cpp') != info['adapter_sha256']:
            raise ValueError('checker no longer matches its pinned build')
    return checker


def evaluate(source, tests, out, label='candidate'):
    source, tests, out = Path(source).resolve(), Path(tests).resolve(), Path(out).resolve()
    if not source.is_relative_to(CAMPAIGN) or not out.is_relative_to(CAMPAIGN):
        raise ValueError('sources and outputs must be inside this campaign')
    official = REPO / 'data/pipes/open'
    if not (tests == official or (tests.parent == official and tests.suffix == '.in')
            or tests.is_relative_to(CAMPAIGN)):
        raise ValueError('tests must be Open15 or fresh campaign inputs; heldouts excluded')
    if not tests.exists():
        raise FileNotFoundError(tests)
    out.mkdir(parents=True, exist_ok=False)
    source_sha = digest(source)
    shutil.copy2(source, out / 'source.cpp')
    inputs = sorted(tests.glob('*.in')) if tests.is_dir() else [tests]
    if not inputs:
        raise ValueError('empty suite')
    for path in inputs:
        if path.is_symlink():
            raise ValueError('input symlinks are excluded')
    manifest = {'status': 'prepared', 'label': label, 'created_at': datetime.now(ZoneInfo('Asia/Novosibirsk')).isoformat(),
        'source': str(source), 'source_sha256': source_sha, 'tests': str(tests),
        'input_sha256': {str(p): digest(p) for p in inputs}, 'case_count': len(inputs),
        'cpu_limit_exclusive_s': 5, 'rss_limit_exclusive_mib': 256, 'workers': 2,
        'validation_accessed': False, 'platform_accessed': False,
        'engine': 'pinned-official-checker-native-direct'}
    save(out / 'manifest.json', manifest)
    with evaluation_slot():
        checker = prepare_checker()
        compiler = shutil.which('clang++') or shutil.which('g++')
        command = [compiler, '-O2', '-std=c++20', '-pipe', str(out / 'source.cpp'), '-o', str(out / 'solver')]
        compiled = invoke(command, out, 'compile.log', 120)
        if compiled:
            manifest.update(status='compile_failed', compile_returncode=compiled, compile_command=command)
            save(out / 'manifest.json', manifest)
            print(json.dumps({'status': 'compile_failed', 'out': str(out)}), flush=True)
            return manifest
        manifest.update(status='running', compile_command=command, solver_sha256=digest(out / 'solver'))
        save(out / 'manifest.json', manifest)
        command = [sys.executable, '-B', str(NATIVE / 'native_harness.py'), '--workers', '2',
            '--solver', str(out / 'solver'), '--interactor', str(checker), '--name', label,
            '--tests', str(tests), '--out', str(out / 'harness'), '--cpu-limit', '5',
            '--memory-limit-mb', '256', '--response-timeout', '5', '--wall-timeout', '180']
        started = time.monotonic()
        returned = invoke(command, out, 'harness.log', max(240, len(inputs) * 185))
        elapsed = time.monotonic() - started
    summary_path = out / 'harness/summary.json'
    if not summary_path.exists():
        manifest.update(status='harness_failed', harness_returncode=returned)
        save(out / 'manifest.json', manifest)
        return manifest
    summary = json.loads(summary_path.read_text())
    records = summary['records']
    covered = {r['test_sha256'] for r in records}
    expected = set(manifest['input_sha256'].values())
    correct = (returned == 0 and summary['ok_count'] == summary['case_count'] == len(inputs)
        and covered == expected and all(r['status'] == 'ok' and r['solver_cpu_total_s'] is not None
        and r['solver_cpu_total_s'] < 5 and r['solver_peak_rss_mb'] is not None
        and r['solver_peak_rss_mb'] < 256
        and r['judge_commands_seen_including_final_zero'] == r['operation_count'] + 1 for r in records))
    if digest(source) != source_sha or digest(out / 'source.cpp') != source_sha:
        raise RuntimeError('source changed during evaluation')
    if {str(p): digest(p) for p in inputs} != manifest['input_sha256']:
        raise RuntimeError('suite changed during evaluation')
    manifest.update(status='completed' if correct else 'rejected', correct=correct,
        weighted_score=summary['weighted_score_sum'] if correct else None,
        valid_cases=summary['ok_count'], wall_seconds=elapsed,
        max_cpu_s=max((r['solver_cpu_total_s'] or 0 for r in records), default=0),
        max_rss_mib=max((r['solver_peak_rss_mb'] or 0 for r in records), default=0),
        summary_path=str(summary_path), summary_sha256=digest(summary_path),
        harness_returncode=returned, harness_command=command)
    save(out / 'manifest.json', manifest)
    print(json.dumps({k: manifest.get(k) for k in ['status','correct','label','weighted_score','valid_cases','max_cpu_s','max_rss_mib','wall_seconds','summary_path']}), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tests', type=Path, default=REPO / 'data/pipes/open')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--label', default='candidate')
    args = parser.parse_args()
    result = evaluate(args.source, args.tests, args.out, args.label)
    raise SystemExit(0 if result.get('correct') else 1)
