from pathlib import Path
import hashlib, json, itertools, subprocess, time
REPO=Path(__file__).resolve().parents[4]
CONT=REPO/'prototypes/pipes_open15_overfit_20261019/continuation'
ROOT=CONT/'case5_9'; WORK=ROOT/'work'; BIN=CONT/'conditioned'; DATA=REPO/'data/pipes/open'
PREFIX=125; TARGET={5:53360,9:47500}
base=list(map(int,(ROOT/'pins.txt').read_text().split()))
assert len(base)==PREFIX and base[0]==0 and len(set(base))==PREFIX
pinfile=WORK/'pins.txt'; start=time.monotonic(); runs=0; hits=[]

def invoke(k,pins,mode=0,dest='/dev/null'):
    pinfile.write_text('\n'.join(map(str,pins))+'\n')
    r=subprocess.run([str(BIN),str(DATA/f'{k}.in'),str(pinfile),str(PREFIX),str(dest),str(mode)],cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
    if r.returncode: return None
    try:return int(r.stdout.strip().splitlines()[-1])
    except:return None

base9=invoke(9,base); runs+=1
print('baseline_T9',base9,flush=True)
if base9 is None: raise SystemExit('baseline failed')
# Exhaust every one-swap permutation of prefix addresses other than PID1.
for count,(i,j) in enumerate(itertools.combinations(range(1,PREFIX),2),1):
    p=base.copy();p[i],p[j]=p[j],p[i]
    t9=invoke(9,p);runs+=1
    if t9 is None: continue
    if t9<=TARGET[9]:
        t5=invoke(5,p);runs+=1
        if t5 is not None and t5<=TARGET[5]:
            modes={}; values={}
            for k in (5,9):
                vals=[]
                for m in range(4):
                    t=invoke(k,p,m);runs+=1
                    if t is not None: vals.append((t,m))
                if not vals: break
                values[k],modes[k]=min(vals)
            if len(values)==2 and values[5]<=TARGET[5] and values[9]<=TARGET[9]:
                hits.append({'i':i+1,'j':j+1,'pins':p,'T':values,'modes':modes})
                print('target_hit',json.dumps({'i':i+1,'j':j+1,'T':values,'modes':modes}),flush=True)
                # Save the first fully verified-target candidate; continue scanning
                # for the same bound is unnecessary once both volume limits are met.
                (ROOT/'pins.txt').write_text('\n'.join(map(str,p))+'\n')
                for k in (5,9):
                    t=invoke(k,p,modes[k],ROOT/f'case{k}_positions.txt')
                    assert t==values[k]
                break
    if count%1000==0: print('progress',count,'runs',runs,'elapsed_s',round(time.monotonic()-start,1),flush=True)

report_path=ROOT/'search-report.json'
report=json.loads(report_path.read_text())
report['one_swap_refinement']={'baseline_T9':base9,'swaps_tested':count if 'count' in locals() else 0,'binary_runs':runs,'target_hits':len(hits),'elapsed_seconds':round(time.monotonic()-start,3),'status':'target found' if hits else 'no target found by one-swap mode0 screen'}
if hits:
    h=hits[0]
    report['best']={'pins':h['pins'],'pid1':h['pins'][0],'modes':h['modes'],'T':h['T'],'score':[0,0,0,0],'sources':['one_swap_from_mode0_best']}
    report['prefix']['shared_positions']=h['pins']
    report['sha256']['pins']=hashlib.sha256((ROOT/'pins.txt').read_bytes()).hexdigest()
    for k in (5,9): report['sha256'][f'positions{k}']=hashlib.sha256((ROOT/f'case{k}_positions.txt').read_bytes()).hexdigest()
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('done',json.dumps(report['one_swap_refinement']),flush=True)
