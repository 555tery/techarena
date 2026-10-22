"""Quota watchdog for owned local evaluations in this campaign only."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import psutil

CAMPAIGN = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN.parents[1] / 'shinka-pipes/search-v3-1'))
from usage_guard import gate


def save(name, value):
    path = CAMPAIGN / name
    temporary = path.with_name(path.name + '.watchdog.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    known = {}
    next_check = 0
    reason = None
    while True:
        manifest = json.loads((CAMPAIGN / 'manifest.json').read_text())
        if manifest['status'] not in ['preparing', 'running']:
            break
        for path in (CAMPAIGN / 'processes').glob('*.json'):
            try:
                value = json.loads(path.read_text())
                if value['status'] == 'running':
                    known[value['pid']] = value['created_at']
            except (ValueError, KeyError, FileNotFoundError):
                continue
        active = {}
        for pid, created in known.items():
            try:
                proc = psutil.Process(pid)
                if proc.create_time() != created or not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                    continue
                active[pid] = created
                for child in proc.children(recursive=True):
                    active[child.pid] = child.create_time()
            except psutil.NoSuchProcess:
                pass
        known = active
        if time.monotonic() >= next_check:
            try:
                snapshot = gate(CAMPAIGN, min_remaining_percent=65, max_age_seconds=0)
            except Exception as error:
                reason = 'quota_guard: ' + str(error)
            next_check = time.monotonic() + 60
        if (CAMPAIGN / 'night-stop-request.json').exists():
            reason = reason or 'campaign_stop_request'
        save('watchdog-state.json', {'pid': os.getpid(), 'updated_at': time.time(),
            'owned_active_processes': known, 'stop_reason': reason})
        if reason:
            owned = []
            for pid, created in reversed(list(known.items())):
                try:
                    proc = psutil.Process(pid)
                    if proc.create_time() == created:
                        proc.terminate()
                        owned.append(proc)
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(owned, timeout=2)
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(alive, timeout=3)
            manifest = json.loads((CAMPAIGN / 'manifest.json').read_text())
            manifest.update(status='stopped', stop_reason=reason, stopped_at=time.time())
            save('manifest.json', manifest)
            break
        time.sleep(1)
    save('watchdog-exit.json', {'finished_at': time.time(), 'reason': reason or 'campaign_finished'})


if __name__ == '__main__':
    main()
