from pathlib import Path
import hashlib, json, random, subprocess, time

REPO = Path(__file__).resolve().parents[4]
CONT = REPO / 'prototypes/pipes_open15_overfit_20261019/continuation'
ROOT = CONT / 'case5_9'
BIN = CONT / 'conditioned'
DATA = REPO / 'data/pipes/open'
TARGET = {5: 53360, 9: 47500}
PREFIX = 125
WORK = ROOT / 'work'
WORK.mkdir(exist_ok=True)

def read_case(k):
    toks=(DATA/f'{k}.in').read_text().split(); n=int(toks[1]); cmd=list(map(int,toks[2:2+n]))
    size=[0]; pidat=[0]*n; death=[n]
    for t,c in enumerate(cmd):
        if c>0: pidat[t]=len(size); size.append(c); death.append(n)
        else: death[-c]=t
    return cmd,size,pidat,death

CASES={k:read_case(k) for k in (5,9)}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def order_from_plan(k, mode):
    p=list(map(int,(CONT.parent/'future'/str(mode)/f'{k}.txt').read_text().split()))
    assert len(p)==len(CASES[k][1])-1
    return tuple(i+1 for _,i in sorted((p[i],i) for i in range(PREFIX)))

layouts={}
def add_layout(name, order):
    order=tuple(order)
    if len(order)!=PREFIX or len(set(order))!=PREFIX: return
    layouts.setdefault(order,[]).append(name)

# Preserve the relative prefix geometry represented by each raw offline plan.
raw_orders={}
for k in (5,9):
    for m in range(5):
        o=order_from_plan(k,m); raw_orders[(k,m)]=o; add_layout(f'raw{k}_mode{m}',o)
# Consensus rank layouts between every pair of raw plans.
rank={key:{pid:r for r,pid in enumerate(o)} for key,o in raw_orders.items()}
for (k1,m1),r1 in rank.items():
    if k1!=5: continue
    for (k2,m2),r2 in rank.items():
        if k2!=9: continue
        for direction, keyfn in (
            ('mean',lambda pid:(r1[pid]+r2[pid], max(r1[pid],r2[pid]),pid)),
            ('max',lambda pid:(max(r1[pid],r2[pid]), r1[pid]+r2[pid],pid)),
            ('min',lambda pid:(min(r1[pid],r2[pid]), r1[pid]+r2[pid],pid)),
        ):
            add_layout(f'consensus_{k1}{m1}_{k2}{m2}_{direction}', sorted(range(1,PREFIX+1),key=keyfn))
# Lifetime rank orders, using both streams jointly.
d5=CASES[5][3]; d9=CASES[9][3]; n5=len(CASES[5][0]); n9=len(CASES[9][0])
def normalized(d,n,pid): return d[pid]/n
keys={
 'sum_early':lambda pid:(normalized(d5,n5,pid)+normalized(d9,n9,pid),pid),
 'sum_late':lambda pid:(-(normalized(d5,n5,pid)+normalized(d9,n9,pid)),pid),
 'max_early':lambda pid:(max(normalized(d5,n5,pid),normalized(d9,n9,pid)),pid),
 'max_late':lambda pid:(-max(normalized(d5,n5,pid),normalized(d9,n9,pid)),pid),
 'min_early':lambda pid:(min(normalized(d5,n5,pid),normalized(d9,n9,pid)),pid),
 'min_late':lambda pid:(-min(normalized(d5,n5,pid),normalized(d9,n9,pid)),pid),
 'case5_early_case9_late':lambda pid:(normalized(d5,n5,pid),-normalized(d9,n9,pid),pid),
 'case9_early_case5_late':lambda pid:(normalized(d9,n9,pid),-normalized(d5,n5,pid),pid),
 'same_survivors_first':lambda pid:(-(d5[pid]==n5)-(d9[pid]==n9),normalized(d5,n5,pid)+normalized(d9,n9,pid),pid),
 'same_survivors_last':lambda pid:((d5[pid]==n5)+(d9[pid]==n9),normalized(d5,n5,pid)+normalized(d9,n9,pid),pid),
}
for name,key in keys.items(): add_layout('life_'+name,sorted(range(1,PREFIX+1),key=key))

