from pathlib import Path
import json
import verify_support as v
HERE=Path(__file__).resolve().parent
v.FAST=HERE;v.HERE=HERE/'qualification'
r=v.run('fast','open',v.REPO/'data/pipes/open')
expected=json.loads((HERE.parent/'speed-v20/verification-summary.json').read_text())['native_result']['answers']
assert r['answers']==expected and abs(r['score']-30.75747404826914)<1e-12
assert min(r['per_case_cpu'].values())>=0.74
v.e.save(HERE/'qualification.json',{'status':'verified_temporary_control','source_sha256':r['source_sha256'],'score':r['score'],'checks':15,'CPU_added_seconds_per_test':0.75,'cpu_sum_s':r['cpu_sum_s'],'max_cpu_s':r['max_cpu_s'],'exact_output_parity':True,'do_not_leave_on_platform':True,'restore_source':str(HERE.parent/'speed-v20/solution.cpp')})
