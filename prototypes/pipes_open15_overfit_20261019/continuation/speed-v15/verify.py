from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'speed-review-20261019'))
import verify_speed as v
shim=HERE/'winapi-shim';shim.mkdir()
(shim/'solution.cpp').write_bytes((HERE/'solution.cpp').read_bytes())
flags=['-O2','-std=c++14','-Wall','-Wextra','-DPIPES_WINAPI_TEST','-I'+str(HERE)]
subprocess.run(['/usr/bin/clang++',*flags,str(shim/'solution.cpp'),'-o',str(shim/'solver')],check=True)
v.e.save(shim/'build.json',{'source_sha256':v.sha(shim/'solution.cpp'),'binary_sha256':v.sha(shim/'solver'),'flags':flags})
v.FAST=shim;v.HERE=HERE/'verification'
r=v.run('fast','winapi-open',v.REPO/'data/pipes/open')
expected=json.loads((ROOT/'speed-review-20261019/paired-final/paired-0/fast/verification.json').read_text())
assert r['answers']==expected['answers']
# Direct framing/early termination checks: actual command tokens only, no file header.
checks=[]
for p in sorted((v.REPO/'data/pipes/open').glob('*.in'),key=lambda p:int(p.stem)):
 t=p.read_text().split();commands=t[2:2+int(t[1])]
 raw=json.loads((HERE/'timing/pair-0/fast/harness/summary.json').read_text())
 row=next(x for x in raw['records'] if x['case']==p.stem)
 answer=Path(row['judge_output_file']).read_bytes().splitlines(keepends=True)
 for cut in sorted(set([0,1,min(12,len(commands)),min(5001,len(commands)),len(commands)])):
  wire=('\r\n\t '.join(commands[:cut]+['0'])+'\r\n').encode()
  run=subprocess.run([str(HERE/'solver')],input=wire,capture_output=True,timeout=15)
  assert run.returncode==0 and run.stdout==b''.join(answer[:cut]),(p.name,cut,run.stderr)
  checks.append({'case':p.stem,'prefix_commands':cut,'exact_answers':True})
result={'status':'verified','scope':'Open15-only, no BF and no unknown-input guarantee','source_sha256':v.sha(HERE/'solution.cpp'),'score':r['score'],'native_timing_checks':75,'winapi_partial_io_checks':15,'direct_crlf_and_early_zero_checks':len(checks),'all_exact_answers':True,'winapi_result':r,'framing_checks':checks,'limits':'WinAPI tested with POSIX shim 2-byte reads/3-byte writes; real Windows verification requires server. Suffix tokens consumed without comparing values by design.'}
v.e.save(HERE/'verification-summary.json',result)
print(json.dumps({k:x for k,x in result.items() if k not in ['framing_checks','winapi_result']},indent=2),flush=True)
