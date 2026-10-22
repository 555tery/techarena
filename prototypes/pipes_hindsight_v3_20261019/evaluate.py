"""Bounded local official evaluations; coordinator only, no model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
NATIVE = REPO / 'shinka-pipes/evaluator-native'
sys.path.insert(0, str(REPO / 'shinka-pipes/search-v3-1'))
from usage_guard import gate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def quota():
    return gate(ROOT, min_remaining_percent=65, max_age_seconds=45)


def verify_freeze():
    frozen = json.loads((ROOT / 'freeze.json').read_text())
    for name, expected in frozen['artifact_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen artifact changed: ' + name)
    for label, expected in frozen['binary_sha256'].items():
        if sha(ROOT / 'builds' / label / 'solver') != expected:
            raise ValueError('Frozen binary changed: ' + label)
    return frozen


def invoke(command, out, name, timeout):
    import psutil
    quota()
    with (out / name).open('w') as log:
        p = subprocess.Popen(command, cwd=REPO, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        identity = {'pid': p.pid, 'created_at': psutil.Process(p.pid).create_time(),
                    'command': command, 'status': 'running', 'started_at': time.time()}
        record = ROOT / 'processes' / f'{p.pid}.json'
        save(record, identity)
        start, last_gate = time.monotonic(), time.monotonic()
        try:
            while p.poll() is None:
                if time.monotonic() - start > timeout:
                    raise TimeoutError(command[0])
                if time.monotonic() - last_gate > 30:
                    quota()
                    last_gate = time.monotonic()
                time.sleep(.2)
            return p.returncode
        finally:
            if p.poll() is None:
                try:
                    owner = psutil.Process(p.pid)
                    if abs(owner.create_time() - identity['created_at']) < .01:
                        children = owner.children(recursive=True)
                        for child in children:
                            child.terminate()
                        owner.terminate()
                        _, living = psutil.wait_procs(children + [owner], timeout=3)
                        for child in living:
                            child.kill()
                except psutil.NoSuchProcess:
                    pass
                p.wait(timeout=5)
            identity.update(status='finished', finished_at=time.time(), returncode=p.returncode)
            save(record, identity)


def build_variant(label):
    spec = json.loads((ROOT / 'variants.json').read_text())[label]
    source_root = ROOT / spec['directory']
    out = ROOT / 'builds' / label
    out.mkdir(parents=True, exist_ok=False)
    snapshot = out / 'source'
    snapshot.mkdir()
    hashes = {}
    for path in source_root.rglob('*'):
        if path.is_file() and path.suffix in ('.cpp', '.hpp', '.h', '.inc'):
            relative = path.relative_to(source_root)
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            hashes[str(relative)] = sha(path)
    for relative, origin in spec.get('overrides', {}).items():
        shutil.copy2(ROOT / origin, snapshot / relative)
        hashes[relative] = sha(snapshot / relative)
    compiler = shutil.which('clang++') or shutil.which('g++')
    command = [compiler, '-std=c++20', '-O2', '-pipe', '-Wall', '-Wextra',
               *['-D' + d for d in spec.get('defines', [])],
               '-I', str(snapshot), str(snapshot / spec['entry']), '-o', str(out / 'solver')]
    rc = invoke(command, out, 'compile.log', 120)
    manifest = {'label': label, 'spec': spec, 'source_files_sha256': hashes,
                'compile_command': command, 'returncode': rc, 'created_at': time.time()}
    if rc == 0:
        manifest['binary_sha256'] = sha(out / 'solver')
    save(out / 'manifest.json', manifest)
    print(json.dumps({'label': label, 'compiled': rc == 0}))
    if rc:
        raise RuntimeError('Compile failed: ' + label)


def prepare_checker():
    out = ROOT / 'checker'
    out.mkdir(exist_ok=True)
    prior = REPO / 'prototypes/pipes_architecture_v2_20261018/checker'
    info = json.loads((prior / 'build.json').read_text())
    if sha(prior / 'native_runner') != info['binary_sha256']:
        raise ValueError('Checker binary hash mismatch')
    if sha(NATIVE / 'native_runner.cpp') != info['adapter_sha256']:
        raise ValueError('Checker adapter hash mismatch')
    shutil.copy2(prior / 'native_runner', out / 'native_runner')
    save(out / 'build.json', info)
    return out / 'native_runner'


def evaluate(label, phase, workers=2):
    quota()
    if phase in ('final', 'repeat') and not (ROOT / 'freeze.json').exists():
        raise ValueError('Final evaluation requires freeze')
    if phase in ('final', 'repeat'):
        verify_freeze()
    build = ROOT / 'builds' / label
    built = json.loads((build / 'manifest.json').read_text())
    if sha(build / 'solver') != built['binary_sha256']:
        raise ValueError('Binary changed')
    for relative, expected in built['source_files_sha256'].items():
        if sha(build / 'source' / relative) != expected:
            raise ValueError('Source snapshot changed')
    tests = ROOT / 'data' / phase
    files = sorted(tests.glob('*.in'))
    if not files:
        raise ValueError('Empty test set')
    counter_path = ROOT / 'evaluation-counts.json'
    counter = json.loads(counter_path.read_text()) if counter_path.exists() else {'reserved': 0, 'batches': []}
    if counter['reserved'] + len(files) > 800:
        raise ValueError('Predeclared official budget exceeded')
    out = ROOT / 'evaluations' / phase / label
    out.mkdir(parents=True, exist_ok=False)
    checker = prepare_checker()
    manifest = {'label': label, 'phase': phase, 'status': 'running', 'created_at': time.time(),
                'binary_sha256': built['binary_sha256'], 'build_manifest_sha256': sha(build / 'manifest.json'),
                'input_sha256': {str(p): sha(p) for p in files}, 'workers': workers}
    counter['reserved'] += len(files)
    counter['batches'].append({'label': label, 'phase': phase, 'cases': len(files)})
    save(counter_path, counter)
    save(out / 'manifest.json', manifest)
    command = [sys.executable, '-B', str(NATIVE / 'native_harness.py'), '--workers', str(workers),
               '--solver', str(build / 'solver'), '--interactor', str(checker),
               '--tests', str(tests), '--out', str(out / 'harness'), '--name', label,
               '--cpu-limit', '5', '--memory-limit-mb', '256', '--response-timeout', '5', '--wall-timeout', '180']
    rc = invoke(command, out, 'harness.log', max(240, len(files) * 185))
    summary = json.loads((out / 'harness/summary.json').read_text())
    records = summary['records']
    expected = set(manifest['input_sha256'].values())
    correct = (rc == 0 and summary['case_count'] == summary['ok_count'] == len(files)
               and {r['test_sha256'] for r in records} == expected
               and all(r['status'] == 'ok' and r['solver_cpu_total_s'] is not None
                       and r['solver_cpu_total_s'] < 5 and r['solver_peak_rss_mb'] is not None
                       and r['solver_peak_rss_mb'] < 256
                       and r['judge_commands_seen_including_final_zero'] == r['operation_count'] + 1
                       for r in records))
    if {str(p): sha(p) for p in files} != manifest['input_sha256']:
        raise ValueError('Input changed during evaluation')
    manifest.update(status='completed' if correct else 'rejected', correct=correct,
                    finished_at=time.time(), returncode=rc, command=command,
                    weighted_score=summary['weighted_score_sum'] if correct else None,
                    ok_count=summary['ok_count'], case_count=len(files),
                    max_cpu=max((r['solver_cpu_total_s'] or 0 for r in records), default=0),
                    max_rss=max((r['solver_peak_rss_mb'] or 0 for r in records), default=0))
    save(out / 'manifest.json', manifest)
    print(json.dumps({k:manifest[k] for k in ('label','phase','status','ok_count','case_count','weighted_score','max_cpu','max_rss')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'evaluate'])
    parser.add_argument('label')
    parser.add_argument('--phase', choices=['preflight','dev','final','repeat'], default='preflight')
    parser.add_argument('--workers', type=int, choices=[1,2], default=2)
    args = parser.parse_args()
    build_variant(args.label) if args.action == 'build' else evaluate(args.label, args.phase, args.workers)
