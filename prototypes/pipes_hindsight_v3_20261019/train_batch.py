"""One fixed training attempt, quota guarded, no automatic tuning/retries."""
import json
from pathlib import Path
import sys
import time
import evaluate as e
ROOT=Path(__file__).resolve().parent

def main():
    e.quota()
    freeze=ROOT/'training-freeze.json'
    if freeze.exists():raise ValueError('Training already started; no overwrite')
    sources=list((ROOT/'implementation').glob('*.hpp'))+list((ROOT/'implementation').glob('*.cpp'))
    sources += [ROOT/'implementation/train.py', ROOT/'implementation/README.md',ROOT/'dataset/generate.py',ROOT/'protocol.json']
    e.save(freeze,{'created_at':time.time(),'artifact_sha256':{str(p.relative_to(ROOT)):e.sha(p) for p in sources},
                   'teacher_binary_sha256':e.sha(ROOT/'implementation/teacher'),
                   'train_manifest_sha256':e.sha(ROOT/'data/train.json'),
                   'attempts':1,'recipe':'causal_cross128_v1 pairwise logistic L2=.05, fixed Newton40'})
    out=ROOT/'labels/train';out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();count=0
    for inp in sorted((ROOT/'data/train').glob('*.in')):
        remaining=600-(time.monotonic()-start)
        if remaining<=0:raise TimeoutError('Total teacher budget exhausted')
        cmd=[str(ROOT/'implementation/teacher'),'--input',str(inp),'--output',str(out/(inp.stem+'.jsonl')),'--stats',str(out/(inp.stem+'.stats.json'))]
        rc=e.invoke(cmd,out,inp.stem+'.log',min(60,remaining));count+=1
        if rc:raise ValueError('Teacher failed: '+inp.name)
        print(json.dumps({'completed':count,'elapsed':round(time.monotonic()-start,2)}),flush=True)
    e.save(ROOT/'teacher-batch.json',{'completed_files':count,'elapsed_seconds':time.monotonic()-start})
    # Independent witness/label verification MUST pass before fitting.
    rc=e.invoke([sys.executable,'-B',str(ROOT/'audit_labels.py')],ROOT,'teacher-audit.log',120)
    if rc:raise ValueError('Independent teacher audit failed')
    rc=e.invoke([sys.executable,'-B',str(ROOT/'implementation/train.py'),'--labels-dir',str(out),'--out',str(ROOT/'model')],ROOT,'training.log',120)
    if rc not in (0,3):raise ValueError('Fixed training failed')
    frozen=json.loads(freeze.read_text())
    for name,digest in frozen['artifact_sha256'].items():
        assert e.sha(ROOT/name)==digest,'Training source changed: '+name
    print((ROOT/'training.log').read_text(),flush=True)

if __name__=='__main__':main()
