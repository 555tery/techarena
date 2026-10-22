#!/usr/bin/env python3
"""Compare matching official-interactor reports; no solver execution."""
import argparse
import csv
import hashlib
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_run(name):
    return {r['case']: r for r in csv.DictReader((ROOT / 'runs' / name / 'cases.csv').open())}


def bootstrap(values):
    rng = random.Random(71527999)
    draws = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(20000))
    return [draws[499], draws[19499]]


def compare(baseline_name, candidate_name):
    baseline, candidate = read_run(baseline_name), read_run(candidate_name)
    assert baseline.keys() == candidate.keys()
    pairs = []
    for key in baseline:
        a, b = baseline[key], candidate[key]
        assert a['test_sha256'] == b['test_sha256']
        assert a['status'] == b['status'] == 'ok'
        assert a['final_occupied_length_m'] == b['final_occupied_length_m']
        pairs.append({
            'case': key, 'input_sha256': a['test_sha256'],
            'baseline_trench_m': int(a['trench_length_m']),
            'candidate_trench_m': int(b['trench_length_m']),
            'delta_trench_m': int(b['trench_length_m']) - int(a['trench_length_m']),
            'relative_trench_delta': int(b['trench_length_m']) / int(a['trench_length_m']) - 1,
            'baseline_kpi': float(a['kpi']), 'candidate_kpi': float(b['kpi']),
            'delta_kpi': float(b['kpi']) - float(a['kpi']),
            'delta_weighted_score': float(b['weighted_score']) - float(a['weighted_score']),
            'solver_cpu_s': float(b['solver_cpu_total_s']),
            'solver_rss_mib': float(b['solver_peak_rss_mb']),
            'candidate_diagnostics': b['candidate_stderr'],
            'within_resource_limits': float(b['solver_cpu_total_s']) < 5 and float(b['solver_peak_rss_mb']) < 256,
        })
    deltas = [p['delta_kpi'] for p in pairs]
    summary = {
        'baseline': baseline_name, 'candidate': candidate_name, 'pairs': pairs,
        'case_count': len(pairs), 'mean_delta_kpi': statistics.mean(deltas),
        'paired_trace_bootstrap_95_ci': bootstrap(deltas),
        'wins': sum(p['delta_trench_m'] < 0 for p in pairs),
        'losses': sum(p['delta_trench_m'] > 0 for p in pairs),
        'ties': sum(p['delta_trench_m'] == 0 for p in pairs),
        'worst_relative_trench_regression': max(p['relative_trench_delta'] for p in pairs),
        'weighted_score_delta': sum(p['delta_weighted_score'] for p in pairs),
        'max_solver_cpu_s': max(p['solver_cpu_s'] for p in pairs),
        'max_solver_rss_mib': max(p['solver_rss_mib'] for p in pairs),
        'all_within_limits': all(p['within_resource_limits'] for p in pairs),
        'caveat': 'Synthetic mean/CI describe only this finite seeded suite, not official hidden tests.',
    }
    out = ROOT / f'comparison_{candidate_name}.json'
    out.write_text(json.dumps(summary, indent=2) + '\n')
    csvout = ROOT / f'comparison_{candidate_name}.csv'
    with csvout.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    print(json.dumps({k: v for k, v in summary.items() if k != 'pairs'}, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline')
    parser.add_argument('candidate')
    args = parser.parse_args()
    compare(args.baseline, args.candidate)
