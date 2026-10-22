"""Thin isolated adapter to round2 complete-response checker. Serial, no auto-promotion."""
import sys,importlib.util,json,collections,statistics,math,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
P=Path('/Users/555tery/techarena/prototypes/pipes_round2_20261022')
_spec=importlib.util.spec_from_file_location('_pipes_round3_base','/tmp/pipes_round2_eval_20261022.py')
b=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=b;_spec.loader.exec_module(b)
b.E=b.R/'prototypes/pipes_round3_20261022';b.REC=b.E/'records.jsonl';b.MANIFEST=b.E/'input_manifest.jsonl'
b.BASE_CPP=P/'recycled_deleted_band/solution.cpp';b.BASE_CPP_BIN=P/'bin/recycled_deleted_band-cpp'
b.BASE_CJ=P/'core-ring/release/solution.cj';b.BASE_CJ_BIN=P/'bin/core-ring-cj'
b.BASE_UNCACHED_CJ=P/'core-ring/uncached/solution.cj';b.BASE_UNCACHED_CJ_SHA=b.sha(b.BASE_UNCACHED_CJ.read_bytes())
b._ROWS_CACHE=None;b._ROWS_STAMP=None
CPP_SHA='1cb3af5bba22e7176d7533d2c20ff6dab5b96bc0cdf1c1ac3046b537ccdcd1b0'
CPP_BIN_SHA='f39c5b0b15b6bda0cf67da8ec63953040b503cfaf87b78496a9b68ee5998765c'
CJ_SHA='511b92f2e24a62b2eabf6593bd8129a136fdbf5437ebf161bcc7334fa2fd63bf'
CJ_BIN_SHA='26ff9e92cd49bcc5641c24b18d24f30208dd4086542c525a7c28c43fd49e8216'
GEN=Path('/tmp/pipes_async_microtransactions_next_20261022.py')
GEN_SHA='86c3724450bba7dc483196df5504f0df421eda30cab79990f9bdee2bd938a90c'
VARIANTS={
 'ordinary-bf-all':('/tmp/pipes_ordinary_bestfit_round3_20261022.py','da8ce0de942ea62e1dcc0ece8219f7585cdbfb6168d0bc2213234c0a4ba30d0a'),
 'ordinary-bf-large':('/tmp/pipes_ordinary_bestfit_large_round3_20261022.py','c36edc5345102290810ddf2f1bd6d6363d1e37bd47e09e456a8d28ed86e9cf75'),
 'coalescence-side':('/tmp/pipes_coalescence_side_round3_20261022.py','f6713e807f0a477ed93bf5f1d1eec32ac7a643318c4f98013c2239f5d0a3528b')}

def pins():
 for path,expected in [(b.BASE_CPP,CPP_SHA),(b.BASE_CPP_BIN,CPP_BIN_SHA),(b.BASE_CJ,CJ_SHA),(b.BASE_CJ_BIN,CJ_BIN_SHA),(GEN,GEN_SHA)]+[(Path(p),s)for p,s in VARIANTS.values()]:assert b.sha(path.read_bytes())==expected,str(path)

def freeze_archive():
 pins()
 if b.MANIFEST.exists():
  ms=b.inputs('archive');assert len(ms)==3029;return ms
 old=b.read_jsonl(P/'input_manifest.jsonl');assert len(old)==3029
 oldids={m['id']for m in old};refs={}
 for q in b.read_jsonl(P/'records.jsonl'):
  if(q.get('type')=='evaluation'and q.get('language')=='cpp'and q.get('source_sha256')==CPP_SHA and q.get('binary_sha256')==CPP_BIN_SHA and q.get('status')=='ok'and q.get('id')in oldids):refs[q['id']]=q
 assert set(refs)=={m['id']for m in old},(len(refs),len(old))
 ms=[]
 for original in old:
  m=dict(original);r=refs[m['id']];assert r['test_sha256']==m['test_sha256']
  m.update(split='archive',round2_split=original['split'],baseline_response_sha256=r['response_sha256'],baseline_kpi=r['kpi'],
   baseline_trench_length_m=r['trench_length_m'],baseline_record_type=r['type'],baseline_record_suite=r['suite'],baseline_record_binary_sha256=CPP_BIN_SHA,
   baseline_record_source_sha256=CPP_SHA,baseline_reference_kind=r['kind'],
   baseline_cpp_cpu_total_s=r.get('solver_cpu_total_s'),baseline_cpp_cpu_user_s=r.get('solver_cpu_user_s'),
   baseline_cpp_cpu_system_s=r.get('solver_cpu_system_s'),baseline_cpp_rss_mib=r.get('solver_peak_rss_mb'))
  ms.append(m)
 b._unique_id(ms);assert len({m['test_sha256']for m in ms})==3029
 b.atomic_manifest(ms)
 b.record(dict(type='archive_freeze',count=3029,baseline_cpp_sha256=CPP_SHA,baseline_cpp_binary_sha256=CPP_BIN_SHA,
  baseline_cj_sha256=CJ_SHA,baseline_cj_binary_sha256=CJ_BIN_SHA,prior_manifest_sha256=b.sha((P/'input_manifest.jsonl').read_bytes()),
  reference='qualified round2 core-ring; actual complete CPP responses with proven Cj parity',old_inputs_read=False,prior_final112_now_archive=True))
 return ms

