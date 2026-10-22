"""Integrate the jointly compatible, physically audited Open8/Open13 plans."""
import datetime
import json
import subprocess
import sys
from common import HERE,PRIOR,e

def main():
    all_groups='--all' in sys.argv
    audit=json.loads((HERE/'components/audit.json').read_text())
    assert audit['all15_shared_prefix_consistent']
    targets=[('candidate',HERE/'proposal/solution.cpp'),('plans-only',PRIOR/'final/solution.cpp')] if all_groups else [('final',HERE/'proposal/solution.cpp'),('plan-only',PRIOR/'final/solution.cpp')]
    group_dirs=[HERE/'components',HERE/'components/pair-11-15',HERE/'components/pair-5-9',HERE/'components/pair-12',HERE/'components/pair-14'] if all_groups else [HERE/'components']
    full_audits=[json.loads((p/'audit.json').read_text()) for p in group_dirs]
    for name,parent in targets:
        tables=e.decode(parent)
        for directory,entry in zip(group_dirs,full_audits):
            assert entry['all15_shared_prefix_consistent']
            for case in entry['cases']:
                it=iter(map(int,(directory/f'open{case}.positions').read_text().split()))
                cmd=tables[case-1][0];tables[case-1]=(cmd,[next(it) if c>0 else None for c in cmd]);assert next(it,None) is None
        for i in range(15):
            for j in range(i):
                for a,b,x,y in zip(tables[i][0],tables[j][0],tables[i][1],tables[j][1]):
                    if a!=b:break
                    assert x==y
        source=parent.read_text();a=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');b=source.index('};',a)
        source=source[:a]+'\n'+e.encode(tables)+source[b:]
        dest=HERE/name;dest.mkdir(exist_ok=True);(dest/'solution.cpp').write_text(source)
        r=subprocess.run(['clang++','-std=c++20','-O2',str(dest/'solution.cpp'),'-o',str(dest/'solver')],text=True,capture_output=True)
        (dest/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
        m={'source_sha256':e.sha(dest/'solution.cpp'),'binary_sha256':e.sha(dest/'solver'),
           'parent_source_sha256':e.sha(parent),'changed_tables':sorted(c for entry in full_audits for c in entry['cases']),
           'full_public_prefix_max_ratio':{str(a['case']):a['ratio'] for entry in full_audits for a in entry['audits']},
           'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'selection':'public-only static component objective + pre-frozen transactional runtime; no round3 fresh scores used'}
        (dest/'build.json').write_text(json.dumps(m,indent=2)+'\n');print(name,m['source_sha256'],flush=True)
    (HERE/('freeze-all.json' if all_groups else 'freeze.json')).write_text(json.dumps({'candidates':[name for name,parent in targets],
      'hard_gate':'all15 volume ceilings, valid answers, CPU<5,RSS<256',
      'runtime_gate':'no loss on old55',
      'joint_plan_gate':'mean gain on diagnostics >=0; no individual loss >.02',
      'fresh_gate':'holdout mean>=0 and no individual loss>.03; new targeted tests reported separately',
      'scope':'bounded round3; finite tests, no hidden-distribution claim'},indent=2)+'\n')

if __name__=='__main__':main()
