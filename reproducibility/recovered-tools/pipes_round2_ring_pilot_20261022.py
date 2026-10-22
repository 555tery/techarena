import sys,json,re,math,statistics,time,subprocess
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
CORE='core-qualified';RING='core-ring';CPP='recycled_deleted_band';DIAG='core-mc-diagnostic'
meta={m['id']:m for m in e.inputs('archive')};cpp=e._evaluations(CPP,'archive');assert len(cpp)==2861
assert not any(q.get('type')=='selection_freeze'for q in e.rows())
long=[i for i,m in meta.items()if not m.get('public_number')and m['operation_count']>=100000]
rank=lambda i:-(cpp[i].get('solver_cpu_total_s')or 0)
mc_pool=sorted([i for i in long if meta[i]['peak_live_pipe_length_m']<=4096],key=lambda i:(rank(i),i))
large=sorted([i for i in long if meta[i]['peak_live_pipe_length_m']>4096*40],key=lambda i:(rank(i),i))
general=large[:10]
if len(general)<10:general+= [i for i in sorted(long,key=lambda i:(rank(i),i))if i not in general][:10-len(general)]
assert len(mc_pool)>=10 and len(general)==10
pins={k:dict(source_sha256=e.sha(e.artifact(k,'cj')[0].read_bytes()),binary_sha256=e.sha(e.artifact(k,'cj')[1].read_bytes()))for k in [CORE,RING]}
e.record(dict(type='ring_pilot_preselection_plan',mc_candidate_ids=mc_pool,general_heavy_ids=general,
    selection='old nonpublic N>=100000; MC candidate peak live volume<=4096 implies <=4096 live pipes, ranked by existing CPP CPU; qualify counter>0. General top10 CPP CPU with peak live volume>163840 proves >4096 active at some point.',
    artifacts=pins,repeats_per_case=2,envvariant='cjProcessorNum=1',mc_geomean_gate=.99,
    cpu_strict_s=5,rss_strict_mib=256,cpu_review_pause_s=4.5,before_native_pilot=True,final_read=False))
# A stderr-only diagnostic, leaving every solver stdout response unchanged.
source0=e.artifact(CPP,'cpp')[0];text=source0.read_text()
anchor='  if(online) cerr<<"reclaimed_reservation_m="'
assert text.count(anchor)==1
line='  if(online) cerr<<"diagnostic_mc_decisions="<<online->mcDecisionsUsed<<" active_pipes_at_end="<<online->activePipeCount<<"\\n";\n'
text=text.replace(anchor,line+anchor)
source=e._immutable_source(e.E/DIAG/'solution.cpp',text);binary=e.E/'bin'/(DIAG+'-cpp')
command=['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=5',str(source),'-o',str(binary)]
q=subprocess.run(command,capture_output=True,text=True)
e.record(dict(type='build',kind=DIAG,language='cpp',source=str(source),source_sha256=e.sha(source.read_bytes()),
 parent_source_sha256=e.sha(source0.read_bytes()),binary=str(binary),binary_sha256=e.sha(binary.read_bytes())if q.returncode==0 else None,
 command=command,status=q.returncode,stderr=q.stderr[-2500:],diagnostic_only=True,change='stderr mcDecisionsUsed counter only'))
assert q.returncode==0,q.stderr
qualified=[]
for i in mc_pool:
    m=meta[i];r=e.batch(m,DIAG,'mc-activation-diagnostic')
    assert r['response_sha256']==cpp[i]['response_sha256'],(i,'diagnostic changed output')
    match=re.search(r'diagnostic_mc_decisions=(\d+)',r.get('candidate_stderr',''));count=int(match[1])if match else 0
    assert count<=32
    if count>0:qualified.append(dict(id=i,mc_decisions=count,n=m['operation_count'],peak_live_volume=m['peak_live_pipe_length_m'],test_sha256=m['test_sha256']))
    print('MC_DIAGNOSTIC',i,count,len(qualified),flush=True)
    if len(qualified)==10:break
