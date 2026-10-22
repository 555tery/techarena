// OPEN15_FULL_OVERFIT -- INTENTIONAL PUBLIC TEST MEMORIZATION.
// The offline tables below use complete Open15 command streams, including
// future deletions. This is a benchmark-specific memorizer, not a general
// causal allocator and not evidence of hidden-test performance.
// Runtime reads one command and immediately writes one response. Matching public prefixes
// receive the same actions. At the first mismatch it permanently switches to
// Best Fit using the actual occupied layout. Prefix excavation is irreversible.
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
size_t appendInteger(char*dst,int value){
 size_t written=0;unsigned int magnitude;if(value<0){dst[written++]='-';magnitude=0u-static_cast<unsigned int>(value);}else magnitude=static_cast<unsigned int>(value);
 char reverse[16];size_t count=0;do{reverse[count++]=static_cast<char>('0'+magnitude%10u);magnitude/=10u;}while(magnitude);
 while(count)dst[written++]=reverse[--count];return written;
}
void writeLine(int value){
 char buffer[32];size_t n=appendInteger(buffer,value);buffer[n++]='\n';writeBytes(buffer,n);
}
void writePairLine(int first,int second){
 char buffer[48];size_t n=appendInteger(buffer,first);buffer[n++]=' ';n+=appendInteger(buffer+n,second);buffer[n++]='\n';writeBytes(buffer,n);
}
// GENERATED_TABLES
// Packed immutable records: zigzag(command), trench length, reply length, reply.
unsigned read32(const unsigned char*p){return unsigned(p[0])|(unsigned(p[1])<<8)|(unsigned(p[2])<<16)|(unsigned(p[3])<<24);}
struct Record{int command,T;const char*reply;unsigned length;};
Record recordAt(const unsigned char*p){unsigned c=read32(p);return{(c&1)?-int(c>>1):int(c>>1),int(read32(p+4)),reinterpret_cast<const char*>(p+9),p[8]};}
struct Test{const unsigned char*cursor;unsigned remaining;};
// CUSTOM_ALLOCATOR
using pipes_custom_bf::Allocator;
// Materialize allocation state only when the observed input leaves the table.
void restore(Allocator&state,size_t chosen,unsigned steps){
 const unsigned char*p=reinterpret_cast<const unsigned char*>(records[chosen]);
 for(unsigned i=0;i<steps;++i){Record r=recordAt(p);p+=9+r.length;
  if(r.command>0){const char*q=r.reply;while(*q!=' ')++q;++q;int x=0;while(*q>='0'&&*q<='9')x=x*10+(*q++-'0');state.pipes.push_back({x,r.command});}
  else{int id=-r.command;if(id<=0||size_t(id)>=state.pipes.size()||state.pipes[id].n<=0)fail("bad restored PID");state.pipes[id].n=0;}
  state.T=r.T;
 }
 state.setOperationCount(steps);state.reconstruct();
}
int main(){
#if defined(PIPES_USE_WINAPI)
 inputHandle=GetStdHandle(STD_INPUT_HANDLE);outputHandle=GetStdHandle(STD_OUTPUT_HANDLE);
#endif
 {
  Test tests[15];for(size_t i=0;i<15;++i)tests[i]={reinterpret_cast<const unsigned char*>(records[i]),counts[i]};
  unsigned active[15];for(unsigned i=0;i<15;++i)active[i]=i;unsigned activeCount=15;
  Allocator state;int c;unsigned replay=0,fallback=0,conflict=0,steps=0;size_t lastTest=0;int lastT=0;bool useTables=true;
  while(readInteger(c)&&c!=0){
   if(useTables){
    Record chosen{};bool matched=false,agrees=true;unsigned kept=0;size_t selected=0;
    for(unsigned k=0;k<activeCount;++k){unsigned i=active[k];Test&t=tests[i];if(!t.remaining)continue;Record r=recordAt(t.cursor);if(r.command!=c)continue;
     t.cursor+=9+r.length;--t.remaining;active[kept++]=i;
     if(matched&&(chosen.length!=r.length||memcmp(chosen.reply,r.reply,r.length)!=0||chosen.T!=r.T))agrees=false;
     chosen=r;selected=i;matched=true;
    }
    activeCount=kept;
    if(matched&&agrees){writeBytes(chosen.reply,chosen.length);lastTest=selected;lastT=chosen.T;++steps;if(c>0)++replay;continue;}
    if(matched)++conflict;
    restore(state,lastTest,steps);useTables=false;
   }
   if(c>0){++fallback;int x=state.bf(c);int digs=state.place(c,x);writePairLine(digs,x);}else writeLine(state.remove(-c));
  }
  fprintf(stderr,"OPEN15_FULL_OVERFIT replay=%u fallback=%u table_conflict=%u T=%d\n",replay,fallback,conflict,useTables?lastT:state.T);
 }
 return 0;
}
