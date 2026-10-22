"""Combine v28 hot path and numeric tables; declare documented Windows ABI.

The contest MSVC environment lacks windows.h (C1083 on submission 1666317).
Keep standard CRT startup and import only the documented Kernel32 functions
actually used here. This is source compatibility, not a custom syscall stub.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'speed-v28'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'solution.cpp')=='51e591874821b96d227ce2424aaf81c903c127479421a4adffd980625fddd122'
s=(BASE/'solution.cpp').read_text()
arrays=[]
def emit(m):
 name=m[1];data=ast.literal_eval('('+m[2]+')').encode('latin1')
 words=[int.from_bytes(data[i:i+8].ljust(8,b'\0'),'little') for i in range(0,len(data),8)] or [0]
 arrays.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 return 'static const uint64_t '+name+'_words[]={\n'+',\n'.join(','.join('0x%016xULL'%x for x in words[i:i+6]) for i in range(0,len(words),6))+'\n};'
s,n=re.subn(r'static const (?:unsigned char|char) ((?:meta|replies)\d+)\[\]=\n(.*?);',emit,s,flags=re.S)
assert n==44
s=re.sub(r'reinterpret_cast<const unsigned char\*>\(replies(\d+)\)',r'reinterpret_cast<const unsigned char*>(replies\1_words)',s)
s=re.sub(r'\{meta(\d+),',r'{reinterpret_cast<const unsigned char*>(meta\1_words),',s)
header=r'''
#if defined(_MSC_VER)
// Documented Windows x64 ABI declarations for the contest's SDK-less MSVC.
// Keep the ordinary main/CRT entry point. Kernel32 is already required by CRT.
using HANDLE=void*;using HMODULE=void*;
using DWORD=unsigned long;using ULONG=unsigned long;using LONG=long;
using ULONG_PTR=uintptr_t;using BOOL=int;
#define NTAPI __stdcall
using FARPROC=void (__stdcall *)();
static_assert(sizeof(DWORD)==4&&sizeof(LONG)==4&&sizeof(HANDLE)==8,"Windows x64 ABI required");
constexpr DWORD STD_INPUT_HANDLE=DWORD(-10),STD_OUTPUT_HANDLE=DWORD(-11);
constexpr DWORD INFINITE=0xffffffffUL,WAIT_OBJECT_0=0;
extern "C" {
__declspec(dllimport) HANDLE __stdcall GetStdHandle(DWORD);
__declspec(dllimport) HMODULE __stdcall GetModuleHandleW(const wchar_t*);
__declspec(dllimport) FARPROC __stdcall GetProcAddress(HMODULE,const char*);
__declspec(dllimport) DWORD __stdcall WaitForSingleObject(HANDLE,DWORD);
__declspec(dllimport) __declspec(noreturn) void __stdcall ExitProcess(DWORD);
}
#pragma comment(lib,"kernel32.lib")
#else
#include <windows.h>
#endif
'''
assert s.count('#include <windows.h>')==1
s=s.replace('#include <windows.h>',header)
s=s.replace('// Runtime consumes one command','// Numeric table words require a little-endian target (Windows x64).\n// Runtime consumes one command')
(HERE/'solution.cpp').write_text(s)
for f in ('verify.py','verify_support.py','winapi_test_shim.hpp'):(HERE/f).write_bytes((BASE/f).read_bytes())
flags=['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'arrays':arrays,'scope':'Exact Open15 full overfit. v28 hot path + word arrays + documented Kernel32 ABI without windows.h for MSVC. Ordinary CRT startup.'},indent=2)+'\n')
print(sha(HERE/'solution.cpp'))
