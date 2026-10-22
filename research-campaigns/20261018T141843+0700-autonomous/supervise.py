"""Own the search tree, enforce live subscription quota, and prevent idle sleep."""
import fcntl,json,os,signal,subprocess,sys,time,traceback
from datetime import datetime
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'shinka-pipes/search-v3-1'))
from usage_guard import gate

def save(path,v):
    p=ROOT/path;t=p.with_name(p.name+f'.super-{os.getpid()}.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)

def live(pid,created):
    try:
        p=psutil.Process(int(pid))
        if p.create_time()==created and p.is_running() and p.status()!=psutil.STATUS_ZOMBIE:return p
    except psutil.NoSuchProcess:pass

def interrupted(signum,frame):
    raise KeyboardInterrupt('supervisor interrupted')

def main():
    f=(ROOT/'.supervisor.lock').open('a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    policy=json.loads((ROOT/'manifest.json').read_text());gate(ROOT,min_remaining_percent=65,max_age_seconds=0)
    if (ROOT/'supervisor.json').exists():
        old=json.loads((ROOT/'supervisor.json').read_text())
        for pid,created in old.get('owned_processes',{}).items():
            if live(pid,created):raise RuntimeError('old owned process remains alive')
    log=(ROOT/'loop.log').open('a');child=subprocess.Popen([sys.executable,'-B',str(ROOT/'loop.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
    signal.signal(signal.SIGTERM,interrupted)
    awake=subprocess.Popen(['/usr/bin/caffeinate','-im','-w',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    known={child.pid:psutil.Process(child.pid).create_time(),awake.pid:psutil.Process(awake.pid).create_time()}
    state=dict(status='running',pid=os.getpid(),created_at=psutil.Process().create_time(),worker_pid=child.pid,worker_created_at=known[child.pid],caffeinate_pid=awake.pid,owned_processes=known,started_at=time.time(),cleanup_confirmed=False)
    save('supervisor.json',state);next_quota=0;reason=None;seen_registry={};observed_count=2
    deadline=datetime.fromisoformat(policy['hard_deadline_local']).timestamp()
    try:
        while child.poll() is None:
            for p in (ROOT/'processes').glob('*.json'):
                try:
                    stamp=p.stat().st_mtime_ns
                    if seen_registry.get(p.name)==stamp:continue
                    seen_registry[p.name]=stamp
                    r=json.loads(p.read_text())
                    if r.get('status')=='running':known[r['pid']]=r['created_at']
                except (ValueError,KeyError,FileNotFoundError):pass
            active={}
            for pid,created in list(known.items()):
                p=live(pid,created)
                if p:
                    active[pid]=created
                    try:
                        for sub in p.children(recursive=True):
                            if sub.pid not in known:observed_count+=1
                            active[sub.pid]=sub.create_time()
                    except psutil.NoSuchProcess:pass
            known=active
            if time.monotonic()>=next_quota:
                try:gate(ROOT,min_remaining_percent=65,max_age_seconds=0)
                except Exception as error:reason='quota_guard: '+str(error)
                next_quota=time.monotonic()+60
            if (ROOT/'night-stop-request.json').exists():reason=reason or json.loads((ROOT/'night-stop-request.json').read_text()).get('reason','requested_stop')
            if time.time()>deadline:reason='evening_deadline'
            state.update(updated_at=time.time(),owned_processes=known,observed_process_count=observed_count,stop_reason=reason);save('supervisor.json',state)
            if reason:
                save('night-stop-request.json',dict(reason=reason,immediate=True,requested_at=time.time()))
                break
            time.sleep(1)
        child.poll()
        reason=reason or ('worker_finished' if child.returncode==0 else 'worker_failed')
    except BaseException:
        reason='supervisor_exception';state['error']=traceback.format_exc();raise
    finally:
        owned=[]
        for pid,created in reversed(list(known.items())):
            p=live(pid,created)
            if p:
                try:p.terminate();owned.append(p)
                except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(owned,timeout=5)
        for p in alive:
            try:p.kill()
            except psutil.NoSuchProcess:pass
        psutil.wait_procs(alive,timeout=3)
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:pass
        remaining=[pid for pid,created in known.items() if live(pid,created)]
        state.update(status='finished' if not remaining else 'cleanup_unconfirmed',stop_reason=reason,finished_at=time.time(),worker_exit_code=child.poll(),owned_processes=known,remaining_owned_pids=remaining,cleanup_confirmed=not remaining);save('supervisor.json',state)
        manifest=json.loads((ROOT/'manifest.json').read_text())
        if manifest['status'] in ['preparing','running']:
            manifest.update(status='stopped',stop_reason=reason,finished_at=time.time());save('manifest.json',manifest)
        pointer=ROOT.parents[1]/'research-campaigns/active.json'
        if json.loads(pointer.read_text()).get('path')==str(ROOT):save(pointer,dict(path=str(ROOT),status=manifest['status'],progress=str(ROOT/'progress.json')))

if __name__=='__main__':main()
