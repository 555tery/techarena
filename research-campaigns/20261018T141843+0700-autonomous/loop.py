"""Subscription-only, quota-bounded causal allocator research with immutable trials."""
import concurrent.futures as futures
import difflib, fcntl, hashlib, json, os, random, re, signal, statistics
import subprocess, sys, tempfile, threading, time, traceback
from datetime import datetime
from pathlib import Path
import psutil
from evaluate import evaluate, digest, save, quota

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'shinka-pipes'))
from local_runtime import subscription_environment, check_prerequisites
sys.path.insert(0,str(REPO/'shinka-pipes/search-v3-1'))
from codex_transport import command as text_command
from usage_guard import UsageStopped, gate

LOCK=threading.RLock()
STOP=threading.Event()
SCHEMA={'type':'object','properties':{
    'idea':{'type':'string'},'hypothesis':{'type':'string'},'causality':{'type':'string'},
    'changes':{'type':'array','items':{'type':'object','properties':{'find':{'type':'string'},'replace':{'type':'string'}},'required':['find','replace'],'additionalProperties':False}},
    'full_source':{'type':'string'}},'required':['idea','hypothesis','causality','changes','full_source'],'additionalProperties':False}
FOCUSES=[
 'Change early placement geometry to avoid permanent barriers among retained objects under recent deletions. A tail-only repair is insufficient.',
 'Learn allocation lifetime classes causally from observed deletion events and outstanding object ages. Do not assume unobserved survivors can be labelled.',
 'Represent and preserve contiguous spans that can coalesce under stack/frame deletions; avoid individual tiny holes isolated by old objects.',
 'Explore mathematically justified packing opportunity cost across sizes, or complementary gap formation. Preserve useful existing cohort/trend rules.',
 'Improve small and medium cases by section-boundary opportunity, insertion side, or prediction confidence; avoid arbitrary stream-specific gates.',
 'Develop a substantially different causal allocator, considering exact fit, segregated slabs, page reuse, or lifetime cohorts; explain why old failed arenas differ.',
 'Use observation of deletion correlations to improve contiguous packing of objects likely to die together, including non-LIFO episodes.',
 'Reconsider whether high-side and low-side placement should depend on expected future coalescence; derive signals only from past observations.',
 'Choose a useful combination of two already measured mechanisms, while preserving each mechanism assumptions and exact candidate enumeration.',
 'Find a robust generalization improvement on diverse fresh development families without sacrificing official weighted score.'
]
PRIOR='''This is online nonmoving dynamic storage allocation. Requests L=1..40 arrive sequentially; negative request deletes a previous insertion PID; answer immediately. Extend trench in20m sections, never shrink or move live pipes. Objective sum(weight*final live volume/final trench); weights total32.1. 200k operations,5s CPU,256MiB. Strictly no future input, test identity/fingerprint, precomputed answers, external files/network, N-specific special casing or oracle labels. You have only supplied source and measured past feedback; no tools are available.
Best verified public seed30.0787631641; C199 baseline30.0742879764. Leader at30.75699652, volume ceiling30.75747405, not a proved online-attainable optimum. Main gaps case15 (~.45score),11(~.07),13(~.07). For fixed first100k operations of baseline, surviving permanent barriers imply T15>=433720, vsactual438640: reaching leader requires changing early prefix. This conditional bound uses future labels only as diagnosis, not an online signal.
Past controlled no-gos: size class arenas and simple birth-generation bins severely regressed; deeper IID Monte Carlo, generic ML rankers, random exact-fit ties and cyclic next-fit regressed. Dual inventory/knapsack prices helped an otherwise weaker gen85(T15=438520) but pure transfer into baseline worsened T15 to439160. Highest-address ties alone worsened439060; combined dual+address438540 indicates interaction. Small confident LIFO high-address ties helped case11 by100m. Recent-free-age tie large-scale helped15 by20m but fresh results mixed. C70 fresh30:2wins,6regressions,22ties,mean deltaF/T=-.00029586; not evidence of general gain. Don't repeat no-gos without a materially distinct causal hypothesis.
Preserve protocol/flush and section-growth invariants. Use std C++20 only. Strong source contains important parity/cohort/slab/geometric/run heuristics; a blind total rewrite loses cases2/3/5/9. Significant innovation is welcome, but an isolated tested mechanism is easier to interpret than many arbitrary threshold changes.'''

