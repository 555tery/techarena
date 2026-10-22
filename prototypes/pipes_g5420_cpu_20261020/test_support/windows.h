// Unit-test stub only. This is not a Windows SDK or native Windows validation.
#pragma once
struct FILETIME {std::uint32_t dwLowDateTime=0,dwHighDateTime=0;};
inline bool fake_ok=true;
inline FILETIME fake_kernel{},fake_user{};
inline void* GetCurrentProcess(){return nullptr;}
inline int GetProcessTimes(void*,FILETIME*,FILETIME*,FILETIME* k,FILETIME* u){*k=fake_kernel;*u=fake_user;return fake_ok;}
