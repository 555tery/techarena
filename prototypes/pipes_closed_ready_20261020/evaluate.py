"""Frozen three-way full-stream comparison; one interactive solver at a time."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('official_harness', ROOT/'tools/pipes_harness.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
NAMES = ['online', 'full', 'hybrid']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cases(group):
    if group == 'open15':
        return [dict(id=f'open{i:02}', path=ROOT/f'data/pipes/open/{i}.in',
                     family=f'open{i:02}', stratum='open') for i in range(1, 16)]
    directory = HERE/'evaluation'/group
    manifest = json.loads((directory/'manifest.json').read_text())
    rows = manifest.get('cases', manifest.get('tests'))
    result = []
    for row in rows:
        path = directory/row.get('file', row.get('filename', row.get('input_file', '')))
        assert sha(path) == row['sha256'], path
        result.append(dict(row, path=path))
    return result


def screen(binary, path):
    """Bulk stdin is a score screen, never an interactive-protocol claim."""
    meta = h.parse_test(path)
    tokens = path.read_text().split()
    commands = list(map(int, tokens[2:2+int(tokens[1])]))
    p = subprocess.run(['/usr/bin/time', '-l', '-p', str(binary)],
                       input='\n'.join(map(str, commands+[0]))+'\n',
                       text=True, capture_output=True, timeout=90)
    assert p.returncode == 0, (path, p.returncode, p.stderr[-2000:])
    lines = p.stdout.splitlines()
    assert len(lines) == len(commands), (path, len(lines), len(commands))
    cells = bytearray()
    pipes = [None]
    trench = 0
    for command, line in zip(commands, lines):
        values = list(map(int, line.split()))
        if command > 0:
            assert len(values) == 2
            digs, x = values
            assert digs >= 0 and x >= 0
            trench += 20*digs
            assert x+command <= trench <= 100000000
            if trench > len(cells):
                cells.extend(b'\0'*(trench-len(cells)))
            assert not any(cells[x:x+command]), (path, command, x)
            cells[x:x+command] = b'\1'*command
            pipes.append((x, command))
        else:
            x, length = pipes[-command]
            assert values == [x] and length > 0 and all(cells[x:x+length])
            cells[x:x+length] = b'\0'*length
            pipes[-command] = (x, 0)
    user = re.search(r'^user\s+(\S+)', p.stderr, re.M)
    system = re.search(r'^sys\s+(\S+)', p.stderr, re.M)
    rss = re.search(r'(\d+)\s+maximum resident set size', p.stderr)
    assert trench > 0 and user and system and rss
    meta.update(status='ok', kpi=meta['final_occupied_length_m']/trench,
                trench_length_m=trench, candidate_stderr=p.stderr,
                solver_cpu_total_s=float(user[1])+float(system[1]),
                solver_peak_rss_mb=int(rss[1])/1048576,
                validation='bulk stdin; full occupancy check; not interactive protocol validation')
    return meta


def verify_freeze(group):
    frozen = json.loads((HERE/'candidates-freeze.json').read_text())
    for name in NAMES:
        for key, leaf in [('source_sha256', 'solution.cpp'), ('binary_sha256', 'solver')]:
            assert sha(HERE/'candidates'/name/leaf) == frozen['candidates'][name][key]
    assert sha(ROOT/'tools/pipes_harness.py') == frozen['harness_sha256']
    assert sha(ROOT/'tools/interactor') == frozen['interactor_sha256']
    if group != 'open15':
        assert sha(HERE/'evaluation'/group/'manifest.json') == frozen['manifests'][group]
    if group == 'final':
        decision = json.loads((HERE/'selection-freeze.json').read_text())
        assert decision['candidates_freeze_sha256'] == sha(HERE/'candidates-freeze.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('group', choices=['calibration', 'final', 'open15', 'stress'])
    ap.add_argument('--mode', choices=['screen', 'official'], default='screen')
    ap.add_argument('--names', default=','.join(NAMES))
    ap.add_argument('--ids')
    args = ap.parse_args()
    verify_freeze(args.group)
    selected = cases(args.group)
    if args.ids:
        selected = [c for c in selected if c['id'] in args.ids.split(',')]
    records = []
    for case in selected:
        for name in args.names.split(','):
            binary = HERE/'candidates'/name/'solver'
            source = binary.with_name('solution.cpp')
            dest = HERE/'measurements'/args.mode/args.group/name/case['id']
            dest.mkdir(parents=True, exist_ok=True)
            record = dest/'record.json'
            if record.exists():
                r = json.loads(record.read_text())
                assert r['binary_sha256'] == sha(binary) and r['test_sha256'] == sha(case['path'])
            else:
                started = time.time()
                try:
                    r = (screen(binary, case['path']) if args.mode == 'screen'
                         else h.run_case([str(binary)], ROOT/'tools/interactor',
                                         case['path'], dest, 5, 240))
                except Exception as exc:
                    r = {'status': 'evaluation_error', 'detail': repr(exc),
                         'solver_cpu_total_s': None, 'solver_peak_rss_mb': None,
                         'kpi': None, 'candidate_stderr': ''}
                r.update(id=case['id'], strategy=name, family=case['family'],
                         stratum=case['stratum'], source_path=str(case['path']),
                         test_sha256=sha(case['path']), binary_sha256=sha(binary),
                         source_sha256=sha(source), started_at_unix=started,
                         mode=args.mode)
                r['resources_ok'] = (r['solver_cpu_total_s'] is not None and
                                     r['solver_peak_rss_mb'] is not None and
                                     r['solver_cpu_total_s'] < 5 and r['solver_peak_rss_mb'] < 256)
                record.write_text(json.dumps(r, indent=2)+'\n')
            if args.mode == 'official' and r['status'] == 'ok':
                previous = HERE/'measurements/screen'/args.group/name/case['id']/'record.json'
                if previous.exists():
                    old = json.loads(previous.read_text())
                    assert old['binary_sha256'] == r['binary_sha256']
                    assert old['trench_length_m'] == r['trench_length_m'], (case['id'], name, 'non-deterministic score')
            records.append(r)
            print(case['id'], name, r['status'], r.get('kpi'),
                  r['solver_cpu_total_s'], r['solver_peak_rss_mb'], flush=True)
    verify_freeze(args.group)
    out = dict(group=args.group, mode=args.mode, records=records,
               source_freeze_sha256=sha(HERE/'candidates-freeze.json'),
               platform_actions=0, workers=1, host='macOS arm64, not Windows/G5420')
    suffix = '-'+args.names.replace(',', '-') if args.names != ','.join(NAMES) else ''
    if args.ids:
        suffix += '-subset'
    (HERE/f'{args.mode}-{args.group}{suffix}.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(dict(n=len(records), invalid=sum(r['status'] != 'ok' for r in records),
                          resource_failures=sum(not r['resources_ok'] for r in records))), flush=True)


if __name__ == '__main__':
    main()