def event(value):
    with LOCK:
        with (ROOT/'events.jsonl').open('a') as f:f.write(json.dumps(dict(at=time.time(),**value),ensure_ascii=False)+'\n')
        print(json.dumps(value,ensure_ascii=False),flush=True)

def budget_reserve():
    with LOCK:
        quota()
        path=ROOT/'counters.json';v=json.loads(path.read_text()) if path.exists() else dict(model_calls=0,failed_proposals=0,evaluated=0)
        policy=json.loads((ROOT/'manifest.json').read_text())
        if v['model_calls']>=policy['max_model_calls']:raise RuntimeError('model_call_budget_exhausted')
        v['model_calls']+=1;save(path,v);return v['model_calls']

def bump(key):
    with LOCK:
        p=ROOT/'counters.json';v=json.loads(p.read_text());v[key]=v.get(key,0)+1;save(p,v)

def reserve_evaluation(trial,source):
    with LOCK:
        p=ROOT/'counters.json';v=json.loads(p.read_text());v.setdefault('evaluation_attempts',v['evaluated'])
        key=str(Path(trial).relative_to(ROOT));sha=digest(source)
        reservations=v.setdefault('evaluation_reservations',{})
        if key in reservations:
            if reservations[key]['source_sha256']!=sha:raise RuntimeError('evaluation reservation source changed')
            return
        limit=json.loads((ROOT/'manifest.json').read_text())['target_evaluated']
        if v['evaluation_attempts']>=limit:raise RuntimeError('evaluation_attempt_budget_exhausted')
        v['evaluation_attempts']+=1;reservations[key]=dict(source_sha256=sha,index=v['evaluation_attempts'],reserved_at=time.time());save(p,v)

def stopping():
    return STOP.is_set() or (ROOT/'night-stop-request.json').exists()

def model(prompt, out):
    if stopping():raise UsageStopped('stop requested')
    call=budget_reserve();out.mkdir(parents=True,exist_ok=False)
    (out/'prompt.txt').write_text(prompt);save(out/'schema.json',SCHEMA)
    work=Path(tempfile.mkdtemp(prefix='pipes-causal-model-'))
    env=subscription_environment()
    args=['exec','--json','--skip-git-repo-check','--sandbox','read-only','--model','gpt-6.1-sol','-c','model_reasoning_effort="xhigh"','-c','forced_login_method="chatgpt"','-c','model_provider="openai"','--output-schema',str(out/'schema.json'),'--output-last-message',str(out/'response.json'),'-']
    cmd=text_command(args,work)
    with (out/'prompt.txt').open('r') as inp,(out/'trace.jsonl').open('w') as log,(out/'stderr.log').open('w') as err:
        gate(ROOT,min_remaining_percent=65,max_age_seconds=0)
        proc=subprocess.Popen(cmd,stdin=inp,stdout=log,stderr=err,cwd=work,env=env,start_new_session=True)
        record=ROOT/'processes'/f'{proc.pid}.json'
        value=dict(pid=proc.pid,created_at=psutil.Process(proc.pid).create_time(),out=str(out),kind='model',call=call,status='running',started_at=time.time())
        save(record,value);started=time.monotonic()
        try:
            while proc.poll() is None:
                if stopping() or time.monotonic()-started>1200:
                    try:
                        tree=psutil.Process(proc.pid)
                        for child in tree.children(recursive=True):child.terminate()
                        tree.terminate()
                    except psutil.NoSuchProcess:pass
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
                    raise RuntimeError('model_timeout_or_stop')
                time.sleep(.5)
            if proc.returncode:raise RuntimeError(f'model_exit_{proc.returncode}: '+(out/'stderr.log').read_text()[-1800:])
        finally:
            value.update(status='finished',returncode=proc.poll(),finished_at=time.time());save(record,value)
    response=json.loads((out/'response.json').read_text())
    if set(response)!=set(SCHEMA['required']):raise ValueError('response schema mismatch')
    # Keep auditable evidence that the requested effort and model were actually accepted.
    usage=[];tools=[];notices=[]
    for line in (out/'trace.jsonl').read_text().splitlines():
        try:r=json.loads(line)
        except json.JSONDecodeError:continue
        if r.get('type')=='turn.completed':usage.append(r.get('usage'))
        item=r.get('item',{})
        if item.get('type')=='error':notices.append(item.get('message',''))
        elif item.get('type') not in [None,'reasoning','agent_message']:tools.append(item.get('type'))
    save(out/'usage.json',dict(call=call,model='gpt-6.1-sol',reasoning_effort='xhigh',service_tier='default',billing='subscription',wall_seconds=time.monotonic()-started,usage=usage,unexpected_item_types=tools,notices=notices))
    if tools:raise ValueError('unexpected tool activity in text-only transport')
    return response

