using LONG=long;
using ULONG=unsigned int;
using ULONG_PTR=unsigned long long;
using HANDLE=void*;
using HMODULE=void*;
using DWORD=unsigned long;
using FARPROC=void(*)();
#define NTAPI __stdcall
#define PIPES_USE_WINAPI
constexpr DWORD INFINITE=0xffffffffu,WAIT_OBJECT_0=0;
struct NativeIOStatus;
[[noreturn]] void fail(const char*);
extern "C" HMODULE GetModuleHandleW(const wchar_t*);
extern "C" FARPROC GetProcAddress(HMODULE,const char*);
extern "C" DWORD WaitForSingleObject(HANDLE,DWORD);
static HANDLE inputHandle,outputHandle;

#include "native_io.inc"
extern "C" void set_handles(void*in,void*out){inputHandle=in;outputHandle=out;}
extern "C" void init_call(){initializeNativeIO();}
extern "C" unsigned read_call(void*data,unsigned capacity){return readNativePipe(data,capacity);}
extern "C" void write_call(const char*data,unsigned length){writeNativePipe(data,length);}
