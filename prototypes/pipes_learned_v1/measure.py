#!/usr/bin/env python3
"""Generate exact same-state/same-suffix action labels, offline only."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def run(stage, binary, entries, max_states, tag):
    label = stage + ('_' + tag if tag else '')
    output = ROOT / 'data' / 'labels' / label
    output.mkdir(parents=True, exist_ok=False)
    split = 'calibration' if stage == 'calibration' else 'train'

    def collect(entry):
        stream = ('dagger_' if stage == 'dagger' else '') + Path(entry['file']).stem
        src = ROOT / 'data' / split / entry['file']
        assert hashlib.sha256(src.read_bytes()).hexdigest() == entry['sha256']
        rollin = 'model' if stage == 'dagger' else ('right' if (entry['replica_index'] // 2) % 2 else 'greedy')
        coverage = str(output / (stream + '_coverage.csv')) if stage == 'measurement' else '-'
        command = [str(binary), 'label', str(src), str(output / (stream + '.csv')), stream,
                   '64', str(max_states), rollin, coverage]
        begin = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        record = json.loads(result.stdout)
        record.update(family=entry['family_id'], input_sha256=entry['sha256'],
                      rollin=rollin, wall_s=time.monotonic() - begin, command=command)
        (output / (stream + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        return record

    records = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = [pool.submit(collect, entry) for entry in entries]
        for future in as_completed(pending):
            record = future.result()
            records.append(record)
            if len(records) % 8 == 0 or len(records) == len(entries):
                print(stage, len(records), '/', len(entries), 'states', sum(r['states'] for r in records), flush=True)
    records.sort(key=lambda r: r['stream'])
    aggregate = ROOT / 'data' / (label + '_labels.csv')
    with aggregate.open('w') as out:
        wrote_header = False
        for record in records:
            path = output / (record['stream'] + '.csv')
            with path.open() as src:
                header = src.readline()
                if not wrote_header:
                    out.write(header)
                    wrote_header = True
                for line in src:
                    out.write(line)
    states = []
    with aggregate.open() as src:
        for row in csv.DictReader(src):
            key = (row['stream'], row['state'])
            if not states or states[-1]['key'] != key:
                states.append({'key': key, 'base': int(row['base_trench']), 'outcomes': []})
            states[-1]['outcomes'].append(int(row['target_trench']))
    gains = [r['base'] - min(r['outcomes']) for r in states]
    random_regrets = [statistics.mean(r['outcomes']) - min(r['outcomes']) for r in states]
    report = {'stage': stage, 'records': records, 'streams': len(records), 'states': len(states),
              'rows': sum(len(r['outcomes']) for r in states),
              'gain_ge20_states': sum(g >= 20 for g in gains),
              'mean_single_action_hindsight_gain_m': statistics.mean(gains) if gains else 0,
              'median_single_action_hindsight_gain_m': statistics.median(gains) if gains else 0,
              'mean_uniform_random_action_regret_m': statistics.mean(random_regrets) if states else 0,
              'suffix_commands': sum(r['suffix_commands'] for r in records),
              'source_sha256': hashlib.sha256((ROOT / 'src/engine.cpp').read_bytes()).hexdigest(),
              'kernel_sha256': hashlib.sha256((ROOT / 'src/allocator.hpp').read_bytes()).hexdigest(),
              'labels_sha256': hashlib.sha256(aggregate.read_bytes()).hexdigest(),
              'caveat': 'Hindsight one-action deviations with fixed greedy continuation. Gains cannot be added or claimed as an online score.'}
    (ROOT / 'reports' / (label + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['measurement', 'train', 'calibration', 'dagger'])
    parser.add_argument('--binary', type=Path, default=ROOT / 'bin/engine')
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    split = 'calibration' if args.stage == 'calibration' else 'train'
    entries = manifest['artifacts'][split]['files']
    if args.stage in ['measurement', 'dagger']:
        grouped = {}
        for entry in entries:
            grouped.setdefault(entry['family_id'], []).append(entry)
        count = 1 if args.stage == 'measurement' else 4
        entries = [entry for family in sorted(grouped) for entry in grouped[family][:count]]
    run(args.stage, args.binary.resolve(), entries, 16 if args.stage == 'measurement' else 64,args.tag)
