"""Paired post-freeze analysis; never trains or changes candidates."""
import collections
import hashlib
import json
from pathlib import Path
import random
import re
import statistics

ROOT = Path(__file__).resolve().parent
LABELS = ['incumbent', 'planner_off', 'planner_on', 'learned_off', 'learned_gen8']


def load(phase, label):
    p = ROOT / 'evaluations' / phase / label
    m = json.loads((p / 'manifest.json').read_text())
    assert m['correct'], (phase, label, m)
    s = json.loads((p / 'harness/summary.json').read_text())
    assert s['case_count'] == s['ok_count'] == m['case_count']
    return {r['case']: r for r in s['records']}, m


def same_transcript(a, b):
    return Path(a['judge_output_file']).read_bytes() == Path(b['judge_output_file']).read_bytes()


def paired(records, baseline, synthetic):
    assert set(records) == set(baseline)
    rows, groups = [], collections.defaultdict(list)
    for case, r in records.items():
        b = baseline[case]
        assert r['test_sha256'] == b['test_sha256']
        delta = r['kpi'] - b['kpi']
        rows.append({'case': case, 'delta_F_over_T': delta,
                     'delta_T_m': r['trench_length_m'] - b['trench_length_m'],
                     'delta_weighted_score': r['weighted_score'] - b['weighted_score'],
                     'identical_answers': same_transcript(r, b)})
        if synthetic:
            groups[case.rsplit('_', 1)[0]].append(delta)
    deltas = [r['delta_F_over_T'] for r in rows]
    result = {'wins': sum(d > 1e-12 for d in deltas),
              'losses': sum(d < -1e-12 for d in deltas),
              'ties': sum(abs(d) <= 1e-12 for d in deltas),
              'mean_delta_F_over_T': statistics.mean(deltas),
              'delta_weighted_score': sum(r['delta_weighted_score'] for r in rows),
              'worst_case': min(rows, key=lambda r: r['delta_F_over_T']),
              'identical_answer_count': sum(r['identical_answers'] for r in rows),
              'rows': rows}
    if synthetic:
        means = {k: statistics.mean(v) for k, v in groups.items()}
        result['family_means'] = means
        rng = random.Random(2026101810)
        values = list(means.values())
        bootstrap = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(10000))
        result['family_macro'] = statistics.mean(values)
        result['bootstrap_family_95_percent_interval'] = [bootstrap[249], bootstrap[9749]]
        result['uncertainty_scope'] = 'Only six procedural families; cluster bootstrap is descriptive, not hidden-distribution confidence.'
    return result


def telemetry(records):
    total, per_case = collections.defaultdict(float), {}
    for case, r in records.items():
        parsed = {}
        for line in r['candidate_stderr'].splitlines():
            if line.startswith('H1 live_'):
                prefix = line.split()[1] + '.'
            elif line.startswith('H1 plan_execution'):
                prefix = 'plan.'
            else:
                prefix = ''
            for key, value in re.findall(r'(\w+)=(\d+(?:\.\d+)?)(?=\s|$)', line):
                parsed[prefix + key] = float(value)
        per_case[case] = parsed
        for key, value in parsed.items():
            total[key] += value
    return {'sums': dict(total), 'per_case': per_case,
            'note': 'Configuration fields (e.g. enabled/horizon/beam) are repeated per run; do not interpret their sum as activity.'}


def main():
    report = {'phases': {}, 'paired': {}, 'telemetry': {}, 'repeat': {}}
    for phase in ('dev', 'final', 'open15'):
        loaded = {}
        report['phases'][phase] = {}
        for label in LABELS:
            records, manifest = load(phase, label)
            loaded[label] = records
            report['phases'][phase][label] = {
                'count': len(records), 'weighted_score': manifest['weighted_score'],
                'mean_F_over_T': statistics.mean(r['kpi'] for r in records.values()),
                'max_cpu_s': manifest['max_cpu'], 'max_rss_MiB': manifest['max_rss'],
                'build_manifest_sha256': manifest['build_manifest_sha256']}
            if label in ('planner_on', 'learned_gen8'):
                report['telemetry'][phase + '/' + label] = telemetry(records)
        for target, control in [('planner_on','planner_off'), ('learned_gen8','learned_off'),
                                ('planner_on','incumbent'), ('learned_gen8','incumbent'),
                                ('planner_off','learned_off')]:
            report['paired'][phase + '/' + target + '_vs_' + control] = paired(loaded[target], loaded[control], phase != 'open15')
    for label in LABELS:
        repeated, _ = load('repeat', label)
        original, _ = load('final', label)
        results = {}
        for case, r in repeated.items():
            b = original[case]
            results[case] = {'same_final_T': r['trench_length_m'] == b['trench_length_m'],
                             'same_answers': same_transcript(r, b),
                             'same_input_sha256': r['test_sha256'] == b['test_sha256']}
            assert all(results[case].values())
        report['repeat'][label] = results
    frozen = json.loads((ROOT / 'freeze.json').read_text())
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in frozen['files'].items())
    report['freeze_unchanged'] = True
    report['official_budget'] = json.loads((ROOT / 'evaluation-counts.json').read_text())
    (ROOT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'phases': report['phases'], 'paired': {k: {n: v[n] for n in ('wins','losses','ties','mean_delta_F_over_T','delta_weighted_score')} for k,v in report['paired'].items()}}, indent=2))


if __name__ == '__main__':
    main()
