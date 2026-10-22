"""Native Windows, single-core, direct interactive protocol + CPU/commit metrics.

Uses Python standard library only. It is not the official C++ interactor.
Never treats wall time as CPU time and never divides CPU time by logical CPUs.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading
import time

def parse_test(path):
    raw=path.read_text(encoding='ascii').split();weight=float(raw[0]);n=int(raw[1])
    commands=list(map(int,raw[2:]))
    if len(commands)==n+1 and commands[-1]==0:commands.pop()
    assert len(commands)==n and 0<n<=200000
    return weight,commands

def run(solver,path,repeat,timeout):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    class FT(ctypes.Structure):_fields_=[('low',wintypes.DWORD),('high',wintypes.DWORD)]
    class Mem(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(x,ctypes.c_size_t) for x in
          ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(FT)]*4)];kernel.GetProcessTimes.restype=wintypes.BOOL
    kernel.GetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];kernel.GetProcessAffinityMask.restype=wintypes.BOOL
    kernel.SetProcessAffinityMask.argtypes=[wintypes.HANDLE,ctypes.c_size_t];kernel.SetProcessAffinityMask.restype=wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Mem),wintypes.DWORD];psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    weight,commands=parse_test(path);started=time.monotonic()
    proc=subprocess.Popen([str(solver)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    handle=wintypes.HANDLE(int(proc._handle));affinity=ctypes.c_size_t();system=ctypes.c_size_t()
    def checked(ok):
        if not ok:raise ctypes.WinError(ctypes.get_last_error())
    def cpu():
        a,b,k,u=FT(),FT(),FT(),FT();checked(kernel.GetProcessTimes(handle,ctypes.byref(a),ctypes.byref(b),ctypes.byref(k),ctypes.byref(u)))
        ticks=lambda x:(x.high<<32)|x.low
        return (ticks(k)+ticks(u))*1e-7
    def memory():
        m=Mem();m.cb=ctypes.sizeof(Mem);checked(psapi.GetProcessMemoryInfo(handle,ctypes.byref(m),m.cb))
        return {'peak_working_set_MiB':m.PeakWorkingSetSize/1048576,'peak_private_commit_MiB':m.PeakPagefileUsage/1048576}
    try:
        checked(kernel.GetProcessAffinityMask(handle,ctypes.byref(affinity),ctypes.byref(system)))
        one_core=affinity.value&-affinity.value;checked(kernel.SetProcessAffinityMask(handle,one_core))
        output=queue.Queue();errors=[]
        def read_lines():
            for line in iter(proc.stdout.readline,b''):output.put(line)
            output.put(None)
        threading.Thread(target=read_lines,daemon=True).start()
        thread=threading.Thread(target=lambda:errors.append(proc.stderr.read()),daemon=True);thread.start()
        T=F=peak=0;cells=bytearray();pipes=[None]
        for command in commands:
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise TimeoutError('wall watchdog; reported separately from CPU')
            proc.stdin.write((str(command)+'\n').encode('ascii'));proc.stdin.flush()
            line=output.get(timeout=remaining)
            if line is None:raise RuntimeError('solver exited before final zero')
            values=list(map(int,line.split()))
            if command>0:
                assert 1<=command<=40 and len(values)==2
                digs,x=values;assert digs>=0 and x>=0;T+=20*digs;assert x+command<=T<=100000000
                if len(cells)<T:cells.extend(b'\0'*(T-len(cells)))
                assert not any(cells[x:x+command]);cells[x:x+command]=b'\1'*command
                pipes.append((x,command));F+=command;peak=max(peak,F)
            else:
                pid=-command;assert 0<pid<len(pipes) and pipes[pid] is not None
                x,n=pipes[pid];assert values==[x] and all(cells[x:x+n]);cells[x:x+n]=b'\0'*n;pipes[pid]=None;F-=n
        mem=memory() # Still alive, blocked waiting for the final zero.
        proc.stdin.write(b'0\n');proc.stdin.flush();proc.stdin.close();proc.wait(timeout=30);thread.join(timeout=5)
        assert proc.returncode==0
        final_cpu=cpu()
        return {'test':path.name,'repeat':repeat,'solver':str(solver),'solver_sha256':hashlib.sha256(solver.read_bytes()).hexdigest(),
           'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'affinity_mask':hex(one_core),'workers':1,
           'CPU_user_plus_kernel_s':final_cpu,'wall_s':time.monotonic()-started,**mem,
           'T':T,'F':F,'KPI':F/T if T else 0,'weighted_score':weight*F/T if T else 0,'volume_lower_bound':20*((peak+19)//20),
           'CPU_below_5s':final_cpu<5,'working_set_below_256MiB':mem['peak_working_set_MiB']<256,
           'private_commit_below_256MiB':mem['peak_private_commit_MiB']<256,
           'protocol':'direct per-command interaction and independent occupancy validation; not official interactor',
           'stderr':b''.join(errors).decode('utf-8','replace')}
    finally:
        if proc.poll() is None:proc.kill();proc.wait()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--solver',type=Path,required=True);ap.add_argument('--tests',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--repeat',type=int,default=3);ap.add_argument('--wall-timeout',type=float,default=180);a=ap.parse_args()
    if sys.platform!='win32':raise SystemExit('Native Windows required; no emulated G5420 timings are reported.')
    if a.out.exists():raise SystemExit('Output already exists; choose a new path to preserve measurements.')
    paths=sorted(a.tests.rglob('*.in')) if a.tests.is_dir() else [a.tests];assert paths
    assert a.repeat>0 and a.wall_timeout>0
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        cpu_name=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
    data={'platform':sys.platform,'windows_version':platform.platform(),'CPU_model':cpu_name,'logical_CPUs_in_machine':os.cpu_count(),
       'measurement':'one pinned logical CPU, process user+kernel seconds','records':[]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    for p in paths:
        for repeat in range(1,a.repeat+1):
            r=run(a.solver.resolve(),p,repeat,a.wall_timeout);data['records'].append(r)
            a.out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            print(p.name,repeat,f"CPU={r['CPU_user_plus_kernel_s']:.3f}s",f"peakWS={r['peak_working_set_MiB']:.1f}MiB",f"KPI={r['KPI']:.6f}",flush=True)
if __name__=='__main__':main()
