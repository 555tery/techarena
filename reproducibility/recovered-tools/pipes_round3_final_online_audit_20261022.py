"""Frozen same-core guard4 comparison only. No Cj work, no final24, no tuning."""
import sys,json,time,math,statistics,subprocess,traceback,collections
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='final-online-audit';SUITE=K
DEADLINE=datetime(2026,10,22,23,24,40,tzinfo=ZoneInfo('Asia/Novosibirsk')).timestamp()
def note(t,**kw):
 r=b.record(dict(type=t,kind=K,**kw));print(t,json.dumps(r,ensure_ascii=False),flush=True);return r
def checktime():
 if time.time()>=DEADLINE:raise TimeoutError('same-core online audit hardstop before23:25')
def run():
 a.pins();checktime();allmeta=b.read_jsonl(b.MANIFEST)
 groups={
 'Open15':[m for m in allmeta if m.get('public_number')],
 'sensitivity36':[m for m in allmeta if m['split']=='sensitivity_development'],
 'previous_final112':[m for m in allmeta if m['split']=='archive'and m.get('round2_split')=='sealed_final']}
 assert [len(groups[k])for k in groups]==[15,36,112]
 ms=sum(groups.values(),[]);assert len(ms)==len({m['id']for m in ms})==163
 refs={}
 for r in b.read_jsonl(a.P/'records.jsonl')+b.rows():
  if r.get('type')=='evaluation'and r.get('language')=='cpp'and r.get('source_sha256')==a.CPP_SHA and r.get('binary_sha256')==a.CPP_BIN_SHA and r.get('status')=='ok':refs[(r['id'],r['test_sha256'])]=r
 c={m['id']:refs[(m['id'],m['test_sha256'])]for m in ms}
 for m in ms:
  r=c[m['id']];assert r['response_sha256']and r.get('validation')not in ['control_flow_certificate','certified_equivalent']
 source=b.BASE_CPP;assert b.sha(source.read_bytes())==a.CPP_SHA
 binary=b.E/'bin'/(K+'-cpp');command=['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1','-DLAZY_SLAB=1','-DREPLAY_GUARD=4',str(source),'-o',str(binary)]
 prior=next(r for r in b.rows()if r.get('type')=='sensitivity36_CEF_freeze')
 scenarios=dict(prior['scenarios'])
 prev=groups['previous_final112'];pg={p:[m['id']for m in prev if m['provenance']==p]for p in ['round2_openlike96','round2_prefix24','round2_growing48']}
 assert sorted(map(len,pg.values()))==[16,32,64]
 scenarios.update({'both-previous-final112':dict(cheap=[m['id']for m in prev],expensive=[m['id']for m in prev])})
 for p,ids in pg.items():scenarios['both-previous-final-'+p]=dict(cheap=ids,expensive=ids)
 assert not any(r.get('type')=='final_online_audit_freeze'for r in b.rows()),'single fixed audit already frozen'
 note('final_online_audit_freeze',before_first_solver_evaluation=True,source=str(source),source_sha256=a.CPP_SHA,command=command,baseline_C_binary_sha256=a.CPP_BIN_SHA,
  group_membership={k:[dict(id=m['id'],test_sha256=m['test_sha256'],baseline_response_sha256=c[m['id']]['response_sha256'])for m in v]for k,v in groups.items()},
  scenarios=scenarios,formula='Open+44*meanCheap+40*meanExpensive+10*E[sum best2of4 without replacement]',no_Cj_ports=True,no_full3029=True,round3_final24_still_sealed=True,no_postanswer_tuning=True,deadline_local='23:25')
 t=time.monotonic();q=subprocess.run(command,capture_output=True,text=True,timeout=90)
 build=b.record(dict(type='build',kind=K,language='cpp',source=str(source),source_sha256=a.CPP_SHA,binary=str(binary),binary_sha256=b.sha(binary.read_bytes())if q.returncode==0 else None,command=command,status=q.returncode,stderr=q.stderr[-2500:],same_current_core_guard_switch_only=True))
 assert q.returncode==0,q.stderr;print('ONLINE_CPP_BUILT',build['binary_sha256'],flush=True)
 online={}
 for j,m in enumerate(ms):
  checktime();q=b.batch(m,K,SUITE,'cpp');assert q['source_sha256']==a.CPP_SHA and q['binary_sha256']==build['binary_sha256']and q['status']=='ok'
  online[m['id']]=q
  if(j+1)%12==0 or j+1==len(ms):print('ONLINE_AUDIT',j+1,len(ms),'elapsed',round(time.monotonic()-t,2),flush=True)
 opens={label:math.fsum(m['weight']*v[m['id']]['kpi']for m in groups['Open15'])for label,v in [('C',c),('online',online)]}
 def describe(ids):
  ds=[online[i]['kpi']-c[i]['kpi']for i in ids]
  return dict(n=len(ids),online_wins=sum(d>1e-12 for d in ds),ties=sum(abs(d)<=1e-12 for d in ds),online_losses=sum(d< -1e-12 for d in ds),mean_delta=sum(ds)/len(ds),minimum_delta=min(ds),maximum_delta=max(ds),C_mean=statistics.fmean(c[i]['kpi']for i in ids),online_mean=statistics.fmean(online[i]['kpi']for i in ids),exact_complete_response_ties=sum(online[i]['response_sha256']==c[i]['response_sha256']for i in ids))
 comparisons={k:describe([m['id']for m in v])for k,v in groups.items()}
 for origin in ['Open12','Open14','independent']:
  comparisons['sensitivity36:'+origin]=describe([m['id']for m in groups['sensitivity36']if m['origin']==origin])
 for p,ids in pg.items():comparisons['previous_final112:'+p]=describe(ids)
 def score(v,op,pools):
  cheap=[v[i]['kpi']for i in pools['cheap']];expensive=[v[i]['kpi']for i in pools['expensive']]
  return op+44*statistics.fmean(cheap)+40*statistics.fmean(expensive)+10*b.expected_best2of4(expensive)
 scores={s:{label:score(v,opens[label],pools)for label,v in [('C',c),('online',online)]}for s,pools in scenarios.items()}
 deltaS={s:r['online']-r['C']for s,r in scores.items()}
 allworst=sorted([(online[m['id']]['kpi']-c[m['id']]['kpi'],m)for m in ms],key=lambda x:x[0])
 worst=[dict(id=m['id'],group=next(k for k,v in groups.items()if m in v),origin=m.get('origin'),family=m.get('family'),n=m['operation_count'],delta=d,C_KPI=c[m['id']]['kpi'],online_KPI=online[m['id']]['kpi'],C_T=c[m['id']]['trench_length_m'],online_T=online[m['id']]['trench_length_m'])for d,m in allworst[:8]]
 best=[dict(id=m['id'],delta=d,C_KPI=c[m['id']]['kpi'],online_KPI=online[m['id']]['kpi'])for d,m in allworst[-5:]]
 note('final_online_audit_result',count=163,source_sha256=a.CPP_SHA,online_binary_sha256=build['binary_sha256'],baseline_C_binary_sha256=a.CPP_BIN_SHA,actual_Open15=opens,Open_online_minus_C=opens['online']-opens['C'],comparisons=comparisons,worst=worst,best=best,scenario_scores_with_hypothetical_Cj_bonus=scores,scenario_online_minus_C=deltaS,
  maximum_CPP_cpu_s=max(q['solver_cpu_total_s']for q in online.values()),maximum_CPP_rss_mib=max(q['solver_peak_rss_mb']for q in online.values()),validation_counts=dict(collections.Counter(q['validation']for q in online.values())),wall_s=time.monotonic()-t,
  limitations='conditional scenario weights, not hidden probability; same-core CPP policy audit, no Cj port/resource/server validation; previous112 now reused archive; final24 untouched',round3_final24_still_sealed=True,no_automatic_promotion=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:note('final_online_audit_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2200:],no_automatic_restart=True);raise