def apply(parent, response):
    text=parent
    if response['full_source'].strip():
        if response['changes']:raise ValueError('choose full_source OR changes')
        text=response['full_source']
    else:
        if not response['changes']:raise ValueError('empty proposal')
        for change in response['changes']:
            find=change['find']
            if not find or text.count(find)!=1:raise ValueError('search block must match exactly once: '+find[:140])
            text=text.replace(find,change['replace'],1)
    if text==parent:raise ValueError('unchanged source')
    if len(text)>220000 or len(text)<300 or 'main(' not in text.replace('main (','main('):raise ValueError('invalid source length/main')
    forbidden=r'\b(fopen|freopen|ifstream|ofstream|fstream|filesystem|socket|connect|popen|system|execve|execl|getenv|dlopen|fork)\s*(?:\(|::|<)|#\s*include\s*[<"](?:filesystem|fstream|unistd|sys/)'
    if re.search(forbidden,text):raise ValueError('external state or process access is excluded')
    if re.search(r'olympic|\.in["\x27]|/Users/|clairvoyant|survivorLabels',text,re.I):raise ValueError('test/external/oracle reference excluded')
    return text

def summary(manifest):
    if not manifest.get('correct'):return None
    return json.loads(Path(manifest['summary_path']).read_text())

def reuse_or_evaluate(source,tests,out,label):
    """Reuse a complete immutable result only after source, input and result checks."""
    source,tests,out=Path(source).resolve(),Path(tests).resolve(),Path(out)
    candidates=[out,*sorted(out.parent.glob(out.name+'_recovery_*'))]
    for candidate in candidates:
        p=candidate/'manifest.json'
        if not p.exists():continue
        m=json.loads(p.read_text())
        inputs=sorted(tests.glob('*.in')) if tests.is_dir() else [tests]
        if (m.get('source_sha256')==digest(source) and m.get('tests')==str(tests)
            and m.get('input_sha256')=={str(x):digest(x) for x in inputs}
            and m.get('status') in ['completed','rejected','compile_failed','harness_failed']):
            if m.get('correct'):
                if digest(Path(m['summary_path']))!=m['summary_sha256']:raise RuntimeError('reused summary changed')
                if digest(candidate/'source.cpp')!=m['source_sha256']:raise RuntimeError('reused source changed')
            return m
    if not out.exists():return evaluate(source,tests,out,label)
    # Preserve an interrupted directory in place and use a distinct output name.
    for i in range(1,100):
        resumed=out.with_name(out.name+f'_recovery_{i}')
        if not resumed.exists():return evaluate(source,tests,resumed,label)
    raise RuntimeError('too many interrupted outputs')

def compare(a,b):
    aa={r['test_sha256']:r for r in a['records']};bb={r['test_sha256']:r for r in b['records']}
    if aa.keys()!=bb.keys():raise ValueError('comparison coverage mismatch')
    delta=[aa[k]['kpi']-bb[k]['kpi'] for k in aa]
    worst=sorted(aa,key=lambda k:aa[k]['kpi']-bb[k]['kpi'])[:6]
    return dict(mean_delta=statistics.mean(delta),worst_delta=min(delta),wins=sum(x>1e-12 for x in delta),regressions=sum(x< -1e-12 for x in delta),ties=sum(abs(x)<=1e-12 for x in delta),worst_cases=[dict(case=aa[k].get('case',k),delta=aa[k]['kpi']-bb[k]['kpi'],baseline_T=bb[k].get('trench_length_m'),candidate_T=aa[k].get('trench_length_m')) for k in worst])

