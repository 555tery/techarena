#pragma once
#include <cstdint>
#include <cstddef>
#if defined(__x86_64__)
#define NTAPI __attribute__((ms_abi))
#else
#define NTAPI
#endif
using HANDLE=void*;using HMODULE=void*;using LONG=int32_t;using ULONG=uint32_t;
using DWORD=uint32_t;using ULONG_PTR=uintptr_t;using BOOL=int;
using FARPROC=void(NTAPI*)();
constexpr DWORD STD_INPUT_HANDLE=DWORD(-10),STD_OUTPUT_HANDLE=DWORD(-11);
constexpr DWORD ERROR_BROKEN_PIPE=109,ERROR_HANDLE_EOF=38,ERROR_MORE_DATA=234;
constexpr DWORD INFINITE=0xffffffffu,WAIT_OBJECT_0=0;
HANDLE NTAPI GetStdHandle(DWORD);
DWORD NTAPI GetLastError();
HMODULE NTAPI GetModuleHandleW(const wchar_t*);
FARPROC NTAPI GetProcAddress(HMODULE,const char*);
DWORD NTAPI WaitForSingleObject(HANDLE,DWORD);
BOOL NTAPI ReadFile(HANDLE,void*,DWORD,DWORD*,void*);
BOOL NTAPI WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
[[noreturn]] void NTAPI ExitProcess(unsigned int);