_original_batch=b.batch
def batch(meta,kind,suite,lang='cpp'):
 if kind=='baseline'and lang=='cpp'and meta['split']=='archive':
  done=b._evaluations(kind,suite,lang).get(meta['id'])
  if done:return done
  return b.record(dict(type='evaluation',suite=suite,kind=kind,language=lang,id=meta['id'],test_sha256=meta['test_sha256'],
   source_sha256=CPP_SHA,binary_sha256=CPP_BIN_SHA,response_sha256=meta['baseline_response_sha256'],kpi=meta['baseline_kpi'],
   trench_length_m=meta['baseline_trench_length_m'],status='ok',validation='reused_actual_complete_current_core_response',
   reference_suite=meta['baseline_record_suite'],reference_kind=meta['baseline_reference_kind'],
   solver_cpu_total_s=meta['baseline_cpp_cpu_total_s'],solver_cpu_user_s=meta['baseline_cpp_cpu_user_s'],solver_cpu_system_s=meta['baseline_cpp_cpu_system_s'],
   solver_peak_rss_mb=meta['baseline_cpp_rss_mib'],envvariant='cjProcessorNum=1',
   timing_scope='historical same-binary CPP batch timing; not a current paired native speed gate'))
 return _original_batch(meta,kind,suite,lang)
b.batch=batch

def pools(archive):
 old2765=[m for m in archive if m['provenance']=='archive2765'];assert len(old2765)==2765
 public=[m['id']for m in archive if m.get('public_number')];assert len(public)==15
 prior=[m['id']for m in old2765[-104:]]
 prev=[m['id']for m in archive if m['provenance']=='previous_certified96'];assert len(prev)==96
 round2=[m['id']for m in archive if m['provenance'].startswith('round2_')];assert len(round2)==168
 screen=public+prior+prev+round2;assert len(screen)==len(set(screen))==383
 cheap=[m['id']for m in archive if m['id']in screen and m.get('stratum')in ['ordinary','series','motif']];assert len(cheap)==42
 group=lambda p:[m['id']for m in archive if m['provenance']==p]
 return dict(screen383=screen,cheap42=cheap,openlike96=group('round2_openlike96'),growing48=group('round2_growing48'),prefix24=group('round2_prefix24'))

def freeze_gates(archive):
 module=b._load_module(GEN);specs=module.specs();new=[ 'round3-'+s.name for s in specs if s.split=='development'];assert len(new)==12
 ps=pools(archive)
 scenarios={
  'both-fresh12':dict(cheap=new,expensive=new),
  'both-old-openlike96':dict(cheap=ps['openlike96'],expensive=ps['openlike96']),
  'both-old-growing48':dict(cheap=ps['growing48'],expensive=ps['growing48']),
  'both-old-prefix24':dict(cheap=ps['prefix24'],expensive=ps['prefix24']),
  'explicit42-cheap-fresh12-expensive':dict(cheap=ps['cheap42'],expensive=new)}
 metadata={m['id']:m for m in archive}
 record=dict(type='development_gate_freeze',before_first_solver_evaluation=True,
  baseline_cpp_sha256=CPP_SHA,baseline_cj_sha256=CJ_SHA,
  variants={k:dict(transformer=p,transformer_sha256=s)for k,(p,s)in VARIANTS.items()},
  generator_sha256=GEN_SHA,screen383_ids=ps['screen383'],new12_ids=new,
  all_valid=True,new12_mean_delta_min=0.,min_delta_on383plus12=-.02,all_five_S_delta_min=0.,scenarios=scenarios,
  formula='Open +44*meanCheap +40*meanExpensive +10*E[sum best2of4 without replacement]',
  ordinarycheap42_membership=[dict(id=i,test_sha256=metadata[i]['test_sha256'],stratum=metadata[i]['stratum'],provenance=metadata[i]['provenance'])for i in ps['cheap42']],
  ordinarycheap_interpretation='explicit ordinary/series/motif42 within screen383; conditional weight4 assignment, not strict507, not empirical hidden distribution or a proved size/weight law; provenance is not ordinaryRequest activation',
  final24_solver_outputs_sealed=True,cj_not_authorized_yet=True,combinations_or_threshold_tuning=False,one_heavy_worker=True,
  resources='CPP batch CPU/RSS descriptive only; Cj/native/final after root review; no platform')
 old=[q for q in b.rows()if q.get('type')=='development_gate_freeze']
 if old:assert len(old)==1 and old[0]==record;return old[0]
 return b.record(record)

