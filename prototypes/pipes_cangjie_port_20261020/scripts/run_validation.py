#!/usr/bin/env python3
"""Sequential paired official-interactor validation and process resource data."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import time

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
spec = importlib.util.spec_from_file_location('pipes_harness', ROOT/'tools/pipes_harness.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='official')
    ap.add_argument('--test', type=Path)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--resume', action='store_true')
    args = ap.parse_args()
    tests = sorted((ROOT/'prototypes/pipes_online_patterns_20261020/release/tests').rglob('*.in'))
    tests += sorted((BASE/'fresh_tests').glob('*.in'))
    if args.test: tests = [args.test.resolve()]
    elif args.limit: tests = tests[:args.limit]
    out = BASE / args.out
    out.mkdir(parents=True,exist_ok=True)
    result_path = out/'results.json'
    if result_path.exists() and not args.resume:
        raise SystemExit('Choose a new --out or --resume to preserve results.')
    os.environ['cjProcessorNum'] = '1'
    # No heap/GC environment override: those constraints are part of solution.cj.
    assert not any(k in os.environ for k in ['cjHeapSize','cjGCThreshold','cjGCInterval'])
    binaries = {k: BASE/'bin'/('solution-' + k) for k in ['cpp','cj']}
    hashes = {k: sha(p) for k,p in binaries.items()}
    data = {'measurement':'official interactive protocol, process user+system CPU; one solver at a time',
            'host': platform.platform(), 'machine': platform.machine(),
            'hard_cpu_affinity':False, 'native_windows_tested':False,
            'runtime_environment':{'cjProcessorNum':'1'},
            'cpu_limit_s':5, 'memory_limit_mib':256,
            'binary_sha256':hashes, 'interactor_sha256':sha(ROOT/'tools/interactor'),
            'source_manifest':json.loads((BASE/'release/source_manifest.json').read_text()),
            'created_unix':time.time(), 'cases':[]}
    if args.resume:
        data = json.loads(result_path.read_text())
        assert hashes == data['binary_sha256'], 'Binaries changed; use new output.'
    done = {r['id'] for r in data['cases']}
    for i,path in enumerate(tests):
        group = 'fresh' if path.parent == BASE/'fresh_tests' else path.parent.name
        identity = group + '/' + path.stem
        if identity in done: continue
        assert hashes == {k:sha(p) for k,p in binaries.items()}
        pair = {'id':identity, 'group':group, 'input_sha256':sha(path), 'test':str(path)}
        for name in (['cpp','cj'] if i%2 == 0 else ['cj','cpp']):
            record = harness.run_case([str(binaries[name])], ROOT/'tools/interactor', path,
                                      out/'runs'/identity/name, 10.0, 240.0)
            record['response_sha256'] = sha(Path(record['judge_output_file']))
            record['within_limits'] = (record['solver_cpu_total_s'] is not None and record['solver_cpu_total_s'] < 5
                                      and record['solver_peak_rss_mb'] is not None and record['solver_peak_rss_mb'] < 256)
            pair[name] = record
        pair['answers_equal'] = pair['cpp']['response_sha256'] == pair['cj']['response_sha256']
        pair['kpi_equal'] = pair['cpp']['kpi'] == pair['cj']['kpi']
        pair['passed'] = all(pair[k]['status']=='ok' and pair[k]['within_limits'] for k in ['cpp','cj']) and pair['answers_equal'] and pair['kpi_equal']
        data['cases'].append(pair)
        result_path.write_text(json.dumps(data,indent=2)+'\n')
        a,b = pair['cpp'], pair['cj']
        if i%10 == 0 or not pair['passed'] or i==len(tests)-1:
            print(f'{i+1}/{len(tests)} {identity} equal={pair["answers_equal"]} '
                  f'CPU C++={a["solver_cpu_total_s"]} CJ={b["solver_cpu_total_s"]} '
                  f'RSS C++={a["solver_peak_rss_mb"]} CJ={b["solver_peak_rss_mb"]} pass={pair["passed"]}',flush=True)
        if a['status']!='ok' or b['status']!='ok' or not pair['answers_equal']:
            raise SystemExit('Protocol/parity failure: investigate before continuing.')
    print('DONE',len(data['cases']),'pairs; passed',sum(x['passed'] for x in data['cases']),flush=True)

if __name__=='__main__':main()