def record(source, trial, idea, parent=None, known=None):
    reserve_evaluation(trial,source)
    public=reuse_or_evaluate(source,REPO/'data/pipes/open',trial/'open15',idea[:60])
    if not public.get('correct'):return dict(status='invalid',manifest=public)
    fresh=reuse_or_evaluate(source,ROOT/'fresh/dev',trial/'fresh_dev',idea[:60])
    if not fresh.get('correct'):return dict(status='invalid_fresh',manifest=fresh)
    pub=summary(public);dev=summary(fresh)
    baseline=known if known is not None else json.loads((ROOT/'baseline-fresh.json').read_text())
    comp=compare(dev,baseline)
    details=[dict(case=r['case'],T=r['trench_length_m'],kpi=r['kpi'],weighted_score=r['weighted_score']) for r in pub['records']]
    result=dict(status='completed',id=trial.name,source=str(source),sha256=digest(source),idea=idea,parent=parent,weighted_score=public['weighted_score'],cases=details,fresh=comp,fresh_mean_kpi=statistics.mean(r['kpi'] for r in dev['records']),max_cpu_s=max(public['max_cpu_s'],fresh['max_cpu_s']),max_rss_mib=max(public['max_rss_mib'],fresh['max_rss_mib']),public_summary=public['summary_path'],fresh_summary=fresh['summary_path'],finished_at=time.time())
    result['balanced_gate']=comp['mean_delta']>=-.0005 and comp['worst_delta']>=-.02
    save(trial/'result.json',result);bump('evaluated')
    return result

def history(rows):
    ordered=sorted(rows,key=lambda r:r['weighted_score'],reverse=True)
    recent=rows[-14:]
    return json.dumps(dict(best=[{k:r[k] for k in ['id','idea','weighted_score','fresh','cases']} for r in ordered[:3]],recent=[{k:r[k] for k in ['id','idea','weighted_score','fresh']} for r in recent]),ensure_ascii=False)

def evaluation_feedback(response,result):
    m=result['manifest'];message='\nPrevious response failed evaluation: '+json.dumps(result,ensure_ascii=False)[:5000]
    command=m.get('compile_command',[])
    directory=Path(command[-1]).parent if command else None
    if directory is not None:
        for filename in ['compile.log','harness.log']:
            p=directory/filename
            if p.is_file():message+='\n'+filename+':\n'+p.read_text()[-6000:]
    if m.get('summary_path'):
        s=json.loads(Path(m['summary_path']).read_text())
        errors=[{k:r.get(k) for k in ['case','status','detail','candidate_stderr','solver_cpu_total_s','solver_peak_rss_mb']} for r in s['records'] if r.get('status')!='ok' or (r.get('solver_cpu_total_s') or 0)>=5 or (r.get('solver_peak_rss_mb') or 0)>=256]
        message+='\nFailing cases:\n'+json.dumps(errors,ensure_ascii=False)[:10000]
    message+='\nYour complete previous proposal:\n'+json.dumps(response,ensure_ascii=False)
    return message+'\nRepair from the ORIGINAL parent source, using complete replacement blocks. Previous candidate was not accepted.'