def register36(manifest):
 existing=b.inputs('archive');assert len(existing)==3029
 old=[q for q in b.rows()if q.get('type')=='input_freeze']
 if old:assert len(b.inputs('development'))==12 and len(b.inputs('sealed_final',allow_final=True))==24;return
 rawitems=b.read_jsonl(manifest);assert collections.Counter(q['split']for q in rawitems)=={'development':12,'sealed_final':24}
 known={m['test_sha256']for m in existing};commands={m['command_sha256']for m in existing if m.get('command_sha256')}
 h,_=b.harness();module=b._load_module(GEN);fresh=[]
 b.record(dict(type='generator_freeze',generator=str(GEN),generator_sha256=GEN_SHA,manifest_sha256=b.sha(Path(manifest).read_bytes()),count=36,before_solver_evaluation=True))
 for j,raw in enumerate(rawitems):
  path=Path(manifest).parent/raw['input'];m=h.parse_test(path);n=raw['n'];tokens=path.read_bytes().split();ch=b.sha(b'\n'.join(tokens[2:2+n])+b'\n')
  assert m['test_sha256']==raw['sha256']and m['operation_count']==n and m['final_occupied_length_m']==raw['F']
  assert m['minimum_trench_lower_bound_m']==raw['bound']<=raw['T']and raw['attainable_KPI']>=.85 and abs(raw['F']/raw['T']-raw['attainable_KPI'])<1e-12
  assert m['test_sha256']not in known and ch not in commands,('duplicate',raw['name'])
  known.add(m['test_sha256']);commands.add(ch)
  m.update(type='input',id='round3-'+raw['name'],test_file=str(path.resolve()),split=raw['split'],provenance='round3_async36',
   family=raw['family'],stratum=raw['stratum'],weight=1.,command_sha256=ch,witness_sha256=raw['witness_sha256'],
   witness_trench=raw['T'],attainable_kpi=raw['attainable_KPI'],offline_optimum_interval=[raw['bound'],raw['T']],
   exact_offline_optimum=raw['bound']==raw['T'],generator_record=raw)
  with tempfile.TemporaryDirectory(prefix='pipes-round3-witness-')as td:
   d=Path(td);wit=module.replay_witness(raw,d/'witness');assert b.sha(wit.read_bytes())==raw['witness_sha256']
   checked=b._official(m,wit,d);assert checked['trench_length_m']==raw['T']
  b.record(dict(type='attainable_witness_certificate',id=m['id'],test_sha256=m['test_sha256'],witness_sha256=raw['witness_sha256'],
   official_checker='ok',trench=raw['T'],final_occupied=raw['F'],kpi=raw['attainable_KPI'],lower_bound=raw['bound'],exact_offline_optimum=m['exact_offline_optimum'],
   proof='complete feasible official-checked witness; exact OPT only if bound equals witness trench'))
  fresh.append(m);print('WITNESS',j+1,36,m['id'],flush=True)
 b.atomic_manifest(existing+fresh)
 b.record(dict(type='input_freeze',count=36,splits={'development':12,'sealed_final':24},n200000=sum(m['operation_count']==200000 for m in fresh),
  all_official_witnesses_valid=True,minimum_attainable_kpi=min(m['attainable_kpi']for m in fresh),exact_offline_optima=sum(m['exact_offline_optimum']for m in fresh),
  archive_file_hashes_checked=3029,archive_canonical_command_hashes_available=sum(bool(m.get('command_sha256'))for m in existing),
  dedup_scope='all3029 archive file hashes plus all available archive canonical command hashes; all new canonical hashes mutually unique',old_streams_read=False,
  final_solver_outputs_not_opened=True))

