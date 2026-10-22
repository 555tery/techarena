import json,sys
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
GUARD=e.Path('/tmp/pipes_replay_guarded_envelope_round2_20261022.py')
GUARD_SHA='0ec7f2f6694191db3a3ff10d7e553b83500a7e33f5355a869af189f0842736f0'
KIND='guarded-envelope'
SCENARIOS=next(q['scenarios']for q in e.rows()[::-1]if q.get('type')=='scenario_scores'and len(q['scenarios'])==6)

def run_screen(kind):
    e.oldscreen(kind)
    e.batch_pairs(['baseline',kind],'development')
    dev=e.compact_summary([kind],'development')
    score=e.scenario_scores(['baseline',kind],SCENARIOS,['archive','development'],'cpp',{'archive':'oldscreen','development':'development'})
    changes={s:score['scores'][kind][s]['S']-score['scores']['baseline'][s]['S']for s in SCENARIOS}
    p=dev['comparisons'][kind]['all']
    print('STAGE_RESULT',json.dumps(dict(kind=kind,development=p,S_changes=changes),ensure_ascii=False),flush=True)
    return p,changes

def combined_transformer():
    core=e.Path('/tmp/pipes_core_round2_20261022.py')
    expected=next(q['transformer']['sha256']for q in e.rows()if q.get('type')=='build'and q.get('kind')=='recycled_deleted_band'and q.get('language')=='cpp')
    assert e.sha(core.read_bytes())==expected
    code='''"""Pure composition; enabled only after the root's fixed screening gate."""
import hashlib,importlib.util
from pathlib import Path
PINS=__PINS__
def _load(path,expected):
 p=Path(path);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
 spec=importlib.util.spec_from_file_location('round2_composed_'+expected[:12],p)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def apply_cpp(source):
 core,guard=(_load(*p)for p in PINS)
 return guard.apply_cpp(core.apply_cpp(source),compact=False)

def apply_cj(source):
 core,guard=(_load(*p)for p in PINS)
 return guard.apply_cj(core.apply_cj(source),compact=False)
'''.replace('__PINS__',repr([(str(core),expected),(str(GUARD),GUARD_SHA)]))
    path=e.Path('/tmp/pipes_core_guarded_envelope_round2_20261022.py')
    if path.exists():assert path.read_text()==code
    else:path.write_text(code)
    return path

assert e.sha(GUARD.read_bytes())==GUARD_SHA
assert not any(q.get('type')=='selection_freeze'for q in e.rows())
e.record(dict(type='guarded_envelope_fixed_gate',kind=KIND,transformer_sha256=GUARD_SHA,compact=False,
    scenarios=SCENARIOS,requirement='all six S deltas >=0; new development40 min delta >= -0.02; epsilon1e-12',
    on_pass='screen core+guarded-envelope on same old215+new40',
    on_fail='only core all2861; core all2861 independently authorized',sealed_final_untouched=True))
e.compile_variant(KIND,GUARD,transformer_kwargs={'compact':False})
paired,changes=run_screen(KIND)
passed=min(changes.values())>=-1e-12 and paired['minimum']>=-.02-1e-12
e.record(dict(type='guarded_envelope_gate_result',kind=KIND,passed=passed,development=paired,S_changes=changes))
print('GUARDED_GATE',passed,flush=True)
if passed:
    combo='core-guarded-envelope'
    e.compile_variant(combo,combined_transformer())
    run_screen(combo)
# Core all2861 independently authorized. All exact source+binary screen rows reuse.
e.batch_pairs(['baseline','recycled_deleted_band'],'archive')
r=e.compact_summary(['recycled_deleted_band'],'archive')
print('CORE_ARCHIVE_RESULT',json.dumps({k:v for k,v in r['comparisons']['recycled_deleted_band'].items()if k=='all'or k.startswith('provenance:')or k.startswith('length:')or k=='weighted_Open15'},ensure_ascii=False),flush=True)
print('STOP_BEFORE_FINAL80_AND_CJ',flush=True)
