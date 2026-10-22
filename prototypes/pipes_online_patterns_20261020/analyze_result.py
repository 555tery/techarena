"""Frozen final decision plus explicitly descriptive, mechanism-level uncertainty."""
import collections,csv,datetime,json,random,statistics
from evaluate import HERE,cases,source,sha
from summarize import load,stats

STRATA=['stable_patterns','changing_patterns','neutral','public_prefix']

def main():
    freeze=json.loads((HERE/'selection-freeze.json').read_text());selected=freeze['selected']
    for n in freeze['sources']:
        assert sha(source(n))==freeze['sources'][n]
        assert sha(source(n).with_name('solver'))==freeze['binaries'][n]
    for group in ['calibration','final','stress']:
        assert sha(HERE/'evaluation'/group/'manifest.json')==freeze['manifests'][group]
    rows={n:load('screen','final',n) for n in freeze['sources']}
    b=rows['baseline'];r=rows[selected];old=rows['legacy']
    s=stats(r,b);legacy=stats(r,old)
    pub=freeze['public_scores'];delta_pub=pub[selected]-pub['baseline']
    macro={t:s['by_stratum'][t]['family_macro_delta'] for t in STRATA}
    endpoints={t:delta_pub+84*macro[t] for t in STRATA}
    equal_gain=statistics.mean(macro.values())
    quality_gates=dict(positive_equal_stratum_KPI=equal_gain>0,
        positive_equal_stratum_total=delta_pub+84*equal_gain>0,
        patterns_positive=(macro['stable_patterns']+macro['changing_patterns'])/2>0,
        stratum_floor=min(macro.values())>=-.002,
        individual_retention=s['min_retention']>=.95,
        worst_total_endpoint=min(endpoints.values())>=-.05)
    dev={n:load('screen','dev',n) for n in ['baseline','legacy',selected]}
    origin=[k for k in dev['baseline'] if k.startswith('core-final-')]
    targets=[k for k in origin if dev['baseline'][k]['kpi']<dev['legacy'][k]['kpi']-1e-12]
    assert len(targets)==23
    target_rows=[]
    for k in targets:
        v={n:dev[n][k] for n in dev}
        d=v[selected]['kpi']-v['baseline']['kpi']
        target_rows.append(dict(id=k.removeprefix('core-final-'),legacy_T=v['legacy']['trench_length_m'],
            current_T=v['baseline']['trench_length_m'],candidate_T=v[selected]['trench_length_m'],delta_KPI=d,
            repaired=v[selected]['kpi']>=v['legacy']['kpi']-1e-12,
            result='win' if d>1e-12 else 'loss' if d<-1e-12 else 'tie'))
    gain_retention=sum(dev[selected][k]['kpi']-dev['legacy'][k]['kpi'] for k in origin)/sum(dev['baseline'][k]['kpi']-dev['legacy'][k]['kpi'] for k in origin)
    with (HERE/'target23-results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(target_rows[0]));w.writeheader();w.writerows(target_rows)

    # Metadata family names include variant suffixes. Keep the frozen estimand
    # and decision unchanged; cluster uncertainty at actual generating mechanisms.
    manifest={c['id']:c for c in cases('final')}
    groups={t:collections.defaultdict(list) for t in STRATA}
    neutral_matched=collections.defaultdict(list);neutral_iid=collections.defaultdict(list)
    pair_rows=[]
    for k,c in manifest.items():
        d=r[k]['kpi']-b[k]['kpi'];t=c['stratum'];family=c['family']
        if t in ['stable_patterns','changing_patterns']:
            groups[t][family.split('/')[0]].append(d)
        elif t=='public_prefix':groups[t][family].append(d)
        elif c.get('matched_control_for'):
            partner=c['matched_control_for'];root=manifest[partner]['family'].split('/')[0]
            neutral_matched[root].append(d)
            pair_rows.append(dict(pattern=partner,control=k,mechanism=root,
                pattern_delta=r[partner]['kpi']-b[partner]['kpi'],control_delta=d))
        else:neutral_iid['/'.join(family.split('/')[:2])].append(d)
    vals={t:{f:statistics.mean(v) for f,v in g.items()} for t,g in groups.items()}
    matched={f:statistics.mean(v) for f,v in neutral_matched.items()}
    iid={f:statistics.mean(v) for f,v in neutral_iid.items()}
    roots=sorted(vals['stable_patterns']);assert set(roots)==set(vals['changing_patterns'])==set(matched)
    assert len(roots)==12 and len(iid)==6
    rng=random.Random(2026102053);boots={t:[] for t in STRATA+['equal_four_strata']}
    for _ in range(10000):
        sampled=rng.choices(roots,k=len(roots))
        d={t:statistics.mean(vals[t][f] for f in sampled) for t in ['stable_patterns','changing_patterns']}
        d['neutral']=.5*statistics.mean(matched[f] for f in sampled)+.5*statistics.mean(rng.choices(list(iid.values()),k=len(iid)))
        d['public_prefix']=statistics.mean(rng.choices(list(vals['public_prefix'].values()),k=len(vals['public_prefix'])))
        d['equal_four_strata']=statistics.mean(d.values())
        for t in boots:boots[t].append(d[t])
    ci={t:[sorted(v)[250],sorted(v)[9749]] for t,v in boots.items()}
    neutral_point=.5*statistics.mean(matched.values())+.5*statistics.mean(iid.values())
    assert abs(neutral_point-macro['neutral'])<1e-12
    matched_summary=dict(n_pairs=len(pair_rows),mean_pattern_delta=statistics.mean(x['pattern_delta'] for x in pair_rows),
        mean_control_delta=statistics.mean(x['control_delta'] for x in pair_rows),
        difference_of_policy_deltas=statistics.mean(x['pattern_delta']-x['control_delta'] for x in pair_rows),
        interpretation='Descriptive matched contrast; shuffled controls alter length order and PID lifetimes together while preserving event signs and size histograms. It does not isolate one causal feature.')
    uncertainty=dict(method='Post-freeze descriptive joint bootstrap of12 generating mechanisms across stable/changing/matched controls;6 IID profiles within neutral;8 suffix families within prefix.10000 draws, fixed seed. Point estimand equals frozen macro; not used for selection.',
        metadata_caveat='Raw family strings in the frozen evaluator contain variant suffixes for non-prefix inputs. Their original intervals are variant-level; this report uses broader mechanism blocks. Do not call the original intervals mechanism-block intervals.',
        intervals95=ci,hidden_distribution_inferred=False,coverage_guarantee=False)
    out=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected=selected,
        source_sha256=freeze['sources'][selected],binary_sha256=freeze['binaries'][selected],
        baseline_sha256=freeze['sources']['baseline'],selection_freeze_sha256=sha(HERE/'selection-freeze.json'),
        quality_gates=quality_gates,quality_passed=all(quality_gates.values()),official_confirmation_pending=True,
        final_statistics=s,relative_to_legacy=legacy,public_scores=pub,delta_public=delta_pub,
        equal_stratum_KPI_delta=equal_gain,total_score_equal_mix_delta=delta_pub+84*equal_gain,
        total_score_endpoints_delta=endpoints,uncertainty=uncertainty,matched_controls=matched_summary,
        target23=target_rows,original_DEV_gain_retained=gain_retention,
        caveat='Small positive point estimate with uncertainty crossing zero; independent synthetic transfer only, not a guarantee of hidden-contest gains.',
        no_source_edits_after_final=True,platform_actions=0,canonical_changed=False)
    (HERE/'quality-outcome.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['quality_passed','quality_gates','equal_stratum_KPI_delta','total_score_equal_mix_delta','total_score_endpoints_delta','original_DEV_gain_retained','uncertainty','matched_controls']},indent=2))

if __name__=='__main__':main()
