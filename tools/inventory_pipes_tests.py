#!/usr/bin/env python3
"""Inventory legal saved Pipes streams, including release ZIP copies.

Read-only with respect to tests and archives. Canonical identity excludes
weight, whitespace and the optional terminal zero. No solvers are executed.
"""
import argparse
from array import array
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = ['**/.git/**', '**/toolchain/**', '**/.venv/**', '**/venv/**',
           '**/node_modules/**', '**/site-packages/**', '**/upstream/**',
           '**/headless-upstream/**', '**/vendor/**', '**/local-deps/**']
DATA_DIRS = {'tests', 'test', 'inputs', 'input', 'data', 'corpus',
             'evaluation', 'generated', 'bases'}
NOT_INPUT_NAMES = {'judge_output.txt', 'score.txt', 'unused_answer.txt',
                   'interactor_report.txt', 'freeze_id.txt'}
INTEGER = re.compile(rb'[+-]?[0-9]+\Z')

def input_name(path):
    path = Path(path)
    if path.suffix.lower() in ('.in', '.input'):
        return True
    return (path.suffix.lower() == '.txt' and path.name not in NOT_INPUT_NAMES
            and 'stderr' not in path.name and 'stdout' not in path.name
            and any(part.lower() in DATA_DIRS for part in path.parts))

