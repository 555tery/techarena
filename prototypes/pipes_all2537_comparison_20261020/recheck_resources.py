#!/usr/bin/env python3
"""Sequential checks of fixed resource edges; never replace primary outcomes."""
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'shinka-pipes/evaluator-native'))
import native_harness as nh

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    frozen=json.loads((HERE/'freeze.json').read_text());freeze_sha=sha(HERE/'freeze.json')
    primary=[json.loads(x) for x in (HERE/'records.jsonl').read_text().splitlines()]
    assert len(primary)==len(frozen['cases'])*len(frozen['methods']), 'Finish primary comparison first.'
    indexed={(r['id'],r['method']):r for r in primary};assert len(indexed)==len(primary)
    methods={m['id']:m for m in frozen['methods']};cases={c['id']:c for c in frozen['cases']}
    for m in methods.values():
        assert sha(HERE/m['binary'])==m['binary_sha256'] and sha(HERE/m['source'])==m['source_sha256']
    native=HERE/frozen['native_binary'];assert sha(native)==frozen['native_binary_sha256']
    for name,expected in frozen['support_sha256'].items():assert sha(ROOT/name)==expected
    os.environ['cjProcessorNum']='1'
    assert not any(k in os.environ for k in ['cjHeapSize','cjGCThreshold','cjGCInterval'])
    reasons={}
    def add(r,why):reasons.setdefault((r['id'],r['method']),set()).add(why)
    for r in primary:
        if r['status']!='ok':add(r,'primary protocol/correctness failure')
        if r['solver_cpu_total_s'] is None or r['solver_cpu_total_s']>=4:add(r,'CPU >= 4 s or unavailable')
        if r['solver_peak_rss_mb'] is None or r['solver_peak_rss_mb']>=230:add(r,'RSS >= 230 MiB or unavailable')
    for method in methods:
        rows=[r for r in primary if r['method']==method]
        for r in sorted(rows,key=lambda x:x['solver_cpu_total_s'] or 0,reverse=True)[:3]:add(r,'three largest primary CPU measurements')
        add(max(rows,key=lambda x:x['solver_peak_rss_mb'] or 0),'largest primary RSS measurement')
    for identity,method in list(reasons):
        if method in ['online_cpp','online_cj']:
            counterpart='online_cj' if method=='online_cpp' else 'online_cpp'
            add(indexed[identity,counterpart],'paired current online C++/Cangjie resource comparison')
    plan=dict(freeze_sha256=freeze_sha,primary_records_sha256=sha(HERE/'records.jsonl'),runner_sha256=sha(Path(__file__)),
              workers=1,rule='All failed/CPU>=4s/RSS>=230MiB, top3 CPU and top1 RSS per method; paired C++/CJ counterparts. One fresh repeat, primary results preserved.',
              jobs=[dict(id=k[0],method=k[1],reasons=sorted(v)) for k,v in sorted(reasons.items())])
    target=HERE/'resource-recheck';target.mkdir(exist_ok=True)
    plan_path=target/'plan.json'
    if plan_path.exists():assert json.loads(plan_path.read_text())==plan
    else:plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    result_path=target/'records.jsonl'
    done={}
    if result_path.exists():
        for line in result_path.read_text().splitlines():
            r=json.loads(line);assert r['freeze_sha256']==freeze_sha;done[r['id'],r['method']]=r
    spec=importlib.util.spec_from_file_location('official_base',ROOT/'tools/pipes_harness.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    with result_path.open('a',buffering=1) as sink:
        for j,item in enumerate(plan['jobs']):
            key=(item['id'],item['method'])
            if key in done:continue
            c=cases[key[0]];m=methods[key[1]];p=indexed[key]
            assert sha(HERE/c['input'])==c['input_sha256']
            base=SimpleNamespace(**original.__dict__);base.parse_test=lambda path,meta=c['meta']:dict(meta)
            folder=target/'runs'/c['id']/m['id']
            if folder.exists():folder=folder.with_name(m['id']+'-retry-'+str(time.time_ns()))
            r=nh.run_case(base,[str(HERE/m['binary'])],native,HERE/c['input'],folder,5,240)
            transcript=Path(r['judge_output_file']);response_sha=sha(transcript) if transcript.exists() else None
            r.update(**item,freeze_sha256=freeze_sha,workers=1,source_sha256=m['source_sha256'],binary_sha256=m['binary_sha256'],
                     response_sha256=response_sha,within_limits=not nh.failed(r,5,256),
                     primary_cpu_s=p['solver_cpu_total_s'],primary_rss_MiB=p['solver_peak_rss_mb'],primary_kpi=p['kpi'],
                     primary_workers=p['workers'],answers_equal_to_primary=response_sha==p['response_sha256'])
            if transcript.exists():
                packed=transcript.with_suffix('.txt.gz')
                with transcript.open('rb') as src,gzip.open(packed,'wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
                assert hashlib.sha256(gzip.decompress(packed.read_bytes())).hexdigest()==response_sha
                r['judge_output_file']=str(packed);transcript.unlink()
            sink.write(json.dumps(r,separators=(',',':'))+'\n');sink.flush();done[key]=r
            print(json.dumps(dict(completed=j+1,total=len(plan['jobs']),method=m['id'],CPU=r['solver_cpu_total_s'],RSS=r['solver_peak_rss_mb'],status=r['status'],pass_limits=r['within_limits'],answers_equal=r['answers_equal_to_primary'])),flush=True)
    summary=dict(complete=len(done)==len(plan['jobs']),plan_sha256=sha(plan_path),records_sha256=sha(result_path),
                 jobs=len(done),workers=1,failures=[{'id':r['id'],'method':r['method'],'status':r['status'],'cpu':r['solver_cpu_total_s'],'rss':r['solver_peak_rss_mb']} for r in done.values() if not r['within_limits']],
                 changed_answers=[{'id':r['id'],'method':r['method'],'primary_kpi':r['primary_kpi'],'repeat_kpi':r['kpi']} for r in done.values() if not r['answers_equal_to_primary']])
    (target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('DONE',json.dumps(summary),flush=True)

if __name__=='__main__':main()
