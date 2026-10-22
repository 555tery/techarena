from pathlib import Path
from types import SimpleNamespace
import collections,hashlib,importlib,json,math,os,statistics,subprocess,sys,tempfile
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_virtual_dig_20261022 as v
e,E=v.e,v.E

def fresh():
 assert not any(r['type']=='evaluation'and r['suite']=='development'for r in e.rows())
 manifest=E/'input_manifest.jsonl'
 assert not manifest.exists()
 modules=[('exchange','pipes_certified_streams_20261022'),('cohort','pipes_certified_cohorts_20261022')]
 e.record(dict(type='generator_freeze',sources={name:Path('/tmp',name+'.py').read_text()for _,name in modules},inputs_before_solver_evaluation=True,constructive_bound='witness attains peak-live lower bound; exact offline optimum, not only a volume upper bound',counts={'development':36,'sealed_final':60}))
 new=[];hashes=set()
 for group,name in modules:
  module=importlib.import_module(name);folder=E/group;rawmanifest=module.generate(folder)
  for raw in map(json.loads,rawmanifest.open()):
   path=folder/raw['input'];m=e.ev.h.parse_test(path)
   assert m['operation_count']==raw['n']and m['final_occupied_length_m']==raw['F']and m['minimum_trench_lower_bound_m']==raw['T']
   assert m['test_sha256']==raw['sha256'];assert raw['attainable_KPI']>=.85
   tok=path.read_bytes().split();h=e.sha(b'\n'.join(tok[2:2+raw['n']])+b'\n');assert h not in hashes;hashes.add(h)
   m.update(type='input',id='certified-'+raw['name'],test_file=str(path),command_sha256=h,split=raw['split'],stratum=group,family=raw['family'],weight=1.,witness_sha256=raw['witness_sha256'],offline_optimal_trench=raw['T'],optimal_kpi=raw['attainable_KPI'],generator_record=raw)
   with tempfile.TemporaryDirectory(prefix='pipes-certified-')as td:
    d=Path(td);w=module.replay_witness(raw,d/'witness');(d/'empty').write_text('')
    with w.open('rb')as fi:q=subprocess.run([str(e.ev.EXP/'bin/official-offline'),str(path),str(d/'checked'),str(d/'empty'),str(d/'report')],stdin=fi,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=d)
    match=e.ev.h.SCORE_RE.search(q.stderr.decode());assert q.returncode==0 and match,(m['id'],q.stderr[-1200:])
    assert int(match[1])==raw['F']and int(match[2])==raw['T']
   e.record(dict(type='offline_optimum_certificate',id=m['id'],test_sha256=m['test_sha256'],witness_sha256=m['witness_sha256'],official_checker='ok',trench=raw['T'],final_occupied=raw['F'],kpi=raw['attainable_KPI'],proof='peak live lower bound equals feasible witness trench; no relocation; witness not supplied to solver'))
   new.append(m)
   if len(new)%8==0:print('CERTIFIED',len(new),96,flush=True)
 with manifest.open('x')as f:
  for m in new:f.write(json.dumps(m,ensure_ascii=False)+'\n')
 old=set()
 for m in v.META.values():
  t=Path(m['test_file']).read_bytes().split();old.add(e.sha(b'\n'.join(t[2:2+m['operation_count']])+b'\n'))
 assert not old&hashes
 e.record(dict(type='input_freeze',count=len(new),splits=dict(collections.Counter(m['split']for m in new)),command_hashes=len(hashes),canonical_prior_streams=len(old),overlap=0,all_offline_optima_certified=True,minimum_optimal_kpi=min(m['optimal_kpi']for m in new),final_test_hashes=[m['test_sha256']for m in new if m['split']=='sealed_final']))

def panel(split):
 for j,m in enumerate(v.inputs(split)):
  kinds=['current','eager','virtual-eager','virtual-lazy']
  for k in(kinds if j%2==0 else kinds[::-1]):e.batch(m,k,split)
  if(j+1)%4==0:print('CPP',split,j+1,len(v.inputs(split)),flush=True)

def paired(a,b,ids):
 d=[a[i]['kpi']-b[i]['kpi']for i in ids]
 return dict(n=len(d),wins=sum(x>1e-12 for x in d),ties=sum(abs(x)<=1e-12 for x in d),losses=sum(x< -1e-12 for x in d),mean=statistics.fmean(d),minimum=min(d),maximum=max(d))

