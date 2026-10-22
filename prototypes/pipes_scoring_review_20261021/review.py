#!/usr/bin/env python3
"""Read frozen measurements; no solver runs or platform actions."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def load(rel):
    return json.loads((ROOT / rel).read_text())

def digest(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()

def best_two_of_four(values):
    """Expected sum of the largest two from four distinct uniform draws."""
    x = sorted(values)
    n = len(x)
    assert n >= 4
    den = math.comb(n, 4)
    coefficients = [math.comb(i, 3) + math.comb(i, 2) * (n-i-1)
                    for i in range(n)]
    assert sum(coefficients) == 2 * den
    return math.fsum(v*c for v,c in zip(x, coefficients)) / den

def main():
    prior = load('prototypes/pipes_all2537_comparison_20261020/analysis.json')
    current = load('prototypes/pipes_current_hybrid_cj_20261020/analysis.json')
    by_id = {r['id']: r for r in current['per_case']}
    cases = [r for r in prior['per_case_results']
             if r['selected'] and r['public_number'] is None]
    assert len(cases) == 2526
    for r in cases:
        t = by_id[r['id']]
        assert (r['operations'],r['F'],r['LB']) == (t['operations'],t['F'],t['LB'])
        assert r['methods']['online_cpp']['contest_adjusted_kpi'] == t['methods']['online_cj']['contest_adjusted_kpi']
        r['scores'] = {
            'full_replay': r['methods']['replay_search']['contest_adjusted_kpi'],
            'online': t['methods']['online_cj']['contest_adjusted_kpi'],
            'current_hybrid': t['methods']['hybrid_cj']['contest_adjusted_kpi'],
        }
    opens = {
        'full_replay': prior['full_open15']['replay_search']['raw_weighted_score'],
        'online': current['open15']['online_cj']['raw'],
        'current_hybrid': current['open15']['hybrid_cj']['raw'],
    }
    short = [r for r in cases if r['operations'] <= 200]
    long = [r for r in cases if r['operations'] > 100000]
    mid = [r for r in cases if r['operations'] <= 100000]
    coverage = load('prototypes/pipes_all2537_comparison_20261020/coverage.json')
    additional_ids = set(coverage['id_sets']['other_selected'])
    extra = [r for r in cases if r['id'] in additional_ids]
    trap_groups = {
        'prototypes/pipes_guarded_traps_20261019',
        'prototypes/pipes_open15_adversary_20261019',
        'prototypes/pipes_prefix_shock_20261019',
        'prototypes/pipes_v5_graves_20261019',
        'prototypes/pipes_presync_transport_20261020',
        'prototypes/pipes_presync_20261020',
        'prototypes/pipes_prefix_replan_20261020',
    }
    traps = [r for r in cases if r['source_group'] in trap_groups]
    pools = [
        ('archive_uniform', cases, cases),
        ('additional_archive', extra, extra),
        ('without_short', [r for r in cases if r['operations'] > 200], [r for r in cases if r['operations'] > 200]),
        ('long_only', long, long),
        ('expensive_are_long', mid, long),
        ('short_only', short, short),
        ('previous_directed_traps_only', traps, traps),
    ]
    # Verify the order-statistic formula directly on a small uneven pool.
    probe = [0.1, 0.3, 0.3, 0.7, 0.9, 1.0]
    brute = statistics.fmean(sum(sorted(s)[-2:]) for s in itertools.combinations(probe, 4))
    assert abs(best_two_of_four(probe) - brute) < 1e-14
    scenarios = []
    for name,cheap,expensive in pools:
        assert len(cheap) >= 11 and len(expensive) >= 4
        methods = {}
        for method in opens:
            a = statistics.fmean(r['scores'][method] for r in cheap)
            b = statistics.fmean(r['scores'][method] for r in expensive)
            bonus = 10 * best_two_of_four([r['scores'][method] for r in expensive])
            without_bonus = opens[method] + 44*a + 40*b
            methods[method] = dict(open15=opens[method],closed_4=44*a,closed_10=40*b,
                                   bonus=bonus,without_bonus=without_bonus,
                                   with_bonus_if_cangjie=without_bonus+bonus)
        scenarios.append(dict(name=name,cheap_pool=len(cheap),expensive_pool=len(expensive),
                              methods=methods,
                              hybrid_minus_full_if_both_cangjie=methods['current_hybrid']['with_bonus_if_cangjie']-methods['full_replay']['with_bonus_if_cangjie'],
                              hybrid_cangjie_minus_full_cpp=methods['current_hybrid']['with_bonus_if_cangjie']-methods['full_replay']['without_bonus']))
    gap = opens['full_replay'] - opens['current_hybrid']
    result = dict(
        source_hashes={p:digest(p) for p in [
            'data/pipes/statement.pdf',
            'prototypes/pipes_all2537_comparison_20261020/analysis.json',
            'prototypes/pipes_all2537_comparison_20261020/coverage.json',
            'prototypes/pipes_current_hybrid_cj_20261020/analysis.json',
            'prototypes/pipes_cj_tle15_20261021/release/solution.cj',
        ]},
        open_weights={'1':0.1,'2..11':1,'12..14':4,'15':10},
        closed_weights={'16..26':4,'27..30':10},
        capacities=dict(open=32.1,closed=84,cangjie_bonus=20,total_with_bonus=136.1),
        bonus_source='User-supplied organizer clarification, 16 October 2026; official website confirms a bonus but does not publish this formula.',
        bonus_formula='10 * (two largest KPI among closed27..30)',
        open15=opens,
        sacrifice=gap,
        uniform_hidden_KPI_gain_needed_without_bonus=gap/84,
        uniform_hidden_KPI_gain_needed_with_bonus=gap/104,
        one_expensive_test_KPI_gain_needed_without_bonus=gap/10,
        source_trap_groups=sorted(trap_groups),
        scenarios=scenarios,
        assumptions=[
            'Closed test distribution and mechanism frequencies are unknown; these are sampling scenarios, not competition forecasts.',
            'Full replay was measured as C++ cache32, with causal fallback. Its Cangjie bonus is hypothetical: no such validated port is provided here.',
            'Current hybrid source585c6e7f preserves the frozen hybrid response/KPI policy. Its Windows1.0.5 verdict is pending.',
            'Archive examples are selected, correlated and partly adversarial. They are not an independent representative holdout.',
            'Fresh96 and newest24 were not evaluated with this full-replay policy; no three-way fresh comparison is claimed.',
            'All expected scores assume successful official execution; TLE/incorrect cases contribute zero.',
        ],
        extra_scenario_compatibility=dict(
            archive_delta_hybrid_online=scenarios[0]['methods']['current_hybrid']['with_bonus_if_cangjie']-scenarios[0]['methods']['online']['with_bonus_if_cangjie']),
    )
    assert abs(result['extra_scenario_compatibility']['archive_delta_hybrid_online']-0.14590919306368733) < 1e-11
    previous_scenarios = {s['name']:s for s in current['score_scenarios']}
    for s in scenarios:
        if s['name'] in previous_scenarios:
            m=s['methods']
            assert abs(m['current_hybrid']['with_bonus_if_cangjie']-m['online']['with_bonus_if_cangjie']-previous_scenarios[s['name']]['exact_delta']) < 1e-11
    (HERE/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'open15':opens,'sacrifice':gap,
                      'threshold_with_bonus':gap/104,'scenarios':scenarios},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
