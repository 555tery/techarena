"""Three fixed own-policy waves plus same-data BF-rollin control. No selection."""
import json
from pathlib import Path
import shutil
import sys
import time
import evaluate as e
ROOT=Path(__file__).resolve().parent
START=time.monotonic()

def run(cmd,out,name,timeout=120):
    if time.monotonic()-START>900:raise TimeoutError('Fixed training budget exhausted')
    rc=e.invoke(cmd,out,name,min(timeout,900-(time.monotonic()-START)))
    if rc:raise RuntimeError(name+' failed; see '+str(out/name))

def compile_pair(name,header):
    out=ROOT/'training-builds'/name;out.mkdir(parents=True,exist_ok=False)
    commands=[]
    for target in ['teacher','solver']:
        cmd=['clang++','-std=c++20','-O2','-Wall','-Wextra',f'-DMODEL_HEADER="{header}"',str(ROOT/'implementation'/f'{target}.cpp'),'-o',str(out/target)]
        run(cmd,out,target+'-compile.log');commands.append(cmd)
    e.save(out/'manifest.json',{'model_sha256':e.sha(header),'commands':commands,'binary_sha256':{t:e.sha(out/t) for t in ['teacher','solver']}})
    return out

def collect(wave,binaries,destination):
    out=destination/f'w{wave}';out.mkdir(parents=True,exist_ok=False)
    for n,inp in enumerate(sorted((ROOT/'data'/f'train{wave}').glob('*.in'))):
        run([str(binaries/'teacher'),'--input',str(inp),'--output',str(out/(inp.stem+'.jsonl')),'--stats',str(out/(inp.stem+'.stats.json'))],out,inp.stem+'.log',60)
    run([sys.executable,'-B',str(ROOT/'audit_wave.py'),str(out),str(binaries/'solver')],out,'audit.log',120)
    print(json.dumps({'collected':str(out.relative_to(ROOT)),'audit':json.loads((out/'audit.json').read_text())['counts']}),flush=True)

def fit(labels,name):
    out=ROOT/'models'/name;out.mkdir(parents=True,exist_ok=False)
    run([sys.executable,'-B',str(ROOT/'implementation/train.py'),'--labels-dir',str(labels),'--out',str(out)],out,'train.log')
    run([sys.executable,'-B',str(ROOT/'implementation/parity.py'),'--model-dir',str(out)],out,'parity.log')
    print(json.dumps({'fitted':name,'fit':json.loads((out/'fit.json').read_text()),'parity':json.loads((out/'parity.log').read_text())}),flush=True)
    return out/'model.hpp'

def verify_sources():
    f=json.loads((ROOT/'training-freeze.json').read_text())
    for p,h in f['artifact_sha256'].items():assert e.sha(ROOT/p)==h,p

def main():
    e.quota()
    if (ROOT/'training-freeze.json').exists():raise ValueError('No automatic repeat or overwrite')
    files=[p for p in (ROOT/'implementation').iterdir() if p.suffix in ['.hpp','.cpp','.py','.md']]
    files += [ROOT/'protocol.json',ROOT/'dataset/generate.py']
    e.save(ROOT/'training-freeze.json',{'created_at':time.time(),'artifact_sha256':{str(p.relative_to(ROOT)):e.sha(p) for p in files},'train_manifest_sha256':{p:e.sha(ROOT/'data'/f'{p}.json') for p in ['train0','train1','train2']}})
    header=ROOT/'implementation/model.hpp';initial=None
    for wave in range(3):
        binaries=compile_pair(f'rollin{wave}',header)
        if initial is None:initial=binaries
        collect(wave,binaries,ROOT/'labels/own')
        verify_sources();header=fit(ROOT/'labels/own',f'M{wave+1}')
    # Wave0 is exactly the same default BF policy and inputs: reuse its labels,
    # not a new teacher call. Later control waves use identical input hashes.
    ctrl=ROOT/'labels/bf_control';ctrl.mkdir(parents=True)
    shutil.copytree(ROOT/'labels/own/w0',ctrl/'w0')
    for wave in [1,2]:collect(wave,initial,ctrl)
    fit(ctrl,'BFrollin');verify_sources()
    e.save(ROOT/'training-completion.json',{'status':'complete','elapsed_seconds':time.monotonic()-START,'own_waves':3,'bf_control_same_inputs':True,'final_checkpoint':'M3','selection':False})

if __name__=='__main__':main()
