import sys,json,math,statistics,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
SELECTED='core-ring';CPP='recycled_deleted_band'

def emit(label,value):print(label,json.dumps(value,ensure_ascii=False),flush=True)
def selected_evaluations(split):
    return e._evaluations(CPP,split,'cpp') if split!='sealed_final' else e._evaluations(SELECTED,split,'cpp')

def run():
    speed=next(q for q in e.rows()[::-1]if q.get('type')=='ring_speed_gate_result')
    assert speed['passes'] and speed['selected']==SELECTED
    archive=e.inputs('archive');dev=e.inputs('development');final=e.inputs('sealed_final',allow_final=True)
    assert len(archive)==2861 and len(dev)==56 and len(final)==112
    assert e.artifact(SELECTED,'cpp')==e.artifact(CPP,'cpp')
    old104=[m['id']for m in archive if m['provenance']=='archive2765'][-104:]
    previous=[m['id']for m in archive if m['provenance']=='previous_certified96'];assert len(previous)==96
    pool=lambda provenance:[m['id']for m in final if m['provenance']==provenance]
    op=pool('round2_openlike96');pr=pool('round2_prefix24');gr=pool('round2_growing48');allids=[m['id']for m in final]
    assert (len(op),len(pr),len(gr))==(64,16,32)
    scenario={
        'both-final-openlike64':dict(cheap=op,expensive=op),
        'both-final-prefix16':dict(cheap=pr,expensive=pr),
        'both-final112':dict(cheap=allids,expensive=allids),
        'cheap-prior104-expensive-final112':dict(cheap=old104,expensive=allids),
        'cheap-previous96-expensive-final112':dict(cheap=previous,expensive=allids),
        'cheap-final-openlike64-expensive-final-prefix16':dict(cheap=op,expensive=pr),
        'both-final-growing32':dict(cheap=gr,expensive=gr)}
    gates=dict(quality_mean_delta_min=0.,quality_min_delta_min=-.02,
       all_scenario_S_delta_min=0.,scenarios=scenario,zero_invalid_and_local_TLE=True,
       strict_native_cpu_s=5.,review_pause_cpu_s=4.5,strict_native_rss_mib=256.,
       actual_cpp_cj_full_response_hash_parity=True,
       exact_ring_gate=dict(mc_geometric_cpu_ratio_max=.99,mc_cases_min=10,repeats=2,env='1'),
       baseline='0759 cached production policy, actual CPP baseline responses',
       no_post_final_refit=True,root_approved_before_final=True)
    selections=[q for q in e.rows()if q.get('type')=='selection_freeze']
    if not selections:e.freeze_selection(SELECTED,gates)
    else:assert len(selections)==1 and selections[0]['selected']==SELECTED and selections[0]['fixed_gates']==gates
    emit('SELECTION_FROZEN',e._selection()['artifacts'])
    e.batch_pairs(['baseline',SELECTED],'sealed_final','cpp')
    base={**e._evaluations('baseline','archive','cpp'),**e._evaluations('baseline','sealed_final','cpp')}
    candidate={**selected_evaluations('archive'),**selected_evaluations('sealed_final')}
    quality=e.paired(candidate,base,allids)
    public=[m for m in archive if m.get('public_number')];assert len(public)==15
    score={}
    for k,values in [('baseline',base),(SELECTED,candidate)]:
        opened=math.fsum(m['weight']*values[m['id']]['kpi']for m in public);score[k]={}
        for name,p in scenario.items():
            c=statistics.fmean(values[i]['kpi']for i in p['cheap']);x=statistics.fmean(values[i]['kpi']for i in p['expensive'])
            bonus=e.expected_best2of4([values[i]['kpi']for i in p['expensive']])
            score[k][name]=dict(Open=opened,cheap_mean=c,expensive_mean=x,expected_best2of4_sum=bonus,S=opened+44*c+40*x+10*bonus)
    delta={name:score[SELECTED][name]['S']-score['baseline'][name]['S']for name in scenario}
    passes=quality['mean']>=0 and quality['minimum']>=-.02 and min(delta.values())>=0
    cpp_result=e.record(dict(type='frozen_final_cpp_quality',selected=SELECTED,count=112,comparison=quality,
        strata={p:e.paired(candidate,base,ids)for p,ids in [('openlike64',op),('prefix16',pr),('growing32',gr)]},
        scenario_scores=score,scenario_S_delta=delta,passes=passes,
        source_alias_exact_hashes=True,zero_invalid_or_local_TLE=True,promotion=False))
    emit('FINAL_CPP_GATE',cpp_result)
    assert passes,'fixed independent final CPP quality gate failed; root review required'
    cj=[]
    for j,m in enumerate(final):
        r=e.native(m,SELECTED,'final-native-env1','cj',processor_env='1');e.cj_resource_review(r)
        assert r['response_sha256']==candidate[m['id']]['response_sha256'],('final CPP/Cj parity',m['id'])
        converted=e.batch(m,SELECTED,'sealed_final','cj');assert converted['response_sha256']==r['response_sha256']
        cj.append(r)
        if(j+1)%8==0 or j+1==len(final):emit('FINAL_CJ_PROGRESS',dict(completed=j+1,total=len(final)))
    emit('FINAL_CJ_VALIDATED',e.record(dict(type='frozen_final_cj_quality',selected=SELECTED,count=112,
        actual_complete_response_cpp_parity=True,official_native_checker_all=True,all_within_limits=True,
        comparison=quality,scenario_S_delta=delta,
        max_cpu_s=max(q['solver_cpu_total_s']for q in cj),max_rss_mib=max(q['solver_peak_rss_mb']for q in cj),
        envvariant='cjProcessorNum=1',promotion=False)))
    panel=next(q for q in e.rows()[::-1]if q.get('type')=='ring_pilot_panel_freeze')['general_heavy_ids']
    emit('ENV_PANEL',e.native_env_pairs(SELECTED,panel,'archive','cj'))
    emit('OPEN15_ENV_PANEL',e.native_env_pairs(SELECTED,[m['id']for m in public],'archive','cj'))
    # A divergence on the last command checks replay fallback after199999 matching commands.
    source=next(m for m in public if m['public_number']==15)
    tok=Path(source['test_file']).read_bytes().split();commands=tok[2:2+source['operation_count']]
    assert len(commands)==200000
    replacement=b'39'if commands[-1]==b'40'else b'40'
    contents=b'1\n200000\n'+b'\n'.join(commands[:-1]+[replacement])+b'\n'
    folder=Path('/tmp/pipes_round2_protocol_20261022');folder.mkdir(exist_ok=True)
    path=folder/'late-cache-fork-199999.in'
    if path.exists():assert path.read_bytes()==contents
    else:path.write_bytes(contents)
    h,_=e.harness();m=dict(h.parse_test(path),id='round2-late-cache-fork-199999',split='protocol',test_file=str(path),provenance='protocol-not-quality')
    ref=e.batch(m,SELECTED,'late-cache-fork-reference','cpp');fork=[]
    for lang in ['cj','cj-uncached']:
        for env in ['1',None]:
            r=e.native(m,SELECTED,'late-cache-fork',lang,processor_env=env);e.cj_resource_review(r)
            assert r['response_sha256']==ref['response_sha256'],('late cache fork',lang,env)
            fork.append(r)
    emit('LATE_CACHE_FORK',e.record(dict(type='late_cache_fork_validation',selected=SELECTED,
        matching_public_commands_before_divergence=199999,divergence_command=200000,
        public_number=15,test_sha256=m['test_sha256'],actual_complete_response_cpp_cached_uncached_parity=True,
        environments=['cjProcessorNum=1','cjProcessorNum=UNSET'],all_within_limits=True,
        max_cpu_s=max(q['solver_cpu_total_s']for q in fork),max_rss_mib=max(q['solver_peak_rss_mb']for q in fork))))
    for split,ms in [('archive',archive),('development',dev)]:
        refs=selected_evaluations(split);assert len(refs)==len(ms),(split,len(refs),len(ms))
        started=time.monotonic();results=[]
        for j,m in enumerate(ms):
            r=e.batch(m,SELECTED,split,'cj');e.cj_resource_review(r)
            assert r['response_sha256']==refs[m['id']]['response_sha256'],('Cj port complete parity',split,m['id'])
            results.append(r)
            if(j+1)%40==0 or j+1==len(ms):emit('CJ_PORT_PROGRESS',dict(split=split,completed=j+1,total=len(ms),elapsed_s=time.monotonic()-started))
        emit('CJ_PORT_VALIDATED',e.record(dict(type='cj_port_validation',selected=SELECTED,split=split,count=len(ms),
            actual_complete_response_cpp_parity=True,reuse_only_same_source_binary_test_hash=True,
            max_cpu_s=max(q['solver_cpu_total_s']or 0 for q in results),max_rss_mib=max(q['solver_peak_rss_mb']or 0 for q in results),
            all_within_limits=True,resource_scope='batch diagnostics; separate native panels supply interactive resource evidence')))
    emit('QUALIFICATION_COMPLETE',e.record(dict(type='round2_qualification_result',selected=SELECTED,qualified=True,
        quality_policy='recycled_deleted_band core only; exact IntRing.clone speed patch',
        artifacts=e._selection()['artifacts'],final112_fixed_gate_pass=True,final_actual_cj_cpp_hash_parity=True,
        full_archive2861_and_dev56_cj_cpp_hash_parity=True,native_env_diagnostics_complete=True,
        late_cache_fork_pass=True,baseline_release_unchanged=True,promotion=False,
        resource_scope='local M1/macOS only; no Windows/server scaling claim; GC threshold not RSS cap')))

if __name__=='__main__':
    try:run()
    except BaseException as ex:
        e.record(dict(type='qualification_stopped_for_review',selected=SELECTED,exception=repr(ex),traceback=traceback.format_exc()[-3000:],promotion=False))
        raise
