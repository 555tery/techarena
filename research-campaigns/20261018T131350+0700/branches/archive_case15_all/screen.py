from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,hashlib,threading,time
D=Path(__file__).resolve().parent;P=D.parents[1];ROOT=P.parents[1]
PYTHON=ROOT/'shinka-pipes/.venv/bin/python'
selection=json.loads((D/'selection-manifest.json').read_text())['selected']
stop=threading.Event(); started=time.time()

def run(row):
    if stop.is_set() or (P/'night-stop-request.json').exists():return dict(generation=row['generation'],status='not_started_stop')
    source=Path(row['campaign_source_path']);assert hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256']
    out=D/'evaluations'/f"gen_{row['generation']:03d}_{row['source_sha256'][:10]}"
    if out.exists():raise RuntimeError(f'refuse existing output {out}')
    command=[str(PYTHON),'-B',str(P/'evaluate.py'),'--source',str(source),'--tests',str(ROOT/'data/pipes/open/15.in'),'--out',str(out),'--label',f"archive15-gen-{row['generation']}"]
    child=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (D/'logs').mkdir(exist_ok=True)
    (D/'logs'/f"gen_{row['generation']}.txt").write_text(child.stdout+child.stderr)
    result={k:row[k] for k in ['generation','source_sha256','campaign_source_path','base_hypothesis','synthetic_score']}
    result.update(returncode=child.returncode,out=str(out))
    manifest=out/'manifest.json';summary=out/'harness/summary.json'
    if manifest.exists():result.update(status=json.loads(manifest.read_text()).get('status'))
    if summary.exists():
        s=json.loads(summary.read_text());assert s['case_count']==1 and s['records'][0]['case']=='15'
        r=s['records'][0];result.update(correct=s['ok_count']==1,trench=r.get('trench_length_m'),score=r.get('weighted_score'),cpu_s=r.get('solver_cpu_total_s'),rss_mib=r.get('solver_peak_rss_mb'))
    if (P/'night-stop-request.json').exists():stop.set()
    return result

results=[]
with ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,row) for row in selection]
    for future in as_completed(futures):
        try:r=future.result()
        except Exception as exc:r=dict(status='driver_error',error=repr(exc));stop.set()
        results.append(r)
        with (D/'results.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
        valid=[r for r in results if r.get('correct')]
        progress=dict(completed=len(results),selected=len(selection),correct=len(valid),best_trench=min((r['trench'] for r in valid),default=None),stopped=stop.is_set())
        (D/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
        if len(results)%10==0:print(json.dumps(progress),flush=True)
valid=sorted([r for r in results if r.get('correct')],key=lambda r:r['trench'])
report=dict(selected=len(selection),completed=len(results),valid=len(valid),stopped=stop.is_set(),elapsed_s=time.time()-started,root_baseline_T=438640,root_composite_T=438620,beats_baseline=sum(r['trench']<438640 for r in valid),beats_composite=sum(r['trench']<438620 for r in valid),top3=valid[:3],results=results)
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n')
brief={k:v for k,v in report.items() if k not in ['results','top3']}
brief['top3']=[{k:r[k] for k in ['generation','source_sha256','trench','score','cpu_s','rss_mib']} for r in valid[:3]]
print(json.dumps(brief),flush=True)
