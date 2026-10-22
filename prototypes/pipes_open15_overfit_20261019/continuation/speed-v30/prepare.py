"""Use documented Ntdll wait completion directly for pending pipe requests."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'speed-v29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'solution.cpp')=='f54eded134153c794db288d3412bd1ef55e391897ea9c7ca9898942399140063'
s=(BASE/'solution.cpp').read_text()
s=s.replace('static NativeIo nativeRead,nativeWrite;','''static NativeIo nativeRead,nativeWrite;
// Documented NtWaitForSingleObject ABI. Nonalertable, infinite wait; only
// STATUS_SUCCESS permits reading the completed IO_STATUS_BLOCK.
using NativeWait=LONG (NTAPI *)(HANDLE,unsigned char,void*);
static NativeWait nativeWait;''')
needle='static void initializeNativeIO(){'
s=s.replace(needle,'''#if defined(PIPES_WINAPI_TEST)
LONG shimNativeWait(HANDLE handle,unsigned char alertable,void*timeout){
 if(alertable||timeout)fail("invalid test wait arguments");
 return WaitForSingleObject(handle,INFINITE)==WAIT_OBJECT_0?0:static_cast<LONG>(0xc0000001u);
}
#endif
''' + needle)
s=s.replace('if(!nativeRead||!nativeWrite)fail("native pipe APIs unavailable");','''nativeWait=reinterpret_cast<NativeWait>(GetProcAddress(module,"NtWaitForSingleObject"));
 if(!nativeRead||!nativeWrite||!nativeWait)fail("native pipe APIs unavailable");''')
old='if(WaitForSingleObject(handle,INFINITE)!=WAIT_OBJECT_0)fail("native pipe wait failed");'
assert s.count(old)==1
s=s.replace(old,'if(nativeWait(handle,0,nullptr)!=0)fail("native pipe wait failed");')
(HERE/'solution.cpp').write_text(s)
shim=(BASE/'winapi_test_shim.hpp').read_text()
needle='FARPROC GetProcAddress(HMODULE,const char*name){'
shim=shim.replace(needle,'''LONG shimNativeWait(HANDLE,unsigned char,void*);
''' + needle + '''
 if(!strcmp(name,"NtWaitForSingleObject"))return reinterpret_cast<FARPROC>(&shimNativeWait);
''')
(HERE/'winapi_test_shim.hpp').write_text(shim)
for f in ('verify.py','verify_support.py'):(HERE/f).write_bytes((BASE/f).read_bytes())
flags=['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'scope':'Exact Open15 full overfit; direct nonalertable infinite NtWaitForSingleObject for pending completion. Ordinary CRT startup; no custom syscalls.','reference':'https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntwaitforsingleobject','speed_evidence':'Removal of Win32 wait wrapper only; server CPU effect unmeasured.'},indent=2)+'\n')
print(sha(HERE/'solution.cpp'))
