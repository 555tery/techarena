"""Paired descriptive analysis; never fits or selects a solver."""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parent
LABELS = ('trial22', 'bf', 'ss')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mean(values):
    values = list(values)
    return statistics.fmean(values) if values else None


def bootstrap(rows, left, right):
    # Five stopping points belong to one base; do not resample them as five
    # independent experiments. Fixed family mechanisms remain stratified.
    clusters = defaultdict(lambda: defaultdict(list))
    for row in rows:
        clusters[row['family']][row['base_id']].append(row[left]['kpi'] - row[right]['kpi'])
    families = [[mean(x) for x in bases.values()] for bases in clusters.values()]
    rng = random.Random(2026101901)
    samples = []
    for _ in range(10000):
        samples.append(mean(mean(rng.choices(values, k=len(values))) for values in families))
    samples.sort()
    return {'low': samples[249], 'high': samples[9749], 'replicates': len(samples),
            'method': '95% percentile bootstrap; base streams within fixed family strata',
            'scope': 'conditional on these 12 constructed families; not uncertainty over hidden tests'}


def summarize(rows):
    output = {'inputs': len(rows), 'bases': len({r['base_id'] for r in rows}), 'algorithms': {}, 'pairs': {}}
    for label in LABELS:
        output['algorithms'][label] = {
            'mean_F_over_T': mean(r[label]['kpi'] for r in rows),
            'mean_T_over_H0': mean(r[label]['trench_length_m'] / r['H0'] for r in rows if r['H0']),
            'mean_excess_m': mean(r[label]['trench_length_m'] - r['H0'] for r in rows),
            'max_excess_ratio': max(r[label]['trench_length_m'] / r['H0'] - 1 for r in rows if r['H0']),
            'max_cpu_s': max(r[label]['solver_cpu_total_s'] for r in rows),
            'max_rss_mib': max(r[label]['solver_peak_rss_mb'] for r in rows),
        }
    for left, right in (('trial22','bf'), ('ss','bf'), ('trial22','ss')):
        delta = [r[left]['kpi'] - r[right]['kpi'] for r in rows]
        dt = [r[right]['trench_length_m'] - r[left]['trench_length_m'] for r in rows]
        ordered = sorted(rows, key=lambda r: r[left]['kpi'] - r[right]['kpi'])
        output['pairs'][left+'_minus_'+right] = {
            'mean_delta_F_over_T': mean(delta),
            'wins_losses_ties_F_over_T': [sum(d > 1e-12 for d in delta), sum(d < -1e-12 for d in delta), sum(abs(d) <= 1e-12 for d in delta)],
            'wins_losses_ties_trench': [sum(d > 0 for d in dt), sum(d < 0 for d in dt), sum(d == 0 for d in dt)],
            'worst_delta': min(delta), 'best_delta': max(delta),
            'worst_cases': [{'case':r['case'], 'family':r['family'], 'stop':r['stop_fraction'],
                             'delta':r[left]['kpi']-r[right]['kpi'],
                             'extra_m':r[left]['trench_length_m']-r[right]['trench_length_m'],
                             'F':r['F'], 'H0':r['H0']} for r in ordered[:5]],
        }
    return output


