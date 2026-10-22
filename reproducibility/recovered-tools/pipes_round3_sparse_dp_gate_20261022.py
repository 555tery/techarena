"""Single fixed exact-speed sparse-DP pilot; no corpus rerun or platform."""
import sys,json,time,traceback,math,statistics
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;K='sparse-dp';P=Path('/tmp/pipes_sparse_dp_uncached_20261022.cj');SHA='29822682b49175c27941e3c808ec05b759855c2538d3a122ee4394796dee7693'
BASESHA='f1f6240fb7ca7e099408a02bb2aeb9926f4240425afbd7be4eebd25ee6a2ac4a';BASEBIN='776dbfc882b3f833979d30e7aba57dba14374f124cb6c3a633fca67b135d98ad'
DEADLINE=datetime(2026,10,22,23,58,30,tzinfo=ZoneInfo('Asia/Novosibirsk')).timestamp()
def note(t,**kw):
 r=b.record(dict(type=t,kind=K,**kw));print(t,json.dumps(r,ensure_ascii=False),flush=True);return r
def check(q,m):
 assert q['status']=='ok'and q['response_sha256']==m['baseline_response_sha256'],('complete response mismatch',m['id'],q)
 assert q['solver_cpu_total_s']<4.5 and q['solver_peak_rss_mb']<230.,q
 return q
def deadline():
 if time.time()>DEADLINE:raise TimeoutError('sparse speed gate deadline')
def run():
 a.pins();assert b.sha(P.read_bytes())==SHA
 parent,basebin=b.artifact('boundary-index','cj-uncached');assert b.sha(parent.read_bytes())==BASESHA and b.sha(basebin.read_bytes())==BASEBIN
 assert 'class Transcript15 {'not in P.read_text()
 archive=b.inputs('archive');public=sorted([m for m in archive if m.get('public_number')],key=lambda m:m['public_number']);assert len(public)==15
 prior=next(q for q in b.read_jsonl(a.P/'records.jsonl')if q.get('type')=='ring_pilot_panel_freeze');meta={m['id']:m for m in archive}
 heavy=prior['general_heavy_ids'][:3];assert all(meta[i]['operation_count']==200000 for i in heavy)
 traps=['final-prefix-renewal-04','final-prefix-renewal-16','15f382e19a19d13d3ec562ba5d5d43ee3a47a238e74874d79ab40182e09c4f10'];ids=heavy+traps;assert len(set(ids))==6
 assert not any(q.get('type')=='sparse_dp_gate_freeze'for q in b.rows())
 note('sparse_dp_gate_freeze',before_first_execution=True,candidate_source_sha256=SHA,parent_uncached_source_sha256=BASESHA,parent_uncached_binary_sha256=BASEBIN,compiler='SDK1.0.5 -O0',Open15_ids=[m['id']for m in public],heavy_and_trap_ids=ids,test_hashes={i:meta[i]['test_sha256']for i in ids},cpu15_repeats_env1=2,cpu15_extra_envUNSET_pair=True,cpu15_pair_order='baseline/candidate then candidate/baseline; UNSET candidate/baseline',strict_cpu_s=4.5,strict_rss_mib=230.,full3029_not_repeated=True,limited_pilot_only=True,original_sources_preserved=True,no_platform=True)
 source=b._immutable_source(b.E/K/'uncached/solution.cj',P.read_text());binary=b.E/'bin/sparse-dp-cj-uncached'
 built=b._compile_cj_source(K,'cj-uncached',source,binary,parent_source_sha256=BASESHA,output_cache=False)
 for j,m in enumerate(public):
  deadline();check(b.batch(m,K,'sparse-open15','cj-uncached'),m);print('SPARSE_OPEN',j+1,15,flush=True)
 artifacts=dict(source=str(source),source_sha256=SHA,binary=str(binary),binary_sha256=built['binary_sha256'])
 note('sparse_dp_open15_pass',**artifacts,all15_actual_complete_CPP_G5_byteparity=True,Open15=30.05605802561868,matched_CPU15_pending=True,heavy_traps_pending=True)
 m=next(m for m in public if m['public_number']==15);observations=[]
 for rep in range(2):
  pair={}
  for k in (['boundary-index',K]if rep==0 else[K,'boundary-index']):
   deadline();pair[k]=check(b.native(m,k,f'sparse-cpu15-r{rep+1}','cj-uncached',processor_env='1'),m)
  observations.append(dict(repeat=rep+1,baseline_cpu_s=pair['boundary-index']['solver_cpu_total_s'],candidate_cpu_s=pair[K]['solver_cpu_total_s'],ratio=pair[K]['solver_cpu_total_s']/pair['boundary-index']['solver_cpu_total_s']))
 ratio=math.exp(statistics.fmean(math.log(q['ratio'])for q in observations))
 note('sparse_dp_cpu15_early_result',**artifacts,pairs=observations,geometric_candidate_to_baseline_CPU_ratio=ratio,all_exact=True,scope='2 matched M1 process CPU pairs env1; not server or corpus evidence',heavy_traps_pending=True)
 unset={}
 for k in [K,'boundary-index']:
  deadline();unset[k]=check(b.native(m,k,'sparse-cpu15-UNSET','cj-uncached',processor_env=None),m)
 qs=[]
 for j,i in enumerate(ids):
  deadline();qs.append(check(b.native(meta[i],K,'sparse-fixed-heavy-traps','cj-uncached',processor_env='1'),meta[i]));print('SPARSE_HEAVYTRAP',j+1,6,flush=True)
 assert b.sha(parent.read_bytes())==BASESHA and b.sha(basebin.read_bytes())==BASEBIN and b.sha(source.read_bytes())==SHA
 note('sparse_dp_limited_qualification',**artifacts,all15_Open_complete_byteparity=True,six_fixed_heavy_traps_complete_byteparity=True,matched_CPU15=observations,CPU15_geometric_ratio=ratio,CPU15_UNSET_baseline_s=unset['boundary-index']['solver_cpu_total_s'],CPU15_UNSET_candidate_s=unset[K]['solver_cpu_total_s'],CPU15_UNSET_ratio=unset[K]['solver_cpu_total_s']/unset['boundary-index']['solver_cpu_total_s'],heavy_trap_maximum_CPU_s=max(q['solver_cpu_total_s']for q in qs),heavy_trap_maximum_RSS_mib=max(q['solver_peak_rss_mb']for q in qs),all_observed_within_CPU4_5_RSS230=True,full3029_not_run=True,sealed24_untouched=True,Windows_server_unverified=True,no_automatic_promotion=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:note('sparse_dp_gate_stopped',exception=repr(e),traceback=traceback.format_exc()[-2200:],no_automatic_retry=True);raise