def parse(raw):
    tokens = raw.split()
    if len(tokens) < 2:
        raise ValueError('missing_header')
    try:
        weight = float(tokens[0])
    except ValueError:
        raise ValueError('invalid_weight')
    if not math.isfinite(weight) or weight < 0:
        raise ValueError('invalid_weight')
    if not INTEGER.fullmatch(tokens[1]):
        raise ValueError('invalid_count_token')
    n = int(tokens[1])
    if not 1 <= n <= 200000:
        raise ValueError('count_outside_1_200000')
    if len(tokens) == n + 3 and tokens[-1] == b'0':
        tokens.pop()
    if len(tokens) != n + 2:
        raise ValueError('declared_count_mismatch')
    lengths = [0]
    live = peak = active = peak_count = 0
    commands = array('i')
    assert commands.itemsize == 4
    for token in tokens[2:]:
        if not INTEGER.fullmatch(token):
            raise ValueError('non_integer_command')
        command = int(token)
        if command > 0:
            if command > 40:
                raise ValueError('pipe_length_outside_1_40')
            lengths.append(command)
            live += command
            active += 1
            peak = max(peak, live)
            peak_count = max(peak_count, active)
        else:
            pid = -command
            if pid <= 0 or pid >= len(lengths) or lengths[pid] == 0:
                raise ValueError('invalid_or_repeated_deletion')
            live -= lengths[pid]
            lengths[pid] = 0
            active -= 1
        commands.append(command)
    if sys.byteorder != 'little':
        commands.byteswap()
    digest = hashlib.sha256(struct.pack('<I', n) + commands.tobytes()).hexdigest()
    lower = 20 * ((peak + 19) // 20)
    # Append-only placement always fits below the official100,000,000m cap:
    # at most200,000 additions of <=40m, each rounded independently to20m.
    assert 40 * (len(lengths) - 1) <= 100000000
    return {'canonical_sha256':digest, 'weight':weight, 'operations':n,
            'placements':len(lengths)-1, 'final_volume':live, 'peak_volume':peak,
            'peak_active_pipes':peak_count, 'minimum_trench_from_volume':lower,
            'KPI_volume_upper_bound':live/lower if lower else 0,
            'upper_bound_at_least_085':lower > 0 and 20*live >= 17*lower}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    listing = ['rg', '--files', '--hidden', '--no-ignore', '-g', '*.in',
               '-g', '*.input', '-g', '*.txt', '-g', '*.zip']
    for pattern in EXCLUDE:
        listing += ['-g', '!' + pattern]
    paths = sorted(Path(p) for p in subprocess.check_output(listing,cwd=ROOT,text=True).splitlines()
                   if Path(p).suffix == '.zip' or input_name(p))
    raw_cache = {}
    unique = {}
    invalid = []
    origins = Counter()
    archives = []
    bytes_read = 0

    def accept(raw, origin, kind):
        nonlocal bytes_read
        bytes_read += len(raw)
        origins[kind] += 1
        raw_hash = hashlib.sha256(raw).hexdigest()
        if raw_hash not in raw_cache:
            try:
                raw_cache[raw_hash] = parse(raw)
            except (ValueError, OverflowError) as error:
                raw_cache[raw_hash] = {'error':str(error)}
        record = raw_cache[raw_hash]
        if 'error' in record:
            invalid.append({'path':origin, 'raw_sha256':raw_hash, 'reason':record['error']})
            return
        digest = record['canonical_sha256']
        if digest not in unique:
            unique[digest] = {**record, 'origins':[], 'raw_sha256s':[], 'weights':[]}
            unique[digest].pop('weight')
        target = unique[digest]
        target['origins'].append(origin)
        if raw_hash not in target['raw_sha256s']:
            target['raw_sha256s'].append(raw_hash)
        if record['weight'] not in target['weights']:
            target['weights'].append(record['weight'])

    for index, path in enumerate(paths):
        if path.suffix == '.zip':
            if not zipfile.is_zipfile(ROOT/path):
                archives.append({'path':str(path),'error':'file_with_zip_extension_is_not_a_zip',
                                 'bytes':(ROOT/path).stat().st_size})
                continue
            with zipfile.ZipFile(ROOT/path) as archive:
                members = [info for info in archive.infolist() if not info.is_dir()
                           and input_name(info.filename)
                           and not any(part in info.filename.split('/') for part in
                                       ['node_modules','toolchain','.venv','vendor','upstream'])]
                archives.append({'path':str(path),'input_members':len(members)})
                for info in members:
                    accept(archive.read(info),str(path)+'!'+info.filename,'zip_member')
        elif input_name(path):
            accept((ROOT/path).read_bytes(),str(path),'file')
        if (index + 1) % 1000 == 0:
            print('Indexed', index+1, 'paths;',len(unique),'unique legal streams',flush=True)

    records = sorted(unique.values(),key=lambda row:row['origins'][0])
    selected = [row for row in records if row['upper_bound_at_least_085']]
    (args.out/'unique_tests.json').write_text(json.dumps(records,indent=2)+'\n')
    (args.out/'invalid_files.json').write_text(json.dumps(invalid,indent=2)+'\n')
    (args.out/'selected_085.json').write_text(json.dumps(selected,indent=2)+'\n')
    prefixes = {'open15':'data/pipes/open/',
        'current339':'prototypes/pipes_cangjie_port_20261020/release/tests/',
        'previous307':'prototypes/pipes_online_patterns_20261020/release/tests/',
        'fresh32':'prototypes/pipes_cangjie_port_20261020/fresh_tests/'}
    subsets = {}
    for key,prefix in prefixes.items():
        rows = [r for r in records if any(x.startswith(prefix) and '!' not in x for x in r['origins'])]
        subsets[key]={'unique_valid':len(rows),'upper_bound_at_least_085':sum(r['upper_bound_at_least_085'] for r in rows)}
    archive_only = [r for r in records if all('!' in p for p in r['origins'])]
    summary = {'generated_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'saved Pipes .in/.input and dataset .txt files plus matching members of project ZIP archives; third-party/SDK trees excluded',
        'root':str(ROOT), 'input_objects_checked':sum(origins.values()),
        'origins':dict(origins),'bytes_read':bytes_read,'distinct_raw_files':len(raw_cache),
        'unique_valid_streams':len(records),'unique_upper_bound_at_least_085':len(selected),
        'unique_below_085':len(records)-len(selected),
        'invalid_input_objects':len(invalid),'invalid_reasons':dict(Counter(r['reason'] for r in invalid)),
        'archive_only_unique':len(archive_only),'archive_only_selected':sum(r['upper_bound_at_least_085'] for r in archive_only),
        'deduplication':'SHA256 of uint32 little-endian N followed by int32 little-endian commands; ignores weights, whitespace and optional final0',
        'criteria':'1<=N<=200000; integer positive lengths1..40; only active existing PIDs deleted; finite nonnegative weight; exact command count',
        'threshold':'F / (20*ceil(peak_live_volume/20)) >=17/20, compared using exact integers',
        'caveat':'volume upper bound is not a proved achievable offline optimum',
        'subsets':subsets,'archives':archives,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'solvers_executed':0}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='archives'},indent=2),flush=True)

if __name__ == '__main__':
    main()
