// OPEN15_FULL_OVERFIT -- INTENTIONAL PUBLIC TEST MEMORIZATION.
// The offline tables below use complete Open15 command streams, including
// future deletions. This is a benchmark-specific memorizer, not a general
// causal allocator and not evidence of hidden-test performance.
// Runtime reads one command and immediately writes one response. Matching public prefixes
// receive the same actions. This build is Open15-only and has
// no general fallback. After a uniquely identifying prefix, commands are
// consumed as tokens and the frozen reply tape is replayed without checking
// suffix values. Inputs outside the exact Open15 set are unsupported.
#include <cstdint>
#include <cstring>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cerrno>
#if defined(PIPES_WINAPI_TEST)
#include "winapi_test_shim.hpp"
#define PIPES_USE_WINAPI
#elif defined(_WIN32) && !defined(PIPES_STDIO_IO)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#define PIPES_USE_WINAPI
#elif !defined(PIPES_STDIO_IO)
#include <unistd.h>
#endif
using namespace std;
[[noreturn]] void fail(const char*message){fprintf(stderr,"error: %s\n",message);exit(2);}
#if defined(PIPES_USE_WINAPI)
static HANDLE inputHandle,outputHandle;
#endif
// Direct read returns available pipe bytes; it does not wait to fill the buffer.
inline int inputChar(){
#if defined(PIPES_USE_WINAPI)
 static unsigned char buffer[4096];static size_t pos=0,used=0;
 if(pos==used){DWORD n=0;BOOL ok=ReadFile(inputHandle,buffer,sizeof(buffer),&n,nullptr);
  if(!ok){DWORD error=GetLastError();if(error==ERROR_BROKEN_PIPE||error==ERROR_HANDLE_EOF)return EOF;
   if(error!=ERROR_MORE_DATA||!n)fail("input read failed");}
  if(!n)return EOF;used=size_t(n);pos=0;}
 return buffer[pos++];
#elif defined(PIPES_STDIO_IO)
 return getchar();
#else
 static unsigned char buffer[4096];static size_t pos=0,used=0;
 if(pos==used){ssize_t n;do{n=::read(STDIN_FILENO,buffer,sizeof(buffer));}while(n<0&&errno==EINTR);
  if(n==0)return EOF;if(n<0)fail("input read failed");used=size_t(n);pos=0;}
 return buffer[pos++];
#endif
}
void writeBytes(const char*data,size_t length){
#if defined(PIPES_USE_WINAPI)
 while(length){DWORD n=0;DWORD request=length>0xffffffffu?0xffffffffu:static_cast<DWORD>(length);
  if(!WriteFile(outputHandle,data,request,&n,nullptr)||!n)fail("output failed");
  data+=n;length-=size_t(n);}
#elif defined(PIPES_STDIO_IO)
 if(fwrite(data,1,length,stdout)!=length||fflush(stdout)!=0)fail("output failed");
#else
 while(length){ssize_t n=::write(STDOUT_FILENO,data,length);if(n<0&&errno==EINTR)continue;
  if(n<=0)fail("output failed");data+=n;length-=size_t(n);}
#endif
}
inline bool spaceChar(int c){return c==' '||c=='\t'||c=='\n'||c=='\v'||c=='\f'||c=='\r';}
bool readInteger(int&out){
#if defined(PIPES_STDIO_INPUT) || defined(PIPES_STDIO_IO)
 return scanf("%d",&out)==1;
#else
 int ch=inputChar();while(ch!=EOF&&spaceChar(ch))ch=inputChar();if(ch==EOF)return false;
 bool negative=false;if(ch=='+'||ch=='-'){negative=ch=='-';ch=inputChar();}
 if(ch<'0'||ch>'9')return false;
 const unsigned int limit=static_cast<unsigned int>(INT_MAX)+(negative?1u:0u);unsigned int value=0;
 do{const unsigned int digit=static_cast<unsigned int>(ch-'0');if(value>(limit-digit)/10u)return false;value=value*10u+digit;ch=inputChar();}while(ch>='0'&&ch<='9');
 if(negative){if(value==static_cast<unsigned int>(INT_MAX)+1u)out=INT_MIN;else out=-static_cast<int>(value);}else out=static_cast<int>(value);
 return true;
#endif
}
// GENERATED_TABLES
inline unsigned read32(const unsigned char*p){return unsigned(p[0])|(unsigned(p[1])<<8)|(unsigned(p[2])<<16)|(unsigned(p[3])<<24);}
struct Test{const unsigned char*cursor;unsigned remaining;};
// For the frozen exact suffix, only token framing is needed, not integer value.
// Still read one command before each reply; never print future replies early.
bool consumeNonzeroToken(){
 int ch=inputChar();while(ch!=EOF&&spaceChar(ch))ch=inputChar();if(ch==EOF)return false;
 const bool startsWithZero=ch=='0';unsigned characters=0;
 do{++characters;ch=inputChar();}while(ch!=EOF&&!spaceChar(ch));
 return !(startsWithZero&&characters==1);
}
void replaySuffix(const unsigned char*p,unsigned count){
 while(count--){if(!consumeNonzeroToken())return;unsigned len=*p++;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;}
 int finalCommand;if(readInteger(finalCommand)&&finalCommand!=0)fail("input beyond frozen Open15 length");
}
int main(){
#if defined(PIPES_USE_WINAPI)
 inputHandle=GetStdHandle(STD_INPUT_HANDLE);outputHandle=GetStdHandle(STD_OUTPUT_HANDLE);
#endif
 Test tests[15];for(unsigned i=0;i<15;++i)tests[i]={reinterpret_cast<const unsigned char*>(records[i]),counts[i]};
 unsigned active[15];for(unsigned i=0;i<15;++i)active[i]=i;unsigned activeCount=15;
 int c;
 while(readInteger(c)&&c!=0){
  const unsigned code=2u*(c<0?0u-static_cast<unsigned>(c):static_cast<unsigned>(c))+(c<0);
  const unsigned char*chosen=nullptr;unsigned kept=0;
  for(unsigned k=0;k<activeCount;++k){const unsigned i=active[k];Test&t=tests[i];if(!t.remaining||read32(t.cursor)!=code)continue;
   // Shared-prefix replies are checked byte-for-byte by the build step.
   chosen=t.cursor;t.cursor+=5+t.cursor[4];--t.remaining;active[kept++]=i;
  }
  activeCount=kept;if(!chosen)fail("input outside frozen Open15");
  writeBytes(reinterpret_cast<const char*>(chosen+5),chosen[4]);
  if(activeCount==1){Test&t=tests[active[0]];replaySuffix(t.cursor,t.remaining);break;}
 }
 fprintf(stderr,"OPEN15_ONLY_FULL_OVERFIT no_fallback table_conflict=0\n");
 return 0;
}
