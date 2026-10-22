#!/usr/bin/env python3
"""Paired full local rollouts, including a predeclared calibration safety gate."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]


def bootstrap(values):
    rng=random.Random(81735999)
    draws=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(20000))
    return [draws[499],draws[19499]]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['calibration','final','open15'])
    args=parser.parse_args();phase=args.phase
    frozen_name='candidate_snapshot.json' if phase=='calibration' else 'model_freeze.json'
    frozen=json.loads((ROOT/'reports'/frozen_name).read_text())
    for name,digest in frozen['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    split='final_validation' if phase=='final' else phase
    tests=PROJECT/'data/pipes/open' if phase=='open15' else ROOT/'data'/split
    output=ROOT/'reports'/('evaluation_'+phase);output.mkdir(exist_ok=False)
    solvers={name:ROOT/'bin'/name for name in ['old_baseline','instrumented','router_candidate']}

    def run(name,binary):
        command=[sys.executable,str(PROJECT/'tools/pipes_harness.py'),'--solver',str(binary),
            '--name','baseline-router-v1-'+phase+'-'+name,'--tests',str(tests),'--out',str(output/name),
            '--cpu-limit','5','--memory-limit-mb','256','--wall-timeout','180']
        result=subprocess.run(command,cwd=PROJECT,capture_output=True,text=True)
        (output/(name+'_stdout.txt')).write_text(result.stdout)
        (output/(name+'_stderr.txt')).write_text(result.stderr)
        (output/(name+'_command.json')).write_text(json.dumps(command,indent=2)+'\n')
        path=output/name/'cases.csv'
        if not path.exists():raise RuntimeError(result.stderr[-2000:])
        rows={r['case']:r for r in csv.DictReader(path.open())}
        print(phase,name,'finished',len(rows),flush=True);return name,rows

    runs={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run,n,b) for n,b in solvers.items()]):
            name,rows=future.result();runs[name]=rows
    keys=set(runs['old_baseline'])
    assert all(set(rows)==keys for rows in runs.values())
    family_map={}
    if phase!='open15':
        entries=manifest['artifacts'][split]['files']
        family_map={Path(e['file']).stem:e['family_id'] for e in entries}
        assert set(family_map)==keys and len(set(family_map.values()))==8
        assert len(keys)==(24 if phase=='final' else 16)
        for entry in entries:
            assert runs['old_baseline'][Path(entry['file']).stem]['test_sha256']==entry['sha256']
    pairs=[]
    for key in sorted(keys):
        raw={name:rows[key] for name,rows in runs.items()}
        assert len({row['test_sha256'] for row in raw.values()})==1
        pair={'case':key,'family':family_map[key] if family_map else 'open15',
            'commands':int(raw['old_baseline']['operation_count']),'input_sha256':raw['old_baseline']['test_sha256']}
        for name,row in raw.items():
            cpu=float(row['solver_cpu_total_s']) if row['solver_cpu_total_s'] else None
            rss=float(row['solver_peak_rss_mb']) if row['solver_peak_rss_mb'] else None
            qualified=row['status']=='ok' and cpu is not None and cpu<5 and rss is not None and rss<256
            pair.update({name+'_status':row['status'],name+'_qualified':qualified,name+'_cpu_s':cpu,name+'_rss_mib':rss,
                name+'_trench_m':int(row['trench_length_m']) if row['trench_length_m'] else None,
                name+'_kpi':float(row['kpi'] or 0) if qualified else 0.0,
                name+'_score':float(row['weighted_score'] or 0) if qualified else 0.0})
        pair['delta_kpi']=pair['router_candidate_kpi']-pair['old_baseline_kpi']
        pair['delta_trench_m']=(pair['router_candidate_trench_m']-pair['old_baseline_trench_m']
            if pair['router_candidate_qualified'] and pair['old_baseline_qualified'] else None)
        pair['router_diagnostics']=raw['router_candidate']['candidate_stderr']
        pair['instrumented_objective_matches_baseline']=(pair['old_baseline_status']==pair['instrumented_status']
            and pair['old_baseline_trench_m']==pair['instrumented_trench_m'] and pair['old_baseline_kpi']==pair['instrumented_kpi'])
        pairs.append(pair)
    with (output/'comparison.csv').open('w') as out:
        writer=csv.DictWriter(out,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
    summary={'phase':phase,'pairs':pairs,'count':len(pairs),
        'correct_and_in_limits':all(p[n+'_qualified'] for p in pairs for n in solvers),
        'instrumented_matches_baseline':all(p['instrumented_objective_matches_baseline'] for p in pairs),
        'scores':{n:sum(p[n+'_score'] for p in pairs) for n in solvers},
        'max_cpu_s':{n:max((p[n+'_cpu_s'] for p in pairs if p[n+'_cpu_s'] is not None),default=None) for n in solvers},
        'max_rss_mib':{n:max((p[n+'_rss_mib'] for p in pairs if p[n+'_rss_mib'] is not None),default=None) for n in solvers},
        'wins':sum(p['delta_kpi']>0 for p in pairs),'losses':sum(p['delta_kpi']<0 for p in pairs),'ties':sum(p['delta_kpi']==0 for p in pairs)}
    if phase!='open15':
        families={f:statistics.mean(p['delta_kpi'] for p in pairs if p['family']==f) for f in sorted(set(family_map.values()))}
        summary.update(families=families,family_macro_mean_kpi_delta=statistics.mean(families.values()),
            family_cluster_bootstrap_95_ci=bootstrap(list(families.values())),
            by_length={str(n):statistics.mean(p['delta_kpi'] for p in pairs if p['commands']==n) for n in sorted({p['commands'] for p in pairs})})
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='pairs'},indent=2),flush=True)


if __name__=='__main__':main()
