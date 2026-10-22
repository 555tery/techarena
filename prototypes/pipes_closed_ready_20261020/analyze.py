"""Predeclared, distribution-sensitive selection; no synthetic hidden-score claims."""
import argparse
import collections
import datetime
import json
import random
import statistics
from pathlib import Path

from evaluate import HERE, NAMES, sha


def read_records(mode, group):
    result = []
    for name in NAMES:
        for path in sorted((HERE/'measurements'/mode/group/name).glob('*/record.json')):
            result.append(json.loads(path.read_text()))
    return result


def summary(records):
    by_name = {name: {r['id']: r for r in records if r['strategy'] == name} for name in NAMES}
    assert all(set(by_name[n]) == set(by_name['online']) for n in NAMES)
    result = {}
    for name, rows in by_name.items():
        r = list(rows.values())
        good = [x for x in r if x['status'] == 'ok']
        family = collections.defaultdict(list)
        for x in good:
            family[(x['stratum'], x['family'])].append(x['kpi'])
        means = {f'{s}/{f}': statistics.mean(v) for (s, f), v in family.items()}
        strata = {s: statistics.mean(v for key, v in means.items() if key.startswith(s+'/'))
                  for s in set(x['stratum'] for x in good)}
        pairs = [dict(id=ident, stratum=x['stratum'], family=x['family'],
                      online=by_name['online'][ident]['kpi'], candidate=x['kpi'],
                      delta=x['kpi']-by_name['online'][ident]['kpi'],
                      retention=x['kpi']/by_name['online'][ident]['kpi'])
                 for ident, x in rows.items() if x['status'] == 'ok' and by_name['online'][ident]['status'] == 'ok']
        delta = [x['delta'] for x in pairs]
        result[name] = dict(n=len(r), valid=len(good), resources_ok=all(x['resources_ok'] for x in r),
                            family_means=means, stratum_macro=strata,
                            overall_mean=statistics.mean(x['kpi'] for x in good),
                            maximum_cpu_s=max(x['solver_cpu_total_s'] or 0 for x in r),
                            maximum_rss_mib=max(x['solver_peak_rss_mb'] or 0 for x in r),
                            paired=dict(wins=sum(d > 1e-12 for d in delta),
                                        ties=sum(abs(d) <= 1e-12 for d in delta),
                                        losses=sum(d < -1e-12 for d in delta),
                                        worst_delta=min(delta), mean_delta=statistics.mean(delta)),
                            pairs=pairs)
        if 'ordinary' in strata:
            result[name]['min_ordinary_retention'] = min(x['retention'] for x in pairs if x['stratum'] == 'ordinary')
            result[name]['paired_by_stratum'] = {}
            for s in ['ordinary', 'prefix']:
                ps = [x for x in pairs if x['stratum'] == s]
                ds = [x['delta'] for x in ps]
                fam_delta = [v - result.get('online', {}).get('family_means', means)[key]
                             for key, v in means.items() if key.startswith(s+'/')]
                rng = random.Random(202610202103)
                boot = sorted(statistics.mean(rng.choices(fam_delta, k=len(fam_delta))) for _ in range(4000))
                result[name]['paired_by_stratum'][s] = dict(n=len(ps),
                    wins=sum(x > 1e-12 for x in ds), ties=sum(abs(x) <= 1e-12 for x in ds),
                    losses=sum(x < -1e-12 for x in ds), worst_delta=min(ds),
                    mean_delta=statistics.mean(ds), family_macro_delta=statistics.mean(fam_delta),
                    family_bootstrap_95=[boot[100], boot[3899]])
    return result


def eligibility(stats):
    baseline = stats['online']['stratum_macro']
    result = {}
    for name in NAMES:
        s = stats[name]
        reasons = []
        if s['valid'] != s['n'] or not s['resources_ok']:
            reasons.append('correctness_or_resources')
        for stratum in ['ordinary', 'prefix']:
            if s['stratum_macro'][stratum] < baseline[stratum] - 0.002 - 1e-12:
                reasons.append(stratum+'_macro_below_online_minus_0.002')
        if s['min_ordinary_retention'] < 0.80 - 1e-12:
            reasons.append('ordinary_case_retention_below_0.80')
        result[name] = reasons
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('group', choices=['calibration', 'final'])
    ap.add_argument('--mode', choices=['screen', 'official'], default='official')
    args = ap.parse_args()
    rows = read_records(args.mode, args.group)
    stats = summary(rows)
    assert len(rows) == (64 if args.group == 'calibration' else 128)*3
    public = read_records('official', 'open15')
    assert len(public) == 45
    open_score = {name: sum(r['weight']*r['kpi'] for r in public if r['strategy'] == name) for name in NAMES}
    reasons = eligibility(stats)
    scenarios = {name: {str(p): open_score[name]+84*((1-p)*stats[name]['stratum_macro']['ordinary']+
                                     p*stats[name]['stratum_macro']['prefix'])
                        for p in [0.0, 0.1, 0.25, 0.5, 1.0]} for name in NAMES}
    regret = {name: max(max(scenarios[n][str(p)] for n in NAMES)-scenarios[name][str(p)] for p in [0.0, 1.0])
              for name in NAMES}
    eligible = [n for n in NAMES if not reasons[n]]
    assert eligible
    minimum = min(regret[n] for n in eligible)
    selected = next(n for n in ['online', 'hybrid', 'full'] if n in eligible and regret[n] <= minimum+0.01)
    out = dict(group=args.group, mode=args.mode, statistics=stats, open15_score=open_score,
               ineligibility_reasons=reasons, illustrative_scenarios=scenarios, maximum_regret=regret,
               scope='Synthetic strata, not the official hidden distribution. Scenario totals are sensitivity calculations only.')
    if args.group == 'calibration':
        path = HERE/'selection-freeze.json'
        assert not path.exists(), 'Selection is already frozen; do not tune on final results.'
        out['selected'] = selected
        freeze = dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), selected=selected,
                      candidates_freeze_sha256=sha(HERE/'candidates-freeze.json'),
                      experiment_sha256=sha(HERE/'experiment.json'),
                      calibration_records_sha256=sha(HERE/f'{args.mode}-calibration.json'),
                      open15_records_sha256=sha(HERE/'official-open15.json'),
                      ineligibility_reasons=reasons, maximum_regret=regret,
                      final_rule='Confirm ordinary/prefix macro >= online-0.002, ordinary retention >=0.8, correctness/resources. If failed, choose online; no retuning.')
        path.write_text(json.dumps(freeze, indent=2)+'\n')
    else:
        freeze = json.loads((HERE/'selection-freeze.json').read_text())
        frozen = freeze['selected']
        out['frozen_selection'] = frozen
        out['confirmation_passed'] = not reasons[frozen]
        out['recommended'] = frozen if not reasons[frozen] else 'online'
        out['retrospective_minimax'] = selected
    (HERE/f'analysis-{args.group}.json').write_text(json.dumps(out, indent=2)+'\n')
    compact = {n: {k: v for k, v in s.items() if k not in ['pairs', 'family_means']} for n, s in stats.items()}
    print(json.dumps(dict(statistics=compact, open15_score=open_score, reasons=reasons,
                          maximum_regret=regret, chosen=out.get('recommended', out.get('selected'))), indent=2))


if __name__ == '__main__':
    main()