def propose(number,parent,rows,recover=False):
    trial=ROOT/'proposals'/f'trial_{number:04d}';trial.mkdir(exist_ok=recover)
    plan=dict(number=number,parent=parent['id'],parent_source=parent['source'],parent_sha256=parent['sha256'])
    if (trial/'plan.json').exists():
        if json.loads((trial/'plan.json').read_text())!=plan:raise RuntimeError('proposal recovery parent changed')
    else:save(trial/'plan.json',plan)
    original=Path(parent['source']).read_text();feedback='';response=None
    focus=FOCUSES[(number-1)%len(FOCUSES)]
    prompt=PRIOR+'\n\nRESEARCH FOCUS: '+focus+'\nParent '+parent['id']+' measured score '+str(parent['weighted_score'])+'\nMeasured memory:\n'+history(rows)
    notes=ROOT/'research-notes.json'
    if notes.exists():prompt+='\nAdditional independently checked findings:\n'+notes.read_text()[:12000]
    if number%7==0:
        others=[r for r in sorted(rows,key=lambda r:r['weighted_score'],reverse=True) if r['sha256']!=parent['sha256']]
        if others:prompt+='\nOptional crossover donor; do not blindly merge:\n```cpp\n'+Path(others[0]['source']).read_text()+'\n```\n'
    prompt+='\nParent exact source:\n```cpp\n'+original+'\n```\nReturn JSON matching schema. Normally changes are exact unique search/replace blocks; full_source must be empty. For a fundamentally different standalone allocator supply full_source and empty changes. Explain one concrete hypothesis and causal observables. Avoid tiny parameter sweeps and test-specific dispatch.'
    for attempt in range(3):
        try:
            if stopping():raise UsageStopped('stop requested')
            model_dir=trial/f'model_{attempt}'
            if recover and model_dir.exists():
                if not (model_dir/'response.json').exists():continue
                response=json.loads((model_dir/'response.json').read_text())
                for line in (model_dir/'trace.jsonl').read_text().splitlines():
                    try:item=json.loads(line).get('item',{})
                    except json.JSONDecodeError:continue
                    if item.get('type') not in [None,'reasoning','agent_message','error']:raise ValueError('unexpected tool activity in recovered response')
                save(model_dir/'recovered.json',dict(recovered_at=time.time(),source='completed saved response',model_call_repeated=False))
            else:response=model(prompt+feedback,model_dir)
            source=apply(original,response)
            sha=hashlib.sha256(source.encode()).hexdigest()
            with LOCK:
                hashes={r['sha256'] for r in rows}
            if sha in hashes:raise ValueError('exact duplicate of previously evaluated source')
            p=trial/f'candidate_{attempt}.cpp';p.write_text(source)
            save(trial/f'proposal_{attempt}.json',response)
            result=record(p,trial/f'evaluation_{attempt}',response['idea'],parent['id'])
            if result['status']=='completed':
                result['id']=trial.name;result['hypothesis']=response['hypothesis'];result['causality']=response['causality'];save(trial/'result.json',result)
                return result
            feedback=evaluation_feedback(response,result)
        except UsageStopped:raise
        except (ValueError,KeyError,json.JSONDecodeError) as err:
            feedback='\nPrevious proposal could not be applied: '+str(err)+'\nRepair from the ORIGINAL source. Previous response:\n'+json.dumps(response,ensure_ascii=False)[-15000:]
            event(dict(event='proposal_repair',trial=number,attempt=attempt,error=str(err)))
    bump('failed_proposals');save(trial/'failed.json',dict(feedback=feedback));return None

def update_status(rows,active):
    best=max(rows,key=lambda r:r['weighted_score']);balanced=[r for r in rows if r['balanced_gate']]
    save(ROOT/'best-public.json',best)
    if balanced:save(ROOT/'best-balanced.json',max(balanced,key=lambda r:r['weighted_score']))
    save(ROOT/'archive.json',rows)
    save(ROOT/'progress.json',dict(updated_at=time.time(),evaluated=len(rows),active=active,best_public_score=best['weighted_score'],best_public_id=best['id'],best_balanced_score=max((r['weighted_score'] for r in balanced),default=None),quota=json.loads((ROOT/'quota-usage.json').read_text()).get('min_remaining_percent'),counters=json.loads((ROOT/'counters.json').read_text())))

def choose(rows,number):
    if number%6==0:return next(r for r in rows if r['id']=='seed_standalone')
    if number%5==0:
        return max(rows,key=lambda r:next(c['weighted_score'] for c in r['cases'] if c['case']=='15'))
    if number%4==0:return max(rows,key=lambda r:r['fresh_mean_kpi'])
    if number%3==0:return max(rows,key=lambda r:next(c['weighted_score'] for c in r['cases'] if c['case']=='13'))
    top=sorted(rows,key=lambda r:r['weighted_score'],reverse=True)[:min(6,len(rows))]
    return random.Random(number*7391).choices(top,weights=[1/(i+1) for i in range(len(top))])[0]