# Bounded neighborhood search around the evidence-derived orders, plus a small
# global random sample. Mutations retain most of a useful prefix ordering.
rng=random.Random(20261019)
seed_orders=list(layouts)
for q in range(160):
    order=list(rng.choice(seed_orders))
    for _ in range(1+rng.randrange(8)):
        a,b=rng.sample(range(PREFIX),2); order[a],order[b]=order[b],order[a]
    if q%3==0:
        a,b=sorted(rng.sample(range(PREFIX),2)); order[a:b+1]=reversed(order[a:b+1])
    add_layout(f'mut_{q}',order)
for q in range(80):
    order=list(range(1,PREFIX+1)); rng.shuffle(order)
    add_layout(f'random_{q}',order)

# Each ordering is compacted to 0..124. Move PID 1 to a chosen low address by
# swapping with that address's owner, preserving a permutation of the prefix block.
def pins_for(order, pid1_address):
    p=[-1]*PREFIX
    for address,pid in enumerate(order): p[pid-1]=address
    assert sorted(p)==list(range(PREFIX))
    owner=p.index(pid1_address)
    p[0],p[owner]=p[owner],p[0]
    assert p[0]==pid1_address and len(set(p))==PREFIX
    return p

def adjust_pid1(pins,pid1_address):
    p=list(pins)
    if pid1_address in p:
        owner=p.index(pid1_address); p[0],p[owner]=p[owner],p[0]
    else:
        p[0]=pid1_address
    assert p[0]==pid1_address and len(set(p))==PREFIX
    return p

