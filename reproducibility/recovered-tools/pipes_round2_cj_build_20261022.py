import sys,time,json
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e
core=e.Path('/tmp/pipes_core_round2_20261022.py')
ring=e.Path('/tmp/pipes_ringclone_round2_20261022.py')
assert e.sha(ring.read_bytes())=='0e38115b01607dffebd1d9085071fc666f3f6453ad939d71353206c6b608c641'
e.record(dict(type='quality_policy_choice',selected_cpp='recycled_deleted_band',parent_cj_sha256=e.BASE_UNCACHED_CJ_SHA,
    rejected_quality_kinds=['guarded-envelope','core-guarded-envelope','early-only','side-only','recent-hazard','oriented-guarded'],
    exact_speed_patch_only='IntRing.clone; separate artifact',cpu_review_pause_s=4.5,
    root_authorized=True,final112_still_sealed=True,promotion=False))
for name,transformer,parent in [('core-qualified',core,None),('core-ring',ring,e.E/'core-qualified/uncached/solution.cj')]:
    start=time.monotonic();e.register_cpp_alias(name,'recycled_deleted_band')
    e.compile_cj_variant(name,transformer,cpp_reference='recycled_deleted_band',uncached_source=parent)
    e.record(dict(type='phase_timing',phase=name+'-cj-build-cache-public15',wall_s=time.monotonic()-start,one_heavy_worker=True))
    print('CJ_BUILD_READY',name,str(e.artifact(name,'cj')[0]),e.sha(e.artifact(name,'cj')[0].read_bytes()),flush=True)
print('CJ_TWO_BUILDS_READY_PILOT_NOT_RUN',flush=True)
