"""Paired full-stream validation; final inputs require a frozen candidate hash."""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('official_harness',ROOT/'tools/pipes_harness.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
BASE=ROOT/'prototypes/pipes_robust_round3_20261019/candidate-physical/solver'
BF=[str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def screen(argv,path):
    data=path.read_text().split();n=int(data[1]);commands=list(map(int,data[2:2+n]))
    result=subprocess.run(['/usr/bin/time','-l','-p',*map(str,argv)],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,timeout=60)
    if result.returncode:raise RuntimeError((path.name,result.returncode,result.stderr[-2000:]))
    lines=result.stdout.splitlines();assert len(lines)==len(commands),(path,len(lines),len(commands))
    cells=bytearray();pipes=[None];T=F=peak=0
    for c,line in zip(commands,lines):
        if c>0:
            digs,x=map(int,line.split());assert digs>=0 and x>=0
            T+=20*digs;assert x+c<=T<=100000000
            if len(cells)<T:cells.extend(b'\0'*(T-len(cells)))
            assert not any(cells[x:x+c]),(path,c,x)
            cells[x:x+c]=b'\1'*c;pipes.append((x,c));F+=c;peak=max(peak,F)
        else:
            x,L=pipes[-c];assert int(line)==x and L>0
            assert all(cells[x:x+L]);cells[x:x+L]=b'\0'*L;pipes[-c]=(x,0);F-=L
    assert F>0
    user=re.search(r'^user\s+(\S+)',result.stderr,re.M);system=re.search(r'^sys\s+(\S+)',result.stderr,re.M)
    rss=re.search(r'(\d+)\s+maximum resident set size',result.stderr)
    return {'status':'ok','case':path.stem,'kpi':F/T,'trench_length_m':T,'final_occupied_length_m':F,'minimum_trench_lower_bound_m':20*((peak+19)//20),
        'operation_count':n,'candidate_stderr':result.stderr,'solver_cpu_total_s':float(user[1])+float(system[1]) if user and system else None,
        'solver_peak_rss_mb':int(rss[1])/1048576 if rss else None,'validation':'bulk stdin full trajectory; independent occupancy check; not interactive protocol validation'}

def tests(group):
    if group in ['calibration','sealed-final','sealed-final-extra','confirmation']:
        directory=HERE/'evaluation'/group
        manifest=json.loads((directory/'manifest.json').read_text())
        return [(row['id'],directory/row['file']) for row in manifest['tests']]
    if group=='open15':return [(str(i),ROOT/f'data/pipes/open/{i}.in') for i in range(1,16)]
    if group=='regression':
        report=json.loads((ROOT/'prototypes/pipes_robust_round3_20261019/report.json').read_text())
        paths=sorted(set(row['file'] for rows in report['paired'].values() for row in rows))
        return [(Path(p).stem,Path(p)) for p in paths]
    raise ValueError(group)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('group');ap.add_argument('--mode',choices=['screen','official'],default='screen')
    ap.add_argument('--ids');ap.add_argument('--names',default='baseline,candidate');ap.add_argument('--candidate',default='candidate')
    ap.add_argument('--workers',type=int,default=2);ap.add_argument('--freeze-manifest',default='freeze.json')
    ap.add_argument('--record-resource-failure',action='store_true');args=ap.parse_args()
    solvers={'baseline':[str(BASE)],'candidate':[str(HERE/args.candidate/'solver')],'bestfit':BF}
    names=args.names.split(',')
    if args.group.startswith('sealed-final') or args.group=='confirmation':
        freeze=json.loads((HERE/args.freeze_manifest).read_text())
        assert freeze['source_sha256']==sha(HERE/args.candidate/'solution.cpp')
        assert freeze['binary_sha256']==sha(HERE/args.candidate/'solver')
    sources=tests(args.group)
    if args.ids:sources=[(i,p) for i,p in sources if i in args.ids.split(',')]
    jobs=[(ident,p,name) for ident,p in sources for name in names]
    def run(job):
        ident,path,name=job;binary=sha(solvers[name][0]);test=sha(path)
        dest=HERE/'measurements'/args.mode/args.group/(args.candidate if name=='candidate' else name)/ident
        record=dest/'record.json';dest.mkdir(parents=True,exist_ok=True)
        if record.exists():
            r=json.loads(record.read_text());assert r['binary_sha256']==binary and r['test_sha256']==test
        else:
            if args.mode=='screen':r=screen(solvers[name],path)
            else:r=h.run_case(solvers[name],ROOT/'tools/interactor',path,dest,5,180)
            r.update(id=ident,strategy=name,source_path=str(path),test_sha256=test,binary_sha256=binary)
            record.write_text(json.dumps(r,indent=2)+'\n')
        assert r['status']=='ok',(ident,name,r.get('detail'))
        if not args.record_resource_failure:
            assert r['solver_cpu_total_s'] is not None and r['solver_cpu_total_s']<5,(ident,name,r)
            assert r['solver_peak_rss_mb'] is not None and r['solver_peak_rss_mb']<256,(ident,name,r)
        if args.group=='open15' and name=='candidate':
            assert r['trench_length_m']==r['minimum_trench_lower_bound_m'],r
            assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr'],r
        return r
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(run,jobs):
            records.append(r);print(r['id'],r['strategy'],round(r['kpi'],6),round(r['solver_cpu_total_s'],3),round(r['solver_peak_rss_mb'],2),flush=True)
    out=HERE/f'{args.mode}-{args.group}-{args.candidate}-summary.json'
    out.write_text(json.dumps({'records':records,'interactor_sha256':sha(ROOT/'tools/interactor'),'harness_sha256':sha(ROOT/'tools/pipes_harness.py'),'platform_actions':0},indent=2)+'\n')
if __name__=='__main__':main()