def select():
 rows=e.rows();assert not any(r['type']=='evaluation'and r['suite']=='sealed_final'for r in rows)
 old={k:{r['id']:r for r in rows if r['type']=='evaluation'and r['suite']=='old'and r['kind']==k}for k in ['virtual-eager','virtual-lazy']}
 assert all(len(a)==2765 for a in old.values())
 old['current']=v.BASE
 dev={k:{r['id']:r for r in rows if r['type']=='evaluation'and r['suite']=='development'and r['kind']==k}for k in ['current','eager','virtual-eager','virtual-lazy']}
 dm={m['id']:m for m in v.inputs('development')};assert all(len(a)==36 for a in dev.values())
 groups={}
 for i,m in v.META.items():groups.setdefault(m.get('family')or'unknown',[]).append(i)
 scenarios={'all_nonpublic':[i for i,m in v.META.items()if not m.get('public_number')],'long':[i for i,m in v.META.items()if m['operation_count']>=100000],'short':[i for i,m in v.META.items()if m['operation_count']<=200],'previous_new104':list(v.META)[-104:],'previous_ordinary42':[i for i,m in list(v.META.items())[-104:]if m.get('stratum')in['ordinary','series','motif']]}
 scenarios.update({'source_'+g:ids for g,ids in groups.items()if len(ids)>=4})
 scenarios.update({'dev_'+g:[i for i,m in dm.items()if m['stratum']==g]for g in ['exchange','cohort']})
 pub=[i for i,m in v.META.items()if m.get('public_number')]
 opens={k:math.fsum(v.META[i]['weight']*old[k][i]['kpi']for i in pub)for k in old}
 scores={}
 for k in old:
  vals={**old[k],**dev[k]};scores[k]={s:opens[k]+84*statistics.fmean(vals[i]['kpi']for i in ids)+10*e.expected_top2([vals[i]['kpi']for i in ids])for s,ids in scenarios.items()}
 diagnostics={};eligible=[]
 for k in ['virtual-eager','virtual-lazy']:
  pa=paired(old[k],v.BASE,v.META);pd=paired(dev[k],dev['current'],dm)
  groupmeans={g:paired(old[k],v.BASE,ids)['mean']for g,ids in groups.items()}
  changes={s:scores[k][s]-scores['current'][s]for s in scenarios}
  passes=pa['minimum']>=-.01 and min(groupmeans.values())>=-1e-12 and pd['mean']>=-1e-12 and min(changes.values())>=-.05 and opens[k]>=opens['current']-1e-12
  diagnostics[k]=dict(old=pa,development=pd,source_macro_means=groupmeans,scenario_changes=changes,passes=passes)
  if passes and(pa['mean']>1e-12 or pd['mean']>1e-12):eligible.append(k)
 if eligible:
  selected=max(eligible,key=lambda k:(round(min(diagnostics[k]['scenario_changes'].values()),10),k=='virtual-eager'))
 else:selected='current'
 record=dict(type='selection_freeze',selected=selected,diagnostics=diagnostics,opens=opens,scores=scores,scenarios=scenarios,final_input_hashes=[m['test_sha256']for m in v.inputs('sealed_final')],before_final=True,final_gate='no post-final tuning; final mean selected-current>=0, min>=-0.01, complete output parity CPP/Cj, all valid and local resources CPU<5/RSS<256; same-parent address equality and domination separately',policy='unchanged causal guard5 certified equal to cautious on public trie; only emitted dig scheduling changed')
 e.record(record);print('SELECT',json.dumps(dict(selected=selected,diagnostics={k:dict(old=a['old'],development=a['development'],passes=a['passes'],min_scenario=min(a['scenario_changes'].values()))for k,a in diagnostics.items()})),flush=True)
 return selected

