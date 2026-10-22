import sys,json,time
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
CANDIDATES=[('recent-hazard','/tmp/pipes_recent_hazard_round2_20261022.py','0e26224befa63b550600afcbbb123c92e11487bbf04e3b60f90a4f733133fdf6'),
 ('oriented-guarded','/tmp/pipes_oriented_replay_round2_20261022.py','5cc1375864c046e7dbf114acfbbbed99b225732ff596af50ed763206e55b40df')]
assert len(e._evaluations('core-guarded-envelope','archive'))==2861,'finish preceding archive first'
assert len(e.inputs('development'))==56
assert not any(q.get('type')=='selection_freeze'for q in e.rows())
SCENARIOS=next(q['scenarios']for q in e.rows()[::-1]if q.get('type')=='scenario_scores'and len(q['scenarios'])==6)
for kind,path,pin in CANDIDATES:
    start=time.monotonic();path=e.Path(path);assert e.sha(path.read_bytes())==pin
    if kind=='oriented-guarded':e.batch_pairs(['guarded-envelope'],'development')
    e.compile_variant(kind,path)
    if kind=='oriented-guarded':
        actual,proof=e._load_module(path).transform_cpp(e.BASE_CPP.read_text())
        assert e.sha(actual.encode())==e.sha(e.artifact(kind,'cpp')[0].read_bytes())
        e.record(dict(type='oriented_replay_static_certificate',kind=kind,source_sha256=e.sha(actual.encode()),proof=proof))
    old=e.oldscreen(kind)
    e.batch_pairs(['baseline',kind],'development')
    dev=e.compact_summary([kind],'development')
    score=e.scenario_scores(['baseline',kind],SCENARIOS,['archive','development'],'cpp',{'archive':'oldscreen','development':'development'})
    changes={s:score['scores'][kind][s]['S']-score['scores']['baseline'][s]['S']for s in SCENARIOS}
    main_gate=min(changes.values())>=-1e-12 and dev['comparisons'][kind]['all']['mean']>=-1e-12 and dev['comparisons'][kind]['all']['minimum']>=-.02-1e-12 and old['comparisons'][kind]['all']['minimum']>=-.02-1e-12
    e.record(dict(type='last_quality_promotion_screen_gate_result',kind=kind,passes=main_gate,S_changes=changes,
        development=dev['comparisons'][kind]['all'],oldscreen=old['comparisons'][kind]['all']))
    if kind=='oriented-guarded':
        guarded='guarded-envelope'
        oldpair=e.paired(e._evaluations(kind,'oldscreen'),e._evaluations(guarded,'oldscreen'),list(e._evaluations(kind,'oldscreen')))
        devpair=e.paired(e._evaluations(kind,'development'),e._evaluations(guarded,'development'),[m['id']for m in e.inputs('development')])
        direct=e.scenario_scores([guarded,kind],SCENARIOS,['archive','development'],'cpp',{'archive':'oldscreen','development':'development'})
        guarded_changes={s:direct['scores'][kind][s]['S']-direct['scores'][guarded][s]['S']for s in SCENARIOS}
        ablation=e.record(dict(type='oriented_vs_guarded_ablation',kind=kind,reference=guarded,oldscreen=oldpair,development=devpair,S_changes=guarded_changes))
        print('ORIENTED_VS_GUARDED',json.dumps(ablation,ensure_ascii=False),flush=True)
    elapsed=time.monotonic()-start
    e.record(dict(type='phase_timing',phase=kind+'-last-screen215+56',wall_s=elapsed,one_heavy_worker=True))
    result=dict(kind=kind,passes_main_screen_gate=main_gate,oldscreen={g:v for g,v in old['comparisons'][kind].items()if g=='all'or g.startswith('provenance:')or g=='weighted_Open15'},
        development={g:v for g,v in dev['comparisons'][kind].items()if g=='all'or g.startswith('provenance:')},S_changes=changes,wall_s=elapsed)
    print('LAST_SCREEN_RESULT',json.dumps(result,ensure_ascii=False),flush=True)
print('LAST_QUALITY_SCREENS_DONE_STOP_BEFORE_FINAL112_AND_CJ',flush=True)
