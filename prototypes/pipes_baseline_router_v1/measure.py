#!/usr/bin/env python3
"""Fixed-budget same-suffix labels with real baseline continuation."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['pilot','train','calibration','dagger'])
    parser.add_argument('--binary',default=str(ROOT/'bin/label_baseline'))
    parser.add_argument('--tag',default='')
    parser.add_argument('--model-header')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    split='calibration' if args.stage=='calibration' else 'train'
    entries=manifest['artifacts'][split]['files']
    if args.stage in ['pilot','dagger']:
        counts={};selected=[]
        for entry in entries:
            family=entry['family_id'];counts.setdefault(family,0)
            if counts[family]<(2 if args.stage=='dagger' else 1):
                selected.append(entry);counts[family]+=1
        entries=selected
    label=args.stage+('_'+args.tag if args.tag else '')
    if args.stage=='dagger' and not args.model_header:raise ValueError('DAgger requires exact model-header snapshot')
    output=ROOT/'data/labels'/label;output.mkdir(parents=True,exist_ok=False)
    max_states=24 if args.stage=='pilot' else 32
    rollin='model' if args.stage=='dagger' else 'baseline'
    binary=Path(args.binary).resolve()

    def collect(entry):
        stream=split+'_'+Path(entry['file']).stem
        path=ROOT/'data'/split/entry['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
        command=[str(binary),'label',str(path),str(output/(stream+'.csv')),stream,str(max_states),rollin,'64']
        begin=time.monotonic();result=subprocess.run(command,text=True,capture_output=True)
        if result.returncode:raise RuntimeError(stream+' '+result.stderr[-2000:])
        record=json.loads(result.stdout)
        record.update(family=entry['family_id'],input_sha256=entry['sha256'],command=command,wall_s=time.monotonic()-begin)
        (output/(stream+'.json')).write_text(json.dumps(record,indent=2)+'\n');return record

    records=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(collect,e) for e in entries]):
            records.append(future.result())
            if len(records)%8==0 or len(records)==len(entries):print(args.stage,len(records),'/',len(entries),flush=True)
    records.sort(key=lambda r:r['stream']);aggregate=ROOT/'data'/(label+'_labels.csv')
    with aggregate.open('w') as dest:
        for i,record in enumerate(records):
            with (output/(record['stream']+'.csv')).open() as src:
                header=src.readline()
                if i==0:dest.write(header)
                for line in src:dest.write(line)
    groups={}
    for row in csv.DictReader(aggregate.open()):
        key=(row['stream'],row['state']);group=groups.setdefault(key,{'base':int(row['base_trench']),'outcomes':[]})
        group['outcomes'].append(int(row['target_trench']))
    gains=[v['base']-min(v['outcomes']) for v in groups.values()]
    report={'stage':args.stage,'records':records,'streams':len(records),'states':len(groups),
        'rows':sum(len(v['outcomes']) for v in groups.values()),'gain_ge20_states':sum(g>=20 for g in gains),
        'mean_one_action_hindsight_gain_m':statistics.mean(gains) if gains else 0,
        'median_one_action_hindsight_gain_m':statistics.median(gains) if gains else 0,
        'mean_uniform_random_regret_m':statistics.mean(statistics.mean(v['outcomes'])-min(v['outcomes']) for v in groups.values()) if gains else 0,
        'suffix_commands':sum(r['suffix_commands'] for r in records),
        'protected_branch_calls':sum(r['protected_branch_calls'] for r in records),
        'sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/baseline_fork.hpp','src/router_members.inc','src/engine.cpp']},
        'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
        'labels_sha256':hashlib.sha256(aggregate.read_bytes()).hexdigest(),
        'model_header_sha256':hashlib.sha256(Path(args.model_header).read_bytes()).hexdigest() if args.model_header else None,
        'interpretation':'One forced local route, exact real suffix, original complete baseline continuation; conditional hindsight, not achievable or additive rollout gain.'}
    (ROOT/'reports'/(label+'_measurement.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['records','sha256']},indent=2),flush=True)


if __name__=='__main__':main()