def build_cj(selected):
 source=v.PARENT/'uncached/solution.cj';code=source.read_text();patches=[]
 def patch(a,b):
  nonlocal code
  assert code.count(a)==1,(a[:70],code.count(a));code=code.replace(a,b);patches.append([a,b])
 if selected=='virtual-eager':
  patch('''            if (tailPlacement) {
                let missing = start + length - trenchLength''','''            if (tailPlacement && !cohortSlabExpanded) {
                let missing = cohortSlabEnd - trenchLength''')
  patch('''                if (digs > 0 && occupiedEnd < trenchLength) { addFreeGap(occupiedEnd, trenchLength, -1) }''','''                if (occupiedEnd < trenchLength) { addFreeGap(occupiedEnd, trenchLength, -1) }''')
  patch('''        let deletedEnd = iMin(trenchLength, cohortSlabBase + cohortSlabDeleteCount * length)''','''        let deletedEnd = cohortSlabBase + cohortSlabDeleteCount * length''')
  patch('''        let survivorEnd = iMin(trenchLength, cohortSlabBase + cohortSlabTailPipeCount * length)''','''        let survivorEnd = cohortSlabBase + cohortSlabTailPipeCount * length''')
 patch('''    public var pipes = ArrayList<Pipe>()
    public var trenchLength: Int64 = 0''','''    public var pipes = ArrayList<Pipe>()
    public var trenchLength: Int64 = 0
    // Output state only; all placement decisions retain the virtual plan.
    public var emittedTrenchLength: Int64 = 0''')
 assert code.count('printPlacement(digs, start)')==2;code=code.replace('printPlacement(digs, start)','printPlacement(digs, start, length)')
 patch('''    public func printPlacement(digs: Int64, start: Int64): Unit { if (emit) { answer(digs, start) } }''','''    public func printPlacement(digs: Int64, start: Int64, length: Int64): Unit {
        if (!emit) { return }
        let missing = start + length - emittedTrenchLength
        let actualDigs: Int64 = if (missing > 0) { (missing + kDigLength - 1) / kDigLength } else { 0 }
        emittedTrenchLength += actualDigs * kDigLength
        answer(actualDigs, start)
    }''')
 patch('''    out.trenchLength = actual.trench''','''    out.trenchLength = actual.trench
    out.emittedTrenchLength = actual.trench''')
 patch('''if (let Some(core) <- online) { trench = core.trenchLength }''','''if (let Some(core) <- online) { trench = core.emittedTrenchLength }''')
 out=E/'uncached';out.mkdir(exist_ok=True);p=out/'solution.cj';assert not p.exists();p.write_text(code)
 e.record(dict(type='cj_translation',selected=selected,parent_sha256=e.sha(source.read_bytes()),source_sha256=e.sha(p.read_bytes()),patches=patches,virtual_decision_state_unchanged=True))
 import pipes_guard_cj_20261022 as factory
 factory.compile_cj(p,E/'bin/uncached')
 refs={r['id']:r for r in e.rows()if r['type']=='evaluation'and r['suite']=='old'and r['kind']==selected}
 for m in e.ev.rows:
  if m.get('public_number'):
   r=e.batch(m,'uncached','public-uncached');assert r['response_sha256']==refs[m['id']]['response_sha256']
 factory.cached()
 for m in e.ev.rows:
  if m.get('public_number'):
   r=e.batch(m,'production','public-production');assert r['response_sha256']==refs[m['id']]['response_sha256']
 e.record(dict(type='production_freeze',selected=selected,source_sha256=e.sha((E/'release/solution.cj').read_bytes()),binary_sha256=e.sha((E/'bin/production').read_bytes()),compiler='Cangjie1.0.5 -O0',before_final=True))

def archive_cj(selected):
 refs={r['id']:r for r in e.rows()if r['type']=='evaluation'and r['suite']=='old'and r['kind']==selected}
 for j,m in enumerate(v.META.values()):
  r=e.batch(m,'production','archive-cj');assert r['response_sha256']==refs[m['id']]['response_sha256'],m['id']
  if(j+1)%128==0 or j+1==len(v.META):print('CJ_OLD',j+1,len(v.META),flush=True)
 for j,m in enumerate(v.inputs('development')):
  r=e.batch(m,'production','development-cj');ref=next(x for x in e.rows()if x['type']=='evaluation'and x['suite']=='development'and x['kind']==selected and x['id']==m['id']);assert r['response_sha256']==ref['response_sha256'],m['id']
  if(j+1)%8==0:print('CJ_DEV',j+1,36,flush=True)

def native(m,kind,suite):
 source,binary=(E/'release/solution.cj',E/'bin/production')if kind=='production'else(v.PARENT/'release/solution.cj',v.PARENT/'bin/production')
 done=[r for r in e.rows()if r['type']=='interactive_evaluation'and r['suite']==suite and r['kind']==kind and r['id']==m['id']]
 if done:return done[-1]
 base=SimpleNamespace(**e.ev.h.__dict__);base.parse_test=lambda _:dict(m);os.environ['cjProcessorNum']='1'
 with tempfile.TemporaryDirectory(prefix='pipes-virtual-native-')as td:
  r=e.ev.nh.run_case(base,[str(binary)],e.ev.NATIVE,Path(m['test_file']),Path(td)/'run',5,240);out=Path(r['judge_output_file'])
  x={k:r.get(k)for k in ['status','detail','kpi','trench_length_m','solver_cpu_total_s','solver_peak_rss_mb','candidate_stderr']};x.update(type='interactive_evaluation',suite=suite,kind=kind,id=m['id'],stratum=m.get('stratum'),family=m.get('family'),test_sha256=m['test_sha256'],source_sha256=e.sha(source.read_bytes()),binary_sha256=e.sha(binary.read_bytes()),response_sha256=e.sha(out.read_bytes())if out.exists()else None,within_limits=not e.ev.nh.failed(r,5,256),resource_scope='whole process user+system; one worker,cjProcessorNum1; M1/macOS not targetWindows/G5420');e.record(x);assert x['within_limits'],x
  return x