def main():
    metadata = json.loads((ROOT/'data/case-index.json').read_text())
    records = {}
    for label in LABELS:
        path = ROOT/'evaluations/final'/label
        batch = json.loads((path/'manifest.json').read_text())
        assert batch['correct'] and batch['case_count'] == 240
        records[label] = {r['case']:r for r in json.loads((path/'harness/summary.json').read_text())['records']}
        assert set(records[label]) == set(metadata)
    rows = []
    for case, meta in sorted(metadata.items()):
        row = dict(meta, case=case)
        for label in LABELS:
            record = records[label][case]
            assert record['test_sha256'] == meta['sha256'] == sha(record['test_file'])
            assert record['occupied_length_m'] == meta['F']
            assert record['minimum_trench_lower_bound_m'] == meta['H0']
            assert record['status'] == 'ok'
            assert record['kpi'] == meta['F'] / record['trench_length_m']
            row[label] = record
        rows.append(row)
    result = {'overall': summarize(rows), 'families': {}, 'stops': {}, 'scales': {}, 'lengths': {},
              'occupancy': {'mean_F_over_peak':mean(r['F']/r['peak'] for r in rows),
                            'min_F_over_peak':min(r['F']/r['peak'] for r in rows),
                            'max_F_over_peak':max(r['F']/r['peak'] for r in rows),
                            'F_zero_count':sum(r['F']==0 for r in rows),
                            'below_20pct_peak':sum(r['F'] < .2*r['peak'] for r in rows),
                            'above_95pct_peak':sum(r['F'] > .95*r['peak'] for r in rows)}}
    for field, target in [('family','families'), ('stop_fraction','stops'), ('scale','scales'), ('full_length','lengths')]:
        for value in sorted({r[field] for r in rows}, key=str):
            result[target][str(value)] = summarize([r for r in rows if r[field] == value])
    for left,right in [('trial22','bf'),('ss','bf'),('trial22','ss')]:
        result['overall']['pairs'][left+'_minus_'+right]['cluster_interval'] = bootstrap(rows,left,right)
    # Verify all shortened answer transcripts are literal prefixes of the full
    # answer transcript, without assuming byte sizes equal operation counts.
    prefix_checks = []
    for base_id in sorted({r['base_id'] for r in rows}):
        group = sorted([r for r in rows if r['base_id']==base_id], key=lambda r:r['stop_fraction'])
        full = group[-1]
        for label in LABELS:
            full_lines = Path(full[label]['judge_output_file']).read_bytes().splitlines()
            assert len(full_lines) == full['n']
            for short in group[:-1]:
                short_lines = Path(short[label]['judge_output_file']).read_bytes().splitlines()
                assert len(short_lines) == short['n']
                assert short_lines == full_lines[:short['n']], (base_id,label,short['case'],'noncausal prefix')
            prefix_checks.append({'base_id':base_id,'label':label,'four_prefixes_match':True})
    repeats = []
    for label in LABELS:
        report = json.loads((ROOT/'evaluations/repeat'/label/'harness/summary.json').read_text())
        assert report['case_count'] == report['ok_count'] == 4
        for record in report['records']:
            original = records[label][record['case']]
            assert record['test_sha256'] == original['test_sha256']
            assert record['kpi'] == original['kpi'] and record['trench_length_m']==original['trench_length_m']
            assert sha(record['judge_output_file']) == sha(original['judge_output_file'])
            repeats.append({'label':label,'case':record['case'],'identical_answers':True})
    result['verification'] = {'answer_prefix_groups':len(prefix_checks), 'short_prefix_checks':4*len(prefix_checks),
                              'repeat_runs':len(repeats), 'repeats':repeats}
    result['source_status'] = {label:json.loads((ROOT/'builds'/label/'manifest.json').read_text()) for label in LABELS}
    (ROOT/'results.json').write_text(json.dumps(result, ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'paired-cases.csv').open('w') as stream:
        names = ['case','family','base_id','replicate','stop_fraction','scale','full_length','n','F','peak','H0']
        names += [label+'_'+field for label in LABELS for field in ('T','F_over_T','cpu_s','rss_mib')]
        writer=csv.DictWriter(stream,fieldnames=names); writer.writeheader()
        for row in rows:
            flat={k:row[k] for k in names if k in row}
            for label in LABELS:
                flat.update({label+'_T':row[label]['trench_length_m'],label+'_F_over_T':row[label]['kpi'],
                             label+'_cpu_s':row[label]['solver_cpu_total_s'],label+'_rss_mib':row[label]['solver_peak_rss_mb']})
            writer.writerow(flat)
    print(json.dumps({'overall':result['overall'],'occupancy':result['occupancy'],'verification':result['verification']},ensure_ascii=False))


if __name__ == '__main__':
    main()
