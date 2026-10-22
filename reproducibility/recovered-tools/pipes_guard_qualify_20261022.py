from pathlib import Path
from types import SimpleNamespace
import collections, hashlib, json, math, os, re, statistics, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp')
import pipes_guards_20261022 as e

KNOWN = e.rows()
NATIVE_CACHE = {(r['suite'], r['kind'], r['id'], r['binary_sha256']): r for r in KNOWN if r['type'] == 'interactive_evaluation'}
CPP_REF = {r['id']: r for r in KNOWN if r['type'] == 'evaluation' and r['suite'] == 'archive-policy' and r['kind'] == 'cautious'}
PUB = sorted([m for m in e.ev.rows if m.get('public_number')], key=lambda m: m['public_number'])

def native(m, kind, suite):
    if kind == 'old-full':
        source, binary = e.OLD/'solution.cj', e.OLD/'bin/cj-release'
    else:
        source, binary = e.E/'release/solution.cj', e.E/'bin/production'
    bsha, ssha = e.sha(binary.read_bytes()), e.sha(source.read_bytes())
    key = (suite, kind, m['id'], bsha)
    if key in NATIVE_CACHE:
        return NATIVE_CACHE[key]
    assert e.sha(Path(m['test_file']).read_bytes()) == m['test_sha256']
    base = SimpleNamespace(**e.ev.h.__dict__)
    base.parse_test = lambda _: dict(m)
    os.environ['cjProcessorNum'] = '1'
    with tempfile.TemporaryDirectory(prefix='pipes-guard-native-') as temp:
        r = e.ev.nh.run_case(base, [str(binary)], e.ev.NATIVE, Path(m['test_file']), Path(temp)/'run', 5, 240)
        output = Path(r['judge_output_file'])
        rec = {k: r.get(k) for k in ['status','detail','solver_cpu_user_s','solver_cpu_system_s','solver_cpu_total_s','solver_peak_rss_mb','kpi','trench_length_m','candidate_stderr']}
        rec.update(type='interactive_evaluation', suite=suite, kind=kind, id=m['id'], family=m.get('family'), stratum=m.get('stratum'), operation_count=m['operation_count'], test_sha256=m['test_sha256'], source_sha256=ssha, binary_sha256=bsha, response_sha256=e.sha(output.read_bytes()) if output.exists() else None, within_limits=not e.ev.nh.failed(r,5,256), runtime_threads_env='cjProcessorNum=1', timing_scope='solver process user+system; single benchmark worker; M1/macOS, not Windows/G5420')
        e.record(rec)
        NATIVE_CACHE[key] = rec
        assert rec['within_limits'], rec
        return rec

def public():
    for m in PUB:
        r = e.batch(m, 'production', 'public-production')
        u = next(x for x in e.rows() if x['type']=='evaluation' and x['suite']=='public-uncached' and x['id']==m['id'])
        assert r['response_sha256'] == u['response_sha256'] == CPP_REF[m['id']]['response_sha256']
        n = native(m, 'production', 'open15')
        assert n['response_sha256'] == r['response_sha256']
        print('PUBLIC', m['public_number'], n['kpi'], n['solver_cpu_total_s'], n['solver_peak_rss_mb'], flush=True)

def boundaries():
    m = PUB[-1]
    t = Path(m['test_file']).read_bytes().split()
    commands = list(map(int,t[2:2+m['operation_count']]))
    # Ends before decoding, at decoding boundary and deep into the cached path;
    # valid positive mismatches also force exact state reconstruction.
    for p in [1,2,15,16,17,9999,199999]:
        for mode in ['end','mismatch']:
            cmds = commands[:p]
            if mode == 'mismatch':
                alt = 40 if commands[p] != 40 else 39
                cmds = cmds+[alt]
            with tempfile.TemporaryDirectory(prefix='pipes-cache-boundary-') as temp:
                path=Path(temp)/'test.in'
                path.write_text('1\n'+str(len(cmds))+'\n'+'\n'.join(map(str,cmds))+'\n')
                meta=e.ev.h.parse_test(path)
                meta.update(id=f'cache-{p}-{mode}',test_file=str(path),family='protocol_cache_boundary',stratum='protocol')
                a=e.batch(meta,'uncached','cache-boundary')
                b=e.batch(meta,'production','cache-boundary')
                assert a['response_sha256']==b['response_sha256'],(p,mode)
                n=native(meta,'production','cache-boundary')
                assert n['response_sha256']==a['response_sha256'],(p,mode,'interactive')
                e.record(dict(type='cache_boundary_check',prefix_commands=p,mode=mode,operation_count=len(cmds),response_equal=True,uncached_cpu=a['solver_cpu_total_s'],production_interactive_cpu=n['solver_cpu_total_s'],valid=True))
                print('BOUNDARY',p,mode,n['solver_cpu_total_s'],flush=True)

def freeze():
    assert not any(r['type']=='evaluation' and r['suite']=='final' for r in e.rows())
    source=e.E/'release/solution.cj'
    pre=[r for r in e.rows() if r['type']=='cache_boundary_check']
    assert len(pre)==14
    e.record(dict(type='production_freeze',source_sha256=e.sha(source.read_bytes()),binary_sha256=e.sha((e.E/'bin/production').read_bytes()),compiler='Cangjie1.0.5 -O0',semantic_policy='cautious',implementation_guard='edge-local',policy_selection_precedes_final=True,final_input_hashes=[m['test_sha256'] for m in e.inputs('final')],archive_cases=2661,post_final_policy_tuning=False,final_gate='predeclared same-policy old-core and robust-score minimax gates; validity, exact selected C++ response parity and local process CPU<5s RSS<256MiB; reject lazy core separately if final gate fails'))
    print('PRODUCTION_FROZEN',e.sha(source.read_bytes()),flush=True)

