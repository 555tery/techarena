#include "winapi_test_shim.hpp"
#include "bench_api.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
struct Row{std::string command,answer;};
static std::vector<std::vector<Row>> fixtures;
static unsigned currentCase,currentRow,readOffset,writeOffset;
static bool verifyOutput;
static uint64_t completed;
std::jmp_buf benchmarkFinish;
static void die(const char*reason){std::fprintf(stderr,"memory handshake: %s\n",reason);std::abort();}
static unsigned get32(std::ifstream&f){uint32_t x;f.read(reinterpret_cast<char*>(&x),4);if(!f)die("fixture header");return x;}
static std::string getString(std::ifstream&f){unsigned n=get32(f);std::string s(n,'\0');f.read(&s[0],n);if(!f)die("fixture body");return s;}
void loadBenchmarkFixtures(const char*path,bool crlf){
 std::ifstream f(path,std::ios::binary);unsigned count=get32(f);fixtures.resize(count);
 for(auto&rows:fixtures){unsigned n=get32(f);rows.resize(n);for(auto&r:rows){r.command=getString(f);r.answer=getString(f);
  if(crlf){r.command.pop_back();r.command+="\r\n";}
 }}
}
void startBenchmarkCase(unsigned i,bool verify){currentCase=i;currentRow=readOffset=writeOffset=0;verifyOutput=verify;}
unsigned benchmarkCases(){return fixtures.size();}
uint64_t benchmarkCommands(){uint64_t n=0;for(auto&r:fixtures)n+=r.size()-1;return n;}
uint64_t benchmarkCompletedCommands(){return completed;}
HANDLE NTAPI GetStdHandle(DWORD id){return reinterpret_cast<HANDLE>(uintptr_t(id==STD_INPUT_HANDLE?1:2));}
DWORD NTAPI GetLastError(){return 0;}
HMODULE NTAPI GetModuleHandleW(const wchar_t*){return reinterpret_cast<HMODULE>(uintptr_t(3));}
DWORD NTAPI WaitForSingleObject(HANDLE,DWORD){return WAIT_OBJECT_0;}
BOOL NTAPI ReadFile(HANDLE,void*buffer,DWORD capacity,DWORD*count,void*){
 if(currentRow>=fixtures[currentCase].size())die("read past final zero");
 auto&r=fixtures[currentCase][currentRow];
 if(writeOffset)die("read before complete reply");
 unsigned n=r.command.size()-readOffset;if(n>capacity)n=capacity;
 if(!n)die("read next command before reply");
 std::memcpy(buffer,r.command.data()+readOffset,n);readOffset+=n;*count=n;return 1;
}
BOOL NTAPI WriteFile(HANDLE,const void*buffer,DWORD length,DWORD*count,void*){
 if(currentRow>=fixtures[currentCase].size())die("extra reply");auto&r=fixtures[currentCase][currentRow];
 if(readOffset!=r.command.size())die("reply before complete command");
 if(!length||writeOffset+length>r.answer.size())die("incorrect reply length");
 if(verifyOutput&&std::memcmp(buffer,r.answer.data()+writeOffset,length))die("wrong reply bytes");
 writeOffset+=length;*count=length;
 if(writeOffset==r.answer.size()){++currentRow;readOffset=writeOffset=0;++completed;}
 return 1;
}
struct IOStatus{union{LONG status;void*pointer;};ULONG_PTR information;};
static LONG NTAPI memoryRead(HANDLE h,HANDLE,void*,void*,IOStatus*r,void*data,ULONG n,void*,void*){DWORD done;ReadFile(h,data,n,&done,nullptr);r->status=0;r->information=done;return 0;}
static LONG NTAPI memoryWrite(HANDLE h,HANDLE,void*,void*,IOStatus*r,void*data,ULONG n,void*,void*){DWORD done;WriteFile(h,data,n,&done,nullptr);r->status=0;r->information=done;return 0;}
FARPROC NTAPI GetProcAddress(HMODULE,const char*name){
 if(!std::strcmp(name,"NtReadFile"))return reinterpret_cast<FARPROC>(&memoryRead);
 if(!std::strcmp(name,"NtWriteFile"))return reinterpret_cast<FARPROC>(&memoryWrite);
 die("unexpected native API");return nullptr;
}
[[noreturn]] void NTAPI ExitProcess(unsigned int status){
 if(status)die("candidate exit failure");
 if(currentRow+1!=fixtures[currentCase].size()||readOffset!=fixtures[currentCase].back().command.size())die("missing command/reply");
 std::longjmp(benchmarkFinish,1);
}
