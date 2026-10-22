"""Read this exact autonomous campaign; optional scoped stop request."""
import argparse,json,time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stop-reason');a=ap.parse_args()
    if a.stop_reason:
        p=ROOT/'night-stop-request.json';t=p.with_suffix('.monitor.tmp');t.write_text(json.dumps(dict(reason=a.stop_reason,immediate=True,requested_at=time.time()))+'\n');t.replace(p)
    output={}
    for name in ['manifest','progress','supervisor','best-public','best-balanced','quota-usage']:
        p=ROOT/(name+'.json')
        if p.exists():
            v=json.loads(p.read_text())
            if name.startswith('best-'):
                v={k:v[k] for k in ['id','source','sha256','weighted_score','fresh','balanced_gate']}
                v['fresh']={k:x for k,x in v['fresh'].items() if k!='worst_cases'}
            if name=='progress':v['counters']={k:x for k,x in v.get('counters',{}).items() if k!='evaluation_reservations'}
            if name=='supervisor':
                alive=[]
                for pid,created in v.get('owned_processes',{}).items():
                    try:
                        proc=psutil.Process(int(pid))
                        if proc.create_time()==created and proc.is_running() and proc.status()!=psutil.STATUS_ZOMBIE:alive.append(dict(pid=int(pid),name=proc.name(),created_at=created))
                    except psutil.NoSuchProcess:pass
                v={k:v.get(k) for k in ['status','pid','worker_pid','updated_at','stop_reason','cleanup_confirmed','worker_exit_code']};v['verified_live_owned_processes']=alive
            output[name]=v
    print(json.dumps(output,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
