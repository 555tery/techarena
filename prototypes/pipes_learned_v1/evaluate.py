#!/usr/bin/env python3
"""One frozen local comparison; no platform/API/network integration."""
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def bootstrap_family(values):
    rng=random.Random(81735999)
    draws=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(20000))
    return [draws[499],draws[19499]]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['final','open15'])
    args=parser.parse_args()
    frozen=json.loads((ROOT/'reports/model_freeze.json').read_text())
    for name,digest in frozen['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    output=ROOT/'reports'/('evaluation_'+args.phase)
    output.mkdir(exist_ok=False)
    tests=ROOT/'data/final_validation' if args.phase=='final' else PROJECT/'data/pipes/open'
    solvers={'old_baseline':ROOT/'bin/old_baseline','generic':ROOT/'bin/generic','learned':ROOT/'bin/learned'}

    def run(name,binary):
        command=[sys.executable,str(PROJECT/'tools/pipes_harness.py'),'--solver',str(binary),
                 '--name','learned-v1-'+args.phase+'-'+name,'--tests',str(tests),
                 '--out',str(output/name),'--cpu-limit','5','--memory-limit-mb','256','--wall-timeout','180']
        result=subprocess.run(command,cwd=PROJECT,capture_output=True,text=True)
        (output/(name+'_stdout.txt')).write_text(result.stdout)
        (output/(name+'_stderr.txt')).write_text(result.stderr)
        (output/(name+'_command.json')).write_text(json.dumps(command,indent=2)+'\n')
        # Failed protocol/resource cases are still reported, never discarded.
        if not (output/name/'cases.csv').exists():raise RuntimeError(result.stderr[-2000:])
        rows={r['case']:r for r in csv.DictReader((output/name/'cases.csv').open())}
        print(args.phase,name,'finished',sum(r['status']=='ok' for r in rows.values()),'/',len(rows),flush=True)
        return name,rows

    runs={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run,name,binary) for name,binary in solvers.items()]):
            name,rows=future.result();runs[name]=rows
    assert runs['generic'].keys()==runs['learned'].keys()==runs['old_baseline'].keys()
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    family_by_case={}
    if args.phase=='final':
        for r in manifest['artifacts']['final_validation']['files']:
            family_by_case[Path(r['file']).stem]=r['family_id']
        assert set(family_by_case)==set(runs['learned']), 'final manifest coverage'
        assert len(family_by_case)==24 and len(set(family_by_case.values()))==8
    pairs=[]
    for key in runs['learned']:
        r={name:rows[key] for name,rows in runs.items()}
        assert len({row['test_sha256'] for row in r.values()})==1
        pair={'case':key,'family':family_by_case[key] if args.phase=='final' else 'open15',
              'commands':int(r['learned']['operation_count']),
              'input_sha256':r['learned']['test_sha256']}
        for name,row in r.items():
            pair[name+'_trench_m']=int(row['trench_length_m']) if row['trench_length_m'] else None
            # A failed execution counts as zero rather than disappearing from
            # the paired comparison. Unknown trench/usage remains explicit.
            pair[name+'_status']=row['status']
            pair[name+'_cpu_s']=float(row['solver_cpu_total_s']) if row['solver_cpu_total_s'] else None
            pair[name+'_rss_mib']=float(row['solver_peak_rss_mb']) if row['solver_peak_rss_mb'] else None
            pair[name+'_qualified']=(row['status']=='ok' and pair[name+'_cpu_s'] is not None
                and pair[name+'_cpu_s']<5 and pair[name+'_rss_mib'] is not None and pair[name+'_rss_mib']<256)
            pair[name+'_kpi']=float(row['kpi'] or 0) if pair[name+'_qualified'] else 0.0
            pair[name+'_score']=float(row['weighted_score'] or 0) if pair[name+'_qualified'] else 0.0
        pair['delta_kpi_vs_generic']=pair['learned_kpi']-pair['generic_kpi']
        pair['delta_kpi_vs_old']=pair['learned_kpi']-pair['old_baseline_kpi']
        for control in ['generic','old_baseline']:
            label='generic' if control=='generic' else 'old'
            pair['delta_trench_vs_'+label]=(pair['learned_trench_m']-pair[control+'_trench_m']
                if pair['learned_qualified'] and pair[control+'_qualified'] and pair['learned_trench_m'] is not None and pair[control+'_trench_m'] is not None else None)
        pair['model_diagnostics']=r['learned']['candidate_stderr']
        pairs.append(pair)
    with (output/'comparison.csv').open('w') as out:
        writer=csv.DictWriter(out,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
    summary={'phase':args.phase,'pairs':pairs,'count':len(pairs),
             'correct_and_in_limits':all(p[name+'_qualified'] for p in pairs for name in solvers),
             'scores':{name:sum(p[name+'_score'] for p in pairs) for name in solvers},
             'max_cpu_s':{name:max((p[name+'_cpu_s'] for p in pairs if p[name+'_cpu_s'] is not None),default=None) for name in solvers},
             'max_rss_mib':{name:max((p[name+'_rss_mib'] for p in pairs if p[name+'_rss_mib'] is not None),default=None) for name in solvers}}
    if args.phase=='final':
        families={}
        for name in sorted(set(p['family'] for p in pairs)):
            selected=[p for p in pairs if p['family']==name]
            families[name]={metric:statistics.mean(p[metric] for p in selected) for metric in ['delta_kpi_vs_generic','delta_kpi_vs_old']}
        summary['families']=families
        for metric in ['delta_kpi_vs_generic','delta_kpi_vs_old']:
            values=[v[metric] for v in families.values()]
            summary[metric]={'family_macro_mean':statistics.mean(values),'family_cluster_bootstrap_95_ci':bootstrap_family(values)}
        summary['by_length']={str(n):{metric:statistics.mean(p[metric] for p in pairs if p['commands']==n) for metric in ['delta_kpi_vs_generic','delta_kpi_vs_old']} for n in sorted(set(p['commands'] for p in pairs))}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='pairs'},indent=2),flush=True)


if __name__=='__main__':main()
