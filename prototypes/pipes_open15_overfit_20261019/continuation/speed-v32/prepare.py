"""Terminate only this completed, resource-free solver through Ntdll.

All replies and the final zero are consumed first. No allocation, buffered
output, worker thread, pending IO or C++ destructor needs user-mode teardown.
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'speed-v31'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'solution.cpp')=='133f65fac8e260c52edc895bf0da66adfca348e27cf123bbb2b2f33ff9759fde'
s=(BASE/'solution.cpp').read_text()
s=s.replace('__declspec(dllimport) HANDLE __stdcall GetStdHandle(DWORD);','__declspec(dllimport) HANDLE __stdcall GetStdHandle(DWORD);\n__declspec(dllimport) HANDLE __stdcall GetCurrentProcess();')
s=s.replace('static NativeWait nativeWait;','''static NativeWait nativeWait;
using NativeTerminate=LONG (NTAPI *)(HANDLE,LONG);
static NativeTerminate nativeTerminate;''')
needle='static void initializeNativeIO(){'
s=s.replace(needle,'''#if defined(PIPES_WINAPI_TEST)
LONG shimNativeTerminate(HANDLE process,LONG status){
 if(process!=GetCurrentProcess()||status!=0)fail("invalid self termination");
 ExitProcess(static_cast<unsigned>(status));
}
#endif
''' + needle)
s=s.replace('if(!nativeRead||!nativeWrite||!nativeWait)fail("native pipe APIs unavailable");','''nativeTerminate=reinterpret_cast<NativeTerminate>(GetProcAddress(module,"NtTerminateProcess"));
 if(!nativeRead||!nativeWrite||!nativeWait||!nativeTerminate)fail("native pipe APIs unavailable");''')
needle='#if defined(PIPES_USE_WINAPI)\n ExitProcess(0);'
assert s.count(needle)==1
s=s.replace(needle,'''#if defined(PIPES_USE_WINAPI)
 // This solver owns no buffered IO or destructible runtime state. End only
 // our own process after the protocol completes; never target another PID.
 nativeTerminate(GetCurrentProcess(),0);
 ExitProcess(2); // A successful self-termination cannot return.
''')
(HERE/'solution.cpp').write_text(s)
shim=(BASE/'winapi_test_shim.hpp').read_text()
needle='FARPROC GetProcAddress(HMODULE,const char*name){'
shim=shim.replace(needle,'''HANDLE GetCurrentProcess(){return -1;}
LONG shimNativeTerminate(HANDLE,LONG);
''' + needle + '''
 if(!strcmp(name,"NtTerminateProcess"))return reinterpret_cast<FARPROC>(&shimNativeTerminate);
''')
(HERE/'winapi_test_shim.hpp').write_text(shim)
for f in ('verify.py','verify_support.py'):(HERE/f).write_bytes((BASE/f).read_bytes())
flags=['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'scope':'Exact Open15 full overfit. End only self via NtTerminateProcess after all IO and final zero. No mutable resource requiring CRT/DLL teardown.','references':['https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-zwterminateprocess','https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getcurrentprocess'],'speed_evidence':'Less user-mode process teardown; actual server CPU effect unmeasured.'},indent=2)+'\n')
print(sha(HERE/'solution.cpp'))