def final_and_resources(selected):
 panel('sealed_final')
 refs={(r['id'],r['kind']):r for r in e.rows()if r['type']=='evaluation'and r['suite']=='sealed_final'}
 for j,m in enumerate(v.inputs('sealed_final')):
  for k in(['production','current']if j%2==0 else['current','production']):
   x=native(m,k,'sealed-final-cj');ref=refs[m['id'],selected if k=='production'else'current'];assert x['response_sha256']==ref['response_sha256'],(m['id'],k)
  if(j+1)%4==0:print('FINAL_NATIVE',j+1,60,flush=True)
 # Previously observed heavy cases and every public path; selected by resources.
 old=[r for r in e.rows()if r['type']=='evaluation'and r['suite']=='archive-cj'];ids=[]
 for key in ['solver_cpu_total_s','solver_peak_rss_mb']:
  ids.extend(r['id']for r in sorted(old,key=lambda r:r[key],reverse=True)[:5])
 ids.extend(m['id']for m in v.META.values()if m.get('public_number'))
 for j,i in enumerate(dict.fromkeys(ids)):
  native(v.META[i],'production','resource-check')
  if(j+1)%4==0:print('RESOURCES',j+1,len(set(ids)),flush=True)
 # Cached-state import at the latest possible mismatch.
 pm=next(m for m in v.META.values()if m.get('public_number')==15);tok=Path(pm['test_file']).read_bytes().split();cmd=list(map(int,tok[2:2+pm['operation_count']]))
 for p in[1,2,15,16,17,9999,199999]:
  cc=cmd[:p]+[40 if cmd[p]!=40 else 39]
  with tempfile.TemporaryDirectory(prefix='pipes-vcache-')as td:
   path=Path(td)/'in';path.write_text('1\n'+str(len(cc))+'\n'+'\n'.join(map(str,cc))+'\n');m=e.ev.h.parse_test(path);m.update(id=f'cache-mismatch-{p}',test_file=str(path),stratum='protocol')
   a=e.batch(m,'uncached','cache-check');b=e.batch(m,'production','cache-check');assert a['response_sha256']==b['response_sha256'];n=native(m,'production','cache-check');assert n['response_sha256']==a['response_sha256']

def summary(selected):
 r=e.rows();ms=v.inputs('sealed_final');ids=[m['id']for m in ms]
 final={k:{x['id']:x for x in r if x['type']=='evaluation'and x['suite']=='sealed_final'and x['kind']==k}for k in ['current','eager',selected]}
 f=paired(final[selected],final['current'],ids);assert f['mean']>=-1e-12 and f['minimum']>=-.01
 assert all(final[selected][i]['kpi']>=final['eager'][i]['kpi']-1e-12 for i in ids)
 old={x['id']:x for x in r if x['type']=='evaluation'and x['suite']=='old'and x['kind']==selected};d=paired(old,v.BASE,v.META)
 resources=[x for x in r if x['type']in['interactive_evaluation','evaluation']and x.get('kind')=='production'and x.get('solver_cpu_total_s')is not None]
 assert all(x.get('within_limits',True)for x in resources)
 pub=[i for i,m in v.META.items()if m.get('public_number')];opens=math.fsum(v.META[i]['weight']*old[i]['kpi']for i in pub)
 result=dict(type='final_summary',promoted=True,selected=selected,source=str(E/'release/solution.cj'),source_sha256=e.sha((E/'release/solution.cj').read_bytes()),old_count=2765,fresh_certified=96,sealed_final=60,old_vs_current=d,final_vs_current=f,final_vs_eager=paired(final[selected],final['eager'],ids),open15=opens,cj_cpp_complete_parity=2861,all_new_offline_optima_certified=True,maximum_cpu_s=max(x['solver_cpu_total_s']for x in resources),maximum_rss_mib=max(x['solver_peak_rss_mb']for x in resources),native_checks=sum(x['type']=='interactive_evaluation'for x in resources),target_measured=False,platform_touched=False,theorem='same addresses/removals as eager, minimum necessary actual digs; physical T<=eager virtual T at every step; empirically checked relative to current lazy, not a universal dominance theorem against current lazy')
 e.record(result);(E/'best.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('FINAL_SUMMARY',json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='fresh':fresh()
 elif mode=='dev':panel('development')
 elif mode=='select':select()
 elif mode=='continue':
  selected=next(r for r in e.rows()[::-1]if r['type']=='selection_freeze')['selected'];assert selected!='current'
  build_cj(selected);archive_cj(selected);final_and_resources(selected);summary(selected)
