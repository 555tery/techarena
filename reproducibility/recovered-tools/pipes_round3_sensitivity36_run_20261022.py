import sys,json,time,statistics,math,collections,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;SUITE='sensitivity36-CEF';GEN=Path('/tmp/pipes_selection_sensitivity36_20261022.py');GPIN='ada54170d6a25fc79052d529cef64446c1ab7d175252aa287b7fddeb53dc8e66'
PINS={
 'C':('recycled_deleted_band',a.CPP_SHA,a.CPP_BIN_SHA,5),
 'E':('core-guarded-envelope','a54d443ae8fd052bd23ece9610533ca868af541e116686bece8ba5a11e7f5a76','15e936bc142bc9875aba605e9e92561a9ca3843eb116f82db458a4e0d35d3265',5),
 'F':('core-full-comparative',a.CPP_SHA,'08bb7d5d6a06692b91bb49f69c4f278b0406bc3b4726d362f54d8e2ff7fd3338',0)}
def describe(values,ref,ids):
 q=b.paired(values,ref,ids);q.update(candidate_mean=statistics.fmean(values[i]['kpi']for i in ids),baseline_mean=statistics.fmean(ref[i]['kpi']for i in ids),candidate_minimum=min(values[i]['kpi']for i in ids),candidate_maximum=max(values[i]['kpi']for i in ids));return q

