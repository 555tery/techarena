import sys,json,tempfile,collections,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True;sys.path.insert(0,'/tmp')
import pipes_round3_eval_20261022 as a
b=a.b;GEN=Path('/tmp/pipes_selection_sensitivity36_20261022.py');PIN='ada54170d6a25fc79052d529cef64446c1ab7d175252aa287b7fddeb53dc8e66';D=Path('/tmp/pipes_selection_sensitivity36_inputs_20261022')
def run():
 assert b.sha(GEN.read_bytes())==PIN
 assert any(q.get('type')=='boundary_full3029_result'and q.get('status')=='ok'for q in b.rows())
 assert not any(q.get('type')=='sensitivity36_input_freeze'for q in b.rows()),'already registered; no automatic repeat'
 existing=b.read_jsonl(b.MANIFEST);assert len(existing)==3065
 raw_index=collections.defaultdict(list);canonical=collections.defaultdict(list)
 for m in existing:
  raw_index[m['test_sha256']].append(m['id'])
  if m.get('command_sha256'):canonical[m['command_sha256']].append(m['id'])
 module=b._load_module(GEN);t=time.monotonic()
 if D.exists():
  manifest=D/'manifest.jsonl';assert len(b.read_jsonl(manifest))==36,'partial generator; stop for review'
 else:manifest=module.generate(D)
 raws=b.read_jsonl(manifest);assert len(raws)==36 and all(r['split']=='development'for r in raws)
 b.record(dict(type='sensitivity36_generator_freeze',generator=str(GEN),generator_sha256=PIN,manifest=str(manifest),manifest_sha256=b.sha(manifest.read_bytes()),count=36,scope='development sensitivity; no solver outputs; retain all fixed cells including archive duplicates',solver_candidates_not_yet_frozen=True,final24_still_sealed=True))
 h,_=b.harness();fresh=[];matches=collections.defaultdict(list)
 for j,r in enumerate(raws):
  path=manifest.parent/r['input'];m=h.parse_test(path);data=path.read_bytes();tok=data.split();n=r['n'];ch=b.sha(b'\n'.join(tok[2:2+n])+b'\n')
  assert m['test_sha256']==r['sha256'] and m['operation_count']==n and m['final_occupied_length_m']==r['F']
  assert m['minimum_trench_lower_bound_m']==r['bound']<=r['T'] and r['attainable_KPI']>=.85 and abs(r['F']/r['T']-r['attainable_KPI'])<1e-12
  same_raw=raw_index.get(r['sha256'],[]);same_canonical=canonical.get(ch,[])
  m.update(type='input',id='sensitivity36-'+r['name'],test_file=str(path.resolve()),split='sensitivity_development',original_split=r['split'],provenance='round3_sensitivity36',origin=r['origin'],family=r['family'],stratum=r['stratum'],weight=1.,command_sha256=ch,witness_sha256=r['witness_sha256'],witness_trench=r['T'],attainable_kpi=r['attainable_KPI'],offline_optimum_interval=[r['bound'],r['T']],exact_offline_optimum=r['bound']==r['T'],generator_record=r,raw_duplicate_of_ids=list(same_raw),canonical_duplicate_of_ids=list(same_canonical),fresh_raw_hash=not same_raw,fresh_available_canonical_hash=not same_canonical,not_fresh_reused=bool(same_raw or same_canonical))
  with tempfile.TemporaryDirectory(prefix='pipes-sensitivity36-witness-')as td:
   d=Path(td);wit=module.replay_witness(r,d/'witness');assert b.sha(wit.read_bytes())==r['witness_sha256'];checked=b._official(m,wit,d);assert checked['trench_length_m']==r['T']
  b.record(dict(type='sensitivity36_witness_certificate',id=m['id'],test_sha256=r['sha256'],command_sha256=ch,witness_sha256=r['witness_sha256'],official_checker='ok',F=r['F'],T=r['T'],lower_bound=r['bound'],attainable_kpi=r['attainable_KPI'],exact_optimum=r['bound']==r['T'],raw_duplicate_of_ids=same_raw,canonical_duplicate_of_ids=same_canonical,not_fresh_reused=m['not_fresh_reused']))
  fresh.append(m)
  if r.get('match_group'):matches[r['match_group']].append(r['matched_signs_positive_lengths_sha256'])
  print('SENSITIVITY_WITNESS',j+1,36,m['id'],'reused',m['not_fresh_reused'],flush=True)
 assert len(matches)==6 and all(len(v)==2 and len(set(v))==1 for v in matches.values())
 b._unique_id(existing+fresh);assert len({m['test_sha256']for m in fresh})==36
 b.atomic_manifest(existing+fresh)
 q=b.record(dict(type='sensitivity36_input_freeze',count=36,input_manifest=str(b.MANIFEST),origin_counts=dict(collections.Counter(m['origin']for m in fresh)),all_official_witnesses_valid=True,minimum_attainable_kpi=min(m['attainable_kpi']for m in fresh),exact_optima=sum(m['exact_offline_optimum']for m in fresh),new_raw_hashes=sum(m['fresh_raw_hash']for m in fresh),new_available_canonical_hashes=sum(m['fresh_available_canonical_hash']for m in fresh),not_fresh_reused_ids=[m['id']for m in fresh if m['not_fresh_reused']],independent_mechanism_cases=12,independent_mechanism_fresh_raw_hashes=sum(m['origin']=='independent'and m['fresh_raw_hash']for m in fresh),known_metadata_rows=len(existing),known_raw_hashes=len(raw_index),known_canonical_hashes_available=len(canonical),dedup_scope='all existing3065 raw metadata hashes and available canonical metadata hashes only; no archive full-input scans; retain all predeclared cells without resampling',all6_matched_neutral_lifetime_pairs_same_sign_positive_length_fingerprint=True,solver_outputs_not_run=True,final24_still_sealed=True,wall_s=time.monotonic()-t,promotion=False))
 print('SENSITIVITY36_PREPARED',json.dumps(q),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as ex:b.record(dict(type='sensitivity36_prepare_stopped',exception=repr(ex),traceback=traceback.format_exc()[-2000:]));raise
