import sys,json,math,statistics,collections
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_guards_20261022 as e

def paired(a,b,ids):
    ds=[a[i]['kpi']-b[i]['kpi'] for i in ids]
    return dict(n=len(ds),wins=sum(x>1e-12 for x in ds),ties=sum(abs(x)<=1e-12 for x in ds),losses=sum(x< -1e-12 for x in ds),mean=statistics.fmean(ds),minimum=min(ds),maximum=max(ds))

def main():
    rr=e.rows();meta={m['id']:m for m in e.ev.rows};fm={m['id']:m for m in e.inputs('final')}
    archive={r['id']:r for r in rr if r['type']=='evaluation' and r['suite']=='archive-production'}
    control={r['id']:r for r in rr if r['type']=='evaluation' and r['suite']=='archive-same-policy-oldcore'}
    assert len(archive)==len(control)==2661
    final={k:{} for k in list(e.KINDS)+['same-policy-oldcore']}
    for r in rr:
        if r['type']=='evaluation' and r['suite']=='final':final[r['kind']][r['id']]=r
    assert all(len(d)==64 for d in final.values())
    native={k:{r['id']:r for r in rr if r['type']=='interactive_evaluation' and r['suite']=='unseen-final' and r['kind']==k} for k in ['production','old-full']}
    assert all(len(d)==64 for d in native.values())
    for i in fm:
        assert native['production'][i]['response_sha256']==final['cautious'][i]['response_sha256']
        assert native['old-full'][i]['response_sha256']==final['full'][i]['response_sha256']
    opens={k:math.fsum(meta[i]['weight']*({r['id']:r for r in rr if r['type']=='evaluation' and r['suite']=='archive-core' and r['kind']=='lazy-full'} if k=='lazy-full' else e.FROZEN if k=='full' else {r['id']:r for r in rr if r['type']=='evaluation' and r['suite']=='archive-policy' and r['kind']==k})[i]['kpi'] for i,m in meta.items() if m.get('public_number')) for k in e.KINDS}
    definitions=next(r for r in reversed(rr) if r['type']=='final_scenario_freeze')
    scores={k:{s:opens[k]+44*statistics.fmean(final[k][i]['kpi'] for i in ids['cheap'])+40*statistics.fmean(final[k][i]['kpi'] for i in ids['expensive'])+10*e.expected_top2([final[k][i]['kpi'] for i in ids['expensive']]) for s,ids in definitions['scenarios'].items()} for k in e.KINDS}
    best={s:max(scores[k][s] for k in e.KINDS) for s in definitions['scenarios']}
    regret={k:max(best[s]-scores[k][s] for s in best) for k in e.KINDS}
    assert regret['cautious']<=regret['full']+1e-12,regret
    core=paired(final['cautious'],final['same-policy-oldcore'],fm)
    assert core['minimum']>=-.02
    groups={g:[i for i,m in fm.items() if m['stratum']==g] for g in sorted({m['stratum'] for m in fm.values()})}
    comparisons={g:dict(vs_full=paired(native['production'],native['old-full'],ids),core=paired(final['cautious'],final['same-policy-oldcore'],ids)) for g,ids in groups.items()}
    for g in ['ordinary','series','motif']:assert comparisons[g]['core']['mean']>=-.002
    assert comparisons['interruption']['core']['mean']>=-1e-12
    prod_native=[r for r in rr if r['type']=='interactive_evaluation' and r['kind']=='production']
    assert all(r['within_limits'] for r in prod_native)
    calibration=[r for r in rr if r['type']=='evaluation' and r['suite']=='calibration-production']
    assert len(calibration)==40
    policy=next(r for r in reversed(rr) if r['type']=='selection_freeze')
    witness=sum(max(final[k][i]['kpi'] for k in final)>=.85 for i in fm)
    result=dict(type='final_summary',selected_policy='cautious',implementation_guard='edge-local',source_file=str(e.E/'release/solution.cj'),source_sha256=e.sha((e.E/'release/solution.cj').read_bytes()),binary_sha256=e.sha((e.E/'bin/production').read_bytes()),compiler='Cangjie1.0.5 -O0',fresh_generated=104,fresh_calibration=40,fresh_independent_final=64,archive_cases=2661,exact_cpp_to_cj_parity=2765,core_archive_vs_same_policy=paired(archive,control,meta),archive_vs_previous_full=paired(archive,e.FROZEN,meta),core_final_vs_same_policy=core,final_actual_cj_vs_previous_full=paired(native['production'],native['old-full'],fm),final_strata=comparisons,open15=opens['cautious'],previous_full_open15=opens['full'],open_tradeoff=opens['full']-opens['cautious'],dev_scores=policy['scenario_scores'],dev_regrets=policy['max_regrets'],final_conditional_scenario_scores=scores,final_max_regrets=regret,final_gate_passed=True,final_witnessed_kpi_ge_085=witness,final_witness_scope='at least one actual feasible solver among frozen candidates; all64 volume upper bounds>=0.85 does not itself prove attainability',production_interactive_cases=len(prod_native),production_interactive_max_cpu_s=max(r['solver_cpu_total_s'] for r in prod_native),production_interactive_max_rss_mb=max(r['solver_peak_rss_mb'] for r in prod_native),production_archive_max_batch_cpu_s=max(r['solver_cpu_total_s'] for r in archive.values()),production_archive_max_batch_rss_mb=max(r['solver_peak_rss_mb'] for r in archive.values()),process_cpu='user+system of entire solver; cjProcessorNum=1, one benchmark worker',target_windows_g5420_measured=False,platform_touched=False,claims='conditional empirical robust selection, not a guaranteed or probabilistic prediction of unknown hidden tests; no policy tuning after final')
    e.record(result)
    print(json.dumps({k:result[k] for k in ['source_sha256','archive_vs_previous_full','core_archive_vs_same_policy','core_final_vs_same_policy','final_actual_cj_vs_previous_full','final_strata','open15','final_max_regrets','production_interactive_max_cpu_s','production_interactive_max_rss_mb','final_witnessed_kpi_ge_085']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
