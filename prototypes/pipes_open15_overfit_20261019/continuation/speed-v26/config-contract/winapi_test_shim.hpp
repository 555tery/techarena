// Test-only POSIX implementation of the synchronous Win32 pipe API.
// Force tiny partial reads/writes; does not validate Windows ABI or performance.
#include <unistd.h>
#include <cstdint>
#include <cerrno>
using HANDLE=int;using DWORD=uint32_t;using BOOL=int;
constexpr DWORD STD_INPUT_HANDLE=DWORD(-10),STD_OUTPUT_HANDLE=DWORD(-11);
constexpr DWORD ERROR_BROKEN_PIPE=109,ERROR_HANDLE_EOF=38,ERROR_MORE_DATA=234;
#ifndef PIPES_SHIM_READ_MAX
#define PIPES_SHIM_READ_MAX 2
#endif
static DWORD last_error=0;
HANDLE GetStdHandle(DWORD id){return id==STD_INPUT_HANDLE?0:1;}
DWORD GetLastError(){return last_error;}
BOOL ReadFile(HANDLE h,void*data,DWORD length,DWORD*count,void*){
 ssize_t n;do{n=::read(h,data,length>PIPES_SHIM_READ_MAX?PIPES_SHIM_READ_MAX:length);}while(n<0&&errno==EINTR);
 if(n<=0){*count=0;last_error=n==0?ERROR_BROKEN_PIPE:5;return 0;}
 *count=DWORD(n);return 1;
}
BOOL WriteFile(HANDLE h,const void*data,DWORD length,DWORD*count,void*){
 ssize_t n;do{n=::write(h,data,length>3?3:length);}while(n<0&&errno==EINTR);
 if(n<=0){*count=0;last_error=5;return 0;}*count=DWORD(n);return 1;
}

[[noreturn]] void ExitProcess(unsigned int status){::_exit(static_cast<int>(status));}

// Native-I/O ABI and completion shim; partial operations remain enforced above.
using LONG=int32_t;using ULONG=uint32_t;using ULONG_PTR=uintptr_t;
using HMODULE=void*;
#define NTAPI
constexpr DWORD INFINITE=0xffffffffu,WAIT_OBJECT_0=0;
struct NativeIOStatus;
LONG shimNativeRead(HANDLE,HANDLE,void*,void*,NativeIOStatus*,void*,ULONG,void*,void*);
LONG shimNativeWrite(HANDLE,HANDLE,void*,void*,NativeIOStatus*,void*,ULONG,void*,void*);
HMODULE GetModuleHandleW(const wchar_t*){return reinterpret_cast<void*>(uintptr_t(1));}
using FARPROC=void(*)();
static int configScenario=0;static unsigned configCalls=0;
LONG shimQueryMode(HANDLE,NativeIOStatus*,void*data,ULONG length,ULONG kind){
 if(length!=sizeof(ULONG)||kind!=16)return static_cast<LONG>(0xc000000du);
 *static_cast<ULONG*>(data)=configScenario==1?0:0x20u;return configScenario==2?static_cast<LONG>(0xc000000du):0;
}
BOOL shimSetMode(HANDLE handle,unsigned char flags){++configCalls;return configScenario!=3&&handle==1&&flags==2;}
FARPROC GetProcAddress(HMODULE,const char*name){
 if(!strcmp(name,"NtQueryInformationFile"))return reinterpret_cast<FARPROC>(&shimQueryMode);
 if(!strcmp(name,"SetFileCompletionNotificationModes"))return reinterpret_cast<FARPROC>(&shimSetMode);
return name[2]=='R'?reinterpret_cast<FARPROC>(&shimNativeRead):reinterpret_cast<FARPROC>(&shimNativeWrite);}
DWORD WaitForSingleObject(HANDLE,DWORD){return WAIT_OBJECT_0;}