def external_candidate(path):
    """Evaluate an independently authored proposal through the same strict gate."""
    v=json.loads(path.read_text());source=Path(v['source']).resolve()
    if not source.is_relative_to(ROOT) or digest(source)!=v['sha256']:raise ValueError('external source identity mismatch')
    # Apply the same source-state exclusions as model proposals.
    apply('//'+('x'*300)+'\nint main(){return 0;}',dict(full_source=source.read_text(),changes=[]))
    trial=ROOT/'evaluations'/('external_'+v['sha256'][:16])
    result=record(source,trial,v['idea'],v.get('parent'))
    if result.get('status')!='completed':
        bump('failed_proposals');save(path.with_suffix('.processed.json'),dict(status='invalid',result=result));return None
    result.update(hypothesis=v.get('hypothesis',''),causality=v.get('causality',''),origin='independent branch inbox');save(trial/'result.json',result)
    save(path.with_suffix('.processed.json'),dict(status='completed',id=result['id'],sha256=result['sha256']));return result

def main():
    lock=(ROOT/'.loop.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    env=subscription_environment();check_prerequisites(env);quota()
    policy=json.loads((ROOT/'manifest.json').read_text());policy.update(status='running',started_at=time.time());save(ROOT/'manifest.json',policy)
    pointer=REPO/'research-campaigns/active.json'
    if json.loads(pointer.read_text()).get('path')==str(ROOT):save(pointer,dict(path=str(ROOT),status='running',progress=str(ROOT/'progress.json')))
    if not (ROOT/'counters.json').exists():save(ROOT/'counters.json',dict(model_calls=0,failed_proposals=0,evaluated=0))
    save(ROOT/'response-schema.json',SCHEMA)
    rows=json.loads((ROOT/'archive.json').read_text()) if (ROOT/'archive.json').exists() else []
    completed_paths=[*sorted((ROOT/'proposals').glob('trial_*/result.json')),*sorted((ROOT/'evaluations').glob('external_*/result.json'))]
    for result_path in completed_paths:
        r=json.loads(result_path.read_text())
        if r.get('status')=='completed' and all(x['id']!=r['id'] for x in rows):
            if digest(r['source'])!=r['sha256']:raise RuntimeError('completed recovered candidate changed')
            rows.append(r)
    if not (ROOT/'baseline-fresh.json').exists():
        baseline=reuse_or_evaluate(ROOT/'seeds/baseline.cpp',ROOT/'fresh/dev',ROOT/'evaluations/baseline_fresh','baseline fresh')
        if not baseline.get('correct'):raise RuntimeError('fresh_baseline_invalid')
        save(ROOT/'baseline-fresh.json',summary(baseline))
    for name in ['baseline','public_best','dual_specialist','standalone']:
        if not any(r['id']=='seed_'+name for r in rows):
            source=ROOT/'seeds'/f'{name}.cpp';result_path=ROOT/'evaluations'/f'seed_{name}'/'result.json'
            if result_path.exists():
                result=json.loads(result_path.read_text())
                if result.get('sha256')!=digest(source):raise RuntimeError('saved seed changed')
                rows.append(result);update_status(rows,[]);continue
            result=record(source,ROOT/'evaluations'/f'seed_{name}',f'seed {name}')
            if result['status']!='completed':raise RuntimeError('invalid_seed_'+name)
            rows.append(result);update_status(rows,[])
    pool=futures.ThreadPoolExecutor(max_workers=2);pending={};number=1;infra=0;reason='unknown';queued_external=set()
    existing=[int(p.name.split('_')[1]) for p in (ROOT/'proposals').glob('trial_*') if p.is_dir()]
    if existing:number=max(existing)+1
    recoveries=[]
    for plan_path in sorted((ROOT/'proposals').glob('trial_*/plan.json')):
        trial=plan_path.parent
        if (trial/'result.json').exists() or (trial/'failed.json').exists():continue
        plan=json.loads(plan_path.read_text());parent=next((r for r in rows if r['id']==plan['parent']),None)
        if parent is not None:recoveries.append((plan['number'],parent))
    deadline=datetime.fromisoformat(policy['hard_deadline_local']).timestamp()
    try:
        while not stopping():
            quota();counts=json.loads((ROOT/'counters.json').read_text())
            if time.time()>=deadline:reason='evening_deadline';break
            if counts.get('evaluation_attempts',counts['evaluated'])>=policy['target_evaluated']:reason='evaluation_budget';break
            if counts['model_calls']>=policy['max_model_calls']:reason='model_budget';break
            if counts['failed_proposals']>=policy['max_failed_proposals']:reason='failed_proposal_budget';break
            while len(pending)<2 and not stopping():
                inbox=[]
                for item in sorted((ROOT/'candidate-inbox').glob('*.json')):
                    if item.name.endswith('.processed.json') or item in queued_external or item.with_suffix('.processed.json').exists():continue
                    try:v=json.loads(item.read_text())
                    except (OSError,json.JSONDecodeError):continue
                    if not isinstance(v,dict):
                        save(item.with_suffix('.processed.json'),dict(status='invalid_metadata'));continue
                    if any(r['sha256']==v.get('sha256') for r in rows):
                        save(item.with_suffix('.processed.json'),dict(status='duplicate'));continue
                    inbox.append(item)
                if inbox:
                    item=inbox[0];queued_external.add(item);task=pool.submit(external_candidate,item);pending[task]='inbox_'+item.stem
                    event(dict(event='independent_proposal_started',inbox=str(item)));continue
                if recoveries:
                    recovered_number,parent=recoveries.pop(0)
                    task=pool.submit(propose,recovered_number,parent,list(rows),True);pending[task]=recovered_number
                    event(dict(event='proposal_recovered',trial=recovered_number,parent=parent['id']));continue
                parent=choose(rows,number);snapshot=list(rows)
                task=pool.submit(propose,number,parent,snapshot);pending[task]=number
                event(dict(event='proposal_started',trial=number,parent=parent['id'],parent_score=parent['weighted_score']));number+=1
            update_status(rows,list(pending.values()))
            done,_=futures.wait(pending,timeout=5,return_when=futures.FIRST_COMPLETED)
            for task in done:
                num=pending.pop(task)
                try:
                    result=task.result();infra=0
                    if result is not None:
                        rows.append(result);event(dict(event='evaluated',trial=num,score=result['weighted_score'],fresh=result['fresh'],idea=result['idea']))
                    else:event(dict(event='proposal_exhausted',trial=num))
                except UsageStopped:raise
                except Exception as error:
                    infra+=1;event(dict(event='infrastructure_failure',trial=num,error=str(error),traceback=traceback.format_exc()[-5000:]));bump('failed_proposals')
                    if infra>=policy['consecutive_infrastructure_failures']:reason='repeated_infrastructure_failure';STOP.set()
            update_status(rows,list(pending.values()))
    except UsageStopped as error:reason='quota_or_stop: '+str(error)
    finally:
        STOP.set();pool.shutdown(wait=True,cancel_futures=True)
        # Preserve a candidate which finished just before the stop boundary.
        for task,num in pending.items():
            if task.done() and not task.cancelled():
                try:
                    r=task.result()
                    if r is not None and all(x['id']!=r['id'] for x in rows):rows.append(r)
                except Exception:pass
        update_status(rows,[])
        policy=json.loads((ROOT/'manifest.json').read_text());policy.update(status='completed' if reason in ['evening_deadline','evaluation_budget','model_budget'] else 'stopped',stop_reason=reason,finished_at=time.time());save(ROOT/'manifest.json',policy)
        if json.loads(pointer.read_text()).get('path')==str(ROOT):save(pointer,dict(path=str(ROOT),status=policy['status'],progress=str(ROOT/'progress.json')))
        event(dict(event='loop_finished',reason=reason,evaluated=len(rows),best=max(r['weighted_score'] for r in rows)))

if __name__=='__main__':
    signal.signal(signal.SIGTERM,lambda *_:STOP.set())
    try:main()
    except Exception:
        event(dict(event='fatal',traceback=traceback.format_exc()))
        p=json.loads((ROOT/'manifest.json').read_text());p.update(status='failed',finished_at=time.time());save(ROOT/'manifest.json',p);raise
