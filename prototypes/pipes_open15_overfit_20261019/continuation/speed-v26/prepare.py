"""Isolate a documented Windows pipe notification-mode experiment on v25."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'speed-v25'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE / 'solution.cpp') == '2abd02de6968851e40b442d0af595f9e297cc2185fda118c8cab38afbd4369b8'
source = (BASE / 'solution.cpp').read_text()
needle = 'static void initializeNativeIO(){'
helper = r'''
// This experiment changes only our inherited stdout handle. Never suppress
// a completion event on an asynchronous handle: the fallback waits on it.
// FileModeInformation=16 is documented by NtQueryInformationFile; mode 0x20
// is FILE_SYNCHRONOUS_IO_NONALERT. Notification flag 0x02 is documented by
// SetFileCompletionNotificationModes. No guessed syscall IDs are involved.
using QueryFileMode=LONG (NTAPI *)(HANDLE,NativeIOStatus*,void*,ULONG,ULONG);
using SetCompletionMode=BOOL (NTAPI *)(HANDLE,unsigned char);
static void configureOutputCompletion(HMODULE ntdll){
 auto query=reinterpret_cast<QueryFileMode>(GetProcAddress(ntdll,"NtQueryInformationFile"));
 HMODULE kernel=GetModuleHandleW(L"kernel32.dll");
 auto setMode=kernel?reinterpret_cast<SetCompletionMode>(GetProcAddress(kernel,"SetFileCompletionNotificationModes")):nullptr;
 if(!query||!setMode)fail("completion mode APIs unavailable");
 NativeIOStatus result;ULONG mode=0;
 if(query(outputHandle,&result,&mode,sizeof(mode),16)!=0||(mode&0x20u)==0)
  fail("stdout is not a verified synchronous pipe");
 if(!setMode(outputHandle,0x02u))fail("stdout completion optimization unavailable");
}
'''
assert source.count(needle) == 1
source = source.replace(needle, helper + needle)
needle = 'if(!nativeRead||!nativeWrite)fail("native pipe APIs unavailable");'
source = source.replace(needle, needle + '\n configureOutputCompletion(module);')
(HERE / 'solution.cpp').write_text(source)
shim = (BASE / 'winapi_test_shim.hpp').read_text()
needle = 'FARPROC GetProcAddress(HMODULE,const char*name){'
shim = shim.replace(needle, '''LONG shimQueryMode(HANDLE,NativeIOStatus*,void*data,ULONG length,ULONG kind){
 if(length!=sizeof(ULONG)||kind!=16)return static_cast<LONG>(0xc000000du);
 *static_cast<ULONG*>(data)=0x20u;return 0;
}
BOOL shimSetMode(HANDLE handle,unsigned char flags){return handle==1&&flags==2;}
''' + needle + '''
 if(!strcmp(name,"NtQueryInformationFile"))return reinterpret_cast<FARPROC>(&shimQueryMode);
 if(!strcmp(name,"SetFileCompletionNotificationModes"))return reinterpret_cast<FARPROC>(&shimSetMode);
''')
(HERE / 'winapi_test_shim.hpp').write_text(shim)
for name in ('verify.py', 'verify_support.py'):
 (HERE / name).write_bytes((BASE / name).read_bytes())
flags = ['-O2', '-std=c++17', '-Wall', '-Wextra']
subprocess.run(['/usr/bin/clang++', *flags, str(HERE / 'solution.cpp'), '-o', str(HERE / 'solver')], check=True)
(HERE / 'build.json').write_text(json.dumps({
 'source_sha256': sha(HERE / 'solution.cpp'),
 'binary_sha256': sha(HERE / 'solver'),
 'parent_sha256': sha(BASE / 'solution.cpp'),
 'flags': flags,
 'scope': 'Exact Open15 full overfit. stdout notification-mode optimization; require confirmed synchronous mode and successful configuration.',
 'kernel_performance': 'Not measurable on the local POSIX shim; real Windows acceptance and CPU are separate.',
 'references': [
  'https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setfilecompletionnotificationmodes',
  'https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationfile',
  'https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_mode_information'
 ]
}, indent=2) + '\n')
print(sha(HERE / 'solution.cpp'))
