from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'speed-review-20261019'))
import verify_speed as v

def main():
 shim=HERE/'winapi-shim';shim.mkdir(exist_ok=False)
 (shim/'solution.cpp').write_bytes((HERE/'solution.cpp').read_bytes())
 flags=['-O2','-std=c++14','-Wall','-Wextra','-DPIPES_WINAPI_TEST','-I'+str(HERE)]
 subprocess.run(['/usr/bin/clang++',*flags,str(shim/'solution.cpp'),'-o',str(shim/'solver')],check=True)
 v.e.save(shim/'build.json',{'source_sha256':v.sha(shim/'solution.cpp'),'binary_sha256':v.sha(shim/'solver'),'flags':flags,'scope':'POSIX shim of Win32 API, NOT Windows ABI/performance'})
 suites=[('open',v.REPO/'data/pipes/open',ROOT/'speed-review-20261019/paired-final/paired-0/fast/verification.json'),
 ('positive',ROOT/'divergence',ROOT/'speed-review-20261019/paired-final/positive-divergence/fast/verification.json'),
 ('negative',ROOT/'speed-review-20261019/paired-final/delete-divergence',ROOT/'speed-review-20261019/paired-final/delete-divergence/fast/verification.json'),
 ('boundaries',ROOT/'speed-review2-20261019/boundary-inputs',ROOT/'speed-review2-20261019/boundaries/boundaries/baseline/verification.json')]
 rows=[]
 for label,source in [('native',HERE),('winapi-shim',shim)]:
  v.FAST=source;v.HERE=HERE/'verification'/label
  for name,tests,ref in suites:
   result=v.run('fast',name,tests)
   assert result['answers']==json.loads(ref.read_text())['answers']
   rows.append(dict(path=label,suite=name,**result))
 r={'status':'verified','source_sha256':v.sha(HERE/'solution.cpp'),'score':rows[0]['score'],'checks':sum(x['cases'] for x in rows),'all_answers_identical':True,'max_cpu_s':max(x['max_cpu_s'] for x in rows),'max_rss_mib':max(x['max_rss_mib'] for x in rows),'rows':rows,'limits':'WinAPI logic verified with 2-byte reads and 3-byte writes through POSIX shim. Real Windows compile and runtime require platform verification; no speed claim from shim.'}
 v.e.save(HERE/'verification-summary.json',r)
 print(json.dumps({k:x for k,x in r.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main()
