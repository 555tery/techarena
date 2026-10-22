import sys,json,math,re,statistics,collections
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
META={m['id']:m for m in e.inputs('archive')};base=e._evaluations('baseline','archive');cand=e._evaluations('core-guarded-envelope','archive')
assert len(META)==len(base)==len(cand)==2861
public=[i for i,m in META.items()if m.get('public_number')];nonpublic=[i for i in META if i not in public]
opens={k:math.fsum(META[i]['weight']*a[i]['kpi']for i in public)for k,a in [('baseline',base),('combo',cand)]}
def score(a,ids,open_score):
 if len(ids)<4:return None
 values=[a[i]['kpi']for i in ids]
 return open_score+84*statistics.fmean(values)+10*e.expected_best2of4(values)
def describe(ids):
 r=e.paired(cand,base,ids);sb=score(base,ids,opens['baseline']);sc=score(cand,ids,opens['combo'])
 r.update(baseline_mean=statistics.fmean(base[i]['kpi']for i in ids),combo_mean=statistics.fmean(cand[i]['kpi']for i in ids),S_baseline=sb,S_combo=sc,S_delta=None if sb is None else sc-sb)
 return r
# Reproduce the existing ordinary465 provenance audit from frozen manifests only.
freeze={r['id']for r in json.loads((e.R/'prototypes/pipes_current_hybrid_cj_20261020/freeze.json').read_text())['cases']}
osha=set();prefix_origins=set()
for project in ['pipes_online_core_20261020','pipes_closed_ready_20261020']:
 for split in ['calibration','final','stress']:
  path=e.R/f'prototypes/{project}/evaluation/{split}/manifest.json'
  original=json.loads(path.read_text())['cases']
  osha.update(r['sha256']for r in original if r.get('stratum')=='ordinary')
  prefix_origins.update(str(path.parent.relative_to(e.R)/r['file'])for r in original if r.get('stratum')in ['prefix','public_prefix'] or r.get('public_prefix'))
for version in ['search-v2','search-v3','search-v3-1']:
 path=e.R/f'shinka-pipes/{version}/task/data/search/manifest.json'
 osha.update(r['sha256']for r in json.loads(path.read_text())['cases'])
ordinary465=[i for i in nonpublic if i in freeze and META[i]['test_sha256']in osha];assert len(ordinary465)==465
prior42=[i for i in nonpublic if META[i].get('stratum')in ['ordinary','series','motif']];assert len(prior42)==42
ordinary=set(ordinary465+prior42)
# This is an explicit provenance-name proxy, not a scan/assertion of input tokens.
def prefix_named(m):
 name=m.get('origin','')+' '+m.get('family','')
 return m.get('stratum')=='public_prefix' or m.get('origin')in prefix_origins or bool(re.search(r'open\d+|prefix|presync',name,re.I))
prefix=[i for i in nonpublic if i not in ordinary and prefix_named(META[i])]
other=[i for i in nonpublic if i not in ordinary and i not in prefix]
strata={'all_nonpublic2846':nonpublic,'legacy_ordinary465':ordinary465,'prior_ordinary_series_motif42':prior42,
        'ordinary_known507':sorted(ordinary),'public_prefix_named_provenance':prefix,'other_unclassified':other}
strata.update({'provenance:'+p:[i for i in nonpublic if META[i].get('provenance')==p]for p in {m['provenance']for m in META.values()}})
families=collections.defaultdict(list)
for i in nonpublic:families[META[i].get('family','unknown')].append(i)
losses=[]
for d,i in sorted((cand[i]['kpi']-base[i]['kpi'],i)for i in cand if cand[i]['kpi']<base[i]['kpi']-1e-12):
 m=META[i];losses.append(dict(id=i,family=m.get('family'),provenance=m['provenance'],origin=m.get('origin'),operation_count=m['operation_count'],
       delta=d,baseline_kpi=base[i]['kpi'],combo_kpi=cand[i]['kpi'],
       known_attainable_at_least_baseline=base[i]['kpi'],attainability_evidence='existing complete checked baseline response, not volume upper bound'))
assert len(losses)==14
r=e.record(dict(type='combo_archive_family_score_diagnosis',classification_version=2,formula='S=Open+84*mean(pool)+10*E[sum best2of4 without replacement]',
  score_scope='diagnostic fixed formula; not a new promotion gate or parameter tuning',opens=opens,
  ordinary_definition='same prior audited legacy465 plus42 explicit ordinary/series/motif metadata cases',
  prefix_definition='original project manifest declares prefix/public_prefix, explicit public_prefix metadata, or origin/family name contains openN/prefix/presync; latter is a provenance proxy; no input scan',
  small_pool_score=None,small_pool_reason='undefined without-replacement sample4 when n<4',
  strata={g:describe(ids)for g,ids in strata.items()if ids},families={f:describe(ids)for f,ids in families.items()},
  loss_family_counts=dict(collections.Counter(m['family']for m in losses)),losses14=losses,
  all_archive_attainability_claim=False))
print('STRATA',json.dumps(r['strata'],ensure_ascii=False),flush=True)
print('LOSS_FAMILIES',json.dumps(r['loss_family_counts']),flush=True)
for f in r['loss_family_counts']:print('LOSS_FAMILY_SCORE',f,json.dumps(r['families'][f]),flush=True)
print('ALL14LOSSES',json.dumps(losses,ensure_ascii=False),flush=True)
