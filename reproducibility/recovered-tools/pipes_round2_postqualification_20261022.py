import sys,json,subprocess,time,collections,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
KIND='core-full-comparative';CORE='recycled_deleted_band'
PILOT=Path('/tmp/pipes_fixedprefix_suffix_pilot_20261022')

def emit(label,value):print(label,json.dumps(value,ensure_ascii=False),flush=True)
def pilot():
    assert not any(q.get('type')=='fixedprefix_suffix_pilot_plan'for q in e.rows()),'one-shot pilot already planned/executed; review instead of rerun'
    manifest=json.loads((PILOT/'manifest.json').read_text());source=PILOT/'pilot.cpp'
    assert e.sha(source.read_bytes())==manifest['pilot_cpp_sha256']=='0448d36ebaabcaea50a91ef242d2d6f9ca46fd6feee0da1ba57b4bf7d89fc343'
    assert e.sha(Path(manifest['files']['runtime_source.cpp']).read_bytes())==manifest['hashes']['RUNTIME_SHA']
    assert e.sha(Path(manifest['files']['prepared.in']).read_bytes())==manifest['hashes']['PREPARED_INPUT_SHA']
    e.record(dict(type='fixedprefix_suffix_pilot_plan',scope='single public15 offline diagnostic; no production candidate or modes/tuning',
        manifest_sha256=e.sha((PILOT/'manifest.json').read_bytes()),pilot_source_sha256=e.sha(source.read_bytes()),
        build_argv=manifest['build_argv'],run_argv=manifest['run_argv'],selection_freeze_unchanged=True))
    started=time.monotonic();q=subprocess.run(manifest['build_argv'],capture_output=True,text=True)
    e.record(dict(type='fixedprefix_suffix_pilot_build',status=q.returncode,wall_s=time.monotonic()-started,
        command=manifest['build_argv'],stderr=q.stderr[-3000:],source_sha256=e.sha(source.read_bytes())))
    assert q.returncode==0,q.stderr
    started=time.monotonic();q=subprocess.run(manifest['run_argv'],capture_output=True,text=True,timeout=240)
    result=json.loads(q.stdout);result.update(type='fixedprefix_suffix_pilot_result',returncode=q.returncode,
        wall_s=time.monotonic()-started,binary_sha256=e.sha(Path(manifest['run_argv'][0]).read_bytes()),
        pilot_source_sha256=e.sha(source.read_bytes()),stderr=q.stderr[-2500:],promotion=False,
        scope='offline public15 diagnostic; post round2 qualification; not a frozen quality candidate')
    e.record(dict(result,type='fixedprefix_suffix_pilot_execution'))
    if q.returncode==0 and result.get('status')=='ok' and result.get('gain'):
        meta=next(m for m in e.inputs('archive')if m.get('public_number')==15)
        assert meta['final_occupied_length_m']==result['F']
        with tempfile.TemporaryDirectory(prefix='pipes-suffix-official-')as td:
            checked=e._official(meta,Path(result['response_file']),Path(td))
        assert checked['trench_length_m']==result['finalT'] and abs(checked['kpi']-result['kpi'])<1e-12
        result.update(official_complete_response_checker=True,official_score=checked,response_sha256=e.sha(Path(result['response_file']).read_bytes()))
    e.record(result);emit('SUFFIX_PILOT',result)
    assert q.returncode==0 and result.get('status')=='ok',result
    # Integration is root-only even if the diagnostic improves.
    return result

def full264():
    source,binary0=e.artifact(CORE,'cpp');assert e.sha(source.read_bytes())=='1cb3af5bba22e7176d7533d2c20ff6dab5b96bc0cdf1c1ac3046b537ccdcd1b0'
    binary=e.E/'bin'/(KIND+'-cpp')
    argv=['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=0',str(source),'-o',str(binary)]
    q=subprocess.run(argv,capture_output=True,text=True)
    e.record(dict(type='build',kind=KIND,language='cpp',source=str(source),source_sha256=e.sha(source.read_bytes()),
        binary=str(binary),binary_sha256=e.sha(binary.read_bytes())if q.returncode==0 else None,
        command=argv,status=q.returncode,stderr=q.stderr[-3000:],comparative_only=True,
        relation='same pinned current recycled core, only REPLAY_GUARD5→0 compiler flag; not a selected round2 quality candidate'))
    assert q.returncode==0,q.stderr
    archive=e.inputs('archive');new=e.inputs('development')+e.inputs('sealed_final')
    public=[m for m in archive if m.get('public_number')];assert len(public)==15
    ms=[m for m in archive if m['provenance']=='previous_certified96']+new;assert len(ms)==264
    e.record(dict(type='comparative_full264_plan',kind=KIND,count=264,ids=[m['id']for m in ms],
        same_source_sha256=e.sha(source.read_bytes()),baseline_current_core=CORE,postqualification=True,
        role='comparative baseline for next round only; not new round2 quality candidate; no retrospective gate changes'))
    started=time.monotonic()
    sanity=[]
    for m in public:sanity.append(e.batch(m,KIND,'comparative-full-open15','cpp'))
    opened=sum(m['weight']*r['kpi']for m,r in zip(public,sanity))
    emit('FULL_OPEN15_SANITY',e.record(dict(type='comparative_full_open15',kind=KIND,count=15,
        weighted_Open=opened,all_complete_responses_checked=True,wall_s=time.monotonic()-started,promotion=False)))
    refs={**e._evaluations(CORE,'archive','cpp'),**e._evaluations(CORE,'development','cpp'),**e._evaluations('core-ring','sealed_final','cpp')}
    started=time.monotonic();values={}
    for j,m in enumerate(ms):
        # Root explicitly authorized these already-open final data for a postqualification comparator.
        # The immutable round2 selection and its results remain unchanged.
        comparative=dict(m,original_split=m['split'],split='postqualification-comparative')
        values[m['id']]=e.batch(comparative,KIND,'comparative-full264','cpp')
        if(j+1)%16==0 or j+1==len(ms):emit('FULL264_PROGRESS',dict(completed=j+1,total=len(ms),elapsed_s=time.monotonic()-started))
    groups=collections.defaultdict(list)
    for m in ms:
        groups['all264'].append(m['id']);groups['provenance:'+m['provenance']].append(m['id']);groups['family:'+m.get('family','unknown')].append(m['id'])
    comparisons={name:e.paired(values,refs,ids)for name,ids in groups.items()}
    worst=sorted(ms,key=lambda m:values[m['id']]['kpi']-refs[m['id']]['kpi'])[:10]
    worst=[dict(id=m['id'],provenance=m['provenance'],family=m.get('family'),delta_kpi=values[m['id']]['kpi']-refs[m['id']]['kpi'],core_kpi=refs[m['id']]['kpi'],full_kpi=values[m['id']]['kpi'])for m in worst]
    emit('FULL264_RESULT',e.record(dict(type='comparative_full264_result',kind=KIND,count=264,
        comparisons=comparisons,worst=worst,wall_s=time.monotonic()-started,full_Open15=opened,
        validation_counts=dict(collections.Counter(q['validation']for q in values.values())),
        actual_complete_outputs_checked=True,promotion=False,selection_freeze_unchanged=True,
        role='fair current-core full comparator for future round; no retrospective round2 gate change')))

if __name__=='__main__':
    assert any(q.get('type')=='round2_qualification_result'and q.get('qualified')for q in e.rows()),'finish current qualification first'
    mode=sys.argv[1]
    if mode=='pilot':pilot()
    elif mode=='full264':full264()
    else:raise ValueError(mode)
