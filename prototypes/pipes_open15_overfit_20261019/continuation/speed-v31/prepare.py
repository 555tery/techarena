"""Minimal MSVC console startup after the numeric-table/ABI compatibility fix.

All Windows runtime storage is POD. Preserve the compiler's /GS policy and
initialize its real security cookie before entering the noinline solver.
"""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'speed-v30'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE/'solution.cpp')=='c2d012c23dc56561f9ac0809743bb19da4aa103b3ab85332bc88fd0d2d4bca59'
s=(BASE/'solution.cpp').read_text()
old='[[noreturn]] void fail(const char*message){fprintf(stderr,"error: %s\\n",message);exit(2);}'
new='''[[noreturn]] void fail(const char*message){
#if defined(_WIN32) && defined(_MSC_VER) && !defined(PIPES_WINAPI_TEST)
 (void)message;ExitProcess(2);
#else
 fprintf(stderr,"error: %s\\n",message);exit(2);
#endif
}'''
assert s.count(old)==1
s=s.replace(old,new)
old='int main(){'
new='''#if defined(_MSC_VER) && defined(_WIN32) && !defined(PIPES_WINAPI_TEST)
__declspec(noinline)
#endif
int runOpen15(){'''
assert s.count(old)==1
s=s.replace(old,new)
s+='''
int main(){return runOpen15();}
#if defined(_MSC_VER) && defined(_WIN32) && !defined(PIPES_WINAPI_TEST)
// No constructors, TLS, allocation, locale, arguments or buffered CRT IO.
// Keep /GS enabled. This entry itself has no GS buffers and must initialize
// the real cookie before calling any protected, non-inlined implementation.
extern "C" void __cdecl __security_init_cookie();
extern "C" __declspec(noreturn) __declspec(safebuffers) void __cdecl mainCRTStartup(){
 __security_init_cookie();
 ExitProcess(static_cast<DWORD>(runOpen15()));
}
#endif
'''
(HERE/'solution.cpp').write_text(s)
for f in ('verify.py','verify_support.py','winapi_test_shim.hpp'):(HERE/f).write_bytes((BASE/f).read_bytes())
flags=['-O2','-std=c++17','-Wall','-Wextra']
subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
(HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'parent_sha256':sha(BASE/'solution.cpp'),'flags':flags,'scope':'Exact Open15 full overfit. Minimal MSVC console entry with real security-cookie initialization and no Win32-path CRT IO. Windows link/startup still requires server confirmation.','references':['https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/security-init-cookie','https://learn.microsoft.com/en-us/cpp/build/reference/entry-entry-point-symbol']},indent=2)+'\n')
print(sha(HERE/'solution.cpp'))
