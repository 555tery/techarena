from pathlib import Path
from types import SimpleNamespace
import importlib,json,math,os,statistics,subprocess,sys,tempfile,time
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_virtual_dig_20261022 as v
import pipes_sparse_snapshot_20261022 as patch
e,E=v.e,v.E

def build():
 source=v.PARENT/'release/solution.cj';out=E/'sparse';out.mkdir(exist_ok=True);target=out/'solution.cj'
 code=patch.apply(source.read_text());assert not target.exists();target.write_text(code)
 e.record(dict(type='exact_speed_protocol',source=str(target),source_sha256=e.sha(target.read_bytes()),parent_source=str(source),parent_sha256=e.sha(source.read_bytes()),transformer_sha256=e.sha(Path(patch.__file__).read_bytes()),transformer_source=Path(patch.__file__).read_text(),change='ascending snapshot active support fast paths only if support<=8; unchanged dense path, arithmetic order and policy schedule',quality_gate='bit-for-bit complete responses on2765old+96new; every new input has certified exact offline optimum; no policy tuning',resource_gate='candidate official interactive CPU<5s and RSS<256MiB; paired geometric mean CPU ratio<=0.995,median<=1.02; non-target M1 only',platform_touched=False))
 from pipes_guard_cj_20261022 import compile_cj
 compile_cj(target,E/'bin/sparse-production')

def batch_all():
 for j,m in enumerate(v.META.values()):
  r=e.batch(m,'sparse-production','sparse-old');assert r['response_sha256']==v.BASE[m['id']]['response_sha256'],m['id']
  if(j+1)%128==0 or j+1==len(v.META):print('SPARSE_OLD',j+1,len(v.META),flush=True)
 ms=v.inputs('development')+v.inputs('sealed_final')
 for j,m in enumerate(ms):
  ref=e.batch(m,'current','sparse-fresh-reference');r=e.batch(m,'sparse-production','sparse-fresh');assert r['response_sha256']==ref['response_sha256'],m['id']
  if(j+1)%8==0:print('SPARSE_FRESH',j+1,len(ms),flush=True)

def native(m,kind,suite):
 binary,source=(E/'bin/sparse-production',E/'sparse/solution.cj')if kind=='sparse'else(v.PARENT/'bin/production',v.PARENT/'release/solution.cj')
 known=[r for r in e.rows()if r['type']=='interactive_evaluation'and r['suite']==suite and r['kind']==kind and r['id']==m['id']]
 if known:return known[-1]
 base=SimpleNamespace(**e.ev.h.__dict__);base.parse_test=lambda _:dict(m);os.environ['cjProcessorNum']='1'
 with tempfile.TemporaryDirectory(prefix='pipes-sparse-native-')as td:
  result=e.ev.nh.run_case(base,[str(binary)],e.ev.NATIVE,Path(m['test_file']),Path(td)/'run',5,240);out=Path(result['judge_output_file'])
  r={k:result.get(k)for k in ['status','detail','kpi','trench_length_m','solver_cpu_user_s','solver_cpu_system_s','solver_cpu_total_s','solver_peak_rss_mb','candidate_stderr']}
  r.update(type='interactive_evaluation',suite=suite,kind=kind,id=m['id'],operation_count=m['operation_count'],stratum=m.get('stratum'),family=m.get('family'),test_sha256=m['test_sha256'],source_sha256=e.sha(source.read_bytes()),binary_sha256=e.sha(binary.read_bytes()),response_sha256=e.sha(out.read_bytes())if out.exists()else None,within_limits=not e.ev.nh.failed(result,5,256),scope='whole solver process user+system; one benchmarkworker,cjProcessorNum1; M1/macOS,not targetWindows')
  e.record(r);assert r['status']=='ok',r
  if kind=='sparse':assert r['within_limits'],r
  return r