def run():
 assert b.sha(GEN.read_bytes())==GPIN
 assert not any(q.get('type')=='sensitivity36_CEF_result'for q in b.rows()),'one fixed run already finished'
 ms=[m for m in b.read_jsonl(b.MANIFEST)if m['split']=='sensitivity_development'];assert len(ms)==36
 assert collections.Counter(m['origin']for m in ms)=={'Open12':12,'Open14':12,'independent':12}
 old=b.read_jsonl(a.P/'records.jsonl');artifacts={};opens={};public_refs={}
 public=[m for m in b.inputs('archive')if m.get('public_number')];assert len(public)==15
 for label,(kind,ss,bs,guard)in PINS.items():
  build=next(q for q in old if q.get('type')=='build'and q.get('kind')==kind and q.get('language')=='cpp'and q.get('source_sha256')==ss and q.get('binary_sha256')==bs)
  assert build['status']==0 and all(x in build['command']for x in['-DRESERVATION_POLICY=1','-DLAZY_SLAB=1',f'-DREPLAY_GUARD={guard}'])
  s,bi=Path(build['source']),Path(build['binary']);assert b.sha(s.read_bytes())==ss and b.sha(bi.read_bytes())==bs
  alias='sensitivity-'+label.lower()
  if not any(q.get('type')=='build'and q.get('kind')==alias for q in b.rows()):b.record(dict(build,kind=alias,command=None,alias_only=True,reference_build_kind=kind,reference_command=build['command'],reference_records=str(a.P/'records.jsonl'),scope='exact existing source/binary; no rebuild'))
  refs={}
  for q in old:
   if q.get('type')=='evaluation'and q.get('language')=='cpp'and q.get('source_sha256')==ss and q.get('binary_sha256')==bs and q.get('status')=='ok':refs[q['id']]=q
  for m in public:assert m['id']in refs and refs[m['id']]['test_sha256']==m['test_sha256']
  opens[label]=math.fsum(m['weight']*refs[m['id']]['kpi']for m in public)
  public_refs[label]=[dict(id=m['id'],test_sha256=m['test_sha256'],response_sha256=refs[m['id']]['response_sha256'],kpi=refs[m['id']]['kpi'],weight=m['weight'],suite=refs[m['id']]['suite'])for m in public]
  artifacts[label]=dict(kind=alias,source=str(s),source_sha256=ss,binary=str(bi),binary_sha256=bs,flags=build['command'][1:6])
 ids=[m['id']for m in ms];byorigin={o:[m['id']for m in ms if m['origin']==o]for o in['Open12','Open14','independent']};prefix=byorigin['Open12']+byorigin['Open14'];ind=byorigin['independent']
 scenarios={f'both-pure-{o}':dict(cheap=byorigin[o],expensive=byorigin[o])for o in byorigin}
 scenarios.update({'cheap-prefix24-exp-independent12':dict(cheap=prefix,expensive=ind),'both-all36':dict(cheap=ids,expensive=ids)})
 plan=dict(type='sensitivity36_CEF_freeze',before_first_solver_evaluation=True,artifacts=artifacts,generator_sha256=GPIN,raw_manifest_sha256=b.sha(Path('/tmp/pipes_selection_sensitivity36_inputs_20261022/manifest.jsonl').read_bytes()),membership=[dict(id=m['id'],test_sha256=m['test_sha256'],command_sha256=m['command_sha256'],origin=m['origin'],family=m['family'])for m in ms],required_all36_valid_each_policy=True,formula='actualOpen+44*meanCheap+40*meanExpensive+10*E[sum best2of4 without replacement]',scenarios=scenarios,actual_Open15=opens,actual_Open15_pinned_references=public_refs,compiler='existing clang++ -O2 binaries only',no_new_builds=True,no_G2_or_width16_or_beam=True,all36_development_sensitivity_not_independent_holdout=True,no_hidden_probability_claim=True,automatic_promotion=False,selection_by_root_in_context_of_known_archive=True,final24_still_sealed=True)
 freezes=[q for q in b.rows()if q.get('type')=='sensitivity36_CEF_freeze']
 if freezes:assert len(freezes)==1 and freezes[0]==plan
 else:b.record(plan)
 t=time.monotonic();values={label:{}for label in PINS}
 for j,m in enumerate(ms):
  order=list(PINS);order=order[j%3:]+order[:j%3]
  for label in order:
   q=b.batch(m,artifacts[label]['kind'],SUITE,'cpp');assert q['status']=='ok'and q['source_sha256']==artifacts[label]['source_sha256']and q['binary_sha256']==artifacts[label]['binary_sha256'];values[label][m['id']]=q
  if(j+1)%3==0:print('SENSITIVITY_CEF',j+1,len(ms),'elapsed',round(time.monotonic()-t,2),flush=True)
 scores={}
 for label,v in values.items():
  scores[label]={}
  for name,pool in scenarios.items():
   cheap=statistics.fmean(v[i]['kpi']for i in pool['cheap']);exp=statistics.fmean(v[i]['kpi']for i in pool['expensive']);bonus=b.expected_best2of4([v[i]['kpi']for i in pool['expensive']]);scores[label][name]=dict(actualOpen=opens[label],meanCheap=cheap,meanExpensive=exp,expected_best2of4_sum=bonus,S=opens[label]+44*cheap+40*exp+10*bonus)
 comparison_pairs=[('E','C'),('F','C'),('F','E')];groups={'all36':ids,**{'origin:'+o:x for o,x in byorigin.items()}}
 for m in ms:groups.setdefault('cell:'+m['origin']+':'+m['family'],[]).append(m['id'])
 assert sum(k.startswith('cell:')for k in groups)==12
 comparisons={f'{x}-vs-{y}':{name:describe(values[x],values[y],is_)for name,is_ in groups.items()}for x,y in comparison_pairs}
 matches=collections.defaultdict(list)
 for m in ms:
  if m['generator_record'].get('match_group'):matches[m['generator_record']['match_group']].append(m)
 pairs=[]
 for group,members in sorted(matches.items()):
  assert len(members)==2 and len({m['generator_record']['matched_signs_positive_lengths_sha256']for m in members})==1
  neutral=next(m for m in members if m['family']=='neutral');permuted=next(m for m in members if m['family']=='lifetime_permutation');ni,pi=neutral['id'],permuted['id']
  pair=dict(match_group=group,neutral_id=ni,lifetime_permutation_id=pi,sign_positive_length_fingerprint=neutral['generator_record']['matched_signs_positive_lengths_sha256'],policies={label:dict(neutral_kpi=v[ni]['kpi'],lifetime_permutation_kpi=v[pi]['kpi'],permutation_minus_neutral=v[pi]['kpi']-v[ni]['kpi'])for label,v in values.items()})
  pair['paired_effect_vs_C']={label:(values[label][pi]['kpi']-values['C'][pi]['kpi'])-(values[label][ni]['kpi']-values['C'][ni]['kpi'])for label in['E','F']};pairs.append(pair)
 ds={f'{x}-vs-{y}':{name:scores[x][name]['S']-scores[y][name]['S']for name in scenarios}for x,y in comparison_pairs}
 r=b.record(dict(type='sensitivity36_CEF_result',count=36,all108_complete_responses_valid=True,artifacts=artifacts,actual_Open15=opens,comparisons=comparisons,scenario_scores=scores,scenario_S_deltas=ds,matched_pairs=pairs,matched_effect_means={label:statistics.fmean(q['paired_effect_vs_C'][label]for q in pairs)for label in['E','F']},validation_counts={label:dict(collections.Counter(q['validation']for q in v.values()))for label,v in values.items()},cpp_cpu_descriptive={label:dict(total_s=sum(q['solver_cpu_total_s']for q in v.values()),max_s=max(q['solver_cpu_total_s']for q in v.values()),max_rss_mib=max(q['solver_peak_rss_mb']for q in v.values()))for label,v in values.items()},wall_s=time.monotonic()-t,no_hidden_probability_claim=True,conditional_scenarios_not_hidden_distribution=True,automatic_promotion=False,final24_still_sealed=True))
 print('SENSITIVITY_CEF_RESULT',json.dumps({k:r[k]for k in['actual_Open15','scenario_S_deltas','cpp_cpu_descriptive','wall_s']}),flush=True)
 print('SENSITIVITY_CEF_WTL',json.dumps({k:v['all36']for k,v in comparisons.items()}),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:b.record(dict(type='sensitivity36_CEF_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2000:],automatic_promotion=False));raise
