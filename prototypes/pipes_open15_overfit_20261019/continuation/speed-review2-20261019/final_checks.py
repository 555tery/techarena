"""Additional boundary coverage and the stdio-only portability path."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'speed-review-20261019'))
import verify_speed as v

def main():
    tests=HERE/'boundary-inputs';tests.mkdir(exist_ok=False)
    # Continue beyond each known stream's final command, within the 200k limit.
    firsts=set()
    for case in range(1,16):
        tokens=(v.REPO/f'data/pipes/open/{case}.in').read_text().split()
        n=int(tokens[1]);commands=list(map(int,tokens[2:2+n]));firsts.add(commands[0])
        if n==200000:continue
        live={};pid=0
        for c in commands:
            if c>0:pid+=1;live[pid]=c
            else:del live[-c]
        for name,extra in [('add',[40]),('delete',[-min(live),40])]:
            seq=commands+extra+[1,19,40]
            (tests/f'{case:02d}_{name}.in').write_text('1\n'+str(len(seq))+'\n'+'\n'.join(map(str,seq))+'\n0\n')
    unseen=next(x for x in range(1,41) if x not in firsts)
    seq=[unseen,40,-1,19,-2,1]
    (tests/'first_mismatch.in').write_text('1\n6\n'+'\n'.join(map(str,seq))+'\n0\n')
    v.HERE=HERE/'boundaries';v.HERE.mkdir(exist_ok=False)
    v.BASE=ROOT/'speed-v4'
    reference=v.run('baseline','boundaries',tests)
    boundary_results={}
    for name in ['speed-v5','speed-v6']:
        v.FAST=ROOT/name
        result=v.run('fast',name,tests)
        assert result['answers']==reference['answers']
        boundary_results[name]=result['cases']
    stdio_results={}
    for name in ['speed-v5','speed-v6']:
        source=ROOT/name;out=source/'stdio-path';out.mkdir(exist_ok=False)
        (out/'solution.cpp').write_bytes((source/'solution.cpp').read_bytes())
        flags=['-O2','-std=c++14','-Wall','-Wextra','-DPIPES_STDIO_IO']
        subprocess.run(['/usr/bin/clang++',*flags,str(out/'solution.cpp'),'-o',str(out/'solver')],check=True)
        build={'source_sha256':v.sha(out/'solution.cpp'),'binary_sha256':v.sha(out/'solver'),
               'compiler':'/usr/bin/clang++','flags':flags,'scope':'stdio path on macOS, not a Windows build'}
        v.e.save(out/'build.json',build)
        v.FAST=out;v.HERE=HERE/(name+'-stdio');v.HERE.mkdir(exist_ok=False)
        total=0
        for suite,inputs,ref in [
            ('open',v.REPO/'data/pipes/open',ROOT/'speed-review-20261019/paired-final/paired-0/fast/verification.json'),
            ('positive',ROOT/'divergence',ROOT/'speed-review-20261019/paired-final/positive-divergence/fast/verification.json'),
            ('negative',ROOT/'speed-review-20261019/paired-final/delete-divergence',ROOT/'speed-review-20261019/paired-final/delete-divergence/fast/verification.json')]:
            result=v.run('fast',suite,inputs)
            assert result['answers']==json.loads(ref.read_text())['answers']
            total+=result['cases']
        stdio_results[name]=total
    result={'status':'verified','boundaries':boundary_results,'stdio_checks':stdio_results,
            'boundary_manifest':{p.name:v.sha(p) for p in sorted(tests.glob('*.in'))},
            'exact_answer_parity':True,'platform_submissions':0,
            'limitations':'C++14 stdio branch verified on macOS only; server build and timings unmeasured.'}
    v.e.save(HERE/'final-checks.json',result)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
