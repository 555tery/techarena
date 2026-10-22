#!/usr/bin/env python3
"""Small fixed prequential check of neighbor-deletion features; no policy code."""
from __future__ import annotations
import bisect, hashlib, json, math, random, subprocess, time
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/555tery/techarena')
OUT = ROOT/'results/pipes/improvement/coalescence_neighbor_hazard'
BIN = ROOT/'results/pipes/final/bin/solution'
SPECS = [
    ('lifo_uniform_seed94101','lifo','uniform',94101),
    ('fifo_uniform_seed94102','fifo','uniform',94102),
    ('random_bimodal_seed94103','random','bimodal',94103),
    ('phase_lifo_fifo_random_seed94104','phase','bimodal',94104),
]
N = 10000

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def draw(rng, profile):
    if profile == 'uniform': return rng.randint(1,40)
    if profile == 'bimodal': return rng.randint(1,5) if rng.random()<.5 else rng.randint(30,40)
    raise ValueError(profile)

def stream(policy, profile, seed):
    rng=random.Random(seed); active={}; cmds=[]; pid=0
    for op in range(1,N+1):
        place = True if len(active)<80 else False if len(active)>500 else rng.random()<.5
        if place:
            pid+=1; L=draw(rng,profile); active[pid]=L; cmds.append(L)
        else:
            mode=policy
            if mode=='phase': mode=('lifo','fifo','random')[(op//2500)%3]
            ids=list(active)
            d=max(ids) if mode=='lifo' else min(ids) if mode=='fifo' else rng.choice(ids)
            cmds.append(-d); del active[d]
    return cmds

def bins(L,age,rank_frac):
    lb='1-4' if L<=4 else '5-12' if L<=12 else '13-24' if L<=24 else '25-40'
    ab='0-1' if age<=1 else '2-4' if age<=4 else '5-16' if age<=16 else '17-64' if age<=64 else '65+'
    rb='newest5' if rank_frac<.05 else 'newest25' if rank_frac<.25 else 'middle' if rank_frac<.75 else 'oldest25' if rank_frac<.95 else 'oldest5'
    return lb,ab,rb

def extract(name, cmds, existing_answer=None):
    if existing_answer is None:
        inp='\n'.join(map(str,cmds+[0]))+'\n'
        t=time.perf_counter(); p=subprocess.run([str(BIN)],input=inp,text=True,capture_output=True,check=True); wall=time.perf_counter()-t
        answers=p.stdout.splitlines(); assert len(answers)==len(cmds),(name,len(answers),len(cmds))
        (OUT/'synthetic'/f'{name}.commands').write_text(inp)
        (OUT/'synthetic'/f'{name}.answer.txt').write_text(p.stdout)
    else:
        answers=Path(existing_answer).read_text().splitlines(); wall=None
        assert len(answers)==len(cmds),(name,len(answers),len(cmds))
    n=len(cmds); nxt=[n+1]*(n+1); nextpos=n+1
    for op in range(n,0,-1):
        nxt[op]=nextpos
        if cmds[op-1]>0: nextpos=op
    dels_before={}
    for op,c in enumerate(cmds,1):
        if c>0 and nxt[op]<=n:
            dels_before[op]={-cmds[j-1] for j in range(op+1,nxt[op]) if cmds[j-1]<0}
    active={}; by_start={}; by_end={}; starts=[]; rows=[]; del_hist=[]; placement=0; pid=0; trench=0
    # Only active PID count/rank is needed; this Fenwick avoids scanning all pipes.
    fw=[0]*(200002)
    def add(i,d):
        while i<len(fw): fw[i]+=d; i+=i&-i
    def pref(i):
        s=0
        while i: s+=fw[i]; i-=i&-i
        return s
    for op,(c,line) in enumerate(zip(cmds,answers),1):
        tok=line.split()
        if c>0:
            digs,start=map(int,tok); trench+=20*digs
            targets=[]
            if start in by_end: targets.append(by_end[start])
            if start+c in by_start and by_start[start+c] not in targets: targets.append(by_start[start+c])
            np=nxt[op]
            for target_pid in targets:
                x=active[target_pid]; newer=len(active)-pref(target_pid)
                rank=newer/max(1,len(active)-1); age=op-x['birth']
                lb,ab,rb=bins(x['L'],age,rank)
                recent=del_hist[-8:]
                mean=sum(q['rank'] for q in recent)/len(recent) if recent else None
                mode='none' if mean is None else 'lifo_like' if mean<=.10 else 'fifo_like' if mean>=.90 else 'mixed'
                rows.append({'stream':name,'op':op,'pid':target_pid,'L':x['L'],'age':age,'rank':rank,
                    'lb':lb,'ab':ab,'rb':rb,'mode':mode,'active':len(active),'resolve':np,
                    'label':int(target_pid in dels_before.get(op,set()))})
            # Validate local non-overlap via ordered starts.
            ix=bisect.bisect_left(starts,start)
            if ix and active[by_start[starts[ix-1]]]['start']+active[by_start[starts[ix-1]]]['L']>start: raise RuntimeError(f'{name}: overlap')
            if ix<len(starts) and start+c>starts[ix]: raise RuntimeError(f'{name}: overlap')
            pid+=1; placement+=1
            active[pid]={'start':start,'L':c,'birth':op}; starts.insert(ix,start); by_start[start]=pid; by_end[start+c]=pid; add(pid,1)
        elif c<0:
            start=int(tok[0]); q=-c; x=active[q]
            if x['start']!=start: raise RuntimeError(f'{name}: invalid deletion at {op}')
            newer=len(active)-pref(q); rank=newer/max(1,len(active)-1)
            del_hist.append({'rank':rank,'age':op-x['birth']})
            starts.pop(bisect.bisect_left(starts,start)); by_start.pop(start); by_end.pop(start+x['L']); active.pop(q); add(q,-1)
        else: raise ValueError('zero terminator')
    return rows,{'name':name,'operations':n,'neighbor_samples':len(rows),'final_trench_m':trench,'wall_seconds':wall}

def metrics(rows,nops):
    at=defaultdict(list); resolve=defaultdict(list)
    for r in rows:
        if r['resolve']<=nops: at[r['op']].append(r); resolve[r['resolve']].append(r)
    gn=gy=0; ind=defaultdict(lambda:[0,0]); ctx=defaultdict(lambda:[0,0]); scored=[]
    for op in range(1,nops+1):
        for old in resolve[op]:
            y=old['label']; k=(old['lb'],old['ab']); ck=k+(old['rb'],old['mode'])
            gn+=1; gy+=y; ind[k][0]+=1; ind[k][1]+=y; ctx[ck][0]+=1; ctx[ck][1]+=y
        pg=(gy+1)/(gn+2)
        for r in at[op]:
            k=(r['lb'],r['ab']); ck=k+(r['rb'],r['mode'])
            ni,yi=ind[k]; nc,yc=ctx[ck]
            pi=(yi+20*pg)/(ni+20); pc=(yc+20*pi)/(nc+20)
            scored.append((r['label'],pg,pi,pc))
    out={}
    for name,j in [('global',1),('length_age',2),('rank_recent',3)]:
        n=len(scored); ys=[x[0] for x in scored]; ps=[max(1e-6,min(1-1e-6,x[j])) for x in scored]
        out[name]={'n':n,'positive_rate':sum(ys)/n if n else None,
            'brier':sum((p-y)**2 for p,y in zip(ps,ys))/n if n else None,
            'logloss':-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in zip(ps,ys))/n if n else None}
    return out

def forecast_after_history(rows,target,cutoff):
    resolved=defaultdict(list)
    for r in rows:
        if r['resolve']<=cutoff and r['op']<target['op']:
            resolved[r['resolve']].append(r)
    gn=gy=0; ind=defaultdict(lambda:[0,0]); ctx=defaultdict(lambda:[0,0])
    for op in range(1,cutoff+1):
        for old in resolved[op]:
            y=old['label']; k=(old['lb'],old['ab']); ck=k+(old['rb'],old['mode'])
            gn+=1; gy+=y; ind[k][0]+=1; ind[k][1]+=y; ctx[ck][0]+=1; ctx[ck][1]+=y
    pg=(gy+1)/(gn+2); k=(target['lb'],target['ab']); ck=k+(target['rb'],target['mode'])
    ni,yi=ind[k]; nc,yc=ctx[ck]; pi=(yi+20*pg)/(ni+20); pc=(yc+20*pi)/(nc+20)
    return {'resolved_training_samples':gn,'p_global':pg,'p_length_age':pi,'p_rank_recent':pc,
            'label_after_resolution':target['label']}

def main():
    syn_dir=OUT/'synthetic'; syn_dir.mkdir(exist_ok=True)
    allres=[]; allrows=[]
    raw=(ROOT/'data/pipes/open/15.in').read_text().split(); n=int(raw[1]); c15=list(map(int,raw[2:2+n]))
    rows,meta=extract('case15',c15,OUT/'case15.baseline_answer.txt'); allrows+=rows; allres.append({**meta,'metrics':metrics(rows,len(c15))})
    case_event=[r for r in rows if r['op']==100146 and r['pid']==80252]
    if len(case_event)!=1: raise RuntimeError(f'event rows={len(case_event)}')
    for name,pol,prof,seed in SPECS:
        c=stream(pol,prof,seed); r,m=extract(name,c); allrows+=r; allres.append({**m,'policy':pol,'profile':prof,'seed':seed,'metrics':metrics(r,len(c))})
    # Specific event prediction only from rows resolved before op 100146.
    prior=[r for r in rows if r['resolve']<=100146]
    mini=metrics(prior,100146)
    out={'design':{'synthetic_streams':SPECS,'operations_each':N,'no_parameter_tuning':True},
      'case15_window_C_neighbor_event':case_event[0],
      'case15_window_C_prequential_forecast':forecast_after_history(rows,case_event[0],100146),
      'case15_pre_event_resolved_row_metrics':mini,
      'per_stream':allres,'hashes':{'frozen_source':sha(ROOT/'results/pipes/final/solution.cpp'),
        'canonical_source':sha(ROOT/'src/pipes.cpp'),'frozen_binary':sha(BIN),
        'case15_input':sha(ROOT/'data/pipes/open/15.in'),'case15_answer':sha(OUT/'case15.baseline_answer.txt')},
      'interpretation':'Rank/context model is causal and prequential, but aggregate lift across streams is exploratory only; synthetic policy labels are known to the generator and do not establish robustness.'}
    (OUT/'rank_lift_quickcheck.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__': main()