def run(k,pins,mode,dest):
    pinfile=WORK/'pins.txt'; pinfile.write_text('\n'.join(map(str,pins))+'\n')
    cmd=[str(BIN),str(DATA/f'{k}.in'),str(pinfile),str(PREFIX),str(dest),str(mode)]
    r=subprocess.run(cmd,cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
    if r.returncode: return None,r.stdout.strip()
    try: t=int(r.stdout.strip().splitlines()[-1])
    except Exception: return None,r.stdout.strip()
    return t,r.stdout.strip()

def score(ts):
    a=max(0,ts[5]-TARGET[5]); b=max(0,ts[9]-TARGET[9])
    return (a+b,max(a,b),a,b)

# Screen compact and exact raw-prefix layouts, with a bounded set of compact
# breaks that leave small reusable holes in the first-125 address block.
candidates={}; evaluations=0; started=time.monotonic(); bestscreen=None
def screen_pins(pins,name,x):
    global evaluations,bestscreen
    key=tuple(pins)
    if key in candidates: return
    t5,log5=run(5,pins,0,WORK/'cand5.txt'); evaluations+=1
    t9,log9=run(9,pins,0,WORK/'cand9.txt'); evaluations+=1
    if t5 is None or t9 is None: return
    row={'pins':pins,'sources':[name],'pid1':x,'mode0':{5:t5,9:t9},'mode0_score':score({5:t5,9:t9})}
    candidates[key]=row
    if bestscreen is None or row['mode0_score']<bestscreen['mode0_score']:
        bestscreen=row
        print('screen_best',json.dumps({'evals':evaluations,'pid1':x,'T5':t5,'T9':t9,'score':row['mode0_score'],'source':name}),flush=True)
    if evaluations%200==0: print('progress',evaluations,'unique',len(candidates),'elapsed',round(time.monotonic()-started,1),flush=True)

for order,names in layouts.items():
    xs=range(20) if any(name.startswith(('raw','consensus','life')) for name in names) else (0,5,10,15,19)
    for x in xs: screen_pins(pins_for(order,x),names[0],x)

# Preserve exact (possibly spaced) raw prefixes as separate hypotheses.
for k in (5,9):
    for m in range(5):
        raw=list(map(int,(CONT.parent/'future'/str(m)/f'{k}.txt').read_text().split()))[:PREFIX]
        for x in (0,5,10,15,19): screen_pins(adjust_pid1(raw,x),f'exact_raw{k}_mode{m}',x)

# Five insertion points and three small gaps test whether compact breaks help
# the two traces share useful temporary space.
for order in seed_orders:
    for cut in (20,40,62,80,104):
        for gap in (1,5,10):
            spaced=[]
            for rank0,pid in enumerate(order): spaced.append((pid,rank0+(gap if rank0>=cut else 0)))
            base=[-1]*PREFIX
            for pid,address in spaced: base[pid-1]=address
            for x in (0,5,10,15,19): screen_pins(adjust_pid1(base,x),f'gap_cut{cut}_size{gap}',x)

ranked=sorted(candidates.values(),key=lambda r:(r['mode0_score'],r['pid1'],r['pins']))
# Include a few candidates from each source family and expand mode choice.
selected=[]; seen=set()
for r in ranked:
    key=tuple(r['pins'])
    if key not in seen: selected.append(r);seen.add(key)
    if len(selected)>=24: break
# Preserve the previous best as an explicit candidate during a resumed run.
prior_report=ROOT/'search-report.json'
best=None
if prior_report.exists() and (ROOT/'pins.txt').exists():
    prior=json.loads(prior_report.read_text())['best']
    prior['T']={int(k):v for k,v in prior['T'].items()}
    prior['modes']={int(k):v for k,v in prior['modes'].items()}
    prior['score']=score(prior['T'])
    prior['pins']=list(map(int,(ROOT/'pins.txt').read_text().split()))
    best=prior
    if tuple(prior['pins']) not in seen:
        selected.append({'pins':prior['pins'],'sources':prior.get('sources',['previous_best']),'pid1':prior['pins'][0],'mode0_score':prior['score']})
for idx,r in enumerate(selected):
    per_case={}
    for k in (5,9):
        trials=[]
        for m in range(4):
            t,log=run(k,r['pins'],m,WORK/f'cand{k}.txt'); evaluations+=1
            if t is not None: trials.append((t,m))
        if not trials: break
        per_case[k]=min(trials)
    if len(per_case)!=2: continue
    row={'pins':r['pins'],'sources':r['sources'],'pid1':r['pid1'],'modes':{k:v[1] for k,v in per_case.items()},'T':{k:v[0] for k,v in per_case.items()}}
    row['score']=score(row['T'])
    if best is None or row['score']<best['score']:
        best=row
        (ROOT/'pins.txt').write_text('\n'.join(map(str,row['pins']))+'\n')
        # Recreate and save the selected plan for each case/mode.
        for k in (5,9):
            t,log=run(k,row['pins'],row['modes'][k],ROOT/f'case{k}_positions.txt')
            assert t==row['T'][k]
        print('full_best',json.dumps({'evals':evaluations,'T':row['T'],'modes':row['modes'],'pid1':row['pid1'],'score':row['score'],'sources':row['sources'][:4]}),flush=True)
    if row['score']==(0,0,0,0): break

if best is None: raise SystemExit('no conditioned candidate')
report={'scope':'offline joint Open5/Open9 plans with shared 125-command prefix; uses known future deletions','targets':TARGET,'prefix':{'commands':PREFIX,'allocations':PREFIX,'all_sizes':1,'pid1_address':best['pid1'],'shared_positions':best['pins']},'best':best,'screen':{'unique_pin_layouts':len(candidates),'layouts':len(layouts),'pid1_addresses_tested':'0..19 for raw/consensus/lifetime orders; 0,5,10,15,19 for mutations/random','mode0_evaluations':len(candidates)*2,'top_full_mode_candidates':len(selected),'total_binary_runs':evaluations,'elapsed_seconds':round(time.monotonic()-started,3)},'sha256':{'conditioned_cpp':hashlib.sha256((CONT/'conditioned.cpp').read_bytes()).hexdigest(),'conditioned_binary':sha(BIN),'input5':sha(DATA/'5.in'),'input9':sha(DATA/'9.in'),'positions5':sha(ROOT/'case5_positions.txt'),'positions9':sha(ROOT/'case9_positions.txt'),'pins':sha(ROOT/'pins.txt')}}
(ROOT/'search-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('done',json.dumps({'best':best,'report':str(ROOT/'search-report.json'),'evaluations':evaluations}),flush=True)
