"""Fixed full-rollout comparison; no checkpoint or parameter selection."""
from pathlib import Path
import json
import shutil
import time
import evaluate as e
import audit
ROOT=Path(__file__).resolve().parent
LABELS=['candidate','bf_rollin','no_hold','bf','ss','trial22']

def main():
    e.quota()
    assert json.loads((ROOT/'training-completion.json').read_text())['status']=='complete'
    v=json.loads((ROOT/'variants.json').read_text())
    for label,model,defines in [('candidate','M3',[]),('bf_rollin','BFrollin',[]),('no_hold','M3',['OPTION_HOLD=1'])]:
        v[label]={'directory':'implementation','entry':'solver.cpp','defines':defines,'overrides':{'model.hpp':f'models/{model}/model.hpp'}}
    e.save(ROOT/'variants.json',v)
    for label in LABELS[:3]:e.build_variant(label)
    print(audit.solver_check(LABELS[:3]),flush=True)
    for label in LABELS[:3]:e.evaluate(label,'dev',2)
    # Complete own-policy training trajectories, not just local teacher targets.
    records=[];out=ROOT/'data/train';out.mkdir()
    for w in range(3):
        manifest=json.loads((ROOT/'data'/f'train{w}.json').read_text())
        for r in manifest['records']:
            new=dict(r);new['name']=f'w{w}_'+r['name'];new['base']=f'w{w}_'+r['base']
            shutil.copy2(ROOT/'data'/f'train{w}'/(r['name']+'.in'),out/(new['name']+'.in'));records.append(new)
    e.save(ROOT/'data/train.json',{'records':records,'count':len(records),'role':'union of existing three training waves; no new draws'})
    for label in ['candidate','bf_rollin','bf']:e.evaluate(label,'train',2)
    artifacts=[]
    for d in ['implementation','dataset','controls','incumbent','models/M1','models/M2','models/M3','models/BFrollin']:
        artifacts += [p for p in (ROOT/d).glob('*') if p.suffix in ['.cpp','.hpp','.py','.json','.md']]
    artifacts += [ROOT/'protocol.json',ROOT/'evaluate.py',ROOT/'variants.json']
    e.save(ROOT/'freeze.json',{'created_at':time.time(),'artifact_sha256':{str(p.relative_to(ROOT)):e.sha(p) for p in artifacts},
           'binary_sha256':{l:e.sha(ROOT/'builds'/l/'solver') for l in LABELS},'model_choice':'M3 predeclared, no selection'})
    g=audit.source_module('fresh_generator',ROOT/'dataset/generate.py');g.generate('final');print(audit.data_check('final'),flush=True)
    for label in LABELS:e.evaluate(label,'final',2)
    repeat=ROOT/'data/repeat';repeat.mkdir()
    for n in ['renewal_0_growth','bursty_lengths_0_size_shift','anchors_0_early_stop','resource_anchors']:
        shutil.copy2(ROOT/'data/final'/(n+'.in'),repeat/(n+'.in'))
    for label in LABELS:e.evaluate(label,'repeat',2)
    verified=0
    for label in LABELS:
        original={x['case']:x for x in json.loads((ROOT/'evaluations/final'/label/'harness/summary.json').read_text())['records']}
        for x in json.loads((ROOT/'evaluations/repeat'/label/'harness/summary.json').read_text())['records']:
            y=original[x['case']]
            assert x['test_sha256']==y['test_sha256'] and x['trench_length_m']==y['trench_length_m']
            assert Path(x['judge_output_file']).read_bytes()==Path(y['judge_output_file']).read_bytes();verified+=1
    e.save(ROOT/'repeat-audit.json',{'passed':True,'identical_full_transcripts':verified})
    e.verify_freeze()

if __name__=='__main__':main()
