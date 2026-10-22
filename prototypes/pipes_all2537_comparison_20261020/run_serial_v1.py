#!/usr/bin/env python3
"""Complete strict interactive comparison. Resume only matching frozen artifacts."""
import argparse
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0,str(ROOT/'shinka-pipes/evaluator-native'))
import native_harness as nh

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int); ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    freeze_path=HERE/'freeze.json'; freeze_sha=sha(freeze_path)
    frozen=json.loads(freeze_path.read_text())
    os.environ['cjProcessorNum']='1'
    assert not any(x in os.environ for x in ['cjHeapSize','cjGCThreshold','cjGCInterval'])
    for name,expected in frozen['support_sha256'].items(): assert sha(ROOT/name)==expected
    for m in frozen['methods']:
        assert sha(HERE/m['source'])==m['source_sha256']
        assert sha(HERE/m['binary'])==m['binary_sha256']
    native=HERE/frozen['native_binary'];assert sha(native)==frozen['native_binary_sha256']
    spec=importlib.util.spec_from_file_location('official_base',ROOT/'tools/pipes_harness.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    out=HERE/'runs'; out.mkdir(exist_ok=True)
    result_path=HERE/'records.jsonl'
    if result_path.exists() and not args.resume: raise SystemExit('Use --resume; existing records preserved.')
    done={}
    if result_path.exists():
        for line in result_path.read_text().splitlines():
            row=json.loads(line);assert row['freeze_sha256']==freeze_sha
            key=(row['id'],row['method']);assert key not in done;done[key]=row
    cases=frozen['cases'][:args.limit] if args.limit else frozen['cases']
    methods=frozen['methods'];started=time.monotonic();last_print=0;new_runs=0
    total=len(cases)*len(methods)
    with result_path.open('a',buffering=1) as sink:
        for i,c in enumerate(cases):
            test=HERE/c['input'];assert sha(test)==c['input_sha256']
            # Cached metadata was independently validated against the frozen input in prepare.py.
            base=SimpleNamespace(**original.__dict__)
            base.parse_test=lambda p,meta=c['meta']:dict(meta)
            ordered=methods[i%len(methods):]+methods[:i%len(methods)]
            for m in ordered:
                key=(c['id'],m['id'])
                if key in done: continue
                dest=out/c['id']/m['id']
                if dest.exists():
                    # Keep incomplete work; never overwrite a previous partial transcript.
                    dest=dest.with_name(m['id']+'-retry-'+str(time.time_ns()))
                t=time.time()
                row=nh.run_case(base,[str(HERE/m['binary'])],native,test,dest,
                                frozen['response_timeout_s'],frozen['wall_timeout_s'])
                response=Path(row['judge_output_file'])
                row.update(id=c['id'],method=m['id'],selected=c['selected'],public_number=c['public_number'],
                           origin=c['origin'],source_group=c['source_group'],started_unix=t,
                           source_sha256=m['source_sha256'],binary_sha256=m['binary_sha256'],
                           freeze_sha256=freeze_sha,workers=1,measurement='strict native interactive; process user+system CPU; no CPU affinity')
                row['response_sha256']=sha(response) if response.exists() else None
                row['within_limits']=not nh.failed(row,frozen['cpu_limit_s'],frozen['memory_limit_mib'])
                row['contest_adjusted_kpi']=row['kpi'] if row['within_limits'] else 0.0
                # Lossless archive of our own fresh transcripts; source artifacts stay untouched.
                if response.exists():
                    packed=response.with_suffix('.txt.gz')
                    with response.open('rb') as src, gzip.open(packed,'wb',compresslevel=1) as dst: shutil.copyfileobj(src,dst)
                    assert hashlib.sha256(gzip.decompress(packed.read_bytes())).hexdigest()==row['response_sha256']
                    row['judge_output_file']=str(packed);response.unlink()
                payload=json.dumps(row,separators=(',',':'))
                (dest/'record.json').write_text(payload+'\n')
                sink.write(payload+'\n');sink.flush()
                done[key]=row;new_runs+=1
                elapsed=time.monotonic()-started
                completed=sum((x['id'],y['id']) in done for x in cases for y in methods)
                progress=dict(completed=completed,total=total,complete_cases=sum(all((x['id'],y['id']) in done for y in methods) for x in cases),
                              elapsed_this_run_s=elapsed,new_runs=new_runs,latest=dict(id=c['id'],method=m['id'],status=row['status'],kpi=row['kpi']),
                              failures=sum(r['status']!='ok' for r in done.values()),resource_failures=sum(r['status']=='ok' and not r['within_limits'] for r in done.values()))
                temp=HERE/'progress.tmp';temp.write_text(json.dumps(progress,indent=2)+'\n');temp.replace(HERE/'progress.json')
                if elapsed-last_print>=30 or not row['within_limits'] or completed==total:
                    print(json.dumps(progress,separators=(',',':')),flush=True);last_print=elapsed
    print('DONE',len(done),'records',flush=True)

if __name__=='__main__':main()