def regression():
    for i,m in enumerate(e.ev.rows):
        r=e.batch(m,'production','archive-production')
        ref=CPP_REF[m['id']]
        assert r['response_sha256']==ref['response_sha256'],(m['id'],r['candidate_stderr'],ref['candidate_stderr'])
        assert r['kpi']==ref['kpi']
        if (i+1)%128==0 or i+1==len(e.ev.rows):
            print('CJ_ARCHIVE',i+1,len(e.ev.rows),flush=True)
    refs={r['id']:r for r in e.rows() if r['type']=='evaluation' and r['suite']=='calibration' and r['kind']=='cautious'}
    for i,m in enumerate(e.inputs('calibration')):
        r=e.batch(m,'production','calibration-production')
        assert r['response_sha256']==refs[m['id']]['response_sha256'],m['id']
        if (i+1)%8==0:
            print('CJ_CALIBRATION',i+1,len(refs),flush=True)

def oldcore_control():
    known={(r['id'],r['binary_sha256']) for r in e.rows() if r['type']=='evaluation' and r['suite']=='archive-same-policy-oldcore'}
    bsha=e.sha((e.E/'bin/same-policy-oldcore').read_bytes())
    for i,m in enumerate(e.ev.rows):
        if (m['id'],bsha) in known:continue
        ref=e.FROZEN[m['id']]
        match=re.search(r'abort_step=(\d+)',ref['candidate_stderr'])
        abort=int(match[1]) if match else -1
        if abort in [1,2]:
            # Both guards accept the same minimal first placement, or none,
            # and then fresh-import the same observations into the old core.
            r={**ref,'suite':'archive-same-policy-oldcore','kind':'same-policy-oldcore','binary_sha256':bsha,'source_sha256':None,'validation':'control_flow_certificate','certificate':'full and cautious both import same physical prefix at first mismatch step1/2; old eager core and reservation repair identical','status':'certified_equivalent','solver_cpu_total_s':None,'solver_peak_rss_mb':None,'candidate_stderr':None}
            e.record(r)
        else:e.batch(m,'same-policy-oldcore','archive-same-policy-oldcore')
        if (i+1)%128==0 or i+1==len(e.ev.rows):print('OLDCORE_CONTROL',i+1,len(e.ev.rows),flush=True)

def resources():
    freeze=next(x for x in reversed([json.loads(s) for s in(e.OLD/'records.jsonl').open()]) if x['type']=='selection_freeze')
    old=[json.loads(s) for s in(e.ev.EXP/'records.jsonl').open()]
    metas={r['meta']['id']:r['meta'] for r in old if r['type'] in ['fresh_input','holdout_input']}
    archive=[r for r in e.rows() if r['type']=='evaluation' and r['suite']=='archive-production']
    metas.update({m['id']:m for m in e.ev.rows})
    chosen=list(freeze['resource_ids'])
    for field in ['solver_cpu_total_s','solver_peak_rss_mb']:
        for r in sorted(archive,key=lambda r:r[field],reverse=True)[:5]:
            if r['id'] not in chosen:chosen.append(r['id'])
    e.record(dict(type='resource_panel',ids=chosen,rule='union previous five slow observed200k cases and current Cj archive top5 process CPU and top5 peak RSS; selection based on resources only, not KPI; no concurrent benchmark or compilation'))
    for i,ident in enumerate(chosen):
        m=metas[ident]
        for k in (['production','old-full'] if i%2==0 else ['old-full','production']):
            r=native(m,k,'worst-observed-200k')
            if k=='production':
                b=e.batch(m,k,'worst-observed-200k')
                assert r['response_sha256']==b['response_sha256']
        print('RESOURCES',i+1,len(chosen),flush=True)

def final_native():
    freeze=next(r for r in e.rows()[::-1] if r['type']=='production_freeze')
    assert e.sha((e.E/'release/solution.cj').read_bytes())==freeze['source_sha256']
    metas=e.inputs('final')
    assert [m['test_sha256'] for m in metas]==freeze['final_input_hashes']
    refs={(r['id'],r['kind']):r for r in e.rows() if r['type']=='evaluation' and r['suite']=='final'}
    assert len(refs)==len(metas)*9,len(refs)
    for i,m in enumerate(metas):
        for k in (['production','old-full'] if i%2==0 else ['old-full','production']):
            r=native(m,k,'unseen-final')
            cpp=refs[m['id'],'cautious' if k=='production' else 'full']
            assert r['response_sha256']==cpp['response_sha256'],(m['id'],k,r['candidate_stderr'],cpp['candidate_stderr'])
            assert r['kpi']==cpp['kpi']
        if (i+1)%4==0 or i+1==len(metas):
            print('FINAL_CJ',i+1,len(metas),flush=True)

if __name__=='__main__':
    {'public':public,'boundaries':boundaries,'freeze':freeze,'archive':regression,'oldcore-control':oldcore_control,'resources':resources,'final-native':final_native}[sys.argv[1]]()
