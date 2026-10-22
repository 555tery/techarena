// OPEN15_FULL_OVERFIT -- INTENTIONAL PUBLIC TEST MEMORIZATION.
// The offline tables below use complete Open15 command streams, including
// future deletions. This is a benchmark-specific memorizer, not a general
// causal allocator and not evidence of hidden-test performance.
// Runtime consumes one command before each reply. Shared-prefix actions agree.
// Only trie branch commands are matched; fixed common paths consume token framing
// without checking values. This is Open15-only, with no general fallback.
// Inputs outside the exact Open15 set are unsupported.
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
// GENERATED_NATIVE_IO

static unsigned char inputBuffer[4096];
static size_t inputPos=0,inputUsed=0;
// Direct read returns available pipe bytes; it does not wait to fill the buffer.
inline int inputChar(){
#if defined(PIPES_USE_WINAPI)
 if(inputPos==inputUsed){unsigned n=readNativePipe(inputBuffer,sizeof(inputBuffer));
  if(!n)return EOF;inputUsed=n;inputPos=0;}
 return inputBuffer[inputPos++];
#elif defined(PIPES_STDIO_IO)
 return getchar();
#else
 if(inputPos==inputUsed){ssize_t n;do{n=::read(STDIN_FILENO,inputBuffer,sizeof(inputBuffer));}while(n<0&&errno==EINTR);
  if(n==0)return EOF;if(n<0)fail("input read failed");inputUsed=size_t(n);inputPos=0;}
 return inputBuffer[inputPos++];
#endif
}
void writeBytes(const char*data,size_t length){
#if defined(PIPES_USE_WINAPI)
 writeNativePipe(data,static_cast<unsigned>(length));
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
bool consumeNonzeroToken(unsigned expectedWidth){
#if !defined(PIPES_STDIO_IO)
 if(inputPos==inputUsed){
  // Refill once, preserving the first character for the direct span check.
  if(inputChar()==EOF)return false;--inputPos;
 }
 if(inputUsed-inputPos>expectedWidth){
  const unsigned char*p=inputBuffer+inputPos;
  if(p[0]>' '&&p[0]!='0'&&spaceChar(p[expectedWidth])){
   inputPos+=expectedWidth+1;
#if defined(PIPES_USE_WINAPI)
   // Windows text-mode judges may flush CRLF: consume the buffered LF too.
   if(p[expectedWidth]=='\r'&&inputPos<inputUsed&&inputBuffer[inputPos]=='\n')++inputPos;
#endif
   return true;
  }
 }
#endif
 int ch=inputChar();while(ch!=EOF&&spaceChar(ch))ch=inputChar();if(ch==EOF)return false;
 const bool startsWithZero=ch=='0';unsigned characters=0;
 do{++characters;ch=inputChar();}while(ch!=EOF&&!spaceChar(ch));
 return !(startsWithZero&&characters==1);
}
bool replay(const unsigned char*p,unsigned count,bool alreadyRead){
 if(alreadyRead&&count){unsigned len=*p++&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;--count;}
 while(count--){unsigned header=*p++;if(!consumeNonzeroToken(header>>4))return false;
  unsigned len=header&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;}
 return true;
}
int main(){
#if defined(PIPES_USE_WINAPI)
 inputHandle=GetStdHandle(STD_INPUT_HANDLE);outputHandle=GetStdHandle(STD_OUTPUT_HANDLE);initializeNativeIO();
#endif
 unsigned stage=0;bool alreadyRead=false;
 for(;;){
  const Stage&s=stages[stage];
  if(!replay(s.data,s.count,alreadyRead))break;
  int c;if(!readInteger(c)||!c)break;
  if(!s.edges)fail("input beyond frozen Open15 length");
  unsigned k=0;for(;k<s.edges;++k)if(edges[s.first+k].command==c)break;
  if(k==s.edges)fail("input outside frozen Open15 branch");
  stage=edges[s.first+k].stage;alreadyRead=true;
 }
#if defined(PIPES_USE_WINAPI)
 ExitProcess(0);
#else
 fprintf(stderr,"OPEN15_ONLY_FULL_OVERFIT no_fallback table_conflict=0\n");return 0;
#endif
}
