"""Freeze once, repeat Open15, and test one new independent release suite."""
import argparse,fcntl,hashlib,importlib.util,json,random,secrets,shutil,time
from pathlib import Path
from evaluate import evaluate,digest,save,quota,CAMPAIGN as ROOT
from loop import compare,reuse_or_evaluate
import make_fresh

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);a=ap.parse_args()
    source=a.source.resolve()
    if not source.is_relative_to(ROOT):raise ValueError('source outside campaign')
    quota();sha=digest(source);out=ROOT/'releases'/sha
    out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.release.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'release-result.json').exists():
        result=json.loads((out/'release-result.json').read_text())
        if result.get('source_sha256')!=sha:raise ValueError('release result identity mismatch')
        if (out/'freeze.json').exists():
            f=json.loads((out/'freeze.json').read_text());f.update(release_results_seen=True,result_sha256=digest(out/'release-result.json'));save(out/'freeze.json',f)
        print(json.dumps(dict(status='already_consumed',new_independent_replication=False,result_path=str(out/'release-result.json'),original_result=result),ensure_ascii=False));lock.close();return
    frozen=out/'solution.cpp'
    if frozen.exists() and digest(frozen)!=sha:raise ValueError('freeze mismatch')
    if not frozen.exists():shutil.copy2(source,frozen)
    freeze=out/'freeze.json'
    if not freeze.exists():save(freeze,dict(source=str(source),sha256=sha,frozen_at=time.time(),release_results_seen=False))
    inputs=out/'fresh';inputs.mkdir(exist_ok=True)
    dp=inputs/'design.json'
    if dp.exists():design=json.loads(dp.read_text())
    else:
        namespace=secrets.randbits(128);rng=random.Random(namespace);design=make_fresh.design('release')
        design.update(namespace=namespace,frozen_source_sha256=sha,created_after_freeze=True,generator_sha256=digest(Path(__file__)),dependency_sha256={str(p):digest(p) for p in [Path(make_fresh.__file__),make_fresh.OLD/'generate_checks.py',make_fresh.OLD/'generate_lifo_checks.py']},purpose='Independent post-freeze release, excluded from model feedback and parent selection')
        for i,row in enumerate(design['cases']):
            s=row['spec'];s['seed']=rng.randrange(2**63);row['name']='release_'+str(i).zfill(2)+'_'+row['kind']
            if row['kind']=='general':
                s.update(operations=200000 if i<2 else 80000,short_max=rng.choice([2,4,7,10,14]),large_min=rng.choice([8,12,20]),transition_fraction=rng.uniform(.2,.8),recent_span=rng.choice([8,24,64,160,320]),old_delete_probability=rng.choice([0,.015,.08,.2]),insert_first=rng.uniform(.58,.94),insert_second=rng.uniform(.48,.75))
            elif row['kind']=='lifo':
                s.update(operations=200000,target_live=[6144,16384,32768,65536,12288,24576][i-12],recent_window=rng.choice([8,24,64,128,256]))
            elif row['kind']=='frames':s.update(retain_probability=rng.uniform(.04,.4),max_frame=rng.choice([4,16,48,192]),operations=100000)
            else:s.update(max_live=rng.choice([1,2,3,4,6]),size_limit=rng.choice([4,8,12,20]))
        save(dp,design)
    general=make_fresh.load('release_general',make_fresh.OLD/'generate_checks.py');lifo=make_fresh.load('release_lifo',make_fresh.OLD/'generate_lifo_checks.py')
    for row in design['cases']:
        p=inputs/(row['name']+'.in')
        if p.exists():continue
        ops=general.generate(row['spec']) if row['kind']=='general' else lifo.generate(row['spec']) if row['kind']=='lifo' else make_fresh.custom(row)
        p.write_text(f'1.0 {len(ops)}\n'+'\n'.join(map(str,ops+[0]))+'\n')
    save(inputs/'manifest.json',dict(design_sha256=digest(dp),inputs={p.name:digest(p) for p in sorted(inputs.glob('*.in'))}))
    pub=reuse_or_evaluate(frozen,ROOT.parents[1]/'data/pipes/open',out/'open15_repeat','release repeat')
    baseline=reuse_or_evaluate(ROOT/'seeds/baseline.cpp',inputs,out/'baseline_fresh','release baseline')
    candidate=reuse_or_evaluate(frozen,inputs,out/'candidate_fresh','release candidate')
    result=dict(source_sha256=sha,source=str(frozen),created_at=time.time(),correct=all(x.get('correct') for x in [pub,baseline,candidate]),public_score=pub.get('weighted_score'),platform_submission_automatic=False)
    if result['correct']:
        b=json.loads(Path(baseline['summary_path']).read_text());c=json.loads(Path(candidate['summary_path']).read_text());result['fresh']=compare(c,b)
        original=[r for r in json.loads((ROOT/'archive.json').read_text()) if r['sha256']==sha]
        if original:
            prev=json.loads(Path(original[0]['public_summary']).read_text());repeat=json.loads(Path(pub['summary_path']).read_text());aa={r['case']:digest(Path(r['judge_output_file'])) for r in prev['records']};bb={r['case']:digest(Path(r['judge_output_file'])) for r in repeat['records']};result['all15_repeat_transcripts_identical']=aa==bb
        result['transfer_assessment']='mixed_or_negative' if result['fresh']['mean_delta']<=0 or result['fresh']['regressions']>result['fresh']['wins'] else 'positive_on_this_fresh_sample_only'
    save(out/'release-result.json',result)
    f=json.loads(freeze.read_text());f.update(release_results_seen=True,consumed_at=time.time(),result_sha256=digest(out/'release-result.json'));save(freeze,f)
    print(json.dumps(result,ensure_ascii=False));lock.close()
if __name__=='__main__':main()
