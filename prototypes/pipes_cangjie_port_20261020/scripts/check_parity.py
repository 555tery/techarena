#!/usr/bin/env python3
"""Compare every protocol answer with frozen C++, before interactive validation.

Input is preloaded for this diagnostic stage. These resource numbers are NOT
the final interactive benchmark and are kept separately for that reason.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]

def run(binary, inp, prefix):
    env = os.environ.copy()
    env['cjProcessorNum'] = '1'
    with inp.open('rb') as stdin, prefix.with_suffix('.stdout').open('wb') as stdout, prefix.with_suffix('.stderr').open('wb') as stderr:
        proc = subprocess.Popen([str(binary)], stdin=stdin, stdout=stdout, stderr=stderr, env=env, start_new_session=True)
        started = time.monotonic()
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - started > 90:
                os.killpg(proc.pid, signal.SIGKILL)
            time.sleep(0.005)
    return {'returncode': proc.returncode, 'cpu_s': usage.ru_utime + usage.ru_stime,
            'rss_mib': usage.ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024),
            'stdout_sha256': hashlib.sha256(prefix.with_suffix('.stdout').read_bytes()).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    parser.add_argument('--test', type=Path)
    args = parser.parse_args()
    paths = sorted((ROOT / 'prototypes/pipes_online_patterns_20261020/release/tests').rglob('*.in'))
    paths += sorted((BASE / 'fresh_tests').glob('*.in'))
    if args.test: paths = [args.test.resolve()]
    elif args.limit: paths = paths[:args.limit]
    out = BASE / 'parity'
    out.mkdir(exist_ok=True)
    records = []
    for i, path in enumerate(paths):
        tokens = path.read_bytes().split()
        n = int(tokens[1]); commands = tokens[2:2+n]
        inp = out / 'commands.in'
        inp.write_bytes(b'\n'.join(commands) + b'\n0\n')
        identity = ('fresh/' if path.parent == BASE / 'fresh_tests' else path.parent.name + '/') + path.stem
        case = out / identity
        case.mkdir(parents=True, exist_ok=True)
        cpp = run(BASE / 'bin/solution-cpp', inp, case / 'cpp')
        cj = run(BASE / 'bin/solution-cj', inp, case / 'cj')
        equal = cpp['returncode'] == cj['returncode'] == 0 and cpp['stdout_sha256'] == cj['stdout_sha256']
        rec = {'id': identity, 'path': str(path), 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'operations': n, 'cpp': cpp, 'cj': cj, 'stdout_equal': equal}
        if not equal:
            a = (case/'cpp.stdout').read_bytes().splitlines(); b = (case/'cj.stdout').read_bytes().splitlines()
            first = next((k for k, (x,y) in enumerate(zip(a,b)) if x != y), min(len(a),len(b)))
            rec['first_mismatch_operation'] = first + 1
            rec['cpp_answer'] = str(a[first:first+1]); rec['cj_answer'] = str(b[first:first+1])
            print('MISMATCH', json.dumps(rec), flush=True)
        records.append(rec)
        (out/'results.json').write_text(json.dumps({'preloaded_diagnostic_only': True, 'cases': records},indent=2)+'\n')
        if not equal: return 1
        if i % 20 == 0 or i == len(paths)-1:
            print(f'{i+1}/{len(paths)} byte-identical, last {identity}, CJ diagnostic CPU {cj["cpu_s"]:.3f}s', flush=True)
    return 0

if __name__ == '__main__': raise SystemExit(main())