def resources():
 refs={r['id']:r for r in e.rows()if r['type']=='evaluation'and r['suite']=='sparse-fresh'};ms=v.inputs('development')+v.inputs('sealed_final')
 # Predetermined paired sample balances both families, split and live-scale.
 families={}
 for m in ms:families.setdefault(m['family'],[]).append(m)
 paired_ids=set()
 for pool in families.values():
  ordered=sorted(pool,key=lambda m:m['offline_optimal_trench'])
  paired_ids.update([ordered[0]['id'],ordered[-1]['id']])
 e.record(dict(type='sparse_resource_panel',paired_ids=sorted(paired_ids),selected='smallest and largest live capacity per frozen generator family; all96 candidate native,36 paired, balanced executionorder; plus15public,uniontop5 CPU/RSSold and latestcachemismatch',before_native=True))
 paired_number=0
 for i,m in enumerate(ms):
  kinds=['sparse']
  if m['id']in paired_ids:
   kinds=['sparse','current']if paired_number%2==0 else['current','sparse']
   paired_number+=1
  for kind in kinds:
   r=native(m,kind,'sparse-certified-native');assert r['response_sha256']==refs[m['id']]['response_sha256']
  if(i+1)%4==0:print('SPARSE_NATIVE',i+1,len(ms),flush=True)
 old=[r for r in e.rows()if r['type']=='evaluation'and r['suite']=='sparse-old'];ids=[]
 for field in ['solver_cpu_total_s','solver_peak_rss_mb']:ids.extend(r['id']for r in sorted(old,key=lambda r:r[field],reverse=True)[:5])
 ids.extend(m['id']for m in v.META.values()if m.get('public_number'))
 for i,ident in enumerate(dict.fromkeys(ids)):
  m=v.META[ident]
  for kind in(['sparse','current']if i%2==0 else['current','sparse']):
   r=native(m,kind,'sparse-heavy-native');assert r['response_sha256']==v.BASE[ident]['response_sha256']
  if(i+1)%4==0:print('SPARSE_HEAVY',i+1,len(set(ids)),flush=True)
 pm=next(m for m in v.META.values()if m.get('public_number')==15);t=Path(pm['test_file']).read_bytes().split();cmd=list(map(int,t[2:2+pm['operation_count']]))
 for prefix in[1,2,15,16,17,9999,199999]:
  cc=cmd[:prefix]+[40 if cmd[prefix]!=40 else 39]
  with tempfile.TemporaryDirectory(prefix='sparse-cache-')as td:
   path=Path(td)/'test.in';path.write_text('1\n'+str(len(cc))+'\n'+'\n'.join(map(str,cc))+'\n');m=e.ev.h.parse_test(path);m.update(id=f'sparse-cache-{prefix}',test_file=str(path),stratum='protocol')
   a=native(m,'current','sparse-cache-native');b=native(m,'sparse','sparse-cache-native');assert a['response_sha256']==b['response_sha256']

def summary():
 r=e.rows();a=[x for x in r if x['type']=='evaluation'and x['suite']=='sparse-old'];f=[x for x in r if x['type']=='evaluation'and x['suite']=='sparse-fresh'];assert len(a)==2765 and len(f)==96
 native_rows=[x for x in r if x['type']=='interactive_evaluation'and x['kind']=='sparse']
 controls={(x['suite'],x['id']):x for x in r if x['type']=='interactive_evaluation'and x['kind']=='current'}
 pairs=[(x,controls[x['suite'],x['id']])for x in native_rows if(x['suite'],x['id'])in controls]
 ratios=[x['solver_cpu_total_s']/y['solver_cpu_total_s']for x,y in pairs];geo=math.exp(statistics.fmean(math.log(z)for z in ratios));med=statistics.median(ratios)
 promoted=geo<=.995 and med<=1.02
 data=dict(type='sparse_final_summary',promoted=promoted,source=str(E/'sparse/solution.cj'),source_sha256=e.sha((E/'sparse/solution.cj').read_bytes()),compiler='Cangjie1.0.5 -O0',old_complete_parity=2765,new_complete_parity=96,new_optimum_certificates=96,native_candidate_cases=len(native_rows),paired_cases=len(pairs),paired_cpu_ratio_geomean=geo,paired_cpu_ratio_median=med,paired_new_cpu_median=statistics.median(x['solver_cpu_total_s']for x,y in pairs),paired_old_cpu_median=statistics.median(y['solver_cpu_total_s']for x,y in pairs),max_interactive_cpu=max(x['solver_cpu_total_s']for x in native_rows),max_all_rss_mib=max(x['solver_peak_rss_mb']for x in a+f+native_rows),open15=30.05605802561868,kpi_changed=False,platform_touched=False,target_windows_measured=False,selection_basis='exact unchanged policy plus measured CPU benefit; virtual-eager rejected separately by regression gate; no numerical-policy tuning')
 e.record(data)
 best=data if promoted else dict(source=str(v.PARENT/'release/solution.cj'),source_sha256=e.sha((v.PARENT/'release/solution.cj').read_bytes()),reason='exact speed candidate did not pass predeclared paired-speed gate')
 (E/'best.json').write_text(json.dumps(best,ensure_ascii=False,indent=2)+'\n');print('SPARSE_SUMMARY',json.dumps(data,ensure_ascii=False),flush=True)

if __name__=='__main__':
 if sys.argv[1]=='wait-run':
  start=time.monotonic()
  while not any(r['type']=='selection_freeze'for r in e.rows()):
   assert time.monotonic()-start<3600,'preceding pipeline did not complete selection'
   time.sleep(5)
  chosen=next(r for r in e.rows()[::-1]if r['type']=='selection_freeze')['selected'];assert chosen=='current',chosen
  build();batch_all();resources();summary()
 elif sys.argv[1]=='build':build()
 elif sys.argv[1]=='batch':batch_all()
 elif sys.argv[1]=='resources':resources()
 elif sys.argv[1]=='summary':summary()
