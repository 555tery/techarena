import json,sys,time,collections,subprocess
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
GROWING=e.Path('/tmp/pipes_growing_lifetimes_round2_20261022.py')
GROWING_SHA='234797b9ef09150dd3ec802255cdd344b980e4b1e82af105b82ab0f801086ebc'
ACTIONS=e.Path('/tmp/pipes_lifetime_actions_round2_20261022.py')
ACTIONS_SHA='3845b69a282be277234c3ed239fb4eebc575a280028f83dfd063bf975a6a9983'
CONTROL=e.R/'results/pipes/policy-comparison/source.cpp'
CONTROL_SHA='bf04dc2cf7dd18fb1e4cf28f42366e164ab4de668e0be6fb5243709cc4147bb6'
CORE='recycled_deleted_band';COMBO='core-guarded-envelope'

def timed(label,fn):
    start=time.monotonic();result=fn();elapsed=time.monotonic()-start
    e.record(dict(type='phase_timing',phase=label,wall_s=elapsed,one_heavy_worker=True))
    print('PHASE_DONE',label,round(elapsed,3),flush=True);return result

def build_control(kind,policy):
    assert e.sha(CONTROL.read_bytes())==CONTROL_SHA
    folder=e.E/kind;folder.mkdir(parents=True,exist_ok=True)
    source=e._immutable_source(folder/'solution.cpp',CONTROL.read_text());binary=e.E/'bin'/(kind+'-cpp')
    command=['clang++','-O2','-std=c++17',f'-DPIPE_POLICY={policy}',str(source),'-o',str(binary)]
    q=subprocess.run(command,capture_output=True,text=True)
    r=e.record(dict(type='build',kind=kind,language='cpp',source=str(source),source_sha256=e.sha(source.read_bytes()),
        parent_source_sha256=CONTROL_SHA,binary=str(binary),binary_sha256=e.sha(binary.read_bytes())if q.returncode==0 else None,
        command=command,status=q.returncode,stderr=q.stderr[-3000:],scope='absolute control on newdev56 only'))
    assert q.returncode==0,q.stderr;return r

def absolute_summary(kinds):
    meta=e.inputs('development');assert len(meta)==56
    groups={provenance:[m['id']for m in meta if m['provenance']==provenance]for provenance in {m['provenance']for m in meta}}
    groups['all56']=[m['id']for m in meta]
    results={}
    for k in kinds:
        a=e._evaluations(k,'development');assert len(a)==56,(k,len(a))
        results[k]={g:dict(n=len(ids),mean_kpi=sum(a[i]['kpi']for i in ids)/len(ids),
                          minimum_kpi=min(a[i]['kpi']for i in ids),maximum_kpi=max(a[i]['kpi']for i in ids))for g,ids in groups.items()}
    e.record(dict(type='newdev56_absolute_summary',results=results,groups=groups))
    print('ABSOLUTE56',json.dumps(results,ensure_ascii=False),flush=True)

assert e.sha(GROWING.read_bytes())==GROWING_SHA and e.sha(ACTIONS.read_bytes())==ACTIONS_SHA
assert len(e._evaluations(CORE,'archive'))==2861,'wait for core full archive first'
assert not any(q.get('type')=='selection_freeze'for q in e.rows())
# The combination was explicitly authorized iff it retains both screened effects.
b=e._evaluations('baseline','oldscreen');c=e._evaluations(CORE,'oldscreen');z=e._evaluations(COMBO,'oldscreen')
assert len(b)==len(c)==len(z)==215
assert all(z[i]['kpi']>=c[i]['kpi']-1e-12 for i in c)
assert all(z[i]['kpi']>=b[i]['kpi']-1e-12 for i in b)
assert e.paired(e._evaluations(COMBO,'development'),e._evaluations('baseline','development'),[m['id']for m in e.inputs('development')])['minimum']>=-1e-12

def growing():
    destination=e.Path('/tmp/pipes_growing_round2_inputs_20261022')
    manifest=e._load_module(GROWING).generate(destination)if not destination.exists()else destination/'manifest.jsonl'
    if not any(m.get('provenance')=='round2_growing48'for m in e.read_jsonl(e.MANIFEST)):
        e.register_fresh(manifest,GROWING,expected_splits={'development':16,'sealed_final':32},provenance='round2_growing48',id_prefix='round2-growing-')
    assert len(e.inputs('development'))==56
    return manifest

timed('growing48_generation_official_witnesses',growing)
timed('core_combo_newgrowing16',lambda:e.batch_pairs(['baseline',CORE,COMBO],'development'))
for kind in [CORE,COMBO]:e.compact_summary([kind],'development')
for kind,policy in [('absolute-bestfit',4),('absolute-firstfit',1)]:
    timed(kind+'-build',lambda kind=kind,policy=policy:build_control(kind,policy))
    timed(kind+'-newdev56',lambda kind=kind:e.batch_pairs([kind],'development'))
absolute_summary(['baseline',CORE,COMBO,'absolute-bestfit','absolute-firstfit'])
for kind,kwargs in [('early-only',dict(early_lifetime=True)),('side-only',dict(lifetime_side=True))]:
    timed(kind+'-build',lambda kind=kind,kwargs=kwargs:e.compile_variant(kind,ACTIONS,transformer_kwargs=kwargs))
    timed(kind+'-oldscreen215',lambda kind=kind:e.oldscreen(kind))
    timed(kind+'-newdev56',lambda kind=kind:e.batch_pairs(['baseline',kind],'development'))
    report=e.compact_summary([kind],'development')
    print('ACTION_RESULT',kind,json.dumps({g:v for g,v in report['comparisons'][kind].items()if g=='all'or g.startswith('provenance:')},ensure_ascii=False),flush=True)
    scenarios=next(q['scenarios']for q in e.rows()[::-1]if q.get('type')=='scenario_scores'and len(q['scenarios'])==6)
    score=e.scenario_scores(['baseline',kind],scenarios,['archive','development'],'cpp',{'archive':'oldscreen','development':'development'})
    print('ACTION_ORIGINAL_S_DELTAS',kind,json.dumps({s:score['scores'][kind][s]['S']-score['scores']['baseline'][s]['S']for s in scenarios}),flush=True)
# Do not combine new lifetime hypotheses. The already qualified old combo is next.
timed('core_guarded_combo_all2861',lambda:e.batch_pairs(['baseline',COMBO],'archive'))
r=e.compact_summary([COMBO],'archive')
print('COMBO_ARCHIVE_RESULT',json.dumps({g:v for g,v in r['comparisons'][COMBO].items()if g=='all'or g.startswith('provenance:')or g.startswith('length:')or g=='weighted_Open15'},ensure_ascii=False),flush=True)
core=e._evaluations(CORE,'archive');combo=e._evaluations(COMBO,'archive')
ablation=e.paired(combo,core,list(core));e.record(dict(type='archive_causal_ablation',comparison='core+guarded versus core alone',result=ablation))
print('CORE_VS_COMBO_ABLATION',json.dumps(ablation),flush=True)
print('STOP_BEFORE_FINAL112_AND_CJ_SPEED',flush=True)
