#!/usr/bin/env python3
import argparse,gzip,hashlib,importlib.util,json,os,shutil,sys,time
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'shinka-pipes/evaluator-native'))
import native_harness as nh
spec=importlib.util.spec_from_file_location('official',ROOT/'tools/pipes_harness.py');original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--name',required=True);ap.add_argument('--baseline',action='store_true');ap.add_argument('--resume',action='store_true');args=ap.parse_args()
 os.environ['cjProcessorNum']='1'
 mf=HERE/'fresh/manifest.json';cases=json.loads(mf.read_text())['cases'];out=HERE/'fresh-checks'/args.name;out.mkdir(parents=True,exist_ok=True)
 native=ROOT/'prototypes/pipes_all2537_comparison_20261020/native-build/native_runner'
 identity=dict(binary=str(args.binary.resolve()),binary_sha256=sha(args.binary),source=str(args.source.resolve()),source_sha256=sha(args.source),input_manifest_sha256=sha(mf),runner_sha256=sha(__file__),workers=1,cjProcessorNum=1,cpu_limit_s=5,rss_limit_mib=256,baseline=args.baseline)
 ip=out/'manifest.json'
 if ip.exists():assert args.resume and json.loads(ip.read_text())==identity
 else:ip.write_text(json.dumps(identity,indent=2)+'\n')
 rows=[];rp=out/'records.jsonl'
 if rp.exists():assert args.resume;rows=[json.loads(x) for x in rp.read_text().splitlines()]
 previous={} if args.baseline else {x['id']:x for x in map(json.loads,(HERE/'fresh-checks/baseline-o0/records.jsonl').read_text().splitlines())}
 done={x['id'] for x in rows};started=time.monotonic()
 with rp.open('a',buffering=1) as sink:
  for case in cases:
   if case['id'] in done:continue
   test=ROOT/case['path'];assert sha(test)==case['sha256']
   base=SimpleNamespace(**original.__dict__);base.parse_test=lambda path,meta=case['metadata']:dict(meta)
   dest=out/'runs'/case['id'];assert not dest.exists()
   row=nh.run_case(base,[str(args.binary.resolve())],native,test,dest,5,240)
   response=Path(row['judge_output_file']);digest=sha(response)
   row.update(id=case['id'],family=case['family'],seed=case['seed'],response_sha256=digest,source_sha256=identity['source_sha256'],within_limits=not nh.failed(row,5,256))
   if not args.baseline:row.update(response_equal=digest==previous[case['id']]['response_sha256'],kpi_equal=row.get('kpi')==previous[case['id']].get('kpi'))
   packed=response.with_suffix('.txt.gz')
   with response.open('rb') as src,gzip.open(packed,'wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
   response.unlink();row['judge_output_file']=str(packed)
   sink.write(json.dumps(row,separators=(',',':'))+'\n');rows.append(row)
   progress=dict(completed=len(rows),total=len(cases),failures=sum(x['status']!='ok' for x in rows),mismatches=sum(x.get('response_equal')==False or x.get('kpi_equal')==False for x in rows),resource_failures=sum(not x['within_limits'] for x in rows),cpu_max_s=max(x.get('solver_cpu_total_s') or 0 for x in rows),rss_max_mib=max(x.get('solver_peak_rss_mb') or 0 for x in rows),elapsed_s=time.monotonic()-started,latest=case['id'])
   (out/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress),flush=True)
   if row['status']!='ok' or row.get('response_equal')==False or row.get('kpi_equal')==False:raise SystemExit('parity/correctness failure')
if __name__=='__main__':main()
