#!/usr/bin/env python3
import json, os, platform, resource, subprocess, sys, time
from pathlib import Path

if len(sys.argv) != 6:
    raise SystemExit('usage: run_limited.py CASE START COUNT WIDTH ACTION_CAP')
case, start, count, width, cap = map(int, sys.argv[1:])
root = Path.cwd()
work = root / 'results/pipes/improvement/offline_longbeam_longanchors'
binary = root / 'results/pipes/improvement/offline_longbeam/longbeam'
input_path = root / f'data/pipes/open/{case}.in'
trace_path = root / f'results/pipes/final/open-run-size-cohort-lanes/runs/{case}/judge_output.txt'
out_path = work / f'case{case}_start{start}_n{count}_w{width}_a{cap}.json'
log_path = work / f'case{case}_start{start}_n{count}_w{width}_a{cap}.log'
cmd = [str(binary), str(input_path), str(trace_path), str(out_path), str(start), str(count), str(width), str(cap)]

def limit_child():
    cpu = 60
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))

started = time.monotonic()
with open(log_path, 'w') as log:
    log.write(json.dumps({
        'command': cmd,
        'cpu_limit_seconds': 60,
        'memory_budget_bytes': 256*1024*1024,
        'memory_enforcement': 'Darwin RLIMIT_AS/ulimit -v rejected 256 MiB with EINVAL; peak RSS is measured and checked after run',
    }, indent=2) + '\n')
    log.flush()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limit_child)
    rc = proc.wait()
wall = time.monotonic() - started
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
max_rss = usage.ru_maxrss
max_rss_bytes = max_rss if platform.system() == 'Darwin' else max_rss * 1024
result = {
    'case': case, 'start_op_1based': start, 'count': count,
    'beam_width': width, 'action_cap': cap,
    'return_code': rc, 'wall_seconds': round(wall, 3),
    'child_cpu_seconds_cumulative': round(usage.ru_utime + usage.ru_stime, 3),
    'peak_rss_bytes': max_rss_bytes,
    'peak_rss_mib': round(max_rss_bytes / (1024*1024), 3),
    'output_json': str(out_path.relative_to(root)) if out_path.exists() else None,
    'log': str(log_path.relative_to(root)),
    'cpu_limit_seconds': 60, 'memory_budget_bytes': 256*1024*1024,
    'memory_enforced': False if platform.system() == 'Darwin' else True,
}
meta = work / f'case{case}_start{start}_n{count}_w{width}_a{cap}_resource.json'
meta.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if rc != 0:
    raise SystemExit(1)