def screen():
 gate=next(q for q in b.rows()if q.get('type')=='development_gate_freeze');ms={m['id']:m for m in b.inputs('archive')+b.inputs('development')}
 ids=gate['screen383_ids']+gate['new12_ids'];assert len(ids)==395
 for name,(path,pin)in VARIANTS.items():
  if not any(q.get('type')=='build'and q.get('kind')==name for q in b.rows()):b.compile_variant(name,path)
  # First insertion/deletion protocol sanity, independently checked, outside quality pools.
  folder=b.E/'protocol';folder.mkdir(exist_ok=True);p=folder/'first-commands.in'
  data=b'1\n8\n1\n40\n-1\n2\n-2\n39\n-3\n40\n'
  if not p.exists():p.write_bytes(data)
  else:assert p.read_bytes()==data
  h,_=b.harness();sanity=dict(h.parse_test(p),id='round3-first-commands',split='protocol',test_file=str(p))
  for kind in ['baseline',name]:batch(sanity,kind,'first-source-sanity','cpp')
  started=time.monotonic()
  for j,i in enumerate(ids):
   for kind in (['baseline',name]if j%2==0 else[name,'baseline']):batch(ms[i],kind,'development-screen395','cpp')
   if(j+1)%32==0 or j+1==len(ids):print('SCREEN',name,j+1,len(ids),time.monotonic()-started,flush=True)
  base=b._evaluations('baseline','development-screen395');candidate=b._evaluations(name,'development-screen395')
  comparison=b.paired(candidate,base,ids);new=b.paired(candidate,base,gate['new12_ids'])
  public=[i for i in ids if ms[i].get('public_number')];assert len(public)==15
  scores={}
  for k,values in [('baseline',base),(name,candidate)]:
   opened=math.fsum(ms[i]['weight']*values[i]['kpi']for i in public);scores[k]={}
   for sn,pool in gate['scenarios'].items():
    c=statistics.fmean(values[i]['kpi']for i in pool['cheap']);x=statistics.fmean(values[i]['kpi']for i in pool['expensive']);bonus=b.expected_best2of4([values[i]['kpi']for i in pool['expensive']])
    scores[k][sn]=dict(Open=opened,cheap_mean=c,expensive_mean=x,expected_best2of4_sum=bonus,S=opened+44*c+40*x+10*bonus)
  ds={sn:scores[name][sn]['S']-scores['baseline'][sn]['S']for sn in gate['scenarios']}
  passed=new['mean']>=0 and comparison['minimum']>=-.02 and min(ds.values())>=0
  worst=sorted(ids,key=lambda i:candidate[i]['kpi']-base[i]['kpi'])[:5]
  r=b.record(dict(type='development_screen_result',kind=name,count=395,comparison=comparison,new12=new,
   old383=b.paired(candidate,base,gate['screen383_ids']),
   comparisons_by_provenance={p:b.paired(candidate,base,[i for i in ids if ms[i]['provenance']==p])for p in sorted({ms[i]['provenance']for i in ids})},
   cheap42=b.paired(candidate,base,[x['id']for x in gate['ordinarycheap42_membership']]),
   scenario_scores=scores,scenario_S_delta=ds,passes_fixed_gate=passed,
   worst=[dict(id=i,family=ms[i].get('family'),provenance=ms[i]['provenance'],baseline_kpi=base[i]['kpi'],candidate_kpi=candidate[i]['kpi'],delta=candidate[i]['kpi']-base[i]['kpi'])for i in worst],
   cpu_cpp_batch=dict(candidate_total_s=sum(candidate[i]['solver_cpu_total_s']or 0 for i in ids),candidate_max_s=max(candidate[i]['solver_cpu_total_s']or 0 for i in ids),
    historical_baseline_total_s=sum(base[i]['solver_cpu_total_s']or 0 for i in ids),interpretation='CPP batch descriptive; old baseline CPU reused, not paired native speed evidence or Cj result'),
   wall_s=time.monotonic()-started,all_valid=True,final24_still_sealed=True,promotion=False))
  print('SCREEN_RESULT',json.dumps(r,ensure_ascii=False),flush=True)

if __name__=='__main__':
 pins();archive=freeze_archive();freeze_gates(archive)
 if sys.argv[1]=='prepare':
  folder=Path('/tmp/pipes_async_round3_inputs_20261022')
  if folder.exists():manifest=folder/'manifest.jsonl';assert len(b.read_jsonl(manifest))==36,'partial generator output; review, do not silently regenerate'
  else:manifest=b._load_module(GEN).generate(folder)
  register36(manifest)
 elif sys.argv[1]=='screen':screen()
 else:raise ValueError(sys.argv[1])