assert len(qualified)>=10,'not enough strongly bounded MC-active heavy cases; review instead of changing panel eligibility'
mc=[x['id']for x in qualified]
e.record(dict(type='ring_pilot_panel_freeze',mc_active_cases=qualified,general_heavy_ids=general,artifacts=pins,
  diagnostic_source_sha256=e.sha(source.read_bytes()),diagnostic_binary_sha256=e.sha(binary.read_bytes()),
  selection_before_native_timings=True,repeats_per_case=2,alternated_pairs=True,
  gate='MC paired geometric mean CPU ratio<=0.99; complete output hashes equal CPP/core; every CPU<5/RSS<256; review at CPU>=4.5',
  general_runtime_separate=True,envvariant='cjProcessorNum=1',final_read=False))
# Check the one old input where the quality core actually changes KPI.
i='certified-cohort_dev_02_01'
for k in [CORE,RING]:
    r=e.cj_resource_review(e.batch(meta[i],k,'core-mechanism-cj-parity','cj'))
    assert r['response_sha256']==cpp[i]['response_sha256'],(k,i,'Cj core mechanism differs from CPP')
print('CORE_MECHANISM_CPP_CJ_PARITY_OK',flush=True)

def panel(label,ids):
    pairs=[]
    for repeat in range(2):
        for j,i in enumerate(ids):
            current={}
            kinds=[CORE,RING]if(repeat+j)%2==0 else[RING,CORE]
            for k in kinds:
                r=e.native(meta[i],k,f'ring-{label}-repeat{repeat+1}','cj',processor_env='1')
                assert r['binary_sha256']==pins[k]['binary_sha256']
                assert r['response_sha256']==cpp[i]['response_sha256'],(k,i,'native Cj != checked CPP')
                current[k]=r
            assert current[CORE]['response_sha256']==current[RING]['response_sha256']
            pairs.append((i,repeat,current[CORE],current[RING]))
            if(j+1)%2==0:print('PILOT',label,repeat+1,j+1,len(ids),flush=True)
    ratios=[b['solver_cpu_total_s']/a['solver_cpu_total_s']for _,_,a,b in pairs]
    before=sum(meta[i].get('weight',1.)*a['solver_cpu_total_s']for i,_,a,b in pairs)
    after=sum(meta[i].get('weight',1.)*b['solver_cpu_total_s']for i,_,a,b in pairs)
    result=e.record(dict(type='ring_pilot_panel_result',panel=label,n_cases=len(ids),pairs=len(pairs),ids=ids,
        geometric_cpu_ratio=math.exp(statistics.fmean(math.log(x)for x in ratios)),median_cpu_ratio=statistics.median(ratios),
        arithmetic_cpu_ratio=statistics.fmean(ratios),minimum_cpu_ratio=min(ratios),maximum_cpu_ratio=max(ratios),
        weighted_total_core_cpu_s=before,weighted_total_ring_cpu_s=after,weighted_runtime_ratio=after/before,
        weights='frozen input manifest weight on this selected sample; not a claim about hidden-test distribution',
        max_core_cpu_s=max(a['solver_cpu_total_s']for _,_,a,b in pairs),max_ring_cpu_s=max(b['solver_cpu_total_s']for _,_,a,b in pairs),
        max_core_rss_mib=max(a['solver_peak_rss_mb']for _,_,a,b in pairs),max_ring_rss_mib=max(b['solver_peak_rss_mb']for _,_,a,b in pairs),
        complete_response_hash_parity=True,all_within_strict_limits=True,envvariant='cjProcessorNum=1',
        resource_scope='whole process user+system and RSS; one benchmark worker; local M1 only; scheduler env does not cap all GC/native threads'))
    print('PANEL_RESULT',json.dumps(result,ensure_ascii=False),flush=True)
    return result

mc_result=panel('mc-active',mc)
general_result=panel('general-heavy',general)
passed=mc_result['geometric_cpu_ratio']<=.99
selected=RING if passed else CORE
result=e.record(dict(type='ring_speed_gate_result',passes=passed,selected=selected,
    mc_geometric_cpu_ratio=mc_result['geometric_cpu_ratio'],general_geometric_cpu_ratio=general_result['geometric_cpu_ratio'],
    general_weighted_runtime_ratio=general_result['weighted_runtime_ratio'],cpu_strict_s=5,rss_strict_mib=256,
    complete_output_hash_parity=True,all_within_limits=True,quality_policy_unchanged=True,final_still_sealed=True,promotion=False))
print('RING_GATE_RESULT',json.dumps(result),flush=True)
print('PILOT_DONE_STOP_BEFORE_FINAL_FREEZE',flush=True)
